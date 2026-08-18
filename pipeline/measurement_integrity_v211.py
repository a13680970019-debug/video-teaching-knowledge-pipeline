"""Measurement-integrity audit for the fixed-24 Gate V2.1 evidence set.

The module is deliberately independent of the V2.1 decision code.  It treats
the pipeline output as the system under test and never uses that output as
reference truth.  It consumes existing text/JSON/CSV evidence, recomputes
file hashes when the referenced bytes are available, and represents missing
reference truth as ``NOT_MEASURED`` rather than coercing it to zero.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


HARD_METRICS = (
    "critical_false_negative",
    "wrongly_accepted_critical",
    "extractor_critical_error",
    "critical_source_binding_failure",
    "text_only_correction_accepted",
    "clean_control_harmful_change",
)
MEASUREMENT_STATUSES = {"VERIFIED", "PARTIAL", "NOT_MEASURED", "CONFLICT"}
IDENTITY_FIELDS = ("episode_key", "cue_index", "cue_start", "cue_end")
NONCRITICAL_RISK_TYPES = {"", "CLEAN_CONTROL", "MODULE_COVERAGE_UNKNOWN"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def as_bool(value: Any) -> bool:
    return value is True or str(value).strip().lower() == "true"


def first_by_id(rows: Iterable[Mapping[str, Any]]) -> tuple[dict[str, dict[str, Any]], Counter[str]]:
    result: dict[str, dict[str, Any]] = {}
    duplicates: Counter[str] = Counter()
    for row in rows:
        sample_id = str(row.get("sample_id", ""))
        if not sample_id:
            continue
        if sample_id in result:
            duplicates[sample_id] += 1
            continue
        result[sample_id] = dict(row)
    return result, duplicates


def safe_path_ref(path_value: Any, asset_type: str) -> str:
    name = Path(str(path_value or "")).name
    return f"{asset_type}/{name}" if name else f"{asset_type}/MISSING"


def path_hash(path_value: Any) -> str:
    return sha256_text(str(path_value or "")) if path_value else ""


def is_critical_row(row: Mapping[str, Any]) -> bool:
    return str(row.get("sample_kind", "")).upper() == "UNCERTAINTY" and str(row.get("risk_type", "")).upper() not in NONCRITICAL_RISK_TYPES


def load_evidence(root: Path) -> dict[str, Any]:
    fixed = read_csv(root / "00_v2_baseline_freeze" / "00_V2_FIXED_SAMPLE_SET.csv")
    pairs, pair_dupes = first_by_id(read_jsonl(root / "05_post_fix_replay" / "09_V21_AB_TRANSCRIPT_PAIRS.jsonl"))
    audio, audio_dupes = first_by_id(read_csv(root / "05_post_fix_replay" / "10_V21_AUDIO_ADJUDICATION.csv"))
    source_audio, source_dupes = first_by_id(read_jsonl(root / "00_v2_baseline_freeze" / "V2_AUDIO_ADJUDICATION_SOURCE.jsonl"))
    know_a, know_a_dupes = first_by_id(read_jsonl(root / "05_post_fix_replay" / "11_V21_KNOWLEDGE_A.jsonl"))
    know_b, know_b_dupes = first_by_id(read_jsonl(root / "05_post_fix_replay" / "12_V21_KNOWLEDGE_B.jsonl"))
    return {
        "root": root,
        "stage": read_json(root / "00_STAGE_MANIFEST.json"),
        "fixed": fixed,
        "pairs": pairs,
        "audio": audio,
        "source_audio": source_audio,
        "knowledge_a": know_a,
        "knowledge_b": know_b,
        "duplicate_counts": {
            "pairs": dict(pair_dupes),
            "audio": dict(audio_dupes),
            "source_audio": dict(source_dupes),
            "knowledge_a": dict(know_a_dupes),
            "knowledge_b": dict(know_b_dupes),
        },
        "pipeline_metrics": read_json(root / "05_post_fix_replay" / "20_V21_GATE_METRICS.json"),
        "v2_metrics": read_json(root / "00_v2_baseline_freeze" / "V2_GATE_METRICS.json"),
    }


def fixed_sample_identity(evidence: Mapping[str, Any]) -> dict[str, Any]:
    rows = list(evidence["fixed"])
    ids = [str(row.get("sample_id", "")) for row in rows]
    fixed_path = Path(evidence["root"]) / "00_v2_baseline_freeze" / "00_V2_FIXED_SAMPLE_SET.csv"
    current_hash = sha256_file(fixed_path)
    expected_hash = str(evidence["stage"].get("fixed_sample_manifest_sha256", "")).lower()
    unique = len(set(ids))
    return {
        "fixed_sample_count": len(rows),
        "unique_sample_count": unique,
        "fixed_sample_hash": current_hash,
        "expected_fixed_sample_hash": expected_hash,
        "fixed_sample_preserved": len(rows) == 24 and unique == 24 and current_hash == expected_hash,
        "sample_ids": ids,
    }


def cross_record_binding(evidence: Mapping[str, Any]) -> list[dict[str, Any]]:
    fixed_by_id = {str(row["sample_id"]): row for row in evidence["fixed"]}
    outputs = []
    sources = ("manifest", "pair", "audio", "source_audio", "knowledge_a", "knowledge_b")
    maps = {
        "manifest": fixed_by_id,
        "pair": evidence["pairs"],
        "audio": evidence["audio"],
        "source_audio": evidence["source_audio"],
        "knowledge_a": evidence["knowledge_a"],
        "knowledge_b": evidence["knowledge_b"],
    }
    required_identity_sources = {
        "episode_key": {"manifest", "pair", "audio", "source_audio"},
        "cue_index": {"manifest", "pair", "source_audio"},
        "cue_start": {"manifest", "pair", "audio", "source_audio"},
        "cue_end": {"manifest", "pair", "audio", "source_audio"},
    }
    required_sha_sources = {
        "audio_sha256": {"manifest", "audio", "source_audio"},
        "clip_sha256": {"audio", "source_audio"},
    }

    def identity_value(row: Mapping[str, Any], field: str) -> str:
        aliases = {
            "cue_start": ("cue_start", "start_time"),
            "cue_end": ("cue_end", "end_time"),
            "cue_index": ("cue_index",),
            "episode_key": ("episode_key",),
        }
        for key in aliases[field]:
            if key in row and str(row.get(key, "")).strip():
                return str(row.get(key, ""))
        return ""

    def sha_value(row: Mapping[str, Any], field: str) -> str:
        aliases = {
            "audio_sha256": ("audio_sha256", "audio_sha256_observed", "source_audio_sha256"),
            "clip_sha256": ("clip_sha256",),
        }
        for key in aliases[field]:
            if key in row and str(row.get(key, "")).strip():
                return str(row.get(key, ""))
        return ""

    for sample_id in fixed_by_id:
        records = {name: maps[name].get(sample_id) for name in sources}
        missing_sources = [name for name, row in records.items() if not row]
        conflicts: list[str] = []
        for field in IDENTITY_FIELDS:
            values = {identity_value(row, field) for row in records.values() if row is not None and identity_value(row, field)}
            if any(not identity_value(records[name], field) for name in required_identity_sources[field] if records[name] is not None):
                conflicts.append(f"MISSING:{field}")
            elif len(values) > 1:
                conflicts.append(field)
        sha_fields = {
            "audio_sha256": [sha_value(records[name], "audio_sha256") for name in sources if records[name]],
            "clip_sha256": [sha_value(records[name], "clip_sha256") for name in sources if records[name]],
        }
        for field, values in sha_fields.items():
            values = [str(value) for value in values if str(value).strip()]
            required_values = [sha_value(records[name], field) for name in required_sha_sources[field] if records[name]]
            if not required_values or any(not str(value).strip() for value in required_values):
                conflicts.append(f"MISSING:{field}")
            elif len(set(values)) > 1:
                conflicts.append(field)
        if missing_sources or any(item.startswith("MISSING:") for item in conflicts):
            status = "BINDING_MISSING"
        elif conflicts:
            status = "BINDING_CONFLICT"
        else:
            status = "BINDING_VERIFIED"
        outputs.append({
            "sample_id": sample_id,
            "episode_key": fixed_by_id[sample_id].get("episode_key", ""),
            "cue_index": fixed_by_id[sample_id].get("cue_index", ""),
            "cue_start": fixed_by_id[sample_id].get("cue_start", ""),
            "cue_end": fixed_by_id[sample_id].get("cue_end", ""),
            "record_sources_checked": "|".join(sources),
            "missing_sources": "|".join(missing_sources),
            "conflict_fields": "|".join(conflicts),
            "duplicate_source_rows": evidence["duplicate_counts"].get("source_audio", {}).get(sample_id, 0),
            "manifest_audio_sha256": fixed_by_id[sample_id].get("audio_sha256", ""),
            "pipeline_audio_sha256": (records["audio"] or {}).get("audio_sha256", ""),
            "pipeline_clip_sha256": (records["audio"] or {}).get("clip_sha256", ""),
            "binding_status": status,
            "independent_of_system_under_test": False,
            "notes": "Canonical first row used when historical source JSONL contains duplicate sample rows." if evidence["duplicate_counts"].get("source_audio", {}).get(sample_id, 0) else "",
        })
    return outputs


def recompute_byte_hashes(evidence: Mapping[str, Any]) -> list[dict[str, Any]]:
    fixed_by_id = {str(row["sample_id"]): row for row in evidence["fixed"]}
    source = evidence["source_audio"]
    rows: list[dict[str, Any]] = []
    for sample_id, manifest in fixed_by_id.items():
        source_row = source.get(sample_id, {})
        assets = (
            ("AUDIO", manifest.get("audio_path"), manifest.get("audio_sha256"), "SOURCE_AUDIO"),
            ("VTT", manifest.get("vtt_path"), manifest.get("vtt_sha256"), "SOURCE_VTT"),
            ("CLIP", source_row.get("clip_path"), source_row.get("clip_sha256"), "EVIDENCE_CLIP"),
        )
        for asset_type, raw_path, recorded, ref_type in assets:
            path = Path(str(raw_path)) if raw_path else None
            exists = bool(path and path.is_file())
            recomputed = sha256_file(path) if exists and path else ""
            if not path or not str(raw_path).strip():
                status = "NOT_RECOMPUTABLE"
            elif not exists:
                status = "FILE_MISSING"
            elif not recorded:
                status = "NOT_RECOMPUTABLE"
            elif recomputed.lower() != str(recorded).lower():
                status = "HASH_MISMATCH"
            else:
                status = "VERIFIED_BYTES"
            rows.append({
                "sample_id": sample_id,
                "asset_type": asset_type,
                "path_ref": safe_path_ref(raw_path, ref_type),
                "original_path_hash": path_hash(raw_path),
                "exists": exists,
                "recorded_sha256": recorded or "",
                "recomputed_sha256": recomputed,
                "match": status == "VERIFIED_BYTES",
                "size_bytes": path.stat().st_size if exists and path else "",
                "mtime": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat() if exists and path else "",
                "status": status,
            })
    return rows


def temporal_evidence(evidence: Mapping[str, Any], binding: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    critical_ids = {str(row["sample_id"]) for row in evidence["fixed"] if is_critical_row(row)}
    for sample_id in critical_ids:
        audio = evidence["source_audio"].get(sample_id, {})
        v21 = evidence["audio"].get(sample_id, {})
        try:
            start = float(audio.get("window_start_seconds"))
            end = float(audio.get("window_end_seconds"))
            duration = float(audio.get("audio_duration_seconds"))
            bounds_valid = start >= 0 and end > start and end <= duration + 0.25
        except (TypeError, ValueError):
            start = end = duration = ""
            bounds_valid = False
        legacy = str(v21.get("temporal_state", ""))
        if legacy == "TEMPORAL_FAILED":
            evidence_state = "TEMPORAL_CONFLICT"
        elif not bounds_valid:
            evidence_state = "TEMPORAL_UNKNOWN"
        else:
            evidence_state = "WINDOW_ONLY"
        rows.append({
            "sample_id": sample_id,
            "episode_key": v21.get("episode_key", ""),
            "cue_start": v21.get("cue_start", ""),
            "cue_end": v21.get("cue_end", ""),
            "clip_start": audio.get("window_start_seconds", ""),
            "clip_end": audio.get("window_end_seconds", ""),
            "audio_duration_seconds": audio.get("audio_duration_seconds", ""),
            "legacy_temporal_state": legacy,
            "window_bounds_valid": bounds_valid,
            "token_timestamps_present": False,
            "token_start": "",
            "token_end": "",
            "temporal_evidence_state": evidence_state,
            "critical_token": v21.get("critical_signature_state", ""),
            "source_binding_status": binding.get(sample_id, {}).get("binding_status", ""),
            "status_reason": "No word/token timestamps are present in the frozen V2/V2.1 evidence; bounds alone are not token-time proof.",
        })
    return sorted(rows, key=lambda row: row["sample_id"])


def clean_control_measurement(evidence: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for sample_id, b in sorted(evidence["knowledge_b"].items()):
        if not sample_id.startswith("V2C"):
            continue
        a = evidence["knowledge_a"].get(sample_id, {})
        changed = str(a.get("claim", "")) != str(b.get("claim", ""))
        rows.append({
            "sample_id": sample_id,
            "original_claim_sha256": sha256_text(str(a.get("claim", ""))),
            "system_claim_sha256": sha256_text(str(b.get("claim", ""))),
            "text_changed": changed,
            "critical_token_changed": "NOT_ASSESSED",
            "unit_changed": str(a.get("unit_type", "")) != str(b.get("unit_type", "")),
            "system_acceptance": b.get("knowledge_acceptance", ""),
            "harmful_change_value": False if not changed else "",
            "harmful_change_status": "VERIFIED" if not changed else "NOT_MEASURED",
            "reference_required": changed,
            "reason": "No output claim change." if not changed else "Claim changed; harmfulness requires independent semantic/human reference truth.",
        })
    return rows


def text_only_acceptance(evidence: Mapping[str, Any], binding: Mapping[str, Mapping[str, Any]], byte_rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    bytes_by_sample: dict[str, list[Mapping[str, Any]]] = {}
    for row in byte_rows:
        bytes_by_sample.setdefault(str(row["sample_id"]), []).append(row)
    rows: list[dict[str, Any]] = []
    for sample_id, b in sorted(evidence["knowledge_b"].items()):
        a = evidence["knowledge_a"].get(sample_id, {})
        changed = str(a.get("claim", "")) != str(b.get("claim", ""))
        audio_bound = (
            binding.get(sample_id, {}).get("binding_status") == "BINDING_VERIFIED"
            and all(row.get("status") == "VERIFIED_BYTES" for row in bytes_by_sample.get(sample_id, []) if row.get("asset_type") in {"AUDIO", "CLIP"})
        )
        accepted = as_bool(b.get("admitted_downstream")) or str(b.get("knowledge_acceptance", "")) == "ACCEPTED_AUDIO_BOUND"
        text_only = bool(changed and accepted and not audio_bound)
        rows.append({
            "sample_id": sample_id,
            "claim_changed": changed,
            "accepted_downstream": accepted,
            "audio_bound_evidence_verified": audio_bound,
            "text_only_correction_accepted": text_only,
            "measurement_status": "VERIFIED",
            "reason": "Changed output has independently recomputed audio/clip bytes." if changed and audio_bound else "No accepted changed output without byte-verified audio evidence.",
        })
    return rows


def metric(value: Any, status: str, denominator: Any, reference: str, independent: bool, derivation: str, limitations: str) -> dict[str, Any]:
    if status not in MEASUREMENT_STATUSES:
        raise ValueError(status)
    return {
        "value": value,
        "denominator": denominator,
        "measurement_status": status,
        "reference_source": reference,
        "independent_of_system_under_test": independent,
        "derivation": derivation,
        "limitations": limitations,
    }


def build_metrics(evidence: Mapping[str, Any], binding_rows: list[dict[str, Any]], byte_rows: list[dict[str, Any]], clean_rows: list[dict[str, Any]], text_rows: list[dict[str, Any]], gold: dict[str, Any], temporal_rows: list[dict[str, Any]]) -> dict[str, Any]:
    critical_count = sum(1 for row in evidence["fixed"] if is_critical_row(row))
    critical_binding = [row for row in binding_rows if is_critical_row(next((x for x in evidence["fixed"] if x.get("sample_id") == row["sample_id"]), {}))]
    critical_bytes = [row for row in byte_rows if row["sample_id"] in {r["sample_id"] for r in critical_binding}]
    source_binding_failed = sum(1 for row in critical_binding if row["binding_status"] != "BINDING_VERIFIED") + sum(1 for row in critical_bytes if row["status"] != "VERIFIED_BYTES")
    clean_unmeasured = sum(1 for row in clean_rows if row["harmful_change_status"] != "VERIFIED")
    text_value = sum(1 for row in text_rows if row["text_only_correction_accepted"])
    text_status = "VERIFIED" if all(row["measurement_status"] == "VERIFIED" for row in text_rows) else "PARTIAL"
    source_status = "VERIFIED" if source_binding_failed == 0 and len(critical_binding) == critical_count and len(critical_bytes) == critical_count * 3 else "PARTIAL"
    metrics = {
        "critical_false_negative": metric(None, "NOT_MEASURED", critical_count, "No independent human/objective critical mismatch gold in frozen evidence", False, "Requires reference-positive mismatch labels compared with accepted system output.", "System output, signature, and ASR transcript are not gold."),
        "wrongly_accepted_critical": metric(None, "NOT_MEASURED", critical_count, "No independent human/objective critical truth in frozen evidence", False, "Requires accepted output versus independently adjudicated critical truth.", "A signature match is system evidence, not reference truth."),
        "extractor_critical_error": metric(None, "NOT_MEASURED", critical_count, "No reviewed/reference knowledge type labels in frozen evidence", False, "Internal extractor state is retained as diagnostic only; no independent type truth exists.", "The V2.1 inferred taxonomy cannot validate itself."),
        "critical_source_binding_failure": metric(source_binding_failed, source_status, critical_count, "Cross-record identity plus recomputed AUDIO/VTT/CLIP bytes", True, "Count critical rows with cross-record conflicts/missing fields or non-verified required bytes.", "Duplicate historical rows are canonicalized and reported separately."),
        "text_only_correction_accepted": metric(text_value, text_status, len(text_rows), "A/B claim comparison plus cross-record and recomputed audio/clip evidence", True, "Count accepted claim changes lacking independently verified audio/clip bytes.", "This does not establish semantic correctness of the changed claim."),
        "clean_control_harmful_change": metric(None if clean_unmeasured else 0, "NOT_MEASURED" if clean_unmeasured else "VERIFIED", len(clean_rows), "Independent semantic/human reference required for changed clean-control claims", False, "A changed clean-control claim is observable; harmfulness needs independent reference truth.", "All changed clean controls remain unresolved for semantic harmfulness."),
    }
    hard_statuses = {name: item["measurement_status"] for name, item in metrics.items()}
    independent_decision = "NOT_EVALUABLE" if any(status != "VERIFIED" for status in hard_statuses.values()) else ("CONDITIONAL_PASS" if evidence["pipeline_metrics"].get("blocked_critical_count", 0) else "PASS")
    return {
        "stage": "V2.1.1",
        "pipeline_gate_v21_result": evidence["pipeline_metrics"].get("gate_decision", ""),
        "independent_gate_decision": independent_decision,
        "fixed_sample_count": len(evidence["fixed"]),
        "unique_sample_count": len({row.get("sample_id") for row in evidence["fixed"]}),
        "critical_units_total": critical_count,
        "blocked_critical_count": evidence["pipeline_metrics"].get("blocked_critical_count"),
        "metrics": metrics,
        "reference_gold_status": gold["reference_gold_status"],
        "reference_gold_verified_count": gold["verified_count"],
        "reference_gold_unknown_count": gold["unknown_count"],
        "human_gold_required": gold["unknown_count"] > 0,
        "temporal_counts": dict(Counter(row["temporal_evidence_state"] for row in temporal_rows)),
        "full_measurement_integrity": all(item["measurement_status"] == "VERIFIED" for item in metrics.values()),
        "limited_canary_eligible": False,
        "knowledge_canary_authorized": False,
        "full_scale_authorized": False,
        "production_write_count": 0,
        "knowledge_reconstruction_count": 0,
        "canary_execution_count": 0,
        "external_data_upload_count": 0,
    }


def build_gold_registry(evidence: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    gold: list[dict[str, Any]] = []
    human: list[dict[str, Any]] = []
    critical = [row for row in evidence["fixed"] if is_critical_row(row)]
    for row in critical:
        sample_id = str(row["sample_id"])
        question = "Which critical token is actually spoken in the bound audio span?"
        if "unit" in str(row.get("cue_text", "")).lower() or sample_id == "V2U018":
            question = "Which unit is spoken in the bound audio span?"
        if sample_id == "V2U010":
            question = "Does the target speech occur inside the bound cue window?"
        gold.append({
            "sample_id": sample_id,
            "episode_key": row.get("episode_key", ""),
            "critical_type": row.get("risk_type", ""),
            "source_claim": row.get("cue_text", ""),
            "candidate_audio_claim": "",
            "critical_token": "",
            "reference_truth": "",
            "reference_status": "NOT_REVIEWED",
            "reference_source": "NO_INDEPENDENT_GOLD_IN_FROZEN_EVIDENCE",
            "reviewer": "",
            "review_timestamp": "",
            "audio_clip_sha256": evidence["audio"].get(sample_id, {}).get("clip_sha256", ""),
            "cue_start": row.get("cue_start", ""),
            "cue_end": row.get("cue_end", ""),
            "token_start": "",
            "token_end": "",
            "confidence": "",
            "notes": "Frozen evidence is ASR/system evidence, not independent human gold.",
        })
        human.append({
            "sample_id": sample_id,
            "episode_key": row.get("episode_key", ""),
            "exact_question": question,
            "audio_clip_ref": f"EVIDENCE_CLIP/{sample_id}__local.wav",
            "cue_start": row.get("cue_start", ""),
            "cue_end": row.get("cue_end", ""),
            "candidate_a": "",
            "candidate_b": "",
            "critical_token": "",
            "reason": "Independent gold is required before hard safety metrics can be evaluated.",
            "allowed_answers": "reviewer-defined narrow answer only",
            "approval": "",
        })
    return gold, human


def git_info(repo: Path) -> dict[str, Any]:
    def run(*args: str) -> str:
        completed = subprocess.run(["git", f"-c", f"safe.directory={repo}", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
        return completed.stdout.strip()
    main = run("rev-parse", "main")
    pr2 = run("rev-parse", "feature/import-authoritative-r2-r21-pipeline")
    pr4 = run("rev-parse", "fix/gate-v2-1-controlled-remediation-20260817")
    merge_base = run("merge-base", "main", "fix/gate-v2-1-controlled-remediation-20260817")
    count = run("rev-list", "--count", "main..fix/gate-v2-1-controlled-remediation-20260817")
    files = run("diff", "--name-only", "main...fix/gate-v2-1-controlled-remediation-20260817").splitlines()
    commits = run("log", "--format=%H%x09%s", "main..fix/gate-v2-1-controlled-remediation-20260817").splitlines()
    return {
        "repo": str(repo),
        "main_sha": main,
        "pr2_head_sha": pr2,
        "pr4_head_sha": pr4,
        "pr4_merge_base": merge_base,
        "pr4_commit_count_ahead_of_main": int(count or 0),
        "pr4_changed_file_count": len([x for x in files if x]),
        "pr4_commits": commits,
        "pr4_stacked_on_pr2": bool(pr2 and pr4 and run("merge-base", "feature/import-authoritative-r2-r21-pipeline", "fix/gate-v2-1-controlled-remediation-20260817") == pr2),
        "read_only_local_git_evidence": True,
    }


def run_audit(evidence_root: Path, output_root: Path, repo: Path | None = None) -> dict[str, Any]:
    evidence = load_evidence(evidence_root)
    identity = fixed_sample_identity(evidence)
    if not identity["fixed_sample_preserved"]:
        raise RuntimeError("FIXED_SAMPLE_IDENTITY_CHANGED")
    binding_rows = cross_record_binding(evidence)
    binding_map = {row["sample_id"]: row for row in binding_rows}
    byte_rows = recompute_byte_hashes(evidence)
    temporal_rows = temporal_evidence(evidence, binding_map)
    clean_rows = clean_control_measurement(evidence)
    text_rows = text_only_acceptance(evidence, binding_map, byte_rows)
    gold_rows, human_rows = build_gold_registry(evidence)
    gold = {
        "reference_gold_status": "INSUFFICIENT" if gold_rows and not any(row["reference_status"] == "VERIFIED_HUMAN" for row in gold_rows) else "PARTIAL",
        "verified_count": sum(row["reference_status"] in {"VERIFIED_HUMAN", "VERIFIED_OBJECTIVE"} for row in gold_rows),
        "unknown_count": sum(row["reference_status"] in {"UNKNOWN", "NOT_REVIEWED", "DISPUTED"} for row in gold_rows),
    }
    metrics = build_metrics(evidence, binding_rows, byte_rows, clean_rows, text_rows, gold, temporal_rows)

    output_root.mkdir(parents=True, exist_ok=True)
    write_json(output_root / "00_STAGE_MANIFEST.json", {
        "stage_id": "GATE-V2.1.1-MEASUREMENT-INTEGRITY-CLOSEOUT-20260818",
        "created_at_utc": utc_now(),
        "evidence_root": str(evidence_root),
        "fixed_sample_count": identity["fixed_sample_count"],
        "unique_sample_count": identity["unique_sample_count"],
        "fixed_sample_hash": identity["fixed_sample_hash"],
        "fixed_sample_preserved": identity["fixed_sample_preserved"],
        "pipeline_gate_v21_result": metrics["pipeline_gate_v21_result"],
        "independent_gate_decision": metrics["independent_gate_decision"],
        "no_rerun": True,
        "no_resampling": True,
        "production_write_count": 0,
        "knowledge_reconstruction_count": 0,
        "canary_execution_count": 0,
        "external_data_upload_count": 0,
    })
    write_csv(output_root / "02_CRITICAL_GOLD_REGISTRY.csv", gold_rows, list(gold_rows[0]))
    write_csv(output_root / "03_HUMAN_GOLD_REQUIRED.csv", human_rows, list(human_rows[0]))
    write_csv(output_root / "04_CROSS_RECORD_BINDING.csv", binding_rows, list(binding_rows[0]))
    write_csv(output_root / "05_BYTE_HASH_RECOMPUTE.csv", byte_rows, list(byte_rows[0]))
    write_csv(output_root / "06_CRITICAL_TEMPORAL_EVIDENCE.csv", temporal_rows, list(temporal_rows[0]))
    write_csv(output_root / "07_CLEAN_CONTROL_MEASUREMENT.csv", clean_rows, list(clean_rows[0]))
    write_csv(output_root / "08_TEXT_ONLY_ACCEPTANCE_AUDIT.csv", text_rows, list(text_rows[0]))
    write_json(output_root / "09_V211_GATE_METRICS.json", metrics)
    write_json(output_root / "13_REFERENCE_TRUTH_COVERAGE.json", gold)
    matrix = []
    for name, data in metrics["metrics"].items():
        matrix.append({"metric": name, **data})
    write_csv(output_root / "14_MEASUREMENT_VALIDITY_MATRIX.csv", matrix, list(matrix[0]))
    fixed_rows = []
    for sample_id in identity["sample_ids"]:
        b = binding_map[sample_id]
        bytes_for = [row for row in byte_rows if row["sample_id"] == sample_id]
        fixed_rows.append({
            "sample_id": sample_id,
            "identity_preserved": True,
            "binding_status": b["binding_status"],
            "byte_verified_count": sum(row["status"] == "VERIFIED_BYTES" for row in bytes_for),
            "byte_unknown_count": sum(row["status"] != "VERIFIED_BYTES" for row in bytes_for),
            "pipeline_acceptance": evidence["audio"].get(sample_id, {}).get("knowledge_acceptance", ""),
            "temporal_evidence_state": next((row["temporal_evidence_state"] for row in temporal_rows if row["sample_id"] == sample_id), "NOT_CRITICAL"),
            "gold_status": next((row["reference_status"] for row in gold_rows if row["sample_id"] == sample_id), "NOT_APPLICABLE"),
            "independent_safety_evaluation": "NOT_EVALUABLE" if next((row["reference_status"] for row in gold_rows if row["sample_id"] == sample_id), "") != "VERIFIED_HUMAN" else "EVALUATED",
        })
    write_csv(output_root / "15_FIXED24_REPLAY_RESULT.csv", fixed_rows, list(fixed_rows[0]))
    delta_rows = []
    for row in fixed_rows:
        sample_id = row["sample_id"]
        pipeline = evidence["audio"].get(sample_id, {})
        delta_rows.append({
            "sample_id": sample_id,
            "pipeline_acceptance": row["pipeline_acceptance"],
            "source_binding_v211": row["binding_status"],
            "temporal_evidence_v211": row["temporal_evidence_state"],
            "gold_status_v211": row["gold_status"],
            "measurement_conclusion": row["independent_safety_evaluation"],
            "change_reason": "V2.1 numeric safety result is retained as pipeline output; V2.1.1 separates independent measurement status.",
        })
    write_csv(output_root / "16_V21_TO_V211_DELTA.csv", delta_rows, list(delta_rows[0]))
    return {"identity": identity, "metrics": metrics, "binding": binding_rows, "bytes": byte_rows, "temporal": temporal_rows, "clean": clean_rows, "text": text_rows, "gold": gold, "output_root": str(output_root)}


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--git-repo", type=Path)
    args = parser.parse_args(argv)
    result = run_audit(args.evidence_root, args.output_root, args.git_repo)
    if args.git_repo:
        write_json(args.output_root / "10_GIT_STATE_BEFORE.json", git_info(args.git_repo))
    print(json.dumps({"independent_gate_decision": result["metrics"]["independent_gate_decision"], "fixed_sample_hash": result["identity"]["fixed_sample_hash"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

