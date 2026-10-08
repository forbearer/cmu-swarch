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


class WaypointMetaDriveBridge(MetaDriveBridge):
  """Drive from a generated waypoint A to a generated waypoint B and stop on arrival."""

  # Overridable by subclasses (e.g. ml-pipeline's RecordingMetaDriveWorld) that need to wrap
  # the world without duplicating the config-building below.
  world_cls = MetaDriveWorld

  def __init__(self, dual_camera, high_quality, num_blocks=12, seed=None,
               test_duration=math.inf, test_run=False):
    super().__init__(dual_camera, high_quality, test_duration, test_run)
    self.num_blocks = num_blocks
    self.seed = seed

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
