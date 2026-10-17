# Assignment: Fleet Management with Three AVs

A worked scenario for the **Fleet Management Service** (`../../fleet-service/`): three AV
instances running concurrently, each demonstrating a different fleet status, so the service's
aggregation/derivation logic is actually visible rather than theoretical.

## What's here, and what isn't

**Three mock AV telemetry sources** (`mock_av.mjs`), each emitting the exact JSON contract
`av-sim/bridge/telemetry_server.py` produces (`t`, `lat`, `lon`, `alt`, `yaw`, `speed`,
`engaged`) over its own WebSocket — fleet-service can't tell these apart from a real running AV
Sim instance. It's a stand-in for *the simulator*, not for the fleet service itself.

**Not three real openpilot+MetaDrive stacks.** Each one needs its own 4-terminal setup
(`av-sim/README.md`'s Running section) and real CPU/GPU budget — running three concurrently
isn't a reasonable ask for a laptop. For illustrating the fleet service's own architecture
specifically (N-tier client/server, aggregation, derived status), three lightweight stand-ins
make the point without the cost. **You can swap any one mock for a real AV Sim** — point its
`wsUrl` in `fleet.config.json` at a real `telemetry_server.py` instance instead, and nothing else
changes.

## The three scenarios

| Vehicle | Pattern | What it demonstrates |
|---|---|---|
| `av-1` | `loop` — drives a small circular route forever | `status: driving` |
| `av-2` | `idle` — connected, `engaged: false`, stationary | `status: idle` |
| `av-3` | `disconnect` — drives for 15s, then the process exits | `status: driving` → **`offline`**, and stays there |

`av-3` is deliberately a process **exit**, not just closing one connection. fleet-service's
`avConnector.js` auto-reconnects within 2s by design (correct, resilient behavior for a real
flaky link) — if the mock server just dropped one socket and kept listening, "offline" would
flash by almost invisibly as it immediately reconnects. An actual crashed/stopped AV Sim is a
closer real-world match anyway: the process is genuinely gone, reconnect attempts genuinely fail,
and "offline" sticks — verified 2026-10-16, stayed offline for 5+ seconds of continued polling,
not a flicker.

## Running

```bash
cd assignments/fleet-3av-demo
npm install

node mock_av.mjs --port 8765 --lat 40.4433 --lon -79.9436 --speed 8 --pattern loop &
node mock_av.mjs --port 8766 --lat 40.4500 --lon -79.9500 --pattern idle &
node mock_av.mjs --port 8767 --lat 40.4600 --lon -79.9300 --speed 5 --pattern disconnect &

FLEET_CONFIG="$PWD/fleet.config.json" PORT=4001 node ../../fleet-service/src/server.js
```

Open `http://localhost:4001` for the dashboard, or poll `http://localhost:4001/api/fleet`. Watch
`av-3` transition from `driving` to `offline` around the 15s mark.

## Verified

Ran the full scenario end-to-end 2026-10-16: all three vehicles connected and showed their
expected status within 2s; `av-3` correctly transitioned to `offline` at the 15s mark and stayed
there through continued polling (not a reconnect flicker); fleet-service's own retry log showed
it correctly retrying every 2s indefinitely rather than giving up — confirming the resilience
behavior this scenario is meant to showcase actually works as designed, not just in theory.

## Assignment ideas

- Add a fourth vehicle with a new pattern (e.g. `stale` — connected, telemetry stops updating but
  the socket stays open) and confirm `fleetStore.js`'s `stale` status (connected, no telemetry in
  3s) actually fires, not just `offline`.
- Swap one mock for a real AV Sim instance (`av-sim/bridge/telemetry_server.py --port 876x`) and
  confirm the fleet dashboard shows it identically to the mocks — a concrete way to verify the
  "same contract, different producer" claim above.
- Extend `fleetStore.js` with a new derived field (e.g. estimated time to a stale/offline
  transition) and have `mock_av.mjs`'s patterns exercise it.
