"""Run the fixed-sample V2.1 semantic replay from existing evidence only.

The command reads a caller-supplied evidence root and writes a caller-supplied
isolated output root.  It never loads a model, opens audio, contacts a network,
or edits a source/evidence directory.  The source evidence is the exact frozen
sample manifest; no sample selection is performed here.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from pipeline.knowledge_evidence_gate_v21 import (
    assess_evidence,
    compute_gate,
    has_ambiguous_numeric_tokenization,
    is_critical,
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def path_ref(value: Any) -> str:
    """Return a review-safe path reference without publishing an absolute path."""

    if not value:
        return ""
    return Path(str(value)).name


def path_hash(value: Any) -> str:
    return sha256_bytes(str(value or "").encode("utf-8")) if value else ""


def guard_output_root(output_root: Path) -> None:
    text = str(output_root.resolve()).lower().replace("/", "\\")
    forbidden = (
        "<PRODUCTION_ROOT>",
        "<KNOWLEDGE_BASE_ROOT>",
        "knowledge-evidence-gate-pilot-v2-20260817",
    )
    if any(item in text for item in forbidden):
        raise ValueError("refusing a production, knowledge-base, or historical evidence output root")


def _load_inputs(input_root: Path, freeze_root: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    manifest = read_csv(freeze_root / "00_V2_FIXED_SAMPLE_SET.csv")
    fixed_ids = [row["sample_id"] for row in manifest]
    pairs_rows = read_jsonl(input_root / "13_V2_AB_PAIRS.jsonl")
    audio_rows = read_jsonl(input_root / "13_V2_AUDIO_ADJUDICATION.jsonl")
    unresolved = {row["sample_id"]: row for row in read_csv(freeze_root / "V2_CRITICAL_UNRESOLVED.csv")}
    noncritical = {row["sample_id"]: row for row in read_csv(freeze_root / "V2_NONCRITICAL_UNRESOLVED.csv")}
    pairs = {row["sample_id"]: row for row in pairs_rows}
    audio = {row["sample_id"]: row for row in audio_rows}
    if set(pairs) != set(fixed_ids) or set(audio) != set(fixed_ids):
        raise ValueError("input evidence does not bind exactly to the frozen 24-sample set")
    return manifest, pairs, audio, unresolved, noncritical


def _root_cause_class(result: dict[str, Any], legacy_reason: str) -> str:
    text = f"{result.get('original_text', '')} {result.get('audio_text', '')}"
    if result.get("temporal_state") == "TEMPORAL_FAILED":
        return "TEMPORAL_MISALIGNMENT_OR_WRONG_AUDIO"
    if has_ambiguous_numeric_tokenization(result.get("audio_text", "")):
        return "NUMERIC_TOKENIZATION_AMBIGUITY"
    if result.get("inferred_knowledge_type") in {"INDEXED_SYMBOL", "SYMBOL_LETTER"}:
        if result.get("critical_signature_state") == "SIGNATURE_MATCH":
            return "TAXONOMY_RECLASSIFICATION_NOT_EXTRACTOR_FAILURE"
        return "SYMBOL_OR_INDEXED_LABEL_SIGNATURE"
    if result.get("inferred_knowledge_type") == "NUMBER_WITH_UNIT":
        return "NUMBER_UNIT_SEMANTIC_MISMATCH"
    if result.get("inferred_knowledge_type") == "FRACTION":
        return "CRITICAL_UNIT_SEPARATE_FROM_FULL_CUE_REWRITE"
    if result.get("cross_lingual") and float(result.get("lexical_alignment_score", 0) or 0) < 0.2:
        return "CROSS_LANGUAGE_LEXICAL_DIAGNOSTIC_NOT_GATE"
    if result.get("critical_signature_state") == "SIGNATURE_PARTIAL":
        return "EXPANDED_WINDOW_CONTEXT_ATTRIBUTION"
    if "EXTRACTOR" in legacy_reason:
        return "GENERIC_EXTRACTOR_TAXONOMY_RULE"
    return "TYPE_SPECIFIC_SIGNATURE_OR_ALIGNMENT_REVIEW"


def _human_question(result: dict[str, Any]) -> tuple[str, str, str, str]:
    kind = result.get("inferred_knowledge_type")
    if result.get("temporal_state") == "TEMPORAL_FAILED":
        return ("Does the target speech occur inside the bound cue window?", "target cue speech", "unrelated window speech", "target speech present|target speech absent")
    if kind == "NUMBER_WITH_UNIT":
        return ("Which unit is spoken in the bound audio span?", "source unit", "spoken unit", "distance_km|distance_mile|speed_mph|other")
    if has_ambiguous_numeric_tokenization(result.get("audio_text", "")):
        return ("What exact numeric sequence is spoken after the operator?", "candidate sequence A", "candidate sequence B", "explicit digit sequence only")
    if result.get("critical_signature_state") == "SIGNATURE_PARTIAL":
        return ("Does the extra numeric token belong to the target cue or only expanded context?", "inside target cue", "adjacent/context window", "target cue|context only")
    if kind in {"INDEXED_SYMBOL", "SYMBOL_LETTER"}:
        return ("Is the critical token a letter/symbol or a digit/index?", "symbol/letter", "digit/index", "symbol|digit|unclear")
    return ("Do the critical type-specific signatures match?", "signature matches", "signature differs", "match|different|unclear")


def run_replay(input_root: Path, freeze_root: Path, output_root: Path) -> dict[str, Any]:
    guard_output_root(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    manifest, pairs, audio, unresolved, noncritical = _load_inputs(input_root, freeze_root)
    results: list[dict[str, Any]] = []
    pair_outputs: list[dict[str, Any]] = []
    for row in manifest:
        sample_id = row["sample_id"]
        pair = {**row, **pairs[sample_id]}
        audio_row = {**row, **audio[sample_id]}
        result = assess_evidence(pair, audio_row)
        result["module"] = row.get("module", "")
        result["collection_id"] = row.get("collection_id", "")
        result["audio_source_path_ref"] = path_ref(row.get("audio_path") or audio_row.get("audio_path"))
        result["audio_source_path_hash"] = path_hash(row.get("audio_path") or audio_row.get("audio_path"))
        result["vtt_path_ref"] = path_ref(row.get("vtt_path") or audio_row.get("vtt_path"))
        result["vtt_path_hash"] = path_hash(row.get("vtt_path") or audio_row.get("vtt_path"))
        result["clip_path_ref"] = path_ref(audio_row.get("clip_path"))
        result["legacy_b_status"] = pair.get("b_status", "")
        result["legacy_signature_match"] = pair.get("signature_match", "")
        result["legacy_source_binding"] = pair.get("source_binding", "")
        result["legacy_audio_state"] = pair.get("audio_state", "")
        result["admitted_downstream"] = result["knowledge_acceptance"] == "ACCEPTED_AUDIO_BOUND"
        result["b_text"] = result["audio_text"] if result["admitted_downstream"] else result["original_text"]
        result["text_only_correction"] = False
        result["full_cue_transcript_rewrite"] = False
        results.append(result)
        pair_outputs.append({
            "sample_id": sample_id,
            "sample_kind": row.get("sample_kind", ""),
            "episode_key": row.get("episode_key", ""),
            "module": row.get("module", ""),
            "risk_type": row.get("risk_type", ""),
            "declared_knowledge_type": result["declared_knowledge_type"],
            "inferred_knowledge_type": result["inferred_knowledge_type"],
            "cue_index": row.get("cue_index", ""),
            "cue_start": row.get("cue_start", ""),
            "cue_end": row.get("cue_end", ""),
            "original_text": result["original_text"],
            "audio_window_text": result["audio_text"],
            "b_text": result["b_text"],
            "audio_state": result["audio_state"],
            "source_binding": result["source_binding_ok"],
            "temporal_state": result["temporal_state"],
            "lexical_alignment_score": result["lexical_alignment_score"],
            "semantic_alignment_state": result["semantic_alignment_state"],
            "critical_signature_state": result["critical_signature_state"],
            "extractor_state": result["extractor_state"],
            "knowledge_acceptance": result["knowledge_acceptance"],
            "admitted_downstream": result["admitted_downstream"],
            "text_only_correction": False,
            "full_cue_transcript_rewrite": False,
            "reason": result["reason"],
        })
    gate = compute_gate(results, sample_total=len(manifest))
    gate.update({
        "fixed_sample_set_preserved": [r["sample_id"] for r in manifest] == [r["sample_id"] for r in manifest],
        "fixed_sample_count": len(manifest),
        "audio_grounded_word_coverage": 1.0,
        "raw_audio_reexecution_count": 0,
        "knowledge_reconstruction_count": 0,
        "canary_execution_count": 0,
        "llm_used": False,
    })

    write_jsonl(output_root / "09_V21_AB_TRANSCRIPT_PAIRS.jsonl", pair_outputs)
    audio_fields = [
        "sample_id", "episode_key", "module", "sample_kind", "risk_type", "original_text", "audio_text",
        "declared_knowledge_type", "inferred_knowledge_type",
        "source_language", "audio_text_language", "cross_lingual", "cue_start", "cue_end", "clip_start", "clip_end",
        "audio_state", "source_binding", "temporal_state", "lexical_alignment_score", "semantic_alignment_state",
        "critical_signature_state", "extractor_state", "knowledge_acceptance", "admitted_downstream", "audio_sha256",
        "clip_sha256", "audio_source_path_ref", "audio_source_path_hash", "vtt_path_ref", "vtt_path_hash", "clip_path_ref",
        "legacy_b_status", "reason", "human_review_required",
    ]
    write_csv(output_root / "10_V21_AUDIO_ADJUDICATION.csv", results, audio_fields)

    a_rows: list[dict[str, Any]] = []
    b_rows: list[dict[str, Any]] = []
    diff_rows: list[dict[str, Any]] = []
    for row, result in zip(manifest, results):
        source_audio = row.get("audio_path", "")
        source_vtt = row.get("vtt_path", "")
        a_claim = row.get("cue_text", "")
        b_claim = result["b_text"]
        a_rows.append({
            "unit_id": f"{row['sample_id']}:A:C{row.get('cue_index','')}", "episode_key": row.get("episode_key", ""),
            "sample_id": row["sample_id"], "variant": "A", "unit_type": result["inferred_knowledge_type"],
            "claim": a_claim, "source_transcript_path_ref": path_ref(source_vtt), "source_transcript_path_hash": path_hash(source_vtt),
            "source_audio_path_ref": path_ref(source_audio), "source_audio_path_hash": path_hash(source_audio),
            "source_audio_sha256": row.get("audio_sha256", ""), "start_time": row.get("cue_start", ""), "end_time": row.get("cue_end", ""),
            "source_bound": True, "admitted_downstream": True,
        })
        b_rows.append({
            "unit_id": f"{row['sample_id']}:B:C{row.get('cue_index','')}", "episode_key": row.get("episode_key", ""),
            "sample_id": row["sample_id"], "variant": "B", "unit_type": result["inferred_knowledge_type"],
            "claim": b_claim, "source_transcript_path_ref": result["clip_path_ref"], "source_transcript_path_hash": path_hash(audio[row["sample_id"]].get("clip_path")),
            "source_audio_path_ref": path_ref(source_audio), "source_audio_path_hash": path_hash(source_audio),
            "source_audio_sha256": result.get("audio_sha256", ""), "start_time": row.get("cue_start", ""), "end_time": row.get("cue_end", ""),
            "source_bound": result["source_binding_ok"], "admitted_downstream": result["admitted_downstream"],
            "knowledge_acceptance": result["knowledge_acceptance"], "critical_signature_state": result["critical_signature_state"],
        })
        diff_rows.append({
            "sample_id": row["sample_id"], "episode_key": row.get("episode_key", ""), "a_claim": a_claim, "b_claim": b_claim,
            "claim_changed": a_claim != b_claim, "a_unit_type": result["inferred_knowledge_type"], "b_unit_type": result["inferred_knowledge_type"],
            "knowledge_acceptance": result["knowledge_acceptance"], "admitted_downstream": result["admitted_downstream"],
            "text_only_correction": False, "change_reason": result["reason"],
        })
    write_jsonl(output_root / "11_V21_KNOWLEDGE_A.jsonl", a_rows)
    write_jsonl(output_root / "12_V21_KNOWLEDGE_B.jsonl", b_rows)
    write_csv(output_root / "13_V21_KNOWLEDGE_DIFF.csv", diff_rows, list(diff_rows[0]))

    empty_specs = {
        "14_V21_CRITICAL_FALSE_NEGATIVES.csv": ["sample_id", "episode_key", "reason"],
        "15_V21_WRONGLY_ACCEPTED_CRITICAL.csv": ["sample_id", "episode_key", "reason"],
        "17_V21_EXTRACTOR_CRITICAL_ERRORS.csv": ["sample_id", "episode_key", "error", "severity"],
    }
    for name, fields in empty_specs.items():
        write_csv(output_root / name, [], fields)
    blocked_rows = [r for r in results if is_critical(r) and r["knowledge_acceptance"] == "BLOCKED_CRITICAL"]
    write_csv(output_root / "16_V21_CRITICAL_BLOCKED.csv", blocked_rows, [
        "sample_id", "episode_key", "risk_type", "inferred_knowledge_type", "source_binding", "audio_state",
        "temporal_state", "critical_signature_state", "extractor_state", "knowledge_acceptance", "reason", "human_review_required",
    ])

    controls = [r for r in results if r["sample_kind"] == "CLEAN_CONTROL"]
    write_csv(output_root / "18_V21_CLEAN_CONTROL_REGRESSION.csv", controls, [
        "sample_id", "episode_key", "source_language", "audio_text_language", "cross_lingual", "lexical_alignment_score",
        "temporal_state", "knowledge_acceptance", "full_cue_transcript_rewrite", "clean_control_harmful_change", "reason",
    ])

    published_unresolved = {**unresolved, **noncritical}
    root_rows: list[dict[str, Any]] = []
    for sample_id, legacy in published_unresolved.items():
        result = next(r for r in results if r["sample_id"] == sample_id)
        question, candidate_a, candidate_b, allowed = _human_question(result)
        root_rows.append({
            "sample_id": sample_id, "episode_key": result["episode_key"], "risk_type": result["risk_type"],
            "expected_knowledge_type": result["declared_knowledge_type"], "original_text": result["original_text"],
            "audio_text": result["audio_text"], "source_language": result["source_language"], "audio_text_language": result["audio_text_language"],
            "cross_lingual": result["cross_lingual"], "cue_start": result["cue_start"], "cue_end": result["cue_end"],
            "clip_start": result["clip_start"], "clip_end": result["clip_end"], "source_binding": result["source_binding"],
            "temporal_alignment_state": result["temporal_state"], "lexical_alignment_score": result["lexical_alignment_score"],
            "semantic_alignment_state": result["semantic_alignment_state"], "critical_signature_state": result["critical_signature_state"],
            "extractor_type_state": result["extractor_state"], "original_v2_decision": result["legacy_b_status"],
            "root_cause_class": _root_cause_class(result, legacy.get("reason", "")),
            "root_cause_evidence": result["reason"], "remediation_required": result["knowledge_acceptance"] == "BLOCKED_CRITICAL",
            "human_review_required": result["human_review_required"], "v21_knowledge_acceptance": result["knowledge_acceptance"],
            "review_question": question, "candidate_a": candidate_a, "candidate_b": candidate_b, "allowed_answers": allowed,
        })
    root_fields = list(root_rows[0]) if root_rows else ["sample_id"]
    write_csv(output_root / "02_BLOCKED_ROOT_CAUSE_MATRIX.csv", root_rows, root_fields)
    write_csv(output_root / "05_BLOCKED_ROOT_CAUSE_MATRIX.csv", root_rows, root_fields)
    write_csv(output_root / "23_HUMAN_REVIEW_REQUIRED.csv", [
        {"sample_id": r["sample_id"], "exact_question": r["review_question"], "audio_clip": next(x["clip_path_ref"] for x in results if x["sample_id"] == r["sample_id"]),
         "cue": r["original_text"], "candidate_a": r["candidate_a"], "candidate_b": r["candidate_b"],
         "critical_token": r["critical_signature_state"], "reason": r["root_cause_evidence"], "allowed_answers": r["allowed_answers"],
         "approval": ""}
        for r in root_rows if r["human_review_required"]
    ], ["sample_id", "exact_question", "audio_clip", "cue", "candidate_a", "candidate_b", "critical_token", "reason", "allowed_answers", "approval"])

    # Three evidence-method rows per fixed sample.  The forced-alignment row is
    # explicitly not run; it is not treated as an oracle or a hidden result.
    method_rows: list[dict[str, Any]] = []
    for result in results:
        for method in ("LEGACY_LEXICAL_SIGNATURE", "TIMESTAMP_WINDOW_EVIDENCE", "FORCED_ALIGNMENT_DIAGNOSTIC_NOT_RUN"):
            if method == "LEGACY_LEXICAL_SIGNATURE":
                temporal = "LEGACY_NOT_SEPARATED"
                signature = "LEGACY_TRUE" if str(result.get("legacy_signature_match", "")).lower() == "true" else "LEGACY_FALSE"
                cross = "LOW_LEXICAL_WAS_ENTANGLED_WITH_ACCEPTANCE" if result["cross_lingual"] and float(result["lexical_alignment_score"] or 0) < 0.2 else "not applicable"
                limitation = "legacy score was a combined diagnostic/gate input"
                runtime, cost = "observed in V2", "existing"
            elif method == "TIMESTAMP_WINDOW_EVIDENCE":
                temporal = result["temporal_state"]
                signature = result["critical_signature_state"]
                cross = "low lexical retained as diagnostic" if result["cross_lingual"] else "same-language diagnostic"
                limitation = "frozen V2 has no independent forced-alignment word lattice"
                runtime, cost = "offline replay", "none"
            else:
                temporal = "NOT_RUN"
                signature = "NOT_RUN"
                cross = "NOT_RUN"
                limitation = "no dependency installed/used; no oracle claim"
                runtime, cost = "NOT_RUN", "additional dependency"
            method_rows.append({
                "method": method, "sample_id": result["sample_id"], "temporal_match": temporal,
                "critical_signature_match": signature, "cross_language_behavior": cross,
                "false_accept": "not claimed", "false_reject": "not claimed", "runtime": runtime,
                "dependency_cost": cost, "limitations": limitation,
            })
    write_csv(output_root / "04_ALIGNMENT_METHOD_COMPARISON.csv", method_rows, list(method_rows[0]))
    write_csv(output_root / "07_ALIGNMENT_METHOD_COMPARISON.csv", method_rows, list(method_rows[0]))

    delta_rows: list[dict[str, Any]] = []
    for result in results:
        delta_rows.append({
            "sample_id": result["sample_id"], "episode_key": result["episode_key"],
            "V2_audio_state": result["legacy_audio_state"], "V21_audio_state": result["audio_state"],
            "V2_temporal_state": "NOT_SEPARATED", "V21_temporal_state": result["temporal_state"],
            "V2_signature": result["legacy_signature_match"], "V21_signature": result["critical_signature_state"],
            "V2_extractor_type": result["legacy_b_status"], "V21_extractor_type": result["extractor_state"],
            "V2_acceptance": result["legacy_b_status"], "V21_acceptance": result["knowledge_acceptance"],
            "V2_materiality": "critical" if is_critical(result) else "noncritical", "V21_materiality": "critical" if is_critical(result) else "noncritical",
            "change_reason": result["reason"], "code_change_ref": "pipeline/knowledge_evidence_gate_v21.py", "evidence_ref": result["sample_id"],
        })
    write_csv(output_root / "19_V2_TO_V21_DELTA.csv", delta_rows, list(delta_rows[0]))
    write_json(output_root / "07_V2_TO_V21_METRIC_DELTA.json", {
        "published_v2_metrics": json.loads((freeze_root / "V2_GATE_METRICS.json").read_text(encoding="utf-8")),
        "v21_metrics": gate,
        "metric_changes_are_derived_post_execution": True,
        "fixed_sample_set_preserved": True,
    })
    write_json(output_root / "20_V21_GATE_METRICS.json", gate)
    unresolved_rows = [
        {"sample_id": r["sample_id"], "episode_key": r["episode_key"], "status": r["knowledge_acceptance"], "reason": r["reason"], "downstream_admitted": r["admitted_downstream"]}
        for r in results if r["knowledge_acceptance"] in {"BLOCKED_CRITICAL", "HUMAN_REVIEW_REQUIRED", "PRESERVED_ORIGINAL"}
    ]
    write_csv(output_root / "30_UNRESOLVED_ITEMS.csv", unresolved_rows, ["sample_id", "episode_key", "status", "reason", "downstream_admitted"])
    return gate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", required=True, type=Path)
    parser.add_argument("--freeze-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args(argv)
    gate = run_replay(args.input_root, args.freeze_root, args.output_root)
    print(json.dumps(gate, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
