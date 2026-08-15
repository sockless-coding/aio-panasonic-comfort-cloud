import logging

from .. import constants

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


class HwsDeviceParameters:
    """Live status of a standalone Heat Pump Hot Water tank unit
    (deviceType "11", e.g. HE-UM40CR).

    Parsed directly from the ``parameters`` object already present in the
    ``/device/group`` response — unlike air conditioners, this device class
    doesn't support a per-device ``deviceStatus`` refresh call (it 403s), so
    there's nothing more to fetch beyond what the group listing already
    contains.

    The exact meaning of ``operation_mode`` (and whether
    ``hpu_operation_status`` is a user-controllable power switch or just a
    read-only "is it actively heating right now" indicator, analogous to
    Aquarea's ``direction``/``pump_duty``) hasn't been confirmed yet — only
    ``tank_temperature`` and ``boost_mode`` have been verified against a real
    device.
    """

    def __init__(self, json=None) -> None:
        self._hpu_operation_status = constants.AquareaOperationStatus.Off
        self._operation_mode: int | None = None
        self._boost_mode = constants.AquareaOperationStatus.Off
        self._tank_temperature: float | None = None

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

    def load(self, json) -> bool:
        if not json:
            return False
        self._has_changed = False

        self.hpu_operation_status = read_enum(json, 'hpuOperationStatus', constants.AquareaOperationStatus, self.hpu_operation_status)
        self.operation_mode = read_value(json, 'operationMode', self.operation_mode)
        self.boost_mode = read_enum(json, 'boostMode', constants.AquareaOperationStatus, self.boost_mode)
        self.tank_temperature = read_value(json, 'tankTemperature', self.tank_temperature)

        has_changed = self._has_changed
        self._has_changed = False
        return has_changed
