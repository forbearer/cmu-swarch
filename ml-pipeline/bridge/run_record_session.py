#!/usr/bin/env python3
"""
Drives like av-sim/bridge/run_waypoint_bridge.py, but records (frame, control) pairs for
behavior-cloning training as it drives. Drive manually (keyboard/joystick) or let openpilot
engage -- either way, every applied control gets logged alongside the frame it was applied to.

Run multiple sessions into the same --dataset-dir to build up a larger dataset; frame numbering
continues from wherever label.csv left off is NOT implemented -- each run starts a fresh
labels.csv in a new --dataset-dir. Merge datasets at training time instead (see train.py).
"""
import argparse
import functools
import sys
from pathlib import Path
from typing import Any
from multiprocessing import Queue

ML_PIPELINE_ROOT = Path(__file__).resolve().parents[1]
CMU_SWARCH_ROOT = ML_PIPELINE_ROOT.parent
AV_SIM_BRIDGE = CMU_SWARCH_ROOT / "av-sim" / "bridge"
OPENPILOT_ROOT = CMU_SWARCH_ROOT / "av-sim" / "openpilot"

sys.path.insert(0, str(ML_PIPELINE_ROOT / "bridge"))
sys.path.insert(0, str(AV_SIM_BRIDGE))
sys.path.insert(0, str(OPENPILOT_ROOT))

from waypoint_bridge import WaypointMetaDriveBridge  # noqa: E402
from recording_world import RecordingMetaDriveWorld  # noqa: E402


class RecordingBridge(WaypointMetaDriveBridge):
  def __init__(self, *args, dataset_dir, record_every=5, **kwargs):
    super().__init__(*args, **kwargs)
    self.world_cls = functools.partial(
      RecordingMetaDriveWorld, dataset_dir=dataset_dir, record_every=record_every)


def create_bridge(dual_camera, high_quality, num_blocks, seed, dataset_dir, record_every):
  queue: Any = Queue()
  simulator_bridge = RecordingBridge(
    dual_camera, high_quality, num_blocks=num_blocks, seed=seed,
    dataset_dir=dataset_dir, record_every=record_every)
  simulator_process = simulator_bridge.run(queue)
  return queue, simulator_process, simulator_bridge


def parse_args(add_args=None):
  parser = argparse.ArgumentParser(description='Record an AV Sim driving session for behavior-cloning training.')
  parser.add_argument('--joystick', action='store_true')
  parser.add_argument('--high_quality', action='store_true')
  parser.add_argument('--dual_camera', action='store_true')
  parser.add_argument('--num-blocks', type=int, default=12)
  parser.add_argument('--seed', type=int, default=None)
  parser.add_argument('--dataset-dir', required=True, help='output directory for frames/ and labels.csv')
  parser.add_argument('--record-every', type=int, default=5,
                       help='save 1 of every N applied-control ticks (ticks run at 100Hz)')
  return parser.parse_args(add_args)


if __name__ == "__main__":
  args = parse_args()

  queue, simulator_process, simulator_bridge = create_bridge(
    args.dual_camera, args.high_quality, args.num_blocks, args.seed,
    args.dataset_dir, args.record_every)

  if args.joystick:
    from openpilot.tools.sim.lib.manual_ctrl import wheel_poll_thread
    wheel_poll_thread(queue)
  else:
    from openpilot.tools.sim.lib.keyboard_ctrl import keyboard_poll_thread
    keyboard_poll_thread(queue)

  simulator_bridge.shutdown()
  simulator_process.join()
