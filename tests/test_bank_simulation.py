"""A full bank simulation (synthetic): a made-up bank's design specifications for A1–A4, its security, network, technology and
design standards and two reference patterns, over a design in all four layers — validated upstream (A4 → A3 → A2 → A1), downstream
(trace and impact) and sidestream (against the standards and patterns), while SDEM's metamodel keeps its structure.

docs/design/sdem-profile-spec.md PR-02, PR-10, PR-13…PR-20; the fixture is tests/fixtures/bank-simulation/ on top of examples/profiles/."""
import datetime, hashlib, json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem import comply, conformance, exceptions, profile  # noqa: E402
from sdem.metamodel import Metamodel  # noqa: E402

AS_OF = datetime.date(2026, 11, 10)
ENV = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', ''), 'SDEM_AS_OF': AS_OF.isoformat()}
FIXTURE = ROOT / 'tests' / 'fixtures' / 'bank-simulation'


def _j(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def _w(p, d): Path(p).write_text(json.dumps(d, indent=2), encoding='utf-8')


def sdem(*args, cwd):
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], capture_output=True, text=True, env=ENV, cwd=cwd)
    return r.returncode, r.stdout + r.stderr


def metamodel_digest():
    h = hashlib.sha256()
    for p in sorted((ROOT / 'metamodel').rglob('*')):
        if p.is_file(): h.update(p.relative_to(ROOT).as_posix().encode()); h.update(p.read_bytes())
    return h.hexdigest()


DESIGN = {   # a complete design, in all four layers, that meets every standard and pattern
    'a1-business.json': {'CAP-PAY-010': {'design_scope': 'in_scope', 'key_decisions': ['KD-B-01 straight-through processing for domestic transfers'],
                                         'design_risks': ['RK-B-01 a cut-off missed at month end']}},
    'a2-service-domain.json': {'SD-PI': {'adoption_scope': 'full', 'deviations': []}},
    'a3-application.json': {'APP-PAY-HUB': {'owner': 'ROLE-PAY-OFFICER', 'risk_tier': '1', 'exposure': 'external', 'authentication': 'oauth2-mtls',
                                            'key_decisions': ['ADR-012 one hub for every payment channel', 'ADR-015 events for status'],
                                            'design_risks': ['RK-A-03 the hub is a single point of change'],
                                            'design_scope': 'initiation, validation and status for domestic credit transfers',
                                            'conforms_to': ['PAT-SECURE-API']},
                            'CMP-PAY-CAPTURE': {'owner': 'ROLE-PAY-OFFICER', 'risk_tier': '2'},
                            'CMP-PAY-VALIDATE': {'owner': 'ROLE-PAY-OFFICER', 'risk_tier': '2'},
                            'CMP-PAY-EXEC': {'owner': 'ROLE-PAY-OFFICER', 'risk_tier': '2'}},
    'a4-technology.json': {'INF-K8S-PAY-PROD': {'environment': 'production', 'dr_tier': '3', 'dr_region': 'region-a', 'replication_mode': 'async',
                                                'network_zone': 'restricted', 'monitoring': True, 'encryption_in_transit': 'tls1.3',
                                                'end_of_support': '2028-06-30', 'key_decisions': ['TD-04 a managed Kubernetes service'],
                                                'design_scope': 'the payments production cluster', 'conforms_to': ['PAT-RESILIENT-PLATFORM']},
                           'INF-K8S-PAY-UAT': {'network_zone': 'restricted', 'monitoring': True, 'encryption_in_transit': 'tls1.3', 'end_of_support': '2028-06-30'},
                           'INF-PG-PAY-PROD': {'end_of_support': '2029-11-30', 'network_zone': 'restricted'}},
}


class Simulation(unittest.TestCase):
    def setUp(self):
        self.addCleanup(profile.deactivate)
        self.digest = metamodel_digest()
        self.tmp = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, self.tmp, True)
        shutil.copytree(ROOT / 'examples' / 'profiles', self.tmp / 'profiles')
        shutil.copytree(FIXTURE / 'profiles', self.tmp / 'profiles', dirs_exist_ok=True)
        self.ws = self.tmp / 'ws'
        shutil.copytree(ROOT / 'examples' / 'payment-initiation', self.ws, ignore=shutil.ignore_patterns('graph', 'm1-*'))
        _w(self.ws / 'sdem-profile.json', {'format': 'sdem-profile/1', 'name': 'payments', 'version': 1, 'extends': '../profiles/bank-design-specs.json'})
        for f, recs in DESIGN.items():
            for rid, kv in recs.items(): self.set(f, rid, **kv)
        a3 = _j(self.ws / 'a3-application.json')   # the bank's API gateway (a profile type) in front of the hub — the secure API pattern's part
        a3['instances'].append({'id': 'GW-PAY-EDGE', 'type': 'BANK.A3.APIGateway', 'version': '1.0', 'name': 'Payments API gateway', 'lifecycle_status': 'active',
                                'description': 'Fronts the payment APIs for external channels.', 'attributes': {'owner': 'ROLE-PAY-OFFICER', 'risk_tier': '2'}})
        a3['relationships'].append({'source': 'GW-PAY-EDGE', 'kind': 'composition', 'target': 'APP-PAY-HUB'})
        _w(self.ws / 'a3-application.json', a3)

    def tearDown(self):
        self.assertEqual(metamodel_digest(), self.digest, "SDEM's metamodel files changed")

    def set(self, f, rid, **kv):
        d = _j(self.ws / f)
        for i in d['instances']:
            if i['id'] == rid:
                for k, v in kv.items():
                    if v is None: i.setdefault('attributes', {}).pop(k, None)
                    else: i.setdefault('attributes', {})[k] = v
        _w(self.ws / f, d)

    def unlink(self, mapping_id, status=None):
        reg = _j(self.ws / 'mappings.json')
        if status: next(m for m in reg['mappings'] if m['mapping_id'] == mapping_id)['status'] = status
        else: reg['mappings'] = [m for m in reg['mappings'] if m['mapping_id'] != mapping_id]
        _w(self.ws / 'mappings.json', reg)

    def report(self): return comply.collect(self.ws, AS_OF)

    def outcome(self, rule, record):
        fs = [f for f in self.report()['findings'] if f['rule'] == rule and f['record'] == record]
        return (fs[0]['outcome'], fs[0]['detail']) if fs else ('not_applicable', '')

    def assertOutcome(self, rule, record, want, detail=None):
        got, why = self.outcome(rule, record)
        self.assertEqual(got, want, f'{rule} on {record}: {why}')
        if detail: self.assertIn(detail, why)


class TheBankDesign(Simulation):
    def test_the_profile_resolves_with_every_layer_specified(self):
        merged = profile.resolve(self.ws / 'sdem-profile.json')
        self.assertEqual(profile.check(merged, Metamodel.base()), [])
        self.assertEqual([x['id'] for x in merged['included']], ['SEC-API', 'NET', 'TECH-LC', 'PAT-SECURE-API', 'DS', 'PAT-RESILIENT-PLATFORM'])
        specified = {a['entity'].split('.')[0] for a in merged['attributes'] if a['name'] in ('key_decisions', 'design_scope', 'adoption_scope', 'deviations')}
        self.assertEqual(specified, {'A1', 'A2', 'A3', 'A4'})

    def test_a_complete_design_meets_every_rule_in_every_layer(self):
        r = self.report()
        bad = [f"{f['rule']} {f['record']}: {f['detail']}" for f in r['findings'] if f['outcome'] in ('non_compliant', 'unresolved')]
        self.assertEqual(bad, [])
        layers = {f['layer'] for f in r['findings'] if f['outcome'] == 'compliant'}
        self.assertEqual(layers, {'A2', 'A3', 'A4'})          # A1 is reached through A2's upstream rule (DS-05)
        met = {(f['rule'], f['record']) for f in r['findings'] if f['outcome'] == 'compliant'}
        for want in [('DS-01', 'APP-PAY-HUB'), ('DS-02', 'INF-K8S-PAY-PROD'), ('DS-03', 'INF-K8S-PAY-PROD'), ('DS-04', 'APP-PAY-HUB'), ('DS-05', 'SD-PI'),
                     ('NET-07', 'APP-PAY-HUB'), ('PAT-SECURE-API-4', 'APP-PAY-HUB'), ('PAT-RES-1', 'INF-K8S-PAY-PROD'), ('PAT-RES-4', 'INF-K8S-PAY-PROD')]:
            self.assertIn(want, met)
        self.assertEqual(sdem('comply', '--workspace', self.ws, cwd=self.tmp)[0], 0)
        code, out = sdem('check', '--workspace', self.ws, cwd=self.tmp)
        self.assertEqual(code, 0, out)


class Upstream(Simulation):
    """A4 → A3 → A2 → A1: each layer's design is held to the approved design of the layer above."""

    def test_a_platform_that_serves_no_approved_application(self):                     # DS-03, A4 → A3
        self.set('a4-technology.json', 'INF-PG-PAY-PROD', environment='production', dr_tier='3', dr_region='region-b', replication_mode='sync',
                 key_decisions=['TD-07 PostgreSQL'], design_scope='payments database', encryption_in_transit='tls1.3')
        self.assertOutcome('DS-03', 'INF-PG-PAY-PROD', 'non_compliant', '0 approved DEPLOYED_ON')

    def test_an_application_whose_service_domain_the_bank_does_not_adopt(self):         # DS-04, A3 → A2
        self.set('a2-service-domain.json', 'SD-PI', adoption_scope='reference_only')
        self.assertOutcome('DS-04', 'APP-PAY-HUB', 'non_compliant', 'SD-PI (REALIZED_BY): adoption_scope')
        self.assertOutcome('DS-05', 'SD-PI', 'not_applicable')

    def test_only_an_approved_link_traces_upstream(self):                                 # DS-04, PR-16
        self.unlink('PAY-106', status='proposed')
        self.assertOutcome('DS-04', 'APP-PAY-HUB', 'non_compliant', '0 approved REALIZED_BY')
        self.unlink('PAY-106')
        self.assertOutcome('DS-04', 'APP-PAY-HUB', 'non_compliant', '0 approved REALIZED_BY')

    def test_a_service_domain_supporting_a_capability_outside_the_scope(self):          # DS-05, A2 → A1
        self.set('a1-business.json', 'CAP-PAY-010', design_scope='future')
        self.assertOutcome('DS-05', 'SD-PI', 'non_compliant', 'CAP-PAY-010 (SUPPORTED_BY): design_scope')
        self.set('a1-business.json', 'CAP-PAY-010', design_scope=None)
        self.assertOutcome('DS-05', 'SD-PI', 'unresolved', 'design_scope of CAP-PAY-010 not known')   # never counted compliant

    def test_a_platform_change_is_found_on_the_application_above_it(self):             # NET-07: an A4 value, an A3 finding
        self.set('a4-technology.json', 'INF-K8S-PAY-UAT', network_zone='dmz')
        self.assertOutcome('NET-07', 'APP-PAY-HUB', 'non_compliant', 'INF-K8S-PAY-UAT (DEPLOYED_ON): network_zone')
        code, out = sdem('comply', '--workspace', self.ws, cwd=self.tmp)
        self.assertEqual(code, 1); self.assertIn('NOT MET    NET-07', out)

    def test_trace_reaches_every_layer_with_and_without_the_profile(self):              # the customisation never changes traceability
        def reach(direction, start):
            code, out = sdem('trace', start, '--direction', direction, '--workspace', self.ws, '--json', cwd=self.tmp)
            self.assertEqual(code, 0, out)
            seen, stack = set(), [json.loads(out)[direction]]
            while stack:
                n = stack.pop(); seen.add(n['id']); stack += [c['node'] for c in n.get('children', [])]
            return seen
        up, down = reach('up', 'INF-K8S-PAY-PROD'), reach('down', 'CAP-PAY-010')
        self.assertTrue({'APP-PAY-HUB', 'SD-PI', 'CAP-PAY-010'} <= up, up)
        self.assertTrue({'SD-PI', 'APP-PAY-HUB', 'INF-K8S-PAY-PROD'} <= down, down)
        (self.ws / 'sdem-profile.json').unlink()
        self.assertEqual((reach('up', 'INF-K8S-PAY-PROD'), reach('down', 'CAP-PAY-010')), (up, down))


class Downstream(Simulation):
    def test_impact_of_rehosting_the_platform_reaches_every_layer(self):
        code, out = sdem('impact', 'INF-K8S-PAY-PROD', '--change', 'rehost', '--workspace', self.ws, '--json', cwd=self.tmp)
        self.assertEqual(code, 0, out)
        hit = {i['id']: (i['level'], i['classification']) for i in json.loads(out)['instances']}
        self.assertEqual(hit['APP-PAY-HUB'], ('A3', 'design_change_required'))
        self.assertEqual(hit['SD-PI'][0], 'A2'); self.assertEqual(hit['CAP-PAY-010'][0], 'A1')

    def test_a_business_decision_flows_down_to_the_application(self):                     # A1 out of scope → A2 → A3
        self.set('a1-business.json', 'CAP-PAY-010', design_scope='out_of_scope')
        self.set('a2-service-domain.json', 'SD-PI', adoption_scope='reference_only')        # what the architect does next
        self.assertOutcome('DS-05', 'SD-PI', 'not_applicable')
        self.assertOutcome('DS-04', 'APP-PAY-HUB', 'non_compliant')                         # the application's design must follow


class Sidestream(Simulation):
    """The same design, against the bank's security, network, technology and design standards and its reference patterns."""

    def test_security_standard_and_the_secure_api_pattern(self):
        self.set('a3-application.json', 'APP-PAY-HUB', authentication=None)
        self.assertOutcome('SEC-API-01', 'APP-PAY-HUB', 'non_compliant', 'missing authentication')
        self.assertOutcome('PAT-SECURE-API-1', 'APP-PAY-HUB', 'non_compliant')

    def test_network_standard_and_the_resilient_platform_pattern(self):
        self.set('a4-technology.json', 'INF-K8S-PAY-PROD', network_zone='dmz', monitoring=False)
        self.assertOutcome('NET-07', 'APP-PAY-HUB', 'non_compliant')
        self.assertOutcome('PAT-RES-2', 'INF-K8S-PAY-PROD', 'non_compliant', 'monitoring')
        self.assertOutcome('PAT-RES-3', 'INF-K8S-PAY-PROD', 'non_compliant', 'network_zone')
        self.assertOutcome('PAT-SECURE-API-4', 'APP-PAY-HUB', 'non_compliant', 'INF-K8S-PAY-PROD (DEPLOYED_ON): monitoring')

    def test_a_pattern_applies_to_the_records_that_say_they_follow_it(self):            # PR-10, PR-17: conforms_to (SDEM's own attribute)
        self.set('a4-technology.json', 'INF-K8S-PAY-PROD', monitoring=False)
        self.assertOutcome('PAT-RES-2', 'INF-K8S-PAY-PROD', 'non_compliant')
        self.set('a4-technology.json', 'INF-K8S-PAY-PROD', conforms_to=['BIAN 14.0'])
        self.assertOutcome('PAT-RES-2', 'INF-K8S-PAY-PROD', 'not_applicable')
        self.assertOutcome('PAT-RES-2', 'INF-K8S-PAY-UAT', 'not_applicable')

    def test_technology_lifecycle_is_a_warning_not_a_block(self):
        self.set('a4-technology.json', 'INF-K8S-PAY-PROD', end_of_support='2027-02-01')
        self.assertOutcome('TECH-LC-01', 'INF-K8S-PAY-PROD', 'non_compliant')
        self.assertEqual(self.report()['blocking'], 0)

    def test_the_design_spec_itself_a_placeholder_is_not_a_decision(self):               # DS-01, PR-20
        self.set('a3-application.json', 'APP-PAY-HUB', key_decisions=['TBD'], design_risks=None)
        self.assertOutcome('DS-01', 'APP-PAY-HUB', 'non_compliant', 'missing key_decisions, design_risks')
        code, out = sdem('check', '--workspace', self.ws, cwd=self.tmp)
        self.assertEqual(code, 1); self.assertIn('DS-01', out)

    def test_a_recorded_deviation_held_by_a_persons_exception(self):                      # PR-18
        self.set('a4-technology.json', 'INF-K8S-PAY-UAT', network_zone='dmz')
        self.set('a3-application.json', 'APP-PAY-HUB', deviations=['UAT stays in the DMZ until the Q1 network migration'])
        exceptions.grant(self.ws, 'NET-07', ['APP-PAY-HUB'], 'UAT stays in the DMZ until the Q1 network migration', '2027-03-31', 'jane.architect', as_of=AS_OF)
        self.assertOutcome('NET-07', 'APP-PAY-HUB', 'exception_approved')
        self.assertEqual(sdem('check', '--workspace', self.ws, cwd=self.tmp)[0], 0)
        self.assertEqual(comply.collect(self.ws, datetime.date(2027, 4, 1))['blocking'], 1)   # the day after it ends, the finding is back


class TheMetamodelHolds(Simulation):
    def test_a_design_spec_value_of_the_wrong_form_is_refused(self):
        self.set('a2-service-domain.json', 'SD-PI', adoption_scope='mostly')
        self.set('a3-application.json', 'APP-PAY-HUB', key_decisions='ADR-012 one hub')
        code, out = sdem('check', '--workspace', self.ws, cwd=self.tmp)
        self.assertEqual(code, 1)
        self.assertIn('adoption_scope', out); self.assertIn('key_decisions', out)

    def test_sdem_s_own_attributes_are_used_never_redefined(self):                       # PR-14: pattern reference is SDEM's conforms_to
        std = self.tmp / 'profiles' / 'standards' / 'example-design-spec.json'; d = _j(std)
        d['attributes'].append({'entity': 'A4.InfrastructureComponent', 'name': 'conforms_to', 'type': 'string'}); _w(std, d)
        issues = profile.check(profile.resolve(self.ws / 'sdem-profile.json'), Metamodel.base())
        self.assertTrue(any("SDEM already defines 'conforms_to'" in i for i in issues), issues)

    def test_the_profile_adds_to_the_metamodel_and_changes_nothing_in_it(self):
        base = Metamodel.base()
        base_attrs, base_common, _ = conformance.model(base=True)
        profile.activate_from(self.ws)
        mm = Metamodel.load()
        for t, e in base.entities.items():                                                    # every SDEM type, as it is
            self.assertEqual(mm.entities[t], e, t)
            self.assertEqual(mm.ancestors(t), base.ancestors(t), t)
        added = set(mm.entities) - set(base.entities)
        self.assertTrue(added)
        for t in added:                                                                       # the bank's types extend SDEM's, in SDEM's layers
            self.assertTrue(any(a in base.entities for a in mm.ancestors(t)), t)
            self.assertIn(mm.level(t), ('A1', 'A2', 'A3', 'A4'))
        for k in ('kinds', 'constraints', 'inheritance'):                                    # no SDEM link changed or removed
            for row in base.relationships[k]: self.assertIn(row, mm.relationships[k], k)
        attrs, common, _ = conformance.model()
        self.assertEqual(common, base_common)
        for ent, defs in base_attrs.items():                                                  # SDEM's attributes kept, the bank's added beside them
            for name, a in defs.items(): self.assertEqual(attrs[ent][name], a, f'{ent}.{name}')
        self.assertIn('key_decisions', attrs['A3.ApplicationComponent']); self.assertIn('adoption_scope', attrs['A2.ServiceDomain'])
        self.assertEqual(Metamodel.base().entities, base.entities)                            # base() is still SDEM's alone


if __name__ == '__main__':
    unittest.main()
