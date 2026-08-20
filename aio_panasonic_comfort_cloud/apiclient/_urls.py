from urllib.parse import quote_plus, urlencode

from .. import constants


class UrlsMixin:
    """Builders for the Comfort Cloud API endpoint URLs used by ApiClient."""

    def _get_group_url(self):
        return '{base_url}/device/group'.format(
            base_url=constants.BASE_PATH_ACC
        )

    def _get_device_status_url(self, guid):
        return '{base_url}/deviceStatus/{guid}'.format(
            base_url=constants.BASE_PATH_ACC,
            guid=self._prepare_device_guid(guid)
        )

    def _get_device_status_now_url(self, guid):
        return '{base_url}/deviceStatus/now/{guid}'.format(
            base_url=constants.BASE_PATH_ACC,
            guid=self._prepare_device_guid(guid)
        )

    def _get_aquarea_device_info_url(self, guid):
        return '{base_url}/device/a2wInfo/{guid}'.format(
            base_url=constants.BASE_PATH_ACC,
            guid=self._prepare_device_guid(guid)
        )

    def _get_device_status_control_url(self):
        return '{base_url}/deviceStatus/control'.format(
            base_url=constants.BASE_PATH_ACC
        )

    def _get_device_history_url(self):
        return '{base_url}/deviceHistoryData'.format(
            base_url=constants.BASE_PATH_ACC,
        )

    def _get_aquarea_request_url(self):
        return '{base_url}/remote/v1/app/common/transfer'.format(
            base_url=constants.BASE_PATH_ACC
        )

    def _get_agreement_status_url(self, type_id: int):
        return '{base_url}/auth/agreement/status/{type_id}'.format(
            base_url=constants.BASE_PATH_ACC,
            type_id=type_id
        )

    def _get_agreement_accept_url(self):
        return '{base_url}/auth/agreement/status/'.format(
            base_url=constants.BASE_PATH_ACC
        )

    def _get_agreement_documents_url(self, type_id: int | None, language: int, include_content: bool):
        params = {"language": str(language)}
        if type_id is not None:
            params["type"] = str(type_id)
        params["includeContent"] = "1" if include_content else "0"
        return '{base_url}/auth/v2/agreement/documents?{query}'.format(
            base_url=constants.BASE_PATH_ACC,
            query=urlencode(params)
        )

    def _get_agreement_status_v2_url(self, type_id: int | None = None):
        if type_id is None:
            return '{base_url}/auth/v2/agreement/status'.format(
                base_url=constants.BASE_PATH_ACC
            )
        return '{base_url}/auth/v2/agreement/status?{query}'.format(
            base_url=constants.BASE_PATH_ACC,
            query=urlencode({"type": str(type_id)})
        )

    def _prepare_device_guid(self, device_guid: str):
        device_guid = device_guid.replace("/", "f")
        return quote_plus(device_guid, encoding='utf-8')
