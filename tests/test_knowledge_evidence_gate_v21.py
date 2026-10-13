from __future__ import annotations

from pathlib import Path

from pipeline.knowledge_evidence_gate_v21 import (
    assess_evidence,
    compute_gate,
    critical_signature_state,
    formula_signature,
    has_ambiguous_numeric_tokenization,
    infer_knowledge_type,
    number_signature,
    number_with_unit_signature,
    source_binding_required,
    temporal_alignment_state,
    text_only_correction_is_forbidden,
)


def _pair(text: str, *, risk: str = "NUMBER", kind: str = "UNCERTAINTY", declared: str | None = None):
    return {
        "sample_id": "SYNTH-001",
        "sample_kind": kind,
        "episode_key": "bilibili:SYNTH:P001",
        "risk_type": risk,
        "knowledge_type": declared or risk,
        "cue_index": "1",
        "cue_start": "00:00:01.000",
        "cue_end": "00:00:04.000",
        "original_text": text,
        "audio_sha256": "a" * 64,
        "clip_sha256": "b" * 64,
        "source_binding": True,
        "alignment_score": 0.01,
    }


def _audio(text: str, *, start: float = 1.0, end: float = 4.0, duration: float = 10.0):
    return {
        "episode_key": "bilibili:SYNTH:P001",
        "cue_index": "1",
        "audio_state": "AUDIO_RECOVERABLE",
        "audio_window_text": text,
        "audio_sha256": "a" * 64,
        "clip_sha256": "b" * 64,
        "source_binding": True,
        "window_start_seconds": start,
        "window_end_seconds": end,
        "audio_duration_seconds": duration,
    }


def _result(text: str = "8", *, acceptance: str = "ACCEPTED_AUDIO_BOUND", signature: str = "SIGNATURE_MATCH", critical: bool = True):
    return {
        "sample_id": text,
        "sample_kind": "UNCERTAINTY" if critical else "CLEAN_CONTROL",
        "risk_type": "NUMBER" if critical else "CLEAN_CONTROL",
        "knowledge_acceptance": acceptance,
        "critical_signature_state": signature,
        "extractor_state": "EXTRACTOR_CONSISTENT",
        "source_binding": "SOURCE_BOUND",
        "text_only_correction": False,
        "clean_control_harmful_change": False,
    }


def test_fixed_sample_identity_unchanged():
    frozen = ["V2U001", "V2U002", "V2C001"]
    replay = ["V2U001", "V2U002", "V2C001"]
    assert frozen == replay and len(set(replay)) == len(replay)


def test_no_sample_specific_algorithm_patch():
    source = Path(__file__).parents[1].joinpath("pipeline", "knowledge_evidence_gate_v21.py").read_text(encoding="utf-8")
    assert "V2U" not in source and "V2C" not in source


def test_source_binding_required():
    result = assess_evidence(_pair("8"), _audio("eight"))
    assert source_binding_required(result)
    broken = _audio("eight")
    broken.pop("clip_sha256")
    broken_pair = _pair("8")
    broken_pair.pop("clip_sha256")
    result = assess_evidence(broken_pair, broken)
    assert result["knowledge_acceptance"] == "BLOCKED_CRITICAL"


def test_cross_language_low_lexical_score_not_equal_temporal_failure():
    result = assess_evidence(_pair("这是一个定义", risk="TERM", declared="TERM"), _audio("this is a definition"))
    assert result["cross_lingual"] is True
    assert result["temporal_state"] == "TEMPORAL_VERIFIED"
    assert result["semantic_alignment_state"] == "SEMANTIC_SUPPORTING_SIGNAL_CROSS_LANGUAGE"


def test_true_temporal_mismatch_remains_blocked():
    result = assess_evidence(_pair("exercise 2.6", risk="NUMBER"), _audio("请不吝点赞 订阅 转发 打赏支持明镜与点点栏目 BXD"))
    assert result["temporal_state"] == "TEMPORAL_FAILED"
    assert result["knowledge_acceptance"] == "BLOCKED_CRITICAL"


def test_number_signature_integer():
    assert number_signature("the answer is 42") == ("42",)


def test_number_signature_decimal():
    assert number_signature("the value is 7.6") == ("7.6",)


def test_number_signature_fraction():
    assert critical_signature_state("6分之一", "六分之一", "FRACTION") == "SIGNATURE_MATCH"


def test_number_with_unit_signature():
    assert number_with_unit_signature("75 公里") == (("75", "distance_km"),)
    assert number_with_unit_signature("75 miles per hour") == (("75", "speed_mph"),)
    assert critical_signature_state("75 公里", "75 miles per hour", "NUMBER_WITH_UNIT") == "SIGNATURE_MISMATCH"


def test_numeric_sequence_tokenization():
    assert has_ambiguous_numeric_tokenization("除238 再加158")
    assert critical_signature_state("100, 50, 25", "除238 再加158", "NUMBER") == "SIGNATURE_UNKNOWN"


def test_symbol_vs_number_not_forced():
    assert infer_knowledge_type("A1 B2", "NUMBER") == "INDEXED_SYMBOL"
    assert infer_knowledge_type("a 1 b 2", "NUMBER") == "INDEXED_SYMBOL"
    assert critical_signature_state("A1 B2", "A1 B2", "INDEXED_SYMBOL") == "SIGNATURE_MATCH"


def test_formula_signature():
    assert formula_signature("x = 2 + 3") == ("x", "=", "2", "+", "3")
    assert critical_signature_state("x = 2 + 3", "x=2+3", "FORMULA") == "SIGNATURE_MATCH"


def test_term_type_consistency():
    assert infer_knowledge_type("The Series and the Proof from the Book", "TERM") == "NAMED_TITLE_OR_TERM"
    assert critical_signature_state("The Series and the Proof from the Book", "a book called The Series and the Proof from the Book", "NAMED_TITLE_OR_TERM") == "SIGNATURE_MATCH"


def test_expanded_audio_window_does_not_leak_neighbor_number():
    assert critical_signature_state("32.41", "32.41 and 7.6", "NUMBER", expanded_window=True) == "SIGNATURE_PARTIAL"


def test_critical_unit_acceptance_separate_from_full_cue_rewrite():
    result = assess_evidence(_pair("这个 6 分之一的时候要不要成一切"), _audio("这个六分之一的时候要不要沉进去"))
    assert result["critical_signature_state"] == "SIGNATURE_MATCH"
    assert result["knowledge_acceptance"] == "ACCEPTED_AUDIO_BOUND"
    assert result["full_cue_transcript_rewrite"] is False


def test_text_only_correction_never_accepted():
    result = assess_evidence(_pair("8"), _audio("eight"))
    assert text_only_correction_is_forbidden(result) is False
    result["text_only_correction"] = True
    assert text_only_correction_is_forbidden(result) is True


def test_extractor_critical_error_blocks():
    gate = compute_gate([_result("bad", acceptance="BLOCKED_CRITICAL", signature="SIGNATURE_MATCH")])
    bad = _result("bad", acceptance="ACCEPTED_AUDIO_BOUND")
    bad["extractor_state"] = "EXTRACTOR_TYPE_MISMATCH"
    gate = compute_gate([bad])
    assert gate["extractor_critical_error_count"] == 1
    assert gate["gate_decision"] == "FAIL"


def test_blocked_critical_not_admitted_downstream():
    gate = compute_gate([_result("blocked", acceptance="BLOCKED_CRITICAL", signature="SIGNATURE_UNKNOWN")])
    assert gate["blocked_critical_count"] == 1
    assert gate["accepted_critical_count"] == 0


def test_clean_control_no_harmful_change():
    result = assess_evidence(_pair("这是一个定义", risk="CLEAN_CONTROL", kind="CLEAN_CONTROL", declared="TERM"), _audio("this is a definition"))
    assert result["clean_control_harmful_change"] is False


def test_gate_fail_on_false_negative():
    row = _result("fn")
    row["wrongly_accepted_critical"] = True
    gate = compute_gate([row])
    assert gate["critical_false_negative_count"] == 1
    assert gate["gate_decision"] == "FAIL"


def test_gate_fail_on_extractor_error():
    row = _result("extractor")
    row["extractor_state"] = "EXTRACTOR_TYPE_MISMATCH"
    assert compute_gate([row])["gate_decision"] == "FAIL"


def test_gate_fail_on_wrong_critical_accept():
    row = _result("wrong", signature="SIGNATURE_MISMATCH")
    assert compute_gate([row])["wrongly_accepted_critical_count"] == 1
    assert compute_gate([row])["gate_decision"] == "FAIL"


def test_gate_conditional_pass_with_safe_abstention():
    gate = compute_gate([_result("ok"), _result("blocked", acceptance="BLOCKED_CRITICAL", signature="SIGNATURE_UNKNOWN")])
    assert gate["gate_decision"] == "CONDITIONAL_PASS"
    assert gate["blocked_critical_count"] == 1
    assert gate["hard_fail_conditions"]["extractor_critical_error_count"] == 0


def test_gate_pass_contract():
    gate = compute_gate([_result("ok")])
    assert gate["gate_decision"] == "PASS"
    assert gate["blocked_critical_count"] == 0


def test_no_full_scale_authorization():
    gate = compute_gate([_result("ok")])
    assert gate["full_scale_authorized"] is False
    assert gate["knowledge_canary_authorized"] is False
