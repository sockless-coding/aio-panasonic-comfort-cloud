import logging
from typing import TYPE_CHECKING

from ..exceptions import AgreementNotAcceptedError

if TYPE_CHECKING:
    from ._protocol import ApiClientCore
else:
    ApiClientCore = object

_LOGGER = logging.getLogger(__name__)


class AgreementsMixin(ApiClientCore):
    """Agreement / terms acceptance.

    The app (v4.4.0) exclusively uses the "v2" agreement API below; the v1
    endpoints (`check_agreement_status`/`accept_agreement`, hitting
    `/auth/agreement/status/{type}`) do not appear anywhere in the current
    app and are kept only for backward compatibility — prefer the v2
    methods (`get_agreement_documents`/`get_agreement_status`/
    `accept_agreements`/`ensure_all_agreements_accepted`).
    """

    AGREEMENT_TYPE_TERMS = 1           # Terms & Conditions
    AGREEMENT_TYPE_PRIVACY = 2         # Privacy Policy
    AGREEMENT_TYPE_SERVICE = 3         # Service Agreement (Turkey only)
    AGREEMENT_TYPE_COOKIE_POLICY = 4   # Cookie Policy

    async def check_agreement_status(self, type_id: int):
        """[Legacy v1] Check if an agreement of the given type has been accepted.

        Args:
            type_id: 1 = Terms & Conditions, 2 = Privacy Policy, 3 = Service Agreement

        Returns:
            The agreement status (1 = accepted, any other value = not accepted).
        """
        result = await self.execute_get(
            self._get_agreement_status_url(type_id),
            "check_agreement_status",
            200
        )
        return result.get("agreementStatus")

    async def accept_agreement(self, type_id: int):
        """[Legacy v1] Accept an agreement by sending a PUT request.

        Args:
            type_id: 1 = Terms & Conditions, 2 = Privacy Policy, 3 = Service Agreement
        """
        payload = {
            "agreementStatus": 1,
            "type": type_id
        }
        await self.execute_put(
            self._get_agreement_accept_url(),
            payload,
            "accept_agreement",
            200
        )

    async def get_agreement_documents(self, type_id: int | None = None, language: int = 0, include_content: bool = True):
        """Fetch the current agreement documents (terms, privacy policy, etc.).

        Args:
            type_id: Restrict to a single agreement type. Omit to fetch all
                (Terms, Privacy, Turkey Service Agreement, Cookie Policy).
            language: Language id understood by the API (0 = default/English).
            include_content: If True, the response includes the full document
                text in each entry's "content" field.

        Returns:
            A list of dicts like ``{"type": "1", "version": "...", "content": "..."}``.
            Note the API returns ``type`` as a string here (unlike
            :meth:`get_agreement_status`, where it's an int).
        """
        result = await self.execute_get(
            self._get_agreement_documents_url(type_id, language, include_content),
            "get_agreement_documents",
            200
        )
        return result.get("agreementList", [])

    async def get_agreement_status(self, type_id: int | None = None):
        """Get the agreement type/version pairs already accepted on this account.

        Args:
            type_id: Restrict to a single agreement type. Omit to fetch all.

        Returns:
            A list of dicts like ``{"type": 1, "version": "..."}``. A type
            missing from the list has never been accepted on this account.
        """
        result = await self.execute_get(
            self._get_agreement_status_v2_url(type_id),
            "get_agreement_status",
            200
        )
        return result.get("agreementList", [])

    async def accept_agreements(self, agreements: list[dict]):
        """Accept one or more agreements.

        Args:
            agreements: A list of ``{"type": int, "version": str}`` — the
                version should be the latest one reported by
                :meth:`get_agreement_documents` for that type.
        """
        payload = {"agreementList": agreements}
        await self.execute_put(
            self._get_agreement_status_v2_url(),
            payload,
            "accept_agreements",
            200
        )

    async def ensure_all_agreements_accepted(self, language: int = 0):
        """Fetch the latest agreement documents and accept anything outdated or missing.

        Auto-accepts Terms & Conditions, Privacy Policy and Cookie Policy.
        The Turkey Service Agreement is intentionally left out — like the
        official app, it only applies to a subset of accounts and should be
        a deliberate, user-driven choice rather than an automatic one.

        Raises:
            AgreementNotAcceptedError: If the outdated/missing agreements
                could not be accepted.
        """
        auto_accept_types = {
            self.AGREEMENT_TYPE_TERMS,
            self.AGREEMENT_TYPE_PRIVACY,
            self.AGREEMENT_TYPE_COOKIE_POLICY,
        }

        documents = await self.get_agreement_documents(language=language, include_content=False)
        accepted = await self.get_agreement_status()
        accepted_versions = {item.get("type"): item.get("version") for item in accepted}

        to_accept = []
        for document in documents:
            try:
                doc_type = int(document.get("type"))
            except (TypeError, ValueError):
                continue
            if doc_type not in auto_accept_types:
                continue
            latest_version = document.get("version")
            if latest_version is None or accepted_versions.get(doc_type) == latest_version:
                continue
            to_accept.append({"type": doc_type, "version": latest_version})

        if not to_accept:
            return

        _LOGGER.info("Accepting updated agreements: %s", to_accept)
        try:
            await self.accept_agreements(to_accept)
        except Exception as ex:
            _LOGGER.warning("Failed to auto-accept agreements %s", to_accept, exc_info=ex)
            raise AgreementNotAcceptedError([item["type"] for item in to_accept]) from ex
