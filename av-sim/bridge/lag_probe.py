#!/usr/bin/env python3
"""
Diagnostic: is openpilot keeping up in real time on this machine, and is it engaged?

Subscribes to the cereal bus (same way telemetry_server.py does) and prints one line per
second with the message rates that decide whether selfdrived's Ratekeeper declares "lagging"
(see av-sim/README.md, "Why openpilot disengages with 'System Lagging'"):

  carState Hz   - selfdrived's loop is paced by carState (100 Hz nominal). If the simulated CAN
                  feed averages below ~90 Hz, Ratekeeper.lagging goes true -> selfdrivedLagging.
  can Hz        - the simulated CAN feed from the bridge (carState's upstream).
  modelV2 Hz    - the driving model (20 Hz nominal).
  state/events  - selfdriveState.state and the active onroadEvents names.

Run it in a second terminal while run_demo.sh is running:
  av-sim/openpilot/.venv/bin/python av-sim/bridge/lag_probe.py [seconds]
"""
import sys
import time
from pathlib import Path

OPENPILOT_ROOT = Path(__file__).resolve().parents[1] / "openpilot"
sys.path.insert(0, str(OPENPILOT_ROOT))

import openpilot.cereal.messaging as messaging  # noqa: E402

SERVICES = ["can", "carState", "narrowRoadCameraState", "modelV2", "selfdriveState", "onroadEvents"]


def main():
  duration = float(sys.argv[1]) if len(sys.argv) > 1 else 60.
  socks = {s: messaging.sub_sock(s, conflate=False, timeout=0) for s in SERVICES}
  counts = dict.fromkeys(SERVICES, 0)
  state, events = "?", []
  exec_ms, drop = [], []
  vego = steer = curv = 0.
  lagging_secs = engaged_secs = total_secs = 0
  t_end = time.monotonic() + duration
  t_tick = time.monotonic() + 1.
  while time.monotonic() < t_end:
    for name, sock in socks.items():
      for msg in messaging.drain_sock(sock):
        counts[name] += 1
        if name == "modelV2":
          exec_ms.append(msg.modelV2.modelExecutionTime * 1000.)
          drop.append(msg.modelV2.frameDropPerc)
          curv = msg.modelV2.action.desiredCurvature
        elif name == "carState":
          vego, steer = msg.carState.vEgo, msg.carState.steeringAngleDeg
        elif name == "selfdriveState":
          state = str(msg.selfdriveState.state)
        elif name == "onroadEvents":
          events = [str(e.name) for e in msg.onroadEvents]
    time.sleep(0.002)
    if time.monotonic() >= t_tick:
      t_tick += 1.
      total_secs += 1
      lagging_secs += "selfdrivedLagging" in events
      engaged_secs += state in ("enabled", "preEnabled", "overriding")
      mexec = sum(exec_ms) / len(exec_ms) if exec_ms else 0.
      mdrop = sum(drop) / len(drop) if drop else 0.
      print(f"{time.strftime('%H:%M:%S')} can={counts['can']:4d} carState={counts['carState']:4d} "
            f"cam={counts['narrowRoadCameraState']:3d} modelV2={counts['modelV2']:3d} (exec {mexec:5.1f}ms, drop {mdrop:4.1f}%) "
            f"v={vego:5.1f}m/s steer={steer:6.1f}deg curv={curv:+.4f} state={state:12s} events={events}", flush=True)
      counts = dict.fromkeys(SERVICES, 0)
      exec_ms, drop = [], []
  print(f"SUMMARY: {total_secs}s observed, {engaged_secs}s engaged, {lagging_secs}s with selfdrivedLagging")


if __name__ == "__main__":
  main()
