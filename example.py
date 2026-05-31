"""Example script demonstrating how to use aio-panasonic-comfort-cloud."""

import argparse
import asyncio
import logging
import os

import aiohttp

from aio_panasonic_comfort_cloud import ApiClient, constants
from aio_panasonic_comfort_cloud.exceptions import AgreementNotAcceptedError


def parse_args():
    parser = argparse.ArgumentParser(
        description="Test the aio-panasonic-comfort-cloud library."
    )
    parser.add_argument(
        "-u", "--username",
        default=os.getenv("PANASONIC_USERNAME"),
        help="Panasonic Comfort Cloud username (email). "
             "Can also be set via PANASONIC_USERNAME env var.",
    )
    parser.add_argument(
        "-p", "--password",
        default=os.getenv("PANASONIC_PASSWORD"),
        help="Panasonic Comfort Cloud password. "
             "Can also be set via PANASONIC_PASSWORD env var.",
    )
    parser.add_argument(
        "--agreements-only",
        action="store_true",
        help="Only check and accept pending agreements, then exit (no device operations).",
    )
    return parser.parse_args()


async def main(username: str, password: str, agreements_only: bool = False):
    # Configure logging
    logging.basicConfig(level=logging.INFO)

    async with aiohttp.ClientSession() as session:
        client = ApiClient(username, password, session)

        try:
            # Start the session (authenticate and fetch devices)
            # If 2FA is enabled, you may need to provide an OTP code:
            # await client.start_session(otp_code="123456")
            await client.start_session()

            # --- Agreement / terms acceptance check ---
            if agreements_only:
                print("Checking agreement status...")
                for type_id in (client.AGREEMENT_TYPE_TERMS,
                                client.AGREEMENT_TYPE_PRIVACY):
                    status = await client.check_agreement_status(type_id)
                    type_name = {1: "Terms & Conditions",
                                 2: "Privacy Policy"}.get(type_id, f"Type {type_id}")
                    print(f"  {type_name}: {'accepted' if status == 1 else 'NOT accepted'}")

                try:
                    await client.ensure_all_agreements_accepted()
                    print("All agreements are now accepted.")
                except AgreementNotAcceptedError as ex:
                    print(f"Some agreements could not be auto-accepted: {ex}")
                return  # Exit early — no device operations

            # Get list of devices
            devices = client.get_devices()
            print(f"Found {len(devices)} device(s):")

            for device_info in devices:
                print(f"\n  Device: {device_info.name}")
                print(f"    ID:     {device_info.id}")
                print(f"    GUID:   {device_info.guid}")
                print(f"    Group:  {device_info.group}")
                print(f"    Model:  {device_info.model}")

                # Get full device status
                device = await client.get_device(device_info)
                params = device.parameters

                print(f"    Power:            {params.power.name}")
                print(f"    Mode:             {params.mode.name}")
                print(f"    Fan Speed:        {params.fan_speed.name}")
                print(f"    Target Temp:      {params.target_temperature}°C")
                print(f"    Inside Temp:      {params.inside_temperature}°C")
                print(f"    Horizontal Swing: {params.horizontal_swing_mode.name}")
                print(f"    Vertical Swing:   {params.vertical_swing_mode.name}")

            # --- Example: Turn on a device and set temperature ---
            if devices:
                first_device_info = devices[0]
                device = await client.get_device(first_device_info)

                # Build changes using ChangeRequestBuilder (fluent API)
                from aio_panasonic_comfort_cloud import ChangeRequestBuilder

                builder = ChangeRequestBuilder(device)
                builder.set_power_mode(constants.Power.On)
                builder.set_hvac_mode(constants.OperationMode.Cool)
                builder.set_target_temperature(24)
                builder.set_fan_speed(constants.FanSpeed.Auto)

                if builder.has_changes:
                    # Apply the changes
                    await client.set_device_raw(device, builder.build())
                    print(f"\n  Updated {device.info.name}: Power=On, Mode=Cool, Temp=24°C")

                    # Refresh device status to confirm
                    await client.try_update_device(device)
                    print(f"    New power state: {device.parameters.power.name}")
                    print(f"    New mode:        {device.parameters.mode.name}")
                    print(f"    New temp:        {device.parameters.target_temperature}°C")

            # --- Example: Get energy history ---
            if devices:
                first_device_info = devices[0]
                from datetime import date

                today = date.today().strftime("%Y%m%d")
                history = await client.history(
                    first_device_info.id, constants.DataMode.Day, today
                )
                if history:
                    print(f"\n  Energy history for {first_device_info.name} (today):")
                    print(f"    {history}")

        finally:
            # Clean up the session
            await client.stop_session()


if __name__ == "__main__":
    args = parse_args()

    if not args.username or not args.password:
        print("Error: username and password are required.")
        print("Pass them as arguments (-u / -p) or set PANASONIC_USERNAME / PANASONIC_PASSWORD env vars.")
        raise SystemExit(1)

    asyncio.run(main(args.username, args.password, agreements_only=args.agreements_only))
