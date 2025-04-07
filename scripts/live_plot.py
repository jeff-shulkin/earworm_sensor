import asyncio
import logging
import os
import threading
import numpy as np
import scipy as sp
from bleak import BleakClient, BleakScanner
from matplotlib import pyplot as plt
from matplotlib.animation import FuncAnimation
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
SAMPLE_RATE = 50

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Plot setup
fig, ax = plt.subplots(figsize=(10, 5))
time_window = 30  # seconds
buffer_size = time_window * SAMPLE_RATE
time_axis = np.linspace(-time_window, 0, buffer_size)


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

            # Rolling buffer
            
            captured_data['raw_x'].append(raw_x)
            captured_data['raw_y'].append(raw_y)
            captured_data['raw_z'].append(raw_z)

    except Exception as e:
        logger.error(f"Error in notification handler: {e}")

async def connect_device(device):
    client = BleakClient(device.address)
    await client.connect()
    logger.info(f"Connected to {device.name} ({device.address})")
    services = await client.get_services()
    for service in services:
        for char in service.characteristics:
            logger.info(f"Service: {service.uuid}, Characteristic: {char.uuid}, Properties: {char.properties}")

    return client

async def dump_packets(client):
    captured_data = {'raw_x': [], 'raw_y': [], 'raw_z': []}

    await client.start_notify(UART_UUID, lambda sender, data: notification_handler(sender, data, captured_data))
    await asyncio.sleep(1)

    await client.stop_notify(UART_UUID)

    return captured_data

def convert_values(raw_values, resolution=14):
    min_val = 2**(resolution-1)
    max_val = 2**resolution-1
    scale_factor = (2 * GRAVITY) / (max_val - min_val)

    return [val * scale_factor for val in raw_values]

def update_plot(frame):
    """ Updates the plot with the latest data. """
    if len(captured_data['raw_x']) > buffer_size:
        captured_data['raw_x'] = captured_data['raw_x'][-buffer_size:]
        captured_data['raw_y'] = captured_data['raw_y'][-buffer_size:]
        captured_data['raw_z'] = captured_data['raw_z'][-buffer_size:]

    x_vals = convert_values(captured_data['raw_x'])
    y_vals = convert_values(captured_data['raw_y'])
    z_vals = convert_values(captured_data['raw_z'])

    x_line.set_ydata(np.pad(x_vals, (buffer_size - len(x_vals), 0), 'constant'))
    y_line.set_ydata(np.pad(y_vals, (buffer_size - len(y_vals), 0), 'constant'))
    z_line.set_ydata(np.pad(z_vals, (buffer_size - len(z_vals), 0), 'constant'))

    return x_line, y_line, z_line


def ble_capture():
    """ Runs the asyncio event loop for BLE capture. """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    device = loop.run_until_complete(discover_device())
    client = loop.run_until_complete(connect_device(device))
    if device:
        loop.run_until_complete(dump_packets())
    loop.close()

def plot_live_data():
    capture_thread = threading.Thread(target=ble_capture, daemon=True)
    capture_thread.start()

    # Start the animation
    ani = FuncAnimation(
        fig, update,
        interval=50,  # ms between plot updates
        blit=False
    )
    plt.show()

if __name__ == "__main__":
    plot_live_data()
