from datetime import datetime
from typing import TYPE_CHECKING

from .. import constants
from ..panasonicdevice import PanasonicDeviceEnergy, PanasonicDeviceInfo
from ._timezone import get_current_time_zone

if TYPE_CHECKING:
    from ._protocol import ApiClientCore
else:
    ApiClientCore = object


class EnergyMixin(ApiClientCore):
    """Today's air conditioner energy consumption, derived from deviceHistoryData."""

    async def async_get_energy(self, device_info: PanasonicDeviceInfo) -> PanasonicDeviceEnergy | None:
        todays_item = await self._async_get_todays_energy(device_info)
        if todays_item is None:
            return None
        return PanasonicDeviceEnergy(device_info, todays_item)

    async def async_try_update_energy(self, energy: PanasonicDeviceEnergy) -> bool:
        todays_item = await self._async_get_todays_energy(energy.info)
        return energy.load(todays_item)

    async def _async_get_todays_energy(self, device_info: PanasonicDeviceInfo):
        today = datetime.now().strftime("%Y%m%d")
        device_guid = device_info.guid
        if not device_guid:
            return None

        payload = {
            "deviceGuid": device_guid,
            "dataMode": constants.DataMode.Month.value,
            "date": today,
            "osTimezone": get_current_time_zone()
        }

        history = await self.execute_post(self._get_device_history_url(), payload, "get_todays_energy", 200)

        if history is None:
            return None
        if 'historyDataList' not in history:
            return None
        history_items = history['historyDataList']
        todays_item = None
        for item in history_items:
            if 'dataTime' not in item:
                continue
            if item['dataTime'] != today:
                continue
            todays_item = item
            break
        return todays_item
