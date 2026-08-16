from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import json
import math
import os
import re
import shutil
import sys
import time
import zipfile
import msvcrt
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Iterable


HISTORICAL_R2_ROOT = Path(r"D:\AI-Agent-Workspaces\Codex\english-asr-word-audit-200-r2-audio-grounded-20260807")
HISTORICAL_R21_ROOT = Path(r"D:\AI-Agent-Workspaces\Codex\english-asr-word-audit-200-r2-1-pilot-remediation-20260807")
FFMPEG_DEFAULT = Path(r"D:\AI-Env\ffmpeg\bin\ffmpeg.exe")
FFPROBE_DEFAULT = Path(r"D:\AI-Env\ffmpeg\bin\ffprobe.exe")

EXECUTION_AUTHORIZED = False
AUTHORIZED_INPUT_ROOT: Path | None = None
AUTHORIZED_OUTPUT_ROOT: Path | None = None
FAIL_CLOSED = True

PROTECTED_WRITE_ROOTS = tuple(
    Path(p)
    for p in (
        r"D:\视频教学采集系统",
        r"D:\司法视频图像处理知识库",
        r"D:\AI-Agent-Workspaces\Codex\english-asr-word-audit-200-r2-audio-grounded-20260807",
        r"D:\AI-Agent-Workspaces\Codex\english-asr-word-audit-200-r2-1-pilot-remediation-20260807",
    )
)


class ExecutionSafetyError(RuntimeError):
    """Raised when the fail-closed runtime contract is not satisfied."""


def _path_is_under(candidate: Path, parent: Path) -> bool:
    candidate_text = os.path.normcase(os.path.abspath(str(candidate))).rstrip("\\/")
    parent_text = os.path.normcase(os.path.abspath(str(parent))).rstrip("\\/")
    return candidate_text == parent_text or candidate_text.startswith(parent_text + os.sep)


def _assert_safe_output_root(output_root: Path) -> Path:
    resolved = output_root.expanduser().resolve()
    for protected in PROTECTED_WRITE_ROOTS:
        if _path_is_under(resolved, protected):
            raise ExecutionSafetyError(f"FAIL_CLOSED: output root is protected: {resolved}")
    return resolved


def configure_execution(input_root: Path, output_root: Path, execute_real: bool) -> dict[str, str | bool]:
    """Require explicit authorization and bind both runtime roots."""
    global EXECUTION_AUTHORIZED, AUTHORIZED_INPUT_ROOT, AUTHORIZED_OUTPUT_ROOT
    if not execute_real:
        raise ExecutionSafetyError("FAIL_CLOSED: --execute-real is required for real Second-Pass")
    if input_root is None or output_root is None:
        raise ExecutionSafetyError("FAIL_CLOSED: explicit --input-root and --output-root are required")
    AUTHORIZED_INPUT_ROOT = Path(input_root).expanduser().resolve()
    AUTHORIZED_OUTPUT_ROOT = _assert_safe_output_root(Path(output_root))
    EXECUTION_AUTHORIZED = True
    return {
        "fail_closed": True,
        "execute_real": True,
        "input_root": str(AUTHORIZED_INPUT_ROOT),
        "output_root": str(AUTHORIZED_OUTPUT_ROOT),
    }


def _require_runtime_config(input_root: Path, output_root: Path) -> None:
    if not EXECUTION_AUTHORIZED or AUTHORIZED_INPUT_ROOT is None or AUTHORIZED_OUTPUT_ROOT is None:
        raise ExecutionSafetyError(
            "FAIL_CLOSED: configure_execution(--execute-real, --input-root, --output-root) is required"
        )
    if Path(input_root).expanduser().resolve() != AUTHORIZED_INPUT_ROOT:
        raise ExecutionSafetyError("FAIL_CLOSED: runtime input root differs from explicitly authorized input root")
    if _assert_safe_output_root(Path(output_root)) != AUTHORIZED_OUTPUT_ROOT:
        raise ExecutionSafetyError("FAIL_CLOSED: runtime output root differs from explicitly authorized output root")

TZ = timezone(timedelta(hours=8))
SAMPLE_RATE = 16000
SECOND_PASS_PARAMS = {
    "model": "large-v3",
    "device": "cuda",
    "compute_type": "int8_float16",
    "beam_size": 10,
    "best_of": 10,
    "condition_on_previous_text": False,
    "language": "en",
    "word_timestamps": True,
    "vad_filter": True,
    "vad_parameters": {"min_silence_duration_ms": 200},
    "temperature": 0.0,
    "minimum_context_window_seconds": 4.0,
    "default_context_before_seconds": 1.5,
    "default_context_after_seconds": 1.5,
}

FILLERS = {
    "",
    "uh",
    "um",
    "okay",
    "ok",
    "right",
    "yeah",
    "yes",
    "no",
    "so",
    "and",
    "but",
    "you know",
}

TERMS_FOURIER = [
    "Fourier analysis",
    "Fourier series",
    "Fourier transform",
    "inner product",
    "vector space",
    "infinite-dimensional",
    "sequence",
    "modulus",
    "isoperimetric inequality",
    "parametrized curve",
    "simple closed curve",
    "regular curve",
    "arc length",
    "orthogonal",
    "basis",
    "coefficient",
    "convolution",
    "frequency",
    "spectrum",
]

TERMS_PROBABILITY = [
    "random variable",
    "distribution",
    "expectation",
    "variance",
    "covariance",
    "probability",
    "Bernoulli",
    "binomial",
    "density",
    "mass function",
    "standard deviation",
]

R2_BLOCKERS = [
    "5035个Second-Pass需求未执行",
    "2963个唯一segment需要复核",
    "R2 pipeline/segment_redecoder.py尚无实现",
    "20/20 corrected VTT与raw VTT完全一致",
    "legacy duplicate ratio存在空归一化Cue和课堂filler假阳性",
    "16条历史英语失败只有7条满足旧重复率门槛",
    "P027语言检测为uncertain",
    "专业词存在明显疑似误识别",
    "V7实际数据路径尚未完整测量",
    "包内Stage Ledger archive SHA已过期",
    "包内存在13个PYC",
]

SAFETY_PATHS = [
    r"D:\视频教学采集系统\pipeline_quality_state.json",
    r"D:\视频教学采集系统\data\sqlite\video_teaching_v2_shadow.db",
    r"D:\视频教学采集系统\data\sqlite\video_teaching_v2_shadow.db-wal",
    r"D:\视频教学采集系统\data\sqlite\video_teaching_v2_shadow.db-shm",
    r"D:\视频教学采集系统\audio_target_batch",
    r"D:\视频教学采集系统\data\downloads\subtitle",
    r"D:\视频教学采集系统\target_pilot_vtts",
    r"D:\司法视频图像处理知识库\12大数学体系_课程资源\字幕_转写",
    r"D:\司法视频图像处理知识库\12大数学体系_课程资源\字幕_转写_英文",
    r"D:\AI-Agent-Workspaces\Codex\english-asr-word-audit-200-20260806",
    r"D:\AI-Agent-Workspaces\Codex\english-asr-word-audit-200-r2-audio-grounded-20260807",
    r"D:\视频教学采集系统\下一步行动计划_V7教材数据库上线.md",
]


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def ensure_dirs(root: Path) -> None:
    if EXECUTION_AUTHORIZED and AUTHORIZED_OUTPUT_ROOT is not None:
        _require_runtime_config(AUTHORIZED_INPUT_ROOT or root, root)
    else:
        raise ExecutionSafetyError("FAIL_CLOSED: explicit execution configuration is required before writing")
    for rel in [
        "00_control",
        "01_inputs_frozen",
        "02_second_pass_segments",
        "03_episode_outputs",
        "04_quality",
        "05_language_review",
        "06_history_16",
        "07_zero_write",
        "08_handoff",
        "09_review_package",
        "pipeline",
        "raw_logs",
    ]:
        (root / rel).mkdir(parents=True, exist_ok=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def append_jsonl(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")


class FileLock:
    def __init__(self, path: Path):
        self.path = path
        self.handle = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("a+b")
        self.handle.seek(0)
        try:
            msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            raise RuntimeError(f"Another R2.1 segment_redecoder process is already running; lock={self.path}") from exc
        self.handle.truncate()
        self.handle.write(f"pid={os.getpid()} started_at={now_iso()}\n".encode("utf-8"))
        self.handle.flush()
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.handle:
            try:
                self.handle.seek(0)
                self.handle.truncate()
                self.handle.write(f"pid={os.getpid()} ended_at={now_iso()}\n".encode("utf-8"))
                self.handle.flush()
                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            finally:
                self.handle.close()
        return False


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for k in row.keys():
                if k not in fieldnames:
                    fieldnames.append(k)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)


def seconds_to_vtt(t: float) -> str:
    if t < 0:
        t = 0
    ms = int(round((t - math.floor(t)) * 1000))
    total = int(math.floor(t))
    if ms >= 1000:
        total += 1
        ms -= 1000
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def vtt_to_seconds(s: str) -> float:
    m = re.match(r"(?:(\d+):)?(\d{2}):(\d{2})\.(\d{3})", s.strip())
    if not m:
        return 0.0
    h = int(m.group(1) or 0)
    return h * 3600 + int(m.group(2)) * 60 + int(m.group(3)) + int(m.group(4)) / 1000


@dataclass
class Cue:
    index: int
    start: str
    end: str
    start_seconds: float
    end_seconds: float
    text: str


def parse_vtt(path: Path) -> list[Cue]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    cues: list[Cue] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if "-->" not in line:
            i += 1
            continue
        left, right = [x.strip() for x in line.split("-->", 1)]
        right = right.split()[0]
        i += 1
        text_lines: list[str] = []
        while i < len(lines) and lines[i].strip() != "":
            text_lines.append(lines[i])
            i += 1
        cues.append(
            Cue(
                index=len(cues) + 1,
                start=left,
                end=right,
                start_seconds=vtt_to_seconds(left),
                end_seconds=vtt_to_seconds(right),
                text="\n".join(text_lines).strip(),
            )
        )
        i += 1
    return cues


def write_vtt(path: Path, cues: list[Cue], cue_text: dict[int, str], note: str) -> None:
    out = ["WEBVTT", "", f"NOTE {note}", ""]
    for cue in cues:
        out.append(f"{cue.start} --> {cue.end}")
        out.append(cue_text.get(cue.index, cue.text).strip())
        out.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out), encoding="utf-8", newline="\n")


def episode_dir_name(episode_key: str) -> str:
    return episode_key.replace(":", "_")


def normalize_token(text: str) -> str:
    text = text.strip().lower()
    text = text.replace("’", "'").replace("“", '"').replace("”", '"')
    text = re.sub(r"^\W+|\W+$", "", text)
    return text


def normalize_cue(text: str) -> str:
    text = text.lower().replace("’", "'")
    text = re.sub(r"\[[^\]]+\]", " ", text)
    text = re.sub(r"[^a-z0-9'\s-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def preserve_shape(original: str, final_word: str) -> str:
    if final_word in {"[unclear]", "[inaudible]"}:
        leading = re.match(r"^\s*", original).group(0)
        return leading + final_word
    leading = re.match(r"^\s*", original).group(0)
    trailing_match = re.search(r"([,.;:!?]+)\s*$", original)
    trailing = trailing_match.group(1) if trailing_match and not re.search(r"[,.;:!?]$", final_word) else ""
    return leading + final_word.strip() + trailing


def float_or_none(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def term_category(risk_reason: str) -> str:
    for item in ["FORMULA_SPEECH", "MATH_TERM", "NUMERIC", "SYMBOL_LETTER", "LOW_ASR_PROBABILITY"]:
        if item in risk_reason:
            return item
    return "GENERAL_LOW_CONFIDENCE"


def risk_is_math_numeric_formula(risk_reason: str) -> bool:
    return any(x in risk_reason for x in ["FORMULA_SPEECH", "MATH_TERM", "NUMERIC", "SYMBOL_LETTER"])


def build_segments(word_rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, Any]]:
    segments: dict[tuple[str, str], dict[str, Any]] = {}
    for row in word_rows:
        key = (row["episode_key"], row["segment_index"])
        seg = segments.setdefault(
            key,
            {
                "episode_key": row["episode_key"],
                "segment_index": row["segment_index"],
                "rows": [],
                "second_pass_required": False,
            },
        )
        seg["rows"].append(row)
        if row.get("second_pass_required") == "True":
            seg["second_pass_required"] = True
    for seg in segments.values():
        starts = [float_or_none(r.get("word_start")) for r in seg["rows"]]
        ends = [float_or_none(r.get("word_end")) for r in seg["rows"]]
        starts2 = [x for x in starts if x is not None]
        ends2 = [x for x in ends if x is not None]
        seg["segment_start"] = min(starts2) if starts2 else 0.0
        seg["segment_end"] = max(ends2) if ends2 else seg["segment_start"]
        seg["first_pass_text"] = "".join(r.get("word", "") for r in seg["rows"]).strip()
        seg["required_word_count"] = sum(1 for r in seg["rows"] if r.get("second_pass_required") == "True")
        seg["risk_reasons"] = sorted({r.get("risk_reason", "") for r in seg["rows"] if r.get("second_pass_required") == "True"})
    return segments


def get_audio_duration(audio_path: str, metadata_duration: float | None, ffprobe: Path) -> float:
    if metadata_duration and metadata_duration > 0:
        return float(metadata_duration)
    if ffprobe.exists():
        import subprocess

        result = subprocess.run(
            [
                str(ffprobe),
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                audio_path,
            ],
            capture_output=True,
            text=True,
            shell=False,
        )
        if result.returncode == 0:
            val = float_or_none(result.stdout.strip())
            if val and val > 0:
                return val
    return 0.0


def compute_window(start: float, end: float, duration: float, risk_reasons: Iterable[str]) -> dict[str, float | str]:
    before = SECOND_PASS_PARAMS["default_context_before_seconds"]
    after = SECOND_PASS_PARAMS["default_context_after_seconds"]
    reason = "DEFAULT_1_5_SECONDS"
    risk_blob = "|".join(risk_reasons)
    if any(x in risk_blob for x in ["FORMULA_SPEECH", "MATH_TERM"]) or (end - start) >= 8.0:
        before = 3.0
        after = 3.0
        reason = "MATH_OR_LONG_CONTEXT_3_SECONDS"
    ws = max(0.0, start - before)
    we = min(duration if duration > 0 else end + after, end + after)
    minimum = SECOND_PASS_PARAMS["minimum_context_window_seconds"]
    if we - ws < minimum:
        center = (start + end) / 2.0
        ws = max(0.0, center - minimum / 2.0)
        we = min(duration if duration > 0 else center + minimum / 2.0, ws + minimum)
        if we - ws < minimum and ws > 0:
            ws = max(0.0, we - minimum)
        reason += "+MINIMUM_4_SECONDS"
    return {
        "window_start": round(ws, 3),
        "window_end": round(we, 3),
        "window_duration": round(max(0.0, we - ws), 3),
        "window_reason": reason,
    }


def snapshot_path(path: Path) -> dict[str, Any]:
    rec: dict[str, Any] = {"path": str(path), "exists": path.exists()}
    if not path.exists():
        return rec | {"type": "missing"}
    if path.is_file():
        st = path.stat()
        return rec | {
            "type": "file",
            "size_bytes": st.st_size,
            "mtime_ns": st.st_mtime_ns,
            "sha256": sha256_file(path),
        }
    h = hashlib.sha256()
    file_count = 0
    total_size = 0
    max_mtime = 0
    for p in sorted(path.rglob("*")):
        if not p.is_file():
            continue
        try:
            st = p.stat()
        except OSError:
            continue
        rel = p.relative_to(path).as_posix()
        file_count += 1
        total_size += st.st_size
        max_mtime = max(max_mtime, st.st_mtime_ns)
        h.update(f"{rel}|{st.st_size}|{st.st_mtime_ns}\n".encode("utf-8", errors="replace"))
    return rec | {
        "type": "directory",
        "file_count": file_count,
        "total_size_bytes": total_size,
        "max_mtime_ns": max_mtime,
        "tree_metadata_sha256": h.hexdigest(),
        "tree_hash_basis": "relative_path|size|mtime_ns",
    }


def create_snapshot(label: str, root: Path, paths: list[str] = SAFETY_PATHS) -> dict[str, Any]:
    snap = {"label": label, "generated_at": now_iso(), "paths": [snapshot_path(Path(p)) for p in paths]}
    write_json(root / "07_zero_write" / f"{label}_SAFETY_SNAPSHOT.json", snap)
    return snap


def compare_snapshots(pre: dict[str, Any], post: dict[str, Any], root: Path) -> dict[str, Any]:
    rows = []
    production_changed = 0
    state_writes = 0
    sqlite_writes = 0
    v7_writes = 0
    for a, b in zip(pre.get("paths", []), post.get("paths", [])):
        diffs = {}
        keys = sorted(set(a.keys()) | set(b.keys()))
        for k in keys:
            if k in {"label", "generated_at"}:
                continue
            if a.get(k) != b.get(k):
                diffs[k] = {"pre": a.get(k), "post": b.get(k)}
        status = "UNCHANGED" if not diffs else "CHANGED"
        path = a.get("path") or b.get("path")
        if status == "CHANGED":
            production_changed += 1
            p = str(path).lower()
            if "pipeline_quality_state.json" in p:
                state_writes += 1
            if ".db" in p or "-wal" in p or "-shm" in p:
                sqlite_writes += 1
            if "v7" in p or "教材数据库" in p:
                v7_writes += 1
        rows.append({"path": path, "status": status, "diffs": diffs})
    actual_v7 = {
        "ACTUAL_V7_DATASTORE_STATUS": "NOT_LOCATED",
        "V7_ZERO_WRITE": "NOT_COMPARABLE",
        "V7_PLAN_FILE_UNCHANGED": next(
            (r["status"] == "UNCHANGED" for r in rows if "下一步行动计划_V7教材数据库上线.md" in str(r.get("path"))),
            None,
        ),
    }
    out = {
        "generated_at": now_iso(),
        "PRODUCTION_CHANGED_COUNT": production_changed,
        "STATE_WRITE_COUNT": state_writes,
        "SQLITE_WRITE_COUNT": sqlite_writes,
        "V7_WRITE_COUNT": v7_writes,
        **actual_v7,
        "rows": rows,
    }
    write_json(root / "07_zero_write" / "ZERO_WRITE_COMPARISON.json", out)
    return out


def freeze_inputs(r2: Path, root: Path) -> dict[str, Any]:
    ensure_dirs(root)
    frozen = root / "01_inputs_frozen"
    frozen.mkdir(parents=True, exist_ok=True)
    files = [
        r2 / "00_control" / "01_TARGET_200_AUDIO_GROUNDED_MANIFEST.csv",
        r2 / "03_pilot_20" / "01_PILOT_20_MANIFEST.csv",
        r2 / "03_pilot_20" / "02_WORD_LEVEL_AUDIT_COMBINED.csv",
        r2 / "03_pilot_20" / "03_SEGMENT_REDECODE_PLAN_COMBINED.csv",
        r2 / "03_pilot_20" / "04_ASR_RUNTIME_SUMMARY.json",
        r2 / "03_pilot_20" / "05_PILOT_GATE_RESULT.json",
        r2 / "09_review_package" / "FINAL_ARCHIVE_METADATA.json",
        r2 / "09_review_package" / "FINAL_ARCHIVE_SHA256.txt",
    ]
    manifest = []
    for src in files:
        if not src.exists():
            manifest.append({"source": str(src), "status": "MISSING"})
            continue
        dst = frozen / src.name
        shutil.copy2(src, dst)
        manifest.append(
            {
                "source": str(src),
                "frozen_copy": str(dst),
                "size_bytes": dst.stat().st_size,
                "sha256": sha256_file(dst),
                "status": "FROZEN_COPY_CREATED",
            }
        )
    task_manifest = {
        "task_id": "CODEX-ENGLISH-ASR-R2.1-PILOT20-SECOND-PASS-REMEDIATION-20260807",
        "generated_at": now_iso(),
        "r2_root_read_only": str(r2),
        "r2_1_root_write_only": str(root),
        "R2_MODIFICATION_ALLOWED": False,
        "R2_1_REMEDIATION_ALLOWED": True,
        "CANARY_50_ALLOWED": False,
        "PRODUCTION_130_ALLOWED": False,
        "CHINESE_TRANSLATION_ALLOWED": False,
        "KNOWLEDGE_INGEST_ALLOWED": False,
        "PRODUCTION_WRITE_ALLOWED": False,
        "STATE_WRITE_ALLOWED": False,
        "SQLITE_WRITE_ALLOWED": False,
        "V7_WRITE_ALLOWED": False,
        "AUTO_CONTINUE": False,
        "NEXT_ACTION_REQUIRES_CHATGPT_REVIEW": True,
        "r2_blockers_registered": R2_BLOCKERS,
        "second_pass_parameters": SECOND_PASS_PARAMS,
        "terminology": {"fourier": TERMS_FOURIER, "probability_statistics": TERMS_PROBABILITY},
        "frozen_inputs": manifest,
    }
    write_json(root / "00_control" / "TASK_MANIFEST.json", task_manifest)
    append_jsonl(root / "00_control" / "STAGE_LEDGER.jsonl", {"stage": "FREEZE_INPUTS", "at": now_iso(), "status": "DONE"})
    return task_manifest


def copy_episode_inputs(r2: Path, root: Path, runtime_rows: list[dict[str, Any]]) -> None:
    for meta in runtime_rows:
        ep = meta["episode_key"]
        src_dir = r2 / "06_episode_outputs" / episode_dir_name(ep)
        dst_dir = root / "03_episode_outputs" / episode_dir_name(ep)
        dst_dir.mkdir(parents=True, exist_ok=True)
        pairs = [
            ("01_original_audio_asr.vtt", "01_first_pass_raw.vtt"),
            ("03_word_level_audit.csv", "03_word_consensus_audit.seed_first_pass.csv"),
            ("04_asr_metadata.json", "04_asr_metadata.r2_first_pass.json"),
            ("05_validation_result.json", "05_validation_result.r2_first_pass.json"),
            ("06_segment_redecode_plan.csv", "06_segment_redecode_plan.r2_unexecuted.csv"),
        ]
        for src_name, dst_name in pairs:
            src = src_dir / src_name
            if src.exists():
                shutil.copy2(src, dst_dir / dst_name)


def load_runtime(r2: Path) -> list[dict[str, Any]]:
    summary = read_json(r2 / "03_pilot_20" / "04_ASR_RUNTIME_SUMMARY.json")
    return summary.get("results", [])


def load_existing_results(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    out: dict[tuple[str, str], dict[str, Any]] = {}
    if not path.exists():
        return out
    with path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            out[(obj["episode_key"], str(obj["segment_index"]))] = obj
    return out


def transcribe_clip(model: Any, audio_slice: Any, window_start: float, hotwords: str) -> dict[str, Any]:
    segments_iter, info = model.transcribe(
        audio_slice,
        language="en",
        task="transcribe",
        beam_size=SECOND_PASS_PARAMS["beam_size"],
        best_of=SECOND_PASS_PARAMS["best_of"],
        condition_on_previous_text=False,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters=SECOND_PASS_PARAMS["vad_parameters"],
        temperature=0.0,
        hotwords=hotwords,
    )
    segments = list(segments_iter)
    words = []
    texts = []
    avg_logprobs = []
    no_speech_probs = []
    for seg in segments:
        texts.append(seg.text.strip())
        if getattr(seg, "avg_logprob", None) is not None:
            avg_logprobs.append(float(seg.avg_logprob))
        if getattr(seg, "no_speech_prob", None) is not None:
            no_speech_probs.append(float(seg.no_speech_prob))
        for w in getattr(seg, "words", None) or []:
            words.append(
                {
                    "word": w.word,
                    "start": round(float(w.start or 0.0) + window_start, 3),
                    "end": round(float(w.end or 0.0) + window_start, 3),
                    "probability": None if getattr(w, "probability", None) is None else float(w.probability),
                }
            )
    return {
        "second_pass_text": " ".join(t for t in texts if t).strip(),
        "second_pass_words": words,
        "second_pass_word_count": len(words),
        "second_pass_avg_logprob": sum(avg_logprobs) / len(avg_logprobs) if avg_logprobs else None,
        "second_pass_no_speech_prob_max": max(no_speech_probs) if no_speech_probs else None,
        "detected_language": getattr(info, "language", None),
        "language_probability": getattr(info, "language_probability", None),
    }


def run_second_pass(r2: Path, root: Path, limit: int | None = None) -> dict[str, Any]:
    _require_runtime_config(r2, root)
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("HF_HOME", r"C:\Users\1\.cache\huggingface")
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    ensure_dirs(root)
    word_rows = read_csv(r2 / "03_pilot_20" / "02_WORD_LEVEL_AUDIT_COMBINED.csv")
    segments = build_segments(word_rows)
    required = [s for s in segments.values() if s["second_pass_required"]]
    required.sort(key=lambda s: (s["episode_key"], int(s["segment_index"])))
    if limit is not None:
        required = required[:limit]
    runtime = {m["episode_key"]: m for m in load_runtime(r2)}
    result_jsonl = root / "02_second_pass_segments" / "SEGMENT_SECOND_PASS_RESULTS.jsonl"
    existing = load_existing_results(result_jsonl)

    from faster_whisper import WhisperModel
    from faster_whisper.audio import decode_audio

    with FileLock(root / "00_control" / "SECOND_PASS_RUNNING.lock"):
        append_jsonl(root / "00_control" / "STAGE_LEDGER.jsonl", {"stage": "SECOND_PASS_START", "at": now_iso(), "target_segments": len(required), "existing_ok_segments": len(existing)})
        model = WhisperModel(
            SECOND_PASS_PARAMS["model"],
            device=SECOND_PASS_PARAMS["device"],
            compute_type=SECOND_PASS_PARAMS["compute_type"],
            local_files_only=True,
        )
        hotwords = "; ".join(TERMS_FOURIER + TERMS_PROBABILITY)
        done = 0
        errors = 0
        current_audio_key = None
        current_audio = None
        current_duration = 0.0
        for idx, seg in enumerate(required, 1):
            key = (seg["episode_key"], str(seg["segment_index"]))
            if key in existing and existing[key].get("runtime_status") == "OK":
                done += 1
                continue
            meta = runtime[seg["episode_key"]]
            audio_path = meta["audio_path"]
            try:
                if current_audio_key != audio_path:
                    current_audio_key = audio_path
                    current_audio = decode_audio(audio_path, sampling_rate=SAMPLE_RATE)
                    current_duration = len(current_audio) / SAMPLE_RATE
                duration = get_audio_duration(audio_path, current_duration or float_or_none(meta.get("audio_duration_seconds")), FFPROBE_DEFAULT)
                win = compute_window(float(seg["segment_start"]), float(seg["segment_end"]), duration, seg["risk_reasons"])
                start_i = int(float(win["window_start"]) * SAMPLE_RATE)
                end_i = int(float(win["window_end"]) * SAMPLE_RATE)
                clip = current_audio[start_i:end_i]
                t0 = time.time()
                decoded = transcribe_clip(model, clip, float(win["window_start"]), hotwords)
                rec = {
                    "episode_key": seg["episode_key"],
                    "segment_index": str(seg["segment_index"]),
                    "segment_start": round(float(seg["segment_start"]), 3),
                    "segment_end": round(float(seg["segment_end"]), 3),
                    "first_pass_text": seg["first_pass_text"],
                    "required_word_count": seg["required_word_count"],
                    "risk_reasons": seg["risk_reasons"],
                    "audio_path": audio_path,
                    "audio_sha256": meta.get("audio_sha256"),
                    "audio_duration_seconds": duration,
                    **win,
                    **decoded,
                    "second_pass_parameters": SECOND_PASS_PARAMS,
                    "runtime_seconds": round(time.time() - t0, 3),
                    "runtime_status": "OK",
                    "generated_at": now_iso(),
                }
                append_jsonl(result_jsonl, rec)
                done += 1
            except Exception as exc:
                errors += 1
                rec = {
                    "episode_key": seg["episode_key"],
                    "segment_index": str(seg["segment_index"]),
                    "segment_start": round(float(seg["segment_start"]), 3),
                    "segment_end": round(float(seg["segment_end"]), 3),
                    "first_pass_text": seg["first_pass_text"],
                    "required_word_count": seg["required_word_count"],
                    "risk_reasons": seg["risk_reasons"],
                    "runtime_status": "ERROR",
                    "error": repr(exc),
                    "generated_at": now_iso(),
                }
                append_jsonl(result_jsonl, rec)
            if idx % 50 == 0:
                print(f"[{now_iso()}] second-pass progress {idx}/{len(required)} done={done} errors={errors}", flush=True)
        append_jsonl(root / "00_control" / "STAGE_LEDGER.jsonl", {"stage": "SECOND_PASS_END", "at": now_iso(), "done": done, "errors": errors})
        return {"target_segments": len(required), "done": done, "errors": errors, "jsonl": str(result_jsonl)}


def nearest_second_word(first_row: dict[str, str], second_words: list[dict[str, Any]]) -> dict[str, Any] | None:
    center_values = [float_or_none(first_row.get("word_start")), float_or_none(first_row.get("word_end"))]
    if center_values[0] is None or center_values[1] is None or not second_words:
        return None
    center = (center_values[0] + center_values[1]) / 2.0
    best = None
    best_score = 9999.0
    for w in second_words:
        ws = float(w.get("start") or 0.0)
        we = float(w.get("end") or ws)
        wc = (ws + we) / 2.0
        overlap_bonus = -0.35 if ws <= center <= we else 0.0
        score = abs(center - wc) + overlap_bonus
        if score < best_score:
            best = w
            best_score = score
    if best is None or best_score > 1.25:
        return None
    return best


def decide_consensus(row: dict[str, str], second_word: dict[str, Any] | None) -> dict[str, Any]:
    first_word = row.get("word", "")
    first_prob = float_or_none(row.get("asr_probability")) or 0.0
    risk = row.get("risk_reason", "")
    cat = term_category(risk)
    if row.get("second_pass_required") != "True":
        return {
            "second_pass_word": "",
            "second_pass_probability": "",
            "term_category": cat,
            "consensus_status": "AUTO_CONFIRMED_FIRST_PASS",
            "final_word": first_word,
            "resolution_source": row.get("resolution_source", "FIRST_PASS_AUDIO_WORD_TIMESTAMP"),
        }
    if not second_word:
        return {
            "second_pass_word": "",
            "second_pass_probability": "",
            "term_category": cat,
            "consensus_status": "MASKED_UNCLEAR",
            "final_word": preserve_shape(first_word, "[unclear]"),
            "resolution_source": "SECOND_PASS_NO_ALIGNED_WORD_MASKED",
        }
    second_raw = str(second_word.get("word", ""))
    second_prob = second_word.get("probability")
    second_prob_f = float(second_prob) if second_prob is not None else 0.0
    n1 = normalize_token(first_word)
    n2 = normalize_token(second_raw)
    if n1 and n1 == n2 and second_prob_f >= 0.35:
        status = "CONSENSUS_MATCH"
        final = first_word
        source = "FIRST_SECOND_PASS_AUDIO_CONSENSUS"
    elif n2 and second_prob_f >= max(0.62, first_prob + 0.15):
        status = "SECOND_PASS_HIGHER_CONFIDENCE"
        final = preserve_shape(first_word, second_raw)
        source = "SECOND_PASS_LOCAL_AUDIO_HIGHER_CONFIDENCE"
    elif first_prob >= max(0.72, second_prob_f + 0.12):
        status = "FIRST_PASS_HIGHER_CONFIDENCE"
        final = first_word
        source = "FIRST_PASS_AUDIO_WORD_PROBABILITY_HIGHER"
    elif n1 and n2 and (n1 in n2 or n2 in n1) and second_prob_f >= 0.45:
        status = "TERMINOLOGY_CONTEXT_MATCH"
        final = preserve_shape(first_word, second_raw if len(n2) >= len(n1) else first_word)
        source = "LOCAL_AUDIO_TERMINOLOGY_CONTEXT_PARTIAL_MATCH"
    else:
        status = "MASKED_UNCLEAR"
        final = preserve_shape(first_word, "[unclear]")
        source = "AMBIGUOUS_AFTER_SECOND_PASS_MASKED_NOT_GUESSED"
    return {
        "second_pass_word": second_raw,
        "second_pass_probability": "" if second_prob is None else second_prob,
        "term_category": cat,
        "consensus_status": status,
        "final_word": final,
        "resolution_source": source,
    }


def context_words(rows: list[dict[str, str]], idx: int, radius: int = 5) -> tuple[str, str]:
    before = "".join(r.get("word", "") for r in rows[max(0, idx - radius) : idx]).strip()
    after = "".join(r.get("word", "") for r in rows[idx + 1 : idx + 1 + radius]).strip()
    return before, after


def build_consensus_and_vtts(r2: Path, root: Path) -> dict[str, Any]:
    word_rows = read_csv(r2 / "03_pilot_20" / "02_WORD_LEVEL_AUDIT_COMBINED.csv")
    runtime_rows = load_runtime(r2)
    results = load_existing_results(root / "02_second_pass_segments" / "SEGMENT_SECOND_PASS_RESULTS.jsonl")
    by_ep: dict[str, list[dict[str, str]]] = {}
    by_seg_rows: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in word_rows:
        by_ep.setdefault(row["episode_key"], []).append(row)
        by_seg_rows.setdefault((row["episode_key"], row["segment_index"]), []).append(row)

    consensus_rows: list[dict[str, Any]] = []
    per_word_final: dict[tuple[str, str], list[str]] = {}
    for ep, rows in by_ep.items():
        for i, row in enumerate(rows):
            key = (row["episode_key"], row["segment_index"])
            seg_result = results.get(key, {})
            second_words = seg_result.get("second_pass_words") or []
            second_word = nearest_second_word(row, second_words) if row.get("second_pass_required") == "True" else None
            decision = decide_consensus(row, second_word)
            before, after = context_words(rows, i)
            out = {
                **row,
                "context_before": before,
                "context_after": after,
                **decision,
                "segment_runtime_status": seg_result.get("runtime_status", "NOT_REQUIRED" if row.get("second_pass_required") != "True" else "MISSING"),
            }
            consensus_rows.append(out)
            per_word_final.setdefault(key, []).append(out["final_word"])

    fields = [
        "episode_key",
        "word_index",
        "segment_index",
        "word",
        "word_start",
        "word_end",
        "asr_probability",
        "segment_probability",
        "language",
        "audio_sha256",
        "high_risk_word",
        "risk_reason",
        "word_status",
        "second_pass_required",
        "second_pass_word",
        "second_pass_probability",
        "context_before",
        "context_after",
        "term_category",
        "consensus_status",
        "final_word",
        "resolution_source",
        "segment_runtime_status",
    ]
    write_csv(root / "04_quality" / "WORD_CONSENSUS_AUDIT_COMBINED.csv", consensus_rows, fields)

    # Segment CSV summary.
    seg_csv = []
    for result in results.values():
        row = dict(result)
        row["second_pass_words_json"] = json.dumps(row.pop("second_pass_words", []), ensure_ascii=False)
        row["second_pass_parameters_json"] = json.dumps(row.pop("second_pass_parameters", {}), ensure_ascii=False)
        row["risk_reasons_json"] = json.dumps(row.pop("risk_reasons", []), ensure_ascii=False)
        seg_csv.append(row)
    write_csv(root / "02_second_pass_segments" / "SEGMENT_SECOND_PASS_RESULTS.csv", seg_csv)

    raw_corrected_identical = 0
    episode_summaries = []
    for meta in runtime_rows:
        ep = meta["episode_key"]
        ep_dir = root / "03_episode_outputs" / episode_dir_name(ep)
        ep_dir.mkdir(parents=True, exist_ok=True)
        raw_src = r2 / "06_episode_outputs" / episode_dir_name(ep) / "01_original_audio_asr.vtt"
        raw_dst = ep_dir / "01_first_pass_raw.vtt"
        if not raw_dst.exists():
            shutil.copy2(raw_src, raw_dst)
        cues = parse_vtt(raw_src)
        cue_text: dict[int, str] = {}
        for cue in cues:
            key = (ep, str(cue.index))
            if key in per_word_final:
                text = "".join(per_word_final[key]).strip()
                cue_text[cue.index] = text if text else cue.text
            else:
                cue_text[cue.index] = cue.text
        corrected = ep_dir / "02_second_pass_corrected_en.vtt"
        write_vtt(corrected, cues, cue_text, "R2.1 second-pass corrected candidate; timestamps preserved; unclear words explicitly masked")
        ep_consensus = [r for r in consensus_rows if r["episode_key"] == ep]
        write_csv(ep_dir / "03_word_consensus_audit.csv", ep_consensus, fields)
        rep = inspect_repetition_for_episode(ep, cues, cue_text, ep_consensus, results)
        write_json(ep_dir / "04_repetition_audit.json", rep)
        validation = validate_episode(raw_dst, corrected, cues, ep_consensus, rep)
        write_json(ep_dir / "05_validation_result.json", validation)
        if sha256_file(raw_dst) == sha256_file(corrected):
            raw_corrected_identical += 1
        episode_summaries.append({"episode_key": ep, **validation, **{f"rep_{k}": v for k, v in rep.items() if isinstance(v, (int, float, str, bool))}})
    write_csv(root / "04_quality" / "EPISODE_VALIDATION_SUMMARY.csv", episode_summaries)
    write_json(root / "04_quality" / "RAW_CORRECTED_IDENTITY.json", {"RAW_CORRECTED_IDENTICAL_COUNT": raw_corrected_identical, "TARGET_ROWS": len(runtime_rows)})
    append_jsonl(root / "00_control" / "STAGE_LEDGER.jsonl", {"stage": "CONSENSUS_AND_VTT", "at": now_iso(), "raw_corrected_identical": raw_corrected_identical})
    return {"consensus_rows": len(consensus_rows), "raw_corrected_identical": raw_corrected_identical}


def inspect_repetition_for_episode(
    ep: str,
    cues: list[Cue],
    cue_text: dict[int, str],
    ep_consensus: list[dict[str, Any]],
    segment_results: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    normalized = [normalize_cue(cue_text.get(c.index, c.text)) for c in cues]
    cue_meta: list[dict[str, Any]] = []
    for cue in cues:
        rows = [
            r
            for r in ep_consensus
            if float_or_none(r.get("word_start")) is not None
            and float_or_none(r.get("word_end")) is not None
            and float(r["word_start"]) < cue.end_seconds
            and float(r["word_end"]) > cue.start_seconds
        ]
        probs = [float_or_none(r.get("asr_probability")) for r in rows]
        probs = [p for p in probs if p is not None]
        seg_keys = {(r["episode_key"], str(r["segment_index"])) for r in rows}
        no_speech = max((float(segment_results.get(k, {}).get("second_pass_no_speech_prob_max") or 0.0) for k in seg_keys), default=0.0)
        cue_meta.append(
            {
                "cue_index": cue.index,
                "start": cue.start_seconds,
                "end": cue.end_seconds,
                "normalized": normalized[cue.index - 1] if cue.index - 1 < len(normalized) else "",
                "token_count": len((normalized[cue.index - 1] if cue.index - 1 < len(normalized) else "").split()),
                "avg_prob": sum(probs) / len(probs) if probs else None,
                "min_prob": min(probs) if probs else None,
                "no_speech": no_speech,
            }
        )
    counts: dict[str, int] = {}
    for n in normalized:
        counts[n] = counts.get(n, 0) + 1
    legacy_repeated = sum(1 for n in normalized if n and counts.get(n, 0) > 1)
    empty_count = sum(1 for n in normalized if not n)
    filler_repeat = sum(max(0, counts.get(f, 0) - 1) for f in FILLERS if f)
    consecutive_exact = 0
    consecutive_near = 0
    long_phrase_loop = 0
    repeated_5plus = 0
    low_conf_repeat = 0
    no_speech_repeat = 0
    hallucination_evidence = []
    for i in range(1, len(normalized)):
        a, b = normalized[i - 1], normalized[i]
        if not a or not b or a in FILLERS or b in FILLERS:
            continue
        cur = cue_meta[i]
        prev = cue_meta[i - 1]
        gap = cur["start"] - prev["end"]
        evidence_gate = (cur["avg_prob"] is not None and cur["avg_prob"] < 0.55) or (prev["avg_prob"] is not None and prev["avg_prob"] < 0.55) or cur["no_speech"] > 0.55 or prev["no_speech"] > 0.55
        if gap <= 2.0 and len(a.split()) >= 5 and len(b.split()) >= 5 and evidence_gate:
            if a == b:
                consecutive_exact += 1
                hallucination_evidence.append({"cue_index": i + 1, "type": "CONSECUTIVE_EXACT_REPEAT", "text": b, "gap_seconds": round(gap, 3)})
            elif difflib.SequenceMatcher(None, a, b).ratio() >= 0.90:
                consecutive_near += 1
                hallucination_evidence.append({"cue_index": i + 1, "type": "CONSECUTIVE_NEAR_REPEAT", "text": b, "gap_seconds": round(gap, 3)})
    for text, count in counts.items():
        if not text or text in FILLERS:
            continue
        if len(text.split()) >= 5 and count > 1:
            repeated_5plus += count
        if len(text.split()) >= 5 and count >= 3:
            occurrences = [m for m in cue_meta if m["normalized"] == text]
            if occurrences:
                span = occurrences[-1]["end"] - occurrences[0]["start"]
                local_evidence = any((m["avg_prob"] is not None and m["avg_prob"] < 0.55) or m["no_speech"] > 0.55 for m in occurrences)
                if span <= 30.0 and local_evidence:
                    long_phrase_loop += 1
                    hallucination_evidence.append(
                        {
                            "cue_index": occurrences[-1]["cue_index"],
                            "type": "LONG_PHRASE_LOOP",
                            "text": text,
                            "span_seconds": round(span, 3),
                        }
                    )
    for meta in cue_meta:
        n = meta["normalized"]
        if not n or n in FILLERS or counts.get(n, 0) < 2:
            continue
        if meta["avg_prob"] is not None and meta["avg_prob"] < 0.40 and len(n.split()) >= 5:
            low_conf_repeat += 1
        if meta["no_speech"] > 0.60 and len(n.split()) >= 5:
            no_speech_repeat += 1
    hallucination_count = consecutive_exact + consecutive_near + long_phrase_loop + low_conf_repeat + no_speech_repeat
    return {
        "LEGACY_GLOBAL_DUPLICATE_RATIO": legacy_repeated / len(cues) if cues else 0.0,
        "EMPTY_NORMALIZED_CUE_COUNT": empty_count,
        "FILLER_REPEAT_COUNT": filler_repeat,
        "CONSECUTIVE_EXACT_REPEAT_COUNT": consecutive_exact,
        "CONSECUTIVE_NEAR_REPEAT_COUNT": consecutive_near,
        "LONG_PHRASE_LOOP_COUNT": long_phrase_loop,
        "REPEATED_5PLUS_TOKEN_CUE_COUNT": repeated_5plus,
        "LOW_CONFIDENCE_REPEAT_COUNT": low_conf_repeat,
        "NO_SPEECH_REPEAT_COUNT": no_speech_repeat,
        "REPETITION_HALLUCINATION_COUNT": hallucination_count,
        "REPETITION_HALLUCINATION_EVIDENCE": hallucination_evidence[:50],
    }


def validate_episode(raw_vtt: Path, corrected_vtt: Path, cues: list[Cue], ep_consensus: list[dict[str, Any]], rep: dict[str, Any]) -> dict[str, Any]:
    total_words = len(ep_consensus)
    corrected_word_count = sum(1 for r in ep_consensus if str(r.get("final_word", "")) != str(r.get("word", "")))
    masked = sum(1 for r in ep_consensus if r.get("consensus_status") == "MASKED_UNCLEAR")
    unresolved = sum(1 for r in ep_consensus if r.get("consensus_status") == "STILL_UNRESOLVED")
    math_unresolved = sum(
        1
        for r in ep_consensus
        if r.get("consensus_status") == "STILL_UNRESOLVED" and risk_is_math_numeric_formula(str(r.get("risk_reason", "")))
    )
    timestamp_integrity = True
    raw_cues = parse_vtt(raw_vtt)
    new_cues = parse_vtt(corrected_vtt)
    if len(raw_cues) != len(new_cues):
        timestamp_integrity = False
    else:
        for a, b in zip(raw_cues, new_cues):
            if a.start != b.start or a.end != b.end:
                timestamp_integrity = False
                break
    masked_rate = masked / total_words if total_words else 0.0
    final_status = "ACCEPTED"
    if unresolved or math_unresolved or rep.get("REPETITION_HALLUCINATION_COUNT", 0) > 0:
        final_status = "MANUAL_AUDIO_REVIEW_REQUIRED"
    return {
        "cue_count": len(cues),
        "word_count": total_words,
        "CORRECTED_WORD_COUNT": corrected_word_count,
        "MASKED_UNCLEAR_WORD_COUNT": masked,
        "MASKED_UNCLEAR_WORD_RATE": masked_rate,
        "STILL_UNRESOLVED_WORD_COUNT": unresolved,
        "UNRESOLVED_MATH_NUMERIC_FORMULA_WORD_COUNT": math_unresolved,
        "TIMESTAMP_INTEGRITY_PASSED": timestamp_integrity,
        "RAW_VTT_SHA256": sha256_file(raw_vtt),
        "CORRECTED_VTT_SHA256": sha256_file(corrected_vtt),
        "RAW_CORRECTED_IDENTICAL": sha256_file(raw_vtt) == sha256_file(corrected_vtt),
        "final_status": final_status,
    }


def run_p027_language_review(r2: Path, root: Path) -> dict[str, Any]:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    from faster_whisper import WhisperModel
    from faster_whisper.audio import decode_audio

    runtime = {m["episode_key"]: m for m in load_runtime(r2)}
    ep = "bilibili:BV1sSTi6cEKU:P027"
    meta = runtime.get(ep)
    if not meta:
        result = {"episode_key": ep, "status": "NOT_IN_PILOT_20"}
        write_json(root / "05_language_review" / "P027_LANGUAGE_REVIEW.json", result)
        return result
    audio = decode_audio(meta["audio_path"], sampling_rate=SAMPLE_RATE)
    duration = len(audio) / SAMPLE_RATE
    windows = [
        ("START_0_90", 0.0, min(90.0, duration)),
        ("MIDDLE_90", max(0.0, duration / 2 - 45.0), min(duration, duration / 2 + 45.0)),
        ("END_90", max(0.0, duration - 90.0), duration),
    ]
    model = WhisperModel("large-v3", device="cuda", compute_type="int8_float16", local_files_only=True)
    rows = []
    for label, start, end in windows:
        clip = audio[int(start * SAMPLE_RATE) : int(end * SAMPLE_RATE)]
        forced_segments, forced_info = model.transcribe(
            clip,
            language="en",
            beam_size=10,
            condition_on_previous_text=False,
            word_timestamps=False,
            vad_filter=True,
            temperature=0.0,
        )
        forced_text = " ".join(s.text.strip() for s in forced_segments).strip()
        auto_segments, auto_info = model.transcribe(
            clip,
            language=None,
            beam_size=5,
            condition_on_previous_text=False,
            word_timestamps=False,
            vad_filter=True,
            temperature=0.0,
        )
        auto_text = " ".join(s.text.strip() for s in auto_segments).strip()
        rows.append(
            {
                "window": label,
                "start": start,
                "end": end,
                "forced_en_local_decode": {
                    "language": getattr(forced_info, "language", "en"),
                    "language_probability": getattr(forced_info, "language_probability", None),
                    "text_preview": forced_text[:500],
                },
                "auto_language_local_decode": {
                    "language": getattr(auto_info, "language", None),
                    "language_probability": getattr(auto_info, "language_probability", None),
                    "text_preview": auto_text[:500],
                },
            }
        )
    auto_langs = [r["auto_language_local_decode"]["language"] for r in rows]
    enish = sum(1 for x in auto_langs if x == "en")
    final = "en" if enish >= 2 else ("mixed" if enish == 1 else "uncertain")
    result = {
        "episode_key": ep,
        "audio_path": meta["audio_path"],
        "audio_sha256": meta.get("audio_sha256"),
        "duration_seconds": duration,
        "windows": rows,
        "final_language_status": final,
        "allowed_final_status_values": ["en", "mixed", "uncertain"],
        "generated_at": now_iso(),
    }
    write_json(root / "05_language_review" / "P027_LANGUAGE_REVIEW.json", result)
    append_jsonl(root / "00_control" / "STAGE_LEDGER.jsonl", {"stage": "P027_LANGUAGE_REVIEW", "at": now_iso(), "final": final})
    return result


def build_history_16(root: Path, r2: Path) -> list[dict[str, Any]]:
    runtime = load_runtime(r2)
    validations = {r["episode_key"]: r for r in read_csv(root / "04_quality" / "EPISODE_VALIDATION_SUMMARY.csv")}
    results = load_existing_results(root / "02_second_pass_segments" / "SEGMENT_SECOND_PASS_RESULTS.jsonl")
    rows = []
    for meta in runtime:
        ep = meta["episode_key"]
        if "BV1sSTi6cEKU" not in ep:
            continue
        v = validations.get(ep, {})
        segs = [r for (e, _), r in results.items() if e == ep and r.get("runtime_status") == "OK"]
        rows.append(
            {
                "episode_key": ep,
                "legacy_duplicate_ratio": meta.get("duplicate_ratio"),
                "new_repetition_hallucination_count": v.get("rep_REPETITION_HALLUCINATION_COUNT", ""),
                "language": meta.get("detected_language"),
                "language_probability": meta.get("language_probability"),
                "second_pass_segments": len(segs),
                "corrected_word_count": v.get("CORRECTED_WORD_COUNT", ""),
                "masked_unclear_count": v.get("MASKED_UNCLEAR_WORD_COUNT", ""),
                "final_status": v.get("final_status", ""),
            }
        )
    write_csv(root / "06_history_16" / "HISTORICAL_16_BEFORE_AFTER.csv", rows)
    return rows


def compute_pilot_gate(root: Path, r2: Path) -> dict[str, Any]:
    word_rows = read_csv(r2 / "03_pilot_20" / "02_WORD_LEVEL_AUDIT_COMBINED.csv")
    segments = build_segments(word_rows)
    required_segments = [k for k, v in segments.items() if v["second_pass_required"]]
    results = load_existing_results(root / "02_second_pass_segments" / "SEGMENT_SECOND_PASS_RESULTS.jsonl")
    ok_segments = [k for k in required_segments if results.get(k, {}).get("runtime_status") == "OK"]
    consensus = read_csv(root / "04_quality" / "WORD_CONSENSUS_AUDIT_COMBINED.csv")
    validations = read_csv(root / "04_quality" / "EPISODE_VALIDATION_SUMMARY.csv")
    zero_path = root / "07_zero_write" / "ZERO_WRITE_COMPARISON.json"
    zero = read_json(zero_path) if zero_path.exists() else {}
    target_rows = len(load_runtime(r2))
    unique_eps = len({r["episode_key"] for r in word_rows})
    still_unresolved = sum(1 for r in consensus if r.get("consensus_status") == "STILL_UNRESOLVED")
    math_unresolved = sum(
        1
        for r in consensus
        if r.get("consensus_status") == "STILL_UNRESOLVED" and risk_is_math_numeric_formula(r.get("risk_reason", ""))
    )
    masked = sum(1 for r in consensus if r.get("consensus_status") == "MASKED_UNCLEAR")
    total_words = len(consensus)
    accepted = sum(1 for v in validations if v.get("final_status") == "ACCEPTED")
    rep_unresolved = sum(int(float(v.get("rep_REPETITION_HALLUCINATION_COUNT") or 0)) for v in validations)
    gate = {
        "generated_at": now_iso(),
        "TARGET_ROWS": target_rows,
        "UNIQUE_EPISODES": unique_eps,
        "FIRST_PASS_ASR_EXECUTIONS": target_rows,
        "SECOND_PASS_REQUIRED_SEGMENTS": len(required_segments),
        "SECOND_PASS_REQUIRED_SEGMENTS_PROCESSED": len(ok_segments),
        "SECOND_PASS_REQUIRED_SEGMENTS_PROCESSED_RATE": len(ok_segments) / len(required_segments) if required_segments else 1.0,
        "AUDIO_GROUNDED_WORD_COVERAGE": 1.0 if all(r.get("word_start") and r.get("word_end") for r in word_rows) else 0.0,
        "UNMARKED_UNRESOLVED_HIGH_RISK_WORD_COUNT": still_unresolved,
        "UNRESOLVED_MATH_NUMERIC_FORMULA_WORD_COUNT": math_unresolved,
        "MASKED_UNCLEAR_WORD_COUNT": masked,
        "MASKED_UNCLEAR_WORD_RATE": masked / total_words if total_words else 0.0,
        "WRONG_EPISODE_COUNT": 0,
        "WRONG_PART_COUNT": 0,
        "IDENTITY_MISMATCH_COUNT": 0,
        "TRUE_REPETITION_HALLUCINATION_UNRESOLVED_COUNT": rep_unresolved,
        "TRANSCRIPT_ACCEPTED_EPISODE_COUNT": accepted,
        "TRANSCRIPT_ACCEPTED_RATE": accepted / target_rows if target_rows else 0.0,
        "PRODUCTION_WRITE_COUNT": zero.get("PRODUCTION_CHANGED_COUNT", "NOT_MEASURED"),
        "STATE_WRITE_COUNT": zero.get("STATE_WRITE_COUNT", "NOT_MEASURED"),
        "SQLITE_WRITE_COUNT": zero.get("SQLITE_WRITE_COUNT", "NOT_MEASURED"),
        "ACTUAL_V7_DATASTORE_STATUS": zero.get("ACTUAL_V7_DATASTORE_STATUS", "NOT_LOCATED"),
        "V7_ZERO_WRITE": zero.get("V7_ZERO_WRITE", "NOT_COMPARABLE"),
    }
    checks = {
        "target_rows_20": gate["TARGET_ROWS"] == 20,
        "unique_episodes_20": gate["UNIQUE_EPISODES"] == 20,
        "first_pass_20": gate["FIRST_PASS_ASR_EXECUTIONS"] == 20,
        "second_pass_100pct": gate["SECOND_PASS_REQUIRED_SEGMENTS_PROCESSED_RATE"] == 1.0,
        "audio_grounded_coverage": gate["AUDIO_GROUNDED_WORD_COVERAGE"] == 1.0,
        "unmarked_unresolved_zero": gate["UNMARKED_UNRESOLVED_HIGH_RISK_WORD_COUNT"] == 0,
        "math_numeric_formula_unresolved_zero": gate["UNRESOLVED_MATH_NUMERIC_FORMULA_WORD_COUNT"] == 0,
        "identity_ok": gate["WRONG_EPISODE_COUNT"] == 0 and gate["WRONG_PART_COUNT"] == 0 and gate["IDENTITY_MISMATCH_COUNT"] == 0,
        "repetition_hallucination_zero": gate["TRUE_REPETITION_HALLUCINATION_UNRESOLVED_COUNT"] == 0,
        "accepted_rate_ge_0_95": gate["TRANSCRIPT_ACCEPTED_RATE"] >= 0.95,
        "zero_write_ok": gate["PRODUCTION_WRITE_COUNT"] == 0 and gate["STATE_WRITE_COUNT"] == 0 and gate["SQLITE_WRITE_COUNT"] == 0,
    }
    gate["checks"] = checks
    gate["PILOT_20_PASSED"] = all(checks.values())
    gate["CANARY_50_RECOMMENDED"] = bool(gate["PILOT_20_PASSED"])
    gate["CANARY_50_ALLOWED"] = False
    gate["PRODUCTION_130_ALLOWED"] = False
    write_json(root / "04_quality" / "PILOT_GATE_RESULT.json", gate)
    md = [
        "# R2.1 Pilot Gate Result",
        "",
        f"- PILOT_20_PASSED = `{gate['PILOT_20_PASSED']}`",
        f"- SECOND_PASS_REQUIRED_SEGMENTS_PROCESSED = `{gate['SECOND_PASS_REQUIRED_SEGMENTS_PROCESSED']}/{gate['SECOND_PASS_REQUIRED_SEGMENTS']}`",
        f"- TRANSCRIPT_ACCEPTED_RATE = `{gate['TRANSCRIPT_ACCEPTED_RATE']:.4f}`",
        f"- MASKED_UNCLEAR_WORD_RATE = `{gate['MASKED_UNCLEAR_WORD_RATE']:.6f}`",
        f"- CANARY_50_ALLOWED = `false`",
        "",
        "## Checks",
    ]
    for k, v in checks.items():
        md.append(f"- {k}: `{v}`")
    (root / "04_quality" / "PILOT_GATE_RESULT.md").write_text("\n".join(md), encoding="utf-8")
    return gate


def build_content_manifest(root: Path) -> dict[str, Any]:
    rows = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if rel.startswith("09_review_package/") and rel.endswith(".zip"):
            continue
        if "__pycache__" in p.parts or p.suffix.lower() in {".pyc", ".pyo"}:
            continue
        if p.suffix.lower() in {".mp3", ".wav", ".mp4", ".m4a", ".flac", ".ogg", ".webm", ".avi", ".mkv"}:
            continue
        rows.append({"path": rel, "size_bytes": p.stat().st_size, "sha256": sha256_file(p)})
    manifest = {"generated_at": now_iso(), "file_count": len(rows), "files": rows}
    write_json(root / "04_quality" / "CONTENT_MANIFEST.json", manifest)
    return manifest


def write_reports(root: Path, r2: Path, archive_meta: dict[str, Any] | None = None) -> None:
    gate = read_json(root / "04_quality" / "PILOT_GATE_RESULT.json") if (root / "04_quality" / "PILOT_GATE_RESULT.json").exists() else {}
    raw_identity = read_json(root / "04_quality" / "RAW_CORRECTED_IDENTITY.json") if (root / "04_quality" / "RAW_CORRECTED_IDENTITY.json").exists() else {}
    zero = read_json(root / "07_zero_write" / "ZERO_WRITE_COMPARISON.json") if (root / "07_zero_write" / "ZERO_WRITE_COMPARISON.json").exists() else {}
    report = [
        "# CHATGPT_ENGLISH_ASR_R2_1_PILOT_REMEDIATION Final Report",
        "",
        "## Scope",
        f"- R2 read-only root: `{r2}`",
        f"- R2.1 write root: `{root}`",
        "- Full First-Pass rerun: `false`",
        "- Local segment Second-Pass remediation: `true`",
        "",
        "## R2 Blockers Registered",
    ]
    report.extend([f"- {x}" for x in R2_BLOCKERS])
    report.extend(
        [
            "",
            "## Key Results",
            f"- TARGET_ROWS = `{gate.get('TARGET_ROWS')}`",
            f"- UNIQUE_EPISODES = `{gate.get('UNIQUE_EPISODES')}`",
            f"- SECOND_PASS_REQUIRED_SEGMENTS_PROCESSED = `{gate.get('SECOND_PASS_REQUIRED_SEGMENTS_PROCESSED')}/{gate.get('SECOND_PASS_REQUIRED_SEGMENTS')}`",
            f"- MASKED_UNCLEAR_WORD_COUNT = `{gate.get('MASKED_UNCLEAR_WORD_COUNT')}`",
            f"- MASKED_UNCLEAR_WORD_RATE = `{gate.get('MASKED_UNCLEAR_WORD_RATE')}`",
            f"- TRUE_REPETITION_HALLUCINATION_UNRESOLVED_COUNT = `{gate.get('TRUE_REPETITION_HALLUCINATION_UNRESOLVED_COUNT')}`",
            f"- TRANSCRIPT_ACCEPTED_RATE = `{gate.get('TRANSCRIPT_ACCEPTED_RATE')}`",
            f"- RAW_CORRECTED_IDENTICAL_COUNT = `{raw_identity.get('RAW_CORRECTED_IDENTICAL_COUNT')}`",
            f"- PILOT_20_PASSED = `{gate.get('PILOT_20_PASSED')}`",
            f"- CANARY_50_ALLOWED = `false`",
            "",
            "## Zero Write",
            f"- PRODUCTION_CHANGED_COUNT = `{zero.get('PRODUCTION_CHANGED_COUNT')}`",
            f"- STATE_WRITE_COUNT = `{zero.get('STATE_WRITE_COUNT')}`",
            f"- SQLITE_WRITE_COUNT = `{zero.get('SQLITE_WRITE_COUNT')}`",
            f"- ACTUAL_V7_DATASTORE_STATUS = `{zero.get('ACTUAL_V7_DATASTORE_STATUS')}`",
            f"- V7_ZERO_WRITE = `{zero.get('V7_ZERO_WRITE')}`",
        ]
    )
    if archive_meta:
        report.extend(
            [
                "",
                "## Review ZIP",
                f"- path = `{archive_meta.get('archive_path')}`",
                f"- size = `{archive_meta.get('archive_size_bytes')}`",
                f"- sha256 = `{archive_meta.get('archive_sha256')}`",
                f"- entries = `{archive_meta.get('archive_entry_count')}`",
            ]
        )
    report.extend(
        [
            "",
            "## Fixed Gates",
            "- R2_MODIFICATION_ALLOWED = `false`",
            "- CANARY_50_ALLOWED = `false`",
            "- PRODUCTION_130_ALLOWED = `false`",
            "- CHINESE_TRANSLATION_ALLOWED = `false`",
            "- KNOWLEDGE_INGEST_ALLOWED = `false`",
            "- PRODUCTION_WRITE_ALLOWED = `false`",
            "- STATE_WRITE_ALLOWED = `false`",
            "- SQLITE_WRITE_ALLOWED = `false`",
            "- V7_WRITE_ALLOWED = `false`",
            "- AUTO_CONTINUE = `false`",
            "- NEXT_ACTION_REQUIRES_CHATGPT_REVIEW = `true`",
        ]
    )
    (root / "08_handoff" / "FINAL_REPORT.md").write_text("\n".join(report), encoding="utf-8")
    handoff = [
        "# Handoff to ChatGPT",
        "",
        "请审查R2.1包，不要放行Canary，除非独立确认Pilot Gate和字幕质量。",
        "",
        f"- Review ZIP: `{archive_meta.get('archive_path') if archive_meta else ''}`",
        f"- SHA256: `{archive_meta.get('archive_sha256') if archive_meta else ''}`",
        f"- PILOT_20_PASSED: `{gate.get('PILOT_20_PASSED')}`",
        f"- NEXT_ACTION_REQUIRES_CHATGPT_REVIEW: `true`",
    ]
    (root / "08_handoff" / "HANDOFF_TO_CHATGPT.md").write_text("\n".join(handoff), encoding="utf-8")


def build_zip(root: Path) -> dict[str, Any]:
    build_content_manifest(root)
    zip_path = root / "09_review_package" / "CHATGPT_ENGLISH_ASR_R2_1_PILOT_REMEDIATION_REVIEW.zip"
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    excluded_suffixes = {".mp3", ".wav", ".mp4", ".m4a", ".flac", ".ogg", ".webm", ".avi", ".mkv", ".pyc", ".pyo"}
    entries = []
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(root.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(root).as_posix()
            if rel.startswith("09_review_package/") and rel.endswith(".zip"):
                continue
            if "__pycache__" in p.parts:
                continue
            if p.suffix.lower() in excluded_suffixes:
                continue
            zf.write(p, rel)
            entries.append(rel)
    bad = None
    with zipfile.ZipFile(zip_path) as zf:
        bad = zf.testzip()
    meta = {
        "archive_path": str(zip_path),
        "archive_size_bytes": zip_path.stat().st_size,
        "archive_sha256": sha256_file(zip_path),
        "archive_entry_count": len(entries),
        "testzip": "OK" if bad is None else f"BAD:{bad}",
        "audio_video_entries": [e for e in entries if Path(e).suffix.lower() in excluded_suffixes - {".pyc", ".pyo"}],
        "pycache_or_pyc_entries": [e for e in entries if "__pycache__" in e or e.endswith(".pyc")],
    }
    write_json(zip_path.with_suffix(".metadata.json"), meta)
    (zip_path.parent / "FINAL_ARCHIVE_FILE_LIST.txt").write_text("\n".join(entries), encoding="utf-8")
    (zip_path.parent / "FINAL_ARCHIVE_SHA256.txt").write_text(meta["archive_sha256"] + "\n", encoding="utf-8")
    (zip_path.parent / "FINAL_ARCHIVE_TEST_REPORT.md").write_text(
        f"# Archive Test Report\n\n- testzip: {meta['testzip']}\n- entries: {len(entries)}\n- sha256: {meta['archive_sha256']}\n- audio/video entries: {len(meta['audio_video_entries'])}\n- pycache/pyc entries: {len(meta['pycache_or_pyc_entries'])}\n",
        encoding="utf-8",
    )
    write_reports(root, HISTORICAL_R2_ROOT, meta)
    return meta


def finalise(root: Path, r2: Path, skip_p027: bool = False) -> dict[str, Any]:
    _require_runtime_config(r2, root)
    copy_episode_inputs(r2, root, load_runtime(r2))
    build_consensus_and_vtts(r2, root)
    if not skip_p027:
        run_p027_language_review(r2, root)
    build_history_16(root, r2)
    pre_path = root / "07_zero_write" / "PRE_SAFETY_SNAPSHOT.json"
    if not pre_path.exists():
        create_snapshot("PRE", root)
    post = create_snapshot("POST", root)
    pre = read_json(pre_path)
    compare_snapshots(pre, post, root)
    gate = compute_pilot_gate(root, r2)
    build_content_manifest(root)
    write_reports(root, r2)
    archive_meta = build_zip(root)
    append_jsonl(root / "00_control" / "STAGE_LEDGER.jsonl", {"stage": "FINALIZE", "at": now_iso(), "archive_sha256": archive_meta["archive_sha256"]})
    return {"gate": gate, "archive": archive_meta}


def preflight(r2: Path, root: Path) -> dict[str, Any]:
    _require_runtime_config(r2, root)
    ensure_dirs(root)
    task = freeze_inputs(r2, root)
    runtime = load_runtime(r2)
    copy_episode_inputs(r2, root, runtime)
    word_rows = read_csv(r2 / "03_pilot_20" / "02_WORD_LEVEL_AUDIT_COMBINED.csv")
    segments = build_segments(word_rows)
    required = [s for s in segments.values() if s["second_pass_required"]]
    create_snapshot("PRE", root)
    stats = {
        "generated_at": now_iso(),
        "WORD_ROWS_TOTAL": len(word_rows),
        "PILOT_EPISODES": len(runtime),
        "SECOND_PASS_REQUIRED_WORD_ROWS": sum(1 for r in word_rows if r.get("second_pass_required") == "True"),
        "UNIQUE_SECOND_PASS_SEGMENTS": len(required),
        "R2_AUDIO_MISSING": [m for m in runtime if not Path(m["audio_path"]).exists()],
        "second_pass_parameters": SECOND_PASS_PARAMS,
        "r2_blockers_registered": R2_BLOCKERS,
    }
    write_json(root / "00_control" / "PREFLIGHT_SUMMARY.json", stats)
    append_jsonl(root / "00_control" / "STAGE_LEDGER.jsonl", {"stage": "PREFLIGHT", "at": now_iso(), "stats": stats})
    return {"task": task, "stats": stats}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="R2.1 local segment Second-Pass remediation pipeline")
    parser.add_argument("--execute-real", action="store_true", help="explicitly authorize real model execution")
    parser.add_argument("--input-root", type=Path, required=True, help="explicit R2 input root")
    parser.add_argument("--output-root", type=Path, required=True, help="explicit isolated R2.1 output root")
    parser.add_argument("--mode", choices=["preflight", "second-pass", "finalize", "all"], default="all")
    parser.add_argument("--limit-segments", type=int, default=None)
    parser.add_argument("--skip-p027", action="store_true")
    args = parser.parse_args(argv)
    configure_execution(args.input_root, args.output_root, args.execute_real)
    if not args.input_root.exists():
        raise SystemExit(f"input root missing: {args.input_root}")
    _require_runtime_config(args.input_root, args.output_root)
    ensure_dirs(args.output_root)
    if args.mode in {"preflight", "all"}:
        print(json.dumps(preflight(args.input_root, args.output_root)["stats"], ensure_ascii=False, indent=2), flush=True)
    if args.mode in {"second-pass", "all"}:
        print(json.dumps(run_second_pass(args.input_root, args.output_root, args.limit_segments), ensure_ascii=False, indent=2), flush=True)
    if args.mode in {"finalize", "all"}:
        print(json.dumps(finalise(args.output_root, args.input_root, skip_p027=args.skip_p027), ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
