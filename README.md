# aio-panasonic-comfort-cloud
**aio-panasonic-comfort-cloud**: Asynchronous Python library for Panasonic Comfort Cloud API

This library provides asynchronous access to the Panasonic Comfort Cloud API, enabling developers to interact with Panasonic air conditioning units.

## Installation

```bash
pip install aio-panasonic-comfort-cloud
```

## Quick Start

### Basic Usage

```python
import asyncio
import aiohttp
from aio_panasonic_comfort_cloud import ApiClient

async def main():
    async with aiohttp.ClientSession() as session:
        client = ApiClient("your_email@example.com", "your_password", session)
        
        # Start the session (authenticate and fetch devices)
        await client.start_session()
        
        # Get list of devices
        devices = client.get_devices()
        
        for device_info in devices:
            print(f"Device: {device_info.name}")
            
            # Get full device status
            device = await client.get_device(device_info)
            params = device.parameters
            
            print(f"  Power:       {params.power.name}")
            print(f"  Mode:        {params.mode.name}")
            print(f"  Fan Speed:   {params.fan_speed.name}")
            print(f"  Target Temp: {params.target_temperature}°C")
            print(f"  Inside Temp: {params.inside_temperature}°C")
        
        # Clean up the session
        await client.stop_session()

asyncio.run(main())
```

### Controlling a Device

Use `ChangeRequestBuilder` for a fluent API to build and apply changes:

```python
from aio_panasonic_comfort_cloud import ApiClient, ChangeRequestBuilder, constants

# ... (start session as above)

device = await client.get_device(devices[0])

builder = ChangeRequestBuilder(device)
builder.set_power_mode(constants.Power.On)
builder.set_hvac_mode(constants.OperationMode.Cool)
builder.set_target_temperature(24)
builder.set_fan_speed(constants.FanSpeed.Auto)

if builder.has_changes:
    await client.set_device_raw(device, builder.build())
```

### Avoiding Unwanted Power-On

Some changes (swing direction, hvac mode, target temperature, eco mode) require the
device to be on to take effect, so by default the library silently powers the device
on for you if it's currently off. If you'd rather not have those changes wake up an
AC that was deliberately left off, construct the client with `auto_power_on=False`.
While the device is off, matching changes are buffered instead of sent; they're
applied together the next time the device is explicitly powered on.

```python
client = ApiClient("your_email@example.com", "your_password", session, auto_power_on=False)

# ... device is off ...
builder = client.new_change_request(device)  # wires auto_power_on from the client
builder.set_horizontal_swing(constants.AirSwingLR.Left)
await client.set_device_raw(device, builder.build())  # buffered, nothing sent yet

# later, when the device is turned on the buffered swing change is merged in and sent together
builder = client.new_change_request(device)
builder.set_power_mode(constants.Power.On)
await client.set_device_raw(device, builder.build())
```

Use `client.has_pending_changes(device)` to check whether a device has buffered
changes waiting to be applied.

### Available Enums

| Category | Values |
|---|---|
| **Power** | `Off`, `On` |
| **OperationMode** | `Auto`, `Dry`, `Cool`, `Heat`, `Fan` |
| **FanSpeed** | `Auto`, `Low`, `LowMid`, `Mid`, `HighMid`, `High` |
| **EcoMode** | `Auto`, `Powerful`, `Quiet` |
| **AirSwingUD** | `Auto`, `Up`, `UpMid`, `Mid`, `DownMid`, `Down`, `Swing` |
| **AirSwingLR** | `Auto`, `Left`, `LeftMid`, `Mid`, `RightMid`, `Right`, `Unavailable` |
| **NanoeMode** | `Unavailable`, `Off`, `On`, `ModeG`, `All` |

### ChangeRequestBuilder Methods

- `set_power_mode(value)` — Set power on/off
- `set_hvac_mode(value)` — Set operation mode (cool, heat, etc.)
- `set_target_temperature(value)` — Set target temperature in °C
- `set_fan_speed(value)` — Set fan speed
- `set_eco_mode(value)` — Set eco mode
- `set_horizontal_swing(value)` — Set horizontal air swing
- `set_vertical_swing(value)` — Set vertical air swing
- `set_nanoe_mode(value)` — Set Nanoe mode
- `set_eco_navi_mode(value)` — Set EcoNavi mode
- `set_eco_function_mode(value)` — Set EcoFunction mode

### Getting Energy History

```python
from datetime import date
from aio_panasonic_comfort_cloud import constants

today = date.today().strftime("%Y%m%d")
history = await client.history(device_info.id, constants.DataMode.Day, today)
```

## Aquarea (Air to Water heat pump) Support

Aquarea units show up in the same account/group listing as air conditioners,
but expose a different status shape (hot water tank + heating/cooling zones
instead of a single `parameters` object), so they're kept separate from
`get_devices()`:

```python
devices = client.get_devices()          # air conditioners
aquarea_devices = client.aquarea_devices  # Aquarea heat pumps

for device_info in aquarea_devices:
    device = await client.get_aquarea_device(device_info)
    params = device.parameters

    print(f"{device_info.name}: {params.operation_status.name} / {params.operation_mode.name}")
    if params.has_tank:
        print(f"  Tank: {params.tank.temperature}°C -> {params.tank.heat_set}°C")
    for zone in params.zones:
        print(f"  Zone {zone.id} ({zone.name}): {zone.temperature}°C -> {zone.heat_set}°C")

    # Refresh status in place
    await client.try_update_aquarea_device(device)
```

Controlling a unit:

```python
from aio_panasonic_comfort_cloud import constants

await client.set_aquarea_operation_status(device_info, constants.AquareaOperationStatus.On)
await client.set_aquarea_operation_mode(device_info, constants.AquareaUpdateOperationMode.Heat)
await client.set_aquarea_tank_temperature(device_info, 55)
await client.set_aquarea_tank_operation_status(device_info, constants.AquareaOperationStatus.On)
await client.set_aquarea_zone_temperature(device_info, zone_id=1, temperature=22, mode="heat")
await client.set_aquarea_quiet_mode(device_info, constants.AquareaQuietMode.Level1)
await client.set_aquarea_force_dhw(device_info, constants.AquareaForceDHW.On)
```

Eco/Comfort "special status" applies a per-zone temperature offset on top of
the current setpoint rather than being a simple flag, so setting it needs
the full `AquareaDevice` (not just its `PanasonicDeviceInfo`) to know the
current setpoints/status to offset from:

```python
device = await client.get_aquarea_device(device_info)
await client.set_aquarea_special_status(device, constants.AquareaSpecialStatus.Eco)
# ... or constants.AquareaSpecialStatus.Comfort, or None to turn it off
```

Energy consumption/cost history (heat/cool/tank breakdown) uses a separate
endpoint from air conditioners, with its own `AquareaDataMode` (Day/Month/Year
— no "Week", and different values from the AC-only `DataMode`):

```python
from datetime import date

today = date.today().strftime("%Y%m%d")
consumption = await client.async_get_aquarea_consumption(
    device_info, constants.AquareaDataMode.Day, today
)
for entry in consumption:
    print(f"{entry.data_time}: heat={entry.heat_consumption}kWh cool={entry.cool_consumption}kWh "
          f"tank={entry.tank_consumption}kWh total={entry.total_consumption}kWh")
```

`set_aquarea_special_status` is unverified/best-effort like the HWS control
methods above — see its docstring for why.

## HWS (Standalone Heat Pump Hot Water Tank) Support

Some accounts have a standalone hot water heat pump (e.g. an HE-UM40CR),
distinct from an Aquarea combi unit — it has no heating/cooling zones, just
a tank. These report `deviceType: "11"` and, confusingly, *do* have a
`parameters` object like an air conditioner, but with tank-specific fields
(`tankTemperature`, `hpuOperationStatus`, `operationMode`, `boostMode`)
instead — and the usual `deviceStatus`/`deviceHistoryData` calls reject them
with a 403. They're kept separate from `get_devices()`/`aquarea_devices`:

```python
hws_devices = client.hws_devices

for device_info in hws_devices:
    device = client.get_hws_device(device_info)  # no network call — built
                                                   # from the group listing
    params = device.parameters
    print(f"{device_info.name}: {params.tank_temperature}°C, boost={params.boost_mode.name}")

    # Refresh (re-fetches /device/group, there's no per-device status call)
    await client.try_update_hws_device(device)
```

Reading status this way is confirmed working against a real device. Control
(`set_hws_tank_temperature`, `set_hws_boost_mode`, `set_hws_operation_status`,
`set_hws_operation_mode`) targets `/device/a2wInfoUpdate`, reported from a
Comfort Cloud app capture but **not yet verified against a live account** —
please open an issue if it doesn't work as-is.

## Terms / Privacy Policy Agreements

Panasonic occasionally updates its Terms of Use, Privacy Policy or Cookie
Policy; when that happens, API calls start failing with error code `4103`
until the account re-accepts them. You can fetch and handle this yourself:

```python
# Fetch the current documents (set include_content=True to get the full text)
documents = await client.get_agreement_documents(include_content=True)
for doc in documents:
    print(doc["type"], doc["version"], doc.get("content", "")[:80])

# See what's already been accepted on this account
accepted = await client.get_agreement_status()

# Auto-accept anything outdated/missing (Terms, Privacy, Cookie Policy —
# the Turkey-only Service Agreement is intentionally excluded, matching
# the official app's behavior of only surfacing it to a subset of accounts)
await client.ensure_all_agreements_accepted()
```

This isn't called automatically on login — auto-accepting legal agreements
is a decision your application should make deliberately, not something the
library does silently. A typical pattern is to catch
`AgreementNotAcceptedError` from `start_session()`/`_get_groups()` and call
`ensure_all_agreements_accepted()` (or show the fetched document text to the
user first) in response.

## 2FA / MFA Support

If your account has two-factor authentication enabled, `start_session()`
raises `MFARequiredError` instead of logging in. Catch it, prompt the user
for the OTP code from their authenticator app, and retry with it:

```python
from aio_panasonic_comfort_cloud.exceptions import MFARequiredError

try:
    await client.start_session()
except MFARequiredError:
    otp_code = input("Enter the 2FA code: ")
    await client.start_session(otp_code=otp_code)
```

## Alternative: Browser-Based Authentication

`start_session()` drives Panasonic's login page itself — it POSTs your
credentials and scrapes the resulting HTML/redirects, which has to correctly
handle whatever Auth0 renders for every connection type (password, MFA,
social login, ...). As an alternative that sidesteps all of that, you can let
a real browser (a WebView, the system browser, etc.) handle the login instead
and just hand the result back to the library:

```python
# 1. Build the URL and open it in any browser
auth_url, code_verifier = client.get_browser_authorization_url()
print(f"Open this URL and log in: {auth_url}")

# 2. After login, the browser is redirected to a URL starting with
#    "panasonic-iot-cfc://...callback?code=...". Capture that redirect
#    (however your application observes it — a WebView navigation listener,
#    a custom URI scheme handler, pasting it in, etc.) and finish the login:
redirect_url = input("Paste the redirect URL here: ")
await client.complete_browser_authentication(redirect_url, code_verifier)

# From here on, the client behaves exactly as if start_session() had been
# called — get_devices(), get_device(), etc. all work normally.
devices = client.get_devices()
```

This is entirely separate from `start_session()`/`authenticate()` — it
doesn't change how the default username/password flow behaves, it's just
another way to obtain the same tokens. Because Auth0's own hosted page
handles the actual login, this path naturally supports MFA, social login,
etc. without any special-casing in the library.

## Full Example

See [`example.py`](example.py) for a complete working example.

## License

MIT
