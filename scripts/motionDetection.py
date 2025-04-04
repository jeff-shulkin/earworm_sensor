import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split
from dopplerSpectrogramDataset import DopplerSpectrogramDataset
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix
import seaborn as sns
import os
import time
import numpy as np


# Define a CNN model for 1024x133 spectrogram classification
class MotionDetection(nn.Module):
    def __init__(self, num_features=3, num_classes=2, sequence_length=3):  # Binary Classification: Either there is motion or there isn't
        super(MotionDetection, self).__init__()

        # Definition of layers in order of dataflow
        self.classifier = nn.Sequential(
            nn.Conv1D(in_channels=num_features, out_channels=8, kernel_size=num_classes),
            nn.ReLU(),
            nn.BatchNorm2d(8),
            nn.Flatten(),
            nn.Linear((SEQ_LEN - 1) * 8, 1),
            nn.Sigmoid()
        )

    def forward(self, x):
        # input already has the shape: (batch_size, 1, 28, 28)
        x = x.permute(0, 2, 1)  # reshape to (B, C, T)
        x = self.classifier(x)
        return x    # Model outputs confidence in each possible label, not the predicted label directly
