#!/usr/bin/env python3
"""
Drives the AV Sim using a trained checkpoint's predictions directly, instead of openpilot's own
driving stack.

Deliberately does NOT go through openpilot's SimulatorBridge._run() loop (av-sim/openpilot/
openpilot/tools/sim/bridge/common.py) -- that loop exists to interface with openpilot's own
control stack (simulated CAN bus, cereal, SimulatedCar/SimulatedSensors), none of which is needed
here. Instead this calls WaypointMetaDriveBridge.spawn_world() directly and drives World's public
interface (apply_controls/read_state/read_sensors/tick, all read from metadrive_world.py, not
guessed) in a plain 100Hz loop -- the same rate MetaDrive's own background process steps at.

This is the architectural point worth drawing out as a course artifact: a trained model can be
dropped in as a complete, decoupled replacement for the "robotic control" component, without
touching the simulator or the rest of the stack.
"""
import argparse
import sys
import time
from pathlib import Path
from multiprocessing import Queue

import numpy as np
from PIL import Image

ML_PIPELINE_ROOT = Path(__file__).resolve().parents[1]
CMU_SWARCH_ROOT = ML_PIPELINE_ROOT.parent
AV_SIM_BRIDGE = CMU_SWARCH_ROOT / "av-sim" / "bridge"
OPENPILOT_ROOT = CMU_SWARCH_ROOT / "av-sim" / "openpilot"

sys.path.insert(0, str(ML_PIPELINE_ROOT))
sys.path.insert(0, str(AV_SIM_BRIDGE))
sys.path.insert(0, str(OPENPILOT_ROOT))

from waypoint_bridge import WaypointMetaDriveBridge  # noqa: E402
from openpilot.tools.sim.lib.common import SimulatorState  # noqa: E402
from openpilot.common.realtime import Ratekeeper  # noqa: E402

from policy import TrainedDrivingPolicy  # noqa: E402
from recording_world import SAVE_SIZE  # noqa: E402  (match the resolution the policy was trained on)


def parse_args():
  p = argparse.ArgumentParser(description="Drive the AV Sim using a trained checkpoint instead of openpilot.")
  p.add_argument("checkpoint", help="path to a train.py checkpoint (.pt)")
  p.add_argument("--num-blocks", type=int, default=12)
  p.add_argument("--seed", type=int, default=None)
  return p.parse_args()


def main():
  args = parse_args()

  policy = TrainedDrivingPolicy(args.checkpoint)

  bridge = WaypointMetaDriveBridge(dual_camera=False, high_quality=False, num_blocks=args.num_blocks, seed=args.seed)
  queue: Queue = Queue()
  world = bridge.spawn_world(queue)
  state = SimulatorState()

  # Simulation tends to be slow in the initial steps -- let it settle before driving, same as
  # SimulatorBridge._run() does.
  for _ in range(20):
    world.tick()

  rk = Ratekeeper(100, None)
  try:
    while not world.exit_event.is_set():
      world.read_state()
      world.read_sensors(state)

      if state.valid:
        frame = Image.fromarray(world.road_image.copy()).resize(SAVE_SIZE, Image.BILINEAR)
        steer, longitudinal = policy.predict(np.asarray(frame))
        throttle = max(longitudinal, 0.0)
        brake = max(-longitudinal, 0.0)
        world.apply_controls(steer, throttle, brake)

      world.tick()
      rk.keep_time()
  except KeyboardInterrupt:
    pass
  finally:
    world.close("run_trained_policy exiting")


if __name__ == "__main__":
  main()
