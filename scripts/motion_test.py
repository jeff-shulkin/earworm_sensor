import numpy as np
import time
import torch
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix
import seaborn as sns

DEVICE = torch.device("cuda:0") if torch.cuda.is_available() else torch.device("cpu")

# Test function with confusion matrix (percentage) & model saving
def test_model(model, test_loader):
    # load motionDetection model
    predictions = []
    labels = []
    num_total = 0
    num_correct = 0
    inputs = None
    true_labels = None
    batch_size = 8

    with torch.no_grad():
        for inputs, true_labels in test_loader:
            inputs, true_labels = inputs.to(DEVICE), true_labels.to(DEVICE)
            true_labels = true_labels.squeeze(1)
            outputs = model(inputs)
            _, predicted_labels = torch.max(outputs, 1)
            labels += true_labels.cpu()
            predictions += predicted_labels.cpu()
            num_total += batch_size
            num_correct += (predicted_labels == true_labels).sum().item()

    matrix = confusion_matrix(labels, predictions)
    matrix = matrix.astype("float") / matrix.sum(axis=1)[:, np.newaxis]

    plt.figure()
    sns.heatmap(matrix, annot=True, cmap="Blues", cbar=False)
    plt.title("Motion detection Heatmap")
    plt.xlabel("Predicted labels")
    plt.ylabel("True labels")
    plt.show()

    print(f"Test data accuracy: {(num_correct / num_total) * 100}%")

# Function to evaluate single sample inference time on test dataset
def test_single_sample_inference(model, test_loader):
    signal, _ = next(iter(test_loader))
    signal_cpu = signal.to(torch.device("cpu"))
    model_cpu = model.to(torch.device("cpu"))
    start_time = time.time()
    with torch.no_grad():
        _ = model_cpu(signal_cpu)
    end_time = time.time()

    elapsed_time = end_time - start_time
    #print(f"Elapsed time for a single inference: {elapsed_time}")
    print(f"Time Elapsed: {elapsed_time // 60} min {elapsed_time % 60} sec")


# Test the model
#test_model()
#test_single_sample_inference()
