from datetime import datetime, timezone

from .panasonicdevice import PanasonicDeviceInfo
from .models.hws import HwsDeviceParameters, HwsParameters
from .exceptions import DeviceIsNotReadyError


class HwsDevice:
    """A standalone Heat Pump Hot Water tank device (deviceType "11", e.g.
    HE-UM40CR).

    Mirrors :class:`AquareaDevice`/:class:`PanasonicDevice`. Built from the
    ``/hphw/deviceStatus`` response: the top level holds the fixed device
    capabilities (:class:`HwsDeviceParameters`) and the nested ``parameters``
    object holds the current state (:class:`HwsParameters`).
    """

    def __init__(self, info: PanasonicDeviceInfo, json=None) -> None:
        self._info = info
        self._device_parameters: HwsDeviceParameters | None = None
        self._parameters: HwsParameters | None = None
        self._last_update = datetime.now(timezone.utc)
        self.load(json)

    @property
    def id(self) -> str:
        return self.info.id if self.info.id is not None else "-"

    @property
    def info(self) -> PanasonicDeviceInfo:
        return self._info

    @property
    def device_parameters(self) -> HwsDeviceParameters:
        if self._device_parameters is None:
            raise DeviceIsNotReadyError
        return self._device_parameters

    @property
    def parameters(self) -> HwsParameters:
        if self._parameters is None:
            raise DeviceIsNotReadyError
        return self._parameters

    @property
    def last_update(self) -> datetime:
        return self._last_update

    def load(self, json) -> bool:
        """Load/refresh from a ``/hphw/deviceStatus`` response. Returns True
        if anything changed."""
        if not json:
            return False

        has_changed = False
        if not self._device_parameters:
            self._device_parameters = HwsDeviceParameters(json)
            has_changed = True
        else:
            has_changed = self._device_parameters.load(json) or has_changed

        parameters_json = json.get('parameters')
        if parameters_json:
            if not self._parameters:
                self._parameters = HwsParameters(parameters_json)
                has_changed = True
            else:
                has_changed = self._parameters.load(parameters_json) or has_changed

        if has_changed:
            self._last_update = datetime.now(timezone.utc)
        return has_changed
