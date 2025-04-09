import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque

# === CONFIG ===
PORT = 'COM3'            # Change to your serial port
BAUD_RATE = 115200
MAX_POINTS = 200         # Number of points on screen

# === INIT SERIAL AND DATA BUFFER ===
ser = serial.Serial(PORT, BAUD_RATE)
pulse_data = deque([0]*MAX_POINTS, maxlen=MAX_POINTS)

# === SETUP PLOT ===
fig, ax = plt.subplots()
line, = ax.plot(range(MAX_POINTS), pulse_data, lw=2)  # <-- define line here

def init():
    ax.set_xlim(0, MAX_POINTS)
    ax.set_ylim(0, 1023)  # ADC 10-bit range
    ax.set_title("Live Pulse Signal")
    ax.set_xlabel("Samples")
    ax.set_ylabel("Signal")
    return line,

def update(frame):
    while ser.in_waiting:
        try:
            line_data = ser.readline().decode('utf-8').strip()
            parts = line_data.split(',')
            if len(parts) == 3:
                raw_signal = int(parts[2])
                pulse_data.append(raw_signal)
        except:
            continue  # skip any malformed data

    line.set_ydata(pulse_data)
    return line,

ani = animation.FuncAnimation(
    fig, update, init_func=init, interval=50, blit=True,
    cache_frame_data=False  # suppress that warning you saw
)

plt.tight_layout()
plt.show()
