import asyncio
import logging
import sys
import threading
import numpy as np
from bleak import BleakClient, BleakScanner
from matplotlib import pyplot as plt
from matplotlib.animation import FuncAnimation
from datetime import datetime
import time as time_module
import time

# BLE configuration
EARWORM_MAC = "EF:90:1:F7:43:EA"
EARWORM_NAME = "earworm_ble"
UART_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

# Frame decoding
FRAME_SIZE = 6
XYZ_SIZE = 2
X_OFFSET = 0
Y_OFFSET = 2
Z_OFFSET = 4

GRAVITY = 9.8

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Shared data dictionary
captured_data = {'raw_x': [], 'raw_y': [], 'raw_z': []}

# Convert raw values to acceleration (g)
def convert_values(raw_values, resolution=14):
    min_val = 2 ** (resolution - 1)
    max_val = 2 ** resolution - 1
    scale_factor = (2 * GRAVITY) / (max_val - min_val)
    return [val * scale_factor for val in raw_values]

# Notification handler
def notification_handler(sender, data, captured_data):
    try:
        for i in range(0, len(data), FRAME_SIZE):
            frame = data[i:i + FRAME_SIZE]
            raw_x = int.from_bytes(frame[X_OFFSET:X_OFFSET + XYZ_SIZE], byteorder='little', signed=True)
            raw_y = int.from_bytes(frame[Y_OFFSET:Y_OFFSET + XYZ_SIZE], byteorder='little', signed=True)
            raw_z = int.from_bytes(frame[Z_OFFSET:Z_OFFSET + XYZ_SIZE], byteorder='little', signed=True)
            captured_data['raw_x'].append(raw_x)
            captured_data['raw_y'].append(raw_y)
            captured_data['raw_z'].append(raw_z)
            # print(f"X: {raw_x}  Y: {raw_y}  Z: {raw_z}")
        
        print(f"data_len = {len(data)} time = {time.time()}")
    except Exception as e:
        logger.error(f"Error in notification handler: {e}")

# Plotting function
def plot_accel_live(captured_data, fs=50.0, buffer_sec=3):
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

    def update(frame):
        raw_x = captured_data['raw_x'][-buffer_size:]
        raw_y = captured_data['raw_y'][-buffer_size:]
        raw_z = captured_data['raw_z'][-buffer_size:]
        n = len(raw_x)

        if n == 0:
            return line_x, line_y, line_z

        x_vals = convert_values(raw_x)
        y_vals = convert_values(raw_y)
        z_vals = convert_values(raw_z)

        now = time_module.time()
        t_vals = np.linspace(now - n / fs, now, n)

        line_x.set_data(t_vals, x_vals)
        line_y.set_data(t_vals, y_vals)
        line_z.set_data(t_vals, z_vals)

        ax_x.set_xlim(t_vals[0], t_vals[-1])
        ax_y.set_xlim(t_vals[0], t_vals[-1])
        ax_z.set_xlim(t_vals[0], t_vals[-1])

        return line_x, line_y, line_z

    ani = FuncAnimation(fig, update, interval=5000, cache_frame_data=False)
    plt.tight_layout()
    plt.show()

# Discover device
async def discover_device():
    logger.info("Scanning for BLE devices...")
    devices = await BleakScanner.discover()
    for device in devices:
        logger.info(f"Discovered device: {device.name} ({device.address})")
        if device.address == EARWORM_MAC or device.name == EARWORM_NAME:
            logger.info(f"Found target device: {device.name} ({device.address})")
            return device
    return None

# Connect device
async def connect_device(device):
    client = BleakClient(device.address)
    try:
        await client.connect()
        await asyncio.sleep(1)
        logger.info(f"Connected to {device.name} ({device.address})")
        return client
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        return None

# BLE capture loop
def run_event_loop(captured_data):
    async def _run():
        device = await discover_device()
        if device is None:
            logger.error("Target BLE device not found.")
            return
        client = await connect_device(device)
        if client is None:
            logger.error("Client connection failed.")
            return

        await client.start_notify(UART_UUID, lambda s, d: notification_handler(s, d, captured_data))
        logger.info("Started notifications.")
        try:
            while True:
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass
        finally:
            await client.stop_notify(UART_UUID)
            await client.disconnect()
            logger.info("Disconnected from BLE device.")

    asyncio.run(_run())

# Start threads
def total(fs=50.0, buffer_sec=3):
    capture_thread = threading.Thread(target=run_event_loop, args=(captured_data,), daemon=True)
    capture_thread.start()

    # Run plot in main thread
    plot_accel_live(captured_data, fs=fs, buffer_sec=buffer_sec)

# Entry point
if __name__ == "__main__":
    try:
        total(50, 3)
    except KeyboardInterrupt:
        print("Interrupted by user.")
        sys.exit(0)
