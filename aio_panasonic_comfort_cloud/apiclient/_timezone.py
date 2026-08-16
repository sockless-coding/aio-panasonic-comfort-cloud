import time
from datetime import datetime

_current_time_zone = None
_current_time_zone_date = None


def get_current_time_zone():
    global _current_time_zone
    global _current_time_zone_date
    today_date = datetime.now().date()
    if _current_time_zone is not None and today_date == _current_time_zone_date:
        return _current_time_zone
    local_offset_seconds = -time.timezone
    if time.localtime().tm_isdst:
        local_offset_seconds += 3600
    hours, remainder = divmod(abs(local_offset_seconds), 3600)
    minutes = remainder // 60
    _current_time_zone = f"{'+' if local_offset_seconds >= 0 else '-'}{int(hours):02}:{int(minutes):02}"
    _current_time_zone_date = today_date
    return _current_time_zone
