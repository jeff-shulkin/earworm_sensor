import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque

# === CONFIG ===
PORT = 'COM3'           # Adjust as needed
BAUD_RATE = 115200
MAX_POINTS = 200        # Number of samples shown on screen

# === INIT SERIAL AND DATA ===
ser = serial.Serial(PORT, BAUD_RATE)
pulse_data = deque([0] * MAX_POINTS, maxlen=MAX_POINTS)
latest_bpm = [0]  # mutable container for updating BPM across frames

# === SETUP PLOT ===
fig, ax = plt.subplots()
line, = ax.plot(range(MAX_POINTS), pulse_data, lw=2, label='Pulse Signal')

# Add BPM label inside the plot (top-left corner)
bpm_text = ax.text(
    0.02, 0.95, 'BPM: NA',
    transform=ax.transAxes,
    fontsize=12,
    verticalalignment='top',
    bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5)
)

def init():
    ax.set_xlim(0, MAX_POINTS)
    ax.set_ylim(0, 1023)  # ADC 10-bit
    ax.set_xlabel("Samples")
    ax.set_ylabel("Pulse Sensor Output")
    ax.legend(loc="upper right")
    return line, bpm_text

def update(frame):
    while ser.in_waiting:
        try:
            line_data = ser.readline().decode('utf-8', errors='ignore').strip()
            print(line_data)
            parts = line_data.split(',')
            if len(parts) == 3:
                bpm = int(parts[0])
                raw_signal = int(parts[2])
                latest_bpm[0] = bpm
                pulse_data.append(raw_signal)
        except:
            continue  # skip bad lines

    line.set_ydata(pulse_data)
    bpm_text.set_text(f"BPM: {latest_bpm[0]}")
    return line, bpm_text

ani = animation.FuncAnimation(
    fig, update, init_func=init, interval=50, blit=True, cache_frame_data=False
)

plt.tight_layout()
plt.show()
