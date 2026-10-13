# Quickstart

Everything below was executed on Windows 11 with Python 3.13 and Git Bash.
See `docs/VALIDATION_REPORT.md` for the recorded run.

## 1. Get the code

```bash
git clone https://github.com/a13680970019-debug/video-teaching-knowledge-pipeline.git
cd video-teaching-knowledge-pipeline
git checkout feat/public-reproducible-demo-20261013
```

## 2. Create a clean environment

The demo has **no runtime dependencies** beyond the Python standard library.

```bash
python -m venv .venv
.venv/Scripts/python -m pip install pytest   # only needed for the tests
```

## 3. Run the demo

```bash
python -m pipeline.demo_gate_review \
  --input examples/synthetic/evidence_samples.jsonl \
  --output outputs/main
```

Expected: exit code `0` and a gate summary ending in

```json
"gate_decision": "CONDITIONAL_PASS"
```

Read the review list:

```bash
cat outputs/main/review_list.csv
```

## 4. Try the failure paths

```bash
# a critical unit that loses source binding -> gate FAIL (still exit 0)
python -m pipeline.demo_gate_review \
  --input examples/synthetic/evidence_hard_fail.jsonl --output outputs/hard_fail

# contract violation -> exit 3, nothing written
python -m pipeline.demo_gate_review \
  --input examples/synthetic/invalid_missing_field.jsonl --output outputs/invalid

# missing file -> exit 2, nothing written
python -m pipeline.demo_gate_review \
  --input examples/synthetic/does_not_exist.jsonl --output outputs/nope
```

## 5. Run the tests

```bash
python -m pytest -q tests
```

Expected: `48 passed`.

## 6. Check the output against the hand-derived expectation

`examples/expected/README.md` explains the rules used to write the expected
values by hand before the demo was run. The test suite asserts that the
observed output matches them.
