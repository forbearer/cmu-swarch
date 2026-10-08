"""Small CNN: RGB road-camera frame -> (steer, longitudinal) prediction.

Deliberately small -- this is a teaching artifact for tuning training parameters and observing
behavior change in the AV Sim, not a state-of-the-art perception model. `width` multiplies
channel counts so model capacity is itself one of the tunable parameters.
"""
import torch
import torch.nn as nn


class DrivingPolicyNet(nn.Module):
  def __init__(self, width: float = 1.0):
    super().__init__()
    c1, c2, c3 = int(16 * width), int(32 * width), int(64 * width)
    self.features = nn.Sequential(
      nn.Conv2d(3, c1, kernel_size=5, stride=2, padding=2), nn.ReLU(),
      nn.Conv2d(c1, c2, kernel_size=5, stride=2, padding=2), nn.ReLU(),
      nn.Conv2d(c2, c3, kernel_size=3, stride=2, padding=1), nn.ReLU(),
      nn.AdaptiveAvgPool2d((4, 4)),
    )
    self.head = nn.Sequential(
      nn.Flatten(),
      nn.Linear(c3 * 4 * 4, 64), nn.ReLU(),
      nn.Linear(64, 2),
    )

  def forward(self, x: torch.Tensor) -> torch.Tensor:
    return self.head(self.features(x))
