"""Reads a dataset recorded by bridge/run_record_session.py: frames/<name>.png + labels.csv.

Deliberately standalone -- no openpilot or MetaDrive imports. Training should run anywhere torch
is installed, without needing the (much heavier) simulator stack.
"""
import csv
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset
from PIL import Image


class DrivingFrameDataset(Dataset):
  def __init__(self, dataset_dir):
    self.dataset_dir = Path(dataset_dir)
    self.frames_dir = self.dataset_dir / "frames"
    self.samples = []
    with open(self.dataset_dir / "labels.csv") as f:
      reader = csv.DictReader(f)
      for row in reader:
        self.samples.append((row["frame"], float(row["steer"]), float(row["throttle"]), float(row["brake"])))

  def __len__(self):
    return len(self.samples)

  def __getitem__(self, idx):
    frame_name, steer, throttle, brake = self.samples[idx]
    image = Image.open(self.frames_dir / frame_name).convert("RGB")
    image = np.asarray(image, dtype=np.float32) / 255.0
    image = torch.from_numpy(image).permute(2, 0, 1)  # HWC -> CHW

    # Single net longitudinal command (throttle positive, brake negative) -- simpler regression
    # target than two separate, partially-redundant outputs.
    label = torch.tensor([steer, throttle - brake], dtype=torch.float32)
    return image, label
