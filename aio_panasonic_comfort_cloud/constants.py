
from enum import Enum


class Power(Enum):
    OFF = 0
    ON = 1


class OperationMode(Enum):
    AUTO = 0
    DRY = 1
    COOL = 2
    HEAT = 3
    FAN = 4


class AirSwingUD(Enum):
    AUTO = -1
    TOP = 0
    MIDDLE_TOP = 3
    MIDDLE = 2
    MIDDLE_DOWN = 4
    DOWN = 1
    SWING = 5


class AirSwingLR(Enum):
    AUTO = -1
    LEFT = 1
    CENTER_LEFT = 5
    CENTER = 2
    CENTER_RIGHT = 4
    RIGHT = 0
    UNAVAILABLE = 6


class EcoMode(Enum):
    AUTO = 0
    POWERFUL = 1
    QUIET = 2


class AirSwingAutoMode(Enum):
    DISABLED = 1
    BOTH = 0
    SWING_LEFT_RIGHT = 3
    SWING_UP_DOWN = 2


class FanSpeed(Enum):
    AUTO = 0
    LOW = 1
    MEDIUM_LOW = 2
    MEDIUM = 3
    MEDIUM_HIGH = 4
    HIGH = 5


class DataMode(Enum):
    DAY = 0
    WEEK = 1
    MONTH = 2
    YEAR = 4


class NanoeMode(Enum):
    UNAVAILABLE = 0
    OFF = 1
    ON = 2
    MODE_G = 3
    ALL = 4

class EcoNaviMode(Enum):
    UNAVAILABLE = 0
    OFF = 1
    ON = 2

class EcoFunctionMode(Enum):
    UNAVAILABLE = 0
    OFF = 1
    ON = 2

class ZoneMode(Enum):
    OFF = 0
    ON = 1

class IAutoXMode(Enum):
    UNAVAILABLE = 0
    OFF = 1
    ON = 2

class StatusDataMode(Enum):
    LIVE = 0
    CACHED = 1

INVALID_TEMPERATURE = 126

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