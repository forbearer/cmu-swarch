#!/usr/bin/env python3
"""
Entry point for the waypoint-driving bridge. Mirrors the structure of openpilot's own
tools/sim/run_bridge.py, swapping in WaypointMetaDriveBridge (see waypoint_bridge.py) instead of
the stock MetaDriveBridge.
"""
import sys
import argparse
from pathlib import Path
from typing import Any
from multiprocessing import Queue

sys.path.insert(0, str(Path(__file__).resolve().parent))
OPENPILOT_ROOT = Path(__file__).resolve().parents[1] / "openpilot"
sys.path.insert(0, str(OPENPILOT_ROOT))

from waypoint_bridge import WaypointMetaDriveBridge  # noqa: E402


def create_bridge(dual_camera, high_quality, num_blocks, seed):
  queue: Any = Queue()

  simulator_bridge = WaypointMetaDriveBridge(dual_camera, high_quality, num_blocks=num_blocks, seed=seed)
  simulator_process = simulator_bridge.run(queue)

  return queue, simulator_process, simulator_bridge


def parse_args(add_args=None):
  parser = argparse.ArgumentParser(description='Waypoint A-to-B bridge between MetaDrive and openpilot.')
  parser.add_argument('--joystick', action='store_true')
  parser.add_argument('--high_quality', action='store_true')
  parser.add_argument('--dual_camera', action='store_true')
  parser.add_argument('--num-blocks', type=int, default=12, help='number of road blocks between waypoint A and waypoint B')
  parser.add_argument('--seed', type=int, default=None, help='map generation seed, for a repeatable route')
  return parser.parse_args(add_args)


if __name__ == "__main__":
  args = parse_args()

  queue, simulator_process, simulator_bridge = create_bridge(
    args.dual_camera, args.high_quality, args.num_blocks, args.seed)

  if args.joystick:
    from openpilot.tools.sim.lib.manual_ctrl import wheel_poll_thread
    wheel_poll_thread(queue)
  else:
    from openpilot.tools.sim.lib.keyboard_ctrl import keyboard_poll_thread
    keyboard_poll_thread(queue)

  simulator_bridge.shutdown()
  simulator_process.join()
