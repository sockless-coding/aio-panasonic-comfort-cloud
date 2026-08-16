'''
Panasonic session, using Panasonic Comfort Cloud app api
'''

import logging

import aiohttp

from .. import panasonicsession
from ..exceptions import AgreementNotAcceptedError
from ..panasonicdevice import PanasonicDeviceInfo
from ._agreements import AgreementsMixin
from ._ac import AirConditionerMixin
from ._aquarea import AquareaMixin
from ._devices import DeviceDiscoveryMixin
from ._energy import EnergyMixin
from ._hws import HwsMixin
from ._timezone import get_current_time_zone
from ._urls import UrlsMixin

__all__ = ["ApiClient", "get_current_time_zone"]

_LOGGER = logging.getLogger(__name__)


class ApiClient(
        panasonicsession.PanasonicSession,
        UrlsMixin,
        AgreementsMixin,
        DeviceDiscoveryMixin,
        AirConditionerMixin,
        AquareaMixin,
        HwsMixin,
        EnergyMixin):
    """Asynchronous client for the Panasonic Comfort Cloud API.

    Can be used as an async context manager to automatically start and stop sessions:

        async with ApiClient(email, password, session) as client:
            devices = client.get_devices()
    """

    def __init__(self,
                 username,
                 password,
                 client: aiohttp.ClientSession,
                 token_file_name='~/.panasonic-settings',
                 raw=False):
        super().__init__(username, password, client, token_file_name, raw)

        self._groups = None
        self._devices: list[PanasonicDeviceInfo] | None = None
        self._aquarea_devices: list[PanasonicDeviceInfo] = []
        self._hws_devices: list[PanasonicDeviceInfo] = []
        self._unknown_devices: list[PanasonicDeviceInfo] = []
        self._cache_devices = {}

        self._device_indexer = {}
        self._raw = raw
        self._acc_client_id = None

    async def __aenter__(self):
        await self.start_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            await self.stop_session()
        except Exception:
            _LOGGER.debug("Error during session cleanup", exc_info=True)
        return False

    @property
    def unknown_devices(self):
        return self._unknown_devices

    @property
    def has_unknown_devices(self):
        return len(self._unknown_devices) > 0

    @property
    def aquarea_devices(self):
        self.get_devices()
        return self._aquarea_devices

    @property
    def has_aquarea_devices(self):
        return len(self.aquarea_devices) > 0

    @property
    def hws_devices(self):
        self.get_devices()
        return self._hws_devices

    @property
    def has_hws_devices(self):
        return len(self.hws_devices) > 0

    async def start_session(self, otp_code: str | None = None):
        await super().start_session(otp_code)
        try:
            await self._get_groups()
        except AgreementNotAcceptedError:
            # Re-authenticating won't help if terms/policies need acceptance, so re-raise
            raise
        except Exception as ex:
            _LOGGER.warning("Could not get groups, trying to re-authenticate", exc_info=ex)
            await self.reauthenticate(otp_code)
            await self._get_groups()

    async def reauthenticate(self, otp_code: str | None = None):
        await super().reauthenticate(otp_code)
        await self._get_groups()

    def get_browser_authorization_url(self) -> tuple[str, str]:
        """Alternative to :meth:`start_session`: build a URL to authenticate in
        a real browser instead of this library's own credential-scraping
        login flow. Does not touch or affect start_session()/authenticate().

        Returns:
            A ``(authorization_url, code_verifier)`` tuple — see
            :meth:`PanasonicAuthentication.build_authorization_url` for how
            to use them.
        """
        return self.authentication.build_authorization_url()

    async def complete_browser_authentication(self, redirect_url_or_code: str, code_verifier: str):
        """Finish authentication started via :meth:`get_browser_authorization_url`.

        Args:
            redirect_url_or_code: The redirect URL the browser landed on (or
                just the bare ``code`` value extracted from it).
            code_verifier: The value returned by :meth:`get_browser_authorization_url`.
        """
        await self.authentication.complete_browser_authentication(redirect_url_or_code, code_verifier)
        await self._get_groups()

    async def refresh_token(self):
        await super().start_session()
