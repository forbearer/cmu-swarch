#!/usr/bin/env bash
# One-command AV Sim demo: openpilot (with its own native UI) + waypoint bridge + telemetry relay
# + browser viewer, all against ONE live MetaDrive session.
#
# What is (and isn't) being "paired" here -- worth reading before the commands:
#
#   * openpilot's native UI is NOT a separate program to wire in. It is the `ui` process that
#     openpilot's own manager (started by launch_openpilot.sh) spawns, and like telemetry_server.py
#     it is just another subscriber on the cereal bus (plus VisionIPC for the camera frame the
#     bridge publishes). So the native UI and the browser viewer are two independent consumers of
#     the SAME session -- same data, two presentation tiers.
#   * The only reason the UI used to look broken: without BIG=1, openpilot falls back to a tiny
#     stripped-down layout meant for comma's own device. BIG=1 selects the full layout. No code
#     changes; the old BLOCK=ui workaround is not needed.
#
# So this script only orchestrates: start order, shared environment, and cleanup.
#
# Usage (from anywhere):   av-sim/run_demo.sh [extra args passed to run_waypoint_bridge.py]
#   e.g.                   av-sim/run_demo.sh --seed 7
# Env overrides:           VIEWER_PORT (default 8000), WS_PORT (default 8765),
#                          OPENPILOT_WARMUP seconds to wait before starting the bridge (default 8),
#                          NO_BROWSER=1 to skip opening the browser viewer,
#                          SIM_CAMERA_HZ camera frame rate fed to openpilot (default 15; stock
#                          openpilot sim is 20, but a laptop's driving model sustains only ~16)
#
# The waypoint bridge runs in the FOREGROUND of this terminal on purpose: it reads the driving
# keys (2/1 engage, w a s d, q quit -- see README.md) raw from this terminal's stdin.
# Quitting the bridge (q) or Ctrl-C tears everything else down.
set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$REPO_ROOT/av-sim/openpilot/.venv"
VIEWER_PORT="${VIEWER_PORT:-8000}"
WS_PORT="${WS_PORT:-8765}"
OPENPILOT_WARMUP="${OPENPILOT_WARMUP:-8}"

if [[ ! -x "$VENV/bin/python3" ]]; then
  echo "openpilot venv not found at $VENV -- run the Setup steps in av-sim/README.md first." >&2
  exit 1
fi

# launch_openpilot.sh calls bare `python3`, so the venv has to be active (see README.md).
# shellcheck disable=SC1091
source "$VENV/bin/activate"

mkdir -p "$REPO_ROOT/av-sim/logs"

# Applies av-sim/patches/ (macOS timing fix + mock-car cruise-speed fix; see README.md's
# "Staying engaged on a laptop" and "Driving the car" sections). No-op when already applied.
"$REPO_ROOT/av-sim/apply_patches.sh" || exit 1

PIDS=()
cleanup() {
  trap - EXIT INT TERM
  echo; echo "Shutting down..."
  # Ask nicely first so openpilot's manager can stop its own child daemons.
  for pid in "${PIDS[@]}"; do kill -TERM "$pid" 2>/dev/null; done
  sleep 2
  for pid in "${PIDS[@]}"; do kill -KILL "$pid" 2>/dev/null; done
}
trap cleanup EXIT INT TERM

# 1. openpilot manager -- also spawns the native UI. BIG=1 = full UI layout. Only soundd is
#    blocked (it plays loud real-car alert audio through your speakers). LOG_ROOT keeps logs here.
BIG="${BIG:-1}" BLOCK="${BLOCK:-soundd}" LOG_ROOT="$REPO_ROOT/av-sim/logs" \
  "$REPO_ROOT/av-sim/openpilot/openpilot/tools/sim/launch_openpilot.sh" \
  > "$REPO_ROOT/av-sim/logs/openpilot.out" 2>&1 &
PIDS+=($!)
echo "openpilot manager + native UI started (pid ${PIDS[0]}, output: av-sim/logs/openpilot.out)"

# 2. telemetry relay (cereal -> WebSocket) and 3. static server for the browser viewer.
python3 "$REPO_ROOT/av-sim/bridge/telemetry_server.py" --port "$WS_PORT" \
  > "$REPO_ROOT/av-sim/logs/telemetry.out" 2>&1 &
PIDS+=($!)
python3 -m http.server "$VIEWER_PORT" --directory "$REPO_ROOT/av-sim/viewer" \
  > "$REPO_ROOT/av-sim/logs/viewer.out" 2>&1 &
PIDS+=($!)
echo "telemetry relay on ws://localhost:$WS_PORT, viewer on http://localhost:$VIEWER_PORT"

if [[ -z "${NO_BROWSER:-}" ]]; then
  # `open` exists on macOS; elsewhere just print the URL.
  command -v open >/dev/null && open "http://localhost:$VIEWER_PORT" \
    || echo "Open http://localhost:$VIEWER_PORT in a browser."
fi

# 4. Give openpilot's daemons a moment to come up before MetaDrive starts feeding them.
echo "Waiting ${OPENPILOT_WARMUP}s for openpilot to come up..."
sleep "$OPENPILOT_WARMUP"

# 5. Foreground: the bridge (owns MetaDrive, reads keyboard). Ends when you press q.
python3 "$REPO_ROOT/av-sim/bridge/run_waypoint_bridge.py" "$@"
