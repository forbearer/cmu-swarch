#!/usr/bin/env bash
# Applies av-sim/patches/*.patch to openpilot's nested submodules and rebuilds what they touch.
# Idempotent: a patch that is already applied is skipped, and nothing is rebuilt if nothing changed.
# run_demo.sh calls this on every start, so `git submodule update` (which resets the submodule's
# working tree) is self-healing -- the next run_demo.sh re-applies and rebuilds.
#
# Why patches and not forks/commits: the targets are commaai's own submodules (openpilot, then
# msgq_repo inside it), pinned by the root repo. The patch files are the reviewable record of
# exactly how this demo differs from upstream.
#
# Currently only one patch:
#   msgq-macos-poll-1ms.patch  (msgq_repo) -- macOS-only; on Linux the patched code is not compiled
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OP="$REPO_ROOT/av-sim/openpilot"
changed=0

apply_patch() {  # apply_patch <patch file> <git work tree to apply it in>
  local patch="$1" tree="$2"
  if git -C "$tree" apply --reverse --check "$patch" 2>/dev/null; then
    return 0                                   # already applied
  elif git -C "$tree" apply --check "$patch" 2>/dev/null; then
    git -C "$tree" apply "$patch"
    echo "applied $(basename "$patch") to ${tree#"$REPO_ROOT"/}"
    changed=1
  else
    echo "ERROR: $(basename "$patch") neither applies nor is already applied in ${tree#"$REPO_ROOT"/} --" \
         "the pinned openpilot/msgq version probably changed; regenerate the patch." >&2
    exit 1
  fi
}

# The patched branch is under #ifdef __APPLE__, so on other platforms this is a harmless no-op.
if [[ "$(uname -s)" == "Darwin" ]]; then
  apply_patch "$REPO_ROOT/av-sim/patches/msgq-macos-poll-1ms.patch" "$OP/msgq_repo"
fi

if (( changed )); then
  echo "Rebuilding openpilot native code (scons -u, one-time, ~30s)..."
  # shellcheck disable=SC1091
  mkdir -p "$REPO_ROOT/av-sim/logs"
  if ! ( source "$OP/.venv/bin/activate" && cd "$OP" && scons -u -j"$(sysctl -n hw.ncpu 2>/dev/null || nproc)" ) \
      > "$REPO_ROOT/av-sim/logs/scons.out" 2>&1; then
    tail -20 "$REPO_ROOT/av-sim/logs/scons.out" >&2
    echo "ERROR: rebuild failed (full output: av-sim/logs/scons.out)" >&2
    exit 1
  fi
  echo "Rebuild done."
fi
