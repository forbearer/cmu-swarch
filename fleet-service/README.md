# Fleet Management Service

Node.js service tracking a table of AVs: identity, whereabouts, and latest travel status.
N-tier client/server style — deliberately the simplest of the three subsystems, architecturally
contrasting with AV Sim's robotic-control/pipeline style and the ML pipeline's blackboard-adjacent
style.

## Architecture

Connects out, as a WebSocket **client**, to each configured AV Sim instance's
`telemetry_server.py` (see `../av-sim/README.md`) — reusing its existing JSON telemetry contract
as-is rather than inventing a second protocol. The fleet service is just another consumer of that
stream, the same way the AV Sim's own browser viewer is.

```
AV Sim 1 (telemetry_server.py, ws://host:8765) ─┐
AV Sim 2 (telemetry_server.py, ws://host:8766) ─┼─> fleet-service (WebSocket client + aggregator)
AV Sim N ...                                    ─┘        │
                                                            ├─ GET /api/fleet       (JSON)
                                                            ├─ GET /api/fleet/:id   (JSON)
                                                            └─ GET /              (HTML dashboard)
```

Status per vehicle is derived, not stored directly:
- `offline` — no live WebSocket connection to that AV Sim's telemetry server.
- `stale` — connected, but no telemetry message in the last 3 seconds.
- `driving` — connected, fresh telemetry, `engaged: true`.
- `idle` — connected, fresh telemetry, `engaged: false`.

## Setup

```bash
cd fleet-service
npm install
```

## Configuration

Edit `fleet.config.json` to list vehicles:

```json
{
  "vehicles": [
    { "id": "av-1", "name": "AV Sim 1", "wsUrl": "ws://localhost:8765" }
  ]
}
```

Add one entry per running AV Sim instance (each needs its own `telemetry_server.py --port`, since
the AV Sim's telemetry server defaults to one fixed port — see `../av-sim/README.md`). Override
the config path with the `FLEET_CONFIG` env var.

## Running

```bash
npm start            # defaults to http://localhost:4000
PORT=4001 npm start   # override the port
```

Open `http://localhost:4000` for the table dashboard, or hit `/api/fleet` directly for JSON.

## Verified

Actually run end-to-end in this session (unlike AV Sim, which needs openpilot's heavier
dependencies): started the service with no AV Sim running (correctly showed `offline`), then
pointed a scratch WebSocket source at it emitting the same telemetry shape the real
`telemetry_server.py` sends — status correctly flipped to `driving`, lat/lon/speed updated live,
and on disconnect it correctly degraded to `offline` while retaining the last known position.
`/api/fleet`, `/api/fleet/:id`, the 404 case, and the dashboard HTML all checked directly.

**Not yet verified against a real running AV Sim** — only against a stand-in emitting the same
JSON shape. Confirm against `av-sim`'s actual `telemetry_server.py` once that's been run for
real.

## Open items

- No persistence — fleet state is in-memory and resets on restart. Fine for a course exercise;
  worth calling out explicitly if a quality-attribute discussion wants "availability across
  service restarts" as a requirement to design against.
- No travel-status concept beyond derived connectivity/engagement (e.g. no "current route
  progress" or "distance to destination B" yet) — depends on what AV Sim exposes once waypoint
  routing to arbitrary coordinates is built (see `../av-sim/README.md`'s open items).
