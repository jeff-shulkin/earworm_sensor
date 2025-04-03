import asyncio
import logging
import os
import threading
import numpy as np
import scipy as sp
from bleak import BleakClient, BleakScanner
from matplotlib import pyplot as plt
from datetime import datetime
from functools import partial
import hdf5storage as h5

EARWORM_MAC = "EF:90:1:F7:43:EA"
EARWORM_NAME = "earworm_ble"
UART_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

DATA_OFFSET = 0

FRAME_SIZE = 6
XYZ_SIZE = 2
X_OFFSET = 0
Y_OFFSET = 2
Z_OFFSET = 4

XYZ_SENSITIVITY = 0.001
RANGE=2
GRAVITY = 9.8

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
def notification_handler(sender, data, captured_data):
    """Callback for received BLE notifications"""
    logger.info(f"Notification from {sender}")
    logger.info(f"Packet length: {len(data)}")
    try:
        for i in range(0, len(data), FRAME_SIZE):
            frame = data[i:i+FRAME_SIZE]

            raw_x = int.from_bytes(frame[X_OFFSET:X_OFFSET + XYZ_SIZE], byteorder='little', signed=True)
            raw_y = int.from_bytes(frame[Y_OFFSET:Y_OFFSET + XYZ_SIZE], byteorder='little', signed=True)
            raw_z = int.from_bytes(frame[Z_OFFSET:Z_OFFSET + XYZ_SIZE], byteorder='little', signed=True)

            captured_data['raw_x'].append(raw_x)
            captured_data['raw_y'].append(raw_y)
            captured_data['raw_z'].append(raw_z)

    except Exception as e:
        logger.error(f"Error in notification handler: {e}")

async def connect_and_dump_packets(device, capture_time_sec=60.0):
    captured_data = {'raw_x': [], 'raw_y': [], 'raw_z': []}
    async with BleakClient(device.address) as client:
        logger.info(f"Connected to {device.name} ({device.address})")

        services = await client.get_services()
        for service in services:
            for char in service.characteristics:
                logger.info(f"Service: {service.uuid}, Characteristic: {char.uuid}, Properties: {char.properties}")

        # This part dumps all incoming packets
        print(f"Starting data capture...")
        await client.start_notify(UART_UUID, partial(notification_handler, captured_data=captured_data))
        await asyncio.sleep(5)
        await asyncio.sleep(capture_time_sec)
        await client.stop_notify(UART_UUID)
        print(f"Data capture complete!")

    return captured_data

async def connect_device(device):
    client = BleakClient(device.address)
    await client.connect()
    logger.info(f"Connected to {device.name} ({device.address})")
    services = await client.get_services()
    for service in services:
        for char in service.characteristics:
            logger.info(f"Service: {service.uuid}, Characteristic: {char.uuid}, Properties: {char.properties}")

    return client

async def dump_packets(client, capture_time_sec=60.0):
    captured_data = {'raw_x': [], 'raw_y': [], 'raw_z': []}

    await client.start_notify(UART_UUID, lambda sender, data: notification_handler(sender, data, captured_data))
    await asyncio.sleep(1)
    await asyncio.sleep(capture_time_sec)
    await client.stop_notify(UART_UUID)

    return captured_data

def convert_values(raw_values, resolution=14):
    min_val = 2**(resolution-1)
    max_val = 2**resolution-1
    scale_factor = (2 * GRAVITY) / (max_val - min_val)

    return [val * scale_factor for val in raw_values]

def plot_accel(accel_values, fs=50.0):
    x_vals = accel_values['accel_x']
    y_vals = accel_values['accel_y']
    z_vals = accel_values['accel_z']

    #print(f"x_val len: {len(x_vals)}")
    #print(f"y_val len: {len(x_vals)}")
    #print(f"z_val len: {len(x_vals)}")

    time = np.arange(len(x_vals)) / fs

    plt.figure(figsize=(10,5))

    plt.plot(time, x_vals, label='X-axis', color='r')
    plt.plot(time, y_vals, label='Y-axis', color='g')
    plt.plot(time, z_vals, label='Z-axis', color='b')


    plt.xlabel('Time (s)')
    plt.ylabel('Acceleration (g)')
    plt.title('Unaltered acceleration data')
    plt.legend()
    plt.grid(True)
    plt.show()

async def eventCap(capture_time_sec=60.0, prefix='dataCapture', sample_rate=50,
                   timestamp_tick=20000, returnDict=None):

    # Set up data collection
    data = {}
    data['timeinfo'] = {}
    data['timeinfo']['tickHz'] = 20000
    data['timeinfo']['timezone'] = datetime.now().astimezone().tzname()
    data['Fs'] = sample_rate

    # Discover and connect to target device
    device = await discover_device()
    client = await connect_device(device)

    print(f"Starting data capture...")
    start_time = datetime.now().astimezone()
    captured = await dump_packets(client, capture_time_sec=60.0)
    print(f"Data capture complete!")

    #print(f"Captured data: {captured}")

    data['sData'] = {}
    data['sData']['Time'] = np.arange(len(captured['raw_x'])) * data['timeinfo']['tickHz'] / sample_rate
    data['sData']['accel_x'] = convert_values(captured['raw_x'])
    data['sData']['accel_y'] = convert_values(captured['raw_y'])
    data['sData']['accel_z'] = convert_values(captured['raw_z'])

    # Save data
    filename = prefix + start_time.strftime('-%Y-%m-%dT%H-%M-%S') + '.mat'

    print(f"Saving to file \"{filename}\"")
#    h5.write(data, filename)

    plot_accel(data['sData'])

    if returnDict is not None:
        returnDict['filename'] = filename
        returnDict['sampleCount'] = len(captured['raw_x'])
        returnDict['startTime'] = start_time

if __name__ == "__main__":
    asyncio.run(eventCap(60.0))
