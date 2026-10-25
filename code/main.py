#!/usr/bin/env python3
"""Run the offline deletion audit from the repository root or any directory."""
import argparse
from collections import Counter
from datetime import datetime,timezone
import csv
import hashlib
import json
from pathlib import Path
import time
from audit import Auditor, OPERATIONS, STATES
from evidence import EvidenceStore, read_csv
from intent import IntentModel

ROOT=Path(__file__).resolve().parents[1]

def validate(results,requests,manifest):
    assert len(results)==len(requests)
    assert [r['case_id'] for r in results]==sorted(r['case_id'] for r in requests)
    assert len({r['case_id'] for r in results})==len(results)
    captures={m['file_id']:m['captured_at'] for m in manifest}
    by_case={r['case_id']:r for r in requests}
    fields={'step_no','phase','system_id','resource_id','operation','state','evidence_id'}
    for row in results:
        assert row['deletion_status'] in {'COMPLETE','INCOMPLETE','NOT_APPLICABLE'}
        if row['deletion_status']=='NOT_APPLICABLE':assert row['steps']==[]
        for i,s in enumerate(row['steps'],1):
            assert set(s)==fields and s['step_no']==i
            assert s['operation'] in OPERATIONS[s['phase']] and s['state']==STATES[s['operation']]
            needs_evidence=s['phase']=='FINDING' or row['deletion_status']=='COMPLETE'
            if needs_evidence:
                assert s['evidence_id'] in captures
                assert captures[s['evidence_id']]<=by_case[row['case_id']]['audit_at']
            else:assert s['evidence_id']==''
            if row['deletion_status']=='COMPLETE':assert s['phase']=='VERIFICATION'

def write_output(path,results):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8',newline='') as f:
        writer=csv.writer(f);writer.writerow(['case_id','deletion_status','steps_json'])
        for r in results:writer.writerow([r['case_id'],r['deletion_status'],json.dumps(r['steps'],separators=(',',':'),ensure_ascii=False)])

def run(dataset,request_path,output,cache,diagnostics_path=None):
    start=time.monotonic();requests=read_csv(request_path)
    store=EvidenceStore(dataset,cache);intent=IntentModel();auditor=Auditor(dataset,store,intent)
    results=[auditor.audit(r) for r in sorted(requests,key=lambda r:r['case_id'])]
    validate(results,requests,store.manifest);write_output(output,results)
    usage={'timestamp':datetime.now(timezone.utc).isoformat(),'requests':len(requests),
           'model':intent.name,'classifier_calls':intent.calls,'ocr_calls':store.ocr_calls,
           'hosted_model_calls':0,'input_tokens':0,'output_tokens':0,'api_cost_usd':0,
           'seconds':round(time.monotonic()-start,3),'observations':len(store.observations),
           'files':len(store.manifest),'output_sha256':hashlib.sha256(Path(output).read_bytes()).hexdigest(),
           'statuses':dict(Counter(r['deletion_status'] for r in results)),
           'cases_with_warnings':sum(bool(d['warnings']) for d in auditor.diagnostics)}
    if diagnostics_path:
        Path(diagnostics_path).parent.mkdir(parents=True,exist_ok=True)
        Path(diagnostics_path).write_text(json.dumps({'usage':usage,'cases':auditor.diagnostics,'files':store.diagnostics},indent=2))
    print(json.dumps(usage,indent=2))
    return results,auditor,usage

def cli():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset',type=Path,default=ROOT/'dataset')
    p.add_argument('--requests',type=Path)
    p.add_argument('--output',type=Path,default=ROOT/'output.csv')
    p.add_argument('--cache',type=Path,default=ROOT/'.cache'/'ocr')
    p.add_argument('--diagnostics',type=Path,default=ROOT/'evaluation'/'run_diagnostics.json')
    args=p.parse_args()
    run(args.dataset,args.requests or args.dataset/'deletion_requests.csv',args.output,args.cache,args.diagnostics)

if __name__=='__main__':cli()
