"""Tests for the public demo adapter.

They cover the documented input contract, the failure paths, source tracing and
the reproducibility contract of the demo entry point.  The migrated core
library has its own separate test module.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline.demo_gate_review import (
    REVIEW_FIELDS,
    load_records,
    run,
    validate_record,
)

REPO_ROOT = Path(__file__).parents[1]
SAMPLES = REPO_ROOT / "examples" / "synthetic" / "evidence_samples.jsonl"
HARD_FAIL = REPO_ROOT / "examples" / "synthetic" / "evidence_hard_fail.jsonl"
INVALID = REPO_ROOT / "examples" / "synthetic" / "invalid_missing_field.jsonl"


def _valid_record(**overrides):
    record = {
        "sample_id": "SYN-T001",
        "episode_key": "synthetic:test:P001",
        "sample_kind": "UNCERTAINTY",
        "risk_type": "NUMBER",
        "declared_knowledge_type": "NUMBER",
        "cue_index": "1",
        "cue_start": "00:00:01.000",
        "cue_end": "00:00:04.000",
        "original_text": "平均数是 42",
        "audio_window_text": "平均数是 42",
        "audio_state": "AUDIO_RECOVERABLE",
        "source_binding": True,
        "audio_sha256": "a" * 64,
        "clip_sha256": "b" * 64,
        "window_start_seconds": 1.0,
        "window_end_seconds": 4.0,
        "audio_duration_seconds": 60.0,
    }
    record.update(overrides)
    return record


# --- input contract -------------------------------------------------------


def test_valid_record_has_no_contract_errors():
    assert validate_record(_valid_record(), 0) == []


def test_missing_field_is_reported():
    record = _valid_record()
    record.pop("clip_sha256")
    errors = validate_record(record, 0)
    assert any("clip_sha256" in e for e in errors)


def test_empty_field_is_reported():
    errors = validate_record(_valid_record(original_text="   "), 0)
    assert any("original_text" in e for e in errors)


def test_bad_timecode_is_reported():
    errors = validate_record(_valid_record(cue_start="0:1:2"), 0)
    assert any("cue_start" in e for e in errors)


def test_bad_hash_is_reported():
    errors = validate_record(_valid_record(clip_sha256="XYZ"), 0)
    assert any("clip_sha256" in e for e in errors)


def test_non_boolean_source_binding_is_reported():
    errors = validate_record(_valid_record(source_binding="true"), 0)
    assert any("source_binding" in e for e in errors)


def test_duplicate_sample_id_is_reported(tmp_path: Path):
    path = tmp_path / "dup.jsonl"
    row = json.dumps(_valid_record(), ensure_ascii=False)
    path.write_text(row + "\n" + row + "\n", encoding="utf-8")
    _, errors = load_records(path)
    assert any("duplicate sample_id" in e for e in errors)


# --- failure paths --------------------------------------------------------


def test_missing_input_file_returns_exit_2(tmp_path: Path):
    gate, code = run(tmp_path / "absent.jsonl", tmp_path / "out")
    assert code == 2 and gate == {}
    assert not (tmp_path / "out").exists()


def test_invalid_input_returns_exit_3_and_writes_nothing(tmp_path: Path):
    gate, code = run(INVALID, tmp_path / "out")
    assert code == 3 and gate == {}
    assert not (tmp_path / "out").exists()


# --- happy path and reproducibility ---------------------------------------


def test_main_sample_set_is_conditional_pass(tmp_path: Path):
    gate, code = run(SAMPLES, tmp_path / "out")
    assert code == 0
    assert gate["record_count"] == 7
    assert gate["gate_decision"] == "CONDITIONAL_PASS"
    assert gate["accepted_critical_count"] == 3
    assert gate["blocked_critical_count"] == 3
    assert all(value == 0 for value in gate["hard_fail_conditions"].values())


def test_hard_fail_sample_set_fails_closed(tmp_path: Path):
    gate, code = run(HARD_FAIL, tmp_path / "out")
    assert code == 0
    assert gate["gate_decision"] == "FAIL"
    assert gate["critical_source_binding_failure"] == 1


def test_demo_is_offline(tmp_path: Path):
    gate, _ = run(SAMPLES, tmp_path / "out")
    assert gate["network_used"] is False
    assert gate["model_used"] is False
    assert gate["audio_opened"] is False
    assert gate["production_paths_written"] == 0


def test_run_is_repeatable(tmp_path: Path):
    first, _ = run(SAMPLES, tmp_path / "a")
    second, _ = run(SAMPLES, tmp_path / "b")
    keys = ("gate_decision", "accepted_critical_count", "blocked_critical_count", "input_sha256")
    assert {k: first[k] for k in keys} == {k: second[k] for k in keys}


def test_outputs_are_written_only_inside_output_root(tmp_path: Path):
    out = tmp_path / "isolated"
    run(SAMPLES, out)
    assert sorted(p.name for p in out.iterdir()) == [
        "gate_summary.json",
        "review_list.csv",
        "review_list.jsonl",
    ]


# --- source tracing and uncertainty preservation ---------------------------


def test_review_rows_keep_source_locator_and_schema(tmp_path: Path):
    out = tmp_path / "out"
    run(SAMPLES, out)
    rows = [json.loads(line) for line in (out / "review_list.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 7
    for row in rows:
        assert set(REVIEW_FIELDS).issubset(row)
        assert row["sample_id"]
        assert row["cue_start"] and row["cue_end"]


def test_ambiguous_record_stays_unresolved(tmp_path: Path):
    out = tmp_path / "out"
    run(SAMPLES, out)
    rows = {r["sample_id"]: r for r in map(json.loads, (out / "review_list.jsonl").read_text(encoding="utf-8").splitlines())}
    ambiguous = rows["SYN-003"]
    assert ambiguous["critical_signature_state"] == "SIGNATURE_UNKNOWN"
    assert ambiguous["knowledge_acceptance"] == "BLOCKED_CRITICAL"
    assert ambiguous["human_review_required"] is True


def test_clean_control_is_not_rewritten(tmp_path: Path):
    out = tmp_path / "out"
    run(SAMPLES, out)
    rows = {r["sample_id"]: r for r in map(json.loads, (out / "review_list.jsonl").read_text(encoding="utf-8").splitlines())}
    control = rows["SYN-007"]
    assert control["clean_control_harmful_change"] is False
    assert control["full_cue_transcript_rewrite"] is False


def test_migrated_core_is_not_modified_by_the_demo():
    """The demo must not patch the migrated core module."""

    import pipeline.knowledge_evidence_gate_v21 as core

    assert Path(core.__file__).name == "knowledge_evidence_gate_v21.py"
    assert "SYN-" not in Path(core.__file__).read_text(encoding="utf-8")


@pytest.mark.parametrize("sample_id", ["SYN-001", "SYN-003", "SYN-008"])
def test_source_ids_are_traceable_to_input(sample_id: str, tmp_path: Path):
    out = tmp_path / "out"
    run(SAMPLES, out)
    source_ids = {json.loads(line)["sample_id"] for line in SAMPLES.read_text(encoding="utf-8").splitlines() if line.strip()}
    rows = {json.loads(line)["sample_id"] for line in (out / "review_list.jsonl").read_text(encoding="utf-8").splitlines()}
    assert sample_id in source_ids and sample_id in rows


# --- observed output versus hand-derived expectation ------------------------

EXPECTED_REVIEW = REPO_ROOT / "examples" / "expected" / "expected_review.csv"
EXPECTED_GATE = REPO_ROOT / "examples" / "expected" / "expected_gate_summary.json"


def test_observed_review_matches_hand_derived_expectation(tmp_path: Path):
    import csv

    out = tmp_path / "out"
    run(SAMPLES, out)
    observed = {r["sample_id"]: r for r in map(json.loads, (out / "review_list.jsonl").read_text(encoding="utf-8").splitlines())}
    with EXPECTED_REVIEW.open(encoding="utf-8-sig") as handle:
        expected = list(csv.DictReader(handle))
    assert expected, "expected_review.csv must not be empty"
    for row in expected:
        actual = observed[row["sample_id"]]
        for column, value in row.items():
            if column in ("sample_id", "rule_ref"):
                continue
            field = column[len("expected_"):]
            assert str(actual[field]).lower() == value.lower(), f"{row['sample_id']}.{field}"


def test_observed_gate_matches_hand_derived_expectation(tmp_path: Path):
    out = tmp_path / "out"
    gate, _ = run(SAMPLES, out)
    expected = json.loads(EXPECTED_GATE.read_text(encoding="utf-8"))
    for key, value in expected.items():
        if key.startswith("_"):
            continue
        assert gate[key] == value, f"gate.{key}: expected {value!r}, observed {gate[key]!r}"

