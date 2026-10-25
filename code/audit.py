"""Identity resolution, cutoff-aware state reconstruction, policy, and planning."""
from collections import defaultdict
import hashlib
from evidence import read_csv, tokens, Observation, CATEGORY_SYSTEM

PHASES=['FINDING','REMEDIATION','VERIFICATION']
OPERATIONS={
 'FINDING':['REPORT_REMAINING_RECORD','REPORT_EXPOSED_PII','REPORT_ACTIVE_DATA_FLOW','REPORT_RESTORE_RISK'],
 'REMEDIATION':['DISABLE_DATA_FLOW','BLOCK_RESTORE','DELETE_RECORD','REDACT_RECORD','ANONYMIZE_RECORD'],
 'VERIFICATION':['VERIFY_RECORD_ABSENT','VERIFY_RECORD_PRESENT','VERIFY_RECORD_REDACTED','VERIFY_RECORD_ANONYMIZED','VERIFY_DATA_FLOW_DISABLED','VERIFY_RESTORE_BLOCKED'],
}
STATES={
 'REPORT_REMAINING_RECORD':'PRESENT','REPORT_EXPOSED_PII':'PRESENT',
 'REPORT_ACTIVE_DATA_FLOW':'ACTIVE','REPORT_RESTORE_RISK':'ACTIVE',
 'DISABLE_DATA_FLOW':'DISABLED','BLOCK_RESTORE':'BLOCKED','DELETE_RECORD':'ABSENT',
 'REDACT_RECORD':'REDACTED','ANONYMIZE_RECORD':'ANONYMIZED',
 'VERIFY_RECORD_ABSENT':'ABSENT','VERIFY_RECORD_PRESENT':'PRESENT',
 'VERIFY_RECORD_REDACTED':'REDACTED','VERIFY_RECORD_ANONYMIZED':'ANONYMIZED',
 'VERIFY_DATA_FLOW_DISABLED':'DISABLED','VERIFY_RESTORE_BLOCKED':'BLOCKED',
}
TARGETS={
 'DELETE':('ABSENT','REPORT_REMAINING_RECORD','DELETE_RECORD','VERIFY_RECORD_ABSENT'),
 'REDACT':('REDACTED','REPORT_EXPOSED_PII','REDACT_RECORD','VERIFY_RECORD_REDACTED'),
 'ANONYMIZE':('ANONYMIZED','REPORT_EXPOSED_PII','ANONYMIZE_RECORD','VERIFY_RECORD_ANONYMIZED'),
 'RETAIN':('PRESENT',None,None,'VERIFY_RECORD_PRESENT'),
 'DISABLE':('DISABLED','REPORT_ACTIVE_DATA_FLOW','DISABLE_DATA_FLOW','VERIFY_DATA_FLOW_DISABLED'),
 'BLOCK':('BLOCKED','REPORT_RESTORE_RISK','BLOCK_RESTORE','VERIFY_RESTORE_BLOCKED'),
}

class IdentityIndex:
    def __init__(self,dataset):
        self.people=read_csv(dataset/'user_identities.csv')
        self.history=defaultdict(list)
        for row in read_csv(dataset/'user_audit_log.csv'):self.history[row['user_id']].append(row)
        self.by_email=defaultdict(set)
        for row in self.people:
            self.by_email[row['email'].casefold()].add(row['user_id'])
            for h in self.history[row['user_id']]:
                if h['field_name']=='email':
                    for v in ['old_value','new_value']:self.by_email[h[v].casefold()].add(row['user_id'])
        self.by_user={r['user_id']:r for r in self.people}

    def resolve(self,email,cutoff):
        users=self.by_email[email.casefold()]
        if len(users)!=1:raise ValueError(f'Request email resolves to {len(users)} subjects')
        user=next(iter(users));snapshot=dict(self.by_user[user])
        # Roll current values back through future changes before enumerating historical values.
        for h in sorted(self.history[user],key=lambda h:h['event_time'],reverse=True):
            if h['event_time']>cutoff:snapshot[h['field_name']]=h['old_value']
        identifiers=tokens(snapshot)
        for h in self.history[user]:
            if h['event_time']<=cutoff:
                identifiers |= tokens(h['old_value'])|tokens(h['new_value'])
        # Hash recovery from historical email is a grounded transformation, not fuzzy matching.
        for kind,value in list(identifiers):
            if kind=='email':identifiers.add(('hash',hashlib.sha256(value.encode()).hexdigest()))
        if ('email',email.casefold()) not in identifiers:
            raise ValueError('Request identifier is not known at the audit cutoff')
        return user,identifiers

class Auditor:
    def __init__(self,dataset,store,intent):
        self.store=store;self.intent=intent;self.identities=IdentityIndex(dataset)
        self.rules={r['data_category']:r for r in read_csv(dataset/'deletion_rules.csv')}
        self.diagnostics=[]

    def audit(self,request):
        authorized,confidence,reason=self.intent.classify(request['request_text'])
        diag={'case_id':request['case_id'],'intent_authorized':authorized,'intent_probability':confidence,'intent_reason':reason,'warnings':[],'resources':[],'ownership_links':[],'unverified_resources':[]}
        self.diagnostics.append(diag)
        if not authorized:return {'case_id':request['case_id'],'deletion_status':'NOT_APPLICABLE','steps':[]}
        cutoff=request['audit_at'];user,identifiers=self.identities.resolve(request['email'],cutoff)
        eligible=[o for o in self.store.observations if o.available_at<=cutoff and o.observed_at<=cutoff]
        # Subject associations and references must themselves exist at or before the cutoff.
        owned={o.resource for o in eligible if o.identifiers & identifiers}
        for o in eligible:
            if o.identifiers & identifiers:
                diag['ownership_links'].append(dict(resource=o.resource,evidence=o.evidence,
                    observed_at=o.observed_at,available_at=o.available_at,method='exact subject identifier'))
        for when,resource,ids,evidence in self.store.links:
            if when<=cutoff and ids & identifiers:
                owned.add(resource)
                diag['ownership_links'].append(dict(resource=resource,evidence=evidence,
                    observed_at=when,available_at=when,method='explicit catalog identity'))
        # Direct record references support identity propagation, not mere co-location in a file.
        changed=True
        while changed:
            changed=False
            for o in eligible:
                if o.resource in owned:
                    for ref in o.references:
                        # An explicit link to a record with another subject must not leak identity.
                        conflicts=[x for x in eligible if x.resource==ref and x.identifiers and not x.identifiers & identifiers]
                        if ref not in owned and not conflicts:
                            owned.add(ref);changed=True
                            diag['ownership_links'].append(dict(resource=ref,evidence=o.evidence,
                                observed_at=o.observed_at,available_at=o.available_at,
                                method='explicit source-resource reference',from_resource=o.resource))
        candidates=defaultdict(list)
        for o in eligible:
            if o.resource in owned:candidates[o.resource].append(o)
        # Closed-world absence is valid only within a declared snapshot scope, anchored
        # to this subject; an arbitrary unrelated database dump is not global absence proof.
        anchors={o.evidence for o in eligible if o.resource in owned}
        for scope in self.store.scopes:
            if scope.evidence not in anchors or scope.available_at>cutoff or scope.observed_at>cutoff:continue
            for resource in owned-scope.resources:
                prior=[o for o in candidates[resource] if o.system==scope.system and o.category==scope.category and o.observed_at<=scope.observed_at]
                if prior and scope.category in {'USER_PROFILE','SEARCH_INDEX_ENTRY','USER_EXPORT','SUPPORT_ATTACHMENT','MARKETING_PROFILE','SECONDARY_IDENTIFIER'}:
                    candidates[resource].append(Observation(scope.system,resource,scope.category,'ABSENT',scope.observed_at,scope.available_at,scope.evidence,location='snapshot absence',priority=2))
        latest=[]
        for resource,items in candidates.items():
            if not items:continue
            # Readbacks supersede stale rows. At equal times preserve a violating replica
            # over a compliant primary; then prefer direct readbacks over OCR interpretation.
            best=max(items,key=lambda o:(o.observed_at,o.state in {'PRESENT','ACTIVE'},o.priority,o.available_at,o.evidence))
            latest.append(best)
        # Keep referenced targets in the plan even when their state is unknown.
        # UNKNOWN is internal only: it creates no unsupported finding or remediation.
        # It requires a future verification and prevents a false COMPLETE verdict.
        observed_resources={o.resource for o in latest}
        hinted=set()
        for hint in self.store.resource_hints:
            if (hint['available_at']>cutoff or hint['observed_at']>cutoff
                    or hint['resource'] not in owned or hint['owner_resource'] not in owned
                    or hint['resource'] in observed_resources or hint['resource'] in hinted):
                continue
            hinted.add(hint['resource'])
            latest.append(Observation(hint['system'],hint['resource'],hint['category'],'UNKNOWN',
                hint['observed_at'],hint['available_at'],hint['evidence'],location=hint['location']))
            diag['unverified_resources'].append(dict(resource=hint['resource'],system=hint['system'],
                category=hint['category'],linked_from=hint['owner_resource'],link_evidence=hint['evidence'],
                reason='Explicit ownership reference exists, but no cutoff-valid state observation.'))
            diag['warnings'].append(f"No cutoff-valid state observation for referenced resource {hint['resource']}.")
        if not any(o.category=='USER_PROFILE' and o.state!='UNKNOWN' for o in latest):
            diag['warnings'].append('No identity-linked account resource with cutoff-valid readback; cannot prove account absence.')
        findings=[];remediations=[];verifications=[]
        def step(phase,op,o,evidence):
            return dict(step_no=0,phase=phase,system_id=o.system,resource_id=o.resource,operation=op,state=STATES[op],evidence_id=evidence)
        for o in latest:
            action=self.action(o)
            if action not in TARGETS:
                diag['warnings'].append(f'No applicable policy for {o.resource} ({o.category})');continue
            wanted,finding,remedy,verify=TARGETS[action]
            diag['resources'].append(dict(resource=o.resource,category=o.category,observed_state=o.state,target_state=wanted,evidence=o.evidence,observed_at=o.observed_at,location=o.location))
            if o.state not in {wanted,'UNKNOWN'}:
                if finding and remedy:
                    findings.append(step('FINDING',finding,o,o.evidence))
                    remediations.append(step('REMEDIATION',remedy,o,''))
                else:diag['warnings'].append(f'Required retained record {o.resource} is missing; contract has no restore-retained operation.')
            verifications.append(step('VERIFICATION',verify,o,o.evidence))
        # Evidence gaps are never upgraded to COMPLETE. The fixed contract has no UNKNOWN;
        # INCOMPLETE plus explicit diagnostics is the conservative representation.
        status='INCOMPLETE' if findings or diag['warnings'] else 'COMPLETE'
        if status=='INCOMPLETE':
            for v in verifications:v['evidence_id']=''
        steps=findings+remediations+verifications
        steps.sort(key=lambda x:(PHASES.index(x['phase']),OPERATIONS[x['phase']].index(x['operation']),x['system_id'],x['resource_id']))
        for n,s in enumerate(steps,1):s['step_no']=n
        return {'case_id':request['case_id'],'deletion_status':status,'steps':steps}

    def action(self,obs):
        if obs.category=='DATA_FLOW':return 'DISABLE'
        if obs.category=='BACKUP_ARCHIVE':return 'BLOCK'
        return self.rules.get(obs.category,{}).get('required_action')
