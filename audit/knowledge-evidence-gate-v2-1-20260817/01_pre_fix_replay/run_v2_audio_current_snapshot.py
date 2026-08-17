from __future__ import annotations
import csv, hashlib, json, os, re, subprocess, sys, time
from pathlib import Path
from datetime import datetime, timezone

OUT=Path(r"D:\AI-Agent-Workspaces\GitHub\video-teaching-knowledge-pipeline\audit\knowledge-evidence-gate-v2-1-20260817\01_pre_fix_replay")
MAN=OUT/"11_V2_SAMPLE_MANIFEST.csv"
CLIPS=OUT/"audio_clips"; CLIPS.mkdir(exist_ok=True)
RESULT=OUT/"13_V2_AUDIO_ADJUDICATION.jsonl"
FFMPEG=Path(r"D:\AI-Env\ffmpeg\bin\ffmpeg.exe")
FFPROBE=Path(r"D:\AI-Env\ffmpeg\bin\ffprobe.exe")
MODEL=Path(r"C:\Users\1\.cache\huggingface\hub\models--Systran--faster-whisper-large-v3\snapshots\edaa852ec7e145841d8ffdb056a99866b5f0a478")
os.environ["HF_HUB_OFFLINE"]="1"; os.environ["TRANSFORMERS_OFFLINE"]="1"; os.environ["HF_HOME"]=r"C:\Users\1\.cache\huggingface"

def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()
def sec(s):
    a=s.replace(",",".").split(":"); return int(a[0])*3600+int(a[1])*60+float(a[2])
def run_cmd(args):
    return subprocess.run([str(x) for x in args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding="utf-8",errors="replace",shell=False)
def duration(p):
    r=run_cmd([FFPROBE,"-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",p])
    try:return float(r.stdout.strip()),r.returncode,""
    except:return None,r.returncode,(r.stderr.strip()[-500:] if r.stderr else "AUDIO_DURATION_UNAVAILABLE")
def clip(src,start,end,dst):
    r=run_cmd([FFMPEG,"-hide_banner","-loglevel","error","-y","-ss",f"{start:.3f}","-to",f"{end:.3f}","-i",src,"-vn","-ac","1","-ar","16000","-f","wav",dst])
    return r.returncode,(r.stderr.strip()[-1000:] if r.stderr else "")
def load_existing():
    out={}
    if RESULT.exists():
        for l in RESULT.open(encoding="utf-8"):
            try:
                x=json.loads(l);out[x["sample_id"]]=x
            except: pass
    return out
rows=list(csv.DictReader(MAN.open(encoding="utf-8-sig",newline="")))
existing=load_existing()
try:
    from faster_whisper import WhisperModel
except Exception as e:
    print(json.dumps({"status":"DEPENDENCY_MISSING","error":repr(e)})); raise
print(json.dumps({"event":"MODEL_LOAD_START","model":str(MODEL),"exists":MODEL.exists(),"rows":len(rows),"resumed":len(existing)},ensure_ascii=False),flush=True)
model=WhisperModel(str(MODEL),device="cpu",compute_type="int8",cpu_threads=4,num_workers=1)
print(json.dumps({"event":"MODEL_LOAD_DONE"}),flush=True)
for idx,row in enumerate(rows,1):
    sid=row["sample_id"]
    if sid in existing: continue
    src=Path(row["audio_path"])
    rec={"sample_id":sid,"sample_kind":row["sample_kind"],"episode_key":row["episode_key"],"module":row["module"],"risk_type":row["risk_type"],"knowledge_type":row["knowledge_type"],"cue_index":row["cue_index"],"cue_start":row["cue_start"],"cue_end":row["cue_end"],"audio_path":str(src),"audio_sha256_declared":row["audio_sha256"],"audio_sha256_observed":sha(src) if src.exists() else "","vtt_path":row["vtt_path"],"started_at_utc":datetime.now(timezone.utc).isoformat(),"method":"faster_whisper_local_clip","model":"faster-whisper-large-v3","model_path":str(MODEL),"parameters":{"device":"cpu","compute_type":"int8","beam_size":10,"condition_on_previous_text":False,"word_timestamps":True,"language":"auto","vad_filter":False,"offline_env":True},"status":"","audio_duration_seconds":None,"window_start_seconds":None,"window_end_seconds":None,"clip_path":"","clip_sha256":"","transcribed_text":"","word_count":0,"audio_state":"","error":""}
    if not src.exists():
        rec.update(status="AUDIO_SOURCE_MISSING",audio_state="AUDIO_UNRESOLVED",error="current audio file does not exist"); 
        with RESULT.open("a",encoding="utf-8") as f:f.write(json.dumps(rec,ensure_ascii=False)+"\n")
        continue
    d,rc,err=duration(src);rec["audio_duration_seconds"]=d
    if d is None:
        rec.update(status="AUDIO_DURATION_UNAVAILABLE",audio_state="AUDIO_UNRESOLVED",error=err)
        with RESULT.open("a",encoding="utf-8") as f:f.write(json.dumps(rec,ensure_ascii=False)+"\n")
        continue
    center_s=sec(row["cue_start"]);center_e=sec(row["cue_end"]); ws=max(0.0,center_s-3.0);we=min(d,center_e+3.0)
    if we-ws<4.0:
        mid=(ws+we)/2;ws=max(0,mid-2);we=min(d,mid+2)
    rec.update(window_start_seconds=round(ws,3),window_end_seconds=round(we,3))
    dst=CLIPS/f"{sid}__local.wav"; rec["clip_path"]=str(dst)
    crc,cerr=clip(src,ws,we,dst)
    if crc!=0 or not dst.exists():
        rec.update(status="CLIP_CREATE_ERROR",audio_state="AUDIO_UNRESOLVED",error=cerr)
        with RESULT.open("a",encoding="utf-8") as f:f.write(json.dumps(rec,ensure_ascii=False)+"\n")
        continue
    rec["clip_sha256"]=sha(dst)
    try:
        segs,info=model.transcribe(str(dst),language=None,beam_size=10,condition_on_previous_text=False,word_timestamps=True,vad_filter=False)
        text_parts=[];wc=0
        for s in segs:
            text_parts.append(s.text.strip())
            if s.words:wc+=len(s.words)
        text=" ".join(x for x in text_parts if x).strip()
        rec.update(status="ASR_OK",audio_state="AUDIO_RECOVERABLE" if text else "AUDIO_UNRESOLVED",transcribed_text=text,word_count=wc)
    except Exception as e:
        rec.update(status="ASR_ERROR",audio_state="AUDIO_UNRESOLVED",error=f"{type(e).__name__}:{e}")
    rec["finished_at_utc"]=datetime.now(timezone.utc).isoformat()
    with RESULT.open("a",encoding="utf-8") as f:f.write(json.dumps(rec,ensure_ascii=False)+"\n")
    print(json.dumps({"event":"SAMPLE_DONE","index":idx,"sample_id":sid,"status":rec["status"],"audio_state":rec["audio_state"],"text":rec["transcribed_text"][:120]},ensure_ascii=False),flush=True)
print(json.dumps({"event":"COMPLETE","result":str(RESULT),"count":len(rows)}),flush=True)

