"""Structural type describing what ApiClient's mixins rely on from each
other (and from PanasonicSession).

Each mixin only implements one slice of ApiClient's functionality, but many
of its methods call across into other slices (e.g. `_ac.py` builds status
URLs defined in `_urls.py`, `_hws.py` calls `_get_groups()` from
`_devices.py`). At runtime this all works fine once the mixins are combined
into the concrete `ApiClient` class, but a type checker looking at a mixin
file in isolation has no way to know those attributes/methods exist.

`ApiClientCore` fills that gap for the type checker only: every mixin
inherits it under `TYPE_CHECKING` (see the `if TYPE_CHECKING` block near the
top of each `_*.py` file here), which resolves `self.*` cross-references
without adding a real base class at runtime.
"""

from typing import Any, Protocol

from ..aquareadevice import AquareaDevice
from ..panasonicdevice import PanasonicDeviceInfo


class ApiClientCore(Protocol):
    _groups: dict | None
    _devices: list[PanasonicDeviceInfo] | None
    _aquarea_devices: list[PanasonicDeviceInfo]
    _hws_devices: list[PanasonicDeviceInfo]
    _unknown_devices: list[PanasonicDeviceInfo]
    _cache_devices: dict
    _device_indexer: dict
    _auto_power_on: bool
    _pending_changes: dict[str, dict]

    @property
    def unknown_devices(self) -> list[PanasonicDeviceInfo]: ...

    @property
    def has_unknown_devices(self) -> bool: ...

    # — PanasonicSession —
    async def execute_get(self, url, function_description, expected_status_code) -> Any: ...
    async def execute_post(self, url, json_data, function_description, expected_status_code) -> Any: ...
    async def execute_put(self, url, json_data, function_description, expected_status_code) -> Any: ...

    # — DeviceDiscoveryMixin —
    async def _get_groups(self) -> None: ...
    def _find_raw_device(self, guid: str | None): ...

    # — AquareaMixin —
    async def get_aquarea_device(self, device_info: PanasonicDeviceInfo) -> AquareaDevice: ...

    # — UrlsMixin —
    def _get_group_url(self) -> str: ...
    def _get_device_status_url(self, guid) -> str: ...
    def _get_device_status_now_url(self, guid) -> str: ...
    def _get_device_status_control_url(self) -> str: ...
    def _get_device_history_url(self) -> str: ...
    def _get_aquarea_request_url(self) -> str: ...
    def _get_agreement_status_url(self, type_id: int) -> str: ...
    def _get_agreement_accept_url(self) -> str: ...
    def _get_agreement_documents_url(self, type_id: int | None, language: int, include_content: bool) -> str: ...
    def _get_agreement_status_v2_url(self, type_id: int | None = None) -> str: ...
