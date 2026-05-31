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

## 2FA / MFA Support

If your account has two-factor authentication enabled, pass the OTP code:

```python
await client.start_session(otp_code="123456")
```

## Full Example

See [`example.py`](example.py) for a complete working example.

## License

MIT
