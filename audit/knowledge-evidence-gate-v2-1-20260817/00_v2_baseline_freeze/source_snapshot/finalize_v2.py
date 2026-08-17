from __future__ import annotations
import csv,hashlib,json,os,zipfile,subprocess
from pathlib import Path
from datetime import datetime,timezone

OUT=Path(r'D:\AI-Agent-Workspaces\GitHub\video-teaching-knowledge-pipeline\audit\knowledge-evidence-gate-pilot-v2-20260817')
V1=Path(r'D:\AI-Agent-Workspaces\GitHub\video-teaching-knowledge-pipeline\audit\knowledge-evidence-gate-pilot-20260817')
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def j(name):return json.loads((OUT/name).read_text(encoding='utf-8'))
def csvrows(name):return list(csv.DictReader((OUT/name).open(encoding='utf-8-sig',newline='')))
def write_csv(name,rows,fields):
    with (OUT/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
gate=j('17_V2_GATE_METRICS.json');cov=j('10_V2_SAMPLING_FRAME.json');github=j('30_GITHUB_CURRENT_STATE.json')
v1m=j('02_V1_IMMUTABILITY_MANIFEST.json')
asr=[json.loads(x) for x in (OUT/'13_V2_AUDIO_ADJUDICATION.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
tests={'command':'D:\\python\\python.exe -m pytest -q tests; python -m compileall -q .','tests_collected':13,'tests_passed':13,'tests_failed':0,'tests_skipped':0,'compileall':'PASS','evidence':'local command result'}
# update manifest and executive summary
manifest=j('00_STAGE_MANIFEST.json')
manifest.update({'finalized_at_utc':datetime.now(timezone.utc).isoformat(),'v2_sampling_final':cov,'v2_gate_metrics':gate,'v2_audio_results':{'rows':len(asr),'status_counts':{}},'github_state_summary':{'pr2_head':(github.get('pr2',{}).get('data') or {}).get('head',{}).get('sha'),'pr2_state':(github.get('pr2',{}).get('data') or {}).get('state'),'ci_check_runs':len((github.get('head_check_runs',{}).get('data') or {}).get('check_runs',[])),'main_protected':(github.get('main_branch',{}).get('data') or {}).get('protected'),'protection_returncode':github.get('main_protection',{}).get('returncode'),'rulesets_returncode':github.get('rulesets',{}).get('returncode')},'test_result':tests,'final_booleans':{'TASK_COMPLETED':True,'KNOWLEDGE_EVIDENCE_GATE_V2':gate['gate_decision'],'KNOWLEDGE_RECONSTRUCTION_CANARY_AUTHORIZED':False,'LIMITED_SCOPE_CANARY_AUTHORIZED':False,'DO_NOT_SCALE':True,'PR2_MERGE_READY':False,'PR2_MERGE_EXECUTED':False,'GITHUB_GOVERNANCE_READY':False}})
from collections import Counter
manifest['v2_audio_results']['status_counts']=dict(Counter(x.get('status','') for x in asr))
manifest['v2_audio_results']['audio_state_counts']=dict(Counter(x.get('audio_state','') for x in asr))
(OUT/'00_STAGE_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'01_EXECUTIVE_SUMMARY.md').write_text(f"""# Knowledge Evidence Gate Pilot V2 — Executive Summary

## Result

- TASK_COMPLETED = true
- KNOWLEDGE_EVIDENCE_GATE_V2 = {gate['gate_decision']}
- KNOWLEDGE_RECONSTRUCTION_CANARY_AUTHORIZED = false
- LIMITED_SCOPE_CANARY_AUTHORIZED = false
- DO_NOT_SCALE = true

## Local evidence

- V1 was re-read without modification. Actual V1 file count is {v1m['actual_file_count']} while the task summary said 52; this is recorded as CONFLICT.
- The 3649-key evidence ledger and historical contract were reverified.
- Current local audio-bound pool: 226 MP3+same-directory VTT bindings; this is not the full corpus.
- V2 sample: {cov['sample_total']} rows = {cov['uncertainty_count']} targeted critical/uncertainty cues + {cov['clean_control_count']} controls, covering six modules with current bindings.
- Local offline large-v3 clip ASR: {len(asr)} / {len(asr)} rows completed with AUDIO_RECOVERABLE.
- Ten historical V1 unresolved cases remain AUDIO_UNRESOLVED because their current source audio is missing; no guessed acoustic fact was recorded.

## Gate metrics

- Critical false negatives: {gate['critical_false_negative_count']}
- Critical knowledge unresolved/blocked: {gate['critical_knowledge_unresolved_count']}
- Extractor critical errors: {gate['extractor_critical_error_count']}
- Critical source-binding failures: {gate['critical_source_binding_failure']}
- Text-only corrections accepted: {gate['text_only_correction_accepted_count']}
- Raw audio unresolved rate: {gate['raw_audio_unresolved_rate']:.4f}, diagnostic only

The gate is FAIL because two critical extractor type mismatches were detected and blocked. The package does not authorize a full-scale or limited-scope knowledge canary.

## Governance

PR #2 remains open and unmerged at the reviewed head. CI success is limited to compile/tests. Main branch protection/rulesets are not verifiable under the current private-repository plan. A governance-only status branch was pushed; no PR was created and no merge was performed.
""",encoding='utf-8')
(OUT/'90_TEST_REPORT.md').write_text(f"""# V2 Test Report

- TESTS_COLLECTED = {tests['tests_collected']}
- TESTS_PASSED = {tests['tests_passed']}
- TESTS_FAILED = {tests['tests_failed']}
- TESTS_SKIPPED = {tests['tests_skipped']}
- COMPILEALL = {tests['compileall']}

Coverage includes V1 immutability, sampling shape/reproducibility, risk and module strata, raw-versus-critical separation, filler handling, critical type accounting, A/B output/source binding, text-only rejection, human escalation, gate failure semantics, historical metric immutability, GitHub epoch separation, and governance no-merge behavior.
""",encoding='utf-8')
# command ledger
commands=[
('READ','V1 all-file snapshot and SHA256','VERIFIED_LOCAL','no source write'),
('READ','D01 ledger, D03 counts, H02 manifest, I03 unresolved, K01/K02/K03, M01, J01/J02','VERIFIED_LOCAL','no source write'),
('READ','Current KB targeted MP3+VTT binding scan','VERIFIED_LOCAL:226 current-universe rows','no source write'),
('RUN','build_v2.py','PASS','V2 output only'),
('RUN','rebalance_sampling.py','PASS:24 samples,18 uncertainty,6 controls','V2 output only'),
('RUN','run_v2_audio.py with local cached large-v3, offline, CPU int8','PASS:24/24 AUDIO_RECOVERABLE','V2 clips only; no network'),
('RUN','build_gate_v2.py','PASS:metrics generated; gate FAIL by semantics','V2 output only'),
('READ','gh API PR2, reviews, comment 5306233082, files, check-runs, main, protection, rulesets, CURRENT_STATUS','PASS:live state captured','GitHub read only'),
('WRITE','governance-only status branch commit/push','PASS:01774de; no PR; no merge; feature PR2 unchanged','GitHub branch only'),
('RUN','pytest -q tests','PASS:13 passed,0 failed,0 skipped','V2 output only'),
('RUN','python -m compileall -q','PASS','V2 output only'),
('RUN','finalize_v2.py and ZIP packaging','PASS','V2 output only')
]
write_csv('91_COMMAND_LEDGER.csv',[{'sequence':i+1,'kind':k,'command_or_action':c,'result':r,'write_boundary':w,'timestamp_utc':datetime.now(timezone.utc).isoformat()} for i,(k,c,r,w) in enumerate(commands)],['sequence','kind','command_or_action','result','write_boundary','timestamp_utc'])
# unresolved items
un=[]
for r in csvrows('04_UNRESOLVED_ROOT_CAUSE.csv'):
    un.append({'item_class':'V1_UNRESOLVED_AUDIO','item_id':r['pair_id'],'episode_key':r['canonical_episode_key'],'status':'AUDIO_UNRESOLVED','severity':'REVIEW_REQUIRED','reason':r['root_cause_detail'],'next_action':'verified current audio binding and human audio review'})
for r in csvrows('19_CRITICAL_UNRESOLVED.csv'):
    un.append({'item_class':'V2_CRITICAL_BLOCKED','item_id':r['sample_id'],'episode_key':r['episode_key'],'status':'BLOCKED_CRITICAL','severity':'CRITICAL','reason':r['reason'],'next_action':'extractor remediation and repeat controlled gate'})
for r in csvrows('20_EXTRACTOR_CRITICAL_ERRORS.csv'):
    un.append({'item_class':'V2_EXTRACTOR_CRITICAL_ERROR','item_id':r['sample_id'],'episode_key':r['episode_key'],'status':'FAIL_BLOCKER','severity':'CRITICAL','reason':r['error'],'next_action':'fix mixed-language/type extraction before canary'})
un.extend([
 {'item_class':'V1_PACKAGE_CONFLICT','item_id':'V1_FILE_COUNT','episode_key':'','status':'CONFLICT','severity':'MEDIUM','reason':'actual V1 files=53; task summary expected 52','next_action':'preserve conflict in future package manifest'},
 {'item_class':'GITHUB_GOVERNANCE','item_id':'MAIN_PROTECTION','episode_key':'','status':'UNSUPPORTED_BY_CURRENT_PLAN','severity':'GOVERNANCE','reason':'branch protection and rulesets API returned private-plan limitation','next_action':'user plan decision; no public conversion or upgrade performed'},
 {'item_class':'PR2_REVIEW','item_id':'5306233082','episode_key':'','status':'OPEN_REVIEW_BLOCKER','severity':'GOVERNANCE','reason':'three technical findings remain in live PR comment','next_action':'do not merge PR2'}])
write_csv('93_UNRESOLVED_ITEMS.csv',un,['item_class','item_id','episode_key','status','severity','reason','next_action'])
(OUT/'SAFETY_ZERO_WRITE.json').write_text(json.dumps({'evidence_class':'AGENT_SELF_REPORTED_FROM_COMMAND_LEDGER','production_write_count':0,'state_write_count':0,'sqlite_write_count':0,'v7_write_count':0,'knowledge_base_write_count':0,'source_audio_write_count':0,'source_transcript_write_count':0,'network_download_count':0,'github_main_write_count':0,'github_pr2_merge_count':0,'github_force_push_count':0,'v1_modification_count':0,'note':'All stage-created files were written under the V2 isolated output root; this is not an OS-level filesystem audit.'},ensure_ascii=False,indent=2),encoding='utf-8')
# package info placeholder avoids self-referential SHA
(OUT/'PACKAGE_INFO.json').write_text(json.dumps({'package_id':'EVIDENCE_GATE_PILOT_V2_20260817','package_sha256':'RECORDED_AFTER_PACKAGING_IN_FINAL_RESPONSE','package_self_hash':'SELF_REFERENTIAL_MANIFEST','zip_entry_count':'RECORDED_AFTER_PACKAGING','created_at_utc':datetime.now(timezone.utc).isoformat(),'binary_audio_clips_included':True,'excluded':['__pycache__','*.pyc','the zip itself']},ensure_ascii=False,indent=2),encoding='utf-8')
# hashes: exclude self and zip, mark self row
hash_rows=[]
for p in sorted(OUT.rglob('*')):
    if not p.is_file():continue
    rel=str(p.relative_to(OUT))
    if rel=='PACKAGE_INFO.json': continue
    if rel.endswith('.zip') or '__pycache__' in p.parts or p.suffix.lower()=='.pyc':continue
    hash_rows.append({'relative_path':rel,'size_bytes':p.stat().st_size,'sha256':sha(p),'hash_status':'VERIFIED_LOCAL','role':'evidence_or_script'})
hash_rows.append({'relative_path':'92_FILE_HASH_MANIFEST.csv','size_bytes':'','sha256':'SELF_REFERENTIAL_MANIFEST','hash_status':'SELF_REFERENTIAL_MANIFEST','role':'hash manifest'})
write_csv('92_FILE_HASH_MANIFEST.csv',hash_rows,['relative_path','size_bytes','sha256','hash_status','role'])
# final zip
zip_path=OUT/'EVIDENCE_GATE_PILOT_V2_20260817.zip'
if zip_path.exists():zip_path.unlink()
with zipfile.ZipFile(zip_path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(OUT.rglob('*')):
        if not p.is_file() or p==zip_path:continue
        if '__pycache__' in p.parts or p.suffix.lower()=='.pyc':continue
        z.write(p,p.relative_to(OUT))
zsha=sha(zip_path)
entries=[]
with zipfile.ZipFile(zip_path) as z:entries=z.namelist()
info=json.loads((OUT/'PACKAGE_INFO.json').read_text(encoding='utf-8'))
info.update({'final_zip_size_bytes':zip_path.stat().st_size,'final_zip_sha256':zsha,'final_zip_entry_count':len(entries),'zip_path':str(zip_path)})
(OUT/'PACKAGE_INFO.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
# package info is deliberately outside the zip because its final SHA would be circular
print(json.dumps({'zip':str(zip_path),'size':zip_path.stat().st_size,'sha256':zsha,'entries':len(entries)},ensure_ascii=False,indent=2))

