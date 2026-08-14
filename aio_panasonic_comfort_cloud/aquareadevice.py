from datetime import datetime, timezone

from .panasonicdevice import PanasonicDeviceInfo
from .models.aquarea import AquareaDeviceParameters
from .exceptions import DeviceIsNotReadyError


class AquareaDevice:
    """An Aquarea (Air to Water heat pump) device.

    Mirrors :class:`PanasonicDevice` but wraps :class:`AquareaDeviceParameters`
    instead of the air conditioner parameter set, since Aquarea units expose a
    different status shape (tank + zone status rather than a single
    ``parameters`` object).
    """

    def __init__(self, info: PanasonicDeviceInfo, json=None) -> None:
        self._info = info
        self._parameters: AquareaDeviceParameters | None = None
        self._last_update = datetime.now(timezone.utc)
        self._operation: str | None = None
        self._owner_flag: bool = False
        self._a2w_name: str = ""
        self.load(json)

    @property
    def id(self) -> str:
        return self.info.id if self.info.id is not None else "-"

    @property
    def info(self) -> PanasonicDeviceInfo:
        return self._info

    @property
    def parameters(self) -> AquareaDeviceParameters:
        if self._parameters is None:
            raise DeviceIsNotReadyError
        return self._parameters

    @property
    def last_update(self) -> datetime:
        return self._last_update

    @property
    def operation(self) -> str | None:
        return self._operation

    @property
    def owner_flag(self) -> bool:
        return self._owner_flag

    @property
    def a2w_name(self) -> str:
        return self._a2w_name

    def load(self, json) -> bool:
        if not json:
            return False
        self._operation = json.get('operation', self._operation)
        self._owner_flag = json.get('ownerFlg', self._owner_flag)
        self._a2w_name = json.get('a2wName', self._a2w_name)

        status_json = json.get('status')
        has_changed = False
        if not self._parameters:
            self._parameters = AquareaDeviceParameters(status_json)
            has_changed = True
        else:
            has_changed = self._parameters.load(status_json) or has_changed

        if has_changed:
            self._last_update = datetime.now(timezone.utc)
        return has_changed
