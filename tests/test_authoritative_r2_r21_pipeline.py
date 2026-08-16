from pathlib import Path

from pipeline.asr import authoritative_r2_first_pass as first_pass
from pipeline.transcript_qc import authoritative_r21_segment_redecoder as qc


def _required_row(word="variance", probability="0.20"):
    return {
        "episode_key": "bilibili:TEST:P001",
        "word_index": "1",
        "segment_index": "1",
        "word": word,
        "word_start": "0.10",
        "word_end": "0.60",
        "asr_probability": probability,
        "risk_reason": "MATH_TERM",
        "second_pass_required": "True",
        "resolution_source": "FIRST_PASS_AUDIO_WORD_TIMESTAMP",
    }


def test_imports_and_entrypoint_markers():
    assert callable(first_pass.run_asr_pilot)
    assert callable(qc.run_second_pass)
    assert callable(qc.decide_consensus)
    assert "WhisperModel" in Path(first_pass.__file__).read_text(encoding="utf-8")
    assert "decode_audio" in Path(qc.__file__).read_text(encoding="utf-8")


def test_identity_parser_behavior_with_synthetic_audio(tmp_path, monkeypatch):
    audio = tmp_path / "BV1p94y1i7PY#P001.mp3"
    audio.write_bytes(b"synthetic")
    monkeypatch.setattr(first_pass, "ffprobe_duration_seconds", lambda _path: 1.0)
    result = first_pass.make_candidate_from_audio({"collection_title": "fixture"}, audio)
    assert result["episode_key"] == "bilibili:BV1p94y1i7PY:P001"


def test_consensus_match():
    result = qc.decide_consensus(_required_row(), {"word": "variance", "probability": 0.40, "start": 0.1, "end": 0.6})
    assert result["consensus_status"] == "CONSENSUS_MATCH"


def test_second_pass_higher_confidence():
    result = qc.decide_consensus(_required_row("varience"), {"word": "variance", "probability": 0.90, "start": 0.1, "end": 0.6})
    assert result["consensus_status"] == "SECOND_PASS_HIGHER_CONFIDENCE"


def test_terminology_context_match():
    result = qc.decide_consensus(_required_row("Fourier"), {"word": "Fourier's", "probability": 0.50, "start": 0.1, "end": 0.6})
    assert result["consensus_status"] == "TERMINOLOGY_CONTEXT_MATCH"


def test_masked_unclear_branch():
    result = qc.decide_consensus(_required_row("variance"), None)
    assert result["consensus_status"] == "MASKED_UNCLEAR"
    assert result["final_word"].strip() == "[unclear]"


def test_known_defect_masked_unclear_not_in_gate(tmp_path):
    raw = tmp_path / "raw.vtt"
    corrected = tmp_path / "corrected.vtt"
    raw.write_text("WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nvariance\n", encoding="utf-8")
    corrected.write_text("WEBVTT\n\n00:00:00.000 --> 00:00:01.000\n[unclear]\n", encoding="utf-8")
    cues = qc.parse_vtt(raw)
    consensus = [{**_required_row(), "consensus_status": "MASKED_UNCLEAR", "final_word": "[unclear]"}]
    result = qc.validate_episode(raw, corrected, cues, consensus, {"REPETITION_HALLUCINATION_COUNT": 0})
    assert result["MASKED_UNCLEAR_WORD_COUNT"] == 1
    assert result["final_status"] == "ACCEPTED"


def test_repetition_postprocessing(tmp_path):
    raw = tmp_path / "synthetic_repetition.vtt"
    raw.write_text(
        "WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nthis is a repeated classroom phrase\n\n"
        "00:00:02.100 --> 00:00:04.000\nthis is a repeated classroom phrase\n",
        encoding="utf-8",
    )
    cues = qc.parse_vtt(raw)
    consensus = [
        {"episode_key": "bilibili:TEST:P001", "segment_index": "1", "word_start": "0.1", "word_end": "1.0", "asr_probability": "0.2"},
        {"episode_key": "bilibili:TEST:P001", "segment_index": "2", "word_start": "2.2", "word_end": "3.0", "asr_probability": "0.2"},
    ]
    segments = {
        ("bilibili:TEST:P001", "1"): {"second_pass_no_speech_prob_max": 0.6},
        ("bilibili:TEST:P001", "2"): {"second_pass_no_speech_prob_max": 0.6},
    }
    result = qc.inspect_repetition_for_episode(
        "bilibili:TEST:P001", cues, {1: cues[0].text, 2: cues[1].text}, consensus, segments
    )
    assert result["CONSECUTIVE_EXACT_REPEAT_COUNT"] == 1


def test_vtt_builder_preserves_cues_and_timestamps(tmp_path):
    source = tmp_path / "source.vtt"
    target = tmp_path / "target.vtt"
    source.write_text(
        "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nold text\n\n00:00:01.500 --> 00:00:02.000\nsecond\n",
        encoding="utf-8",
    )
    cues = qc.parse_vtt(source)
    qc.write_vtt(target, cues, {1: "new text", 2: "[unclear]"}, "synthetic test")
    result = qc.parse_vtt(target)
    assert target.read_text(encoding="utf-8").startswith("WEBVTT")
    assert [(x.start, x.end) for x in result] == [(x.start, x.end) for x in cues]
    assert [x.text for x in result] == ["new text", "[unclear]"]
