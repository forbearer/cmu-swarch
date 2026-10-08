"""
Wraps MetaDriveWorld to record (camera frame, applied control) pairs to disk for behavior-cloning
training.

Hooks into apply_controls(), the one call openpilot's SimulatorBridge main loop already makes
every tick with the exact steer/throttle/brake about to be applied -- see
av-sim/openpilot/openpilot/tools/sim/bridge/metadrive/metadrive_world.py (read directly, not
guessed). Reads self.road_image, the same shared-memory RGB frame array MetaDrive's own camera
process fills continuously (metadrive_process.py) -- this is the plain RGB frame *before* it gets
re-encoded to NV12 and published over VisionIPC for openpilot's own perception stack, so no
VisionIPC/YUV decoding is needed here at all.
"""
from pathlib import Path

from PIL import Image

from openpilot.tools.sim.bridge.metadrive.metadrive_world import MetaDriveWorld

# Full sim camera is 1928x1208 (see tools/sim/lib/common.py) -- far more resolution than a
# teaching behavior-cloning model needs. Downsized at record time to keep the dataset small.
SAVE_SIZE = (320, 160)  # (width, height)


class RecordingMetaDriveWorld(MetaDriveWorld):
  """Same as MetaDriveWorld, but saves every applied (frame, steer, throttle, brake) to disk."""

  def __init__(self, *args, dataset_dir, record_every=5, **kwargs):
    super().__init__(*args, **kwargs)
    self.dataset_dir = Path(dataset_dir)
    self.frames_dir = self.dataset_dir / "frames"
    self.frames_dir.mkdir(parents=True, exist_ok=True)
    self.record_every = record_every

    self._tick_count = 0
    self._sample_idx = 0
    self.labels_path = self.dataset_dir / "labels.csv"
    if not self.labels_path.exists():
      self.labels_path.write_text("frame,steer,throttle,brake\n")

  def apply_controls(self, steer_angle, throttle_out, brake_out):
    self._tick_count += 1
    if self._tick_count % self.record_every == 0:
      frame_name = f"{self._sample_idx:06d}.png"
      image = Image.fromarray(self.road_image.copy()).resize(SAVE_SIZE, Image.BILINEAR)
      image.save(self.frames_dir / frame_name)
      with open(self.labels_path, "a") as f:
        f.write(f"{frame_name},{steer_angle},{throttle_out},{brake_out}\n")
      self._sample_idx += 1

    super().apply_controls(steer_angle, throttle_out, brake_out)
