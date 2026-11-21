
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
    # Only accepted by units whose ``nanoeStandAlone`` feature flag is set. The
    # app sends 5 to start it, but the unit then reports Fan (4) with
    # ``lastSettingMode`` 2 and nanoe 3/4 (see
    # ``PanasonicDevice.in_nanoe_stand_alone_mode``).
    NanoeStandAlone = 5
    # Only accepted by units whose ``clothesDrying`` feature flag is set.
    # Reported back as 6 as well.
    ClothesDrying = 6


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

class FireplaceMode(Enum):
    """``fireplace`` parameter. The app only lets it be changed while the unit
    is in Heat mode, and only when the device-level ``fireplace`` flag is set."""
    Unavailable = 0
    Off = 1
    On = 2

class StatusDataMode(Enum):
    LIVE = 0
    CACHED = 1


# Air conditioner device types the Comfort Cloud app treats as "CAC" (ducted /
# commercial) units rather than "RAC" room units. The app limits these to the
# fan speeds given by the device's ``fanSpeedMode`` and hides Quiet/Powerful,
# EcoFunction, nanoe and horizontal swing for them.
CAC_DEVICE_TYPES = ("4", "5", "6", "8", "9", "10")

# Values of the device-level ``fanSpeedMode`` field (CAC units only).
FAN_SPEED_MODE_NONE = 0
FAN_SPEED_MODE_3_STEP = 3
FAN_SPEED_MODE_5_STEP = 5


class WeeklyTimerWeekday(Enum):
    """Position of a day in the AC weekly timer's ``weeklyTimerList``."""
    Monday = 0
    Tuesday = 1
    Wednesday = 2
    Thursday = 3
    Friday = 4
    Saturday = 5
    Sunday = 6


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


class AquareaDhwType(Enum):
    """``dhwType`` of a standalone domestic hot water (DHW) unit in the group
    listing (only meaningful when ``dhwFlg`` is true).

    Picks the endpoint the app talks to: the Aquarea DHW tanks use
    ``/remote/v1/api/devices/dhw`` and EcoFlex (new in app 5.x) uses
    ``/remote/v1/api/devices/ecoflex``.
    """
    AquareaDhwWH = 1
    AquareaDhwFS = 2
    EcoFlex = 3


class AquareaDhwOperationMode(Enum):
    """``operationMode`` of a standalone DHW unit (``dhwFlg`` true). Not the
    same values as the heat pump's :class:`AquareaUpdateOperationMode`."""
    HeatPump = 1
    HeaterOnly = 2
    Auto = 3


AQUAREA_DEVICES_API = "/remote/v1/api/devices"
AQUAREA_DHW_DEVICES_API = "/remote/v1/api/devices/dhw"
AQUAREA_ECOFLEX_DEVICES_API = "/remote/v1/api/devices/ecoflex"
AQUAREA_WEEKLY_TIMER_API = "/remote/v1/api/data/weeklyTimer"
AQUAREA_FAVORITE_TIMER_API = "/remote/v1/api/data/weeklyTimer/favoriteTimer"


class AquareaDataMode(Enum):
    """dataMode values for the Aquarea /remote/v1/api/consumption endpoint.

    Distinct from — and NOT interchangeable with — the AC-only ``DataMode``
    enum used by ``deviceHistoryData`` (which has different values, e.g.
    ``Week`` and a different Year encoding). Aquarea's consumption endpoint
    has no "Week" granularity.
    """
    Day = 0
    Month = 1
    Year = 2


# --- HWS (standalone Heat Pump Hot Water tank, e.g. HE-UM40CR) ---
# Device type "11" in the group listing identifies a standalone hot-water
# heat pump unit. Unlike Aquarea combi units (type "2"), these report a flat
# tankTemperature/hpuOperationStatus/operationMode/boostMode set inside a
# "parameters" object (so they look superficially like an air conditioner),
# but the AC deviceStatus/deviceHistoryData endpoints 403 for this device
# class. They have their own /hphw/deviceStatus, /hphw/deviceStatus/control
# and /hphw/deviceHistoryData endpoints instead, confirmed against a real
# HE-UM40CR.
HWS_DEVICE_TYPE = "11"


class HwsOperationStatus(Enum):
    """Whether the heat pump unit is currently running (read-only)."""
    Off = 0
    On = 1
    Unknown = 2


class HwsOperationMode(Enum):
    """Operation mode of an HWS device."""
    Schedule = 0
    # Only useful when the unit is wired to an inverter output signalling
    # that PV production is active
    PVTimer = 1
    Holiday = 2


class HwsBoostMode(Enum):
    Off = 0
    On = 1


class HwsWeekday(Enum):
    Monday = 1
    Tuesday = 2
    Wednesday = 3
    Thursday = 4
    Friday = 5
    Saturday = 6
    Sunday = 7


class HwsDailyMode(Enum):
    """Heating mode for one day of the weekly schedule."""
    Timer = 0
    Continuous = 1


class HwsDataMode(Enum):
    """dataMode values for the HWS /hphw/deviceHistoryData endpoint."""
    Day = 0
    Month = 1
    Year = 2


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

# Since app 5.x the inputs of the X-CFC-API-KEY hash come from this file
# instead of being built into the app. Its values are RSA-OAEP(SHA-256)
# blobs that the app decrypts with SECURITY_KEY_PUBLIC_KEY. The defaults
# below are what it held when 5.1.2 was released and are used whenever the
# file can't be fetched or decoded.
SECURITY_KEY_INITIALIZE_URL = f"{BASE_PATH_ACC}/resources/Initialize/V_5_0_0/initialize_android.json"
SECURITY_KEY_PUBLIC_KEY = (
    "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDaZEmYUsl3PON0oD+3O5rlL1RBVtKXyVxDv2eN1JP+A0jWmuWm"
    "rgtaws/7OQokkcYIX4G9BRz8s6T2UMjaGrAk+5ImUxaS9q9IEVhdhVAckHrBAR980j/IubC+y3Xa0Rd0EwN79Mom"
    "mayrXg9SrmJGHIEqkku7UAz5k2Nu5V/OuQIDAQAB"
)
DEFAULT_SECURITY_KEY_APP_NAME_HASH = "d2bf5231251384fb684dacf71344674b"
DEFAULT_SECURITY_KEY_INSERT_STRING = "cfc"

CHECK_RESPONSE_ERROR_MESSAGE = """Error in %s
Expected status code '%s' but received '%s'
Response body: %s"""
CHECK_RESPONSE_ERROR_MESSAGE_WITH_PAYLOAD = """Error in %s
Expected status code '%s' but received '%s'
Payload: %s
Response body: %s"""