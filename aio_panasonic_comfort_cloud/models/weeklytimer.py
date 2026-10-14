"""Weekly timer (weekly schedule) of an air conditioner, as read from
``GET /weeklyTimer/{guid}`` and written back with ``POST /weeklyTimer``.

The schedule holds seven days (Monday first) of up to six patterns each. A
pattern is a start time plus the settings the unit switches to at that time.

Each object keeps the JSON it was loaded from and only rewrites the keys it
knows about, so fields this library doesn't model are sent back unchanged.
"""

import copy
import logging
import re
from enum import Enum

from .. import constants

_LOGGER = logging.getLogger(__name__)

WEEKLY_TIMER_DAYS = 7
WEEKLY_TIMER_PATTERNS_PER_DAY = 6

# The API uses -255 for "not set" in a pattern's optional settings.
_NOT_SET = -255

_START_TIME_PATTERN = re.compile(r'^([01]\d|2[0-3]):[0-5]\d$')


def _read_enum(json: dict, key: str, enum_type: type[Enum]):
    value = json.get(key)
    if value is None or value == _NOT_SET:
        return None
    try:
        return enum_type(value)
    except ValueError:
        _LOGGER.debug("Unknown weekly timer value '%s' for '%s'", value, key)
        return None


def _write_enum(json: dict, key: str, value, enum_type: type[Enum]):
    if value is None:
        json.pop(key, None)
    elif isinstance(value, str):
        json[key] = enum_type[value].value
    elif isinstance(value, Enum):
        json[key] = value.value
    else:
        json[key] = int(value)


def _normalize_start_time(value: str) -> str:
    hours, sep, minutes = value.partition(':')
    if sep and hours.isdigit() and minutes.isdigit():
        value = f"{int(hours):02d}:{int(minutes):02d}"
    if not _START_TIME_PATTERN.match(value):
        raise ValueError(f"Invalid weekly timer start time '{value}', expected HH:MM")
    return value


class WeeklyTimerZone:
    """On/off state of one zone in a pattern (zone-capable ducted units only)."""

    def __init__(self, json: dict | None = None) -> None:
        self._json: dict = copy.deepcopy(json) if json else {}

    @property
    def zone_id(self) -> int | None:
        return self._json.get('zoneId')
    @zone_id.setter
    def zone_id(self, value: int | None):
        self._json['zoneId'] = value

    @property
    def zone_name(self) -> str | None:
        return self._json.get('zoneName')
    @zone_name.setter
    def zone_name(self, value: str | None):
        self._json['zoneName'] = value

    @property
    def zone_on_off(self) -> constants.ZoneMode | None:
        return _read_enum(self._json, 'zoneOnOff', constants.ZoneMode)
    @zone_on_off.setter
    def zone_on_off(self, value):
        _write_enum(self._json, 'zoneOnOff', value, constants.ZoneMode)

    def to_dict(self) -> dict:
        return {key: value for key, value in self._json.items() if value is not None}

    def __repr__(self) -> str:
        return f"WeeklyTimerZone({self.to_dict()})"


class WeeklyTimerPattern:
    """One scheduled change: at :attr:`start_time` the unit switches to the
    settings in this pattern. Settings left as ``None`` aren't sent.

    ``mode`` is the raw API value. Besides :class:`constants.OperationMode`
    (0-4) the app also stores 5 (nanoe standalone) and 6 for some units;
    those read back as ``None`` from :attr:`mode` but are kept in
    :attr:`mode_raw` and round-trip untouched.
    """

    def __init__(self, json: dict | None = None, *,
                 start_time: str | None = None,
                 power: constants.Power | None = None,
                 mode: constants.OperationMode | None = None,
                 temperature: float | None = None,
                 fan_speed: constants.FanSpeed | None = None) -> None:
        self._json: dict = copy.deepcopy(json) if json else {}
        self._zones = [WeeklyTimerZone(zone) for zone in self._json.get('zoneParameters') or []]
        if start_time is not None:
            self.start_time = start_time
        if power is not None:
            self.power = power
        if mode is not None:
            self.mode = mode
        if temperature is not None:
            self.temperature = temperature
        if fan_speed is not None:
            self.fan_speed = fan_speed

    @property
    def is_empty(self) -> bool:
        """An unused slot. The API pads each day with these."""
        return not self._json.get('startTime')

    @property
    def start_time(self) -> str | None:
        """Start time as ``HH:MM`` (24h, device local time)."""
        return self._json.get('startTime') or None
    @start_time.setter
    def start_time(self, value: str | None):
        if value is None:
            self._json.pop('startTime', None)
            return
        self._json['startTime'] = _normalize_start_time(value)

    @property
    def power(self) -> constants.Power | None:
        return _read_enum(self._json, 'onOff', constants.Power)
    @power.setter
    def power(self, value):
        _write_enum(self._json, 'onOff', value, constants.Power)

    @property
    def mode(self) -> constants.OperationMode | None:
        return _read_enum(self._json, 'mode', constants.OperationMode)
    @mode.setter
    def mode(self, value):
        _write_enum(self._json, 'mode', value, constants.OperationMode)

    @property
    def mode_raw(self) -> int | None:
        return self._json.get('mode')

    @property
    def temperature(self) -> float | None:
        """Target temperature, always in Celsius."""
        value = self._json.get('temperature')
        return None if value is None else float(value)
    @temperature.setter
    def temperature(self, value: float | None):
        if value is None:
            self._json.pop('temperature', None)
        else:
            self._json['temperature'] = float(value)

    @property
    def fan_speed(self) -> constants.FanSpeed | None:
        return _read_enum(self._json, 'fanSpeed', constants.FanSpeed)
    @fan_speed.setter
    def fan_speed(self, value):
        _write_enum(self._json, 'fanSpeed', value, constants.FanSpeed)

    @property
    def fan_auto_mode(self) -> constants.AirSwingAutoMode | None:
        return _read_enum(self._json, 'fanAutoMode', constants.AirSwingAutoMode)
    @fan_auto_mode.setter
    def fan_auto_mode(self, value):
        _write_enum(self._json, 'fanAutoMode', value, constants.AirSwingAutoMode)

    @property
    def air_swing_ud(self) -> constants.AirSwingUD | None:
        return _read_enum(self._json, 'airSwingUD', constants.AirSwingUD)
    @air_swing_ud.setter
    def air_swing_ud(self, value):
        _write_enum(self._json, 'airSwingUD', value, constants.AirSwingUD)

    @property
    def air_swing_lr(self) -> constants.AirSwingLR | None:
        return _read_enum(self._json, 'airSwingLR', constants.AirSwingLR)
    @air_swing_lr.setter
    def air_swing_lr(self, value):
        _write_enum(self._json, 'airSwingLR', value, constants.AirSwingLR)

    @property
    def eco_mode(self) -> constants.EcoMode | None:
        return _read_enum(self._json, 'ecoMode', constants.EcoMode)
    @eco_mode.setter
    def eco_mode(self, value):
        _write_enum(self._json, 'ecoMode', value, constants.EcoMode)

    @property
    def eco_navi(self) -> constants.EcoNaviMode | None:
        return _read_enum(self._json, 'ecoNavi', constants.EcoNaviMode)
    @eco_navi.setter
    def eco_navi(self, value):
        _write_enum(self._json, 'ecoNavi', value, constants.EcoNaviMode)

    @property
    def nanoe(self) -> constants.NanoeMode | None:
        return _read_enum(self._json, 'nanoe', constants.NanoeMode)
    @nanoe.setter
    def nanoe(self, value):
        _write_enum(self._json, 'nanoe', value, constants.NanoeMode)

    @property
    def iauto(self) -> int | None:
        """Raw ``iAuto`` flag: 2 when an Auto-mode pattern uses iAuto, else 1."""
        value = self._json.get('iAuto')
        return None if value is None or value == _NOT_SET else value
    @iauto.setter
    def iauto(self, value: int | None):
        if value is None:
            self._json.pop('iAuto', None)
        else:
            self._json['iAuto'] = int(value)

    @property
    def zones(self) -> list[WeeklyTimerZone]:
        return self._zones
    @zones.setter
    def zones(self, value: list[WeeklyTimerZone] | None):
        self._zones = list(value) if value else []

    @property
    def raw(self) -> dict:
        """The pattern's underlying JSON, for fields not modelled here."""
        return self._json

    def to_dict(self) -> dict:
        """Serialize for ``POST /weeklyTimer``. An empty slot becomes ``{}``,
        as the app sends it."""
        if self.is_empty:
            return {}
        data = {key: value for key, value in self._json.items() if value is not None}
        data.pop('zoneParameters', None)
        if self._zones:
            data['zoneParameters'] = [zone.to_dict() for zone in self._zones]
        # The app sets iAuto on every pattern it saves (1 unless the pattern
        # is its iAuto mode).
        if data.get('iAuto') in (None, _NOT_SET):
            data['iAuto'] = 1
        return data

    def __repr__(self) -> str:
        return f"WeeklyTimerPattern({self.to_dict()})"


class WeeklyTimerDay:
    """The patterns of one weekday, kept sorted by start time."""

    _pattern_type = WeeklyTimerPattern

    def __init__(self, weekday: constants.WeeklyTimerWeekday, json: dict | None = None) -> None:
        self._weekday = weekday
        self._json: dict = copy.deepcopy(json) if json else {}
        self._patterns = [
            pattern for pattern in
            (self._pattern_type(pattern_json) for pattern_json in self._json.get('patternList') or [])
            if not pattern.is_empty
        ]
        self._sort()

    @property
    def weekday(self) -> constants.WeeklyTimerWeekday:
        return self._weekday

    @property
    def patterns(self) -> list[WeeklyTimerPattern]:
        """The day's non-empty patterns, sorted by start time. Edit through
        :meth:`add_pattern`/:meth:`remove_pattern`/:meth:`clear`, or change
        a pattern's settings in place."""
        return list(self._patterns)

    def _sort(self):
        self._patterns.sort(key=lambda pattern: pattern.start_time or '')

    def add_pattern(self, pattern: WeeklyTimerPattern) -> WeeklyTimerPattern:
        """Add a pattern, replacing any existing one with the same start time."""
        if pattern.is_empty:
            raise ValueError("A weekly timer pattern needs a start time")
        existing = [p for p in self._patterns if p.start_time != pattern.start_time]
        if len(existing) >= WEEKLY_TIMER_PATTERNS_PER_DAY:
            raise ValueError(
                f"A weekly timer day holds at most {WEEKLY_TIMER_PATTERNS_PER_DAY} patterns")
        self._patterns = existing + [pattern]
        self._sort()
        return pattern

    def remove_pattern(self, pattern_or_start_time: WeeklyTimerPattern | str) -> bool:
        """Remove a pattern, by object or by its ``HH:MM`` start time.
        Returns False if nothing matched."""
        if isinstance(pattern_or_start_time, self._pattern_type):
            remaining = [p for p in self._patterns if p is not pattern_or_start_time]
        else:
            start_time = _normalize_start_time(pattern_or_start_time)
            remaining = [p for p in self._patterns if p.start_time != start_time]
        removed = len(remaining) != len(self._patterns)
        self._patterns = remaining
        return removed

    def clear(self):
        self._patterns = []

    def set_patterns(self, patterns: list[WeeklyTimerPattern]):
        """Replace all patterns of this day."""
        self.clear()
        for pattern in patterns:
            self.add_pattern(pattern)

    def to_dict(self) -> dict:
        self._sort()
        pattern_list = [pattern.to_dict() for pattern in self._patterns]
        pattern_list += [{}] * (WEEKLY_TIMER_PATTERNS_PER_DAY - len(pattern_list))
        data = dict(self._json)
        data['patternList'] = pattern_list
        return data

    def __repr__(self) -> str:
        return f"WeeklyTimerDay({self._weekday.name}, {self._patterns})"


class WeeklyTimer:
    """The weekly schedule of one air conditioner."""

    def __init__(self, device_guid: str, json: dict | None = None) -> None:
        self._device_guid = device_guid
        self._json: dict = {}
        self._days: list[WeeklyTimerDay] = []
        self.load(json)

    @property
    def device_guid(self) -> str:
        return self._device_guid

    @property
    def enabled(self) -> bool:
        """Whether the schedule is active (``avlFlg``)."""
        return bool(self._json.get('avlFlg'))
    @enabled.setter
    def enabled(self, value: bool):
        self._json['avlFlg'] = bool(value)

    @property
    def permission(self) -> int | None:
        return self._json.get('permission')

    @property
    def can_edit(self) -> bool:
        """The app only lets permission 2 and 3 change the schedule."""
        return self.permission in (2, 3)

    @property
    def temperature_unit(self) -> int | None:
        return self._json.get('temperatureUnit')

    @property
    def mode_availability(self) -> dict | None:
        """Raw ``modeAvlList`` (``autoMode``/``fanMode`` flags)."""
        return self._json.get('modeAvlList')

    @property
    def days(self) -> list[WeeklyTimerDay]:
        """Monday through Sunday."""
        return list(self._days)

    def day(self, weekday: constants.WeeklyTimerWeekday | int | str) -> WeeklyTimerDay:
        if isinstance(weekday, str):
            weekday = constants.WeeklyTimerWeekday[weekday]
        return self._days[constants.WeeklyTimerWeekday(weekday).value]

    @property
    def raw(self) -> dict:
        return self._json

    def load(self, json: dict | None) -> bool:
        """Replace the schedule with ``json``. Returns True if it changed."""
        json = copy.deepcopy(json) if json else {}
        json.setdefault('deviceGuid', self._device_guid)
        json.setdefault('avlFlg', False)
        day_jsons = list(json.get('weeklyTimerList') or [])
        day_jsons += [{}] * (WEEKLY_TIMER_DAYS - len(day_jsons))
        days = [
            WeeklyTimerDay(weekday, day_json)
            for weekday, day_json in zip(constants.WeeklyTimerWeekday, day_jsons)
        ]
        has_changed = self._days == [] or self.to_dict() != self._serialize(json, days)
        self._json = json
        self._days = days
        return has_changed

    @staticmethod
    def _serialize(json: dict, days: list[WeeklyTimerDay]) -> dict:
        data = {key: value for key, value in json.items() if value is not None}
        data['weeklyTimerList'] = [day.to_dict() for day in days]
        return data

    def to_dict(self) -> dict:
        """Serialize for ``POST /weeklyTimer``."""
        data = self._serialize(self._json, self._days)
        data['deviceGuid'] = self._device_guid
        return data

    def __repr__(self) -> str:
        return f"WeeklyTimer({self._device_guid}, enabled={self.enabled}, days={self._days})"
