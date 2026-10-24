#!/usr/bin/env python3
"""
Drives MetaDrive's own point-to-point task (randomly generated road network, real start
point, real destination, real arrival detection) instead of openpilot's stock tools/sim demo,
which deliberately loops a fixed closed-loop track forever (arrive_dest_done=False) because
it's built for continuous lane-keeping regression tests, not a one-shot A-to-B drive.

This is the entire diff from openpilot/tools/sim/bridge/metadrive/metadrive_bridge.py's
MetaDriveBridge.spawn_world(): a different map_config (MetaDrive's standard procedural
network instead of the closed loop) and arrive_dest_done=True.

What this does NOT yet do: accept two specific user-chosen coordinates as waypoint A/B.
MetaDrive generates its own start and destination as part of building the road network; routing
to arbitrary chosen coordinates needs MetaDrive's navigation/route API, which hasn't been
verified against actual metadrive source in this repo yet (metadrive is a pip dependency of
openpilot, not vendored here) -- see README.md's Open Items.
"""
import math
import os
import sys
from pathlib import Path
from multiprocessing import Queue

OPENPILOT_ROOT = Path(__file__).resolve().parents[1] / "openpilot"
sys.path.insert(0, str(OPENPILOT_ROOT))

from metadrive.component.map.pg_map import MapGenerateMethod  # noqa: E402
from metadrive.component.sensors.base_camera import _cuda_enable  # noqa: E402

from openpilot.tools.sim.bridge.metadrive.metadrive_bridge import MetaDriveBridge  # noqa: E402
from openpilot.tools.sim.bridge.metadrive.metadrive_common import RGBCameraRoad, RGBCameraWide  # noqa: E402
from openpilot.tools.sim.bridge.metadrive.metadrive_world import MetaDriveWorld  # noqa: E402
from openpilot.tools.sim.lib.camerad import W, H  # noqa: E402
import openpilot.tools.sim.bridge.common as sim_common  # noqa: E402

# Camera frame rate sent to openpilot. Stock tools/sim hard-codes 20 Hz (the rate openpilot's
# driving model is designed for), but on a laptop the model needs ~60 ms/frame (measured on an
# M3: av-sim/README.md, "Staying engaged on a laptop"), i.e. it can only sustain ~16 Hz. At 20 Hz
# in, ~1 frame in 6 gets dropped, and modeld marks cameraOdometry invalid on ANY dropped frame
# (modeld.py: `vipc_dropped_frames < 1`), which cascades through locationd into a SOFT_DISABLE.
# Feeding the model fewer frames than it can chew -- evenly spaced, none dropped -- avoids that.
# Set SIM_CAMERA_HZ=20 to restore stock behavior (e.g. on a much faster machine).
CAMERA_HZ = float(os.environ.get("SIM_CAMERA_HZ", "15"))

_stock_rk_loop = sim_common.rk_loop


def _rk_loop_with_camera_hz(function, hz, exit_event):
  # SimulatorBridge._run starts exactly one thread at 20 Hz (the camera sender); the CAN thread
  # is 100 Hz. Retarget only the 20 Hz one. Applied at import time so it also takes effect in the
  # spawned bridge process (macOS uses spawn, which re-imports this module).
  return _stock_rk_loop(function, CAMERA_HZ if hz == 20 else hz, exit_event)


sim_common.rk_loop = _rk_loop_with_camera_hz


class WaypointMetaDriveBridge(MetaDriveBridge):
  """Drive from a generated waypoint A to a generated waypoint B and stop on arrival."""

  # Overridable by subclasses (e.g. ml-pipeline's RecordingMetaDriveWorld) that need to wrap
  # the world without duplicating the config-building below.
  world_cls = MetaDriveWorld

  def __init__(self, dual_camera, high_quality, num_blocks=12, seed=None,
               test_duration=math.inf, test_run=False):
    super().__init__(dual_camera, high_quality, test_duration, test_run)
    self.num_blocks = num_blocks
    # MetaDrive's own default is start_seed=0 (metadrive/envs/metadrive_env.py); passing None
    # through unchanged breaks arithmetic deep inside PGMapManager (start_seed + env_num).
    # seed=None here means "no specific seed requested", so fall back to MetaDrive's own default
    # instead of overriding it with None.
    self.seed = seed if seed is not None else 0

  def spawn_world(self, queue: Queue):
    sensors = {
      "rgb_road": (RGBCameraRoad, W, H),
    }
    if self.dual_camera:
      sensors["rgb_wide"] = (RGBCameraWide, W, H)

    config = {
      "use_render": self.should_render,
      "vehicle_config": {
        "enable_reverse": False,
        "render_vehicle": False,
        "image_source": "rgb_road",
      },
      "sensors": sensors,
      "image_on_cuda": _cuda_enable,
      "image_observation": True,
      "interface_panel": [],
      "out_of_route_done": False,
      "on_continuous_line_done": False,
      "crash_vehicle_done": False,
      "crash_object_done": False,
      "arrive_dest_done": True,  # <- the actual behavior change vs. stock metadrive_bridge.py
      "traffic_density": 0.0,
      "map_config": {
        "type": MapGenerateMethod.BIG_BLOCK_NUM,
        "config": self.num_blocks,
      },
      "start_seed": self.seed,
      "decision_repeat": 1,
      "physics_world_step_size": self.TICKS_PER_FRAME / 100,
      "preload_models": False,
      "show_logo": False,
      "anisotropic_filtering": False,
    }

    return self.world_cls(queue, config, self.test_duration, self.test_run, self.dual_camera)
