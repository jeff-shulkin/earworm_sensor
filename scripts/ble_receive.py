import asyncio
import logging
import os

import numpy as np
import scipy as sp
from bleak import BleakClient, BleakScanner
from matplotlib import pyplot as plt

EARWORM_MAC = "EF:90:1:F7:43:EA"
EARWORM_NAME = "Nordic_UART_Service"
UART_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

DATA_OFFSET = 0

FRAME_SIZE = 6
XYZ_SIZE = 2
X_OFFSET = 0
Y_OFFSET = 2
Z_OFFSET = 4

XYZ_SENSITIVITY = 0.001

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
        logger.info(
            f"Discovered device: {device.name} ({device.address})"
        )  # Log all discovered devices
        if device.address == EARWORM_MAC or device.name == EARWORM_NAME:
            logger.info(f"Found target device: {device.name} ({device.address})")
            return device
    return None

# Define the notification handler function
def notification_handler(sender, data):
    """Callback for received BLE notifications"""
    logger.info(f"Notification from {sender}: {data}")

async def connect_and_dump_packets(device):
    async with BleakClient(device.address) as client:
        logger.info(f"Connected to {device.name} ({device.address})")

        services = await client.get_services()
        for service in services:
            for char in service.characteristics:
                logger.info(f"Service: {service.uuid}, Characteristic: {char.uuid}, Properties: {char.properties}")
        # Here we assume the device has some service for data transfer.
        # You can adjust the code based on the specific service and characteristics of the target device.

        # This part dumps all incoming packets
        await client.start_notify(UART_UUID, notification_handler)
        asyncio.sleep(5)
        # Keep receiving notifications
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("Stopping notifications.")
        
        await client.stop_notify(UART_UUID)
        #while True:
            # Replace with an actual characteristic UUID you're interested in, or dump all notifications.
            # Here we assume a generic way of receiving packets, but you should use the specific service UUIDs for your device.
        #    try:
        #        # For the sake of simplicity, we'll print received data as raw bytes
        #        data = await client.read_gatt_char(UART_UUID)
        #        metadata = data[0:DATA_OFFSET]
        #        x, y, z = []
        #        idx = DATA_OFFSET
        #        while idx < len(data):
        #            x.append(XYZ_SENSITIVITY * data[idx + X_OFFSET : idx + XYZ_SIZE])
        #            y.append(XYZ_SENSITIVITY * data[idx + Y_OFFSET : idx + XYZ_SIZE])
        #            z.append(XYZ_SENSITIVITY * data[idx + Z_OFFSET : idx + XYZ_SIZE])
        #            idx += 6

        #        plt.plot(x, y, z)
                # logger.info(f"Received packet: {data.hex()}")
        #    except Exception as e:
        #        logger.error(f"Error while receiving data: {e}")
        #        break


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
