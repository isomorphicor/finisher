#!/usr/bin/env bash
# Smoke test: scheme (plan) + IDE (code) in one run.
# See: docs/experiments/smoke_plan_and_code.md
# Requires Python 3.10+ (repo uses PEP 604 types). Set PYTHON=/path/to/python3.11 to override.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

pick_python() {
  if [[ -n "${PYTHON:-}" && -x "${PYTHON}" ]]; then
    echo "${PYTHON}"
    return 0
  fi
  local cand
  for cand in \
    "/opt/miniconda3/bin/python3" \
    "${HOME}/.local/bin/python3.11" \
    "$(command -v python3.13 2>/dev/null)" \
    "$(command -v python3.12 2>/dev/null)" \
    "$(command -v python3.11 2>/dev/null)" \
    "$(command -v python3.10 2>/dev/null)" \
    "$(command -v python3 2>/dev/null)"; do
    [[ -z "${cand}" || ! -x "${cand}" ]] && continue
    if "${cand}" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
      echo "${cand}"
      return 0
    fi
  done
  return 1
}

PY="$(pick_python)" || {
  echo "smoke_research_session: need Python 3.10+. Set PYTHON=/path/to/python3." >&2
  exit 1
}
echo "Using ${PY} ($("${PY}" --version))" >&2

TASK_FILE="$ROOT/scripts/smoke_research_session_task.txt"
if [[ ! -f "$TASK_FILE" ]]; then
  echo "Missing $TASK_FILE" >&2
  exit 1
fi

# Session dir must lie under --workspace-root or prepare_execution_workspace rejects (E_SESSION_PATH).
# Default: <repo>/out/ (gitignored) so smoke works with --workspace-root "$ROOT".
if [[ "${INVERST_SCHEME_PHASE_RUNS:-}" == "" ]]; then
  export INVERST_SCHEME_PHASE_RUNS="${ROOT}/out"
fi
mkdir -p "${INVERST_SCHEME_PHASE_RUNS}"
echo "Using INVERST_SCHEME_PHASE_RUNS=$INVERST_SCHEME_PHASE_RUNS" >&2

# shellcheck disable=SC2002
SMOKE_TASK="$(cat "$TASK_FILE")"

exec "${PY}" scripts/run_research_session.py \
  --project smoke_plan_code \
  --session main \
  --scheme-max-rounds 45 \
  --ide-max-rounds 35 \
  --workspace-root "$ROOT" \
  "$SMOKE_TASK"
