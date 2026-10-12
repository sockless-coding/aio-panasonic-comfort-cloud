import logging
import json

from .. import constants
from ..exceptions import DeviceIsNotReadyError
#

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


class HwsTemperatureSettingLimits:
    """Temperature set limits for the HWS tank.  These are fixed values for the 
    device and are returned by the /hphw/deviceStatus endpoint.
    """

    def __init__(self, json=None) -> None:
        self._set1_end_temperature: int | None = None
        self._set2_start_temperature_min: int | None = None       
        self._set2_start_temperature_max: int | None = None 
        self._set2_end_temperature_min: int | None = None       
        self._set2_end_temperature_max: int | None = None                                    
        self.load(json)

    @property
    def has_changed(self):
        return self._has_changed

    @property
    def set1_end_temperature(self):
        return  self._set1_end_temperature
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
        self.set1_end_temperature = read_value(json, 'set1EndTemperature', self._set1_end_temperature)
        self.set2_start_temperature_min = read_value(json, 'set2StartTemperatureMin', self._set2_start_temperature_min)
        self.set2_start_temperature_max = read_value(json, 'set2StartTemperatureMax', self._set2_start_temperature_max)
        self.set2_end_temperature_min = read_value(json, 'set2EndTemperatureMin', self._set2_end_temperature_min)
        self.set2_end_temperature_max = read_value(json, 'set2EndTemperatureMax', self._set2_end_temperature_max)
        has_changed = self._has_changed
        self._has_changed = False
        return has_changed

class HwsParameters:
    """Global parameters for the HWS tank. These are returned by the /hphw/deviceStatus endpoint."""

    def __init__(self, json=None) -> None:
        self._hpu_operation_status = constants.HwsOperationStatus.Off
        self._operation_mode = constants.HwsBoostModeSettings.Off
        self._boost_mode = constants.HwsBoostModeSettings.Off
        self._tank_temperature: float | None = None
        self._outdoor_temperature: float | None = None
        self._weeklySettings: list[HwsDailySettings] | None = None
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


    def _load_weekly_settings(self, json):
        weeklySettings_json = json.get("weeklySettingInfo")
        if not weeklySettings_json:
            self._has_weeklySettings = False
            return
        try :
            if self._weeklySettings is None:
                self._weeklySettings = []
                for day_settings_json in weeklySettings_json:
                    self._weeklySettings.append(HwsDailySettings(day_settings_json))
            else:
                for index,day_settings in enumerate(self._weeklySettings):
                    day_settings.load(weeklySettings_json[index])
        except TypeError as e:
            self._has_weeklySettings = False
            self._weeklySettings=None
            return
        self._has_weeklySettings = True
        self._has_changed = True
        return

    
    @property
    def weeklySettings(self):
        return  self._weeklySettings
    
    def load(self, json) -> bool:
        if not json:
            return False
        self._has_changed = False
        self.hpu_operation_status = read_enum(json, 'hpuOperationStatus', constants.HwsOperationStatus, self._hpu_operation_status)
        self.operation_mode = read_enum(json, 'operationMode', constants.HwsOperationModeSettings,self._operation_mode)
        self.boost_mode = read_enum(json, 'boostMode', constants.HwsBoostModeSettings, self._boost_mode)
        self.tank_temperature = read_value(json, 'tankTemperature', self._tank_temperature)
        self.outdoor_temperature = read_value(json, 'outdoorTemperature', self._outdoor_temperature)
        self._load_weekly_settings(json)       
        has_changed = self._has_changed
        self._has_changed = False
        return has_changed
    
class HwsDeviceParameters:
    """Device parameters for a standalone Heat Pump Hot Water tank unit
    (deviceType "11", e.g. HE-UM40CR).  These values don't change, and can't be changed by the user.

    This is returned by the /hphw/deviceStatus endpoint.
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
        return  self._permission

    @property
    def weekly_mode(self):
        return  self._weekly_mode

    @property
    def pv_mode(self):
        return  self._pv_mode

    @property
    def holiday_mode(self):
        return  self._holiday_mode
    

    def load(self, json) -> bool:
        if not json:
            return False

        self._has_changed = False
        self._permission = read_value(json, 'permission', self._permission)
        self._weekly_mode = read_value(json, 'weeklyMode', self._weekly_mode)
        self._pv_mode = read_value(json, 'pvMode', self._pv_mode)
        self._holiday_mode = read_value(json, 'holidayMode', self._holiday_mode)
        has_changed = self._has_changed
        has_changed = True if self._load_temperature_setting_limits(json) else has_changed
        self._has_changed = False
        return has_changed

    def _load_temperature_setting_limits(self, json)-> bool:
        limits_json = json.get('temperatureSettingLimits')
        if not limits_json:
            self._has_limits = False
            return False
        self._has_limits = True
        if not self._limits:
            self._limits = HwsTemperatureSettingLimits(limits_json)
            return True
        else:
            return self._limits.load(limits_json) 


class HwsConsumption:
    """One entry of HWS energy consumption/cost history, broken down by
    only for hot-water-tank, as returned by the hphw/deviceHistoryData 
    endpoint
    """

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
        return self._tank_consumption if self._tank_consumption else None

    def load(self, json) -> bool:
        if not json:
            self._has_changed = False
            return False
        self._tank_consumption = read_value(json, 'consumption', self._tank_consumption)
        self._tank_cost = read_value(json, 'cost', self._tank_cost)
        self._data_time = read_value(json, 'dataTime', self._data_time)
        self._tank_temp = read_value(json, 'tankTemperature', self._tank_temp)
        self._outdoor_temp = read_value(json, 'outdoorTemperature', self._outdoor_temp)       
        self._has_changed = True
        return True


    def copy(self, other) -> bool:
        if not other:
            self._has_changed = False
            return False
        self._tank_consumption = other._tank_consumption
        self._tank_cost = other._tank_cost
        self._data_time = other._data_time
        self._tank_temp = other._tank_temp 
        self._outdoor_temp =  other._outdoor_temp
        self._has_changed = True
        return True

class HwsInhibitTimeSettings:
    """Which hours to prevent operation when heating is set to run continuously"""

    def __init__(self, json=None) -> None:
        self._inhibit_time_available: int | None = None  #shoud be an enum 
        self._start_time: int | None = None       
        self._endTime: int | None = None                                 
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
    def endTime(self):
        return self._endTime
    @endTime.setter
    def endTime(self, value):
        if self._endTime == value:
            return
        self._endTime = value
        self._has_changed = True
    
    def load(self, json) -> bool:
        if not json:
            return False
        self._has_changed = False
        self.inhibit_time_available = read_value(json, 'inhibitTimeAvailable', self._inhibit_time_available)
        self.start_time = read_value(json, 'startTime', self._start_time)
        self.endTime = read_value(json, 'endTime', self._endTime)
        has_changed=self._has_changed
        self._has_changed = False
        return has_changed

class HwsSet1Settings:
    """Which hours to allow operation when heating is set to run only periodically"""

    def __init__(self, json=None) -> None:
        self._startTime: int | None = None       
        self._endTime: int | None = None                                 
        self.load(json)

    @property
    def has_changed(self):
        return self._has_changed

    @property
    def startTime(self):
        return self._startTime 
    @startTime.setter
    def startTime(self, value):
        if self._startTime == value:
            return
        self._startTime = value
        self._has_changed = True


    @property
    def endTime(self):
        return self._endTime
    @endTime.setter
    def endTime(self, value):
        if self._endTime == value:
            return
        self._endTime = value
        self._has_changed = True
    
    def load(self, json) -> bool:
        if not json:
            return False
        self._has_changed = False
        self.startTime = read_value(json, 'startTime', self._startTime)
        self.endTime = read_value(json, 'endTime', self._endTime)
        has_changed = self._has_changed
        self._has_changed = False
        return has_changed


class HwsSet2Settings:
    """Which hours to allow operation for a second time in a day when heating is set to run only periodically"""

    def __init__(self, json=None) -> None:
        self._set2_available: int | None = None  #shoud be an enum
        self._startTime: int | None = None       
        self._endTime: int | None = None          
        self._start_temperature: int | None = None
        self._end_temperature: int | None = None                       
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
    def startTime(self):
        return self._startTime
    @startTime.setter
    def startTime(self, value):
        if self._startTime == value:
            return
        self._startTime = value
        self._has_changed = True

    @property
    def endTime(self):
        return self._endTime
    @endTime.setter
    def endTime(self, value):
        if self._endTime == value:
            return
        self._endTime = value   
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
        self.set2_available = read_value(json, 'set2Available', self._set2_available)
        self.startTime = read_value(json, 'startTime', self._startTime)
        self.endTime = read_value(json, 'endTime', self._endTime)
        self.start_temperature = read_value(json, 'startTemperature', self._start_temperature)
        self.end_temperature = read_value(json, 'endTemperature', self._end_temperature)
        has_changed = self._has_changed
        self._has_changed = False
        return has_changed


class HwsDailySettings:
    """One day of HWS energy operational settings.
    These are set with the /hphw/deviceStatus/control
    endpoint
    """

    def __init__(self, json=None) -> None:

        self._weekday: constants.HwsWeekdaySettings | None = None
        self._mode: constants.HwsDailyModeSettings | None = None
        self._inhibit_time: HwsInhibitTimeSettings | None = None
        self._set1: HwsSet1Settings | None = None
        self._set2: HwsSet2Settings | None = None
        self.load(json)

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

    def _load_set1(self, json)->bool:
        set1_json = json.get('set1')
        if not set1_json:
            self._set1 = None
            return False
        if not self._set1:
            self._set1 = HwsSet1Settings(set1_json)
            return True
        else:
            return self._set1.load(set1_json)

    def _load_set2(self, json)->bool:
        set2_json = json.get('set2')
        if not set2_json:
            self._set2 = None
            return False
        if not self._set2:
            self._set2 = HwsSet2Settings(set2_json)
            return True
        else:
            has_changed = self._set2.load(set2_json)
        return has_changed

    def _load_inhibit_time(self, json)->bool:
        inhibit_time_json = json.get('inhibitTime')
        if not inhibit_time_json:
            self._inhibit_time = None
            return False
        if not self._inhibit_time:
            self._inhibit_time = HwsInhibitTimeSettings(inhibit_time_json)
            return True
        else:
            return self._inhibit_time.load(inhibit_time_json)


    def load(self, json) -> bool:
        if not json:
            return False
        self._has_changed = False
        has_changed=False
        self.weekday = read_enum(json, 'weekday', constants.HwsWeekdaySettings, self._weekday)
        self.mode = read_enum(json, 'mode', constants.HwsDailyModeSettings,self._mode)  
        has_changed = self._has_changed
        has_changed = True if self._load_inhibit_time(json) else has_changed
        has_changed = True if self._load_set1(json) else has_changed
        has_changed = True if self._load_set2(json) else has_changed
        self._has_changed = False
        return has_changed

class HwsCustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, HwsDailySettings):
            return {"weekday": obj.weekday.value if obj.weekday is not None else None, 
                    "mode": obj.mode.value if obj.mode else None, 
                    "inhibitTime": obj.inhibit_time if obj.inhibit_time else None, 
                    "set1": obj.set1 if obj.set1 else None, 
                    "set2": obj.set2 if obj.set2 else None}
        if isinstance(obj, HwsSet1Settings):
            return{"startTime": obj.startTime if obj.startTime is not None else None, 
                    "endTime": obj.endTime if obj.endTime is not None else None
            }
        if isinstance(obj, HwsSet2Settings):
            return{"set2Available": obj.set2_available if obj.set2_available is not None else None, 
                    "startTime": obj.startTime if obj.startTime is not None else None, 
                    "endTime": obj.endTime if obj.endTime is not None else None,
                    "startTemperature": obj.start_temperature if obj.start_temperature is not None else None,
                    "endTemperature": obj.end_temperature if obj.end_temperature is not None else None
            }
        if isinstance(obj, HwsInhibitTimeSettings):
            return{"inhibitTimeAvailable": obj.inhibit_time_available if obj.inhibit_time_available is not None else None, 
                    "startTime": obj.start_time if obj.start_time is not None else None, 
                    "endTime": obj.endTime if obj.endTime is not None else None
            }
        return super().default(obj)