from datetime import datetime
from typing import TYPE_CHECKING

from .. import constants
from ..hwsdevice import HwsDevice
from ..models.hws import HwsConsumption, HwsDailySettings
from ..panasonicdevice import PanasonicDeviceInfo
from ._timezone import get_current_time_zone

if TYPE_CHECKING:
    from ._protocol import ApiClientCore
else:
    ApiClientCore = object


class HwsMixin(ApiClientCore):
    """Status/control for standalone Heat Pump Hot Water Tank (HWS) devices.

    HWS devices (deviceType "11") have their own ``/hphw/...`` endpoints; the
    AC ``deviceStatus``/``deviceHistoryData`` calls 403 for this device class.
    """

    async def _async_get_hws_status(self, device_info: PanasonicDeviceInfo):
        # No cached-status fallback like AC/Aquarea: no cached variant of the
        # HWS status endpoint has been confirmed yet.
        return await self.execute_get(self._get_hws_device_status_url(device_info.guid), "get_hws_status", 200)

    async def get_hws_device(self, device_info: PanasonicDeviceInfo) -> HwsDevice:
        """Fetch the current status of a standalone Heat Pump Hot Water tank."""
        json_response = await self._async_get_hws_status(device_info)
        return HwsDevice(device_info, json_response)

    async def try_update_hws_device(self, device: HwsDevice) -> bool:
        """Refresh an :class:`HwsDevice`. Returns True if anything changed."""
        json_response = await self._async_get_hws_status(device.info)
        return device.load(json_response)

    async def _async_set_hws(self, device_info: PanasonicDeviceInfo, body: dict):
        """Send a partial update to an HWS device through
        ``/hphw/deviceStatus/control``. ``body`` holds only the changed keys
        of the device's ``parameters`` object."""
        payload = {"deviceGuid": device_info.guid, "parameters": body}
        await self.execute_post(self._get_hws_device_status_control_url(), payload, "set_hws_device", 200)

    async def set_hws_boost_mode(self, device_info: PanasonicDeviceInfo, new_value: str | constants.HwsBoostMode):
        """ Turn boost mode on/off """
        if isinstance(new_value, str):
            new_value = constants.HwsBoostMode[new_value]
        await self._async_set_hws(device_info, {"boostMode": new_value.value})

    async def set_hws_operation_mode(self, device_info: PanasonicDeviceInfo, new_value: str | int | constants.HwsOperationMode):
        """ Set the operation mode (Schedule, PVTimer or Holiday) """
        if isinstance(new_value, str):
            new_value = constants.HwsOperationMode[new_value]
        elif isinstance(new_value, int):
            new_value = constants.HwsOperationMode(new_value)
        await self._async_set_hws(device_info, {"operationMode": new_value.value})

    async def set_hws_holiday_mode(self, device_info: PanasonicDeviceInfo):
        """ Switch to Holiday mode """
        await self.set_hws_operation_mode(device_info, constants.HwsOperationMode.Holiday)

    async def set_hws_schedule_mode(self, device_info: PanasonicDeviceInfo):
        """ Switch to Schedule mode (the default) """
        await self.set_hws_operation_mode(device_info, constants.HwsOperationMode.Schedule)

    async def async_set_hws_weekly_settings(self, device_info: PanasonicDeviceInfo, weekly_settings: list[HwsDailySettings]):
        """Replace the weekly schedule of an HWS device. Pass the full list as
        read from :attr:`HwsParameters.weekly_settings`, edited as needed."""
        days = []
        for day in weekly_settings:
            if day.weekday is None or day.mode is None:
                raise ValueError("Every HWS daily setting needs a weekday and a mode")
            days.append(day.to_dict())
        await self._async_set_hws(device_info, {"weeklySettingInfo": days})

    async def async_get_hws_consumption(self, device_info: PanasonicDeviceInfo) -> HwsConsumption | None:
        """Today's energy consumption, or None if there's no entry for today yet."""
        return await self._async_get_todays_hws_consumption(device_info)

    async def async_try_update_hws_consumption(self, device_info: PanasonicDeviceInfo, energy: HwsConsumption) -> bool:
        todays_item = await self._async_get_todays_hws_consumption(device_info)
        if not todays_item:
            return False
        return energy.copy(todays_item)

    async def _async_get_todays_hws_consumption(self, device_info: PanasonicDeviceInfo) -> HwsConsumption | None:
        device_guid = device_info.guid
        if not device_guid:
            return None
        today = datetime.now().strftime("%Y%m%d")

        payload = {
            "deviceGuid": device_guid,
            "dataMode": constants.HwsDataMode.Month.value,
            "date": today,
            "osTimezone": get_current_time_zone()
        }

        history = await self.execute_post(self._get_hws_device_history_url(), payload, "get_todays_hws_energy", 200)

        if not history or "historyDataList" not in history:
            return None
        for item in history["historyDataList"]:
            if item.get("dataTime") == today:
                return HwsConsumption(item)
        return None
