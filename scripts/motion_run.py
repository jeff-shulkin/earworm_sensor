import torch
import pandas as pd
import numpy as np
from motionDetection import MotionDetection

# Configuration
MODEL_PATH = "motion_model.pth"
CSV_PATH = "../dataset/test_bad2.csv"
BUFFER_SIZE = 128
DEVICE = torch.device("cuda:0") if torch.cuda.is_available() else torch.device("cpu")

# Load trained model
model = MotionDetection(input_channels=3, seq_len=BUFFER_SIZE)
model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
model.eval()

# Load test data
df = pd.read_csv(CSV_PATH)[['x', 'y', 'z']].to_numpy()
num_chunks = len(df) // BUFFER_SIZE
chunks = []

for i in range(num_chunks):
    chunk = df[i * BUFFER_SIZE:(i + 1) * BUFFER_SIZE]
    chunk = chunk.T  # (3, buffer_size)
    chunks.append(chunk)

chunks = torch.tensor(np.array(chunks), dtype=torch.float32).to(DEVICE)

# Predict
with torch.no_grad():
    outputs = model(chunks)  # shape: (num_chunks, 2)
    predicted = torch.argmax(outputs, dim=1)

# Print results
for i, pred in enumerate(predicted):
    label = "GOOD" if pred.item() == 1 else "BAD"
    print(f"Chunk {i + 1}: {label}")
