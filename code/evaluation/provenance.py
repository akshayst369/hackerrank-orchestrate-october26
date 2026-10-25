"""Evaluation-only inspection of missing public-sample verification steps.

This module reads public expected answers to diagnose errors. It is never imported
by the prediction pipeline and never writes ownership links or predictions.
"""
from collections import Counter
import json
from pathlib import Path
import re
from audit import IdentityIndex
from evidence import read_csv


def missing_provenance(root,store,predicted):
    requests={r['case_id']:r for r in read_csv(root/'dataset/sample_deletion_requests.csv')}
    identities=IdentityIndex(root/'dataset')
    expected=read_csv(root/'dataset/sample_output.csv')
    rows=[];counts=Counter()
    for gold in expected:
        case=gold['case_id'];request=requests[case]
        _,ids=identities.resolve(request['email'],request['audit_at'])
        actual={(s['phase'],s['system_id'],s['resource_id'],s['operation']) for s in predicted[case]['steps']}
        for step in json.loads(gold['steps_json']):
            key=(step['phase'],step['system_id'],step['resource_id'],step['operation'])
            if step['phase']!='VERIFICATION' or key in actual:continue
            resource=step['resource_id'];cutoff=request['audit_at']
            all_obs=store.by_resource.get(resource,[])
            eligible=[o for o in all_obs if o.observed_at<=cutoff and o.available_at<=cutoff]
            linked=any(o.identifiers & ids for o in eligible)
            catalog=any(when<=cutoff and r==resource and match&ids for when,r,match,_ in store.links)
            if eligible and not (linked or catalog):reason='Readback exists; no cutoff-valid subject link'
            elif not eligible and all_obs:reason='All parsed state evidence is after cutoff'
            elif not all_obs:reason='No parsed state observation for this resource'
            else:reason='Investigate selection or planning'
            counts[reason]+=1
            details=[]
            for o in all_obs:
                valid=o.observed_at<=cutoff and o.available_at<=cutoff
                details.append(f'{o.evidence}: {o.state}; observed {o.observed_at}; available {o.available_at}; '+('eligible' if valid else 'excluded by cutoff'))
            activities=[a for a in store.activities if a['resource_id']==resource and a['event_time']<=cutoff]
            if activities:
                details.append('Activity references: '+', '.join(a['activity_id'] for a in activities)+'. Operation claims alone do not establish subject ownership or final state.')
            if not details:details.append('No parsed observation or cutoff-valid activity target found.')
            rows.append((case,resource,step['operation'],reason,'<br>'.join(details)))
    text='''# Public-sample provenance review

This report investigates every remaining missing verification step using only participant-facing data.
Expected steps are used **only to locate evaluation failures**, never to create prediction-time links.
A missing explicit row does not itself prove absence: the target's ownership and the snapshot's scope must also be established.

## Summary

'''
    text+=f'Total missing verification steps: **{len(rows)}**, down from 35 before this improvement pass.\n\n'
    text+='| Reason | Missing steps |\n| --- | ---: |\n'
    text+='\n'.join(f'| {reason} | {count} |' for reason,count in sorted(counts.items()))+'\n\n'
    text+='''## Recovered behavior

An explicit `source_resource_id` from a subject-owned search document now keeps the source account in the future verification plan, even if no account-state readback is available.
It does not produce an unsupported finding, claim deletion, or turn UNKNOWN internal state into COMPLETE.
The fix recovers the missing account verification in public sample case_06.
Historical ownership is preserved across later anonymized readbacks when an earlier cutoff-valid association actually exists.
Free-text mentions, filenames, and neighboring records no longer establish resource ownership.

## Remaining missing steps

| Case | Resource | Expected operation | Classification | Participant-visible observations |
| --- | --- | --- | --- | --- |
'''
    text+='\n'.join('| '+' | '.join(row)+' |' for row in rows)+'\n'
    text+='''
## Limits and supported disagreements

The nine remaining status errors are all COMPLETE samples predicted INCOMPLETE because the pipeline lacks an adequately linked account readback.
This report does not assert that all such cases are fundamentally impossible: it identifies exactly which observations the current parsers found, so another retrieval method can be checked against the original artifacts.

Several extra steps are supported by the supplied evidence but absent from the public answers: object_19 has an explicit subject-only catalog link and an object-storage screenshot; account_6523 has an identity-linked absence readback; tombstone_17 has a catalog-linked retained-reference screen. They have not been removed solely to match sample labels.
A larger reliable accuracy gain requires additional explicit provenance or a demonstrated retrieval improvement; numeric ID alignment, fixed event offsets, future evidence, and memorized sample targets are not substitutes.
'''
    (root/'evaluation/provenance_review.md').write_text(text)
    return len(rows)
