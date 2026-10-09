#!/usr/bin/env python3
"""
Streams openpilot's live telemetry (position, heading, speed, engagement) to any connected
browser client over a plain WebSocket, as JSON.

Deliberately doesn't touch the sim bridge or openpilot internals: this subscribes to openpilot's
own cereal message bus (messaging.SubMaster), the same mechanism tools like cabana and
openpilot's own UI use to consume state. Run this as its own process, alongside
launch_openpilot.sh and run_waypoint_bridge.py (see README.md).

Fields read from cereal, verified against openpilot's cereal/log.capnp AND against what our own
sim actually publishes (tools/sim/lib/simulated_sensors.py's send_gps_message) -- not just the
schema, since `liveLocationKalman` turned out to be deprecated (see below):
- gpsLocationExternal.{latitude,longitude,altitude,speed,bearingDeg} -- the raw GPS fix our own
  SimulatedSensors publishes every tick from MetaDrive's simulated position, directly.
- selfdriveState.active -- bool, openpilot currently in control

`liveLocationKalman` (this file's original topic choice) is marked DEPRECATED in current
cereal/log.capnp (`liveLocationKalmanDEPRECATED`), confirmed by a real KeyError running this on
Owen's Mac 2026-10-09: `cereal.services.SERVICE_LIST` no longer has an entry for it at all.
locationd's modern replacement, `deviceMotion`, has no absolute position field (orientation/
velocity/acceleration only) -- not a substitute. `gpsLocationExternal` is simpler anyway: one
topic, no Kalman-filter warm-up needed, and it's exactly what feeds the sim's own GPS input.
"""
import asyncio
import json
import math
import sys
import time
from pathlib import Path

OPENPILOT_ROOT = Path(__file__).resolve().parents[1] / "openpilot"
sys.path.insert(0, str(OPENPILOT_ROOT))

import websockets  # noqa: E402
import openpilot.cereal.messaging as messaging  # noqa: E402

SUBSCRIBE = ['gpsLocationExternal', 'selfdriveState']
HZ = 20


def latest_state(sm: messaging.SubMaster) -> dict:
  sm.update(0)
  state: dict = {'t': time.time()}

  if sm.valid['selfdriveState']:
    state['engaged'] = bool(sm['selfdriveState'].active)

  if sm.valid['gpsLocationExternal'] and sm.alive['gpsLocationExternal']:
    gps = sm['gpsLocationExternal']
    state['lat'] = gps.latitude
    state['lon'] = gps.longitude
    state['alt'] = gps.altitude
    state['speed'] = gps.speed
    state['yaw'] = math.radians(gps.bearingDeg)  # viewer.js expects radians

  return state


async def broadcast(websocket):
  sm = messaging.SubMaster(SUBSCRIBE)
  try:
    while True:
      await websocket.send(json.dumps(latest_state(sm)))
      await asyncio.sleep(1 / HZ)
  except websockets.exceptions.ConnectionClosed:
    pass


async def main(host='0.0.0.0', port=8765):
  async with websockets.serve(broadcast, host, port):
    print(f"Telemetry server listening on ws://{host}:{port}")
    await asyncio.Future()  # run forever


if __name__ == '__main__':
  import argparse
  parser = argparse.ArgumentParser(description='Relay openpilot telemetry to WebSocket clients.')
  parser.add_argument('--host', default='0.0.0.0')
  parser.add_argument('--port', type=int, default=8765,
                       help='use a distinct port per vehicle when running more than one AV Sim instance')
  args = parser.parse_args()
  asyncio.run(main(args.host, args.port))
