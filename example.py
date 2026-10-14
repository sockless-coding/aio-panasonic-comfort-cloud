"""Interactive test tool for aio-panasonic-comfort-cloud.

Logs in, lists every device on the account and opens a menu for the chosen
device (air conditioner, Aquarea heat pump or HWS hot water tank) to read
its state and try out the library's calls against the real API.

    python example.py -u you@example.com -p secret
    python example.py --oauth
    python example.py --agreements-only

Every menu takes the number of an entry; an empty answer or 0 goes back.
"""

import argparse
import asyncio
import json
import logging
import os
from datetime import date
from collections.abc import Awaitable, Callable, Sequence
from enum import Enum
from typing import TypeVar

import aiohttp

from aio_panasonic_comfort_cloud import (
    ApiClient,
    AquareaDevice,
    AquareaWeeklyTimer,
    AquareaWeeklyTimerPattern,
    HwsDevice,
    PanasonicDevice,
    PanasonicDeviceInfo,
    WeeklyTimer,
    WeeklyTimerPattern,
    constants,
)
from aio_panasonic_comfort_cloud.exceptions import AgreementNotAcceptedError, MFARequiredError


def parse_args():
    parser = argparse.ArgumentParser(
        description="Interactively test the aio-panasonic-comfort-cloud library."
    )
    parser.add_argument(
        "-u", "--username",
        default=os.getenv("PANASONIC_USERNAME"),
        help="Panasonic Comfort Cloud username (email). "
             "Can also be set via PANASONIC_USERNAME env var.",
    )
    parser.add_argument(
        "-p", "--password",
        default=os.getenv("PANASONIC_PASSWORD"),
        help="Panasonic Comfort Cloud password. "
             "Can also be set via PANASONIC_PASSWORD env var.",
    )
    parser.add_argument(
        "--agreements-only",
        action="store_true",
        help="Only check and accept pending agreements, then exit (no device operations).",
    )
    parser.add_argument(
        "--oauth",
        action="store_true",
        help="Authenticate via a browser-based OAuth flow instead of "
             "username/password. You'll be given a URL to open in any "
             "browser (Auth0's own hosted page handles login, MFA, etc.) "
             "and asked to paste back the resulting redirect URL. "
             "Username/password are not required with this option.",
    )
    parser.add_argument(
        "--no-auto-power-on",
        action="store_true",
        help="Construct the client with auto_power_on=False, so changes that "
             "need the unit on are buffered while it's off.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Start with debug logging (shows every request and response). "
             "Can also be toggled from the main menu.",
    )
    return parser.parse_args()


# --- Console helpers -------------------------------------------------------

T = TypeVar("T")
E = TypeVar("E", bound=Enum)
Action = Callable[[], Awaitable[None]]

class Back(Exception):
    """Raised by a prompt when the user leaves it empty to go back."""


def heading(text: str):
    print(f"\n=== {text} ===")


def ask(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default is not None else ""
    answer = input(f"{prompt}{suffix}: ").strip()
    if not answer:
        if default is None:
            raise Back
        return default
    return answer


def ask_int(prompt: str, default: int | None = None) -> int:
    while True:
        answer = ask(prompt, None if default is None else str(default))
        try:
            return int(answer)
        except ValueError:
            print("  Please enter a whole number.")


def ask_float(prompt: str, default: float | None = None) -> float:
    while True:
        answer = ask(prompt, None if default is None else str(default))
        try:
            return float(answer)
        except ValueError:
            print("  Please enter a number.")


def confirm(prompt: str) -> bool:
    return input(f"{prompt} [y/N]: ").strip().lower() in ("y", "yes")


def choose(title: str, options: Sequence[tuple[str, T]]) -> T:
    """Pick one of ``options`` (label, value). Raises Back on 0/empty."""
    print(f"\n{title}")
    for index, (label, _) in enumerate(options, start=1):
        print(f"  {index:>2}) {label}")
    print("   0) Back")
    while True:
        answer = input("> ").strip()
        if answer in ("", "0"):
            raise Back
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return options[int(answer) - 1][1]
        print("  Not a valid choice.")


def choose_enum(enum_type: type[E], current: E | None = None) -> E:
    options = [
        (member.name + (" (current)" if member == current else ""), member)
        for member in enum_type
    ]
    return choose(f"{enum_type.__name__}:", options)


def choose_optional_enum(enum_type: type[E], current: E | None = None) -> E | None:
    """Like :func:`choose_enum`, with an extra entry that returns None."""
    options: list[tuple[str, E | None]] = [
        (member.name + (" (current)" if member == current else ""), member)
        for member in enum_type
    ]
    options.append(("<not set>", None))
    return choose(f"{enum_type.__name__}:", options)


def name_of(value) -> str:
    if value is None:
        return "-"
    if isinstance(value, Enum):
        return value.name
    return str(value)


def print_rows(rows: list[tuple[str, object]]):
    width = max((len(label) for label, _ in rows), default=0)
    for label, value in rows:
        print(f"  {label:<{width}}  {name_of(value)}")


def print_json(data):
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


async def run_menu(title: str,
                   entries: Sequence[tuple[str, Action]] | Callable[[], Sequence[tuple[str, Action]]]):
    """Show a menu until the user goes back.

    ``entries`` is a list of (label, async callable), or a callable returning
    one so labels can show live state. Errors from an action are printed
    instead of ending the session, so one failing call doesn't stop testing.
    """
    while True:
        current = entries() if callable(entries) else entries
        try:
            action = choose(f"--- {title} ---", current)
        except Back:
            return
        try:
            await action()
        except Back:
            print("  Cancelled.")
        except (KeyboardInterrupt, EOFError):
            raise
        except Exception as ex:  # keep the session alive while testing
            logging.getLogger(__name__).debug("Action failed", exc_info=True)
            print(f"  ! {type(ex).__name__}: {ex}")


# --- Air conditioner -------------------------------------------------------

class AirConditionerMenu:
    def __init__(self, client: ApiClient, device: PanasonicDevice):
        self.client = client
        self.info = device.info
        self.device = device

    @classmethod
    async def open(cls, client: ApiClient, device_info: PanasonicDeviceInfo):
        await cls(client, await client.get_device(device_info)).run()

    async def refresh(self):
        await self.client.try_update_device(self.device)

    async def show_status(self):
        await self.refresh()
        device = self.device
        params = device.parameters
        heading(f"{self.info.name} ({self.info.model})")
        rows = [
            ("GUID", self.info.guid),
            ("Group", self.info.group),
            ("Power", params.power),
            ("Mode", params.mode),
            ("Target temp", f"{params.target_temperature}°C"),
            ("Inside temp", f"{params.inside_temperature}°C" if device.has_inside_temperature else None),
            ("Outside temp", f"{params.outside_temperature}°C" if device.has_outside_temperature else None),
            ("Fan speed", params.fan_speed),
            ("Eco mode", params.eco_mode),
            ("Vertical swing", params.vertical_swing_mode),
            ("Horizontal swing", params.horizontal_swing_mode if device.has_horizontal_swing else None),
        ]
        if device.has_nanoe:
            rows.append(("Nanoe", params.nanoe_mode))
        if device.has_eco_navi:
            rows.append(("EcoNavi", params.eco_navi_mode))
        if device.has_eco_function:
            rows.append(("Eco function", params.eco_function_mode))
        if device.has_iauto_x:
            rows.append(("iAuto-X", params.iautox_mode))
        if device.has_inside_cleaning:
            rows.append(("Inside cleaning", params.inside_cleaning))
        rows.append(("Last update", device.last_update))
        print_rows(rows)
        for zone in params.zones if device.has_zones else []:
            print(f"  Zone {zone.id} {zone.name!r}: {name_of(zone.mode)}, level {zone.level}")
        if self.client.has_pending_changes(device):
            print("  (changes are buffered until the unit is powered on)")

    async def change(self, apply):
        """Build a change request with ``apply(builder)`` and send it."""
        builder = self.client.new_change_request(self.device)
        apply(builder)
        if not builder.has_changes:
            print("  Nothing to change.")
            return
        print(f"  Sending {builder.build()}")
        await self.client.set_device_raw(self.device, builder.build())
        await self.client.try_update_device(self.device)
        print("  Done.")

    async def toggle_power(self):
        await self.refresh()
        new_value = constants.Power.Off if self.device.parameters.power == constants.Power.On else constants.Power.On
        await self.change(lambda b: b.set_power_mode(new_value))

    async def set_mode(self):
        value = choose_enum(constants.OperationMode, self.device.parameters.mode)
        await self.change(lambda b: b.set_hvac_mode(value))

    async def set_temperature(self):
        value = ask_float("Target temperature (°C)", self.device.parameters.target_temperature)
        await self.change(lambda b: b.set_target_temperature(value))

    async def set_fan_speed(self):
        value = choose_enum(constants.FanSpeed, self.device.parameters.fan_speed)
        await self.change(lambda b: b.set_fan_speed(value))

    async def set_eco_mode(self):
        value = choose_enum(constants.EcoMode, self.device.parameters.eco_mode)
        await self.change(lambda b: b.set_eco_mode(value))

    async def set_vertical_swing(self):
        value = choose_enum(constants.AirSwingUD, self.device.parameters.vertical_swing_mode)
        await self.change(lambda b: b.set_vertical_swing(value))

    async def set_horizontal_swing(self):
        value = choose_enum(constants.AirSwingLR, self.device.parameters.horizontal_swing_mode)
        await self.change(lambda b: b.set_horizontal_swing(value))

    async def set_nanoe(self):
        value = choose_enum(constants.NanoeMode, self.device.parameters.nanoe_mode)
        await self.change(lambda b: b.set_nanoe_mode(value))

    async def set_eco_navi(self):
        value = choose_enum(constants.EcoNaviMode, self.device.parameters.eco_navi_mode)
        await self.change(lambda b: b.set_eco_navi_mode(value))

    async def set_eco_function(self):
        value = choose_enum(constants.EcoFunctionMode, self.device.parameters.eco_function_mode)
        await self.change(lambda b: b.set_eco_function_mode(value))

    async def set_iautox(self):
        value = choose_enum(constants.IAutoXMode, self.device.parameters.iautox_mode)
        await self.change(lambda b: b.set_iautox_mode(value))

    async def set_inside_cleaning(self):
        current = self.device.parameters.inside_cleaning
        value = choose_enum(constants.InsideCleaningMode,
                            constants.InsideCleaningMode(current) if current in (0, 1) else None)
        await self.change(lambda b: b.set_inside_cleaning_mode(value))

    async def set_zone(self):
        zone = choose("Zone:", [(f"{z.id} {z.name}", z) for z in self.device.parameters.zones])
        mode = choose_enum(constants.ZoneMode, zone.mode)
        level = ask_int("Damper level (blank keeps it)", zone.level)

        def apply(builder):
            builder.set_zone_mode(zone.id, mode)
            if level != zone.level:
                builder.set_zone_damper(zone.id, level)
        await self.change(apply)

    async def show_energy(self):
        energy = await self.client.async_get_energy(self.info)
        if energy is None:
            print("  No energy data for today.")
            return
        heading("Energy today")
        print_rows([
            ("Consumption", energy.consumption),
            ("Heating", energy.heating_consumption),
            ("Cooling", energy.cooling_consumption),
            ("Current power", energy.current_power),
        ])

    async def show_history(self):
        mode = choose_enum(constants.DataMode)
        day = ask("Date (YYYYMMDD)", date.today().strftime("%Y%m%d"))
        print_json(await self.client.history(self.info.id, mode, day))

    async def weekly_timer(self):
        await WeeklyTimerMenu.open(self.client, self.info)

    async def dump(self):
        request = self.client.dump(self.info.id)
        print_json(await request if request else None)

    def entries(self):
        device = self.device
        entries = [
            ("Show status", self.show_status),
            ("Toggle power", self.toggle_power),
            ("Set mode", self.set_mode),
            ("Set target temperature", self.set_temperature),
            ("Set fan speed", self.set_fan_speed),
            ("Set eco mode (Auto/Powerful/Quiet)", self.set_eco_mode),
            ("Set vertical swing", self.set_vertical_swing),
        ]
        if device.has_horizontal_swing:
            entries.append(("Set horizontal swing", self.set_horizontal_swing))
        if device.has_nanoe:
            entries.append(("Set nanoe", self.set_nanoe))
        if device.has_eco_navi:
            entries.append(("Set EcoNavi", self.set_eco_navi))
        if device.has_eco_function:
            entries.append(("Set eco function", self.set_eco_function))
        if device.has_iauto_x:
            entries.append(("Set iAuto-X", self.set_iautox))
        if device.has_inside_cleaning:
            entries.append(("Set inside cleaning", self.set_inside_cleaning))
        if device.has_zones:
            entries.append(("Set zone", self.set_zone))
        entries += [
            ("Weekly timer...", self.weekly_timer),
            ("Energy today", self.show_energy),
            ("Energy history", self.show_history),
            ("Dump raw status JSON", self.dump),
        ]
        return entries

    async def run(self):
        await self.show_status()
        await run_menu(f"Air conditioner: {self.info.name}", self.entries)


# --- Weekly timer ----------------------------------------------------------

class WeeklyTimerMenu:
    """Edits the schedule locally; nothing is sent until "Save"."""

    pattern_type = WeeklyTimerPattern
    title = "Weekly timer"

    def __init__(self, client: ApiClient, device_info: PanasonicDeviceInfo, timer: WeeklyTimer):
        self.client = client
        self.info = device_info
        self.timer = timer
        self.dirty = False

    @classmethod
    async def open(cls, client: ApiClient, device_info: PanasonicDeviceInfo):
        await cls(client, device_info, await client.get_weekly_timer(device_info)).run()

    async def fetch(self):
        return await self.client.get_weekly_timer(self.info)

    async def send(self):
        await self.client.set_weekly_timer(self.timer)

    async def reload(self):
        self.timer = await self.fetch()
        self.dirty = False

    def status_line(self) -> str:
        return f"Enabled: {self.timer.enabled}   Can edit: {self.timer.can_edit}"

    def show(self):
        timer = self.timer
        heading(f"{self.title}: {self.info.name}")
        print(f"  {self.status_line()}{'   (unsaved changes)' if self.dirty else ''}")
        for day in timer.days:
            print(f"  {day.weekday.name}")
            if not day.patterns:
                print("    (no patterns)")
            for pattern in day.patterns:
                print(f"    {self.describe(pattern)}")

    @staticmethod
    def describe(pattern: WeeklyTimerPattern) -> str:
        parts = [pattern.start_time or "--:--", name_of(pattern.power)]
        if pattern.power == constants.Power.On or pattern.power is None:
            mode = pattern.mode.name if pattern.mode else f"mode {pattern.mode_raw}"
            parts.append(mode)
            if pattern.temperature is not None:
                parts.append(f"{pattern.temperature}°C")
            for label, value in (("fan", pattern.fan_speed), ("ud", pattern.air_swing_ud),
                                 ("lr", pattern.air_swing_lr), ("eco", pattern.eco_mode)):
                if value is not None:
                    parts.append(f"{label}={value.name}")
        return "  ".join(parts)

    async def show_status(self):
        self.show()

    def choose_days(self, prompt: str) -> list:
        options = [(day.weekday.name, [day]) for day in self.timer.days]
        options.append(("Monday-Friday", self.timer.days[:5]))
        options.append(("Saturday-Sunday", self.timer.days[5:]))
        options.append(("Every day", self.timer.days))
        return choose(prompt, options)

    @staticmethod
    def build_pattern(start_time: str | None = None) -> WeeklyTimerPattern:
        pattern = WeeklyTimerPattern(start_time=ask("Start time (HH:MM)", start_time))
        pattern.power = choose_enum(constants.Power)
        if pattern.power == constants.Power.On:
            pattern.mode = choose_enum(constants.OperationMode)
            pattern.temperature = ask_float("Temperature (°C)", 22.0)
            pattern.fan_speed = choose_optional_enum(constants.FanSpeed)
            if confirm("Set air direction / eco mode too?"):
                pattern.air_swing_ud = choose_optional_enum(constants.AirSwingUD)
                pattern.air_swing_lr = choose_optional_enum(constants.AirSwingLR)
                pattern.eco_mode = choose_optional_enum(constants.EcoMode)
        return pattern

    async def add_pattern(self):
        days = self.choose_days("Add to which day(s)?")
        pattern = self.build_pattern()
        for day in days:
            # Separate copy per day so later edits don't leak between days
            day.add_pattern(self.pattern_type(pattern.to_dict()))
        self.dirty = True
        print(f"  Added {self.describe(pattern)} to {', '.join(d.weekday.name for d in days)}.")

    async def edit_pattern(self):
        day = self.choose_days("Which day?")[0]
        old = choose("Pattern:", [(self.describe(p), p) for p in day.patterns])
        new = self.build_pattern(old.start_time)
        day.remove_pattern(old)
        day.add_pattern(new)
        self.dirty = True

    async def remove_pattern(self):
        day = self.choose_days("Which day?")[0]
        pattern = choose("Remove:", [(self.describe(p), p) for p in day.patterns])
        day.remove_pattern(pattern)
        self.dirty = True

    async def clear_days(self):
        days = self.choose_days("Clear which day(s)?")
        if confirm(f"Remove all patterns from {', '.join(d.weekday.name for d in days)}?"):
            for day in days:
                day.clear()
            self.dirty = True

    async def copy_day(self):
        source = self.choose_days("Copy from which day?")[0]
        targets = self.choose_days("Copy to which day(s)?")
        for target in targets:
            if target is not source:
                target.set_patterns([self.pattern_type(p.to_dict()) for p in source.patterns])
        self.dirty = True

    async def toggle_enabled(self):
        self.timer.enabled = not self.timer.enabled
        self.dirty = True
        print(f"  Enabled will be {self.timer.enabled} once saved.")

    def warn_before_save(self):
        if not self.timer.can_edit:
            print(f"  Warning: permission {self.timer.permission} - the app wouldn't allow editing.")

    async def save(self):
        self.warn_before_save()
        if not confirm("Send this schedule to the device?"):
            return
        await self.send()
        await self.reload()
        print("  Saved.")
        self.show()

    async def discard(self):
        if not self.dirty or confirm("Discard local changes and reload?"):
            await self.reload()
            self.show()

    async def show_json(self):
        print_json(self.timer.to_dict())

    def entries(self):
        return [
            ("Show schedule", self.show_status),
            ("Add pattern", self.add_pattern),
            ("Edit pattern", self.edit_pattern),
            ("Remove pattern", self.remove_pattern),
            ("Clear day(s)", self.clear_days),
            ("Copy day", self.copy_day),
            (f"{'Disable' if self.timer.enabled else 'Enable'} schedule", self.toggle_enabled),
            ("Save to device" + (" *" if self.dirty else ""), self.save),
            ("Reload from device (discard changes)", self.discard),
            ("Show request JSON", self.show_json),
        ]

    async def run(self):
        self.show()
        while True:
            await run_menu(f"{self.title} (edits are local until saved)", self.entries)
            if not self.dirty or confirm("Leave without saving your changes?"):
                return


class AquareaWeeklyTimerMenu(WeeklyTimerMenu):
    """Aquarea flavour of the schedule editor: a pattern holds one mode plus
    the on/off state and setpoint of each zone and the tank."""

    pattern_type = AquareaWeeklyTimerPattern
    title = "Aquarea weekly timer"
    timer: AquareaWeeklyTimer

    def __init__(self, client: ApiClient, device: AquareaDevice, timer: AquareaWeeklyTimer):
        super().__init__(client, device.info, timer)
        self.device = device

    @classmethod
    async def open(cls, client: ApiClient, device: AquareaDevice):
        await cls(client, device, await client.get_aquarea_weekly_timer(device.info)).run()

    async def fetch(self):
        return await self.client.get_aquarea_weekly_timer(self.info)

    async def send(self):
        await self.client.set_aquarea_weekly_timer(self.timer)

    def status_line(self) -> str:
        limits = [f"zone {zone.get('zoneId')} heat {zone.get('heatMin')}-{zone.get('heatMax')}"
                  f" cool {zone.get('coolMin')}-{zone.get('coolMax')}" for zone in self.timer.zone_status]
        tank = self.timer.tank_status
        if tank:
            limits.append(f"tank {tank.get('heatMin')}-{tank.get('heatMax')}")
        return f"Enabled: {self.timer.enabled}   Ranges: {'; '.join(limits) or 'n/a'}"

    def warn_before_save(self):
        pass

    @staticmethod
    def describe(pattern: AquareaWeeklyTimerPattern) -> str:
        mode = pattern.mode.name if pattern.mode else f"mode {pattern.mode_raw}"
        parts = [pattern.start_time or "--:--", mode]
        for zone_id in (1, 2):
            on_off = pattern.zone_on_off(zone_id)
            if on_off is None:
                continue
            text = f"zone{zone_id}={on_off.name}"
            if on_off == constants.AquareaOperationStatus.On:
                setpoints = [f"{label} {value}" for label, value in
                             (("heat", pattern.zone_heat(zone_id)), ("cool", pattern.zone_cool(zone_id)))
                             if value is not None]
                if setpoints:
                    text += f" ({', '.join(setpoints)})"
            parts.append(text)
        if pattern.tank_on_off is not None:
            text = f"tank={pattern.tank_on_off.name}"
            if pattern.tank_on_off == constants.AquareaOperationStatus.On and pattern.tank_temperature is not None:
                text += f" ({pattern.tank_temperature}°C)"
            parts.append(text)
        return "  ".join(parts)

    def build_pattern(self, start_time: str | None = None) -> AquareaWeeklyTimerPattern:
        params = self.device.parameters
        pattern = AquareaWeeklyTimerPattern(start_time=ask("Start time (HH:MM)", start_time))
        modes = [constants.AquareaUpdateOperationMode.Heat]
        if any(zone.supports_cooling for zone in params.zones):
            modes += [constants.AquareaUpdateOperationMode.Cool, constants.AquareaUpdateOperationMode.Auto]
        pattern.mode = choose("Mode:", [(mode.name, mode) for mode in modes])
        on_off_values = [constants.AquareaOperationStatus.On, constants.AquareaOperationStatus.Off]
        for zone in params.zones:
            if zone.id not in (1, 2):
                continue
            on_off = choose(f"Zone {zone.id} {zone.name!r}:", [(value.name, value) for value in on_off_values])
            heat = cool = None
            if on_off == constants.AquareaOperationStatus.On:
                limits = self.timer.zone_limits(zone.id) or {}
                if pattern.mode != constants.AquareaUpdateOperationMode.Cool:
                    heat = ask_int(f"Zone {zone.id} heat setpoint ({limits.get('heatMin')}-{limits.get('heatMax')})",
                                   zone.heat_set)
                if pattern.mode != constants.AquareaUpdateOperationMode.Heat and zone.supports_cooling:
                    cool = ask_int(f"Zone {zone.id} cool setpoint ({limits.get('coolMin')}-{limits.get('coolMax')})",
                                   zone.cool_set)
            pattern.set_zone(zone.id, on_off, heat, cool)
        if params.has_tank and params.tank:
            pattern.tank_on_off = choose("Tank:", [(value.name, value) for value in on_off_values])
            if pattern.tank_on_off == constants.AquareaOperationStatus.On:
                tank = self.timer.tank_status or {}
                pattern.tank_temperature = ask_int(
                    f"Tank temperature ({tank.get('heatMin')}-{tank.get('heatMax')})", params.tank.heat_set)
        return pattern


# --- Aquarea -----------------------------------------------------------------

class AquareaMenu:
    def __init__(self, client: ApiClient, device: AquareaDevice):
        self.client = client
        self.info = device.info
        self.device = device

    @classmethod
    async def open(cls, client: ApiClient, device_info: PanasonicDeviceInfo):
        await cls(client, await client.get_aquarea_device(device_info)).run()

    async def refresh(self):
        await self.client.try_update_aquarea_device(self.device)

    async def show_status(self):
        await self.refresh()
        params = self.device.parameters
        heading(f"{self.info.name} (Aquarea)")
        print_rows([
            ("Operation", params.operation_status),
            ("Mode", params.operation_mode),
            ("Mode status", params.device_mode_status),
            ("Outdoor temp", params.temperature_outdoor),
            ("Direction", params.direction),
            ("Quiet mode", params.quiet_mode),
            ("Force DHW", params.force_dhw),
            ("Force heater", params.force_heater),
            ("Holiday timer", params.holiday_timer),
            ("Powerful time", params.powerful_time),
            ("Special status", params.special_status),
            ("Error", params.fault_status if params.is_on_error else None),
        ])
        tank = params.tank
        if params.has_tank and tank:
            print(f"  Tank: {name_of(tank.operation_status)}, {tank.temperature}°C "
                  f"(set {tank.heat_set}, range {tank.heat_min}-{tank.heat_max})")
        for zone in params.zones:
            print(f"  Zone {zone.id} {zone.name!r}: {name_of(zone.operation_status)}, {zone.temperature}°C "
                  f"(heat set {zone.heat_set}, cool set {zone.cool_set})")

    async def set_and_refresh(self, call):
        await call
        print("  Sent.")
        await self.show_status()

    async def set_operation(self):
        value = choose_enum(constants.AquareaOperationStatus)
        await self.set_and_refresh(self.client.set_aquarea_operation_status(self.info, value))

    async def set_mode(self):
        value = choose_enum(constants.AquareaUpdateOperationMode)
        await self.set_and_refresh(self.client.set_aquarea_operation_mode(self.info, value))

    async def set_quiet(self):
        value = choose_enum(constants.AquareaQuietMode, self.device.parameters.quiet_mode)
        await self.set_and_refresh(self.client.set_aquarea_quiet_mode(self.info, value))

    async def set_force_dhw(self):
        value = choose_enum(constants.AquareaForceDHW, self.device.parameters.force_dhw)
        await self.set_and_refresh(self.client.set_aquarea_force_dhw(self.info, value))

    async def set_force_heater(self):
        value = choose_enum(constants.AquareaForceHeater, self.device.parameters.force_heater)
        await self.set_and_refresh(self.client.set_aquarea_force_heater(self.info, value))

    async def set_holiday(self):
        value = choose_enum(constants.AquareaHolidayTimer, self.device.parameters.holiday_timer)
        await self.set_and_refresh(self.client.set_aquarea_holiday_timer(self.info, value))

    async def set_powerful(self):
        value = choose_enum(constants.AquareaPowerfulTime, self.device.parameters.powerful_time)
        await self.set_and_refresh(self.client.set_aquarea_powerful_time(self.info, value))

    async def set_special(self):
        value = choose_optional_enum(constants.AquareaSpecialStatus, self.device.parameters.special_status)
        await self.refresh()
        await self.set_and_refresh(self.client.set_aquarea_special_status(self.device, value))

    def require_tank(self):
        tank = self.device.parameters.tank
        if tank is None:
            raise RuntimeError("This unit reports no tank")
        return tank

    async def set_tank_temperature(self):
        tank = self.require_tank()
        value = ask_int(f"Tank temperature ({tank.heat_min}-{tank.heat_max})", tank.heat_set)
        await self.set_and_refresh(self.client.set_aquarea_tank_temperature(self.info, value))

    async def set_tank_operation(self):
        value = choose_enum(constants.AquareaOperationStatus, self.require_tank().operation_status)
        await self.set_and_refresh(self.client.set_aquarea_tank_operation_status(self.info, value))

    def choose_zone(self):
        """Returns (zone id, zone)."""
        return choose("Zone:", [
            (f"{zone.id} {zone.name}", (zone.id, zone))
            for zone in self.device.parameters.zones if zone.id is not None
        ])

    async def set_zone_temperature(self):
        zone_id, zone = self.choose_zone()
        mode = choose("Setpoint:", [("Heat", "heat"), ("Cool", "cool")]) if zone.supports_cooling else "heat"
        default = zone.heat_set if mode == "heat" else zone.cool_set
        value = ask_int(f"{mode.title()} setpoint", default)
        await self.set_and_refresh(self.client.set_aquarea_zone_temperature(self.info, zone_id, value, mode))

    async def set_zone_operation(self):
        zone_id, zone = self.choose_zone()
        value = choose_enum(constants.AquareaOperationStatus, zone.operation_status)
        await self.set_and_refresh(self.client.set_aquarea_zone_operation_status(self.info, zone_id, value))

    async def request_defrost(self):
        if confirm("Request a defrost cycle?"):
            await self.set_and_refresh(self.client.request_aquarea_defrost(self.info))

    async def weekly_timer(self):
        await self.refresh()
        await AquareaWeeklyTimerMenu.open(self.client, self.device)

    async def show_consumption(self):
        mode = choose_enum(constants.AquareaDataMode)
        day = ask("Date (YYYYMMDD)", date.today().strftime("%Y%m%d"))
        for item in await self.client.async_get_aquarea_consumption(self.info, mode, day):
            print(f"  {item.data_time}: heat {item.heat_consumption}, cool {item.cool_consumption}, "
                  f"tank {item.tank_consumption}, total {item.total_consumption}")

    def entries(self):
        params = self.device.parameters
        entries = [
            ("Show status", self.show_status),
            ("Set on/off", self.set_operation),
            ("Set mode", self.set_mode),
            ("Set quiet mode", self.set_quiet),
            ("Set force DHW", self.set_force_dhw),
            ("Set force heater", self.set_force_heater),
            ("Set holiday timer", self.set_holiday),
            ("Set powerful time", self.set_powerful),
            ("Set special status (Eco/Comfort)", self.set_special),
        ]
        if params.has_tank:
            entries += [
                ("Set tank temperature", self.set_tank_temperature),
                ("Set tank on/off", self.set_tank_operation),
            ]
        if params.zones:
            entries += [
                ("Set zone temperature", self.set_zone_temperature),
                ("Set zone on/off", self.set_zone_operation),
            ]
        entries += [
            ("Request defrost", self.request_defrost),
            ("Weekly timer...", self.weekly_timer),
            ("Consumption", self.show_consumption),
        ]
        return entries

    async def run(self):
        await self.show_status()
        await run_menu(f"Aquarea: {self.info.name}", self.entries)


# --- HWS (hot water tank) ----------------------------------------------------

class HwsMenu:
    def __init__(self, client: ApiClient, device: HwsDevice):
        self.client = client
        self.info = device.info
        self.device = device

    @classmethod
    async def open(cls, client: ApiClient, device_info: PanasonicDeviceInfo):
        await cls(client, await client.get_hws_device(device_info)).run()

    async def refresh(self):
        await self.client.try_update_hws_device(self.device)

    async def show_status(self):
        await self.refresh()
        params = self.device.parameters
        heading(f"{self.info.name} (HWS)")
        print_rows([
            ("Tank temp", f"{params.tank_temperature}°C"),
            ("Outdoor temp", f"{params.outdoor_temperature}°C"),
            ("Operation mode", params.operation_mode),
            ("Boost", params.boost_mode),
            ("Heat pump", params.hpu_operation_status),
        ])
        for day in params.weekly_settings or []:
            line = f"  {name_of(day.weekday):<10} {name_of(day.mode)}"
            if day.set1:
                line += f"  set1 {day.set1.start_time}-{day.set1.end_time}"
            if day.set2 and day.set2.set2_available:
                line += f"  set2 {day.set2.start_time}-{day.set2.end_time}"
            print(line)

    async def set_boost(self):
        value = choose_enum(constants.HwsBoostMode, self.device.parameters.boost_mode)
        await self.client.set_hws_boost_mode(self.info, value)
        await self.show_status()

    async def set_operation_mode(self):
        value = choose_enum(constants.HwsOperationMode, self.device.parameters.operation_mode)
        await self.client.set_hws_operation_mode(self.info, value)
        await self.show_status()

    async def show_consumption(self):
        consumption = await self.client.async_get_hws_consumption(self.info)
        if consumption is None:
            print("  No consumption data for today.")
            return
        print_rows([
            ("Consumption", consumption.tank_consumption),
            ("Cost", consumption.tank_cost),
        ])

    def entries(self):
        return [
            ("Show status", self.show_status),
            ("Set boost", self.set_boost),
            ("Set operation mode", self.set_operation_mode),
            ("Consumption today", self.show_consumption),
        ]

    async def run(self):
        await self.show_status()
        await run_menu(f"HWS: {self.info.name}", self.entries)


# --- Session / main menu -------------------------------------------------------

async def login(client: ApiClient, use_oauth: bool):
    if use_oauth:
        # Alternative to start_session(): authenticate in a real browser
        # instead of this library's own credential-scraping login flow. See
        # README.md "Alternative: Browser-Based Authentication".
        auth_url, code_verifier = client.get_browser_authorization_url()
        print("Open this URL in a browser and log in:")
        print(f"  {auth_url}")
        redirect_url = input(
            "\nAfter logging in, paste the resulting redirect URL "
            "(starts with 'panasonic-iot-cfc://'): "
        ).strip()
        await client.complete_browser_authentication(redirect_url, code_verifier)
        return

    # With 2FA/MFA enabled, start_session() raises MFARequiredError; ask for
    # the code from the authenticator app and retry with it.
    try:
        await client.start_session()
    except MFARequiredError:
        otp_code = input("Enter the 2FA/OTP code from your authenticator app: ").strip()
        await client.start_session(otp_code=otp_code)


async def check_agreements(client: ApiClient):
    heading("Agreements")
    type_names = {client.AGREEMENT_TYPE_TERMS: "Terms & Conditions",
                  client.AGREEMENT_TYPE_PRIVACY: "Privacy Policy",
                  client.AGREEMENT_TYPE_SERVICE: "Service Agreement",
                  client.AGREEMENT_TYPE_COOKIE_POLICY: "Cookie Policy"}
    for item in await client.get_agreement_status():
        print(f"  Accepted: {type_names.get(item.get('type'), item.get('type'))} v{item.get('version')}")
    pending = await client.get_pending_agreements()
    if not pending:
        print("  All agreements are accepted.")
        return
    for doc in pending:
        print(f"  Pending:  {type_names.get(doc['type'], doc['type'])} v{doc['version']}")
    if not confirm("Accept the pending agreements?"):
        return
    try:
        await client.ensure_all_agreements_accepted()
        print("  All agreements are accepted.")
    except AgreementNotAcceptedError as ex:
        print(f"  Some agreements could not be auto-accepted: {ex}")


def device_entries(client: ApiClient) -> list[tuple[str, Action]]:
    """One main-menu entry per device. Each device is loaded when opened."""
    def opener(menu_type, info) -> Action:
        return lambda: menu_type.open(client, info)

    entries = []
    for info in client.get_devices():
        entries.append((f"[AC]      {info.name} ({info.model}, {info.group})",
                        opener(AirConditionerMenu, info)))
    for info in client.aquarea_devices:
        entries.append((f"[Aquarea] {info.name} ({info.group})", opener(AquareaMenu, info)))
    for info in client.hws_devices:
        entries.append((f"[HWS]     {info.name} ({info.group})", opener(HwsMenu, info)))
    return entries


async def main(args):
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    async with aiohttp.ClientSession() as session:
        client = ApiClient(args.username, args.password, session,
                           auto_power_on=not args.no_auto_power_on)
        try:
            await login(client, args.oauth)

            if args.agreements_only:
                await check_agreements(client)
                return

            devices = device_entries(client)
            print(f"\nLogged in. Found {len(devices)} device(s).")
            for info in client.unknown_devices:
                print(f"  Unsupported device: {info.name} (type {info.device_type})")

            async def toggle_debug():
                root = logging.getLogger()
                root.setLevel(logging.INFO if root.level == logging.DEBUG else logging.DEBUG)
                print(f"  Logging level is now {logging.getLevelName(root.level)}.")

            async def agreements():
                await check_agreements(client)

            def main_entries():
                debug_on = logging.getLogger().level == logging.DEBUG
                return devices + [
                    ("Check / accept agreements", agreements),
                    (f"Debug logging: {'on' if debug_on else 'off'}", toggle_debug),
                ]

            await run_menu("Main menu (0 to quit)", main_entries)
        finally:
            # Best-effort: if authentication never completed there's no
            # session to stop, and that error would hide the real one.
            try:
                await client.stop_session()
            except Exception:
                pass


if __name__ == "__main__":
    args = parse_args()

    if not args.oauth and (not args.username or not args.password):
        print("Error: username and password are required (or pass --oauth to authenticate via browser instead).")
        print("Pass them as arguments (-u / -p) or set PANASONIC_USERNAME / PANASONIC_PASSWORD env vars.")
        raise SystemExit(1)

    try:
        asyncio.run(main(args))
    except (KeyboardInterrupt, EOFError):
        print("\nBye.")
