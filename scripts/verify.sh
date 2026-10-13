#!/usr/bin/env bash
#
# One-command verification of the public demo.
#
# Runs the same checks the CI workflow would run, so a reviewer can reproduce
# the whole acceptance story locally without any CI service.
#
# Usage:
#   bash scripts/verify.sh              # uses `python` from PATH
#   PYTHON=/path/to/python bash scripts/verify.sh

set -euo pipefail

cd "$(dirname "$0")/.."
PY="${PYTHON:-python}"

echo "== environment =="
"$PY" --version
if ! "$PY" -c "import pytest" >/dev/null 2>&1; then
  echo
  echo "error: pytest is not installed for this interpreter." >&2
  echo "       The demo itself has no runtime dependencies; only the test" >&2
  echo "       suite needs pytest. Install it with:" >&2
  echo "         $PY -m pip install pytest" >&2
  echo "       Or point PYTHON at an interpreter that has it." >&2
  exit 4
fi
echo

echo "== compile sources =="
"$PY" -m compileall -q pipeline tests
echo "ok"
echo

echo "== demo: main sample set (expect exit 0, gate CONDITIONAL_PASS) =="
"$PY" -m pipeline.demo_gate_review \
  --input examples/synthetic/evidence_samples.jsonl \
  --output outputs/main
echo

echo "== demo: fail closed on a contract violation (expect exit 3) =="
set +e
"$PY" -m pipeline.demo_gate_review \
  --input examples/synthetic/invalid_missing_field.jsonl \
  --output outputs/invalid
code=$?
set -e
echo "observed exit_code=$code (expected 3)"
[ "$code" -eq 3 ] || { echo "FAIL: expected exit 3, got $code"; exit 1; }
[ ! -d outputs/invalid ] || { echo "FAIL: outputs/invalid must not exist"; exit 1; }
echo "ok"
echo

echo "== demo: fail closed on a missing input file (expect exit 2) =="
set +e
"$PY" -m pipeline.demo_gate_review \
  --input examples/synthetic/does_not_exist.jsonl \
  --output outputs/nope
code=$?
set -e
echo "observed exit_code=$code (expected 2)"
[ "$code" -eq 2 ] || { echo "FAIL: expected exit 2, got $code"; exit 1; }
[ ! -d outputs/nope ] || { echo "FAIL: outputs/nope must not exist"; exit 1; }
echo "ok"
echo

echo "== test suite =="
"$PY" -m pytest -q tests --basetemp=.pytest-tmp/run -p no:cacheprovider
echo

echo "ALL CHECKS PASSED"
