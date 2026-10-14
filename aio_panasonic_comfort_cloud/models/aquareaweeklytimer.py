"""Weekly timer (weekly schedule) of an Aquarea heat pump, as read from and
written to ``/remote/v1/api/data/weeklyTimer`` through the common/transfer
proxy.

Same layout as the air conditioner schedule: seven days (Monday first) of up
to six patterns each. An Aquarea pattern is a start time plus one operation
mode for the unit and the on/off state and target temperature of zone 1,
zone 2 and the tank. Leave the settings of a zone or tank the unit doesn't
have as ``None``.

Each object keeps the JSON it was loaded from and only rewrites the keys it
knows about, so fields this library doesn't model are sent back unchanged.
"""

import copy
import logging
from enum import Enum

from .. import constants
from .weeklytimer import (
    WEEKLY_TIMER_DAYS,
    WeeklyTimerDay,
    _normalize_start_time,
)

_LOGGER = logging.getLogger(__name__)

# The app stores the zones as numbered fields, zone1* and zone2*.
_ZONE_IDS = (1, 2)


def _read_enum(json: dict, key: str, enum_type: type[Enum]):
    value = json.get(key)
    if value is None:
        return None
    try:
        return enum_type(value)
    except ValueError:
        _LOGGER.debug("Unknown Aquarea weekly timer value '%s' for '%s'", value, key)
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


def _write_temperature(json: dict, key: str, value: int | None):
    if value is None:
        json.pop(key, None)
    else:
        json[key] = int(value)


def _zone_key(zone_id: int, suffix: str) -> str:
    if zone_id not in _ZONE_IDS:
        raise ValueError(f"Aquarea weekly timer zone id must be 1 or 2, got {zone_id}")
    return f"zone{zone_id}{suffix}"


class AquareaWeeklyTimerPattern:
    """One scheduled change: at :attr:`start_time` the unit switches to the
    settings in this pattern. Settings left as ``None`` aren't sent.

    :attr:`mode` uses the same values as changing the operation mode
    (:class:`constants.AquareaUpdateOperationMode`). The app only offers
    Heat, Cool and Auto, and forces Heat on units without cooling.
    Temperatures are whole degrees and should stay within the ranges in
    :attr:`AquareaWeeklyTimer.zone_status`/:attr:`AquareaWeeklyTimer.tank_status`.
    """

    def __init__(self, json: dict | None = None, *,
                 start_time: str | None = None,
                 mode: constants.AquareaUpdateOperationMode | None = None) -> None:
        self._json: dict = copy.deepcopy(json) if json else {}
        if start_time is not None:
            self.start_time = start_time
        if mode is not None:
            self.mode = mode

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
    def mode(self) -> constants.AquareaUpdateOperationMode | None:
        return _read_enum(self._json, 'mode', constants.AquareaUpdateOperationMode)
    @mode.setter
    def mode(self, value):
        _write_enum(self._json, 'mode', value, constants.AquareaUpdateOperationMode)

    @property
    def mode_raw(self) -> int | None:
        return self._json.get('mode')

    def zone_on_off(self, zone_id: int) -> constants.AquareaOperationStatus | None:
        return _read_enum(self._json, _zone_key(zone_id, 'OnOff'), constants.AquareaOperationStatus)

    def set_zone_on_off(self, zone_id: int, value: constants.AquareaOperationStatus | None):
        _write_enum(self._json, _zone_key(zone_id, 'OnOff'), value, constants.AquareaOperationStatus)

    def zone_heat(self, zone_id: int) -> int | None:
        """Heat setpoint of the zone."""
        return self._json.get(_zone_key(zone_id, 'Heat'))

    def set_zone_heat(self, zone_id: int, value: int | None):
        _write_temperature(self._json, _zone_key(zone_id, 'Heat'), value)

    def zone_cool(self, zone_id: int) -> int | None:
        """Cool setpoint of the zone."""
        return self._json.get(_zone_key(zone_id, 'Cool'))

    def set_zone_cool(self, zone_id: int, value: int | None):
        _write_temperature(self._json, _zone_key(zone_id, 'Cool'), value)

    def set_zone(self, zone_id: int, on_off: constants.AquareaOperationStatus | None,
                 heat: int | None = None, cool: int | None = None):
        """Set a zone's on/off state and setpoints in one call."""
        self.set_zone_on_off(zone_id, on_off)
        self.set_zone_heat(zone_id, heat)
        self.set_zone_cool(zone_id, cool)

    @property
    def tank_on_off(self) -> constants.AquareaOperationStatus | None:
        return _read_enum(self._json, 'tankOnOff', constants.AquareaOperationStatus)
    @tank_on_off.setter
    def tank_on_off(self, value):
        _write_enum(self._json, 'tankOnOff', value, constants.AquareaOperationStatus)

    @property
    def tank_temperature(self) -> int | None:
        return self._json.get('tankTemperature')
    @tank_temperature.setter
    def tank_temperature(self, value: int | None):
        _write_temperature(self._json, 'tankTemperature', value)

    @property
    def raw(self) -> dict:
        """The pattern's underlying JSON, for fields not modelled here."""
        return self._json

    def to_dict(self) -> dict:
        """Serialize for the weekly timer POST. An empty slot becomes ``{}``,
        as the app sends it."""
        if self.is_empty:
            return {}
        return {key: value for key, value in self._json.items() if value is not None}

    def __repr__(self) -> str:
        return f"AquareaWeeklyTimerPattern({self.to_dict()})"


class AquareaWeeklyTimerDay(WeeklyTimerDay):
    """The patterns of one weekday, kept sorted by start time."""

    _pattern_type = AquareaWeeklyTimerPattern

    @property
    def patterns(self) -> list[AquareaWeeklyTimerPattern]:
        return super().patterns

    def __repr__(self) -> str:
        return f"AquareaWeeklyTimerDay({self.weekday.name}, {self._patterns})"


class AquareaWeeklyTimer:
    """The weekly schedule of one Aquarea heat pump."""

    def __init__(self, gwid: str, json: dict | None = None) -> None:
        self._gwid = gwid
        self._json: dict = {}
        self._days: list[AquareaWeeklyTimerDay] = []
        self.load(json)

    @property
    def gwid(self) -> str:
        """The device guid, which the Aquarea API calls ``gwid``."""
        return self._gwid

    @property
    def _weekly_timer(self) -> dict:
        return self._json.setdefault('weeklyTimer', {})

    @property
    def enabled(self) -> bool:
        """Whether the schedule is active (``operation`` 1)."""
        return self._weekly_timer.get('operation') == 1
    @enabled.setter
    def enabled(self, value: bool):
        self._weekly_timer['operation'] = 1 if value else 0

    @property
    def zone_status(self) -> list[dict]:
        """Raw allowed setpoint ranges per zone (``zoneId``, ``heatMin``,
        ``heatMax``, ``coolMin``, ``coolMax``), as returned with the schedule."""
        return (self._json.get('status') or {}).get('zoneStatus') or []

    def zone_limits(self, zone_id: int) -> dict | None:
        return next((zone for zone in self.zone_status if zone.get('zoneId') == zone_id), None)

    @property
    def tank_status(self) -> dict | None:
        """Raw allowed tank temperature range (``heatMin``, ``heatMax``,
        ``minTemp``, ``maxTemp``), as returned with the schedule."""
        return (self._json.get('status') or {}).get('tankStatus')

    @property
    def days(self) -> list[AquareaWeeklyTimerDay]:
        """Monday through Sunday."""
        return list(self._days)

    def day(self, weekday: constants.WeeklyTimerWeekday | int | str) -> AquareaWeeklyTimerDay:
        if isinstance(weekday, str):
            weekday = constants.WeeklyTimerWeekday[weekday]
        return self._days[constants.WeeklyTimerWeekday(weekday).value]

    @property
    def raw(self) -> dict:
        return self._json

    def load(self, json: dict | None) -> bool:
        """Replace the schedule with ``json`` (the GET response, holding
        ``weeklyTimer`` and ``status``). Returns True if it changed."""
        json = copy.deepcopy(json) if json else {}
        weekly_timer = json.get('weeklyTimer') or {}
        json['weeklyTimer'] = weekly_timer
        weekly_timer.setdefault('operation', 0)
        day_jsons = [day or {} for day in weekly_timer.get('timer') or []]
        day_jsons += [{}] * (WEEKLY_TIMER_DAYS - len(day_jsons))
        days = [
            AquareaWeeklyTimerDay(weekday, day_json)
            for weekday, day_json in zip(constants.WeeklyTimerWeekday, day_jsons)
        ]
        has_changed = self._days == [] or self.to_dict() != self._serialize(self._gwid, weekly_timer, days)
        self._json = json
        self._days = days
        return has_changed

    @staticmethod
    def _serialize(gwid: str, weekly_timer: dict, days: list[AquareaWeeklyTimerDay]) -> dict:
        data = {key: value for key, value in weekly_timer.items() if value is not None}
        data['timer'] = [day.to_dict() for day in days]
        return {'gwid': gwid, 'weeklyTimer': data}

    def to_dict(self) -> dict:
        """Serialize as the ``bodyParam`` of the weekly timer POST."""
        return self._serialize(self._gwid, self._weekly_timer, self._days)

    def __repr__(self) -> str:
        return f"AquareaWeeklyTimer({self._gwid}, enabled={self.enabled}, days={self._days})"
