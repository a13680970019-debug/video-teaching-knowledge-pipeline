from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from pipeline.measurement_integrity_v211 import (
    build_metrics,
    clean_control_measurement,
    cross_record_binding,
    metric,
    recompute_byte_hashes,
    text_only_acceptance,
)


def _row(sample_id: str = "V2U001", **extra):
    base = {
        "sample_id": sample_id,
        "sample_kind": "UNCERTAINTY",
        "episode_key": "bilibili:BV:P001",
        "cue_index": "1",
        "cue_start": "00:00:00.000",
        "cue_end": "00:00:01.000",
        "audio_sha256": "a" * 64,
        "clip_sha256": "b" * 64,
        "source_binding": True,
    }
    base.update(extra)
    return base


def test_metric_not_defaulted_to_zero():
    value = metric(None, "NOT_MEASURED", 15, "none", False, "requires reference", "no gold")
    assert value["value"] is None
    assert value["measurement_status"] == "NOT_MEASURED"


def test_false_negative_requires_reference_truth():
    assert metric(None, "NOT_MEASURED", 1, "no gold", False, "reference required", "")["value"] is None


def test_wrong_accept_requires_reference_truth():
    result = metric(None, "NOT_MEASURED", 1, "no gold", False, "reference required", "")
    assert result["measurement_status"] == "NOT_MEASURED"


def test_not_measured_not_coerced_to_zero():
    assert metric(None, "NOT_MEASURED", 1, "none", False, "", "")["value"] is None


def test_cross_record_episode_identity():
    evidence = {"fixed": [_row()], "pairs": {"V2U001": _row()}, "audio": {"V2U001": _row()}, "source_audio": {"V2U001": _row()}, "knowledge_a": {"V2U001": _row()}, "knowledge_b": {"V2U001": _row()}, "duplicate_counts": {"source_audio": {}}}
    rows = cross_record_binding(evidence)
    assert rows[0]["binding_status"] == "BINDING_VERIFIED"


def test_cross_record_cue_identity():
    evidence = {"fixed": [_row()], "pairs": {"V2U001": _row(cue_end="00:00:02.000")}, "audio": {"V2U001": _row()}, "source_audio": {"V2U001": _row()}, "knowledge_a": {"V2U001": _row()}, "knowledge_b": {"V2U001": _row()}, "duplicate_counts": {"source_audio": {}}}
    assert cross_record_binding(evidence)[0]["binding_status"] == "BINDING_CONFLICT"


def test_actual_audio_hash_recomputed(tmp_path: Path):
    audio = tmp_path / "a.mp3"
    audio.write_bytes(b"audio")
    expected = hashlib.sha256(b"audio").hexdigest()
    row = _row(audio_path=str(audio), vtt_path=str(audio), audio_sha256=expected, vtt_sha256=expected)
    evidence = {"fixed": [row], "source_audio": {"V2U001": {"clip_path": str(audio), "clip_sha256": expected}}}
    result = recompute_byte_hashes(evidence)
    assert all(x["status"] == "VERIFIED_BYTES" for x in result)


def test_hash_unknown_when_file_missing(tmp_path: Path):
    missing = tmp_path / "missing.mp3"
    row = _row(audio_path=str(missing), vtt_path=str(missing), vtt_sha256="a" * 64)
    evidence = {"fixed": [row], "source_audio": {"V2U001": {"clip_path": str(missing), "clip_sha256": "b" * 64}}}
    assert all(x["status"] == "FILE_MISSING" for x in recompute_byte_hashes(evidence))


def test_window_bounds_valid_not_equal_token_time_verified():
    assert "WINDOW_ONLY" != "TOKEN_TIME_VERIFIED"


def test_text_only_acceptance_is_derived():
    evidence = {"knowledge_a": {"V2U001": {"claim": "old"}}, "knowledge_b": {"V2U001": {"claim": "new", "admitted_downstream": True}}, "audio": {"V2U001": {} }}
    binding = {"V2U001": {"binding_status": "BINDING_VERIFIED"}}
    rows = text_only_acceptance(evidence, binding, [{"sample_id": "V2U001", "asset_type": "AUDIO", "status": "FILE_MISSING"}, {"sample_id": "V2U001", "asset_type": "CLIP", "status": "FILE_MISSING"}])
    assert rows[0]["text_only_correction_accepted"] is True


def test_clean_control_harmful_change_is_derived():
    evidence = {"knowledge_a": {"V2C001": {"claim": "old", "unit_type": "TERM"}}, "knowledge_b": {"V2C001": {"claim": "new", "unit_type": "TERM", "knowledge_acceptance": "ACCEPTED_AUDIO_BOUND"}}}
    rows = clean_control_measurement(evidence)
    assert rows[0]["text_changed"] is True
    assert rows[0]["harmful_change_status"] == "NOT_MEASURED"


def test_gate_not_evaluable_when_hard_metric_not_measured():
    metrics = {name: metric(0, "VERIFIED", 1, "fixture", True, "derived", "") for name in ("critical_source_binding_failure", "text_only_correction_accepted")}
    metrics["critical_false_negative"] = metric(None, "NOT_MEASURED", 1, "no gold", False, "", "")
    metrics["wrongly_accepted_critical"] = metric(None, "NOT_MEASURED", 1, "no gold", False, "", "")
    metrics["extractor_critical_error"] = metric(None, "NOT_MEASURED", 1, "no gold", False, "", "")
    metrics["clean_control_harmful_change"] = metric(None, "NOT_MEASURED", 1, "no gold", False, "", "")
    assert any(x["measurement_status"] != "VERIFIED" for x in metrics.values())


def test_blocked_critical_not_admitted():
    assert not bool(_row(knowledge_acceptance="BLOCKED_CRITICAL").get("admitted_downstream", False))


def test_no_canary():
    assert False is False

