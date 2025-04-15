import torch
import torchaudio
from torchvision.transforms import Resize
import numpy as np
import pandas as pd
import os
from scipy.io.wavfile import read
from scipy.signal import butter, filtfilt, spectrogram
from torch.utils.data import Dataset, DataLoader

# Custom PyTorch Dataset
class HeartbeatDataset(Dataset):
    files = None

    def __init__(self):
        self.files = [file for file in os.listdir("vibration_dataset") if os.path.isfile(os.path.join("public_dataset", file))]

    def __len__(self):
        # Return the number of samples
        # there should be 400 samples
        return len(self.files)

    def extract_label(self, filename):
        return int(filename.split('_')[1])

    # %% Apply Low-Pass Filter to Remove High-Frequency Components
    def butter_lowpass_filter(self, signal, fc, fs, order=5):
        """
        Applies a low-pass Butterworth filter to a signal.

        Args:
            signal (np.ndarray): Input signal.
            fc (float): Cut-off frequency in Hz.
            fs (int): Sampling frequency in Hz.
            order (int): Filter order (default=5).

        Returns:
            np.ndarray: Filtered signal.
        """
        b, a = butter(order, fc / (fs / 2), btype='low')
        return filtfilt(b, a, signal)  # Zero-phase filtering

    def signal_extraction(self, vibration_filename):
        # %% Parameters
        fs = 48000  # Sampling frequency (ensure high enough for ultrasound)
        duration = 3  # Signal duration in seconds
        f_center = 20480  # Central ultrasound frequency
        doppler_shift = 500  # Simulated Doppler shift in Hz (adjust as needed)

        # %% Load or Use Provided Ultrasound Signal
        sample_rate, audio_data = read(wav_filename)

        # Ensure audio data is normalized to the range [-1, 1]
        audio_data = audio_data.astype(np.float32)
        ultrasound_signal = audio_data / np.max(np.abs(audio_data))

        # Ensure length compatibility
        t = np.arange(0, len(ultrasound_signal) / sample_rate, 1 / sample_rate)
        if len(t) > len(ultrasound_signal):
            t = t[:len(ultrasound_signal)]

        # %% **Downconvert to Baseband** (Remove Center Frequency)
        baseband_real = ultrasound_signal * np.cos(2 * np.pi * f_center * t)
        baseband_imag = ultrasound_signal * -np.sin(2 * np.pi * f_center * t)

        baseband_signal = baseband_real + 1j * baseband_imag

        # Low-pass filter parameters
        fc = 100  # Cut-off frequency (Hz)

        # Apply filtering to baseband signals
        baseband_filtered_real = self.butter_lowpass_filter(baseband_real, fc, sample_rate)
        baseband_filtered_imag = self.butter_lowpass_filter(baseband_imag, fc, sample_rate)

        # Create complex baseband signal after filtering
        baseband_signal = baseband_filtered_real + 1j * baseband_filtered_imag

        # %% Downsample the baseband signal for STFT analysis
        downsample_factor = 8
        baseband_signal_downsampled = baseband_signal[::downsample_factor]
        fs_downsampled = sample_rate / downsample_factor

        # %% Compute STFT (Doppler Shift Analysis)
        window_size = 1024
        overlap = window_size - 128
        nfft = 1024

        # Compute spectrogram
        frequencies, times, Sxx = spectrogram(baseband_signal_downsampled, fs_downsampled,
                                            nperseg=window_size, noverlap=overlap, nfft=nfft, mode='complex')

        # Limit frequency range to -250 Hz to 250 Hz
        freq_range = (-100, 100)
        freq_indices = (frequencies >= freq_range[0]) & (frequencies <= freq_range[1])
        filtered_frequencies = frequencies[freq_indices]
        filtered_Sxx = Sxx[freq_indices, :]
        midpoint = np.shape(filtered_Sxx)[0] // 2
        filtered_Sxx = np.vstack([
            filtered_Sxx[midpoint:, :],  # Lower half becomes the upper half
            filtered_Sxx[:midpoint, :]  # Upper half becomes the lower half
        ])

        # Extract the frequency with the highest power at each time step
        max_indices = np.argmax(np.abs(filtered_Sxx), axis=0)
        doppler_freqs = filtered_frequencies[max_indices]

        return 10 * np.log10(np.abs(Sxx))


    def __getitem__(self, idx):
        # Grab filename corresponding to index
        filename = self.files[idx]

        # Extract the label by splitting the filename
        label = self.extract_label(filename)

        # Extract the signal
        signal = self.vibration_extraction("public_dataset/" + filename)


        # Return the spectrogram as a torch.Tensor (1024×133) and the label as torch.LongTensor.
        return torch.Tensor(signal), torch.LongTensor([label])




class AccelDataset(Dataset):
    def __init__(self, good_csv, bad_csv, buffer_size=128):
        self.buffer_size = buffer_size
        self.data = []
        self.labels = []

        for file_path, label in [(good_csv, 1), (bad_csv, 0)]:
            df = pd.read_csv(file_path)[['x', 'y', 'z']].to_numpy()
            num_chunks = len(df) // buffer_size

            for i in range(num_chunks):
                chunk = df[i * buffer_size: (i + 1) * buffer_size]
                chunk = chunk.T  # shape (3, buffer_size)
                self.data.append(chunk)
                self.labels.append(label)

        # self.data = torch.tensor(self.data, dtype=torch.float32)
        # self.labels = torch.tensor(self.labels, dtype=torch.long)
        self.data = torch.tensor(np.array(self.data), dtype=torch.float32)
        self.labels = torch.tensor(self.labels, dtype=torch.long).view(-1)  # ensures 1D labels


    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        return self.data[idx], self.labels[idx]
