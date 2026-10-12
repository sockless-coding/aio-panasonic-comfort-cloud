from datetime import datetime, timezone
from .panasonicdevice import PanasonicDeviceInfo
from .models.hws import HwsDeviceParameters, HwsParameters
from .exceptions import DeviceIsNotReadyError


class HwsDevice:
    """A standalone Heat Pump Hot Water tank device (deviceType "11", e.g.
    HE-UM40CR).

    Mirrors :class:`AquareaDevice`/:class:`PanasonicDevice`, 
    This reads the data from the /hphw/deviceInfo endpoint and stores the 
    device parameters and the current parameters in the :class:`HwsDeviceParameters` and :class:`HwsParameters` objects, respectively.
    """

    def __init__(self, info: PanasonicDeviceInfo, json=None) -> None:
        self._info = info
        self._deviceParameters: HwsDeviceParameters | None = None
        self._parameters: HwsParameters | None = None
        self._last_update = datetime.now(timezone.utc)
        self._load_device_parameters(json)
        self._load_parameters(json)


    @property
    def id(self) -> str:
        return self.info.id if self.info.id is not None else "-"

    @property
    def info(self) -> PanasonicDeviceInfo:
        return self._info

    @property
    def deviceParameters(self) -> HwsDeviceParameters:
        if self._deviceParameters is None:
            raise DeviceIsNotReadyError
        return self._deviceParameters

    @property
    def parameters(self) -> HwsParameters:
        if self._parameters is None:
            raise DeviceIsNotReadyError
        return self._parameters

    @property
    def last_update(self) -> datetime:
        return self._last_update

    def _load_device_parameters(self, json) -> bool:
        """Load/refresh the device parameters.  These are actually immutable with the API, but detail
        what the acceptible temperature ranges are for the mutable parameters.  Returns True if the device parameters 
        were loaded for the first time or changed."""
        if not json:
            return False

        has_changed = False
        if not self._deviceParameters:
            self._deviceParameters = HwsDeviceParameters(json)
            has_changed = True
        else:
            has_changed = self._deviceParameters.load(json)
        return has_changed    

    def _load_parameters(self, json) -> bool:
        """Load/refresh the current parameters.  Returns True if the parameters were loaded for the first time or changed."""
        parameters_json = json.get("parameters")
        if not parameters_json:
            return False
        has_changed = False
        if not self._parameters:
            self._parameters = HwsParameters(parameters_json)
            has_changed = True
        else:
            has_changed = self._parameters.load(parameters_json)
        return has_changed

    def load(self, json) -> bool:
        """Load/refresh from the top level of the json returned by the API.
        Updates the device parameters and the current parameters, and updates the last_update timestamp if any changes were made.
        Returns True if there was json returned from the API""" 
        if not json:
            return False
        has_changed = False
        has_changed = True if self._load_device_parameters(json) else has_changed
        has_changed = True if self._load_parameters(json) else has_changed
        if has_changed:
            self._last_update = datetime.now(timezone.utc)
        return True
