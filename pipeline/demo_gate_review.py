"""Offline, reproducible demo entry point for the V2.1 knowledge-evidence gate.

This module is **new in the public demo**.  It reuses
``pipeline.knowledge_evidence_gate_v21`` unchanged (no edits to the migrated
core) and adds only a thin, clearly-labelled adapter:

  * a flat, documented JSONL input contract;
  * structural and timecode validation that fails closed;
  * a source-located human-review export.

It performs no network access, loads no model, opens no audio, reads no
production database, and writes only inside the caller-supplied output root.

Exit codes
----------
0   every record was processed (business outcomes such as BLOCKED_CRITICAL are
    results, not errors)
2   the input path is missing or unreadable
3   the input violates the documented contract (missing/invalid field)
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from pipeline.knowledge_evidence_gate_v21 import assess_evidence, compute_gate

TIMECODE_RE = re.compile(r"^\d{2}:\d{2}:\d{2}\.\d{3}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

REQUIRED_FIELDS = (
    "sample_id",
    "episode_key",
    "sample_kind",
    "risk_type",
    "cue_index",
    "cue_start",
    "cue_end",
    "original_text",
    "audio_window_text",
    "audio_state",
    "source_binding",
    "audio_sha256",
    "clip_sha256",
    "window_start_seconds",
    "window_end_seconds",
    "audio_duration_seconds",
)

SAMPLE_KINDS = {"UNCERTAINTY", "CLEAN_CONTROL"}
AUDIO_STATES = {"AUDIO_RECOVERABLE", "AUDIO_UNRECOVERABLE", "AUDIO_UNKNOWN"}

REVIEW_FIELDS = [
    "sample_id",
    "episode_key",
    "cue_index",
    "cue_start",
    "cue_end",
    "declared_knowledge_type",
    "inferred_knowledge_type",
    "source_binding",
    "audio_state",
    "temporal_state",
    "critical_signature_state",
    "extractor_state",
    "knowledge_acceptance",
    "human_review_required",
    "original_text",
    "audio_text",
    "reason",
]


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def guard_output_root(output_root: Path) -> None:
    """Refuse to write into a production or knowledge-base root."""

    text = str(output_root.resolve()).lower().replace("/", "\\")
    forbidden = (
        "d:\\视频教学采集系统",
        "d:\\司法视频图像处理知识库",
        "knowledge-evidence-gate-pilot-v2-20260817",
    )
    if any(item in text for item in forbidden):
        raise ValueError("refusing a production or knowledge-base output root")


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def validate_record(record: Any, index: int) -> list[str]:
    """Return a list of contract violations for one record (empty means valid)."""

    where = f"record[{index}]"
    if not isinstance(record, dict):
        return [f"{where}: not a JSON object"]
    sample_id = record.get("sample_id") or where
    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in record:
            errors.append(f"{sample_id}: missing required field '{field}'")
    for field in REQUIRED_FIELDS:
        if field == "source_binding" or field not in record:
            continue
        if _is_blank(record[field]):
            errors.append(f"{sample_id}: empty required field '{field}'")
    if errors:
        return errors
    kind = str(record["sample_kind"]).upper()
    if kind not in SAMPLE_KINDS:
        errors.append(f"{sample_id}: sample_kind must be one of {sorted(SAMPLE_KINDS)}")
    audio_state = str(record["audio_state"]).upper()
    if audio_state not in AUDIO_STATES:
        errors.append(f"{sample_id}: audio_state must be one of {sorted(AUDIO_STATES)}")
    if not isinstance(record["source_binding"], bool):
        errors.append(f"{sample_id}: source_binding must be a JSON boolean")
    for field in ("audio_sha256", "clip_sha256"):
        if not SHA256_RE.match(str(record[field])):
            errors.append(f"{sample_id}: '{field}' must be a 64-char lowercase hex digest")
    for field in ("cue_start", "cue_end"):
        if not TIMECODE_RE.match(str(record[field])):
            errors.append(f"{sample_id}: '{field}' must match HH:MM:SS.mmm")
    for field in ("window_start_seconds", "window_end_seconds", "audio_duration_seconds"):
        try:
            float(record[field])
        except (TypeError, ValueError):
            errors.append(f"{sample_id}: '{field}' must be numeric")
    return errors


def load_records(input_path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """Read and validate a JSONL evidence file.

    Raises FileNotFoundError / OSError for unreadable input; returns
    ``(records, errors)`` where a non-empty ``errors`` list means the contract
    was violated.
    """

    text = input_path.read_text(encoding="utf-8")
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    for index, line in enumerate(text.splitlines()):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"record[{index}]: invalid JSON ({exc.msg})")
            continue
        errors.extend(validate_record(record, index))
        records.append(record)
    if not records and not errors:
        errors.append("input file contains no evidence records")
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            continue
        sample_id = str(record.get("sample_id", ""))
        if sample_id in seen:
            errors.append(f"{sample_id}: duplicate sample_id")
        seen.add(sample_id)
    return records, errors


def split_record(record: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Map the flat public contract onto the core library's pair/audio inputs."""

    declared = record.get("declared_knowledge_type") or record["risk_type"]
    pair = {
        "sample_id": record["sample_id"],
        "sample_kind": record["sample_kind"],
        "episode_key": record["episode_key"],
        "risk_type": record["risk_type"],
        "knowledge_type": declared,
        "cue_index": record["cue_index"],
        "cue_start": record["cue_start"],
        "cue_end": record["cue_end"],
        "original_text": record["original_text"],
        "audio_sha256": record["audio_sha256"],
        "clip_sha256": record["clip_sha256"],
        "source_binding": record["source_binding"],
    }
    audio = {
        "episode_key": record["episode_key"],
        "cue_index": record["cue_index"],
        "audio_state": record["audio_state"],
        "audio_window_text": record["audio_window_text"],
        "audio_sha256": record["audio_sha256"],
        "clip_sha256": record["clip_sha256"],
        "source_binding": record["source_binding"],
        "window_start_seconds": record["window_start_seconds"],
        "window_end_seconds": record["window_end_seconds"],
        "audio_duration_seconds": record["audio_duration_seconds"],
    }
    return pair, audio


def assess_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        pair, audio = split_record(record)
        result = assess_evidence(pair, audio)
        # The core assessment carries the cue timecodes but not the cue index;
        # the demo re-attaches it so every exported row is fully source-located.
        result["cue_index"] = record["cue_index"]
        result["synthetic"] = bool(record.get("synthetic", False))
        result["module"] = record.get("module", "")
        result["collection_id"] = record.get("collection_id", "")
        rows.append(result)
    return rows


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def write_review_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in REVIEW_FIELDS})


def run(input_path: Path, output_root: Path) -> tuple[dict[str, Any], int]:
    guard_output_root(output_root)
    try:
        records, errors = load_records(input_path)
    except FileNotFoundError:
        print(f"error: input file not found: {input_path.name}", file=sys.stderr)
        return {}, 2
    except OSError as exc:
        print(f"error: cannot read input file: {exc.strerror or exc}", file=sys.stderr)
        return {}, 2
    if errors:
        print("error: input contract violated; no output written", file=sys.stderr)
        for message in errors:
            print(f"  - {message}", file=sys.stderr)
        return {}, 3

    output_root.mkdir(parents=True, exist_ok=True)
    rows = assess_records(records)
    gate = compute_gate(rows, sample_total=len(records))
    gate.update(
        {
            "input_file_ref": input_path.name,
            "input_sha256": sha256_bytes(input_path.read_bytes()),
            "record_count": len(records),
            "network_used": False,
            "model_used": False,
            "audio_opened": False,
            "production_paths_written": 0,
        }
    )
    write_review_csv(output_root / "review_list.csv", rows)
    write_jsonl(output_root / "review_list.jsonl", rows)
    write_json(output_root / "gate_summary.json", gate)
    return gate, 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="synthetic evidence JSONL")
    parser.add_argument("--output", required=True, type=Path, help="isolated output directory")
    args = parser.parse_args(argv)
    gate, code = run(args.input, args.output)
    if code == 0:
        print(json.dumps(gate, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
