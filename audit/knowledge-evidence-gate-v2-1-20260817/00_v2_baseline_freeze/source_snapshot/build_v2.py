from __future__ import annotations
import csv, hashlib, json, os, re
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime, timezone

V1 = Path(r"D:\AI-Agent-Workspaces\GitHub\video-teaching-knowledge-pipeline\audit\knowledge-evidence-gate-pilot-20260817")
OUT = Path(r"D:\AI-Agent-Workspaces\GitHub\video-teaching-knowledge-pipeline\audit\knowledge-evidence-gate-pilot-v2-20260817")
KB = Path(r"D:\司法视频图像处理知识库\12大数学体系_课程资源")
MEDIA = KB / "字幕_转写"
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "audio_clips").mkdir(exist_ok=True)
(OUT / "pipeline").mkdir(exist_ok=True)

def sha256_file(p: Path) -> str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024), b""): h.update(b)
    return h.hexdigest()

def write_json(name, obj):
    (OUT/name).write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

def write_csv(name, rows, fields):
    with (OUT/name).open("w", encoding="utf-8-sig", newline="") as f:
        w=csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows: w.writerow({k:r.get(k,"") for k in fields})

TIMING_RE = re.compile(r"^(\d{2}:\d{2}:\d{2}[.,]\d{3})\s+-->\s+(\d{2}:\d{2}:\d{2}[.,]\d{3})")
def parse_vtt(path: Path):
    try: lines=path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except Exception: return []
    cues=[]; i=0
    while i<len(lines):
        m=TIMING_RE.match(lines[i].strip())
        if not m: i+=1; continue
        start,end=m.groups(); i+=1; body=[]
        while i<len(lines) and lines[i].strip() and not TIMING_RE.match(lines[i].strip()):
            body.append(lines[i].strip()); i+=1
        cues.append({"cue_index":len(cues)+1,"start":start,"end":end,"text":" ".join(body).strip()})
    return cues

def language(text):
    return "mixed" if re.search(r"[\u4e00-\u9fff]", text) else "en"

def critical_type(text):
    t=text.lower()
    if re.search(r"(?:[=∫∑√^]|\b(?:equals?|equal to|derivative|integral|formula|equation|summation|convolution|fourier transform)\b)", t):
        return "FORMULA"
    if re.search(r"(?:\b\d+(?:\.\d+)?\b|\b(?:one|two|three|four|five|ten|hundred|half|twice|percent|probability)\b)", t):
        return "NUMBER"
    if re.search(r"\b(?:define|defined|definition|means|is called|we call|refers to)\b", t):
        return "DEFINITION"
    if re.search(r"\b(?:if|when|unless|provided that|assuming|given that|as long as)\b", t):
        return "CONDITION"
    if re.search(r"\b(?:therefore|thus|hence|in conclusion|we conclude|it follows)\b", t):
        return "CONCLUSION"
    if re.search(r"\b(?:theorem|lemma|proof|orthogonal|basis|variance|expectation|random variable|distribution|vector space|coefficient|frequency|spectrum|arc length)\b", t):
        return "TERM"
    return ""

def cue_by_word(cues, word_index):
    n=0
    for c in cues:
        words=re.findall(r"\S+", c["text"])
        if n < word_index <= n+len(words): return c
        n += len(words)
    return cues[0] if cues else {"cue_index":"","start":"","end":"","text":""}

# V1 immutable snapshot / re-verification
v1_files=[]
for p in sorted(V1.rglob("*")):
    if p.is_file():
        rel=str(p.relative_to(V1)); st=p.stat()
        v1_files.append({"relative_path":rel,"size_bytes":st.st_size,"mtime_ns":st.st_mtime_ns,"sha256":sha256_file(p)})
expected=52
write_csv("02_V1_IMMUTABILITY_MANIFEST.csv", v1_files + [{
    "relative_path":"__SUMMARY__","size_bytes":"","mtime_ns":"","sha256":"",
    "expected_file_count":expected,"actual_file_count":len(v1_files),"status":"CONFLICT" if len(v1_files)!=expected else "VERIFIED_LOCAL"
}], ["relative_path","size_bytes","mtime_ns","sha256","expected_file_count","actual_file_count","status"])
write_json("02_V1_IMMUTABILITY_MANIFEST.json", {
    "v1_root":str(V1),"expected_file_count":expected,"actual_file_count":len(v1_files),
    "status":"CONFLICT" if len(v1_files)!=expected else "VERIFIED_LOCAL","files":v1_files
})

def load_csv(p):
    with p.open(encoding="utf-8-sig", newline="") as f: return list(csv.DictReader(f))
ledger=load_csv(V1/"D01_CURRENT_EPISODE_EVIDENCE_LEDGER.csv")
ledger_by_key={r["canonical_episode_key"]:r for r in ledger}
unresolved=load_csv(V1/"I03_UNRESOLVED_AUDIO_CASES.csv")
pairs=load_csv(V1/"H02_PILOT_SAMPLE_MANIFEST.csv")
i01=[]
with (V1/"I01_AB_TRANSCRIPT_PAIRS.jsonl").open(encoding="utf-8-sig") as f:
    for line in f:
        if line.strip(): i01.append(json.loads(line))
pair_by_id={x["pair_id"]:x for x in i01}
v1_counts=json.loads((V1/"D03_LEDGER_STATE_COUNTS.json").read_text(encoding="utf-8-sig"))
m01=json.loads((V1/"M01_GATE_METRICS.json").read_text(encoding="utf-8-sig"))
historical={"TOTAL_WORD_ROWS":49829,"INITIAL_HIGH_RISK_WORDS":8936,"R2_RESOLVED":3901,"SECOND_PASS_REQUIRED_WORDS":5035,"MASKED_UNCLEAR":1760}
v1_reverify={"ledger_rows":len(ledger),"ledger_unique_keys":len(ledger_by_key),"ledger_state_counts":v1_counts.get("state_counts",{}),"v1_sample_rows":len(pairs),"v1_unresolved_rows":len(unresolved),"v1_gate_metrics":m01,"v1_historical_contract":historical}

# Current audio-bound pool
mp3_re=re.compile(r"^(BV[^_]+)_P(\d{1,3})\.mp3$", re.I)
pool=[]; all_audio=[]
for mp3 in sorted(MEDIA.glob("*.mp3")):
    m=mp3_re.match(mp3.name)
    if not m: continue
    bvid=m.group(1); part=int(m.group(2)); key=f"bilibili:{bvid}:P{part:03d}"; all_audio.append(mp3)
    row=ledger_by_key.get(key)
    if not row: continue
    vtt=MEDIA/f"{bvid}_P{part:03d}_transcribed.vtt"
    if not vtt.exists():
        cands=sorted(MEDIA.glob(f"{bvid}_P{part:03d}*.vtt")); vtt=cands[0] if cands else None
    if not vtt or not vtt.exists(): continue
    pool.append({"episode_key":key,"bvid":bvid,"part":f"P{part:03d}","module":row.get("module",""),"collection_id":row.get("collection_id",""),"episode_title":row.get("episode_title",""),"audio_path":str(mp3),"audio_sha256":sha256_file(mp3),"audio_size_bytes":mp3.stat().st_size,"vtt_path":str(vtt),"vtt_sha256":sha256_file(vtt),"audio_source_bucket":"CURRENT_KB_MEDIA","source_binding":"MATCHED_FILENAME_AND_SAME_DIRECTORY_VTT"})
pool_mod=Counter(x["module"] for x in pool); modules=sorted({r.get("module","") for r in ledger})
module_coverage=[{"module":m,"current_audio_bound_count":pool_mod.get(m,0),"status":"REPRESENTED" if pool_mod.get(m,0) else "MODULE_NOT_REPRESENTED","reason":"" if pool_mod.get(m,0) else "No current KB MP3+same-directory VTT binding found in targeted local evidence"} for m in modules]
write_csv("09_CURRENT_AUDIO_BOUND_SAMPLE_POOL.csv",pool, list(pool[0].keys()) if pool else ["episode_key"])
write_json("09_CURRENT_AUDIO_BOUND_SAMPLE_POOL.json",{"scan_root":str(MEDIA),"mp3_files_matching_pattern":len(all_audio),"current_universe_audio_bound_rows":len(pool),"module_counts":dict(pool_mod),"modules":module_coverage,"verified_local_note":"Pool is limited to current local MP3 plus same-directory VTT bindings; it is not the full corpus."})

# Sampling
by_mod=defaultdict(list)
for x in pool:
    for c in __import__("builtins").globals()["parse_vtt"](Path(x["vtt_path"])):
        typ=critical_type(c["text"])
        if not typ: continue
        score=len(c["text"])+100 if typ in {"FORMULA","DEFINITION","CONDITION","CONCLUSION"} else len(c["text"])
        by_mod[(x["module"],typ)].append((score,x,c))
for k in by_mod: by_mod[k].sort(key=lambda z:(-z[0],z[1]["episode_key"],z[2]["cue_index"]))
unc=[]; used_eps=set(); type_order=["FORMULA","NUMBER","DEFINITION","CONDITION","CONCLUSION","TERM"]; represented=sorted(pool_mod)
for typ in type_order:
    for mod in represented:
        if len(unc)>=18: break
        pick=next((z for z in by_mod.get((mod,typ),[]) if z[1]["episode_key"] not in used_eps),None)
        if pick:
            _,x,c=pick; unc.append((x,c,typ,"targeted critical knowledge-type coverage")); used_eps.add(x["episode_key"])
    if len(unc)>=18: break
if len(unc)<18:
    for typ in type_order:
        for mod in represented:
            for _,x,c in by_mod.get((mod,typ),[]):
                if len(unc)>=18: break
                if x["episode_key"] not in used_eps:
                    unc.append((x,c,typ,"available-strata fallback")); used_eps.add(x["episode_key"])
            if len(unc)>=18: break
        if len(unc)>=18: break
controls=[]
for mod in represented:
    choices=[]
    for x in pool:
        if x["module"]!=mod or x["episode_key"] in used_eps: continue
        for c in parse_vtt(Path(x["vtt_path"])):
            t=c["text"]
            if len(t)>=35 and not critical_type(t) and not re.fullmatch(r"(?i)\s*(okay|ok|so|well|right|yeah|yes|no|and|but)[,.!?\\s]*",t):
                choices.append((len(t),x,c))
    if choices:
        _,x,c=max(choices,key=lambda z:z[0]); controls.append((x,c,"CONTROL","clean control: no heuristic critical marker")); used_eps.add(x["episode_key"])
    if len(controls)>=6: break
samples=[]
for i,(x,c,typ,basis) in enumerate(unc,1):
    samples.append({"sample_id":f"V2U{i:03d}","sample_kind":"UNCERTAINTY","episode_key":x["episode_key"],"module":x["module"],"collection_id":x["collection_id"],"risk_type":typ,"knowledge_type":typ,"language":language(c["text"]),"cue_index":c["cue_index"],"cue_start":c["start"],"cue_end":c["end"],"cue_text":c["text"],"audio_path":x["audio_path"],"audio_sha256":x["audio_sha256"],"vtt_path":x["vtt_path"],"vtt_sha256":x["vtt_sha256"],"audio_source_bucket":x["audio_source_bucket"],"selection_basis":basis})
for i,(x,c,typ,basis) in enumerate(controls,1):
    samples.append({"sample_id":f"V2C{i:03d}","sample_kind":"CLEAN_CONTROL","episode_key":x["episode_key"],"module":x["module"],"collection_id":x["collection_id"],"risk_type":"CLEAN_CONTROL","knowledge_type":"TERM_OR_STATEMENT","language":language(c["text"]),"cue_index":c["cue_index"],"cue_start":c["start"],"cue_end":c["end"],"cue_text":c["text"],"audio_path":x["audio_path"],"audio_sha256":x["audio_sha256"],"vtt_path":x["vtt_path"],"vtt_sha256":x["vtt_sha256"],"audio_source_bucket":x["audio_source_bucket"],"selection_basis":basis})
fields=list(samples[0].keys()) if samples else ["sample_id"]
write_csv("10_V2_SAMPLING_FRAME.csv",samples,fields); write_csv("11_V2_SAMPLE_MANIFEST.csv",samples,fields)
coverage={"sample_total":len(samples),"uncertainty_count":sum(x["sample_kind"]=="UNCERTAINTY" for x in samples),"clean_control_count":sum(x["sample_kind"]=="CLEAN_CONTROL" for x in samples),"n_by_module":dict(Counter(x["module"] for x in samples)),"n_by_collection":dict(Counter(x["collection_id"] for x in samples)),"n_by_risk_type":dict(Counter(x["risk_type"] for x in samples)),"n_by_language":dict(Counter(x["language"] for x in samples)),"n_by_knowledge_type":dict(Counter(x["knowledge_type"] for x in samples)),"represented_modules":sorted({x["module"] for x in samples}),"not_represented_modules":[m for m in modules if m not in {x["module"] for x in samples}],"sample_contract":"18 targeted uncertainty/critical cues plus up to 6 clean controls, across all modules with current local audio+VTT bindings; engineering representative sample, not full-corpus proof."}
write_json("10_V2_SAMPLING_FRAME.json",coverage)
(OUT/"12_V2_SAMPLING_COVERAGE.md").write_text("# V2 Sampling Coverage\n\n"+f"- Current local audio-bound pool: {len(pool)} rows; source root: {MEDIA}.\n"+f"- V2 sample: {len(samples)} rows = {coverage['uncertainty_count']} uncertainty/critical + {coverage['clean_control_count']} controls.\n"+f"- Modules represented: {', '.join(coverage['represented_modules']) or 'none'}.\n"+f"- Modules not represented: {', '.join(coverage['not_represented_modules']) or 'none'}; no binding was fabricated.\n\n## Counts\n\n"+json.dumps(coverage,ensure_ascii=False,indent=2)+"\n\nThe sample contract is explicit and reproducible; it does not establish a full-corpus error rate.\n",encoding="utf-8")

# 10 unresolved root cause
root_rows=[]
for u in unresolved:
    pid=u["pair_id"]; ep=u["episode_key"]; old=pair_by_id.get(pid,{}); lrow=ledger_by_key.get(ep,{})
    avp=Path(old.get("A_original_transcript","")); cues=parse_vtt(avp) if avp.exists() else []; wi=int(u.get("word_index") or 0); cue=cue_by_word(cues,wi)
    ow=old.get("first_pass_word","").strip(); filler=bool(re.fullmatch(r"(?i)(okay|ok|so|well|now|and|but|in|right|yeah|yes)[,.!?]*",ow))
    root_rows.append({"pair_id":pid,"canonical_episode_key":ep,"module":lrow.get("module","10_傅里叶分析"),"collection":lrow.get("collection_id",""),"risk_type":u.get("reason",""),"word_index":u.get("word_index",""),"segment_index":old.get("segment_index",""),"word_start":old.get("word_start",""),"word_end":old.get("word_end",""),"original_word":ow,"original_context":cue.get("text",""),"audio_path":u.get("audio_path",""),"audio_sha256":u.get("audio_sha256",""),"short_window_result":"CURRENT_AUDIO_SOURCE_MISSING","medium_window_result":"CURRENT_AUDIO_SOURCE_MISSING","long_window_result":"CURRENT_AUDIO_SOURCE_MISSING","speech_present":"UNKNOWN","speech_quality":"UNKNOWN","timestamp_alignment_quality":"UNVERIFIABLE_CURRENT_AUDIO_MISSING","lexical_importance":"NONCRITICAL_CANDIDATE" if filler else "UNKNOWN","knowledge_type":"NONE_CANDIDATE" if filler else "UNKNOWN","knowledge_impact_candidate":"NO_KNOWLEDGE_IMPACT_CANDIDATE" if filler else "POSSIBLE_KNOWLEDGE_IMPACT","root_cause":"UNKNOWN","root_cause_detail":"CURRENT_AUDIO_SOURCE_MISSING","evidence_status":"CONFLICT: historical path/hash exists in V1 but current E and D audio roots are absent; no current byte evidence","final_audio_state":"AUDIO_UNRESOLVED","human_review_required":"true"})
rf=list(root_rows[0].keys()) if root_rows else ["pair_id"]; write_csv("04_UNRESOLVED_ROOT_CAUSE.csv",root_rows,rf)
(OUT/"05_UNRESOLVED_ROOT_CAUSE_REPORT.md").write_text("# 10 Unresolved Audio Cases — V2 Root Cause Report\n\nAll 10 cases were re-read from V1 I03_UNRESOLVED_AUDIO_CASES.csv. The historical E-root audio paths and hashes remain in the V1 package, but the current E root is absent and the current D audio target root is absent. Therefore current local acoustic windows cannot be created. This is recorded as root_cause=UNKNOWN with root_cause_detail=CURRENT_AUDIO_SOURCE_MISSING, not as an inferred noise/model cause.\n\n"+f"- Cases: {len(root_rows)}\n- Current audio window evidence available: 0/10\n- AUDIO_UNRESOLVED: {len(root_rows)}/10\n- Human review required: {len(root_rows)}/10\n- Filler-like target candidates: {sum(r['lexical_importance']=='NONCRITICAL_CANDIDATE' for r in root_rows)} (candidate only; not audio-confirmed)\n\nThe missing-source condition is not used to declare an acoustic or knowledge result. A future run with a verified current audio binding must adjudicate these exact keys and timestamps.\n",encoding="utf-8")
write_csv("06_AUDIO_WINDOW_ADJUDICATION.csv",root_rows,["pair_id","canonical_episode_key","short_window_result","medium_window_result","long_window_result","speech_present","speech_quality","timestamp_alignment_quality","final_audio_state","human_review_required"])
write_csv("07_AUDIO_METHOD_COMPARISON.csv",[{"pair_id":r["pair_id"],"episode_key":r["canonical_episode_key"],"method":"LOCAL_CURRENT_SOURCE_LOOKUP","model_version":"NOT_RUN_CURRENT_AUDIO_MISSING","output":"CURRENT_AUDIO_SOURCE_MISSING","agreement":"NOT_AVAILABLE","source_hash":r["audio_sha256"],"evidence_status":"UNPROVEN"} for r in root_rows],["pair_id","episode_key","method","model_version","output","agreement","source_hash","evidence_status"])
(OUT/"08_UNCERTAINTY_TAXONOMY_V2.md").write_text("# Uncertainty Taxonomy V2\n\nTwo independent axes are retained:\n\n1. Audio state: AUDIO_RECOVERABLE, AUDIO_PARTIAL, AUDIO_UNRECOVERABLE; operational AUDIO_UNRESOLVED is used where evidence is missing.\n2. Knowledge impact: NO_KNOWLEDGE_IMPACT, POSSIBLE_KNOWLEDGE_IMPACT, CRITICAL_KNOWLEDGE_IMPACT.\n\nCritical knowledge types: TERM, NUMBER, FORMULA, SYMBOL, DEFINITION, CONDITION, CONCLUSION, DERIVATION. An audio-unresolved filler candidate is not automatically accepted as harmless; only cue/context plus identical deterministic extraction can make it a non-critical candidate, while missing current audio remains unresolved and human-reviewable.\n",encoding="utf-8")

manifest={"stage_id":"KNOWLEDGE-EVIDENCE-GATE-PILOT-V2-20260817","created_at_utc":datetime.now(timezone.utc).isoformat(),"v1_root":str(V1),"v2_root":str(OUT),"knowledge_source_root":str(KB),"v1_immutable_status":"CONFLICT" if len(v1_files)!=expected else "VERIFIED_LOCAL","v1_file_count_actual":len(v1_files),"v1_file_count_claimed_by_task":expected,"v1_reverification":v1_reverify,"current_audio_pool_rows":len(pool),"current_audio_pool_module_counts":dict(pool_mod),"v2_sample_contract":coverage,"safety":{"production_write_count":0,"state_write_count":0,"sqlite_write_count":0,"v7_write_count":0,"knowledge_base_write_count":0,"network_download_count":0,"source_roots_read_only":True,"v1_write_count":0},"evidence_labels":["VERIFIED_LOCAL","CONFLICT","SUPERSEDED","INFERENCE","UNPROVEN","CROSS_VERIFIED","VERIFIED_EXTERNAL"],"notes":["Historical report values were re-read, not accepted as current facts.","V2 output is isolated; V1 was not modified.","Current audio pool is limited to existing local KB media bindings."]}
write_json("00_STAGE_MANIFEST.json",manifest)
(OUT/"01_EXECUTIVE_SUMMARY.md").write_text("# Knowledge Evidence Gate Pilot V2 — Executive Summary\n\n"+f"- V1 package re-read: {len(v1_files)} files; task stated 52; status {'CONFLICT' if len(v1_files)!=expected else 'VERIFIED_LOCAL'}.\n"+f"- V1 unresolved cases: {len(unresolved)}; all individually retained.\n"+f"- Current audio-bound pool: {len(pool)} MP3+same-directory VTT bindings matched to the 3649-key ledger.\n"+f"- V2 sample: {len(samples)} rows ({coverage['uncertainty_count']} targeted critical/uncertainty + {coverage['clean_control_count']} controls).\n- No current audio is claimed for the ten historical unresolved cases; their acoustic state remains unresolved.\n- Gate result is produced only after the current sample audio runner and A/B extraction files are completed.\n\nThis package separates local evidence, historical claims, inference, conflict, and unproven items. It does not authorize full-corpus reconstruction.\n",encoding="utf-8")
print(json.dumps({"v1_files":len(v1_files),"unresolved":len(unresolved),"pool":len(pool),"sample":len(samples),"coverage":coverage},ensure_ascii=False,indent=2))

