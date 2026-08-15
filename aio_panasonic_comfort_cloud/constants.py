
from enum import Enum


class Power(Enum):
    Off = 0
    On = 1


class OperationMode(Enum):
    Auto = 0
    Dry = 1
    Cool = 2
    Heat = 3
    Fan = 4


class AirSwingUD(Enum):
    Auto = -1
    Up = 0
    UpMid = 3
    Mid = 2
    DownMid = 4
    Down = 1
    Swing = 5


class AirSwingLR(Enum):
    Auto = -1
    Left = 1
    LeftMid = 5
    Mid = 2
    RightMid = 4
    Right = 0
    Unavailable = 6


class EcoMode(Enum):
    Auto = 0
    Powerful = 1
    Quiet = 2


class AirSwingAutoMode(Enum):
    Disabled = 1
    Both = 0
    AirSwingLR = 3
    AirSwingUD = 2


class FanSpeed(Enum):
    Auto = 0
    Low = 1
    LowMid = 2
    Mid = 3
    HighMid = 4
    High = 5


class DataMode(Enum):
    Day = 0
    Week = 1
    Month = 2
    Year = 4


class NanoeMode(Enum):
    Unavailable = 0
    Off = 1
    On = 2
    ModeG = 3
    All = 4

class EcoNaviMode(Enum):
    Unavailable = 0
    Off = 1
    On = 2

class EcoFunctionMode(Enum):
    Unavailable = 0
    Off = 1
    On = 2

class ZoneMode(Enum):
    Off = 0
    On = 1

class InsideCleaningMode(Enum):
    Off = 0
    On = 1

class IAutoXMode(Enum):
    Unavailable = 0
    Off = 1
    On = 2

class StatusDataMode(Enum):
    LIVE = 0
    CACHED = 1


# --- Aquarea (Air to Water heat pump) ---
# Device type "2" in the group listing identifies an Aquarea unit.
AQUAREA_DEVICE_TYPE = "2"


class AquareaOperationStatus(Enum):
    """Whole-device, tank or zone on/off status."""
    Off = 0
    On = 1
    Unknown = 2


class AquareaOperationMode(Enum):
    """Operation mode as reported in the device status (read-only)."""
    Off = 0
    Heat = 1
    Cool = 2
    AutoHeat = 3
    AutoCool = 4


class AquareaUpdateOperationMode(Enum):
    """Operation mode values accepted when changing the mode."""
    Off = 0
    Heat = 2
    Cool = 3
    Auto = 8


class AquareaDeviceModeStatus(Enum):
    Normal = 0
    Defrost = 1


class AquareaDeviceDirection(Enum):
    Idle = 0
    Pump = 1
    Water = 2


class AquareaPumpDuty(Enum):
    Off = 0
    On = 1


class AquareaQuietMode(Enum):
    Off = 0
    Level1 = 1
    Level2 = 2
    Level3 = 3


class AquareaForceDHW(Enum):
    Off = 0
    On = 1


class AquareaForceHeater(Enum):
    Off = 0
    On = 1


class AquareaHolidayTimer(Enum):
    Off = 0
    On = 1


class AquareaPowerfulTime(Enum):
    Off = 0
    On30Min = 1
    On60Min = 2
    On90Min = 3


class AquareaSpecialStatus(Enum):
    Eco = 1
    Comfort = 2


# --- HWS (standalone Heat Pump Hot Water tank, e.g. HE-UM40CR) ---
# Device type "11" in the group listing identifies a standalone hot-water
# heat pump unit. Unlike Aquarea combi units (type "2"), these report a flat
# tankTemperature/hpuOperationStatus/operationMode/boostMode set inside the
# normal "parameters" object (so they look superficially like an air
# conditioner), but they don't support the AC deviceStatus/deviceHistoryData
# endpoints — those 403 for this device class. Confirmed against a real
# HE-UM40CR device/group response; reported by a user, not yet independently
# reverse-engineered from the app.
HWS_DEVICE_TYPE = "11"


INVALID_TEMPERATURE = 126

MAX_POWER_WATTS = 5000

DEFAULT_X_APP_VERSION = "1.21.0"

MAX_VERSION_AGE = 2

SETTING_ACCESS_TOKEN = "access_token"
SETTING_ACCESS_TOKEN_EXPIRES = "access_token_expires"
SETTING_REFRESH_TOKEN = "refresh_token"
SETTING_SCOPE = "scope"
SETTING_VERSION = "android_version"
SETTING_VERSION_DATE = "android_version_date"
SETTING_CLIENT_ID = "clientId"

APP_CLIENT_ID = "Xmy6xIYIitMxngjB2rHvlm6HSDNnaMJx"
AUTH_0_CLIENT = "eyJuYW1lIjoiQXV0aDAuQW5kcm9pZCIsImVudiI6eyJhbmRyb2lkIjoiMzAifSwidmVyc2lvbiI6IjIuOS4zIn0="
REDIRECT_URI = "panasonic-iot-cfc://authglb.digital.panasonic.com/android/com.panasonic.ACCsmart/callback"
BASE_PATH_AUTH = "https://authglb.digital.panasonic.com"
BASE_PATH_ACC = "https://accsmart.panasonic.com"
AUTH_API_USER_AGENT = "okhttp/4.10.0"
AUTH_BROWSER_USER_AGENT = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Mobile Safari/537.36"

CHECK_RESPONSE_ERROR_MESSAGE = """Error in %s
Expected status code '%s' but received '%s'
Response body: %s"""
CHECK_RESPONSE_ERROR_MESSAGE_WITH_PAYLOAD = """Error in %s
Expected status code '%s' but received '%s'
Payload: %s
Response body: %s"""