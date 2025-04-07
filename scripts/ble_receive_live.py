import asyncio
import logging
import os
import sys
import threading
import numpy as np
import scipy as sp
from bleak import BleakClient, BleakScanner
from matplotlib import pyplot as plt
from datetime import datetime
from functools import partial
import hdf5storage as h5
from matplotlib.animation import FuncAnimation

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
            print(f"X: {raw_x}  Y: {y}  Z: {raw_z}")

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
    await asyncio.sleep(1)
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

def plot_accel_live(captured_data, fs=50.0, buffer_sec=3):
    from matplotlib.animation import FuncAnimation
    import matplotlib.pyplot as plt
    import numpy as np
    import time as time_module  # avoid conflict with "time" array

    buffer_size = int(fs * buffer_sec)

    fig, (ax_x, ax_y, ax_z) = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    fig.suptitle('Real-time Acceleration Data')

    line_x, = ax_x.plot([], [], color='r', label='X-axis')
    line_y, = ax_y.plot([], [], color='g', label='Y-axis')
    line_z, = ax_z.plot([], [], color='b', label='Z-axis')

    for ax, label in zip([ax_x, ax_y, ax_z], ['X', 'Y', 'Z']):
        ax.set_ylabel(f'{label} (g)')
        ax.set_ylim(-GRAVITY, GRAVITY)
        ax.grid(True)
        ax.legend(loc='upper right')

    ax_z.set_xlabel('Time (s)')

    start_time = time_module.time()  # reference time for live timestamps

    def update(frame):
        # Get raw data
        raw_x = captured_data['raw_x'][-buffer_size:]
        raw_y = captured_data['raw_y'][-buffer_size:]
        raw_z = captured_data['raw_z'][-buffer_size:]
        n = len(raw_x)

        if n == 0:
            return line_x, line_y, line_z

        # Convert to g
        x_vals = convert_values(raw_x)
        y_vals = convert_values(raw_y)
        z_vals = convert_values(raw_z)

        # Generate live time axis (in seconds since start)
        now = time_module.time()
        t_vals = np.linspace(now - n/fs, now, n)

        # Update plots
        line_x.set_data(t_vals, x_vals)
        line_y.set_data(t_vals, y_vals)
        line_z.set_data(t_vals, z_vals)

        ax_x.set_xlim(t_vals[0], t_vals[-1])
        ax_y.set_xlim(t_vals[0], t_vals[-1])
        ax_z.set_xlim(t_vals[0], t_vals[-1])

        return line_x, line_y, line_z

    ani = FuncAnimation(fig, update, interval=100, cache_frame_data=False)
    plt.tight_layout()
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




async def eventCap_live(fs=50.0, buffer_sec=3):
    device = await discover_device()
    if device is None:
        logger.error("Target BLE device not found. Exiting.")
        return
    client = await connect_device(device)

    if client is None or not client.is_connected:
        logger.error("BLE client failed to connect.")
        return

    captured_data = {'raw_x': [], 'raw_y': [], 'raw_z': []}

    # Define a wrapper to handle notifications
    # async def ble_loop():
    #     await client.start_notify(UART_UUID, lambda s, d: notification_handler(s, d, captured_data))
    #     try:
    #         while True:
    #             await asyncio.sleep(0.1)
    #     finally:
    #         await client.stop_notify(UART_UUID)
    #         await client.disconnect()
    #         logger.info("BLE client disconnected.")

    # # Start BLE reading in a background thread using asyncio
    # loop = asyncio.get_event_loop()
    # loop.create_task(ble_loop())
    await client.start_notify(UART_UUID, lambda sender, data: notification_handler(sender, data, captured_data))

    # Run plotting in the MAIN THREAD
    plot_accel_live(captured_data, fs=fs, buffer_sec=buffer_sec)


if __name__ == "__main__":
    try:
        asyncio.run(eventCap_live())  # or eventCap_live()
    except KeyboardInterrupt:
        print("Interrupted by user.")
        sys.exit(0)
