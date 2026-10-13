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

    The app (v4.4.0) exclusively uses the "v2" agreement API below. The v1
    endpoints (`check_agreement_status`/`accept_agreement`, hitting
    `/auth/agreement/status/{type}`) are no longer served — the gateway
    answers 403 "Missing Authentication Token", i.e. no such route. They're
    kept only so existing callers fail loudly; use the v2 methods
    (`get_pending_agreements`/`get_agreement_documents`/`get_agreement_status`/
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

    async def get_pending_agreements(self, language: int = 0, include_content: bool = False):
        """Get the agreement documents this account still needs to accept.

        Compares the latest documents against the account's accepted
        versions. The Turkey Service Agreement (type 3) is always left out:
        the documents endpoint lists it for every account, but like the
        official app we only accept the generally applicable agreements —
        submitting it for an account it doesn't apply to has been seen to
        get the whole acceptance request rejected with HTTP 400.

        Args:
            language: Language id understood by the API (0 = default/English).
            include_content: If True, each entry includes the document text
                in its "content" field.

        Returns:
            A list of document dicts (as returned by
            :meth:`get_agreement_documents`, but with ``type`` as an int).
            Pass ``{"type": d["type"], "version": d["version"]}`` for each
            entry to :meth:`accept_agreements` to accept them.
        """
        acceptable_types = {
            self.AGREEMENT_TYPE_TERMS,
            self.AGREEMENT_TYPE_PRIVACY,
            self.AGREEMENT_TYPE_COOKIE_POLICY,
        }

        documents = await self.get_agreement_documents(language=language, include_content=include_content)
        accepted = await self.get_agreement_status()
        accepted_versions = {item.get("type"): item.get("version") for item in accepted}

        pending = []
        for document in documents:
            try:
                doc_type = int(document.get("type"))
            except (TypeError, ValueError):
                continue
            if doc_type not in acceptable_types:
                continue
            latest_version = document.get("version")
            if latest_version is None or accepted_versions.get(doc_type) == latest_version:
                continue
            pending.append({**document, "type": doc_type})
        return pending

    async def ensure_all_agreements_accepted(self, language: int = 0):
        """Fetch the latest agreement documents and accept anything outdated or missing.

        Auto-accepts Terms & Conditions, Privacy Policy and Cookie Policy
        (see :meth:`get_pending_agreements`).

        Raises:
            AgreementNotAcceptedError: If the outdated/missing agreements
                could not be accepted.
        """
        pending = await self.get_pending_agreements(language=language)
        to_accept = [{"type": doc["type"], "version": doc["version"]} for doc in pending]

        if not to_accept:
            return

        _LOGGER.info("Accepting updated agreements: %s", to_accept)
        try:
            await self.accept_agreements(to_accept)
        except Exception as ex:
            _LOGGER.warning("Failed to auto-accept agreements %s", to_accept, exc_info=ex)
            raise AgreementNotAcceptedError([item["type"] for item in to_accept]) from ex
