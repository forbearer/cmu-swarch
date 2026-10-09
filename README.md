# SWArch Course Autonomous Vehicle Sim

A proposed teaching instrument built for Carnegie Mellon's Software and Societal Systems
Department (S3D), Professor Garlan's Software Architecture course.  Developed by Owen Cheng in
collaboration with the course instructors Professor David Garlan, Dr. Bradley Schmerl, and
Dr. George Fairbanks, as well as course advisors Jonathan Aldrich, Shihong Huang, Eunsuk Kang,
Ehab Al-Shaer, and Andres Diaz-Pace.

## Motivation

The software architecture course lacks a complex software-intensive system that is lightweight yet
rich enough to fit into a single semester course, to enable students to practice the taught
concepts.

## Objectives

1. Complex software-intensive project for architectural evaluation, rich in quality attributes.
2. Designed to enable students to iterative refine over the semester.
3. Supports more than one architectural style.
4. Incorporates modern software development practices, including the use of Generative AI.
5. Retroactively applicable, but also forward design available. (TODO: Reword confusing bullet.)
6. Shapes the next decade of the software architecture course as a teaching instrument.

## The Autonomous Vehicle (AV) Sim Project

Self-driving technology has been around for over a decade and AVs are now commonplace on public
roads. The software that goes into the AV is complex, and spans classical ML and control. The
software needed to train the ML model on an AV is another complex software infrastructure of a
different architectural style. The fleet management system necessary to manage a fleet of such
vehicles provides an additional ecosystem with a different architecture.

Source projects:
- [commaai/openpilot](https://github.com/commaai/openpilot) — open-source driver-assistance
  stack; our primary base.
- A second, ROS-based reference project from a Mathworks symposium (pointer TBD — Owen to supply
  link/name).

Features to draw out as teaching artifacts:
- Relevant system, business, technical, and other requirements
- Architectural models, of different styles
- Quality attributes and tradeoffs
- Design artifacts and their dependence and influence on architecture
  - ROS? (TBD whether we adopt ROS as a messaging layer, or keep openpilot's own `cereal` IPC)
- Test cases to provide signals on architectural tactics and tradeoff decisions

## Software Architecture Course Applicability

This section explores the applicability of the AV Sim to the course, topic by topic.
However, there are existing system examples already in use, so a better approach is to evaluate
what makes sense to shift to using this project as the common thread throught the course.

_Note_: Mapping of topics to the Course Schedule table on the [Spring 2025 Syllabus](https://mse.s3d.cmu.edu/courses/0_syllabi/17-633882-architectures-for-software-systems-2025-syllabus.docx.pdf).

- **Architectural Drivers**: in addition to technological, the business case, time-to-market,
  regulatory policy, public trust, etc.
- **Quality Attributes**: safety, performance, security, among others.
- **Architectural styles**: event-driven (robotic control), dataflow (ML pipeline),
  call return (N-tier client/server), repository (blackboard).
- **Architectural Tactics and Frameworks**:
  - evaluate modifiability of openpilot and our AV ecosystem built on top.
  - evaluate compatibility and mismatch of the model training swap-in prototyped by Claude.
- **Architecture Evaluation**: evaluate the architecture of AV Sim and its ecosystem.
- **Architecture Documentation**: build up documentation for AV Sim.
  - Connected to **Architecture Recovery** due to extensive existing code base.
- **Architecture Design Records**: leverage ADR to decide next-step evolution of the AV.
- **Architecture Modeling**: model AV Sim ecosystem in C4.
- **Architecture Hoisting and Evident Coding**: AV Sim is rich for this exploration, but will
  require upfront work by instructors and collaborators.
- **Architecture as Theory Building**: TODO: George for help with whether there is applicability.
- **Architecture and Tactics for AI**:
  - Either front-and-center, or a side-topic: the AV Sim was initially built up and improved upon
    using Claude.

## Pitfalls and Challenges

We will need to address some challenges to build up this teaching instrument.
- How much IT and staff support resources are necessary to build this up?
- Are instructors plus outside collaborator help sufficent to maintain this?

Some pitfalls to watch out for:
- What design choices and decisions led up to that architecture? Usually lost.
- Can these decisions be discovered retroactively?
- What may be time-syncs for students without adding instruction value?


## System Components

Three subsystems, each deliberately in a different architectural style, so students compare them
directly within one coherent domain:

1. **AV Sim** — drive a simulated vehicle from waypoint A to waypoint B, built on openpilot,
   viewable in a browser.
2. **Fleet Management Service** — a Node.js web service tracking a fleet of AVs: table of
   vehicles, whereabouts, latest travel status.
3. **Perception ML Training Pipeline** — a training pipeline (built on openpilot's existing
   perception stack) that feeds trained behavior back into the AV Sim, with tunable inputs/
   parameters so students can observe how training choices change driving behavior.

### 1. AV Sim

**Grounding on openpilot's actual simulation story** (checked against openpilot's own repo and
docs, not assumed): openpilot already ships `tools/sim`, a bridge that runs the real openpilot
stack (driving policy + controls) against the **MetaDrive** simulator — a lightweight,
Panda3D-based driving simulator, not Unreal Engine. There is no built-in Unreal integration to
reuse.

Implication for the "Unreal-engine-like output in browser" ask: that visual fidelity isn't
something we inherit for free from openpilot. Options to evaluate together:
- Run openpilot against MetaDrive headless, and stream/re-render the scene into the browser via a
  web-based 3D layer (e.g. three.js) driven by the same simulation state — architecturally
  closer to "pipeline feeding a presentation tier," itself a nice teaching example of translating
  server-side sim state into a separate rendering client.
- Swap in a different bridge target (openpilot has at times supported CARLA, which has an Unreal
  Engine core) — heavier to run, more realistic visuals, more infrastructure for students to
  reason about.
- Build a deliberately simplified custom renderer instead of chasing high fidelity, since the
  course's goal is architecture pedagogy, not visual realism.

This is an open decision — see Open Questions below.

### 2. Fleet Management Service

Node.js web service. Tracks a table of AVs: identity, current whereabouts, latest travel status.
Consumes telemetry from one or more running AV Sim instances. N-tier client/server style.

### 3. Perception ML Training Pipeline

**Revised from the original framing** (see `ml-pipeline/README.md` for the full reasoning):
openpilot ships no public training code or dataset for its own driving model, only a pre-trained
compiled artifact, so "retrain openpilot's existing ML components" isn't actually buildable.
Instead: record driving sessions directly from the AV Sim (camera frames + applied controls),
train a small behavior-cloning model on them, and drop the trained model back in as an
alternative driving policy. Students tweak training inputs/parameters and observe the resulting
change in AV Sim driving behavior — same stated goal, reachable path. Pipeline/blackboard-adjacent
architectural style, distinct from the other two subsystems.

## Repository Layout

```
av-sim/              # AV Sim subsystem (in progress, see av-sim/README.md)
  openpilot/          # git submodule: commaai/openpilot, pinned
  bridge/             # waypoint-driving bridge + telemetry WebSocket server
  viewer/             # browser viewer (three.js, no build step)
fleet-service/        # Fleet Management Service (scaffolded + verified, see fleet-service/README.md)
  src/                # Express API + WebSocket client(s) into AV Sim telemetry
  public/             # table dashboard
ml-pipeline/          # Perception ML Training Pipeline (scaffolded, see ml-pipeline/README.md)
  bridge/              # recorder + trained-policy playback (touches the simulator)
  dataset.py, model.py, train.py, policy.py   # standalone, torch-only
```

## Development Status

**2026-10-08 — AV Sim scaffolded, not yet run end-to-end.** Decided: browser rendering via a
lightweight three.js viewer fed by openpilot's own telemetry (not CARLA/Unreal, not a from-scratch
renderer — see Open Questions below for the tradeoff). AV Sim is first in build order, since fleet
service and the ML pipeline both consume its output.

Added `av-sim/openpilot` as a git submodule (pinned at `a742df6`), plus a `waypoint_bridge.py`
that re-enables MetaDrive's own point-to-point driving task (openpilot's stock sim demo loops a
closed-loop track forever instead — confirmed by reading `tools/sim/bridge/metadrive/
metadrive_bridge.py` directly) and a `telemetry_server.py` that subscribes to openpilot's own
cereal message bus and republishes state over a WebSocket for the browser viewer. Full detail,
including what "waypoint A to B" does and doesn't mean yet, is in `av-sim/README.md`.

**Not yet verified end-to-end** — written and checked against openpilot's actual source (paths,
class names, cereal schema fields all confirmed against commit `a742df6`), but not yet executed
on real hardware. That needs a run on a machine with openpilot's dependencies installed.

**Fleet Management Service scaffolded and actually verified end-to-end** (unlike AV Sim, this one
has no heavy native dependencies, so it could be run directly in this session): Express API +
dashboard, connecting out as a WebSocket client to each AV Sim's `telemetry_server.py`. Confirmed
`offline` with no AV Sim running, confirmed `driving` with live lat/lon/speed against a stand-in
telemetry source emitting the real contract shape, confirmed degradation back to `offline` on
disconnect. Full detail in `fleet-service/README.md`. Not yet checked against a real running AV
Sim, only a stand-in emitting the same JSON shape.

**Perception ML Training Pipeline scaffolded, with its design revised from the original
proposal** after checking openpilot's actual source: no public training code/dataset exists for
its driving model, so the pipeline instead records sessions from the AV Sim itself and trains a
small behavior-cloning model on them (full reasoning in `ml-pipeline/README.md`). The standalone
ML code (`dataset.py`/`model.py`/`train.py`/`policy.py`) was actually run end-to-end against a
synthetic dataset in this session — training, checkpointing, and loading the checkpoint for
inference all verified for real. The three files that touch the actual simulator
(`bridge/recording_world.py`, `bridge/run_record_session.py`, `bridge/run_trained_policy.py`) are
written and checked against openpilot/MetaDrive's real interfaces, same as AV Sim, but not yet
run — needs a real simulator environment.

All three subsystems now scaffolded. Next real step across the project: an actual run of AV Sim
(and by extension the ML pipeline's simulator-touching pieces) on a machine with the dependencies
installed.

## Open Questions

- ~~Unreal-like rendering~~ **Decided 2026-10-08:** re-render MetaDrive/openpilot telemetry
  in-browser via three.js (option 1). CARLA/Unreal stays an option to revisit later if the course
  wants higher visual fidelity than this gives.
- Arbitrary waypoint coordinates (student types in A and B) vs. MetaDrive's own randomly
  generated start/destination (what's implemented now) — needs MetaDrive's navigation/route API,
  not yet looked into.
- ROS: adopt it as a messaging layer for part of the system (for architectural-style contrast with
  openpilot's native `cereal` IPC), or leave it out?
- The second reference project (ROS-based, from a Mathworks symposium) — name/link still needed
  from Owen.
- Scope and sequencing across a single semester: which of the three subsystems do students build
  first, and which ship as instructor-provided scaffolding vs. student deliverables?
- The proposal's two open pitfall bullets (retroactively recovering lost architectural decisions)
  — not yet filled in.
