"""Loads a train.py checkpoint and exposes it as a frame -> (steer, longitudinal) predictor.

Standalone (no openpilot/MetaDrive imports) -- bridge/run_trained_policy.py is the thing that
wires this into the actual simulator loop.
"""
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from model import DrivingPolicyNet


class TrainedDrivingPolicy:
  def __init__(self, checkpoint_path, device="cpu"):
    ckpt = torch.load(checkpoint_path, map_location=device)
    self.model = DrivingPolicyNet(width=ckpt.get("width", 1.0))
    self.model.load_state_dict(ckpt["state_dict"])
    self.model.eval()
    self.device = device

  def predict(self, frame_rgb: np.ndarray):
    """frame_rgb: HxWx3 uint8 array (any size -- resize to match training data before calling
    for best results, see bridge/run_trained_policy.py). Returns (steer, longitudinal)."""
    image = torch.from_numpy(frame_rgb.astype(np.float32) / 255.0).permute(2, 0, 1).unsqueeze(0)
    with torch.no_grad():
      steer, longitudinal = self.model(image)[0].tolist()
    return steer, longitudinal
