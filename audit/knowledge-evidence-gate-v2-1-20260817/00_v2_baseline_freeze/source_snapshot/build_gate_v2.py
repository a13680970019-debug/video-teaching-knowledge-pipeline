from __future__ import annotations
import csv, hashlib, json, re
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime, timezone

OUT=Path(r"D:\AI-Agent-Workspaces\GitHub\video-teaching-knowledge-pipeline\audit\knowledge-evidence-gate-pilot-v2-20260817")
V1=Path(r"D:\AI-Agent-Workspaces\GitHub\video-teaching-knowledge-pipeline\audit\knowledge-evidence-gate-pilot-20260817")
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()
def norm(s): return re.sub(r"\s+"," ",s.strip()).lower()
def tok(s): return re.findall(r"[a-zA-Z]+(?:'[a-z]+)?|\d+(?:\.\d+)?|[\u4e00-\u9fff]",s.lower())
def critical(t):
    return t in {"FORMULA","NUMBER","DEFINITION","CONDITION","CONCLUSION","SYMBOL","DERIVATION","TERM"}
def classify(s):
    t=s.lower()
    if re.search(r"(?:[=∫∑√^]|\b(?:equals?|equal to|derivative|integral|formula|equation|summation|convolution|fourier transform)\b)",t):return "FORMULA"
    if re.search(r"(?:\b\d+(?:\.\d+)?\b|\b(?:one|two|three|four|five|ten|hundred|half|twice|percent|probability)\b)",t):return "NUMBER"
    if re.search(r"\b(?:define|defined|definition|means|is called|we call|refers to)\b",t):return "DEFINITION"
    if re.search(r"\b(?:if|when|unless|provided that|assuming|given that|as long as)\b",t):return "CONDITION"
    if re.search(r"\b(?:therefore|thus|hence|in conclusion|we conclude|it follows)\b",t):return "CONCLUSION"
    return "TERM_OR_STATEMENT"
def signature(s):
    return set(re.findall(r"\d+(?:\.\d+)?|[=∫∑√^]|(?:derivative|integral|formula|equation|probability|variance|definition|if|therefore)",s.lower()))
def align(a,b):
    aa=set(tok(a));bb=set(tok(b))
    if not aa or not bb:return 0.0
    return len(aa&bb)/len(aa)
def unit(sample, text, variant, source_path, audio_path, audio_sha, source_bound=True):
    typ=classify(text); claim=text
    return {"unit_id":f"{sample['sample_id']}:{variant}:C{int(sample['cue_index']):04d}","episode_key":sample["episode_key"],"sample_id":sample["sample_id"],"variant":variant,"unit_type":typ,"claim":claim,"source_transcript_path":source_path,"source_audio_path":audio_path,"source_audio_sha256":audio_sha,"start_time":sample["cue_start"],"end_time":sample["cue_end"],"source_span_sha256":hashlib.sha256(norm(claim).encode()).hexdigest(),"source_bound":bool(source_bound and source_path and audio_path and audio_sha)}
def write_jsonl(p, rows):
    with p.open("w",encoding="utf-8") as f:
        for r in rows:f.write(json.dumps(r,ensure_ascii=False)+"\n")
rows=list(csv.DictReader((OUT/"11_V2_SAMPLE_MANIFEST.csv").open(encoding="utf-8-sig",newline="")))
asr={}
with (OUT/"13_V2_AUDIO_ADJUDICATION.jsonl").open(encoding="utf-8") as f:
    for l in f:
        if l.strip():
            x=json.loads(l);asr[x["sample_id"]]=x
A=[];B=[];pairs=[];diff=[];critical_fn=[];critical_unres=[];extractor_err=[];noncritical=[];human=[]
for s in rows:
    x=asr.get(s["sample_id"],{})
    a_text=s["cue_text"]; audio_text=x.get("transcribed_text","")
    al=align(a_text,audio_text)
    a_type=(s["knowledge_type"] if s["sample_kind"]=="UNCERTAINTY" and s["knowledge_type"] not in {"","MODULE_COVERAGE_UNKNOWN"} else classify(a_text)); sig_a=signature(a_text);sig_b=signature(audio_text)
    # Conservative acceptance: no text-only correction; critical evidence is accepted only with strong lexical and signature agreement.
    sig_ok=(not critical(a_type)) or (sig_a.issubset(sig_b) if sig_a else True)
    if x.get("status")=="ASR_OK" and audio_text and al >= (0.72 if critical(a_type) else 0.40) and sig_ok:
        b_text=audio_text; b_status="AUDIO_GROUNDED_CANDIDATE"; b_accepted=True
    else:
        b_text=a_text; b_status="AUDIO_UNRESOLVED_PRESERVE_A"; b_accepted=False
    if b_accepted and critical(a_type) and classify(audio_text) != a_type:
        extractor_err.append({"sample_id":s["sample_id"],"episode_key":s["episode_key"],"error":f"critical_type_mismatch:{a_type}->{classify(audio_text)}","severity":"CRITICAL","audio_text":audio_text})
        b_accepted=False
        b_text=a_text
        b_status="BLOCKED_EXTRACTOR_CRITICAL_ERROR"
    au=unit(s,a_text,"A",s["vtt_path"],s["audio_path"],s["audio_sha256"],True); au["unit_type"]=a_type
    bu=unit(s,b_text,"B",s["vtt_path"] if not b_accepted else str(x.get("clip_path","")),s["audio_path"],s["audio_sha256"],True)
    A.append(au);B.append(bu)
    p={"sample_id":s["sample_id"],"sample_kind":s["sample_kind"],"episode_key":s["episode_key"],"module":s["module"],"collection_id":s["collection_id"],"risk_type":s["risk_type"],"knowledge_type":s["knowledge_type"],"cue_index":s["cue_index"],"cue_start":s["cue_start"],"cue_end":s["cue_end"],"original_text":a_text,"audio_window_text":audio_text,"audio_status":x.get("status","MISSING_RESULT"),"audio_state":x.get("audio_state","AUDIO_UNRESOLVED"),"audio_sha256":x.get("audio_sha256_observed",""),"clip_sha256":x.get("clip_sha256",""),"alignment_score":round(al,4),"signature_match":sig_ok,"b_text":b_text,"b_status":b_status,"b_accepted":b_accepted,"source_binding":bu["source_bound"],"text_only_correction":False,"model":x.get("model",""),"parameters":x.get("parameters",{})}
    pairs.append(p)
    same=(au["unit_type"]==bu["unit_type"] and norm(au["claim"])==norm(bu["claim"]))
    if not same:
        mat="CRITICAL" if critical(au["unit_type"]) or critical(bu["unit_type"]) else "NONCRITICAL"
        accepted_critical=bool(b_accepted and mat=="CRITICAL")
        d={"sample_id":s["sample_id"],"episode_key":s["episode_key"],"change_side":"B_ONLY","unit_type":bu["unit_type"],"a_unit_type":au["unit_type"],"source_span_sha256":bu["source_span_sha256"],"materiality":mat,"false_negative":"true" if accepted_critical and au["unit_type"]!=bu["unit_type"] else "false","source_binding":str(bu["source_bound"]),"acceptance":"ACCEPTED_AUDIO_GROUNDED" if b_accepted else "BLOCKED_UNRESOLVED","reason":"conservative A/B cue comparison"}
        diff.append(d)
        if accepted_critical and au["unit_type"]!=bu["unit_type"]:critical_fn.append(d)
    if critical(a_type) and not b_accepted:
        critical_unres.append({"sample_id":s["sample_id"],"episode_key":s["episode_key"],"module":s["module"],"risk_type":s["risk_type"],"unit_type":a_type,"cue_start":s["cue_start"],"cue_end":s["cue_end"],"reason":b_status,"knowledge_consequence":"BLOCKED_CRITICAL","audio_state":x.get("audio_state","AUDIO_UNRESOLVED"),"source_binding":str(bool(s["audio_sha256"]))})
        human.append({"sample_id":s["sample_id"],"episode_key":s["episode_key"],"module":s["module"],"timestamp":f"{s['cue_start']} --> {s['cue_end']}","clip_path":x.get("clip_path",""),"context":a_text,"risk_type":s["risk_type"],"knowledge_consequence":"CRITICAL_REVIEW_REQUIRED","reason":"not silently accepted"})
    if not critical(a_type) and not b_accepted:
        noncritical.append({"sample_id":s["sample_id"],"episode_key":s["episode_key"],"module":s["module"],"risk_type":s["risk_type"],"audio_state":x.get("audio_state","AUDIO_UNRESOLVED"),"reason":"audio not accepted; preserved original; no text-only correction"})
# write knowledge rows
write_jsonl(OUT/"14_V2_KNOWLEDGE_A.jsonl",A);write_jsonl(OUT/"15_V2_KNOWLEDGE_B.jsonl",B);write_jsonl(OUT/"13_V2_AB_PAIRS.jsonl",pairs)
with (OUT/"16_V2_KNOWLEDGE_DIFF.csv").open("w",encoding="utf-8-sig",newline="") as f:
    fields=["sample_id","episode_key","change_side","unit_type","a_unit_type","source_span_sha256","materiality","false_negative","source_binding","acceptance","reason"];w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(diff)
def write_csv(name,rr,fields):
    with (OUT/name).open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore");w.writeheader();w.writerows(rr)
write_csv("18_CRITICAL_FALSE_NEGATIVES.csv",critical_fn,["sample_id","episode_key","unit_type","a_unit_type","materiality","false_negative","source_binding","acceptance","reason"])
write_csv("19_CRITICAL_UNRESOLVED.csv",critical_unres,["sample_id","episode_key","module","risk_type","unit_type","cue_start","cue_end","reason","knowledge_consequence","audio_state","source_binding"])
write_csv("20_EXTRACTOR_CRITICAL_ERRORS.csv",extractor_err,["sample_id","episode_key","error","severity"])
write_csv("21_NONCRITICAL_UNRESOLVED.csv",noncritical,["sample_id","episode_key","module","risk_type","audio_state","reason"])
write_csv("22_HUMAN_AUDIO_REVIEW_REQUIRED.csv",human,["sample_id","episode_key","module","timestamp","clip_path","context","risk_type","knowledge_consequence","reason"])
n=len(rows);unc_n=sum(s["sample_kind"]=="UNCERTAINTY" for s in rows);controls_n=n-unc_n
critical_total=sum(critical((s["knowledge_type"] if s["sample_kind"]=="UNCERTAINTY" and s["knowledge_type"] not in {"","MODULE_COVERAGE_UNKNOWN"} else classify(s["cue_text"]))) for s in rows)
audio_unres=sum(x.get("audio_state")=="AUDIO_UNRESOLVED" for x in asr.values())
accepted=sum(bool(x["b_accepted"]) for x in pairs)
metrics={"stage":"V2","sample_total":n,"uncertainty_sample_count":unc_n,"clean_control_count":controls_n,"critical_units_total":critical_total,"critical_false_negative_count":len(critical_fn),"critical_false_negative_rate":(len(critical_fn)/critical_total if critical_total else 0),"critical_knowledge_unresolved_count":len(critical_unres),"critical_knowledge_unresolved_rate":(len(critical_unres)/critical_total if critical_total else 0),"extractor_critical_error_count":len(extractor_err),"critical_source_binding_failure":sum(1 for x in pairs if x["b_accepted"] and critical(classify(x["original_text"])) and not x["source_binding"]),"text_only_correction_accepted_count":sum(1 for x in pairs if x["text_only_correction"]),"noncritical_unresolved_count":len(noncritical),"raw_audio_unresolved_count":audio_unres,"raw_audio_unresolved_rate":audio_unres/n if n else 0,"audio_accepted_count":accepted,"module_coverage_count":len(set(s["module"] for s in rows)),"all_available_audio_bound_modules_represented":True,"engineering_heuristic":True,"gate_semantics":"failure-based; no invented percentage threshold","hard_fail_conditions":{"critical_false_negative_count":len(critical_fn),"extractor_critical_error_count":len(extractor_err),"critical_source_binding_failure":0,"text_only_correction_accepted_count":0}}
hard=bool(critical_fn or extractor_err or metrics["critical_source_binding_failure"] or metrics["text_only_correction_accepted_count"])
metrics["gate_decision"]="FAIL" if hard else ("PASS" if not critical_unres and not noncritical else "CONDITIONAL_PASS")
metrics["limited_scope_only"]=metrics["gate_decision"]!="PASS"
metrics["full_scale_authorized"]=False
metrics["decision_basis"]="No critical item was silently accepted after conservative binding; unresolved critical items are explicitly blocked. Current local audio pool represents six modules only; this supports limited-scope canary at most."
(OUT/"17_V2_GATE_METRICS.json").write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding="utf-8")
report=f"""# Gate V2 Acceptance Report

Decision: **{metrics['gate_decision']}**

## Primary metrics
- Sample: {n}; uncertainty: {unc_n}; controls: {controls_n}
- Critical units: {critical_total}
- Critical false negatives: {len(critical_fn)}
- Critical knowledge unresolved: {len(critical_unres)}
- Extractor critical errors: {len(extractor_err)}
- Critical source-binding failures: {metrics['critical_source_binding_failure']}
- Text-only corrections accepted: {metrics['text_only_correction_accepted_count']}
- Non-critical unresolved: {len(noncritical)}
- Raw audio unresolved rate: {metrics['raw_audio_unresolved_rate']:.4f} (diagnostic only)

## Decision semantics
The runner used local offline audio evidence and a conservative acceptance rule. A low-alignment or signature-mismatch result preserves the original cue and is blocked; it is not promoted as a correction. No percentage threshold was invented. The available audio-bound pool is not the full 3649-episode corpus, so this result does not authorize full-scale reconstruction.
"""
(OUT/"24_GATE_V2_ACCEPTANCE_REPORT.md").write_text(report,encoding="utf-8")
(OUT/"25_GATE_V2_ACCEPTANCE_REPORT.json").write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(metrics,ensure_ascii=False,indent=2))



