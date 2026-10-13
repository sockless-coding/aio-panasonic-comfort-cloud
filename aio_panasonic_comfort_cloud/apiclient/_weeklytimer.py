from typing import TYPE_CHECKING

from ..models.weeklytimer import WeeklyTimer
from ..panasonicdevice import PanasonicDeviceInfo

if TYPE_CHECKING:
    from ._protocol import ApiClientCore
else:
    ApiClientCore = object


class WeeklyTimerMixin(ApiClientCore):
    """Weekly timer (weekly schedule) of air conditioners.

    Uses ``/weeklyTimer`` like the Comfort Cloud app does for AC units. The
    whole schedule is always written at once, so read it, edit it and send
    it back.
    """

    async def _async_get_weekly_timer_json(self, device_info: PanasonicDeviceInfo) -> dict | None:
        response = await self.execute_get(
            self._get_weekly_timer_url(device_info.guid), "get_weekly_timer", 200)
        timers = (response or {}).get('devWeeklyTimerList') or []
        # A device that never had a schedule returns an empty list.
        return timers[0] if timers else None

    async def get_weekly_timer(self, device_info: PanasonicDeviceInfo) -> WeeklyTimer:
        """Fetch the weekly schedule of an air conditioner."""
        json_response = await self._async_get_weekly_timer_json(device_info)
        return WeeklyTimer(device_info.guid, json_response)

    async def try_update_weekly_timer(self, device_info: PanasonicDeviceInfo, weekly_timer: WeeklyTimer) -> bool:
        """Refresh a :class:`WeeklyTimer`. Returns True if anything changed.
        Unsaved local edits are discarded."""
        json_response = await self._async_get_weekly_timer_json(device_info)
        return weekly_timer.load(json_response)

    async def set_weekly_timer(self, weekly_timer: WeeklyTimer):
        """Replace the device's weekly schedule with ``weekly_timer``,
        including its :attr:`WeeklyTimer.enabled` flag.

        Note that the app always enables the schedule when saving edits; set
        ``weekly_timer.enabled = True`` to do the same.
        """
        await self.execute_post(
            self._get_weekly_timer_url(), weekly_timer.to_dict(), "set_weekly_timer", 200)

    async def set_weekly_timer_enabled(self, device_info: PanasonicDeviceInfo, enabled: bool) -> WeeklyTimer:
        """Turn the weekly schedule on or off, keeping its patterns.
        Returns the schedule as sent."""
        weekly_timer = await self.get_weekly_timer(device_info)
        weekly_timer.enabled = enabled
        await self.set_weekly_timer(weekly_timer)
        return weekly_timer
