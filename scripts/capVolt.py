import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque
import time

# === CONFIG ===
PORT = 'COM3'            # Update to your port
BAUD_RATE = 9600         # Match Serial.begin() on Arduino
MAX_POINTS = 2000         # Number of data points shown

# === INIT SERIAL AND DATA BUFFER ===
ser = serial.Serial(PORT, BAUD_RATE)
voltages = deque([0.0]*MAX_POINTS, maxlen=MAX_POINTS)
timestamps = deque([0.0]*MAX_POINTS, maxlen=MAX_POINTS)
start_time = time.time()

# === SETUP PLOT ===
fig, ax = plt.subplots()
line, = ax.plot([], [], lw=2)

def init():
    ax.set_ylim(0, 6.5)  # Expected voltage range
    ax.set_title("Capacitor Voltage vs Time")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Voltage (V)")
    return line,

def update(frame):
    global start_time

    while ser.in_waiting:
        try:
            line_data = ser.readline().decode('utf-8').strip()
            voltage = float(line_data)
            current_time = time.time() - start_time
            voltages.append(voltage)
            timestamps.append(current_time)
        except:
            continue

    ax.set_xlim(timestamps[0], timestamps[-1])  # Auto-scroll
    line.set_data(timestamps, voltages)
    return line,

ani = animation.FuncAnimation(
    fig, update, init_func=init, interval=50, blit=True,
    cache_frame_data=False
)

plt.tight_layout()
plt.show()
