"""Inputs of the ``X-CFC-API-KEY`` request header.

Up to app 4.x the hash salt and the string inserted into the hash were built
into the app. Since 5.x the app downloads them from ``initialize_android.json``
(see :data:`constants.SECURITY_KEY_INITIALIZE_URL`), so Panasonic can rotate
them without an app update. Each value in that file is an RSA-OAEP (SHA-256)
blob that the app "decrypts" with a public key, which needs only the raw RSA
public operation and an OAEP unpad, both done here without extra
dependencies.

The values are fetched at most once per :data:`_REFRESH_INTERVAL`, shared by
every session in the process. Until they are fetched, or whenever fetching
fails, the values the file held when app 5.1.2 was released are used.
"""

import asyncio
import base64
import hashlib
import logging
import time

import aiohttp

from . import constants

_LOGGER = logging.getLogger(__name__)

_REFRESH_INTERVAL = 24 * 60 * 60
_RETRY_INTERVAL = 60 * 60
_FETCH_TIMEOUT = aiohttp.ClientTimeout(total=15)


def _read_der_length(data: bytes, pos: int) -> tuple[int, int]:
    length = data[pos]
    pos += 1
    if length & 0x80:
        count = length & 0x7F
        length = int.from_bytes(data[pos:pos + count], "big")
        pos += count
    return length, pos


def _read_der_integer(data: bytes, pos: int) -> tuple[int, int]:
    if data[pos] != 0x02:
        raise ValueError("Expected a DER INTEGER")
    length, pos = _read_der_length(data, pos + 1)
    return int.from_bytes(data[pos:pos + length], "big"), pos + length


def _parse_public_key(b64_der: str) -> tuple[int, int]:
    """Return (modulus, exponent) of an X.509 SubjectPublicKeyInfo RSA key."""
    der = base64.b64decode(b64_der)
    # SubjectPublicKeyInfo ::= SEQUENCE { AlgorithmIdentifier, BIT STRING }
    # and the BIT STRING holds RSAPublicKey ::= SEQUENCE { n, e }.
    def expect(tag: int, pos: int) -> tuple[int, int]:
        if der[pos] != tag:
            raise ValueError(f"Unexpected DER tag {der[pos]:#x} at {pos}, expected {tag:#x}")
        return _read_der_length(der, pos + 1)

    _, pos = expect(0x30, 0)
    algorithm_length, pos = expect(0x30, pos)
    _, pos = expect(0x03, pos + algorithm_length)
    pos += 1  # unused-bits byte of the BIT STRING
    _, pos = expect(0x30, pos)
    modulus, pos = _read_der_integer(der, pos)
    exponent, _ = _read_der_integer(der, pos)
    return modulus, exponent


def _mgf1_sha256(seed: bytes, length: int) -> bytes:
    output = b""
    counter = 0
    while len(output) < length:
        output += hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
        counter += 1
    return output[:length]


def decode_value(b64_value: str, public_key: str = constants.SECURITY_KEY_PUBLIC_KEY) -> str:
    """Decode one ``initialize_android.json`` value the way the app does
    (``RSA/ECB/OAEPWithSHA256AndMGF1Padding`` in decrypt mode with the
    public key)."""
    modulus, exponent = _parse_public_key(public_key)
    key_size = (modulus.bit_length() + 7) // 8
    cipher = int.from_bytes(base64.b64decode(b64_value), "big")
    encoded = pow(cipher, exponent, modulus).to_bytes(key_size, "big")
    hash_len = hashlib.sha256().digest_size
    if encoded[0] != 0:
        raise ValueError("Invalid OAEP block")
    masked_seed = encoded[1:1 + hash_len]
    masked_db = encoded[1 + hash_len:]
    seed = bytes(a ^ b for a, b in zip(masked_seed, _mgf1_sha256(masked_db, hash_len)))
    db = bytes(a ^ b for a, b in zip(masked_db, _mgf1_sha256(seed, len(masked_db))))
    if db[:hash_len] != hashlib.sha256(b"").digest():
        raise ValueError("Invalid OAEP label hash")
    rest = db[hash_len:].lstrip(b"\x00")
    if not rest or rest[0] != 1:
        raise ValueError("Invalid OAEP padding")
    return rest[1:].decode("utf-8")


def app_name_hash_to_salt(app_name_hash: str) -> str:
    """The app reverses the decoded ``appNameHash`` in three chunks
    (0-10, 10-20, 20-end) before hashing it."""
    return app_name_hash[:10][::-1] + app_name_hash[10:20][::-1] + app_name_hash[20:][::-1]


class CCSecurityKeyParams:
    """Process-wide cache of the salt and insert string of ``X-CFC-API-KEY``."""

    _salt: str = app_name_hash_to_salt(constants.DEFAULT_SECURITY_KEY_APP_NAME_HASH)
    _insert: str = constants.DEFAULT_SECURITY_KEY_INSERT_STRING
    _next_refresh: float = 0.0
    _lock: asyncio.Lock | None = None

    @classmethod
    def current(cls) -> tuple[str, str]:
        """The (salt, insert string) in use now, without fetching."""
        return cls._salt, cls._insert

    @classmethod
    async def get(cls, client: aiohttp.ClientSession | None) -> tuple[str, str]:
        """Return (salt, insert string), refreshing them first when due."""
        if client is None or time.monotonic() < cls._next_refresh:
            return cls.current()
        if cls._lock is None:
            cls._lock = asyncio.Lock()
        async with cls._lock:
            if time.monotonic() >= cls._next_refresh:
                await cls._refresh(client)
        return cls.current()

    @classmethod
    async def _refresh(cls, client: aiohttp.ClientSession):
        try:
            async with client.get(
                constants.SECURITY_KEY_INITIALIZE_URL,
                headers={"user-agent": "G-RAC"},
                timeout=_FETCH_TIMEOUT,
            ) as response:
                response.raise_for_status()
                data = await response.json(content_type=None)
            salt = app_name_hash_to_salt(decode_value(data["appNameHash"]))
            insert = decode_value(data["keyInsertString"])
            if len(salt) < 32 or not insert:
                raise ValueError(f"Unexpected security key parameters: salt length {len(salt)}, insert '{insert}'")
        except Exception as ex:
            _LOGGER.warning(
                "Failed to fetch the API key parameters, using the last known ones: %s", ex)
            cls._next_refresh = time.monotonic() + _RETRY_INTERVAL
            return
        if (salt, insert) != (cls._salt, cls._insert):
            _LOGGER.info("The API key parameters changed")
        cls._salt = salt
        cls._insert = insert
        cls._next_refresh = time.monotonic() + _REFRESH_INTERVAL
