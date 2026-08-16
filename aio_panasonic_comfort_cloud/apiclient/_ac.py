import logging
from typing import TYPE_CHECKING

from .. import constants
from ..panasonicdevice import PanasonicDevice, PanasonicDeviceInfo
from ._timezone import get_current_time_zone

if TYPE_CHECKING:
    from ..changerequestbuilder import ChangeRequestBuilder
    from ._protocol import ApiClientCore
else:
    ApiClientCore = object

_LOGGER = logging.getLogger(__name__)


class AirConditionerMixin(ApiClientCore):
    """Status/history/control for regular air conditioner devices."""

    async def history(self, device_id, mode, date, time_zone=""):
        device_guid = self._device_indexer.get(device_id)
        if not device_guid:
            return None
        if not time_zone:
            time_zone = get_current_time_zone()
        if isinstance(mode, str):
            try:
                data_mode = constants.DataMode[mode].value
            except KeyError:
                raise Exception("Wrong mode parameter")
        elif isinstance(mode, constants.DataMode):
            data_mode = mode.value
        else:
            raise Exception("Wrong mode parameter")

        payload = {
            "deviceGuid": device_guid,
            "dataMode": data_mode,
            "date": date,
            "osTimezone": time_zone
        }

        json_response = await self.execute_post(self._get_device_history_url(), payload, "history", 200)

        return {
            'id': device_id,
            'parameters': self._read_parameters(json_response)
        }

    async def _get_device_status(self, device_info: PanasonicDeviceInfo):
        if (device_info.status_data_mode == constants.StatusDataMode.LIVE
            or (device_info.id in self._cache_devices and self._cache_devices[device_info.id] <= 0)):
            try:
                json_response = await self.execute_get(self._get_device_status_url(device_info.guid), "get_status", 200)
                device_info.status_data_mode = constants.StatusDataMode.LIVE
                return json_response
            except Exception as e:
                _LOGGER.warning("Failed to get live status for device {} switching to cached data.".format(device_info.guid))
                device_info.status_data_mode = constants.StatusDataMode.CACHED
                self._cache_devices[device_info.id] = 10
        json_response = await self.execute_get(self._get_device_status_now_url(device_info.guid), "get_status", 200)
        self._cache_devices[device_info.id] -= 1
        return json_response

    async def get_device(self, device_info: PanasonicDeviceInfo) -> PanasonicDevice:
        json_response = await self._get_device_status(device_info)
        return PanasonicDevice(device_info, json_response)

    async def try_update_device(self, device: PanasonicDevice) -> bool:
        json_response = await self._get_device_status(device.info)
        return device.load(json_response)

    async def set_horizontal_swing(self, device: PanasonicDevice, new_value: str | constants.AirSwingLR):
        """ Set horizontal swing"""
        if isinstance(new_value, str):
            new_value = constants.AirSwingLR[new_value]
        fan_auto = (constants.AirSwingAutoMode.AirSwingLR
                    if new_value == constants.AirSwingLR.Auto
                    else constants.AirSwingAutoMode.Disabled)
        if device.parameters.vertical_swing_mode == constants.AirSwingUD.Auto:
            fan_auto = (constants.AirSwingAutoMode.Both
                        if new_value == constants.AirSwingLR.Auto
                        else constants.AirSwingAutoMode.AirSwingUD)

        parameters = {
            "airSwingLR": new_value.value,
            "fanAutoMode": fan_auto.value
        }
        if self._auto_power_on:
            parameters["operate"] = constants.Power.On.value
        await self.set_device_raw(device, parameters)

    async def set_vertical_swing(self, device: PanasonicDevice, new_value: str | constants.AirSwingUD):
        """ Set vertical swing"""
        if isinstance(new_value, str):
            new_value = constants.AirSwingUD[new_value]
        fan_auto = (constants.AirSwingAutoMode.AirSwingUD
                    if new_value == constants.AirSwingUD.Auto
                    else constants.AirSwingAutoMode.Disabled)
        if device.parameters.horizontal_swing_mode == constants.AirSwingLR.Auto:
            fan_auto = (constants.AirSwingAutoMode.Both
                        if new_value == constants.AirSwingUD.Auto
                        else constants.AirSwingAutoMode.AirSwingLR)

        parameters = {
            "airSwingUD": new_value.value,
            "fanAutoMode": fan_auto.value
        }
        if self._auto_power_on:
            parameters["operate"] = constants.Power.On.value
        await self.set_device_raw(device, parameters)

    async def set_nanoe_mode(self, device: PanasonicDevice, new_value: str | constants.NanoeMode):
        """ Set Nanoe mode"""
        if isinstance(new_value, str):
            new_value = constants.NanoeMode[new_value]
        await self.set_device_raw(
            device,
            {
                "nanoe": new_value.value
            })

    async def set_eco_navi_mode(self, device: PanasonicDevice, new_value: str | constants.EcoNaviMode):
        """ Set EcoNavi mode"""
        if isinstance(new_value, str):
            new_value = constants.EcoNaviMode[new_value]
        await self.set_device_raw(
            device,
            {
                "ecoNavi": new_value.value
            })

    async def set_eco_function_mode(self, device: PanasonicDevice, new_value: str | constants.EcoFunctionMode):
        """ Set EcoFunction mode"""
        if isinstance(new_value, str):
            new_value = constants.EcoFunctionMode[new_value]
        await self.set_device_raw(
            device,
            {
                "ecoFunctionData": new_value.value
            })

    async def set_inside_cleaning(self, device: PanasonicDevice, new_value: str | constants.InsideCleaningMode):
        """Set inside cleaning mode"""
        if isinstance(new_value, str):
            new_value = constants.InsideCleaningMode[new_value]
        await self.set_device_raw(
            device,
            {
                "insideCleaning": new_value.value
            })

    async def set_device_raw(self, device: PanasonicDevice, parameters):
        """ Set parameters of device

        If ``auto_power_on`` is disabled on the client and the device is currently off,
        the change is buffered instead of being sent, unless it explicitly powers the
        device on (in which case any previously buffered changes for this device are
        merged in and applied together).
        """
        device_guid = device.info.guid
        turning_on = parameters.get("operate") == constants.Power.On.value

        if turning_on:
            parameters = self._pop_pending_change(device_guid, parameters)
        elif not self._auto_power_on and device.parameters.power != constants.Power.On:
            self._buffer_pending_change(device_guid, parameters)
            return

        payload = {
            "deviceGuid": device_guid,
            "parameters": parameters
        }
        await self.execute_post(self._get_device_status_control_url(), payload, "set_device", 200)

    def _buffer_pending_change(self, device_guid: str | None, parameters: dict) -> None:
        pending = self._pending_changes.setdefault(device_guid or "", {})
        pending.update(parameters)
        _LOGGER.debug("Device %s is off, buffering change: %s", device_guid, parameters)

    def _pop_pending_change(self, device_guid: str | None, parameters: dict) -> dict:
        pending = self._pending_changes.pop(device_guid or "", None)
        if not pending:
            return parameters
        return {**pending, **parameters}

    def has_pending_changes(self, device: PanasonicDevice) -> bool:
        """ True if there are buffered changes waiting for this device to be powered on """
        return (device.info.guid or "") in self._pending_changes

    def new_change_request(self, device: PanasonicDevice) -> "ChangeRequestBuilder":
        """ Create a ChangeRequestBuilder wired to this client's auto_power_on setting """
        from ..changerequestbuilder import ChangeRequestBuilder
        return ChangeRequestBuilder(device, auto_power_on=self._auto_power_on)

    async def set_device(self, device_info: PanasonicDeviceInfo, **kwargs):
        """ Set parameters of device

        Args:
            device_id  (str): Id of the device
            kwargs   : {temperature=float}, {mode=OperationMode}, {fanSpeed=FanSpeed}, {power=Power},
                       {airSwingHorizontal=}, {airSwingVertical=}, {eco=EcoMode}
        """

        parameters = {}
        air_x = None
        air_y = None

        if kwargs is not None:
            for key, value in kwargs.items():
                if key == 'power' and isinstance(value, constants.Power):
                    parameters['operate'] = value.value

                if key == 'temperature':
                    parameters['temperatureSet'] = value

                if key == 'mode' and isinstance(value, constants.OperationMode):
                    parameters['operationMode'] = value.value

                if key == 'fanSpeed' and isinstance(value, constants.FanSpeed):
                    parameters['fanSpeed'] = value.value

                if key == 'airSwingHorizontal' and isinstance(value, constants.AirSwingLR):
                    air_x = value

                if key == 'airSwingVertical' and isinstance(value, constants.AirSwingUD):
                    air_y = value

                if key == 'eco' and isinstance(value, constants.EcoMode):
                    parameters['ecoMode'] = value.value

                if key == 'nanoe' and \
                        isinstance(value, constants.NanoeMode) and \
                        value != constants.NanoeMode.Unavailable:
                    parameters['nanoe'] = value.value

                if key == 'ecoNavi' and isinstance(value, constants.EcoNaviMode):
                    parameters['ecoNavi'] = value.value

                if key == 'ecoFunctionData' and isinstance(value, constants.EcoFunctionMode):
                    parameters['ecoFunctionData'] = value.value

                if key == 'zoneParameters' and value is not None:
                    parameters['zoneParameters'] = value

        # routine to set the auto mode of fan (either horizontal, vertical, both or disabled)
        if air_x is not None or air_y is not None:
            fan_auto = 0
            device = await self.get_device(device_info)

            if device and device.parameters.horizontal_swing_mode == constants.AirSwingLR.Auto:
                fan_auto = fan_auto | 1

            if device and device.parameters.vertical_swing_mode == constants.AirSwingUD.Auto:
                fan_auto = fan_auto | 2

            if air_x is not None:
                if air_x.value == -1:
                    fan_auto = fan_auto | 1
                else:
                    fan_auto = fan_auto & ~1
                    parameters['airSwingLR'] = air_x.value

            if air_y is not None:
                if air_y.value == -1:
                    fan_auto = fan_auto | 2
                else:
                    fan_auto = fan_auto & ~2
                    parameters['airSwingUD'] = air_y.value

            if fan_auto == 3:
                parameters['fanAutoMode'] = constants.AirSwingAutoMode.Both.value
            elif fan_auto == 1:
                parameters['fanAutoMode'] = constants.AirSwingAutoMode.AirSwingLR.value
            elif fan_auto == 2:
                parameters['fanAutoMode'] = constants.AirSwingAutoMode.AirSwingUD.value
            else:
                parameters['fanAutoMode'] = constants.AirSwingAutoMode.Disabled.value

        device_guid = device_info.guid
        if device_guid:
            if parameters.get("operate") == constants.Power.On.value:
                parameters = self._pop_pending_change(device_guid, parameters)
            payload = {
                "deviceGuid": device_guid,
                "parameters": parameters
            }
            _ = await self.execute_post(self._get_device_status_control_url(), payload, "set_device", 200)
            return True
        return False

    def _read_parameters(self, parameters=dict()):
        value = dict()

        _convert = {
            'insideTemperature': 'temperatureInside',
            'outTemperature': 'temperatureOutside',
            'temperatureSet': 'temperature',
            'currencyUnit': 'currencyUnit',
            'energyConsumption': 'energyConsumption',
            'estimatedCost': 'estimatedCost',
            'historyDataList': 'historyDataList',
        }
        for key in _convert:
            if key in parameters:
                value[_convert[key]] = parameters[key]

        if 'operate' in parameters:
            value['power'] = constants.Power(parameters['operate'])

        if 'operationMode' in parameters:
            value['mode'] = constants.OperationMode(
                parameters['operationMode'])

        if 'fanSpeed' in parameters:
            value['fanSpeed'] = constants.FanSpeed(parameters['fanSpeed'])

        if 'airSwingLR' in parameters:
            value['airSwingHorizontal'] = constants.AirSwingLR(
                parameters['airSwingLR'])

        if 'airSwingUD' in parameters:
            value['airSwingVertical'] = constants.AirSwingUD(
                parameters['airSwingUD'])

        if 'ecoMode' in parameters:
            value['eco'] = constants.EcoMode(parameters['ecoMode'])

        if 'nanoe' in parameters:
            value['nanoe'] = constants.NanoeMode(parameters['nanoe'])

        if 'fanAutoMode' in parameters:
            if parameters['fanAutoMode'] == constants.AirSwingAutoMode.Both.value:
                value['airSwingHorizontal'] = constants.AirSwingLR.Auto
                value['airSwingVertical'] = constants.AirSwingUD.Auto
            elif parameters['fanAutoMode'] == constants.AirSwingAutoMode.AirSwingLR.value:
                value['airSwingHorizontal'] = constants.AirSwingLR.Auto
            elif parameters['fanAutoMode'] == constants.AirSwingAutoMode.AirSwingUD.value:
                value['airSwingVertical'] = constants.AirSwingUD.Auto

        return value
