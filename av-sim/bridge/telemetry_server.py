#!/usr/bin/env python3
"""
Streams openpilot's live telemetry (position, heading, speed, engagement) to any connected
browser client over a plain WebSocket, as JSON.

Deliberately doesn't touch the sim bridge or openpilot internals: this subscribes to openpilot's
own cereal message bus (messaging.SubMaster), the same mechanism tools like cabana and
openpilot's own UI use to consume state. Run this as its own process, alongside
launch_openpilot.sh and run_waypoint_bridge.py (see README.md).

Fields read from cereal, verified against openpilot's cereal/log.capnp:
- liveLocationKalman.positionGeodetic.value  -> [lat, lon, alt]
- liveLocationKalman.orientationNED.value    -> [roll, pitch, yaw]
- liveLocationKalman.velocityCalibrated.value -> [vx, vy, vz], vx is forward speed (m/s)
- selfdriveState.active                      -> bool, openpilot currently in control
"""
import asyncio
import json
import sys
import time
from pathlib import Path

OPENPILOT_ROOT = Path(__file__).resolve().parents[1] / "openpilot"
sys.path.insert(0, str(OPENPILOT_ROOT))

import websockets  # noqa: E402
import openpilot.cereal.messaging as messaging  # noqa: E402

SUBSCRIBE = ['liveLocationKalman', 'selfdriveState']
HZ = 20


def latest_state(sm: messaging.SubMaster) -> dict:
  sm.update(0)
  state: dict = {'t': time.time()}

  if sm.valid['selfdriveState']:
    state['engaged'] = bool(sm['selfdriveState'].active)

  if sm.valid['liveLocationKalman'] and sm.alive['liveLocationKalman']:
    llk = sm['liveLocationKalman']
    if llk.positionGeodetic.valid:
      lat, lon, alt = llk.positionGeodetic.value
      state['lat'], state['lon'], state['alt'] = lat, lon, alt
    if llk.orientationNED.valid:
      state['yaw'] = llk.orientationNED.value[2]
    if llk.velocityCalibrated.valid:
      state['speed'] = llk.velocityCalibrated.value[0]

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
