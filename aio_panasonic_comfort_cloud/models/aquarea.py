import logging

from .. import constants

_LOGGER = logging.getLogger(__name__)


def read_enum(json, key, type, default_value):
    if not json or key not in json or json[key] is None:
        return default_value
    try:
        return type(json[key])
    except Exception as ex:
        _LOGGER.warning("Error reading Aquarea property '%s' with value '%s'", key, json[key], exc_info=ex)
    return default_value


def read_value(json, key, default_value):
    if not json:
        return default_value
    value = json.get(key, default_value)
    return default_value if value is None else value


class AquareaZoneStatus:
    """Status of a single Aquarea heating/cooling zone."""

    def __init__(self, json=None) -> None:
        self._id: int | None = None
        self._name: str = ""
        self._operation_status = constants.AquareaOperationStatus.Off
        self._temperature: int | None = None
        self._heat_min: int | None = None
        self._heat_max: int | None = None
        self._heat_set: int | None = None
        self._cool_min: int | None = None
        self._cool_max: int | None = None
        self._cool_set: int | None = None
        self._eco_heat: int | None = None
        self._eco_cool: int | None = None
        self._comfort_heat: int | None = None
        self._comfort_cool: int | None = None
        self._has_changed = False
        self.load(json)

    @property
    def has_changed(self):
        return self._has_changed

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def operation_status(self):
        return self._operation_status

    @property
    def temperature(self):
        return self._temperature

    @property
    def heat_min(self):
        return self._heat_min

    @property
    def heat_max(self):
        return self._heat_max

    @property
    def heat_set(self):
        return self._heat_set

    @property
    def cool_min(self):
        return self._cool_min

    @property
    def cool_max(self):
        return self._cool_max

    @property
    def cool_set(self):
        return self._cool_set

    @property
    def supports_cooling(self):
        return self._cool_min is not None and self._cool_max is not None

    @property
    def eco_heat(self):
        return self._eco_heat

    @property
    def eco_cool(self):
        return self._eco_cool

    @property
    def comfort_heat(self):
        return self._comfort_heat

    @property
    def comfort_cool(self):
        return self._comfort_cool

    def load(self, json) -> bool:
        if not json:
            return False
        self._has_changed = False
        if 'zoneId' in json:
            self._id = json['zoneId']
        self._name = read_value(json, 'zoneName', self._name)
        self._operation_status = read_enum(json, 'operationStatus', constants.AquareaOperationStatus, self._operation_status)
        self._temperature = read_value(json, 'temperatureNow', self._temperature)
        self._heat_min = read_value(json, 'heatMin', self._heat_min)
        self._heat_max = read_value(json, 'heatMax', self._heat_max)
        self._heat_set = read_value(json, 'heatSet', self._heat_set)
        self._cool_min = read_value(json, 'coolMin', self._cool_min)
        self._cool_max = read_value(json, 'coolMax', self._cool_max)
        self._cool_set = read_value(json, 'coolSet', self._cool_set)
        self._eco_heat = read_value(json, 'ecoHeat', self._eco_heat)
        self._eco_cool = read_value(json, 'ecoCool', self._eco_cool)
        self._comfort_heat = read_value(json, 'comfortHeat', self._comfort_heat)
        self._comfort_cool = read_value(json, 'comfortCool', self._comfort_cool)
        self._has_changed = True
        return self._has_changed


class AquareaTankStatus:
    """Status of the Aquarea hot water tank."""

    def __init__(self, json=None) -> None:
        self._operation_status = constants.AquareaOperationStatus.Off
        self._temperature: int | None = None
        self._heat_min: int | None = None
        self._heat_max: int | None = None
        self._heat_set: int | None = None
        self._has_changed = False
        self.load(json)

    @property
    def has_changed(self):
        return self._has_changed

    @property
    def operation_status(self):
        return self._operation_status

    @property
    def temperature(self):
        return self._temperature

    @property
    def heat_min(self):
        return self._heat_min

    @property
    def heat_max(self):
        return self._heat_max

    @property
    def heat_set(self):
        return self._heat_set

    def load(self, json) -> bool:
        if not json:
            return False
        self._has_changed = False
        self._operation_status = read_enum(json, 'operationStatus', constants.AquareaOperationStatus, self._operation_status)
        self._temperature = read_value(json, 'temperatureNow', self._temperature)
        self._heat_min = read_value(json, 'heatMin', self._heat_min)
        self._heat_max = read_value(json, 'heatMax', self._heat_max)
        self._heat_set = read_value(json, 'heatSet', self._heat_set)
        self._has_changed = True
        return self._has_changed


class AquareaDeviceParameters:
    """Live status of an Aquarea (Air to Water) device, as returned by the
    ``remote/v1/app/common/transfer`` proxy for ``/remote/v1/api/devices``.

    Standalone DHW units (``is_dhw``; ``/remote/v1/api/devices/dhw`` and
    ``/devices/ecoflex``) report their tank at the top level of ``status``
    (``operationStatus``, ``temperatureNow``, ``temperatureSet``) instead of in
    ``tankStatus``, and use :class:`constants.AquareaDhwOperationMode` for
    ``operationMode``. For them :attr:`tank` is built from those top-level
    values, :attr:`dhw_operation_mode` holds the mode and
    :attr:`operation_mode` is left at its default.
    """

    def __init__(self, json=None, is_dhw: bool = False) -> None:
        self._is_dhw = is_dhw
        self._operation_status = constants.AquareaOperationStatus.Off
        self._operation_mode = constants.AquareaOperationMode.Off
        self._device_mode_status = constants.AquareaDeviceModeStatus.Normal
        self._temperature_outdoor: int | None = None
        self._direction = constants.AquareaDeviceDirection.Idle
        self._pump_duty = constants.AquareaPumpDuty.Off
        self._quiet_mode = constants.AquareaQuietMode.Off
        self._force_dhw = constants.AquareaForceDHW.Off
        self._force_heater = constants.AquareaForceHeater.Off
        self._holiday_timer = constants.AquareaHolidayTimer.Off
        self._powerful_time = constants.AquareaPowerfulTime.Off
        self._special_status: constants.AquareaSpecialStatus | None = None
        self._cool_mode: int = 0
        self._has_tank: bool = False
        self._water_pressure: int | None = None
        self._bivalent: int | None = None
        self._bivalent_actual: int | None = None
        self._multi_od_connection: int | None = None
        self._control_box: int | None = None
        self._external_heater: int | None = None
        self._model_series_selection: int | None = None
        self._stand_alone: int | None = None
        self._uncontrollable_taw1_flag: bool = False
        self._service_type: str | None = None
        self._fault_status: list = []
        self._tank: AquareaTankStatus | None = None
        self._zones: list[AquareaZoneStatus] = []
        self._zone_index: dict[int, AquareaZoneStatus] = {}

        # Top-level temperatures. Standalone DHW units use these for their
        # tank; the *MinTemp/*MaxTemp pairs (new in app 5.x) are the allowed
        # setpoint range per DHW operation mode.
        self._dhw_operation_mode: constants.AquareaDhwOperationMode | None = None
        self._temperature_now: int | None = None
        self._temperature_set: int | None = None
        self._min_temperature: int | None = None
        self._max_temperature: int | None = None
        self._heat_min_temp: int | None = None
        self._heat_max_temp: int | None = None
        self._heater_min_temp: int | None = None
        self._heater_max_temp: int | None = None
        self._auto_min_temp: int | None = None
        self._auto_max_temp: int | None = None

        self._has_changed = False
        self.load(json)

    @property
    def is_dhw(self) -> bool:
        """True when this is the status of a standalone DHW unit."""
        return self._is_dhw

    @property
    def dhw_operation_mode(self) -> "constants.AquareaDhwOperationMode | None":
        """Operation mode of a standalone DHW unit; None for heat pumps."""
        return self._dhw_operation_mode

    @property
    def temperature_now(self) -> int | None:
        """Top-level ``temperatureNow`` (the tank temperature of a DHW unit)."""
        return self._temperature_now

    @property
    def temperature_set(self) -> int | None:
        """Top-level ``temperatureSet`` (the tank setpoint of a DHW unit)."""
        return self._temperature_set

    @property
    def min_temperature(self) -> int | None:
        return self._min_temperature

    @property
    def max_temperature(self) -> int | None:
        return self._max_temperature

    @property
    def heat_min_temp(self) -> int | None:
        """Lowest setpoint in DHW heat pump mode (``heatMinTemp``)."""
        return self._heat_min_temp

    @property
    def heat_max_temp(self) -> int | None:
        """Highest setpoint in DHW heat pump mode (``heatMaxTemp``)."""
        return self._heat_max_temp

    @property
    def heater_min_temp(self) -> int | None:
        """Lowest setpoint in DHW heater-only mode (``heaterMinTemp``)."""
        return self._heater_min_temp

    @property
    def heater_max_temp(self) -> int | None:
        """Highest setpoint in DHW heater-only mode (``heaterMaxTemp``)."""
        return self._heater_max_temp

    @property
    def auto_min_temp(self) -> int | None:
        """Lowest setpoint in DHW auto mode (``autoMinTemp``)."""
        return self._auto_min_temp

    @property
    def auto_max_temp(self) -> int | None:
        """Highest setpoint in DHW auto mode (``autoMaxTemp``)."""
        return self._auto_max_temp

    def dhw_temperature_range(
        self, mode: "constants.AquareaDhwOperationMode | None" = None
    ) -> tuple[int | None, int | None]:
        """(min, max) setpoint of a standalone DHW unit in `mode` (default:
        the current mode), picked the way app 5.x does it: heat pump uses
        ``heat*Temp``, heater-only ``heater*Temp``, auto ``auto*Temp``, and
        anything else ``min/maxTemperature``. Where a mode-specific value is
        missing, ``min/maxTemperature`` is used instead."""
        if mode is None:
            mode = self._dhw_operation_mode
        if mode == constants.AquareaDhwOperationMode.HeatPump:
            low, high = self._heat_min_temp, self._heat_max_temp
        elif mode == constants.AquareaDhwOperationMode.HeaterOnly:
            low, high = self._heater_min_temp, self._heater_max_temp
        elif mode == constants.AquareaDhwOperationMode.Auto:
            low, high = self._auto_min_temp, self._auto_max_temp
        else:
            low, high = None, None
        return (
            low if low is not None else self._min_temperature,
            high if high is not None else self._max_temperature,
        )

    @property
    def has_changed(self):
        return self._has_changed

    @property
    def operation_status(self):
        return self._operation_status
    @operation_status.setter
    def operation_status(self, value):
        if self._operation_status == value:
            return
        self._operation_status = value
        self._has_changed = True

    @property
    def operation_mode(self):
        return self._operation_mode
    @operation_mode.setter
    def operation_mode(self, value):
        if self._operation_mode == value:
            return
        self._operation_mode = value
        self._has_changed = True

    @property
    def device_mode_status(self):
        return self._device_mode_status

    @property
    def temperature_outdoor(self):
        return self._temperature_outdoor

    @property
    def direction(self):
        return self._direction

    @property
    def pump_duty(self):
        return self._pump_duty

    @property
    def quiet_mode(self):
        return self._quiet_mode
    @quiet_mode.setter
    def quiet_mode(self, value):
        if self._quiet_mode == value:
            return
        self._quiet_mode = value
        self._has_changed = True

    @property
    def force_dhw(self):
        return self._force_dhw
    @force_dhw.setter
    def force_dhw(self, value):
        if self._force_dhw == value:
            return
        self._force_dhw = value
        self._has_changed = True

    @property
    def force_heater(self):
        return self._force_heater
    @force_heater.setter
    def force_heater(self, value):
        if self._force_heater == value:
            return
        self._force_heater = value
        self._has_changed = True

    @property
    def holiday_timer(self):
        return self._holiday_timer
    @holiday_timer.setter
    def holiday_timer(self, value):
        if self._holiday_timer == value:
            return
        self._holiday_timer = value
        self._has_changed = True

    @property
    def powerful_time(self):
        return self._powerful_time
    @powerful_time.setter
    def powerful_time(self, value):
        if self._powerful_time == value:
            return
        self._powerful_time = value
        self._has_changed = True

    @property
    def special_status(self):
        return self._special_status

    @property
    def supports_cooling(self):
        return bool(self._cool_mode)

    @property
    def has_tank(self):
        return self._has_tank

    @property
    def tank(self):
        return self._tank

    @property
    def water_pressure(self):
        return self._water_pressure

    @property
    def bivalent(self):
        return self._bivalent

    @property
    def bivalent_actual(self):
        return self._bivalent_actual

    @property
    def multi_od_connection(self):
        return self._multi_od_connection

    @property
    def control_box(self):
        return self._control_box

    @property
    def external_heater(self):
        return self._external_heater

    @property
    def model_series_selection(self):
        return self._model_series_selection

    @property
    def stand_alone(self):
        return self._stand_alone

    @property
    def uncontrollable_taw1_flag(self):
        return self._uncontrollable_taw1_flag

    @property
    def service_type(self):
        return self._service_type

    @property
    def fault_status(self):
        return list(self._fault_status)

    @property
    def is_on_error(self):
        return len(self._fault_status) > 0

    @property
    def zones(self):
        return list(self._zones)

    def get_zone(self, zone_id: int):
        return self._zone_index.get(zone_id)

    def load(self, json) -> bool:
        if not json:
            return False
        self._has_changed = False

        self.operation_status = read_enum(json, 'operationStatus', constants.AquareaOperationStatus, self.operation_status)
        if self._is_dhw:
            dhw_operation_mode = read_enum(json, 'operationMode', constants.AquareaDhwOperationMode, self._dhw_operation_mode)
            if dhw_operation_mode != self._dhw_operation_mode:
                self._dhw_operation_mode = dhw_operation_mode
                self._has_changed = True
        else:
            self.operation_mode = read_enum(json, 'operationMode', constants.AquareaOperationMode, self.operation_mode)
        self._device_mode_status = read_enum(json, 'deiceStatus', constants.AquareaDeviceModeStatus, self._device_mode_status)
        self._temperature_outdoor = read_value(json, 'outdoorNow', self._temperature_outdoor)
        self._direction = read_enum(json, 'direction', constants.AquareaDeviceDirection, self._direction)
        self._pump_duty = read_enum(json, 'pumpDuty', constants.AquareaPumpDuty, self._pump_duty)
        self.quiet_mode = read_enum(json, 'quietMode', constants.AquareaQuietMode, self.quiet_mode)
        self.force_dhw = read_enum(json, 'forceDHW', constants.AquareaForceDHW, self.force_dhw)
        self.force_heater = read_enum(json, 'forceHeater', constants.AquareaForceHeater, self.force_heater)
        self.holiday_timer = read_enum(json, 'holidayTimer', constants.AquareaHolidayTimer, self.holiday_timer)
        self.powerful_time = read_enum(json, 'powerful', constants.AquareaPowerfulTime, self.powerful_time)

        special_status = json.get('specialStatus') if 'specialStatus' in json else None
        try:
            self._special_status = constants.AquareaSpecialStatus(special_status) if special_status else None
        except ValueError:
            self._special_status = None

        self._cool_mode = read_value(json, 'coolMode', self._cool_mode)
        self._water_pressure = read_value(json, 'waterPressure', self._water_pressure)
        self._bivalent = read_value(json, 'bivalent', self._bivalent)
        self._bivalent_actual = read_value(json, 'bivalentActual', self._bivalent_actual)
        self._multi_od_connection = read_value(json, 'multiOdConnection', self._multi_od_connection)
        self._control_box = read_value(json, 'controlBox', self._control_box)
        self._external_heater = read_value(json, 'externalHeater', self._external_heater)
        self._model_series_selection = read_value(json, 'modelSeriesSelection', self._model_series_selection)
        self._stand_alone = read_value(json, 'standAlone', self._stand_alone)
        self._uncontrollable_taw1_flag = read_value(json, 'uncontrollableTaw1Flg', self._uncontrollable_taw1_flag)
        self._service_type = read_value(json, 'serviceType', self._service_type)
        self._fault_status = read_value(json, 'faultStatus', [])

        self._temperature_now = read_value(json, 'temperatureNow', self._temperature_now)
        self._temperature_set = read_value(json, 'temperatureSet', self._temperature_set)
        self._min_temperature = read_value(json, 'minTemperature', self._min_temperature)
        self._max_temperature = read_value(json, 'maxTemperature', self._max_temperature)
        self._heat_min_temp = read_value(json, 'heatMinTemp', self._heat_min_temp)
        self._heat_max_temp = read_value(json, 'heatMaxTemp', self._heat_max_temp)
        self._heater_min_temp = read_value(json, 'heaterMinTemp', self._heater_min_temp)
        self._heater_max_temp = read_value(json, 'heaterMaxTemp', self._heater_max_temp)
        self._auto_min_temp = read_value(json, 'autoMinTemp', self._auto_min_temp)
        self._auto_max_temp = read_value(json, 'autoMaxTemp', self._auto_max_temp)

        if self._is_dhw and not json.get('tankStatus'):
            self._load_root_tank(json)
        else:
            self._load_tank(json)
        self._load_zones(json)

        has_changed = self._has_changed
        self._has_changed = False
        return has_changed

    def _load_tank(self, json):
        tank_json = json.get('tankStatus')
        if not tank_json:
            self._has_tank = False
            return
        self._has_tank = True
        if not self._tank:
            self._tank = AquareaTankStatus(tank_json)
        else:
            self._tank.load(tank_json)
        self._has_changed = True

    def _load_root_tank(self, json):
        """Build the tank of a standalone DHW unit from the top-level status."""
        heat_min, heat_max = self.dhw_temperature_range()
        tank_json = {
            'operationStatus': json.get('operationStatus'),
            'temperatureNow': self._temperature_now,
            'heatSet': self._temperature_set,
            'heatMin': heat_min,
            'heatMax': heat_max,
        }
        tank_json = {key: value for key, value in tank_json.items() if value is not None}
        if not tank_json:
            self._has_tank = False
            return
        self._has_tank = True
        if not self._tank:
            self._tank = AquareaTankStatus(tank_json)
        else:
            self._tank.load(tank_json)
        self._has_changed = True

    def _load_zones(self, json):
        if 'zoneStatus' not in json or json['zoneStatus'] is None:
            return
        self._zones.clear()
        self._zone_index.clear()
        for zone_json in json['zoneStatus']:
            if not zone_json or 'zoneId' not in zone_json:
                continue
            zone_id = zone_json['zoneId']
            zone = AquareaZoneStatus(zone_json)
            self._zone_index[zone_id] = zone
            self._zones.append(zone)


class AquareaConsumption:
    """One entry of Aquarea energy consumption/cost history, broken down by
    heat/cool/hot-water-tank, as returned by the ``/remote/v1/api/consumption``
    endpoint (see :meth:`ApiClient.async_get_aquarea_consumption`).
    """

    def __init__(self, json=None) -> None:
        self._heat_consumption: float | None = None
        self._cool_consumption: float | None = None
        self._tank_consumption: float | None = None
        self._heat_cost: float | None = None
        self._cool_cost: float | None = None
        self._tank_cost: float | None = None
        self._data_time: str | None = None
        self._outdoor_temp: float | None = None
        self.load(json)

    @property
    def heat_consumption(self):
        return self._heat_consumption

    @property
    def cool_consumption(self):
        return self._cool_consumption

    @property
    def tank_consumption(self):
        return self._tank_consumption

    @property
    def heat_cost(self):
        return self._heat_cost

    @property
    def cool_cost(self):
        return self._cool_cost

    @property
    def tank_cost(self):
        return self._tank_cost

    @property
    def data_time(self):
        return self._data_time

    @property
    def outdoor_temp(self):
        return self._outdoor_temp

    @property
    def total_consumption(self):
        values = [v for v in (self._heat_consumption, self._cool_consumption, self._tank_consumption) if v is not None]
        return sum(values) if values else None

    def load(self, json) -> bool:
        if not json:
            return False
        self._heat_consumption = read_value(json, 'heatConsumption', self._heat_consumption)
        self._cool_consumption = read_value(json, 'coolConsumption', self._cool_consumption)
        self._tank_consumption = read_value(json, 'tankConsumption', self._tank_consumption)
        self._heat_cost = read_value(json, 'heatCost', self._heat_cost)
        self._cool_cost = read_value(json, 'coolCost', self._cool_cost)
        self._tank_cost = read_value(json, 'tankCost', self._tank_cost)
        self._data_time = read_value(json, 'dataTime', self._data_time)
        self._outdoor_temp = read_value(json, 'outdoorTemp', self._outdoor_temp)
        return True
        self._has_changed = True
