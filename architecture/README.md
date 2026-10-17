# Architecture Models

Component-and-connector (C&C) views of all three subsystems, following David Garlan's C&C
architectural style: components and connectors are both first-class, explicitly typed elements —
not just boxes-and-arrows. Written in real SysML v2 textual notation (not a generic diagram tool),
so the model itself is the source of truth, with a matching standalone SVG rendered from the same
data for quick viewing/embedding.

## Files

```
CCLibrary.sysml          # shared connector-type vocabulary, imported by all three models below
av-sim.sysml             # AV Sim + openpilot (openpilot modeled as a real component, not a black box)
fleet-service.sysml      # Fleet Management Service
ml-pipeline.sysml        # Perception ML Training Pipeline
av-sim.svg               # matching diagrams, generated from the same component/connector data
fleet-service.svg
ml-pipeline.svg
render_cc_diagram.py     # the generator -- edit its companion JSON spec, not the SVG directly
```

Each `.sysml` file maps directly onto `../av-sim/`, `../fleet-service/`, `../ml-pipeline/` as they
actually exist — component names reference real files (`waypoint_bridge.py`, `fleetStore.js`,
`train.py`, ...), and connectors reflect verified behavior, not an idealized design. Where a
model's claim depends on something confirmed end-to-end in this project (e.g. av-sim's `canBus`
connector being openpilot's real, unmodified `cereal` bus, genuinely engaging and driving), the
`doc` comment says so and points at the relevant README.

## The connector vocabulary (`CCLibrary.sysml`)

Five reusable connector types, each a SysML v2 `interface def` with a `doc` naming its Garlan
connector style explicitly:

| Connector type | Garlan style | This project's real instance |
|---|---|---|
| `ProcedureCallConnector` | Procedure Call | synchronous in-process function calls |
| `PublishSubscribeConnector` | Publish-Subscribe | openpilot's own `cereal` messaging bus |
| `StreamConnector` | Event/Stream (push) | a WebSocket |
| `RepositoryConnector` | Repository (shared data) | plain files on disk |
| `RequestReplyConnector` | Request-Reply | HTTP/REST |

All three system models import this one vocabulary and instantiate it between their own
components (`interface <name> : <ConnectorType> connect <partA.port> to <partB.port>;`), so the
same five types, drawn and named consistently, make cross-system comparison direct — e.g. AV
Sim's robotic-control/pub-sub style, the fleet service's N-tier client/server style, and the ML
pipeline's pipe-and-filter-over-a-repository style are visibly different connector-type profiles
of the same five building blocks, not three unrelated diagrams.

## Verified legal syntax

Checked against a real, independent SysML v2 parser — not just hand-checked against the spec.
Built [`sysml2`](https://github.com/zbigniewsobiecki/sysml2) (a standalone C implementation, PEG
grammar from the OMG spec) from source, and ran full semantic validation (reference resolution,
not just grammar) against all four files, individually and together:

```bash
# one-time: clone + build
git clone https://github.com/zbigniewsobiecki/sysml2.git && cd sysml2
mkdir build && cd build && cmake .. && make

# validate (run from an otherwise-empty directory containing just these .sysml files --
# the tool has a noisy default behavior of also reporting on its own bundled test fixtures
# if run from near its own source tree, unrelated to your files)
./sysml2 CCLibrary.sysml av-sim.sysml fleet-service.sysml ml-pipeline.sysml
```

Confirmed 2026-10-16: exit code 0, zero errors, for all four files both individually and
together. Also confirmed the tool actually catches real errors (deliberately broke a port
reference, got a precise `error[E3001]: undefined type` back) before trusting a clean result on
the real files.

**Not yet verified: actually opening these in SysON** (Owen has it installed locally). The
textual syntax is confirmed legal against an independent parser, but SysON's own import/rendering
behavior — and whether its own C&C diagram view matches `render_cc_diagram.py`'s output — hasn't
been checked yet. Worth doing and reporting back.

## Regenerating the SVGs

`render_cc_diagram.py` takes a JSON spec (component list with ports, connector list referencing
`CCLibrary`'s five types) and renders a standalone, dependency-free SVG — ports as small black
squares, connectors colored/dashed by type with an auto-generated legend, matching the
`.sysml` file's own component and connector names exactly. If a `.sysml` model changes, the
intent is to update the SVG by hand (same discipline as the rest of this project's SysML-v2-first
documents) rather than treating the script as a live compiler from one to the other.

## What's deliberately not modeled here

- **Behavior.** These are structural C&C views only — no state machines, no action flows (SysML
  v2 supports both; out of scope for an architecture-styles comparison).
- **Full connector protocol fidelity.** E.g. `ProcedureCallConnector` doesn't model the
  call-and-return pair formally, just the invocation direction — enough to convey "this is a
  synchronous call," not a full interaction contract. The `doc` comments carry the nuance that
  the formal model intentionally simplifies.
