import asyncio
import logging
import sys
import threading
import numpy as np
from bleak import BleakClient, BleakScanner
from matplotlib import pyplot as plt
from matplotlib.animation import FuncAnimation
import time
import serial
import torch
from motionDetection import MotionDetection

# BLE config
EARWORM_MAC = "EF:90:1:F7:43:EA"
EARWORM_NAME = "earworm_ble"
UART_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
FRAME_SIZE = 6
XYZ_SIZE = 2
X_OFFSET = 0
Y_OFFSET = 2
Z_OFFSET = 4
GRAVITY = 9.8

# Shared data
captured_data = {'raw_x': [], 'raw_y': [], 'raw_z': []}
pulse_data = {'timestamps': [], 'values': []}

# Convert raw int values to g
def convert_values(raw_values, resolution=14):
    min_val = 2 ** (resolution - 1)
    max_val = 2 ** resolution - 1
    scale_factor = (2 * GRAVITY) / (max_val - min_val)
    return [val * scale_factor for val in raw_values]

# BLE frame handler
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
    except Exception as e:
        logging.error(f"Error in notification handler: {e}")

# Live plotting and model inference
def plot_accel_live(captured_data, pulse_data, fs=50.0, buffer_sec=3):
    buffer_size = int(fs * buffer_sec)
    BUFFER_SIZE_MODEL = 128  # must match training
    last_label = "N/A"

    # Load model
    model = MotionDetection(input_channels=3, seq_len=BUFFER_SIZE_MODEL)
    model.load_state_dict(torch.load("motion_model.pth", map_location=torch.device("cpu")))
    model.eval()

    # Set up plot
    fig, (ax_x, ax_y, ax_z, ax_pulse) = plt.subplots(4, 1, figsize=(10, 10), sharex=True)
    fig.suptitle('Real-time Acceleration Data')

    line_x, = ax_x.plot([], [], color='r', label='X-axis')
    line_y, = ax_y.plot([], [], color='g', label='Y-axis')
    line_z, = ax_z.plot([], [], color='b', label='Z-axis')
    line_pulse, = ax_pulse.plot([], [], color='purple', label='PulseSensor')

    for ax, label in zip([ax_x, ax_y, ax_z], ['X', 'Y', 'Z']):
        ax.set_ylabel(f'{label} (g)')
        ax.set_ylim(-GRAVITY, GRAVITY)
        ax.grid(True)
        ax.legend(loc='upper right')

    ax_pulse.set_ylabel('Pulse (a.u.)')
    ax_pulse.set_xlabel('Time (s)')
    ax_pulse.grid(True)
    ax_pulse.legend(loc='upper right')
    ax_z.set_xlabel('Time (s)')
    plt.tight_layout()

    def update(frame):
        nonlocal last_label
        raw_x = captured_data['raw_x'][-buffer_size:]
        raw_y = captured_data['raw_y'][-buffer_size:]
        raw_z = captured_data['raw_z'][-buffer_size:]
        n = len(raw_x)
        if n == 0:
            return line_x, line_y, line_z, line_pulse

        x_vals = convert_values(raw_x)
        y_vals = convert_values(raw_y)
        z_vals = convert_values(raw_z)

        # Run model inference on latest BUFFER_SIZE_MODEL
        if len(x_vals) >= BUFFER_SIZE_MODEL:
            chunk = np.array([x_vals[-BUFFER_SIZE_MODEL:],
                              y_vals[-BUFFER_SIZE_MODEL:],
                              z_vals[-BUFFER_SIZE_MODEL:]])
            chunk_tensor = torch.tensor(chunk[np.newaxis, ...], dtype=torch.float32)
            with torch.no_grad():
                output = model(chunk_tensor)
                prediction = torch.argmax(output, dim=1).item()
                last_label = "GOOD" if prediction == 1 else "BAD"

        now = time.time()
        t_vals = np.linspace(now - n / fs, now, n)
        line_x.set_data(t_vals, x_vals)
        line_y.set_data(t_vals, y_vals)
        line_z.set_data(t_vals, z_vals)
        ax_x.set_xlim(t_vals[0], t_vals[-1])
        ax_y.set_xlim(t_vals[0], t_vals[-1])
        ax_z.set_xlim(t_vals[0], t_vals[-1])

        # PulseSensor update
        pulse_t = pulse_data['timestamps']
        pulse_v = pulse_data['values']
        recent_idx = [i for i, t in enumerate(pulse_t) if t >= now - buffer_sec]
        if recent_idx:
            pulse_t_vals = [pulse_t[i] for i in recent_idx]
            pulse_y_vals = [pulse_v[i] for i in recent_idx]
            line_pulse.set_data(pulse_t_vals, pulse_y_vals)
            ax_pulse.set_xlim(pulse_t_vals[0], pulse_t_vals[-1])
            ax_pulse.set_ylim(min(pulse_y_vals) - 10, max(pulse_y_vals) + 10)

        # Display model prediction on top
        fig.suptitle(f"Live Prediction: {last_label}",
                     fontsize=16,
                     color='green' if last_label == "GOOD" else 'red')
        return line_x, line_y, line_z, line_pulse

    ani = FuncAnimation(fig, update, interval=500, cache_frame_data=False)
    plt.show()

def read_serial_pulse(port='COM3', baudrate=9600, pulse_data=None):
    try:
        ser = serial.Serial(port, baudrate, timeout=1)
        time.sleep(2)
        print(f"Serial port {port} opened.")
        while True:
            line = ser.readline().decode('utf-8').strip()
            if line.isdigit():
                value = int(line)
                timestamp = time.time()
                pulse_data['timestamps'].append(timestamp)
                pulse_data['values'].append(value)
    except Exception as e:
        print(f"Error reading from serial: {e}")

async def discover_device():
    logging.info("Scanning for BLE devices...")
    devices = await BleakScanner.discover()
    for device in devices:
        if device.address == EARWORM_MAC or device.name == EARWORM_NAME:
            return device
    return None

async def connect_device(device):
    client = BleakClient(device.address)
    try:
        await client.connect()
        await asyncio.sleep(1)
        return client
    except Exception as e:
        logging.error(f"Connection failed: {e}")
        return None

def run_event_loop(captured_data):
    async def _run():
        device = await discover_device()
        if device is None:
            print("BLE device not found.")
            return
        client = await connect_device(device)
        if client is None:
            print("BLE client failed.")
            return
        await client.start_notify(UART_UUID, lambda s, d: notification_handler(s, d, captured_data))
        try:
            while True:
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass
        finally:
            await client.stop_notify(UART_UUID)
            await client.disconnect()

    asyncio.run(_run())

def total(fs=50.0, buffer_sec=3):
    capture_thread = threading.Thread(target=run_event_loop, args=(captured_data,), daemon=True)
    pulse_thread = threading.Thread(target=read_serial_pulse, args=('COM3', 9600, pulse_data), daemon=True)

    capture_thread.start()
    pulse_thread.start()
    plot_accel_live(captured_data, pulse_data, fs=fs, buffer_sec=buffer_sec)

if __name__ == "__main__":
    try:
        total(50, 3)
    except KeyboardInterrupt:
        print("Interrupted by user.")
        sys.exit(0)
