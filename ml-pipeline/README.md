# Perception ML Training Pipeline

A behavior-cloning training pipeline, built directly on the AV Sim: record driving sessions,
train a small model on them, then drop the trained model back in as an alternative driving
policy and watch the AV Sim's behavior change. Pipeline/blackboard-adjacent architectural style,
distinct from AV Sim's robotic-control style and the fleet service's N-tier client/server style.

## Why this design, and not "retrain openpilot's own model"

Checked directly against the `av-sim/openpilot` submodule (commit `a742df6`) before building
anything: `openpilot/selfdrive/modeld/` only contains **inference** code. The real driving model
(`driving_supercombo.onnx`, 60MB) is a pre-trained, compiled artifact distributed via git-lfs —
there's no training code or dataset for it in the public repo. comma.ai does publish one real
public dataset, [comma10k](https://github.com/commaai/comma10k) (10k labeled real-world driving
images, for road segmentation) — but it's real-world photography, disconnected from MetaDrive's
synthetic rendering, and wiring a segmentation net into openpilot's own control path to visibly
change driving behavior is a large integration lift with no fast feedback loop. Neither fits a
semester course's "tweak parameters, see behavior change" goal.

So instead: record training data **directly from the AV Sim itself** (camera frames it's already
rendering, paired with whatever control was actually applied at that tick), train a small model
on that, and let the trained model drive in place of openpilot's own stack. This is still
genuinely "built on what openpilot already has" — it reuses the AV Sim's existing camera
rendering and the `World` interface AV Sim already defines — without inventing a connection to
training infrastructure that doesn't exist.

## Architecture

```
bridge/run_record_session.py  ─┐  (reuses av-sim's WaypointMetaDriveBridge; drive manually or
                                │   let openpilot engage -- every applied control gets logged
                                │   alongside the frame it was applied to)
                                ▼
                     frames/*.png + labels.csv   (a "session": one dataset_dir)
                                │
                                ▼
dataset.py + model.py + train.py   (standalone -- no openpilot/MetaDrive imports, runs anywhere
                                │    torch is installed)
                                ▼
                          checkpoint.pt
                                │
                                ▼
bridge/run_trained_policy.py   (drives MetaDrive directly via WaypointMetaDriveBridge.spawn_world(),
                                 bypassing openpilot's own SimulatorBridge._run() loop entirely --
                                 the trained model's output goes straight to world.apply_controls())
```

The recorder (`bridge/recording_world.py`) hooks `MetaDriveWorld.apply_controls()` — the one call
openpilot's own bridge loop already makes every tick with the exact steer/throttle/brake about to
be applied — and reads `world.road_image`, the plain RGB frame array MetaDrive's background
process fills continuously. This is the frame *before* it gets re-encoded to NV12 and published
over VisionIPC for openpilot's own perception stack, so there's no VisionIPC/YUV decoding
involved at all — one clean, already-shared-memory integration point.

## What's tunable (the actual course exercise)

`train.py` exposes, all via CLI flags: learning rate, epochs, batch size, model capacity
(`--width`, a channel-count multiplier), dataset size (`--max-samples`), and which recorded
session(s) to train on (multiple `dataset_dirs` get concatenated). Re-running
`bridge/run_trained_policy.py` with a different checkpoint makes the effect of each choice
directly observable in the sim.

## Setup

```bash
cd ml-pipeline
pip install -r requirements.txt          # torch, numpy, pillow -- standalone, no openpilot deps
```

`bridge/*.py` additionally need `av-sim`'s own environment (openpilot's venv, built via
`av-sim/openpilot/tools/op.sh setup` + `scons -u` — see `../av-sim/README.md`), since those
scripts drive the actual simulator.

## Running

```bash
# 1. Record a session (drive manually with the AV Sim's own keyboard controls, or let openpilot
#    engage -- see ../av-sim/README.md's bridge controls)
python3 bridge/run_record_session.py --dataset-dir data/session1

# 2. Train (standalone -- doesn't need the simulator running)
python3 train.py data/session1 --epochs 10 --lr 1e-3 --width 1.0 --out checkpoint.pt

# 3. Watch the trained model drive
python3 bridge/run_trained_policy.py checkpoint.pt
```

## Verified

**The standalone ML code (`dataset.py`, `model.py`, `train.py`, `policy.py`) was actually run
end-to-end in this session**, against a synthetic fake dataset (random frames + random
steer/throttle/brake labels): training ran for real, produced decreasing-then-stable loss,
saved a checkpoint, and `policy.py` loaded that checkpoint and produced a real prediction from a
synthetic frame. Also checked the multi-dataset-dir and `--max-samples` code paths.

**Not yet verified: the three files that touch the actual simulator**
(`bridge/recording_world.py`, `bridge/run_record_session.py`, `bridge/run_trained_policy.py`).
Written and checked against openpilot/MetaDrive's real interfaces (`World`'s abstract methods,
`SimulatorState`, frame dimensions, `Ratekeeper`, all read directly from
`av-sim/openpilot/openpilot/tools/sim/lib/common.py` and `metadrive_world.py`), but this
environment has no GPU/display to actually run the simulator — same situation as AV Sim itself.
Needs a real run on a machine with `av-sim`'s environment set up.

## Open items

- `run_trained_policy.py` always applies `brake=0` unless the model predicts a negative
  longitudinal command rather than ever requesting a hard stop near the arrival waypoint —
  reasonable for a first pass, worth revisiting once there's a real trained model to observe.
- No data augmentation (flips, brightness jitter, etc.) — fine as a first pass; a natural
  extension exercise once the base pipeline is confirmed working.
- Frame/label alignment assumes `apply_controls()` is called at a steady rate; if MetaDrive ever
  skips ticks under load, recorded pairs could drift slightly out of sync. Not expected to matter
  at this scale, but worth keeping in mind if recordings look noisy.
