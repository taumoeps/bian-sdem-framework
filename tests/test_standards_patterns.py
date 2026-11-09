"""An organisation's standards, reference-architecture patterns and exceptions (docs/design/sdem-profile-spec.md PR-13…PR-20; the owner's
decisions B1–B6, 2026-11-10) — synthetic: the made-up bank in examples/profiles/."""
import copy, datetime, json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem import comply, exceptions, profile  # noqa: E402
from sdem.metamodel import Metamodel  # noqa: E402

AS_OF = datetime.date(2026, 11, 10)
ENV = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', ''), 'SDEM_AS_OF': AS_OF.isoformat()}


def _j(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def _w(p, d): Path(p).write_text(json.dumps(d, indent=2), encoding='utf-8')


def sdem(*args, cwd):
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], capture_output=True, text=True, env=ENV, cwd=cwd)
    return r.returncode, r.stdout + r.stderr


class Base(unittest.TestCase):
    def setUp(self):
        self.addCleanup(profile.deactivate)
        self.tmp = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, self.tmp, True)
        shutil.copytree(ROOT / 'examples' / 'profiles', self.tmp / 'profiles')
        self.ws = self.tmp / 'ws'
        shutil.copytree(ROOT / 'examples' / 'payment-initiation', self.ws, ignore=shutil.ignore_patterns('graph', 'm1-*'))
        self.team({})
        a3 = _j(self.ws / 'a3-application.json')
        for i in a3['instances']:
            if i['type'] == 'A3.ApplicationComponent': i.setdefault('attributes', {}).update(owner='ROLE-PAY-OFFICER', risk_tier='2')
            if i['id'] == 'APP-PAY-HUB': i['attributes'].update(risk_tier='1', exposure='external', authentication='oauth2-mtls')
        _w(self.ws / 'a3-application.json', a3)
        self.set_a4('INF-K8S-PAY-PROD', environment='production', dr_tier='3', dr_region='region-a', replication_mode='async',
                    network_zone='restricted', monitoring=True, encryption_in_transit='tls1.3')
        self.set_a4('INF-K8S-PAY-UAT', network_zone='restricted', monitoring=True, encryption_in_transit='tls1.3')   # the hub runs there too

    def team(self, extra, base='../profiles/bank-with-standards.json'):
        _w(self.ws / 'sdem-profile.json', {'format': 'sdem-profile/1', 'name': 'payments', 'version': 1, 'extends': base, **extra})

    def set_a4(self, rid, **kv):
        d = _j(self.ws / 'a4-technology.json')
        for i in d['instances']:
            if i['id'] == rid: i.setdefault('attributes', {}).update(kv)
        _w(self.ws / 'a4-technology.json', d)

    def set_a3(self, rid, **kv):
        d = _j(self.ws / 'a3-application.json')
        for i in d['instances']:
            if i['id'] == rid:
                for k, v in kv.items():
                    if k == 'lifecycle_status': i[k] = v
                    elif v is None: i['attributes'].pop(k, None)
                    else: i['attributes'][k] = v
        _w(self.ws / 'a3-application.json', d)

    def findings(self, rule=None, record=None):
        r = comply.collect(self.ws, AS_OF)
        return [f for f in r['findings'] if (rule is None or f['rule'] == rule) and (record is None or f['record'] == record)]

    def outcome(self, rule, record='APP-PAY-HUB'):
        fs = self.findings(rule, record); return fs[0]['outcome'] if fs else 'not_applicable'


class ProfileTests(Base):
    def test_the_example_profile_includes_its_standards_and_pattern(self):        # PR-13, PR-17
        merged = profile.resolve(self.tmp / 'profiles' / 'bank-with-standards.json')
        self.assertEqual(profile.check(merged, Metamodel.base()), [])
        self.assertEqual([x['id'] for x in merged['included']], ['SEC-API', 'NET', 'TECH-LC', 'PAT-SECURE-API'])
        rules = {r['id']: r for r in merged['rules']}
        self.assertEqual(rules['NET-07']['standard']['version'], '2.0'); self.assertEqual(rules['PAT-SECURE-API-1']['pattern']['id'], 'PAT-SECURE-API')
        self.assertEqual(rules['PAT-SECURE-API-1']['require'], ['authentication'])          # the referenced standard rule's content
        self.assertEqual(rules['PAT-SECURE-API-1']['when'], {'exposure': 'external'})       # narrowed to where the pattern applies

    def issues(self, extra):
        self.team(extra)
        return profile.check(profile.resolve(self.ws / 'sdem-profile.json'), Metamodel.base())

    def test_a_team_never_weakens_the_bank(self):                                    # PR-14
        widen = {'entity': 'A3.ApplicationComponent', 'name': 'risk_tier', 'type': 'enum', 'values': ['1', '2', '3', '4']}
        self.assertTrue(any('may not change it' in i for i in self.issues({'attributes': [widen]})))
        self.assertTrue(any('may only narrow' in i for i in self.issues({'attributes': [{**widen, 'narrows': True}]})))
        self.assertTrue(any('id is already used' in i for i in self.issues({'rules': [{'id': 'NET-07', 'entity': 'A3.ApplicationComponent', 'require': ['owner']}]})))
        self.assertTrue(any('no base declares it' in i for i in self.issues({'attributes': [{'entity': 'A3.ApplicationComponent', 'name': 'brand_new', 'type': 'enum', 'values': ['a'], 'narrows': True}]})))
        narrow = {'entity': 'A4.InfrastructureComponent', 'name': 'replication_mode', 'type': 'enum', 'values': ['sync'], 'narrows': True}
        self.assertEqual(self.issues({'attributes': [narrow]}), [])
        merged = profile.resolve(self.ws / 'sdem-profile.json')
        self.assertEqual(next(a for a in merged['attributes'] if a['name'] == 'replication_mode')['values'], ['sync'])

    def test_sdem_s_own_attributes_are_never_redefined(self):                      # PR-02, PR-14 — also what a later SDEM adds
        mine = {'entity': 'A4.SystemSoftware', 'name': 'end_of_support', 'type': 'string', 'required': True}
        self.assertTrue(any("SDEM already defines 'end_of_support'" in i for i in self.issues({'attributes': [mine]})))
        sub = {'entity': 'BANK.A3.APIGateway', 'name': 'owner', 'type': 'string'}            # a common attribute, on a profile subtype
        self.assertTrue(any("SDEM already defines 'owner'" in i for i in self.issues({'attributes': [sub]})))
        std = self.tmp / 'profiles' / 'standards' / 'example-network.json'; d = _j(std)
        d['attributes'].append({'entity': 'A4.SystemSoftware', 'name': 'product_version', 'type': 'string'}); _w(std, d)
        self.assertTrue(any("SDEM already defines 'product_version'" in i for i in self.issues({})))   # inside an included standard too

    def test_rules_are_checked(self):                                                 # PR-15, PR-16, PR-17
        bad_rules = [{'id': 'X-1', 'entity': 'A3.ApplicationComponent', 'check': {'attribute': 'nothing_here', 'op': '==', 'value': 1}},
                     {'id': 'X-2', 'entity': 'A4.SystemSoftware', 'check': {'attribute': 'end_of_support', 'op': 'after', 'value': 'soon'}},
                     {'id': 'X-3', 'entity': 'A3.ApplicationComponent', 'across': {'relationship': 'NOT_A_LINK'}}]
        issues = self.issues({'rules': bad_rules})
        for want in ("checks 'nothing_here'", 'after needs a date', "across 'NOT_A_LINK'"): self.assertTrue(any(want in i for i in issues), (want, issues))
        p = self.tmp / 'profiles' / 'patterns' / 'bad.json'
        _w(p, {'format': 'sdem-pattern/1', 'pattern': {'id': 'P', 'title': 't', 'version': '1', 'owner': 'o', 'applies_when': {'entity': 'A3.ApplicationComponent'}},
               'requires': [{'id': 'P-1', 'rule': 'NO-SUCH-RULE'}]})
        self.assertTrue(any('rule NO-SUCH-RULE is not declared' in i for i in self.issues({'includes': ['../profiles/patterns/bad.json']})))
        _w(p, {'format': 'sdem-pattern/1', 'pattern': {'id': 'P', 'title': 't'}})
        with self.assertRaises(profile.ProfileError): self.issues({'includes': ['../profiles/patterns/bad.json']})


class EvaluationTests(Base):
    def test_comparisons(self):
        t = lambda op, v, have: comply.test({'attribute': 'a', 'op': op, 'value': v}, have, AS_OF)
        self.assertTrue(t('in', ['x', 'y'], 'x')); self.assertFalse(t('not_in', ['x'], 'x')); self.assertTrue(t('<=', 15, 10)); self.assertFalse(t('>', 15, '10'))
        self.assertTrue(t('after', 'today+180d', '2027-06-30')); self.assertFalse(t('after', 'today+180d', '2027-01-01'))
        self.assertTrue(t('before', '2027-01-01', '2026-12-31')); self.assertTrue(t('==', True, True))
        for unknown in (None, 'TBD', '', 'not-a-date'): self.assertIsNone(t('after', 'today', unknown), unknown)
        self.assertEqual(comply.date_of('today-1d', AS_OF), datetime.date(2026, 11, 9))

    def test_a_design_that_meets_every_rule(self):
        self.assertEqual([f for f in self.findings(record='APP-PAY-HUB') if f['outcome'] == 'non_compliant'
                          and not f['rule'].startswith('PAT-SECURE-API-3')], [])   # the gateway is not modelled in the example
        self.assertEqual(self.outcome('NET-07'), 'compliant'); self.assertEqual(self.outcome('SEC-API-02'), 'compliant')

    def test_a_placeholder_does_not_meet_a_rule(self):                                 # PR-20 (the O9 rule, for profile rules)
        self.set_a3('APP-PAY-HUB', authentication='TBD')
        self.assertEqual(self.outcome('SEC-API-01'), 'non_compliant')

    def test_across_follows_only_approved_links(self):                                # PR-16
        self.set_a4('INF-K8S-PAY-PROD', network_zone='internal')
        f = self.findings('NET-07', 'APP-PAY-HUB')[0]
        self.assertEqual(f['outcome'], 'non_compliant'); self.assertIn("INF-K8S-PAY-PROD (DEPLOYED_ON): network_zone is 'internal'", f['detail'])
        reg = _j(self.ws / 'mappings.json')
        for m in reg['mappings']:
            if m['relationship'] == 'DEPLOYED_ON' and m['source']['id'] == 'APP-PAY-HUB': m['status'] = 'proposed'
        _w(self.ws / 'mappings.json', reg)
        self.assertIn('0 approved DEPLOYED_ON link(s)', self.findings('NET-07', 'APP-PAY-HUB')[0]['detail'])   # a proposal is not a fact

    def test_unknown_inferred_and_planned_are_never_compliant(self):
        d = _j(self.ws / 'a4-technology.json')
        for i in d['instances']:
            if i['id'] == 'INF-K8S-PAY-PROD': i['attributes'].pop('monitoring')
        _w(self.ws / 'a4-technology.json', d)
        self.assertEqual(self.outcome('PAT-SECURE-API-4'), 'unresolved')
        self.set_a3('APP-PAY-HUB', inferred={'by': 'sdem aid', 'run': 'AID-001', 'rule': 'x', 'confidence': '0.4'}, lifecycle_status='planned')
        self.assertEqual(self.outcome('SEC-API-02'), 'unresolved')                    # inferred, unconfirmed: unresolved even when it passes
        self.set_a3('APP-PAY-HUB', inferred=None, authentication='api-key')
        self.assertEqual(self.outcome('SEC-API-02'), 'unresolved')                    # a planned design not yet complete

    def test_a_rule_not_yet_effective_is_a_warning(self):                            # PR-15
        std = self.tmp / 'profiles' / 'standards' / 'example-security.json'; d = _j(std); d['standard']['effective_from'] = '2027-01-01'; _w(std, d)
        self.set_a3('APP-PAY-HUB', authentication='api-key')
        f = self.findings('SEC-API-02', 'APP-PAY-HUB')[0]
        self.assertEqual((f['outcome'], f['severity']), ('non_compliant', 'warning')); self.assertIn('not yet effective (from 2027-01-01)', f['detail'])

    def test_sdem_check_enforces_errors_and_reports_warnings(self):
        self.set_a3('APP-PAY-HUB', authentication='api-key'); self.set_a4('INF-K8S-PAY-PROD', network_zone='internal', encryption_in_transit='none')
        code, out = sdem('check', '--workspace', self.ws, cwd=self.tmp)
        self.assertEqual(code, 1, out)
        self.assertIn('SEC-API-02', out); self.assertIn('profile rules across layers: instance APP-PAY-HUB: NET-07', out)
        self.assertTrue(any(l.startswith('WARN') and 'NET-09' in l for l in out.splitlines()), out)   # severity warning: reported, not failing
        self.assertFalse(any(l.startswith('ERROR') and 'NET-09' in l for l in out.splitlines()))

    def test_the_command(self):
        code, out = sdem('comply', '--workspace', self.ws, '--json', cwd=self.tmp)
        r = json.loads(out); self.assertEqual(r['as_of'], AS_OF.isoformat())
        self.assertEqual(code, 1 if r['blocking'] else 0)
        self.assertTrue(any(g['id'] == 'PAT-SECURE-API' and g['kind'] == 'pattern' for g in r['groups']))
        self.set_a3('APP-PAY-HUB', authentication='api-key')
        self.assertEqual(sdem('comply', '--workspace', self.ws, cwd=self.tmp)[0], 1)
        (self.ws / 'sdem-profile.json').unlink()
        code, out = sdem('comply', '--workspace', self.ws, cwd=self.tmp); self.assertEqual(code, 0); self.assertIn('no organisation profile', out)
        (self.tmp / 'empty').mkdir(); self.assertEqual(sdem('comply', '--workspace', self.tmp / 'empty', cwd=self.tmp)[0], 2)


class ExceptionTests(Base):
    def test_a_person_grants_a_time_limited_exception(self):                        # PR-18
        self.set_a4('INF-K8S-PAY-PROD', network_zone='internal')
        args = dict(rule='NET-07', records=['APP-PAY-HUB'], reason='moves in December', expires='2026-12-31', as_of=AS_OF)
        with self.assertRaises(ValueError): exceptions.grant(self.ws, person='sdem-a3-application', **args)
        with self.assertRaises(ValueError): exceptions.grant(self.ws, person='jane.architect', **{**args, 'expires': '2026-11-01'})
        with self.assertRaises(ValueError): exceptions.grant(self.ws, person='jane.architect', **{**args, 'rule': 'NOPE'})
        with self.assertRaises(ValueError): exceptions.grant(self.ws, person='jane.architect', **{**args, 'records': ['NOPE']})
        e, _ = exceptions.grant(self.ws, person='jane.architect', dry_run=True, **args)
        self.assertFalse((self.ws / 'exceptions.json').exists())
        e, gd = exceptions.grant(self.ws, person='jane.architect', **args)
        self.assertEqual((e['id'], gd['kind']), ('EXC-001', 'grant_exception')); self.assertEqual(e['standard'], 'NET')
        f = self.findings('NET-07', 'APP-PAY-HUB')[0]
        self.assertEqual(f['outcome'], 'exception_approved'); self.assertEqual(f['exception']['id'], 'EXC-001')
        code, out = sdem('check', '--workspace', self.ws, cwd=self.tmp); self.assertNotIn('NET-07', out)
        later = comply.collect(self.ws, datetime.date(2027, 1, 1))
        f = next(x for x in later['findings'] if x['rule'] == 'NET-07' and x['record'] == 'APP-PAY-HUB')
        self.assertEqual(f['outcome'], 'non_compliant'); self.assertIn('exception EXC-001 expired on 2026-12-31', f['detail'])
        self.assertEqual([x['state'] for x in exceptions.listing(self.ws, datetime.date(2027, 1, 1))], ['expired'])

    def test_the_handback_shows_what_is_not_met_and_what_is_ending(self):
        from sdem import handback
        self.set_a3('APP-PAY-HUB', authentication='api-key')
        self.set_a4('INF-K8S-PAY-PROD', network_zone='internal')
        exceptions.grant(self.ws, 'NET-07', ['APP-PAY-HUB'], 'moves in December', '2026-11-30', 'jane.architect', as_of=AS_OF)
        old = os.environ.get('SDEM_AS_OF'); os.environ['SDEM_AS_OF'] = AS_OF.isoformat()
        try: h = handback.collect(self.ws)
        finally:
            if old is None: os.environ.pop('SDEM_AS_OF', None)
            else: os.environ['SDEM_AS_OF'] = old
        self.assertGreaterEqual(h['summary']['standards_not_met'], 1); self.assertEqual(h['summary']['exceptions_expiring'], 1)
        self.assertTrue(any('sdem comply' in c for c in h['commands_for_the_person']))


if __name__ == '__main__':
    unittest.main()
