import json
import logging
from typing import TYPE_CHECKING

from ..exceptions import AgreementNotAcceptedError, ResponseError
from ..panasonicdevice import PanasonicDeviceInfo

if TYPE_CHECKING:
    from ._protocol import ApiClientCore
else:
    ApiClientCore = object

_LOGGER = logging.getLogger(__name__)


class DeviceDiscoveryMixin(ApiClientCore):
    """Fetching/caching the `/device/group` listing and sorting devices by kind."""

    async def _get_groups(self):
        try:
            self._groups = await self.execute_get(
                self._get_group_url(),
                "get_groups",
                200
            )
        except ResponseError as ex:
            # Error code 4103 means terms/policies have been updated and need acceptance
            if "4103" in str(ex):
                _LOGGER.warning(
                    "Terms and/or policies have been updated (error 4103), agreement acceptance required"
                )
                raise AgreementNotAcceptedError() from ex
            raise
        self._devices = None

    def get_devices(self):
        if self._devices is None:
            self._devices = []
            self._aquarea_devices = []
            self._hws_devices = []
            self._unknown_devices = []
            if self._groups is not None and 'groupList' in self._groups:
                for group in self._groups['groupList']:
                    if 'deviceList' in group:
                        device_list = group.get('deviceList', [])
                    else:
                        device_list = group.get('deviceIdList', [])

                    for device in device_list:
                        if device:
                            device_info = PanasonicDeviceInfo(device)
                            if device_info.is_valid:
                                self._device_indexer[device_info.id] = device_info.guid
                                self._devices.append(device_info)
                            elif device_info.is_aquarea:
                                self._device_indexer[device_info.id] = device_info.guid
                                self._aquarea_devices.append(device_info)
                            elif device_info.is_hws:
                                self._device_indexer[device_info.id] = device_info.guid
                                self._hws_devices.append(device_info)
                            else:
                                self._unknown_devices.append(device_info)

        return self._devices

    def dump(self, device_id):
        device_guid = self._device_indexer.get(device_id)
        if device_guid:
            return self.execute_get(self._get_device_status_url(device_guid), "dump", 200)
        return None

    async def check_aquarea(self):
        if self.has_unknown_devices:

            _LOGGER.warning(f"""Found {len(self.unknown_devices)} unknown device(s):
{"\n ".join(json.dumps(obj.raw) for obj in self.unknown_devices)}
Submit this log to https://github.com/sockless-coding/panasonic_cc/issues/310
""")
            for device in self.unknown_devices:
                try:
                    aqua_device = await self.get_aquarea_device(device)
                    _LOGGER.warning(f"""Got aquarea device info for: {device.guid}:
{json.dumps(aqua_device.info.raw)}
Submit this log to https://github.com/sockless-coding/panasonic_cc/issues/310""")
                except Exception as e:
                    _LOGGER.warning(f"""Failed to get aquarea device info for {device.guid}
Submit this log to https://github.com/sockless-coding/panasonic_cc/issues/310""", exc_info=e)

    def _find_raw_device(self, guid: str | None):
        if self._groups is None or 'groupList' not in self._groups:
            return None
        for group in self._groups['groupList']:
            device_list = group.get('deviceList') or group.get('deviceIdList', [])
            for device in device_list:
                if device and device.get('deviceGuid') == guid:
                    return device
        return None
