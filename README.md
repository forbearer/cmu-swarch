# SWArch Course Autonomous Vehicle Sim

A teaching project for Carnegie Mellon's Software and Societal Systems Department, built for the
Software Architecture course. Developed with Owen Cheng in collaboration with the course
professor.

## Motivation

We lack a software-intensive system that is complex yet lightweight enough to fit into a single
semester course, while still teaching the real concepts of software architecture.

## Objectives

1. A complex software-intensive project for architectural evaluation, rich in quality attributes.
2. Capable of iterative refinement over the semester.
3. Potentially supportive of more than one architectural style.
4. Incorporates modern software development practices, ideally including use of GenAI.
5. Shape the next decade of the architecture course as a teaching tool.

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
- Requirements
- Design artifacts
- ROS? (TBD whether we adopt ROS as a messaging layer, or keep openpilot's own `cereal` IPC)
- Test cases

Pitfalls to watch for:
- What decisions led up to that architecture? Usually lost. Can it be applied retroactively?
- (Owen's proposal left a second bullet open here — TBD.)

## Software Architecture Course Applicability

- **Architectural styles:** robotic control, pipeline, N-tier client/server, blackboard.
- **Quality attributes:** safety, performance, security, among others.
- ...

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

Training pipeline built on openpilot's existing perception/ML components. Lets students tweak
training inputs and parameters, then observe the resulting change in AV Sim driving behavior.
Pipeline/blackboard-adjacent architectural style, distinct from the other two subsystems.

## Repository Layout

_To be established as implementation starts — placeholder until the first subsystem is scaffolded._

## Status

Early planning stage. Proposal drafted by Owen; this README ports that proposal and will be kept
up to date as the project's architecture and scope are decided.

## Open Questions

- Unreal-like rendering: which of the three AV Sim rendering options above (re-render MetaDrive
  state in-browser, swap to a CARLA/Unreal bridge, or a simplified custom renderer) fits the
  course's time budget and teaching goals?
- ROS: adopt it as a messaging layer for part of the system (for architectural-style contrast with
  openpilot's native `cereal` IPC), or leave it out?
- The second reference project (ROS-based, from a Mathworks symposium) — name/link still needed
  from Owen.
- Scope and sequencing across a single semester: which of the three subsystems do students build
  first, and which ship as instructor-provided scaffolding vs. student deliverables?
- The proposal's two open pitfall bullets (retroactively recovering lost architectural decisions)
  — not yet filled in.
