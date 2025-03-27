import numpy as np
import scipy as sp
import os
import asyncio
import bleak
import logging

EARWORM_MAC = "EF:90:1:F7:43:EA"
EARWORM_NAME = "earworm_ble"

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def discover_device():
    logger.info("Scanning for BLE devices...")

    # Scan for available devices
    devices = await BleakScanner.discover()
    logger.info(f"Found {len(devices)} devices.")

    # Look for the target device by MAC address or name
    for device in devices:
        logger.info(f"Discovered device: {device.name} ({device.address})")  # Log all discovered devices
        if device.address == TARGET_DEVICE_MAC or device.name == TARGET_DEVICE_NAME:
            logger.info(f"Found target device: {device.name} ({device.address})")
            return device
    return None

async def connect_and_dump_packets(device):
    async with BleakClient(device.address) as client:
        logger.info(f"Connected to {device.name} ({device.address})")

        # Here we assume the device has some service for data transfer.
        # You can adjust the code based on the specific service and characteristics of the target device.

        # This part dumps all incoming packets
        while True:
            # Replace with an actual characteristic UUID you're interested in, or dump all notifications.
            # Here we assume a generic way of receiving packets, but you should use the specific service UUIDs for your device.
            try:
                # For the sake of simplicity, we'll print received data as raw bytes
                data = await client.read_gatt_char("your-characteristic-uuid")  # Replace with the actual UUID
                logger.info(f"Received packet: {data.hex()}")
            except Exception as e:
                logger.error(f"Error while receiving data: {e}")
                break

async def main():
    # Discover the target device
    device = await discover_device()

    if device:
        # Connect to the device and start dumping packets
        await connect_and_dump_packets(device)
    else:
        logger.warning("Target device not found.")

if __name__ == "__main__":
    asyncio.run(main())
