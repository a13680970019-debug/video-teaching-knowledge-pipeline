from pathlib import Path
import csv,json,hashlib

OUT=Path(r'D:\AI-Agent-Workspaces\GitHub\video-teaching-knowledge-pipeline\audit\knowledge-evidence-gate-pilot-v2-20260817')
V1=Path(r'D:\AI-Agent-Workspaces\GitHub\video-teaching-knowledge-pipeline\audit\knowledge-evidence-gate-pilot-20260817')
def j(name): return json.loads((OUT/name).read_text(encoding='utf-8'))
def rows(name): return list(csv.DictReader((OUT/name).open(encoding='utf-8-sig',newline='')))
def test_v1_immutable():
    m=j('02_V1_IMMUTABILITY_MANIFEST.json')
    assert m['actual_file_count']==53 and m['status']=='CONFLICT'
    for x in m['files']:
        assert (V1/x['relative_path']).exists()
        assert hashlib.sha256((V1/x['relative_path']).read_bytes()).hexdigest()==x['sha256']
def test_sampling_reproducible_shape():
    r=rows('11_V2_SAMPLE_MANIFEST.csv')
    assert len(r)==24 and len({x['sample_id'] for x in r})==24
    assert sum(x['sample_kind']=='UNCERTAINTY' for x in r)==18
    assert sum(x['sample_kind']=='CLEAN_CONTROL' for x in r)==6
    assert len({x['module'] for x in r})==6
def test_risk_and_module_counts():
    r=rows('11_V2_SAMPLE_MANIFEST.csv')
    assert sum(x['risk_type']=='FORMULA' for x in r)>=1
    assert sum(x['risk_type']=='NUMBER' for x in r)>=1
    assert len(set(x['collection_id'] for x in r))>=6
def test_raw_unresolved_is_not_critical_unresolved():
    m=j('17_V2_GATE_METRICS.json')
    assert m['raw_audio_unresolved_count'] != m['critical_knowledge_unresolved_count']
def test_filler_case_is_not_auto_promoted():
    r=rows('04_UNRESOLVED_ROOT_CAUSE.csv')
    assert len(r)==10 and all(x['final_audio_state']=='AUDIO_UNRESOLVED' for x in r)
    assert all(x['human_review_required']=='true' for x in r)
def test_critical_types_present_in_gate():
    m=j('17_V2_GATE_METRICS.json')
    assert m['critical_units_total']>=1
    assert 'critical_false_negative_count' in m and 'extractor_critical_error_count' in m
def test_ab_extractor_output_shape():
    a=(OUT/'14_V2_KNOWLEDGE_A.jsonl').read_text(encoding='utf-8').splitlines()
    b=(OUT/'15_V2_KNOWLEDGE_B.jsonl').read_text(encoding='utf-8').splitlines()
    assert len(a)==24 and len(b)==24
    for line in a+b:
        x=json.loads(line); assert x['source_bound'] is True and x['source_audio_sha256']
def test_source_binding_and_text_only_rejection():
    r=[json.loads(x) for x in (OUT/'13_V2_AB_PAIRS.jsonl').read_text(encoding='utf-8').splitlines()]
    assert all(x['text_only_correction'] is False for x in r)
    assert all(x['source_binding'] is True for x in r if x['b_accepted'])
def test_human_escalation():
    assert len(rows('19_CRITICAL_UNRESOLVED.csv'))==len(rows('22_HUMAN_AUDIO_REVIEW_REQUIRED.csv'))
def test_gate_fail_logic_is_explicit():
    m=j('17_V2_GATE_METRICS.json')
    assert m['gate_decision']=='FAIL' and m['extractor_critical_error_count']==2
    assert m['critical_false_negative_count']==0 and m['text_only_correction_accepted_count']==0
def test_historical_contract_unchanged():
    h=j('00_STAGE_MANIFEST.json')['v1_reverification']['v1_historical_contract']
    assert h=={'TOTAL_WORD_ROWS':49829,'INITIAL_HIGH_RISK_WORDS':8936,'R2_RESOLVED':3901,'SECOND_PASS_REQUIRED_WORDS':5035,'MASKED_UNCLEAR':1760}
def test_github_epoch_separation():
    s=(OUT/'34_CURRENT_STATUS_RECONCILIATION.md').read_text(encoding='utf-8')
    assert 'INITIAL_HIGH_RISK_WORDS=8936' in s and 'SECOND_PASS_REQUIRED_WORDS=5035' in s
def test_governance_no_merge():
    x=j('35_GOVERNANCE_BRANCH_STATE.json')
    assert x['commit_pushed'] is True and x['pr_created'] is False and x['merge_executed'] is False

