<<<<<<< HEAD
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
import serial

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


def read_serial_pulse(port='COM3', baudrate=9600, pulse_data=None, duration=60):
    try:
        ser = serial.Serial(port, baudrate, timeout=1)
        print(f"Serial port {port} opened.")
        start_time = time.time()

        while time.time() - start_time < duration:
            line = ser.readline().decode('utf-8').strip()
            if line.isdigit():
                value = int(line)
                timestamp = time.time()
                pulse_data['timestamps'].append(timestamp)
                pulse_data['values'].append(value)
    except Exception as e:
        print(f"Error reading from serial: {e}")

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

def plot_accel_n_pulse(accel_values, pulse_data=None, fs=50.0):
    x_vals = accel_values['accel_x']
    y_vals = accel_values['accel_y']
    z_vals = accel_values['accel_z']
    time_vals = np.arange(len(x_vals)) / fs

    plt.figure(figsize=(12, 8))

    plt.subplot(4, 1, 1)
    plt.plot(time_vals, x_vals, 'r', label='X-axis')
    plt.ylabel('Accel X (g)')
    plt.grid()
    plt.legend()

    plt.subplot(4, 1, 2)
    plt.plot(time_vals, y_vals, 'g', label='Y-axis')
    plt.ylabel('Accel Y (g)')
    plt.grid()
    plt.legend()

    plt.subplot(4, 1, 3)
    plt.plot(time_vals, z_vals, 'b', label='Z-axis')
    plt.ylabel('Accel Z (g)')
    plt.grid()
    plt.legend()

    if pulse_data:
        pulse_t = np.array(pulse_data['timestamps'])
        pulse_y = np.array(pulse_data['values'])

        # Normalize time axis relative to pulse start time
        pulse_t -= pulse_t[0]
        plt.subplot(4, 1, 4)
        plt.plot(pulse_t, pulse_y, color='purple', label='PulseSensor')
        plt.xlabel('Time (s)')
        plt.ylabel('Pulse (a.u.)')
        plt.grid()
        plt.legend()

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

    pulse_data = {'timestamps': [], 'values': []}
    pulse_thread = threading.Thread(target=read_serial_pulse,
                                    args=('COM3', 9600, pulse_data, capture_time_sec),
                                    daemon=True)
    pulse_thread.start()

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

    pulse_thread.join()  # Wait for pulse thread to finish

    plot_accel_n_pulse(data['sData'], pulse_data=pulse_data)

    # plot_accel(data['sData'])

    if returnDict is not None:
        returnDict['filename'] = filename
        returnDict['sampleCount'] = len(captured['raw_x'])
        returnDict['startTime'] = start_time

if __name__ == "__main__":
    asyncio.run(eventCap(60.0))
=======
import asyncio
import logging
import os
import threading
import torch
import numpy as np
import scipy as sp
from bleak import BleakClient, BleakScanner
from matplotlib import pyplot as plt
from datetime import datetime
from functools import partial
import hdf5storage as h5

STORAGE_OPTIONS = h5.Options(
    store_python_metadata=True,
    matlab_compatible=True,
    structured_numpy_ndarray_as_struct=True,
    convert_numpy_str_to_utf16=True,
    structs_as_dicts=True,
)

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
WINDOW_SIZE = 64
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_model(filename):
    # Load in the motion detection model
    model = torch.load(filename)
    return model

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

async def connect_device(device):
    client = BleakClient(device.address)
    await client.connect()
    if client._backend.__class__.__name__ == "BleakClientBlueZDBus":
        await client._backend._acquire_mtu()
    print("MTU:", client.mtu_size)
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
    x_vals = sp.signal.detrend(accel_values['accel_x'])
    y_vals = sp.signal.detrend(accel_values['accel_y'])
    z_vals = sp.signal.detrend(accel_values['accel_z'])

    time = np.arange(len(x_vals)) / fs

    plt.figure(figsize=(10,5))

    plt.plot(time, x_vals, label='X-axis', color='r')
    plt.plot(time, y_vals, label='Y-axis', color='g')
    plt.plot(time, z_vals, label='Z-axis', color='b')


    plt.xlabel('Time (s)')
    plt.ylabel('Acceleration (g)')
    plt.title(' Raw Acceleration Data')
    plt.legend()
    plt.grid(True)
    plt.show()

def plot_motion_results(accel_data, fs=50.0):
   ''' Run motion detection model on sliding window of accelerometer data'''
   pass

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
    #h5.writes(data, filename, options=STORAGE_OPTIONS)

    # Plot accelerometer data
    plot_accel(data['sData'])
    plot_motion_results(data['sData'])

    if returnDict is not None:
        returnDict['filename'] = filename
        returnDict['sampleCount'] = len(captured['raw_x'])
        returnDict['startTime'] = start_time

if __name__ == "__main__":
    asyncio.run(eventCap(60.0))
>>>>>>> f079735 (segmenting ble packets based on MTU size)
