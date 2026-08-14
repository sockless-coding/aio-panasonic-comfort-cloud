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
    """

    def __init__(self, json=None) -> None:
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

        self._has_changed = False
        self.load(json)

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
        self._has_changed = True
