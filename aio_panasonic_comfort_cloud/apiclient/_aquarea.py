import logging
from typing import TYPE_CHECKING

from .. import constants
from ..aquareadevice import AquareaDevice
from ..models.aquarea import AquareaConsumption
from ..panasonicdevice import PanasonicDeviceInfo
from ._timezone import get_current_time_zone

if TYPE_CHECKING:
    from ._protocol import ApiClientCore
else:
    ApiClientCore = object

_LOGGER = logging.getLogger(__name__)


class AquareaMixin(ApiClientCore):
    """Status/history/control for Aquarea heat pump devices."""

    async def get_aquarea_device(self, device_info: PanasonicDeviceInfo) -> AquareaDevice:
        json_response = await self._async_get_aquarea_status(device_info)
        return AquareaDevice(device_info, json_response)

    async def try_update_aquarea_device(self, device: AquareaDevice) -> bool:
        json_response = await self._async_get_aquarea_status(device.info)
        return device.load(json_response)

    async def _async_get_aquarea_status(self, device_info: PanasonicDeviceInfo):
        if (device_info.status_data_mode == constants.StatusDataMode.LIVE
            or (device_info.id in self._cache_devices and self._cache_devices[device_info.id] <= 0)):
            try:
                payload = {
                    "apiName": f"/remote/v1/api/devices?gwid={device_info.guid}&deviceDirect=1",
                    "requestMethod": "GET"
                }
                json_response = await self.execute_post(
                    self._get_aquarea_request_url(),
                    payload,
                    "get_aquarea_status",
                    200)
                device_info.status_data_mode = constants.StatusDataMode.LIVE
                return json_response
            except Exception as e:
                _LOGGER.warning("Failed to get live status for device {} switching to cached data.".format(device_info.guid))
                device_info.status_data_mode = constants.StatusDataMode.CACHED
                self._cache_devices[device_info.id] = 10
        payload = {
            "apiName": f"/remote/v1/api/devices?gwid={device_info.guid}&deviceDirect=0",
            "requestMethod": "GET"
        }
        json_response = await self.execute_post(
            self._get_aquarea_request_url(),
            payload,
            "get_aquarea_status",
            200)
        self._cache_devices[device_info.id] -= 1
        return json_response

    async def _async_set_aquarea(self, device_info: PanasonicDeviceInfo, body_param: dict):
        """ Send a partial update to an Aquarea device via the common/transfer proxy """
        payload = {
            "apiName": "/remote/v1/api/devices",
            "requestMethod": "POST",
            "bodyParam": {
                "gwid": device_info.guid,
                **body_param
            }
        }
        await self.execute_post(self._get_aquarea_request_url(), payload, "set_aquarea_device", 200)

    async def set_aquarea_operation_status(self, device_info: PanasonicDeviceInfo, new_value: str | constants.AquareaOperationStatus):
        """ Turn the whole Aquarea unit on/off """
        if isinstance(new_value, str):
            new_value = constants.AquareaOperationStatus[new_value]
        await self._async_set_aquarea(device_info, {"operationStatus": new_value.value})

    async def set_aquarea_operation_mode(self, device_info: PanasonicDeviceInfo, new_value: str | constants.AquareaUpdateOperationMode):
        """ Set the Aquarea operation mode (heat/cool/auto/off) """
        if isinstance(new_value, str):
            new_value = constants.AquareaUpdateOperationMode[new_value]
        await self._async_set_aquarea(device_info, {"operationMode": new_value.value})

    async def set_aquarea_quiet_mode(self, device_info: PanasonicDeviceInfo, new_value: str | constants.AquareaQuietMode):
        """ Set the Aquarea quiet mode level """
        if isinstance(new_value, str):
            new_value = constants.AquareaQuietMode[new_value]
        await self._async_set_aquarea(device_info, {"quietMode": new_value.value})

    async def set_aquarea_force_dhw(self, device_info: PanasonicDeviceInfo, new_value: str | constants.AquareaForceDHW):
        """ Force domestic hot water production on/off """
        if isinstance(new_value, str):
            new_value = constants.AquareaForceDHW[new_value]
        await self._async_set_aquarea(device_info, {"forceDHW": new_value.value})

    async def set_aquarea_force_heater(self, device_info: PanasonicDeviceInfo, new_value: str | constants.AquareaForceHeater):
        """ Force the backup heater on/off """
        if isinstance(new_value, str):
            new_value = constants.AquareaForceHeater[new_value]
        await self._async_set_aquarea(device_info, {"forceHeater": new_value.value})

    async def set_aquarea_holiday_timer(self, device_info: PanasonicDeviceInfo, new_value: str | constants.AquareaHolidayTimer):
        """ Enable/disable the holiday timer """
        if isinstance(new_value, str):
            new_value = constants.AquareaHolidayTimer[new_value]
        await self._async_set_aquarea(device_info, {"holidayTimer": new_value.value})

    async def set_aquarea_powerful_time(self, device_info: PanasonicDeviceInfo, new_value: str | constants.AquareaPowerfulTime):
        """ Enable powerful mode for the given duration """
        if isinstance(new_value, str):
            new_value = constants.AquareaPowerfulTime[new_value]
        await self._async_set_aquarea(device_info, {"powerful": new_value.value})

    async def request_aquarea_defrost(self, device_info: PanasonicDeviceInfo):
        """ Request an immediate defrost cycle """
        await self._async_set_aquarea(device_info, {"forcedefrost": 1})

    async def set_aquarea_tank_temperature(self, device_info: PanasonicDeviceInfo, temperature: int):
        """ Set the target temperature of the hot water tank """
        await self._async_set_aquarea(device_info, {"tankStatus": {"heatSet": temperature}})

    async def set_aquarea_tank_operation_status(self, device_info: PanasonicDeviceInfo, new_value: str | constants.AquareaOperationStatus):
        """ Turn the hot water tank on/off """
        if isinstance(new_value, str):
            new_value = constants.AquareaOperationStatus[new_value]
        await self._async_set_aquarea(device_info, {"tankStatus": {"operationStatus": new_value.value}})

    async def set_aquarea_zone_temperature(self, device_info: PanasonicDeviceInfo, zone_id: int, temperature: int, mode: str = "heat"):
        """ Set the target heat/cool temperature of a zone """
        key = "heatSet" if mode == "heat" else "coolSet"
        await self._async_set_aquarea(device_info, {"zoneStatus": [{"zoneId": zone_id, key: temperature}]})

    async def set_aquarea_zone_operation_status(self, device_info: PanasonicDeviceInfo, zone_id: int, new_value: str | constants.AquareaOperationStatus):
        """ Turn a specific zone on/off """
        if isinstance(new_value, str):
            new_value = constants.AquareaOperationStatus[new_value]
        await self._async_set_aquarea(device_info, {"zoneStatus": [{"zoneId": zone_id, "operationStatus": new_value.value}]})

    async def set_aquarea_operation_state(
        self,
        device: AquareaDevice,
        mode: "constants.AquareaUpdateOperationMode | None" = None,
        zone_id: int | None = None,
        zone_status: "constants.AquareaOperationStatus | None" = None,
        tank_status: "constants.AquareaOperationStatus | None" = None,
    ) -> None:
        """ Change the operation mode and/or a zone's/the tank's on-off status in one combined request.

        Aquarea's ``operationMode`` and whole-unit ``operationStatus`` are
        device-wide (a single compressor serves every zone plus the tank),
        while ``zoneStatus``/``tankStatus`` are effectively replaced rather
        than merged: a request that changes one of these without also
        resending the others' *current* values causes the omitted ones to
        reset (observed as the tank switching itself back on when a zone's
        mode changes, and as zones/tank that can never be turned off since
        the whole-unit ``operationStatus`` was never being sent). This
        mirrors the pre-8.x aioaquarea-based implementation's behavior,
        which always recomputed and resent the complete state on every
        change. Make sure `device` was refreshed recently (get_aquarea_device()/
        try_update_aquarea_device()) before calling this.

        Args:
            device: The Aquarea device, with recently refreshed parameters.
            mode: New operation mode (heat/cool/auto/off), or None to leave
                the current mode unchanged.
            zone_id: The zone to change, together with `zone_status`.
            zone_status: The new on/off status for `zone_id`. Every other
                zone keeps its current status.
            tank_status: The new on/off status for the tank, or None to
                leave it unchanged.
        """
        params = device.parameters

        resolved_zone_status = {zone.id: zone.operation_status for zone in params.zones}
        if zone_id is not None and zone_status is not None:
            resolved_zone_status[zone_id] = zone_status

        resolved_tank_status = (
            params.tank.operation_status if params.has_tank and params.tank else constants.AquareaOperationStatus.Off
        )
        if tank_status is not None:
            resolved_tank_status = tank_status

        any_on = resolved_tank_status == constants.AquareaOperationStatus.On or any(
            status == constants.AquareaOperationStatus.On for status in resolved_zone_status.values()
        )
        operation_status = constants.AquareaOperationStatus.On if any_on else constants.AquareaOperationStatus.Off

        body: dict = {
            "operationStatus": operation_status.value,
            "zoneStatus": [
                {"zoneId": zid, "operationStatus": status.value} for zid, status in resolved_zone_status.items()
            ],
            "tankStatus": {"operationStatus": resolved_tank_status.value},
        }
        if mode is not None:
            body["operationMode"] = mode.value

        await self._async_set_aquarea(device.info, body)

    @staticmethod
    def _clamp(value, min_value, max_value):
        if value is None:
            return None
        if min_value is not None and value < min_value:
            value = min_value
        if max_value is not None and value > max_value:
            value = max_value
        return value

    @staticmethod
    def _special_status_modifiers(zone, status: "constants.AquareaSpecialStatus"):
        if status == constants.AquareaSpecialStatus.Eco:
            return zone.eco_heat, zone.eco_cool
        return zone.comfort_heat, zone.comfort_cool

    def _calculate_zone_special_status_setpoints(self, zone, current_status, new_status):
        """ Undo `current_status`'s offset (if any) then apply `new_status`'s
        offset (if any) to the zone's heat/cool setpoints, clamped to the
        zone's min/max range — mirrors how the official app recalculates
        setpoints when switching Eco/Comfort special status. """
        heat_set = zone.heat_set
        cool_set = zone.cool_set
        if current_status is not None:
            heat_modifier, cool_modifier = self._special_status_modifiers(zone, current_status)
            if heat_set is not None and heat_modifier is not None:
                heat_set = self._clamp(heat_set - heat_modifier, zone.heat_min, zone.heat_max)
            if cool_set is not None and cool_modifier is not None:
                cool_set = self._clamp(cool_set - cool_modifier, zone.cool_min, zone.cool_max)
        if new_status is not None:
            heat_modifier, cool_modifier = self._special_status_modifiers(zone, new_status)
            if heat_set is not None and heat_modifier is not None:
                heat_set = self._clamp(heat_set + heat_modifier, zone.heat_min, zone.heat_max)
            if cool_set is not None and cool_modifier is not None:
                cool_set = self._clamp(cool_set + cool_modifier, zone.cool_min, zone.cool_max)
        return heat_set, cool_set

    async def set_aquarea_special_status(self, device: AquareaDevice, new_value: str | constants.AquareaSpecialStatus | None):
        """ Enable/disable Eco or Comfort special status.

        Eco/Comfort aren't just a flag — Aquarea applies a per-zone
        temperature offset (``zone.eco_heat``/``eco_cool`` or
        ``zone.comfort_heat``/``comfort_cool``) on top of each zone's
        current heat/cool setpoint, and reverts it when switched off or
        away. This recalculates each zone's adjusted setpoint from
        `device`'s currently loaded parameters and sends it together with
        the new specialStatus in one call, mirroring the app's behavior —
        which is why this takes the full AquareaDevice (not just its
        PanasonicDeviceInfo, like the other set_aquarea_* methods): it needs
        the current setpoints/status to compute the offset. Make sure
        `device` was refreshed recently (get_aquarea_device()/
        try_update_aquarea_device()) before calling this.

        Unverified / best-effort: the aioaquarea reference implementation
        posts this via a different, legacy cookie-based endpoint instead of
        the common/transfer proxy used for everything else in this client.
        This method instead follows the same transfer-proxy pattern as the
        other set_aquarea_* methods for consistency with what we've
        confirmed works — please report back if it doesn't.
        """
        if isinstance(new_value, str):
            new_value = constants.AquareaSpecialStatus[new_value]
        current_status = device.parameters.special_status

        zone_updates = []
        for zone in device.parameters.zones:
            heat_set, cool_set = self._calculate_zone_special_status_setpoints(zone, current_status, new_value)
            zone_update = {"zoneId": zone.id}
            if heat_set is not None:
                zone_update["heatSet"] = heat_set
            if cool_set is not None:
                zone_update["coolSet"] = cool_set
            zone_updates.append(zone_update)

        body: dict = {"specialStatus": new_value.value if new_value else 0}
        if zone_updates:
            body["zoneStatus"] = zone_updates
        await self._async_set_aquarea(device.info, body)

    async def async_get_aquarea_consumption(self, device_info: PanasonicDeviceInfo, data_mode: str | constants.AquareaDataMode, date: str) -> list[AquareaConsumption]:
        """ Get Aquarea energy consumption/cost history, broken down by heat/cool/tank.

        Unlike air conditioners (which use deviceHistoryData), Aquarea has
        its own /remote/v1/api/consumption endpoint, reached through the
        same common/transfer proxy used for status/control.

        Args:
            device_info: The Aquarea device.
            data_mode: AquareaDataMode.Day/Month/Year (or the matching
                string name) — NOT the AC-only DataMode enum, which has
                different values and an extra "Week" granularity Aquarea
                doesn't have.
            date: Date string in the format the API expects (e.g.
                "YYYYMMDD"), matching what history()/DataMode use elsewhere
                in this client.

        Returns:
            A list of AquareaConsumption entries.
        """
        if isinstance(data_mode, str):
            data_mode = constants.AquareaDataMode[data_mode]
        payload = {
            "apiName": "/remote/v1/api/consumption",
            "requestMethod": "POST",
            "bodyParam": {
                "gwid": device_info.guid,
                "dataMode": data_mode.value,
                "date": date,
                "osTimezone": get_current_time_zone()
            }
        }
        json_response = await self.execute_post(self._get_aquarea_request_url(), payload, "get_aquarea_consumption", 200)
        history_items = json_response.get("historyDataList") or []
        return [AquareaConsumption(item) for item in history_items]
