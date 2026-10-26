#!/usr/bin/env python3
"""One-off diagnostic: why does carControl.actuators.accel stay near zero despite a healthy
v_cruise_kph? Watches longitudinalPlan/radarState for a phantom lead (radarless Hondas derive
"lead" from the camera model, not radar -- a known source of false positives on synthetic/
low-frame-rate sim video) alongside the raw accel command and vEgo.
Run alongside run_demo.sh:
  av-sim/openpilot/.venv/bin/python av-sim/bridge/accel_probe.py [seconds]
"""
import sys
import time
from pathlib import Path

OPENPILOT_ROOT = Path(__file__).resolve().parents[1] / "openpilot"
sys.path.insert(0, str(OPENPILOT_ROOT))

import openpilot.cereal.messaging as messaging  # noqa: E402

SERVICES = ["carState", "carControl", "longitudinalPlan", "radarState", "selfdriveState"]


def main():
  duration = float(sys.argv[1]) if len(sys.argv) > 1 else 45.
  socks = {s: messaging.sub_sock(s, conflate=True, timeout=0) for s in SERVICES}
  t_end = time.monotonic() + duration
  t_tick = time.monotonic() + 1.
  while time.monotonic() < t_end:
    time.sleep(0.05)
    if time.monotonic() < t_tick:
      continue
    t_tick += 1.
    vego = accel = vcruise = 0.
    state = "?"
    lead_present = lead_dist = lead_vrel = None
    plan_v = plan_a = has_lead = plan_source = should_stop = allow_throttle = None
    cs = messaging.recv_one_or_none(socks["carState"])
    if cs:
      vego, vcruise = cs.carState.vEgo, cs.carState.vCruise
    cc = messaging.recv_one_or_none(socks["carControl"])
    if cc:
      accel = cc.carControl.actuators.accel
    ss = messaging.recv_one_or_none(socks["selfdriveState"])
    if ss:
      state = str(ss.selfdriveState.state)
    rs = messaging.recv_one_or_none(socks["radarState"])
    if rs and rs.radarState.leadOne.present:
      lead_present = True
      lead_dist = rs.radarState.leadOne.dRel
      lead_vrel = rs.radarState.leadOne.vRel
    lp = messaging.recv_one_or_none(socks["longitudinalPlan"])
    if lp:
      plan = lp.longitudinalPlan
      has_lead, should_stop, allow_throttle = plan.hasLead, plan.shouldStop, plan.allowThrottle
      plan_source = str(plan.longitudinalPlanSource)
      plan_v = plan.speeds[-1] if plan.speeds else None
      plan_a = plan.accels[-1] if plan.accels else None
    print(f"{time.strftime('%H:%M:%S')} state={state:12s} vEgo={vego:5.1f}m/s vCruise={vcruise:5.1f}kph "
          f"accel_cmd={accel:+.2f}m/s2 planV={plan_v} planA={plan_a} src={plan_source} "
          f"hasLead={has_lead} shouldStop={should_stop} allowThrottle={allow_throttle} "
          f"radarLead={'YES dRel=%.1fm vRel=%.1f' % (lead_dist, lead_vrel) if lead_present else 'none'}",
          flush=True)


if __name__ == "__main__":
  main()
