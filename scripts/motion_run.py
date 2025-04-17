# import torch
# import pandas as pd
# import numpy as np
# from motionDetection import MotionDetection

# # Configuration
# MODEL_PATH = "motion_model.pth"
# CSV_PATH = "../dataset/test_bad2.csv"
# BUFFER_SIZE = 128
# DEVICE = torch.device("cuda:0") if torch.cuda.is_available() else torch.device("cpu")

# # Load trained model
# model = MotionDetection(input_channels=3, seq_len=BUFFER_SIZE)
# model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
# model.eval()

# # Load test data
# df = pd.read_csv(CSV_PATH)[['x', 'y', 'z']].to_numpy()
# num_chunks = len(df) // BUFFER_SIZE
# chunks = []

# for i in range(num_chunks):
#     chunk = df[i * BUFFER_SIZE:(i + 1) * BUFFER_SIZE]
#     chunk = chunk.T  # (3, buffer_size)
#     chunks.append(chunk)

# chunks = torch.tensor(np.array(chunks), dtype=torch.float32).to(DEVICE)

# # Predict
# with torch.no_grad():
#     outputs = model(chunks)  # shape: (num_chunks, 2)
#     predicted = torch.argmax(outputs, dim=1)

# # Print results
# for i, pred in enumerate(predicted):
#     label = "GOOD" if pred.item() == 1 else "BAD"
#     print(f"Chunk {i + 1}: {label}")





#-----------------------------------------------------------------------------

import torch
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from motionDetection import MotionDetection

# ------------------------
# Config
# ------------------------
csv_path = "../dataset/test_mix2.csv"
MODEL_PATH = "motion_model.pth"
BUFFER_SIZE = 128
DEVICE = torch.device("cuda:0") if torch.cuda.is_available() else torch.device("cpu")

# ------------------------
# Load Model
# ------------------------
model = MotionDetection(input_channels=3, seq_len=BUFFER_SIZE)
model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
model.to(DEVICE)
model.eval()

# ------------------------
# Load CSV Data
# ------------------------
df = pd.read_csv(csv_path)[['x', 'y', 'z']].to_numpy()
num_chunks = len(df) // BUFFER_SIZE

# ------------------------
# Setup Plot
# ------------------------
plt.ion()
fig, axs = plt.subplots(3, 1, figsize=(10, 6), sharex=True)
axes_titles = ['X-axis', 'Y-axis', 'Z-axis']
lines = []

for ax, title in zip(axs, axes_titles):
    # ax.set_title(title)
    ax.set_ylim(-1.5, 1.5)  # Adjust based on sensor range
    line, = ax.plot([], [], lw=2)
    lines.append(line)

axs[-1].set_xlabel("Sample")
plt.tight_layout()

# ------------------------
# Inference + Plot Loop
# ------------------------
for i in range(num_chunks):
    chunk = df[i * BUFFER_SIZE:(i + 1) * BUFFER_SIZE]
    chunk_tensor = torch.tensor(chunk.T[np.newaxis, ...], dtype=torch.float32).to(DEVICE)

    # Predict
    with torch.no_grad():
        output = model(chunk_tensor)
        prediction = torch.argmax(output, dim=1).item()
        label_str = "GOOD" if prediction == 1 else "BAD"

    # Update Plot
    for j in range(3):  # x, y, z
        lines[j].set_data(np.arange(BUFFER_SIZE), chunk[:, j])
        axs[j].set_xlim(0, BUFFER_SIZE)

    # Set live prediction in the figure title
    fig.suptitle(f"Frame {i + 1} Prediction: {label_str}", fontsize=16, color='green' if label_str == "GOOD" else 'red')

    plt.pause(0.5)

plt.ioff()
plt.show()
