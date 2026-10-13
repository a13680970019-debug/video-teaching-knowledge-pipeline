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
# Keep pytest's scratch inside the repo (already git-ignored) instead of the
# system temp directory. The parent must exist first: pytest creates basetemp
# with mkdir(parents=False) and fails on a fresh clone otherwise.
mkdir -p .pytest-tmp
"$PY" -m pytest -q tests --basetemp=.pytest-tmp/run -p no:cacheprovider
echo

echo "== migrated core integrity =="
# Check the *blob*, not the working-tree file: with core.autocrlf=true the
# checkout is CRLF while the repository stores LF, so a working-tree sha256 is
# platform-dependent and would look like tampering on another machine.
EXPECTED_BLOB="96c348c593a5d314858b52cbd17a29d26bdf6b71"
EXPECTED_SHA256="993fe3932bb914868eab015e7e38e8db322b6f80f59736a5b14dcd4592fc48fb"
CORE="pipeline/knowledge_evidence_gate_v21.py"
if command -v git >/dev/null 2>&1 && git rev-parse --git-dir >/dev/null 2>&1; then
  actual_blob="$(git rev-parse "HEAD:$CORE" 2>/dev/null || echo '?')"
  actual_sha="$(git cat-file blob "HEAD:$CORE" | "$PY" -c 'import hashlib,sys; print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest())')"
  echo "blob   : $actual_blob"
  echo "sha256 : $actual_sha"
  [ "$actual_blob" = "$EXPECTED_BLOB" ] || { echo "FAIL: blob differs from the recorded migration"; exit 1; }
  [ "$actual_sha" = "$EXPECTED_SHA256" ] || { echo "FAIL: core content differs"; exit 1; }
  echo "ok - unchanged from the migrated source"
else
  echo "skipped: not a git checkout"
fi
echo

echo "ALL CHECKS PASSED"
