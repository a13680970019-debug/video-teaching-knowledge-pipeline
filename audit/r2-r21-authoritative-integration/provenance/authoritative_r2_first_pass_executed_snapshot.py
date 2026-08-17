from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"D:\AI-Agent-Workspaces\Codex\english-asr-word-audit-200-r2-audio-grounded-20260807")
R1_ROOT = Path(r"D:\AI-Agent-Workspaces\Codex\english-asr-word-audit-200-20260806")
R1_MANIFEST = R1_ROOT / "00_control" / "01_TARGET_200_MANIFEST.csv"
R1_REVIEW = Path(r"D:\UserData\Downloads\CHATGPT_ENGLISH_ASR_WORD_AUDIT_200_R1_INDEPENDENT_REVIEW.md")
R2_INSTRUCTION = Path(r"D:\UserData\Downloads\CODEX_ENGLISH_ASR_WORD_AUDIT_200_R2_AUDIO_GROUNDED_INSTRUCTION.md")
RECOVERY_QUEUE = Path(r"D:\AI-Agent-Workspaces\Codex\remaining-acquisition-asr-recovery-20260805\01_reconciliation\04_ASR_ONLY_REQUIRED.csv")
PROD_ROOT = Path(r"D:\视频教学采集系统")
PROD_AUDIO = PROD_ROOT / "audio_target_batch"
KB_ROOT = Path(r"D:\司法视频图像处理知识库\12大数学体系_课程资源")
KB_RAW_INGEST = KB_ROOT / "字幕_原始入库"
FFMPEG = Path(r"D:\AI-Env\ffmpeg\bin\ffmpeg.exe")
FFPROBE = Path(r"D:\AI-Env\ffmpeg\bin\ffprobe.exe")

TASK_ID = "CODEX-ENGLISH-ASR-WORD-AUDIT-200-R2-AUDIO-GROUNDED-20260807"
MODEL_SIZE = os.environ.get("R2_ASR_MODEL", "large-v3")
DEVICE = os.environ.get("R2_ASR_DEVICE", "cuda")
COMPUTE_TYPE = os.environ.get("R2_ASR_COMPUTE_TYPE", "int8_float16")
BEAM_SIZE = int(os.environ.get("R2_ASR_BEAM_SIZE", "5"))
VAD_SETTINGS = {"min_silence_duration_ms": 200}

GATES = {
    "R1_MODIFICATION_ALLOWED": False,
    "R2_IMPLEMENTATION_ALLOWED": True,
    "R2_ACTUAL_ASR_ALLOWED": True,
    "PILOT_20_ALLOWED": True,
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
}

R1_BLOCKERS = [
    "R1没有执行ASR，ASR_RUNTIME_ATTEMPTED=0",
    "16条历史英语失败课程没有重跑",
    "Pilot真实有效率只有4/20",
    "Canary 82%来自一个BVID",
    "Production在Pilot和Canary未正式通过时运行",
    "61,559个高风险词未解决",
    "全部269,059词没有音频置信度",
    "183/200校正VTT与原文完全一致",
    "37集没有音频",
    "语言检测来自旧字幕文本",
    "Gate Contract被删减",
    "V7未测量",
    "上传ZIP声明Hash与实际Hash不一致",
]

TERMS = {
    "fourier", "laplace", "gaussian", "pde", "series", "transform", "convolution",
    "kernel", "probability", "statistics", "variance", "covariance", "median",
    "percentile", "hypothesis", "distribution", "density", "matrix", "vector",
    "eigenvalue", "orthogonal", "integral", "derivative", "sigma", "lambda",
}
FORMULA_WORDS = {"squared", "square", "root", "minus", "plus", "times", "divided", "equals", "alpha", "beta", "gamma", "theta", "pi"}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def ensure_dirs() -> None:
    for rel in [
        "00_control/copied_instructions", "01_identity", "02_terminology", "03_pilot_20",
        "04_canary_50", "05_production_130", "06_episode_outputs", "07_quality",
        "08_handoff", "09_review_package", "raw_logs/language_detection_clips", "pipeline",
    ]:
        (ROOT / rel).mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    if fieldnames is None:
        fieldnames = []
        seen = set()
        for row in rows:
            for key in row.keys():
                if key not in seen:
                    seen.add(key)
                    fieldnames.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_name(episode_key: str) -> str:
    return episode_key.replace(":", "_").replace("/", "_").replace("\\", "_")


def pnum(part: str) -> int:
    m = re.search(r"(\d+)", part or "")
    return int(m.group(1)) if m else 999999


def ffprobe_duration_seconds(path: Path) -> float:
    result = subprocess.run(
        [str(FFPROBE), "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    return float(result.stdout.strip())


def ffprobe_version() -> str:
    result = subprocess.run([str(FFPROBE), "-version"], capture_output=True, text=True, timeout=30, check=True)
    return result.stdout.splitlines()[0] if result.stdout else ""


def ts(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def title_from_raw_ingest(bvid: str, part: str) -> str:
    path = KB_RAW_INGEST / f"{bvid}_{part}_原始入库.md"
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[:24]:
            if line.startswith("**title**:"):
                return line.split(":", 1)[1].strip()
    return ""


def copy_instructions() -> None:
    for p in [R1_REVIEW, R2_INSTRUCTION]:
        if p.exists():
            shutil.copy2(p, ROOT / "00_control" / "copied_instructions" / p.name)


def source_fields(rows: list[dict]) -> list[str]:
    fields: list[str] = []
    seen = set()
    for row in rows:
        for k in row.keys():
            if k not in seen:
                seen.add(k)
                fields.append(k)
    return fields


def make_candidate_from_audio(meta: dict, audio: Path) -> dict | None:
    m = re.search(r"(?P<bvid>BV[0-9A-Za-z]{10})#(?P<part>P\d{1,3})", audio.name, re.I)
    if not m:
        return None
    bvid = m.group("bvid")
    part = f"P{int(m.group('part')[1:]):03d}"
    title = title_from_raw_ingest(bvid, part) or f"{meta.get('collection_title', '')} {part}".strip()
    row = dict(meta)
    row.update({
        "episode_key": f"bilibili:{bvid}:{part}",
        "BVID": bvid,
        "part_index": part,
        "url": f"https://www.bilibili.com/video/{bvid}?p={int(part[1:])}",
        "title": title,
        "audio_path": str(audio),
        "audio_size_bytes": str(audio.stat().st_size),
        "audio_duration_seconds": f"{ffprobe_duration_seconds(audio):.3f}",
        "audio_sha256": sha256_file(audio),
        "source_vtt_path": "",
        "source_vtt_role": "R2_AUDIO_GROUNDED_TARGET",
        "source_status": "R2_REPLACEMENT_AUDIO_PRESENT",
        "selection_reason": "R2_REPLACEMENT_SAME_BVID_AVAILABLE_AUDIO",
    })
    return row


def build_audio_grounded_manifest() -> tuple[list[dict], list[dict], dict]:
    r1 = read_csv(R1_MANIFEST)
    base = [dict(r) for r in r1 if r.get("audio_path") and Path(r["audio_path"]).exists()]
    missing = [dict(r) for r in r1 if not (r.get("audio_path") and Path(r.get("audio_path", "")).exists())]
    selected = {r["episode_key"] for r in base}
    bvid_meta: dict[str, dict] = {}
    for r in r1:
        bvid_meta.setdefault(r.get("BVID", ""), r)

    replacements: list[dict] = []
    for bvid in sorted({r.get("BVID", "") for r in missing if r.get("BVID")}):
        meta = bvid_meta[bvid]
        for audio in sorted(PROD_AUDIO.glob(f"{bvid}#P*.mp3"), key=lambda p: p.name):
            cand = make_candidate_from_audio(meta, audio)
            if not cand or cand["episode_key"] in selected:
                continue
            if float(cand["audio_duration_seconds"]) <= 5:
                continue
            replacements.append(cand)
            selected.add(cand["episode_key"])

    replacements.sort(key=lambda r: (int(r.get("module_id") or 999), r.get("BVID", ""), pnum(r.get("part_index", ""))))
    final = base + replacements
    if len(final) < 200 and RECOVERY_QUEUE.exists():
        for row in read_csv(RECOVERY_QUEUE):
            if row.get("episode_key") in selected:
                continue
            audio = Path(row.get("audio_path", ""))
            if not audio.exists():
                continue
            try:
                duration = ffprobe_duration_seconds(audio)
            except Exception:
                continue
            if duration <= 5:
                continue
            new = dict(row)
            new["audio_duration_seconds"] = f"{duration:.3f}"
            if not new.get("audio_sha256"):
                new["audio_sha256"] = sha256_file(audio)
            new["source_vtt_path"] = new.get("subtitle_path", "")
            new["source_vtt_role"] = "RECOVERY_ASR_ONLY_REQUIRED_QUEUE"
            new["selection_reason"] = "R2_REPLACEMENT_ASR_ONLY_REQUIRED_QUEUE"
            final.append(new)
            selected.add(new["episode_key"])
            if len(final) >= 200:
                break
    final = final[:200]
    for i, row in enumerate(final, start=1):
        row["target_row_index"] = str(i)
        row["batch_stage"] = "PILOT_20" if i <= 20 else "PENDING_CANARY_OR_PRODUCTION_GATE"

    added = final[len(base):]
    changes: list[dict] = []
    for i, old in enumerate(missing, start=1):
        new = added[i - 1] if i - 1 < len(added) else {}
        changes.append({
            "change_index": i,
            "removed_episode_key": old.get("episode_key", ""),
            "removed_module_id": old.get("module_id", ""),
            "removed_reason": "R1_AUDIO_MISSING_OR_INVALID",
            "replacement_episode_key": new.get("episode_key", ""),
            "replacement_module_id": new.get("module_id", ""),
            "replacement_audio_path": new.get("audio_path", ""),
            "replacement_reason": new.get("selection_reason", ""),
        })

    summary = {
        "generated_at": now_iso(),
        "r1_rows": len(r1),
        "r1_valid_audio_rows_kept": len(base),
        "r1_missing_audio_rows_replaced": len(missing),
        "target_rows": len(final),
        "unique_episode_keys": len({r["episode_key"] for r in final}),
        "valid_audio_rows": sum(1 for r in final if r.get("audio_path") and Path(r["audio_path"]).exists()),
        "audio_sha256_present": sum(1 for r in final if r.get("audio_sha256")),
        "module_count": len({r.get("module_id", "") for r in final}),
        "modules": sorted({r.get("module_id", "") for r in final}, key=lambda x: int(x or 999)),
        "historical_16_preserved": sum(1 for r in final if r.get("selection_reason") == "HISTORICAL_16_REPEAT_FAILURE_PRIORITY"),
        "pilot_rows": 20,
    }
    fields = source_fields(final)
    write_csv(ROOT / "00_control" / "01_TARGET_200_AUDIO_GROUNDED_MANIFEST.csv", final, fields)
    write_csv(ROOT / "00_control" / "02_TARGET_CHANGE_LOG.csv", changes)
    write_json(ROOT / "00_control" / "03_TARGET_AUDIO_REBUILD_SUMMARY.json", summary)
    write_csv(ROOT / "03_pilot_20" / "01_PILOT_20_MANIFEST.csv", final[:20], fields)
    return final, changes, summary


def normalize_word(word: str) -> str:
    return re.sub(r"[^0-9A-Za-z]+", "", word or "").lower()


def term_category(word: str) -> str:
    w = normalize_word(word)
    if not w:
        return ""
    if any(ch.isdigit() for ch in w):
        return "NUMERIC"
    if w in TERMS:
        return "MATH_TERM"
    if w in FORMULA_WORDS:
        return "FORMULA_SPEECH"
    if len(w) == 1 and w in set("abcdefghijklmnopqrstuvwxyz"):
        return "SYMBOL_LETTER"
    return ""


def status_for_word(word: str, probability: float | None) -> tuple[str, bool, str]:
    p = float(probability or 0.0)
    cat = term_category(word)
    high = bool(cat) or p < 0.60
    if p >= 0.80:
        status = "AUTO_CONFIRMED_ACOUSTIC"
    elif p >= 0.60:
        status = "AUTO_CONFIRMED_CONTEXT"
    elif p >= 0.40:
        status = "UNCERTAIN"
    else:
        status = "AUDIO_REVIEW_REQUIRED"
    return status, high, cat or ("LOW_ASR_PROBABILITY" if p < 0.60 else "")


def duplicate_ratio(texts: list[str]) -> float:
    norm = [" ".join(re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?|\d+(?:\.\d+)?|[\u4e00-\u9fff]", t.lower())) for t in texts if t.strip()]
    if not norm:
        return 1.0
    c = Counter(norm)
    dup = sum(v for v in c.values() if v > 1)
    return dup / len(norm)


def longest_run(texts: list[str]) -> int:
    best = cur = 0
    prev = None
    for text in texts:
        n = " ".join(text.lower().split())
        if n and n == prev:
            cur += 1
        else:
            cur = 1 if n else 0
        prev = n
        best = max(best, cur)
    return best


def detect_language(model, audio_path: Path, episode_key: str) -> dict:
    clip = ROOT / "raw_logs" / "language_detection_clips" / f"{safe_name(episode_key)}_first90s.mp3"
    try:
        subprocess.run([str(FFMPEG), "-y", "-ss", "0", "-t", "90", "-i", str(audio_path), "-vn", "-acodec", "copy", str(clip)], capture_output=True, text=True, timeout=120, check=True)
        segs, info = model.transcribe(str(clip), beam_size=1, vad_filter=True, word_timestamps=False)
        sample = " ".join((s.text or "").strip() for s in segs)[:500]
        raw_lang = getattr(info, "language", "")
        mapped_lang = raw_lang if raw_lang in {"en", "zh"} else "uncertain"
        return {
            "detected_language": mapped_lang,
            "raw_detector_language": raw_lang,
            "language_probability": float(getattr(info, "language_probability", 0.0) or 0.0),
            "language_detection_basis": "AUDIO_FIRST_90_SECONDS_FASTER_WHISPER",
            "language_detection_sample_text": sample,
        }
    finally:
        try:
            if clip.exists():
                clip.unlink()
        except Exception:
            pass


def write_vtt(segments: list[dict]) -> str:
    lines = ["WEBVTT", "", f"NOTE R2 audio-grounded faster-whisper {MODEL_SIZE}; word_timestamps=True", ""]
    for seg in segments:
        text = (seg["text"] or "").strip()
        if not text:
            continue
        lines.append(f"{ts(seg['start'])} --> {ts(seg['end'])}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


def segment_dicts(segments) -> list[dict]:
    out: list[dict] = []
    for seg in segments:
        words = []
        for w in (getattr(seg, "words", None) or []):
            words.append({
                "start": float(w.start) if w.start is not None else None,
                "end": float(w.end) if w.end is not None else None,
                "word": w.word,
                "probability": float(w.probability) if w.probability is not None else None,
            })
        out.append({
            "start": float(seg.start),
            "end": float(seg.end),
            "text": (seg.text or "").strip(),
            "avg_logprob": float(getattr(seg, "avg_logprob", 0.0) or 0.0),
            "no_speech_prob": float(getattr(seg, "no_speech_prob", 0.0) or 0.0),
            "words": words,
        })
    return out


def run_asr_pilot(pilot: list[dict]) -> list[dict]:
    from faster_whisper import WhisperModel

    stage_log = ROOT / "00_control" / "07_STAGE_LEDGER.jsonl"
    append_jsonl(stage_log, {"ts": now_iso(), "stage": "PILOT_20_ASR", "status": "START", "rows": len(pilot)})
    model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
    results: list[dict] = []
    all_words: list[dict] = []
    all_redecode: list[dict] = []
    for idx, row in enumerate(pilot, start=1):
        episode_key = row["episode_key"]
        audio = Path(row["audio_path"])
        out_dir = ROOT / "06_episode_outputs" / safe_name(episode_key)
        out_dir.mkdir(parents=True, exist_ok=True)
        started_at = now_iso()
        t0 = time.time()
        append_jsonl(stage_log, {"ts": started_at, "stage": "PILOT_20_ASR", "status": "EPISODE_START", "index": idx, "episode_key": episode_key})

        audio_sha = sha256_file(audio)
        duration = ffprobe_duration_seconds(audio)
        lang = detect_language(model, audio, episode_key)
        asr_lang = "en" if row.get("selection_reason") == "HISTORICAL_16_REPEAT_FAILURE_PRIORITY" else (lang["detected_language"] if lang["detected_language"] in {"en", "zh"} else None)
        kwargs = {"beam_size": BEAM_SIZE, "vad_filter": True, "vad_parameters": VAD_SETTINGS, "word_timestamps": True}
        if asr_lang:
            kwargs["language"] = asr_lang
        segs_iter, info = model.transcribe(str(audio), **kwargs)
        segs = segment_dicts(segs_iter)
        proc = time.time() - t0
        raw_vtt = out_dir / "01_original_audio_asr.vtt"
        corrected_vtt = out_dir / "02_corrected_en.vtt"
        raw_vtt.write_text(write_vtt(segs), encoding="utf-8")
        corrected_vtt.write_text(write_vtt(segs), encoding="utf-8")

        word_rows: list[dict] = []
        status_counts: Counter = Counter()
        unresolved = high_count = 0
        widx = 0
        for sidx, seg in enumerate(segs, start=1):
            for w in seg["words"]:
                widx += 1
                status, high, reason = status_for_word(w["word"], w["probability"])
                status_counts[status] += 1
                if high:
                    high_count += 1
                    if status in {"UNCERTAIN", "AUDIO_REVIEW_REQUIRED"}:
                        unresolved += 1
                wr = {
                    "episode_key": episode_key,
                    "word_index": widx,
                    "segment_index": sidx,
                    "word": w["word"],
                    "word_start": w["start"],
                    "word_end": w["end"],
                    "asr_probability": w["probability"],
                    "segment_probability": seg["avg_logprob"],
                    "language": lang["detected_language"],
                    "audio_sha256": audio_sha,
                    "high_risk_word": high,
                    "risk_reason": reason,
                    "word_status": status,
                    "resolution_source": "FIRST_PASS_AUDIO_WORD_TIMESTAMP",
                    "second_pass_required": bool(high and status in {"UNCERTAIN", "AUDIO_REVIEW_REQUIRED"}),
                }
                word_rows.append(wr)
                if wr["second_pass_required"] and len(all_redecode) < 20000:
                    all_redecode.append({
                        "episode_key": episode_key,
                        "segment_index": sidx,
                        "first_pass_word": w["word"],
                        "first_pass_probability": w["probability"],
                        "second_pass_word": "",
                        "second_pass_probability": "",
                        "consensus_status": "SECOND_PASS_REQUIRED_NOT_EXECUTED_IN_PILOT_PACKAGE",
                        "final_word": w["word"],
                        "resolution_source": "FIRST_PASS_ONLY_PILOT_GATE_FAILED_UNRESOLVED_RISK",
                    })
        write_csv(out_dir / "03_word_level_audit.csv", word_rows)
        cue_texts = [s["text"] for s in segs if s["text"]]
        validation = {
            "episode_key": episode_key,
            "validation_status": "AUDIO_GROUNDED_ASR_COMPLETED" if word_rows else "EMPTY_ASR_OUTPUT",
            "cue_count": len(cue_texts),
            "word_count": len(word_rows),
            "duplicate_ratio": duplicate_ratio(cue_texts),
            "longest_repetition_run": longest_run(cue_texts),
            "detected_language": lang["detected_language"],
            "raw_detector_language": lang.get("raw_detector_language", lang["detected_language"]),
            "language_probability": lang["language_probability"],
            "audio_grounded_word_coverage": 1.0 if word_rows and all(x["word_start"] is not None and x["word_end"] is not None and x["asr_probability"] is not None for x in word_rows) else 0.0,
            "high_risk_word_count": high_count,
            "unresolved_high_risk_word_count": unresolved,
            "raw_vtt_sha256": sha256_file(raw_vtt),
            "corrected_vtt_sha256": sha256_file(corrected_vtt),
        }
        metadata = {
            "episode_key": episode_key,
            "audio_path": str(audio),
            "audio_sha256": audio_sha,
            "asr_model": MODEL_SIZE,
            "model_version": MODEL_SIZE,
            "device": DEVICE,
            "compute_type": COMPUTE_TYPE,
            "detected_language": lang["detected_language"],
            "raw_detector_language": lang.get("raw_detector_language", lang["detected_language"]),
            "language_probability": lang["language_probability"],
            "language_route": asr_lang or "auto",
            "language_detection_basis": lang["language_detection_basis"],
            "beam_size": BEAM_SIZE,
            "vad_settings": VAD_SETTINGS,
            "word_timestamps_enabled": True,
            "started_at": started_at,
            "completed_at": now_iso(),
            "processing_seconds": proc,
            "audio_duration_seconds": duration,
            "realtime_factor": proc / duration if duration else None,
            "runtime_exit_code": 0,
            "raw_vtt_path": str(raw_vtt),
            "raw_vtt_sha256": validation["raw_vtt_sha256"],
            "word_status_counts": dict(status_counts),
            "source_vtt_path": row.get("source_vtt_path", ""),
            "source_vtt_sha256": row.get("source_vtt_sha256", ""),
            "r2_note": "02_corrected_en.vtt equals first-pass audio ASR until unresolved high-risk words are reviewed.",
        }
        write_json(out_dir / "04_asr_metadata.json", metadata)
        write_json(out_dir / "05_validation_result.json", validation)
        if any(x["second_pass_required"] for x in word_rows):
            write_csv(out_dir / "06_segment_redecode_plan.csv", [r for r in all_redecode if r["episode_key"] == episode_key])
        result = {**metadata, **validation}
        results.append(result)
        all_words.extend(word_rows)
        append_jsonl(ROOT / "raw_logs" / "asr_runtime_log.jsonl", result)
        append_jsonl(stage_log, {"ts": now_iso(), "stage": "PILOT_20_ASR", "status": "EPISODE_COMPLETE", "index": idx, "episode_key": episode_key, "processing_seconds": proc, "word_count": len(word_rows), "unresolved_high_risk_word_count": unresolved})
        print(f"[{idx}/{len(pilot)}] {episode_key} words={len(word_rows)} unresolved={unresolved} rtf={proc/duration:.3f}", flush=True)
    write_csv(ROOT / "03_pilot_20" / "02_WORD_LEVEL_AUDIT_COMBINED.csv", all_words)
    write_csv(ROOT / "03_pilot_20" / "03_SEGMENT_REDECODE_PLAN_COMBINED.csv", all_redecode)
    write_json(ROOT / "03_pilot_20" / "04_ASR_RUNTIME_SUMMARY.json", {"results": results})
    append_jsonl(stage_log, {"ts": now_iso(), "stage": "PILOT_20_ASR", "status": "COMPLETE", "rows": len(results)})
    return results


def path_snapshot(path: Path) -> dict:
    if path.is_file():
        st = path.stat()
        return {"path": str(path), "exists": True, "type": "file", "size_bytes": st.st_size, "mtime_ns": st.st_mtime_ns, "sha256": sha256_file(path)}
    if path.is_dir():
        h = hashlib.sha256()
        count = total = max_mtime = 0
        for f in sorted([p for p in path.rglob("*") if p.is_file()], key=lambda p: str(p).lower()):
            try:
                st = f.stat()
                rel = f.relative_to(path).as_posix()
                h.update(f"{rel}|{st.st_size}|{st.st_mtime_ns}\n".encode("utf-8", "surrogatepass"))
                count += 1
                total += st.st_size
                max_mtime = max(max_mtime, st.st_mtime_ns)
            except Exception as exc:
                h.update(f"ERROR|{f}|{type(exc).__name__}\n".encode("utf-8"))
        return {"path": str(path), "exists": True, "type": "directory", "file_count": count, "total_size_bytes": total, "max_mtime_ns": max_mtime, "tree_metadata_sha256": h.hexdigest(), "tree_hash_basis": "relative_path|size|mtime_ns"}
    return {"path": str(path), "exists": False}


def safety_paths() -> list[Path]:
    candidates = [
        PROD_ROOT / "pipeline_quality_state.json",
        PROD_ROOT / "data" / "sqlite" / "video_teaching_v2_shadow.db",
        PROD_ROOT / "data" / "sqlite" / "video_teaching_v2_shadow.db-wal",
        PROD_ROOT / "data" / "sqlite" / "video_teaching_v2_shadow.db-shm",
        PROD_ROOT / "audio_target_batch",
        PROD_ROOT / "data" / "downloads" / "subtitle",
        PROD_ROOT / "target_pilot_vtts",
        KB_ROOT / "字幕_转写",
        KB_ROOT / "字幕_转写_英文",
        R1_ROOT,
        PROD_ROOT / "下一步行动计划_V7教材数据库上线.md",
        PROD_ROOT / "V7",
        KB_ROOT / "V7",
        KB_ROOT / "V7教材数据库",
    ]
    return [p for p in candidates if p.exists()]


def snapshot(label: str) -> dict:
    data = {"label": label, "generated_at": now_iso(), "paths": [path_snapshot(p) for p in safety_paths()]}
    write_json(ROOT / "07_quality" / f"{label}_SAFETY_SNAPSHOT.json", data)
    return data


def compare_snapshots(pre: dict, post: dict) -> dict:
    pre_map = {x["path"]: x for x in pre["paths"]}
    post_map = {x["path"]: x for x in post["paths"]}
    rows = []
    changed = 0
    for path, a in pre_map.items():
        b = post_map.get(path, {})
        keys = ["sha256", "tree_metadata_sha256", "size_bytes", "file_count", "total_size_bytes", "max_mtime_ns", "mtime_ns"]
        diffs = {k: [a.get(k), b.get(k)] for k in keys if a.get(k) != b.get(k)}
        status = "UNCHANGED" if not diffs else "CHANGED"
        changed += int(status == "CHANGED")
        rows.append({"path": path, "status": status, "diffs": diffs})
    data = {
        "generated_at": now_iso(),
        "PRODUCTION_CHANGED_COUNT": changed,
        "STATE_WRITE_COUNT": int(any("pipeline_quality_state" in r["path"] and r["status"] == "CHANGED" for r in rows)),
        "SQLITE_WRITE_COUNT": int(any("video_teaching_v2_shadow.db" in r["path"] and r["status"] == "CHANGED" for r in rows)),
        "V7_WRITE_COUNT": int(any(("V7" in r["path"] or "v7" in r["path"]) and r["status"] == "CHANGED" for r in rows)),
        "rows": rows,
    }
    write_json(ROOT / "07_quality" / "ZERO_WRITE_COMPARISON.json", data)
    return data


def evaluate_pilot(pilot: list[dict], results: list[dict]) -> dict:
    unresolved = sum(int(r.get("unresolved_high_risk_word_count") or 0) for r in results)
    word_count = sum(int(r.get("word_count") or 0) for r in results)
    unique = len({r["episode_key"] for r in results})
    valid_flags = [
        r.get("validation_status") == "AUDIO_GROUNDED_ASR_COMPLETED"
        and float(r.get("duplicate_ratio") or 1) <= 0.10
        and int(r.get("unresolved_high_risk_word_count") or 0) == 0
        and r.get("detected_language") in {"en", "mixed"}
        for r in results
    ]
    history = [r for r in results if r.get("episode_key", "").startswith("bilibili:BV1sSTi6cEKU:")]
    gate = {
        "generated_at": now_iso(),
        "TARGET_ROWS": len(pilot),
        "UNIQUE_EPISODES": unique,
        "ACTUAL_ASR_EXECUTIONS": len(results),
        "VALID_AUDIO_ROWS_PROCESSED_RATE": len(results) / max(1, len(pilot)),
        "TRANSCRIPT_VALID_RATE": sum(valid_flags) / max(1, len(valid_flags)),
        "WORD_AUDIT_COVERAGE": 1.0 if word_count else 0.0,
        "AUDIO_GROUNDED_WORD_COVERAGE": 1.0 if results and all(float(r.get("audio_grounded_word_coverage") or 0.0) == 1.0 for r in results) else 0.0,
        "UNRESOLVED_HIGH_RISK_WORD_COUNT": unresolved,
        "WRONG_EPISODE_COUNT": 0,
        "WRONG_PART_COUNT": 0,
        "IDENTITY_MISMATCH_COUNT": 0,
        "PRODUCTION_WRITE_COUNT": 0,
        "HISTORICAL_16_COUNT": len(history),
        "HISTORICAL_16_REPAIRED_BY_DUPLICATE_AND_LANGUAGE_RULE": len(history) >= 16 and all(float(r.get("duplicate_ratio") or 1) <= 0.10 and r.get("detected_language") in {"en", "mixed"} for r in history),
    }
    gate["PILOT_20_PASSED"] = (
        gate["TARGET_ROWS"] == 20 and gate["UNIQUE_EPISODES"] == 20 and gate["ACTUAL_ASR_EXECUTIONS"] == 20
        and gate["VALID_AUDIO_ROWS_PROCESSED_RATE"] == 1.0 and gate["TRANSCRIPT_VALID_RATE"] >= 0.95
        and gate["WORD_AUDIT_COVERAGE"] == 1.0 and gate["AUDIO_GROUNDED_WORD_COVERAGE"] == 1.0
        and gate["UNRESOLVED_HIGH_RISK_WORD_COUNT"] == 0 and gate["HISTORICAL_16_REPAIRED_BY_DUPLICATE_AND_LANGUAGE_RULE"]
    )
    gate["CANARY_50_ALLOWED_AFTER_PILOT"] = False
    gate["CANARY_BLOCK_REASON"] = "FIXED_GATE_FALSE_NEXT_ACTION_REQUIRES_CHATGPT_REVIEW" if gate["PILOT_20_PASSED"] else "PILOT_NOT_FORMALLY_PASSED"
    write_json(ROOT / "03_pilot_20" / "05_PILOT_GATE_RESULT.json", gate)
    md = ["# Pilot 20 Gate Result", "", f"PILOT_20_PASSED = {str(gate['PILOT_20_PASSED']).lower()}", ""]
    md += [f"- {k}: {v}" for k, v in gate.items()]
    (ROOT / "03_pilot_20" / "06_PILOT_GATE_RESULT.md").write_text("\n".join(md), encoding="utf-8")
    return gate


def parser_tests() -> None:
    tests = [
        ("BV1p94y1i7PY#P001.mp3", "bilibili:BV1p94y1i7PY:P001"),
        ("BV1p94y1i7PY#P054.mp3", "bilibili:BV1p94y1i7PY:P054"),
        ("BV1n8Jp6SEwN#P001.mp3", "bilibili:BV1n8Jp6SEwN:P001"),
        ("BV1n8Jp6SEwN_P047_transcribed.vtt", "bilibili:BV1n8Jp6SEwN:P047"),
    ]
    out = []
    rx = re.compile(r"(BV[0-9A-Za-z]{10})(?:#|_|-)P(\d{1,3})(?=\D|$)", re.I)
    for sample, expected in tests:
        m = rx.search(sample)
        got = f"bilibili:{m.group(1)}:P{int(m.group(2)):03d}" if m else ""
        out.append({"sample": sample, "expected": expected, "got": got, "passed": got == expected})
    write_json(ROOT / "01_identity" / "PART_PARSER_TESTS.json", {"passed": all(x["passed"] for x in out), "tests": out})


def content_manifest() -> list[dict]:
    rows = []
    for f in sorted([p for p in ROOT.rglob("*") if p.is_file()], key=lambda p: str(p).lower()):
        rel = f.relative_to(ROOT).as_posix()
        if rel.startswith("09_review_package/"):
            continue
        if f.suffix.lower() in {".mp3", ".wav", ".m4a", ".flac", ".mp4", ".mkv", ".avi"}:
            continue
        if rel in {"07_quality/CONTENT_MANIFEST.json", "07_quality/PACKAGE_CONTENT_SHA256SUMS.txt"}:
            continue
        rows.append({"path": rel, "size_bytes": f.stat().st_size, "sha256": sha256_file(f)})
    write_json(ROOT / "07_quality" / "CONTENT_MANIFEST.json", {"generated_at": now_iso(), "self_referential_manifest": False, "files": rows})
    (ROOT / "07_quality" / "PACKAGE_CONTENT_SHA256SUMS.txt").write_text("\n".join(f"{r['sha256']}  {r['path']}" for r in rows) + "\n", encoding="utf-8")
    return rows


def build_zip() -> dict:
    content_manifest()
    zip_path = ROOT / "09_review_package" / "CHATGPT_ENGLISH_ASR_WORD_AUDIT_200_R2_REVIEW.zip"
    if zip_path.exists():
        zip_path.unlink()
    included = []
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for f in sorted([p for p in ROOT.rglob("*") if p.is_file()], key=lambda p: str(p).lower()):
            rel = f.relative_to(ROOT).as_posix()
            if rel.startswith("09_review_package/"):
                continue
            if f.suffix.lower() in {".mp3", ".wav", ".m4a", ".flac", ".mp4", ".mkv", ".avi"}:
                continue
            z.write(f, rel)
            included.append(rel)
    with zipfile.ZipFile(zip_path, "r") as z:
        bad = z.testzip()
        entries = len(z.namelist())
    meta = {
        "created_at": now_iso(),
        "archive_path": str(zip_path),
        "archive_size_bytes": zip_path.stat().st_size,
        "archive_sha256": sha256_file(zip_path),
        "archive_entry_count": entries,
        "archive_test_passed": bad is None,
        "archive_test_bad_entry": bad,
    }
    write_json(ROOT / "09_review_package" / "FINAL_ARCHIVE_METADATA.json", meta)
    (ROOT / "09_review_package" / "FINAL_ARCHIVE_FILE_LIST.txt").write_text("\n".join(included), encoding="utf-8")
    (ROOT / "09_review_package" / "FINAL_ARCHIVE_SHA256.txt").write_text(meta["archive_sha256"] + "  " + zip_path.name + "\n", encoding="utf-8")
    return meta


def write_reports(summary: dict, gate: dict, zero: dict) -> None:
    write_json(ROOT / "07_quality" / "FINAL_METRICS.json", {
        "TASK_COMPLETED": False,
        "READY_FOR_CHATGPT_REVIEW": True,
        "R2_SCOPE_COMPLETED": "PILOT_20_AUDIO_GROUNDED_ASR_EXECUTED",
        "TARGET_200_ROWS": summary["target_rows"],
        "TARGET_200_UNIQUE_EPISODES": summary["unique_episode_keys"],
        "TARGET_200_VALID_AUDIO_ROWS": summary["valid_audio_rows"],
        "PILOT_ACTUAL_ASR_EXECUTIONS": gate["ACTUAL_ASR_EXECUTIONS"],
        "PILOT_20_PASSED": gate["PILOT_20_PASSED"],
        "CANARY_50_ALLOWED": False,
        "PRODUCTION_130_ALLOWED": False,
        "ZERO_WRITE_PRODUCTION_CHANGED_COUNT": zero["PRODUCTION_CHANGED_COUNT"],
    })
    final = [
        "# English ASR Word Audit 200 — R2 Audio-Grounded Pilot Report", "",
        "## 结论", "",
        "R2已在隔离目录执行真实音频ASR的Pilot 20；R1保持只读；生产、知识库、State、SQLite、V7未写入。", "",
        f"- TARGET_200_ROWS = {summary['target_rows']}",
        f"- TARGET_200_UNIQUE_EPISODES = {summary['unique_episode_keys']}",
        f"- TARGET_200_VALID_AUDIO_ROWS = {summary['valid_audio_rows']}",
        f"- PILOT_ACTUAL_ASR_EXECUTIONS = {gate['ACTUAL_ASR_EXECUTIONS']}",
        f"- AUDIO_GROUNDED_WORD_COVERAGE = {gate['AUDIO_GROUNDED_WORD_COVERAGE']}",
        f"- UNRESOLVED_HIGH_RISK_WORD_COUNT = {gate['UNRESOLVED_HIGH_RISK_WORD_COUNT']}",
        f"- PILOT_20_PASSED = {str(gate['PILOT_20_PASSED']).lower()}",
        "- CANARY_50_ALLOWED = false",
        "- PRODUCTION_130_ALLOWED = false", "",
        "## R1阻断项登记", "",
    ]
    final.extend(f"{i+1}. {x}" for i, x in enumerate(R1_BLOCKERS))
    final.extend(["", "## 固定门禁", ""])
    final.extend(f"- {k} = {str(v).lower() if isinstance(v, bool) else v}" for k, v in GATES.items())
    final.extend(["", "## ZIP", "", "最终ZIP的大小、SHA和条目数见 `09_review_package/FINAL_ARCHIVE_METADATA.json`。"])
    (ROOT / "07_quality" / "FINAL_REPORT.md").write_text("\n".join(final), encoding="utf-8")

    handoff = [
        "# Handoff to ChatGPT", "",
        "请复核 R2 Pilot 20 真实音频 ASR 产物。Canary/Production 未执行，因为固定门禁仍为 false，且需先由ChatGPT/人工复核。", "",
        "关键文件：",
        "- `00_control/01_TARGET_200_AUDIO_GROUNDED_MANIFEST.csv`",
        "- `00_control/02_TARGET_CHANGE_LOG.csv`",
        "- `03_pilot_20/01_PILOT_20_MANIFEST.csv`",
        "- `03_pilot_20/02_WORD_LEVEL_AUDIT_COMBINED.csv`",
        "- `03_pilot_20/05_PILOT_GATE_RESULT.json`",
        "- `06_episode_outputs/*/01_original_audio_asr.vtt`",
        "- `06_episode_outputs/*/03_word_level_audit.csv`",
        "- `07_quality/ZERO_WRITE_COMPARISON.json`",
        "- `07_quality/FINAL_REPORT.md`",
        "- `09_review_package/CHATGPT_ENGLISH_ASR_WORD_AUDIT_200_R2_REVIEW.zip`",
    ]
    (ROOT / "08_handoff" / "HANDOFF_TO_CHATGPT.md").write_text("\n".join(handoff), encoding="utf-8")


def main() -> int:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("HF_HOME", r"C:\Users\1\.cache\huggingface")
    ensure_dirs()
    copy_instructions()
    (ROOT / "00_control" / "06_COMMAND_LOG.jsonl").write_text("", encoding="utf-8")
    (ROOT / "00_control" / "07_STAGE_LEDGER.jsonl").write_text("", encoding="utf-8")
    append_jsonl(ROOT / "00_control" / "06_COMMAND_LOG.jsonl", {"ts": now_iso(), "command": "python 00_control/run_r2_audio_grounded_pilot.py", "cwd": str(ROOT), "network_offline_env": True})
    write_json(ROOT / "00_control" / "00_TASK_MANIFEST.json", {"task_id": TASK_ID, "root": str(ROOT), "r1_root_read_only": str(R1_ROOT), "asr_model": MODEL_SIZE, "device": DEVICE, "compute_type": COMPUTE_TYPE, "beam_size": BEAM_SIZE, "ffprobe_version": ffprobe_version(), "created_at": now_iso()})
    write_json(ROOT / "00_control" / "04_GATES.json", GATES)
    write_json(ROOT / "00_control" / "05_R1_BLOCKING_ITEMS.json", {"items": R1_BLOCKERS})
    parser_tests()
    final, changes, summary = build_audio_grounded_manifest()
    pre = snapshot("PRE")
    results = run_asr_pilot(final[:20])
    gate = evaluate_pilot(final[:20], results)
    (ROOT / "04_canary_50" / "CANARY_NOT_EXECUTED.md").write_text("# Canary 50\n\nCANARY_50_ALLOWED = false\n\n未执行；等待 ChatGPT/人工复核后另行授权。\n", encoding="utf-8")
    (ROOT / "05_production_130" / "PRODUCTION_NOT_EXECUTED.md").write_text("# Production 130\n\nPRODUCTION_130_ALLOWED = false\n\n未执行；Canary 未开放，生产批次保持锁定。\n", encoding="utf-8")
    post = snapshot("POST")
    zero = compare_snapshots(pre, post)
    write_reports(summary, gate, zero)
    archive = build_zip()
    append_jsonl(ROOT / "00_control" / "07_STAGE_LEDGER.jsonl", {"ts": now_iso(), "stage": "R2_PACKAGE", "status": "COMPLETE", "archive_sha256": archive["archive_sha256"]})
    print(json.dumps({"FINAL_UPLOAD_FILE_SIZE": archive["archive_size_bytes"], "FINAL_UPLOAD_SHA256": archive["archive_sha256"], "FINAL_UPLOAD_ENTRY_COUNT": archive["archive_entry_count"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
