from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent
V1 = ROOT.parent / "knowledge-evidence-gate-pilot-20260817"
CLIPS = ROOT / "audio_clips"
CLIPS.mkdir(exist_ok=True)
FFMPEG = Path(r"D:\AI-Env\ffmpeg\bin\ffmpeg.exe")
FFPROBE = Path(r"D:\AI-Env\ffmpeg\bin\ffprobe.exe")
MODEL = Path(r"C:\Users\1\.cache\huggingface\hub\models--Systran--faster-whisper-large-v3\snapshots\edaa852ec7e145841d8ffdb056a99866b5f0a478")


def rows(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def duration(path: str) -> float | None:
    p = subprocess.run([str(FFPROBE), "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", path], capture_output=True, text=True, timeout=30)
    try:
        return float(p.stdout.strip())
    except Exception:
        return None


def clip(src: str, start: float, end: float, out: Path) -> dict:
    out.parent.mkdir(parents=True, exist_ok=True)
    p = subprocess.run([str(FFMPEG), "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{start:.3f}", "-i", src, "-t", f"{max(0.1, end-start):.3f}", "-ac", "1", "-ar", "16000", str(out)], capture_output=True, text=True, timeout=120)
    return {"exit_code": p.returncode, "exists": out.is_file(), "stderr": p.stderr[-500:]}


def load_model():
    try:
        from faster_whisper import WhisperModel
        return WhisperModel(str(MODEL), device="cpu", compute_type="int8"), "faster-whisper-large-v3", "cpu/int8"
    except Exception as exc:
        return None, "NOT_AVAILABLE", repr(exc)


def transcribe(model, path: Path) -> dict:
    if model is None:
        return {"status": "NOT_AVAILABLE", "text": "", "error": "model_not_loaded"}
    try:
        segments, info = model.transcribe(str(path), language="en", beam_size=10, condition_on_previous_text=False, temperature=0.0, vad_filter=True, word_timestamps=True)
        out = []
        for s in segments:
            out.append({"start": s.start, "end": s.end, "text": s.text, "words": [{"word": w.word, "start": w.start, "end": w.end, "probability": w.probability} for w in (s.words or [])]})
        return {"status": "OK", "text": " ".join(x["text"].strip() for x in out).strip(), "segments": out, "detected_language": info.language, "language_probability": info.language_probability}
    except Exception as exc:
        return {"status": "ERROR", "text": "", "error": repr(exc)}


def main():
    unresolved = rows(V1 / "I03_UNRESOLVED_AUDIO_CASES.csv")
    samples = {r["sample_id"]: r for r in rows(V1 / "H01_PILOT_SAMPLING_FRAME.csv")}
    pair_rows = {r["pair_id"]: r for r in (json.loads(x) for x in (V1 / "I01_AB_TRANSCRIPT_PAIRS.jsonl").read_text(encoding="utf-8").splitlines())}
    model, model_name, model_runtime = load_model()
    out_rows = []
    method_rows = []
    raw_results = {}
    for u in unresolved:
        pid = u["pair_id"]; s = samples[pid]; pair = pair_rows[pid]
        src = s["audio_path"]
        d = duration(src) if src and Path(src).is_file() else None
        ws, we = float(s["word_start"]), float(s["word_end"])
        windows = {"LOCAL": (max(0.0, ws - 2.0), we + 2.0), "MEDIUM": (max(0.0, ws - 8.0), we + 8.0), "LONG": (max(0.0, ws - 20.0), we + 20.0)}
        if d is not None:
            windows = {k: (a, min(d, b)) for k, (a, b) in windows.items()}
        case = {"pair_id": pid, "canonical_episode_key": s["episode_key"], "audio_path": src, "audio_sha256": s["audio_sha256"], "source_duration_seconds": d, "model": model_name, "model_runtime": model_runtime}
        for label, (a, b) in windows.items():
            out = CLIPS / f"{pid}_{label.lower()}.wav"
            probe = clip(src, a, b, out) if src and Path(src).is_file() else {"exit_code": -1, "exists": False, "stderr": "missing_audio"}
            result = transcribe(model, out) if probe["exists"] else {"status": "NOT_AVAILABLE", "text": "", "error": "clip_not_created"}
            raw_results[f"{pid}:{label}"] = {"window_start": a, "window_end": b, "window_duration": b-a, "clip": str(out), "clip_sha256": hashlib.sha256(out.read_bytes()).hexdigest() if out.is_file() else "", "ffmpeg": probe, "result": result}
            case[f"{label.lower()}_window_result"] = result.get("text", "") if result.get("status") == "OK" else f"{result.get('status')}:{result.get('error','')}"
            method_rows.append({"pair_id": pid, "window_type": label, "window_start": f"{a:.3f}", "window_end": f"{b:.3f}", "duration_seconds": f"{b-a:.3f}", "audio_path": src, "audio_sha256": s["audio_sha256"], "clip_path": str(out), "clip_sha256": raw_results[f"{pid}:{label}"]["clip_sha256"], "method": "LOCAL_FASTER_WHISPER" if result.get("status") == "OK" else "NOT_AVAILABLE", "model": model_name, "model_runtime": model_runtime, "output": result.get("text", ""), "status": result.get("status", "")})
        results = [raw_results[f"{pid}:{x}"]["result"] for x in ("LOCAL", "MEDIUM", "LONG")]
        texts = [r.get("text", "").strip() for r in results if r.get("status") == "OK" and r.get("text", "").strip()]
        unique = {" ".join(t.lower().split()) for t in texts}
        speech_present = any(bool(t) for t in texts)
        if len(unique) == 1 and texts:
            final = "AUDIO_PARTIALLY_CONFIRMED" if len(texts) < 3 else "AUDIO_CONFIRMED"
        elif texts:
            final = "AUDIO_PARTIALLY_CONFIRMED"
        else:
            final = "AUDIO_UNRESOLVED"
        # Preserve unresolved status when no window output actually isolates the target word.
        target = s["original_word"].strip().lower().strip(",.!?;:")
        if final == "AUDIO_CONFIRMED" and target and not any(target in t.lower() for t in texts):
            final = "AUDIO_PARTIALLY_CONFIRMED"
        case.update({"speech_present": speech_present, "speech_quality": "MEASURED_BY_LOCAL_DECODE" if texts else "UNKNOWN", "timestamp_alignment_quality": "BOUND_TO_WORD_TIMESTAMP", "final_audio_state": final, "human_review_required": final != "AUDIO_CONFIRMED"})
        out_rows.append(case)
    (ROOT / "audio_review_raw.json").write_text(json.dumps(raw_results, ensure_ascii=False, indent=2), encoding="utf-8")
    fields = list(out_rows[0].keys()) if out_rows else []
    with (ROOT / "06_AUDIO_WINDOW_ADJUDICATION.csv").open("w", encoding="utf-8", newline="") as f:
        w=csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(out_rows)
    mfields=list(method_rows[0].keys()) if method_rows else []
    with (ROOT / "07_AUDIO_METHOD_COMPARISON.csv").open("w", encoding="utf-8", newline="") as f:
        w=csv.DictWriter(f, fieldnames=mfields); w.writeheader(); w.writerows(method_rows)
    print(json.dumps({"cases":len(out_rows),"model":model_name,"runtime":model_runtime,"final_states":{x:sum(r.get("final_audio_state")==x for r in out_rows) for x in ["AUDIO_CONFIRMED","AUDIO_PARTIALLY_CONFIRMED","AUDIO_UNRESOLVED"]}},ensure_ascii=False))


if __name__ == "__main__":
    main()
