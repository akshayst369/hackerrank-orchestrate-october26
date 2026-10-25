"""Participant-created regression cases using fictional example.test identities."""
import csv
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
from audit import Auditor
from evidence import EvidenceStore, tokens
from intent import IntentModel
from main import validate

T0='2026-01-01T00:00:00Z'
T1='2026-01-02T00:00:00Z'
T2='2026-01-03T00:00:00Z'
T3='2026-01-04T00:00:00Z'

class AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.intent=IntentModel()

    def fixture(self, evidence, history=None, text='Delete my account and personal data.', cutoff=T2):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        root=Path(temp.name);(root/'evidence').mkdir()
        def csvwrite(name,fields,rows):
            with (root/name).open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
        person=dict(user_id='user_900',name='Fictional Customer',email='new@example.test',phone='+1 202 555 0142',email_hash=hashlib.sha256(b'new@example.test').hexdigest(),updated_at=T0)
        csvwrite('user_identities.csv',list(person),[person])
        csvwrite('user_audit_log.csv',['audit_id','user_id','event_time','field_name','old_value','new_value'],history or [])
        csvwrite('system_activity.csv',['activity_id','event_time','event_type','source_system','target_system','resource_id','reported_result','details'],[])
        rules=[dict(rule_id=str(n),data_category=c,condition='Always',required_action=a) for n,(c,a) in enumerate([('USER_PROFILE','DELETE'),('SEARCH_INDEX_ENTRY','DELETE'),('ANALYTICS_PROFILE','ANONYMIZE'),('ACCOUNT_TOMBSTONE','REDACT'),('SUPPORT_MESSAGE','REDACT'),('SECURITY_AUDIT_LOG','RETAIN'),('BACKUP_ARCHIVE','RETAIN')])]
        csvwrite('deletion_rules.csv',['rule_id','data_category','condition','required_action'],rules)
        manifests=[]
        for n,(when,contents,suffix) in enumerate(evidence,1):
            path=f'evidence/item{n}.{suffix}';(root/path).write_text(contents if isinstance(contents,str) else json.dumps(contents))
            manifests.append(dict(file_id=f'evidence_{n}',file_path=path,origin='custom_fixture',captured_at=when))
        csvwrite('evidence_files.csv',['file_id','file_path','origin','captured_at'],manifests)
        request=dict(case_id='custom',email='new@example.test',requested_at=T0,reported_at=T1,reported_status='COMPLETE',audit_at=cutoff,request_text=text)
        store=EvidenceStore(root,root/'cache');auditor=Auditor(root,store,self.intent)
        result=auditor.audit(request);validate([result],[request],manifests)
        return result,auditor

    def record(self,resource,cat,result,subject='new@example.test',when=T1):
        systems={'USER_PROFILE':'account_service','SEARCH_INDEX_ENTRY':'search_service','ANALYTICS_PROFILE':'analytics_platform','DATA_FLOW':'integration_service','BACKUP_ARCHIVE':'backup_service','SECURITY_AUDIT_LOG':'security_service','ACCOUNT_TOMBSTONE':'identity_service'}
        return dict(resource_id=resource,system=systems[cat],record_type=cat,result=result,subject_reference=subject,recorded_at=when)

    def test_future_capture_cannot_prove_deletion(self):
        old=self.record('account_88','USER_PROFILE','FOUND')
        future=self.record('account_88','USER_PROFILE','NOT_FOUND',when=T1)
        result,_=self.fixture([(T1,{'records':[old]},'json'),(T3,{'records':[future]},'json')])
        self.assertEqual(result['deletion_status'],'INCOMPLETE')
        self.assertEqual(result['steps'][0]['evidence_id'],'evidence_1')

    def test_future_embedded_observation_is_excluded(self):
        old=self.record('account_88','USER_PROFILE','NOT_FOUND')
        future=self.record('account_88','USER_PROFILE','FOUND',when=T3)
        result,_=self.fixture([(T1,{'records':[old,future]},'json')])
        self.assertEqual(result['deletion_status'],'COMPLETE')

    def test_replica_survives_primary_deletion(self):
        sql='''CREATE TABLE customer_profiles_primary (resource_id TEXT, user_id TEXT, email TEXT, updated_at TEXT);
CREATE TABLE customer_profiles_replica (resource_id TEXT, user_id TEXT, email TEXT, updated_at TEXT);
INSERT INTO customer_profiles_replica VALUES ('account_88','user_900','new@example.test','2026-01-02T00:00:00Z');'''
        result,_=self.fixture([(T1,sql,'sql')])
        self.assertEqual(result['deletion_status'],'INCOMPLETE')
        self.assertEqual(result['steps'][0]['operation'],'REPORT_REMAINING_RECORD')

    def test_historical_email_hash_and_similar_address(self):
        history=[dict(audit_id='audit_1',user_id='user_900',event_time=T1,field_name='email',old_value='old@example.test',new_value='new@example.test')]
        hashed=hashlib.sha256(b'old@example.test').hexdigest()
        rows=[self.record('account_88','USER_PROFILE','NOT_FOUND'),self.record('search_51','SEARCH_INDEX_ENTRY','FOUND',hashed),self.record('search_52','SEARCH_INDEX_ENTRY','FOUND','old.jr@example.test')]
        result,_=self.fixture([(T1,{'records':rows},'json')],history=history)
        found=[s['resource_id'] for s in result['steps'] if s['phase']=='FINDING']
        self.assertEqual(found,['search_51'])

    def test_flows_and_restore_blocked_before_record_changes(self):
        rows=[self.record('account_88','USER_PROFILE','FOUND'),self.record('data_flow_55','DATA_FLOW','ACTIVE'),self.record('backup_66','BACKUP_ARCHIVE','ACTIVE'),self.record('audit_record_77','SECURITY_AUDIT_LOG','FOUND','user_900')]
        result,_=self.fixture([(T1,{'records':rows},'json')])
        ops=[s['operation'] for s in result['steps'] if s['phase']=='REMEDIATION']
        self.assertEqual(ops,['DISABLE_DATA_FLOW','BLOCK_RESTORE','DELETE_RECORD'])
        audit=[s for s in result['steps'] if s['resource_id']=='audit_record_77']
        self.assertEqual([s['operation'] for s in audit],['VERIFY_RECORD_PRESENT'])

    def test_tombstone_reference_can_remain(self):
        doc={'snapshots':[{'captured_at':T1,'data_store':'identity_service','collection':'deleted_customer_references','records':[dict(resource_id='tombstone_42',subject_reference='user_900',name=None,email=None,phone=None,email_hash=None)]}],}
        absent={'records':[self.record('account_88','USER_PROFILE','NOT_FOUND')]}
        result,_=self.fixture([(T1,doc,'json'),(T1,absent,'json')])
        self.assertEqual(result['deletion_status'],'COMPLETE')
        self.assertIn('VERIFY_RECORD_REDACTED',[s['operation'] for s in result['steps']])

    def test_exposed_tombstone_is_redacted_not_deleted(self):
        doc={'collection':'deleted_customer_references','captured_at':T1,'records':[dict(resource_id='tombstone_42',subject_reference='user_900',name='Fictional Customer',email='new@example.test',phone=None,email_hash=None)]}
        result,_=self.fixture([(T1,doc,'json')])
        self.assertEqual([s['operation'] for s in result['steps'] if s['phase']=='REMEDIATION'],['REDACT_RECORD'])

    def test_refusal_authorizes_no_actions(self):
        result,_=self.fixture([(T1,{'records':[self.record('account_88','USER_PROFILE','FOUND')]},'json')],text='Send a data export. Do not delete my account.')
        self.assertEqual(result['deletion_status'],'NOT_APPLICABLE');self.assertEqual(result['steps'],[])

    def test_interleaved_traces_do_not_mix_subjects(self):
        lines='\n'.join([
            f'{T1} service=account_service trace_id=a event=profile_lookup_started lookup_key=new@example.test',
            f'{T1} service=account_service trace_id=b event=profile_lookup_started lookup_key=other@example.test',
            f'{T1} service=account_service trace_id=b event=profile_lookup_completed resource_id=account_99 rows=1',
            f'{T1} service=account_service trace_id=a event=profile_lookup_completed resource_id=account_88 rows=0',
        ])
        result,_=self.fixture([(T1,lines,'log')])
        self.assertEqual(result['deletion_status'],'COMPLETE')
        self.assertEqual([s['resource_id'] for s in result['steps']],['account_88'])

    def test_all_log_dialects(self):
        variants=[
            f'{T1} | INFO | account_service | tr-a | profile_lookup_completed | resource_id="account_88" rows="0" correlation_key="new@example.test"',
            f'{T1} [INFO] [account_service] [tr-a] profile_lookup_completed: resource_id="account_88" rows="0" correlation_key="new@example.test"',
            f'{T1} <14>1 node-1 account_service tr-a - - event="profile_lookup_completed" resource_id="account_88" rows="0" correlation_key="new@example.test"',
            f'{T1} '+json.dumps(dict(service='account_service',event='profile_lookup_completed',resource_id='account_88',rows='0',correlation_key='new@example.test')),
        ]
        for line in variants:
            with self.subTest(line=line):
                result,_=self.fixture([(T1,line,'log')]);self.assertEqual(result['deletion_status'],'COMPLETE')

    def test_missing_evidence_never_claims_complete(self):
        result,auditor=self.fixture([(T1,{'records':[]},'json')])
        self.assertEqual(result['deletion_status'],'INCOMPLETE')
        self.assertTrue(auditor.diagnostics[0]['warnings'])

    def test_sql_cannot_attach_a_file(self):
        import sqlite3
        with self.assertRaises(sqlite3.DatabaseError):
            self.fixture([(T1,"ATTACH DATABASE '/tmp/deletion-audit-forbidden.db' AS external;",'sql')])

    def test_multilingual_authorization(self):
        for text in ['Please finish erasing my account.', 'Veuillez supprimer définitivement mon compte.', 'Solicito eliminar mi cuenta.', 'アカウントを削除してください。', '계정을 삭제해 주세요.', 'أرجو حذف حسابي.', 'कृपया मेरा खाता हटा दें।']:
            with self.subTest(text=text):self.assertTrue(self.intent.classify(text)[0])
        for text in ['Please update my email address.', 'Keep my account and stop newsletters.', 'Do not close my account.', 'アカウントを削除しないでください。']:
            with self.subTest(text=text):self.assertFalse(self.intent.classify(text)[0])

if __name__=='__main__':unittest.main()
