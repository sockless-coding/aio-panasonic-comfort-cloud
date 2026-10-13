import logging

from .. import constants
from ..exceptions import DeviceIsNotReadyError

_LOGGER = logging.getLogger(__name__)


def read_enum(json, key, type, default_value):
    if not json or key not in json or json[key] is None:
        return default_value
    try:
        return type(json[key])
    except Exception as ex:
        _LOGGER.warning("Error reading HWS property '%s' with value '%s'", key, json[key], exc_info=ex)
    return default_value


def read_value(json, key, default_value):
    if not json:
        return default_value
    value = json.get(key, default_value)
    return default_value if value is None else value


def _without_none(values: dict) -> dict:
    return {key: value for key, value in values.items() if value is not None}


class HwsTemperatureSettingLimits:
    """Allowed temperature ranges for the weekly schedule. Fixed per device."""

    def __init__(self, json=None) -> None:
        self._set1_end_temperature: int | None = None
        self._set2_start_temperature_min: int | None = None
        self._set2_start_temperature_max: int | None = None
        self._set2_end_temperature_min: int | None = None
        self._set2_end_temperature_max: int | None = None
        self._has_changed = False
        self.load(json)

    @property
    def has_changed(self):
        return self._has_changed

    @property
    def set1_end_temperature(self):
        return self._set1_end_temperature
    @set1_end_temperature.setter
    def set1_end_temperature(self, value):
        if self._set1_end_temperature == value:
            return
        self._set1_end_temperature = value
        self._has_changed = True

    @property
    def set2_start_temperature_min(self):
        return self._set2_start_temperature_min
    @set2_start_temperature_min.setter
    def set2_start_temperature_min(self, value):
        if self._set2_start_temperature_min == value:
            return
        self._set2_start_temperature_min = value
        self._has_changed = True

    @property
    def set2_start_temperature_max(self):
        return self._set2_start_temperature_max
    @set2_start_temperature_max.setter
    def set2_start_temperature_max(self, value):
        if self._set2_start_temperature_max == value:
            return
        self._set2_start_temperature_max = value
        self._has_changed = True

    @property
    def set2_end_temperature_min(self):
        return self._set2_end_temperature_min
    @set2_end_temperature_min.setter
    def set2_end_temperature_min(self, value):
        if self._set2_end_temperature_min == value:
            return
        self._set2_end_temperature_min = value
        self._has_changed = True

    @property
    def set2_end_temperature_max(self):
        return self._set2_end_temperature_max
    @set2_end_temperature_max.setter
    def set2_end_temperature_max(self, value):
        if self._set2_end_temperature_max == value:
            return
        self._set2_end_temperature_max = value
        self._has_changed = True

    def load(self, json) -> bool:
        if not json:
            return False
        self._has_changed = False
        self.set1_end_temperature = read_value(json, 'set1EndTemperature', self.set1_end_temperature)
        self.set2_start_temperature_min = read_value(json, 'set2StartTemperatureMin', self.set2_start_temperature_min)
        self.set2_start_temperature_max = read_value(json, 'set2StartTemperatureMax', self.set2_start_temperature_max)
        self.set2_end_temperature_min = read_value(json, 'set2EndTemperatureMin', self.set2_end_temperature_min)
        self.set2_end_temperature_max = read_value(json, 'set2EndTemperatureMax', self.set2_end_temperature_max)
        has_changed = self._has_changed
        self._has_changed = False
        return has_changed


class HwsDeviceParameters:
    """Fixed capabilities of a standalone Heat Pump Hot Water tank unit
    (deviceType "11", e.g. HE-UM40CR), from the top level of the
    ``/hphw/deviceStatus`` response. These can't be changed by the user.
    """

    def __init__(self, json=None) -> None:
        self._permission: int | None = None
        self._weekly_mode: bool | None = None
        self._pv_mode: bool | None = None
        self._holiday_mode: bool | None = None
        self._limits: HwsTemperatureSettingLimits | None = None
        self._has_changed = False
        self.load(json)

    @property
    def has_changed(self):
        return self._has_changed

    @property
    def limits(self) -> HwsTemperatureSettingLimits:
        if self._limits is None:
            raise DeviceIsNotReadyError
        return self._limits

    @property
    def permission(self):
        return self._permission
    @permission.setter
    def permission(self, value):
        if self._permission == value:
            return
        self._permission = value
        self._has_changed = True

    @property
    def weekly_mode(self):
        return self._weekly_mode
    @weekly_mode.setter
    def weekly_mode(self, value):
        if self._weekly_mode == value:
            return
        self._weekly_mode = value
        self._has_changed = True

    @property
    def pv_mode(self):
        return self._pv_mode
    @pv_mode.setter
    def pv_mode(self, value):
        if self._pv_mode == value:
            return
        self._pv_mode = value
        self._has_changed = True

    @property
    def holiday_mode(self):
        return self._holiday_mode
    @holiday_mode.setter
    def holiday_mode(self, value):
        if self._holiday_mode == value:
            return
        self._holiday_mode = value
        self._has_changed = True

    def load(self, json) -> bool:
        if not json:
            return False
        self._has_changed = False
        self.permission = read_value(json, 'permission', self.permission)
        self.weekly_mode = read_value(json, 'weeklyMode', self.weekly_mode)
        self.pv_mode = read_value(json, 'pvMode', self.pv_mode)
        self.holiday_mode = read_value(json, 'holidayMode', self.holiday_mode)

        limits_json = json.get('temperatureSettingLimits')
        if limits_json:
            if not self._limits:
                self._limits = HwsTemperatureSettingLimits(limits_json)
                self._has_changed = True
            elif self._limits.load(limits_json):
                self._has_changed = True

        has_changed = self._has_changed
        self._has_changed = False
        return has_changed


class HwsInhibitTimeSettings:
    """Hours in which heating is blocked when the day runs in continuous mode."""

    def __init__(self, json=None) -> None:
        self._inhibit_time_available: int | None = None
        self._start_time: int | None = None
        self._end_time: int | None = None
        self._has_changed = False
        self.load(json)

    @property
    def has_changed(self):
        return self._has_changed

    @property
    def inhibit_time_available(self):
        return self._inhibit_time_available
    @inhibit_time_available.setter
    def inhibit_time_available(self, value):
        if self._inhibit_time_available == value:
            return
        self._inhibit_time_available = value
        self._has_changed = True

    @property
    def start_time(self):
        return self._start_time
    @start_time.setter
    def start_time(self, value):
        if self._start_time == value:
            return
        self._start_time = value
        self._has_changed = True

    @property
    def end_time(self):
        return self._end_time
    @end_time.setter
    def end_time(self, value):
        if self._end_time == value:
            return
        self._end_time = value
        self._has_changed = True

    def load(self, json) -> bool:
        if not json:
            return False
        self._has_changed = False
        self.inhibit_time_available = read_value(json, 'inhibitTimeAvailable', self.inhibit_time_available)
        self.start_time = read_value(json, 'startTime', self.start_time)
        self.end_time = read_value(json, 'endTime', self.end_time)
        has_changed = self._has_changed
        self._has_changed = False
        return has_changed

    def to_dict(self) -> dict:
        return _without_none({
            'inhibitTimeAvailable': self.inhibit_time_available,
            'startTime': self.start_time,
            'endTime': self.end_time,
        })


class HwsSet1Settings:
    """First heating window of the day when the day runs in timer mode."""

    def __init__(self, json=None) -> None:
        self._start_time: int | None = None
        self._end_time: int | None = None
        self._has_changed = False
        self.load(json)

    @property
    def has_changed(self):
        return self._has_changed

    @property
    def start_time(self):
        return self._start_time
    @start_time.setter
    def start_time(self, value):
        if self._start_time == value:
            return
        self._start_time = value
        self._has_changed = True

    @property
    def end_time(self):
        return self._end_time
    @end_time.setter
    def end_time(self, value):
        if self._end_time == value:
            return
        self._end_time = value
        self._has_changed = True

    def load(self, json) -> bool:
        if not json:
            return False
        self._has_changed = False
        self.start_time = read_value(json, 'startTime', self.start_time)
        self.end_time = read_value(json, 'endTime', self.end_time)
        has_changed = self._has_changed
        self._has_changed = False
        return has_changed

    def to_dict(self) -> dict:
        return _without_none({
            'startTime': self.start_time,
            'endTime': self.end_time,
        })


class HwsSet2Settings:
    """Optional second heating window of the day when the day runs in timer
    mode, with its own start/end temperatures."""

    def __init__(self, json=None) -> None:
        self._set2_available: int | None = None
        self._start_time: int | None = None
        self._end_time: int | None = None
        self._start_temperature: int | None = None
        self._end_temperature: int | None = None
        self._has_changed = False
        self.load(json)

    @property
    def has_changed(self):
        return self._has_changed

    @property
    def set2_available(self):
        return self._set2_available
    @set2_available.setter
    def set2_available(self, value):
        if self._set2_available == value:
            return
        self._set2_available = value
        self._has_changed = True

    @property
    def start_time(self):
        return self._start_time
    @start_time.setter
    def start_time(self, value):
        if self._start_time == value:
            return
        self._start_time = value
        self._has_changed = True

    @property
    def end_time(self):
        return self._end_time
    @end_time.setter
    def end_time(self, value):
        if self._end_time == value:
            return
        self._end_time = value
        self._has_changed = True

    @property
    def start_temperature(self):
        return self._start_temperature
    @start_temperature.setter
    def start_temperature(self, value):
        if self._start_temperature == value:
            return
        self._start_temperature = value
        self._has_changed = True

    @property
    def end_temperature(self):
        return self._end_temperature
    @end_temperature.setter
    def end_temperature(self, value):
        if self._end_temperature == value:
            return
        self._end_temperature = value
        self._has_changed = True

    def load(self, json) -> bool:
        if not json:
            return False
        self._has_changed = False
        self.set2_available = read_value(json, 'set2Available', self.set2_available)
        self.start_time = read_value(json, 'startTime', self.start_time)
        self.end_time = read_value(json, 'endTime', self.end_time)
        self.start_temperature = read_value(json, 'startTemperature', self.start_temperature)
        self.end_temperature = read_value(json, 'endTemperature', self.end_temperature)
        has_changed = self._has_changed
        self._has_changed = False
        return has_changed

    def to_dict(self) -> dict:
        return _without_none({
            'set2Available': self.set2_available,
            'startTime': self.start_time,
            'endTime': self.end_time,
            'startTemperature': self.start_temperature,
            'endTemperature': self.end_temperature,
        })


class HwsDailySettings:
    """One day of the HWS weekly schedule, as read from
    ``/hphw/deviceStatus`` and written back with
    :meth:`HwsMixin.async_set_hws_weekly_settings`."""

    def __init__(self, json=None) -> None:
        self._weekday: constants.HwsWeekday | None = None
        self._mode: constants.HwsDailyMode | None = None
        self._inhibit_time: HwsInhibitTimeSettings | None = None
        self._set1: HwsSet1Settings | None = None
        self._set2: HwsSet2Settings | None = None
        self._has_changed = False
        self.load(json)

    @property
    def has_changed(self):
        return self._has_changed

    @property
    def weekday(self):
        return self._weekday
    @weekday.setter
    def weekday(self, value):
        if self._weekday == value:
            return
        self._weekday = value
        self._has_changed = True

    @property
    def mode(self):
        return self._mode
    @mode.setter
    def mode(self, value):
        if self._mode == value:
            return
        self._mode = value
        self._has_changed = True

    @property
    def inhibit_time(self):
        return self._inhibit_time

    @property
    def set1(self):
        return self._set1

    @property
    def set2(self):
        return self._set2

    def _load_child(self, current, child_json, child_type):
        """Create, refresh or clear one nested settings object, flagging a
        change when it appears, disappears or its values change."""
        if not child_json:
            if current is not None:
                self._has_changed = True
            return None
        if current is None:
            self._has_changed = True
            return child_type(child_json)
        if current.load(child_json):
            self._has_changed = True
        return current

    def load(self, json) -> bool:
        if not json:
            return False
        self._has_changed = False
        self.weekday = read_enum(json, 'weekday', constants.HwsWeekday, self.weekday)
        self.mode = read_enum(json, 'mode', constants.HwsDailyMode, self.mode)
        self._inhibit_time = self._load_child(self._inhibit_time, json.get('inhibitTime'), HwsInhibitTimeSettings)
        self._set1 = self._load_child(self._set1, json.get('set1'), HwsSet1Settings)
        self._set2 = self._load_child(self._set2, json.get('set2'), HwsSet2Settings)
        has_changed = self._has_changed
        self._has_changed = False
        return has_changed

    def to_dict(self) -> dict:
        """Serialize for ``/hphw/deviceStatus/control``. Unknown values are
        left out rather than sent as null."""
        return _without_none({
            'weekday': self.weekday.value if self.weekday is not None else None,
            'mode': self.mode.value if self.mode is not None else None,
            'inhibitTime': self.inhibit_time.to_dict() if self.inhibit_time else None,
            'set1': self.set1.to_dict() if self.set1 else None,
            'set2': self.set2.to_dict() if self.set2 else None,
        })


class HwsParameters:
    """Current state of an HWS device, from the ``parameters`` object of the
    ``/hphw/deviceStatus`` response."""

    def __init__(self, json=None) -> None:
        self._hpu_operation_status = constants.HwsOperationStatus.Off
        self._operation_mode = constants.HwsOperationMode.Schedule
        self._boost_mode = constants.HwsBoostMode.Off
        self._tank_temperature: float | None = None
        self._outdoor_temperature: float | None = None
        self._weekly_settings: list[HwsDailySettings] | None = None
        self._has_changed = False
        self.load(json)

    @property
    def has_changed(self):
        return self._has_changed

    @property
    def hpu_operation_status(self):
        return self._hpu_operation_status
    @hpu_operation_status.setter
    def hpu_operation_status(self, value):
        if self._hpu_operation_status == value:
            return
        self._hpu_operation_status = value
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
    def boost_mode(self):
        return self._boost_mode
    @boost_mode.setter
    def boost_mode(self, value):
        if self._boost_mode == value:
            return
        self._boost_mode = value
        self._has_changed = True

    @property
    def tank_temperature(self):
        return self._tank_temperature
    @tank_temperature.setter
    def tank_temperature(self, value):
        if self._tank_temperature == value:
            return
        self._tank_temperature = value
        self._has_changed = True

    @property
    def outdoor_temperature(self):
        return self._outdoor_temperature
    @outdoor_temperature.setter
    def outdoor_temperature(self, value):
        if self._outdoor_temperature == value:
            return
        self._outdoor_temperature = value
        self._has_changed = True

    @property
    def weekly_settings(self) -> list[HwsDailySettings] | None:
        return self._weekly_settings

    def _load_weekly_settings(self, json):
        weekly_json = json.get('weeklySettingInfo')
        if not weekly_json:
            return
        if not isinstance(weekly_json, list):
            _LOGGER.warning("Unexpected HWS weeklySettingInfo value '%s'", weekly_json)
            return
        if self._weekly_settings is None or len(self._weekly_settings) != len(weekly_json):
            self._weekly_settings = [HwsDailySettings(day_json) for day_json in weekly_json]
            self._has_changed = True
            return
        for day_settings, day_json in zip(self._weekly_settings, weekly_json):
            if day_settings.load(day_json):
                self._has_changed = True

    def load(self, json) -> bool:
        if not json:
            return False
        self._has_changed = False
        self.hpu_operation_status = read_enum(json, 'hpuOperationStatus', constants.HwsOperationStatus, self.hpu_operation_status)
        self.operation_mode = read_enum(json, 'operationMode', constants.HwsOperationMode, self.operation_mode)
        self.boost_mode = read_enum(json, 'boostMode', constants.HwsBoostMode, self.boost_mode)
        self.tank_temperature = read_value(json, 'tankTemperature', self.tank_temperature)
        self.outdoor_temperature = read_value(json, 'outdoorTemperature', self.outdoor_temperature)
        self._load_weekly_settings(json)
        has_changed = self._has_changed
        self._has_changed = False
        return has_changed


class HwsConsumption:
    """One day of HWS energy consumption/cost history, as returned by the
    ``/hphw/deviceHistoryData`` endpoint."""

    def __init__(self, json=None) -> None:
        self._tank_consumption: float | None = None
        self._tank_cost: float | None = None
        self._data_time: str | None = None
        self._outdoor_temp: float | None = None
        self._tank_temp: float | None = None
        self.load(json)

    @property
    def tank_consumption(self):
        return self._tank_consumption

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
    def tank_temp(self):
        return self._tank_temp

    @property
    def total_consumption(self):
        return self._tank_consumption

    def load(self, json) -> bool:
        if not json:
            return False
        self._tank_consumption = read_value(json, 'consumption', self._tank_consumption)
        self._tank_cost = read_value(json, 'cost', self._tank_cost)
        self._data_time = read_value(json, 'dataTime', self._data_time)
        self._tank_temp = read_value(json, 'tankTemperature', self._tank_temp)
        self._outdoor_temp = read_value(json, 'outdoorTemperature', self._outdoor_temp)
        return True

    def copy(self, other: 'HwsConsumption') -> bool:
        if not other:
            return False
        self._tank_consumption = other._tank_consumption
        self._tank_cost = other._tank_cost
        self._data_time = other._data_time
        self._tank_temp = other._tank_temp
        self._outdoor_temp = other._outdoor_temp
        return True
