"""Normalize participant evidence into timestamped observations and identity links."""
from dataclasses import dataclass, field
from collections import defaultdict
from pathlib import Path
import csv
import hashlib
import json
import re
import sqlite3

TIME_RE = re.compile(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ')
RESOURCE_RE = re.compile(r'\b(?:account|analytics|search|support|export|data_flow|backup|audit_record|tombstone|marketing|object|cache|email_delivery|legal_hold|telemetry)_\d+\b')
EMAIL_RE = re.compile(r'[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}', re.UNICODE)
CATEGORY_SYSTEM = {
 'USER_PROFILE': 'account_service', 'SECONDARY_IDENTIFIER': 'support_platform',
 'SEARCH_INDEX_ENTRY': 'search_service', 'CACHE_ENTRY': 'cache_service',
 'SUPPORT_MESSAGE': 'support_platform', 'SUPPORT_ATTACHMENT': 'support_platform',
 'ANALYTICS_PROFILE': 'analytics_platform', 'PRODUCT_TELEMETRY': 'analytics_platform',
 'USER_EXPORT': 'export_service', 'MARKETING_PROFILE': 'marketing_platform',
 'EMAIL_DELIVERY_LOG': 'email_delivery_service', 'SECURITY_AUDIT_LOG': 'security_service',
 'LEGAL_HOLD_RECORD': 'legal_service', 'BACKUP_ARCHIVE': 'backup_service',
 'ACCOUNT_TOMBSTONE': 'identity_service', 'DATA_FLOW': 'integration_service',
}
COLLECTIONS = {
 'customer_profiles': 'USER_PROFILE', 'profile_lookups': 'USER_PROFILE',
 'customer_search_documents': 'SEARCH_INDEX_ENTRY', 'search_documents': 'SEARCH_INDEX_ENTRY', 'index_queries': 'SEARCH_INDEX_ENTRY',
 'customer_analytics_reports': 'ANALYTICS_PROFILE', 'customer_analytics_profiles': 'ANALYTICS_PROFILE',
 'support_conversations': 'SUPPORT_MESSAGE', 'support_records': 'SUPPORT_MESSAGE', 'tickets': 'SUPPORT_MESSAGE',
 'support_attachments': 'SUPPORT_ATTACHMENT', 'customer_export_jobs': 'USER_EXPORT', 'customer_exports': 'USER_EXPORT', 'exports': 'USER_EXPORT',
 'connector_configurations': 'DATA_FLOW', 'connector_subscriptions': 'DATA_FLOW', 'connectors': 'DATA_FLOW',
 'backup_catalog': 'BACKUP_ARCHIVE', 'backup_restore_entries': 'BACKUP_ARCHIVE', 'restore_entries': 'BACKUP_ARCHIVE',
 'security_audit_events': 'SECURITY_AUDIT_LOG', 'security_audit_records': 'SECURITY_AUDIT_LOG', 'audit_records': 'SECURITY_AUDIT_LOG',
 'deleted_customer_references': 'ACCOUNT_TOMBSTONE',
}
SYSTEM_CATEGORY = {v:k for k,v in CATEGORY_SYSTEM.items()}
SYSTEM_CATEGORY.update(account_service='USER_PROFILE', support_platform='SUPPORT_MESSAGE',analytics_platform='ANALYTICS_PROFILE')
EMPTY = {'', 'none', 'null', '[redacted]', 'redacted', 'no direct identifier'}
DIRECT_FIELDS = {'name','full_name','display_name','email','phone','email_hash','customer_email',
                 'owner_email','owner_phone','requester_name','requester_email','requester_phone'}
REFERENCE_FIELDS = {'user_id','customer_reference','subject_reference','subject_ref','subject_selector'}

def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def tokens(value):
    """Exact typed tokens: never substring-match similar emails or numeric IDs."""
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value,str) else value
    out = {('email',m.casefold()) for m in EMAIL_RE.findall(text)}
    out |= {('user',m) for m in re.findall(r'\buser_\d+\b',text)}
    out |= {('hash',m.lower()) for m in re.findall(r'(?<![a-zA-Z0-9])[a-fA-F0-9]{64}(?![a-zA-Z0-9])',text)}
    out |= {('phone',re.sub(r'\D','',m)) for m in re.findall(r'\+\d[\d ()-]{7,}\d',text)}
    return out

def flat_items(obj):
    if isinstance(obj,dict):
        for k,v in obj.items():
            if isinstance(v,(dict,list)):yield from flat_items(v)
            else:yield k,v
    elif isinstance(obj,list):
        for v in obj:yield from flat_items(v)

def meaningful(value):
    return value is not None and str(value).strip().casefold() not in EMPTY

def bool_value(value):
    return str(value).casefold() in {'true','1','yes','enabled','allowed'}

def infer_category(collection, system=''):
    for c,cat in sorted(COLLECTIONS.items(),key=lambda x:-len(x[0])):
        if c in collection:return cat
    return SYSTEM_CATEGORY.get(system,'')

@dataclass
class Observation:
    system: str
    resource: str
    category: str
    state: str
    observed_at: str
    available_at: str
    evidence: str
    identifiers: set = field(default_factory=set)
    references: set = field(default_factory=set)
    location: str = ''
    priority: int = 2

@dataclass
class Scope:
    evidence: str
    available_at: str
    observed_at: str
    system: str
    category: str
    resources: set

class EvidenceStore:
    def __init__(self, dataset, cache):
        self.dataset=Path(dataset).resolve();self.cache=Path(cache)
        self.observations=[];self.scopes=[];self.links=[];self.diagnostics=[];self.ocr_calls=0
        self.manifest=read_csv(self.dataset/'evidence_files.csv')
        self.activities=read_csv(self.dataset/'system_activity.csv')
        self.catalog={}
        for a in self.activities:
            if a['event_type']=='LINK_RESOURCE_IDENTITY':
                self.catalog[a['resource_id']]=a
                self.links.append((a['event_time'],a['resource_id'],tokens(a['details']),a['activity_id']))
        for meta in self.manifest:
            p=(self.dataset/meta['file_path']).resolve()
            if not p.is_relative_to(self.dataset/'evidence'):raise ValueError('Evidence path outside dataset/evidence')
            if p.suffix=='.json':self.parse_json(p,meta)
            elif p.suffix=='.sql':self.parse_sql(p,meta)
            elif p.suffix=='.log':self.parse_log(p,meta)
            elif p.suffix=='.txt':self.parse_text(p.read_text(),meta)
            elif p.suffix=='.pdf':self.parse_pdf(p,meta)
            elif p.suffix=='.png':self.parse_image(p,meta)
            else:raise ValueError(f'Unsupported evidence format: {p.suffix}')
        self.by_resource=defaultdict(list)
        for obs in self.observations:self.by_resource[obs.resource].append(obs)

    def add(self, meta, system, resource, category, state, when, raw, location='', priority=2):
        if not (resource and system and category and state and when):
            raise ValueError(f'Incomplete observation in {meta["file_id"]}: {resource}, {category}, {state}')
        refs=set(RESOURCE_RE.findall(json.dumps(raw,ensure_ascii=False)))-{resource}
        self.observations.append(Observation(system,resource,category,state,when,meta['captured_at'],
                                             meta['file_id'],tokens(raw),refs,location,priority))

    def record(self, rec, meta, system, collection, when, location=''):
        cat=rec.get('record_type') or infer_category(collection,system)
        system=rec.get('system') or system or CATEGORY_SYSTEM.get(cat,'')
        resource=rec.get('resource_id','')
        when=rec.get('observed_at') or rec.get('recorded_at') or rec.get('updated_at') or when
        if not cat:raise ValueError(f'Unknown collection {collection} ({system})')
        if 'result' in rec and rec['result'] in {'FOUND','NOT_FOUND','IDENTIFIABLE','ANONYMIZED','ACTIVE','DISABLED','BLOCKED','REDACTED'}:
            state={'FOUND':'PRESENT','NOT_FOUND':'ABSENT','IDENTIFIABLE':'PRESENT'}.get(rec['result'],rec['result'])
        elif cat=='DATA_FLOW':state='ACTIVE' if bool_value(rec.get('enabled')) else 'DISABLED'
        elif cat=='BACKUP_ARCHIVE':state='ACTIVE' if bool_value(rec.get('restore_allowed')) else 'BLOCKED'
        elif str(rec.get('status_code',''))=='404':state='ABSENT'
        elif 'hits' in rec and rec['hits'].get('total')==0:state='ABSENT'
        elif cat in {'ANALYTICS_PROFILE','PRODUCT_TELEMETRY'}:
            identifiers=[v for k,v in flat_items(rec) if k in DIRECT_FIELDS|REFERENCE_FIELDS]
            state='PRESENT' if any(meaningful(v) for v in identifiers) else 'ANONYMIZED'
        elif cat in {'SUPPORT_MESSAGE','ACCOUNT_TOMBSTONE','EMAIL_DELIVERY_LOG'}:
            direct=any(meaningful(v) for k,v in flat_items(rec) if k in DIRECT_FIELDS)
            body=' '.join(str(v) for k,v in flat_items(rec) if k in {'message_text','message_excerpt','body','recipient'})
            direct=direct or bool(tokens(body))
            state='PRESENT' if direct else 'REDACTED'
        else:state='PRESENT'
        self.add(meta,system,resource,cat,state,when,rec,location)

    def parse_json(self,p,meta):
        doc=json.loads(p.read_text())
        if 'service_exports' in doc:
            for system,collections in doc['service_exports'].items():
                for collection,records in collections.items():
                    if collection=='profiles' and system=='analytics_platform':collection='customer_analytics_profiles'
                    for rec in records:self.record(rec,meta,system,collection,doc['exported_at'],collection)
            return
        groups=doc.get('snapshots',[doc])
        for group in groups:
            collection=group.get('collection','');cat=infer_category(collection)
            system=group.get('data_store') or CATEGORY_SYSTEM.get(cat,'')
            when=group.get('captured_at') or group.get('exported_at') or meta['captured_at']
            records=group.get('records',[])
            for rec in records:self.record(rec,meta,system,collection,when,collection)
            if cat:self.scopes.append(Scope(meta['file_id'],meta['captured_at'],when,system,cat,{r['resource_id'] for r in records}))

    def parse_sql(self,p,meta):
        sql=p.read_text();c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
        # Dataset SQL is untrusted: no attached files, extensions, triggers, or filesystem writes.
        banned=[sqlite3.SQLITE_ATTACH,sqlite3.SQLITE_DETACH,sqlite3.SQLITE_CREATE_TRIGGER]
        c.set_authorizer(lambda action,*args: sqlite3.SQLITE_DENY if action in banned else sqlite3.SQLITE_OK)
        c.executescript(sql)
        scopes=defaultdict(set);times={}
        header=re.search(r'-- Captured at: (\S+)',sql)
        when=header[1] if header else meta['captured_at']
        tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        for table in tables:
            quoted='"'+table.replace('"','""')+'"'
            for row in c.execute('SELECT * FROM '+quoted):
                rec=dict(row)
                if table=='snapshot_scope':times[rec['origin_system']]=rec['captured_at'];continue
                if 'record_json' in rec:
                    system=rec['origin_system'];collection=rec['collection_name'];obj=json.loads(rec['record_json'])
                    row_time=rec['updated_at']
                else:
                    collection=table;cat=infer_category(collection);system=CATEGORY_SYSTEM.get(cat,'');obj=rec;row_time=rec.get('updated_at',when)
                self.record(obj,meta,system,collection,row_time,table)
                scopes[(system,infer_category(collection,system))].add(obj['resource_id'])
            cat=infer_category(table)
            if cat:scopes[(CATEGORY_SYSTEM[cat],cat)]  # Include genuinely empty typed tables.
        # Generic customer_data tables cover account profiles too, including missing rows.
        if any(t.startswith('customer_data_') for t in tables):scopes[('account_service','USER_PROFILE')]
        for (system,cat),resources in scopes.items():
            self.scopes.append(Scope(meta['file_id'],meta['captured_at'],times.get(system,when),system,cat,resources))
        c.close()

    @staticmethod
    def log_fields(line):
        stamp=TIME_RE.search(line)
        if not stamp:return None
        rest=line[stamp.end():].strip()
        if rest.startswith('{'):d=json.loads(rest)
        else:
            # Unwrap escaped cloud-runtime message fields before parsing key-value pairs.
            rest=rest.replace('\\"','"')
            d={m[1]:(m[2] if m[2] is not None else m[3]) for m in re.finditer(r'(\w+)=(?:"([^"]*)"|([^\s|]+))',rest)}
            app=re.match(r'\[\w+\] \[([^]]+)\] \[([^]]+)\] (\w+):',rest)
            pipe=rest.split(' | ')
            syslog=re.match(r'<\d+>1 \S+ (\S+) (\S+) - - ',rest)
            if app:d.update(service=app[1],trace_id=app[2],event=app[3])
            elif len(pipe)>=5:d.update(service=pipe[1],trace_id=pipe[2],event=pipe[3])
            elif syslog:d.update(service=syslog[1],trace_id=syslog[2])
            if 'function' in d:d['service']=d['function'];d['trace_id']=d.get('requestId','')
        d['_time']=stamp[0]
        return d

    def parse_log(self,p,meta):
        traces={}
        for no,line in enumerate(p.read_text().splitlines(),1):
            d=self.log_fields(line)
            if not d:continue
            trace=d.get('trace_id');event=d.get('event','');system=d.get('system') or d.get('service','')
            key=(system,trace)
            if trace:
                if event.endswith('_started'):traces[key]=dict(d)
                context={**traces.get(key,{}),**d}
                traces[key]=context
            else:context=d
            resource=d.get('resource_id')
            if not resource:continue
            cat=state=''
            if event=='record_lookup':
                self.record(d,meta,system,'',d['_time'],f'line {no}');continue
            if event=='profile_lookup_completed':cat='USER_PROFILE';state='ABSENT' if d.get('rows')=='0' else 'PRESENT'
            elif event=='index_query_completed':cat='SEARCH_INDEX_ENTRY';state='ABSENT' if d.get('result')=='miss' else 'PRESENT'
            elif event in {'attachment_pii_scan'}:cat='SUPPORT_ATTACHMENT';state='PRESENT'
            elif event in {'message_pii_scan','message_read','support_ticket_read_completed'}:
                cat='SUPPORT_MESSAGE';state='PRESENT' if event=='message_pii_scan' else 'REDACTED'
                if event=='support_ticket_read_completed' and any(meaningful(d.get(k)) for k in DIRECT_FIELDS):state='PRESENT'
            elif event in {'analytics_identity_scan','analytics_profile_read','analytics_profile_read_completed'}:
                cat='ANALYTICS_PROFILE';state='ANONYMIZED'
                if d.get('direct_identifiers')=='1' or any(meaningful(d.get(k)) for k in DIRECT_FIELDS|REFERENCE_FIELDS):state='PRESENT'
            elif event in {'connector_heartbeat','connector_config_loaded','connector_config_read_completed'}:
                cat='DATA_FLOW';state='ACTIVE' if bool_value(d.get('enabled')) else 'DISABLED'
            elif event in {'restore_candidate_evaluated','restore_authorization_completed','restore_policy_read_completed'}:
                cat='BACKUP_ARCHIVE';state='ACTIVE' if bool_value(d.get('eligible',d.get('restore_allowed'))) else 'BLOCKED'
            elif event in {'export_download_check_completed','export_metadata_read_completed'}:cat='USER_EXPORT';state='PRESENT' if bool_value(d.get('available')) else 'ABSENT'
            elif event in {'audit_record_read_completed'}:cat='SECURITY_AUDIT_LOG';state='PRESENT'
            elif event=='contact_lookup_completed':cat='MARKETING_PROFILE';state='PRESENT'
            elif event=='contact_query_completed':cat='SECONDARY_IDENTIFIER';state='PRESENT' if d.get('rows')!='0' else 'ABSENT'
            if cat:
                if system=='support_replica':system='support_platform'
                self.add(meta,system,resource,cat,state,d['_time'],context,f'line {no}',3)

    def parse_text(self,text,meta):
        for no,line in enumerate(text.splitlines(),1):
            parts=[x.strip() for x in line.lstrip('- ').split('|')]
            if len(parts)==6 and TIME_RE.fullmatch(parts[0]):
                when,system,resource,cat,result,subject=parts
                self.record(dict(resource_id=resource,record_type=cat,result=result,subject_reference=subject),meta,system,'',when,f'line {no}')

    def parse_pdf(self,p,meta):
        from pypdf import PdfReader
        text='\n'.join(page.extract_text() or '' for page in PdfReader(p).pages)
        resources=set(RESOURCE_RE.findall(text))
        for resource in resources:
            if resource.startswith('audit_record_'):cat='SECURITY_AUDIT_LOG'
            elif resource.startswith('support_') and 'Attachment' in text:cat='SUPPORT_ATTACHMENT'
            else:continue
            self.add(meta,CATEGORY_SYSTEM[cat],resource,cat,'PRESENT',meta['captured_at'],text,'PDF extracted text',3)
        # Catalog aliases can identify a business document without an embedded resource ID.
        for resource,a in self.catalog.items():
            aliases=re.findall(r'\(([^)]+)\)',a['details'])
            if a['target_system']=='export_service' and any(alias in text for alias in aliases) and resource not in resources:
                cat=SYSTEM_CATEGORY.get(a['target_system'])
                if cat:self.add(meta,a['target_system'],resource,cat,'PRESENT',meta['captured_at'],text,'PDF catalog alias',3)

    def parse_image(self,p,meta):
        import pytesseract
        from PIL import Image
        self.cache.mkdir(parents=True,exist_ok=True)
        digest=hashlib.sha256(p.read_bytes()).hexdigest()
        cache=self.cache/(digest+'.txt')
        if cache.exists():text=cache.read_text()
        else:
            text=pytesseract.image_to_string(Image.open(p),config='--psm 11')
            cache.write_text(text);self.ocr_calls+=1
        # OCR frequently separates the underscore from its ID; normalize only syntax.
        text=re.sub(r'\b(account|analytics|search|support|export|data_flow|backup|audit_record|tombstone|marketing|object|user)\s*_\s*(\d+)',r'\1_\2',text)
        self.diagnostics.append({'file':meta['file_id'],'ocr_characters':len(text)})
        low=text.casefold();resources=set(RESOURCE_RE.findall(text))
        # Catalog-backed identity is scoped to the selected resource, not to every
        # customer visible elsewhere in a table or sidebar. Catalog availability
        # is part of the observation's provenance and therefore its cutoff.
        for resource,a in self.catalog.items():
            aliases=re.findall(r'\(([^)]+)\)',a['details'])
            visible=resource in resources
            if a['target_system']=='object_storage':
                visible=any(alias in text for alias in aliases)
            if a['target_system']=='identity_service':
                visible=visible or ('reference' in low and any(alias in text for alias in aliases))
            if not visible:continue
            system=a['target_system'];cat=SYSTEM_CATEGORY.get(system)
            if system=='object_storage':cat='SUPPORT_ATTACHMENT'
            if not cat:continue
            if cat=='DATA_FLOW':state='DISABLED' if re.search(r'\bdisabled\b',low) else 'ACTIVE'
            elif cat=='BACKUP_ARCHIVE':state='BLOCKED' if re.search(r'\bblocked\b',low) else 'ACTIVE'
            elif cat=='ACCOUNT_TOMBSTONE':state='PRESENT' if EMAIL_RE.search(text) else 'REDACTED'
            else:state='PRESENT'
            source={**meta,'captured_at':max(meta['captured_at'],a['event_time'])}
            self.add(source,system,resource,cat,state,meta['captured_at'],a['details'],'OCR with catalog identity '+a['activity_id'],1)
