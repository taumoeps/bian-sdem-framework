"""Requirements and risk analysis (docs/design/sdem-requirements-risk-spec.md), on the made-up payments example: an A4 platform
change → structural impact → requirements evaluation → risk findings → A1–A4 assessments → the architect's acceptance (residual
risks named) → authorised implementation. S1–S5 are the five infrastructure-to-business scenarios; AT-RR-01…20 the acceptance tests."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem import agents, requirements as R  # noqa: E402

PAY = ROOT / 'examples' / 'payment-initiation'
REHOST = ROOT / '.github' / 'skills' / 'sdem-change-sets' / 'example-a4-rehost.json'
AGENT = {'A1': 'sdem-a1-business', 'A2': 'sdem-a2-bian', 'A3': 'sdem-a3-application', 'A4': 'sdem-a4-technology'}
ORCH, P = 'sdem-orchestrator', 'jane.architect'
CE = agents.CoordinationError


def sdem(*args, ok=(0,)):
    env = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], capture_output=True, text=True, env=env)
    assert r.returncode in ok, f'sdem {" ".join(map(str, args))}: exit {r.returncode}\n{r.stdout[-800:]}\n{r.stderr[-800:]}'
    return r.returncode, (json.loads(r.stdout) if r.stdout.strip().startswith('{') else r.stdout)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); self.ws = self.tmp / 'ws'
        shutil.copytree(PAY, self.ws, ignore=shutil.ignore_patterns('graph', 'coordination', 'migrations'))
        self.e = agents.Estate(self.ws)

    def tearDown(self): shutil.rmtree(self.tmp, ignore_errors=True)

    def plan_change(self):
        return R.evaluate_change(self.ws, 'INF-K8S-PAY-PROD', 'rehost', 'INF-K8S-PAY-PROD2')

    def rehost(self):
        self.e.propose(json.loads(REHOST.read_text()), AGENT['A4'], P)
        return self.e.request_validation('CE-001', ORCH, P)[0]

    def req(self, res, rid): return next(x for x in res['requirements'] if x['requirement'] == rid)
    def findings(self, res, t, rid=None): return [f for f in res['risks'] if f['type'] == t and (rid is None or f.get('requirement') == rid)]

    def assess_all(self, extra_a4=(), a2_missing=()):
        v = self.e.validation('CE-001')
        for l in ('A1', 'A2', 'A3', 'A4'):
            c = v['layers'][l]['calculated']
            if c['classification'] == 'no_impact':
                self.e.assess('CE-001', l, 'no_impact_confirmed', AGENT[l], P, 'no structural change in this layer; requirements reviewed separately',
                              evidence=[f'design_review:{l}'], uncertainty='records without links are not on the changed path', missing=list(a2_missing) if l == 'A2' else [])
            else:
                recs = [r['id'] for r in c['records']] + (list(extra_a4) if l == 'A4' else [])
                self.e.assess('CE-001', l, 'impact_confirmed', AGENT[l], P, 'as calculated', evidence=[f'design_review:{l}'], records=recs)

    def breaches(self): return [f['id'] for f in self.e.validation('CE-001')['analysis']['risks'] if f['type'] == 'confirmed_breach']
    def breaches_of(self, res): return [f['id'] for f in res['risks'] if f['type'] == 'confirmed_breach']


class Scenarios(Base):
    """The five infrastructure-to-business scenarios (S1–S5), each from the A4 rehost of INF-K8S-PAY-PROD to INF-K8S-PAY-PROD2."""

    def test_s1_availability_and_migration_downtime(self):
        res = self.plan_change()
        self.assertEqual(self.req(res, 'REQ-AV-02')['overall'], 'breached')                          # 99.9 % proposed against 99.95 %
        self.assertEqual(self.req(res, 'REQ-AV-02')['current']['result'], 'satisfied')
        self.assertEqual(self.req(res, 'REQ-AV-01')['overall'], 'missing_evidence')                  # the business objective is not shown by the platform's figure
        self.assertTrue(self.findings(res, 'confirmed_breach', 'REQ-AV-02'))
        self.assertTrue(any(f['rule'] == 'RR-AV-01' for f in self.findings(res, 'potential_risk', 'REQ-AV-01')))   # downtime during the migration

    def test_s2_performance_degradation(self):
        res = self.plan_change(); e = self.req(res, 'REQ-PF-01')
        self.assertEqual((e['current']['result'], e['proposed']['result'], e['overall']), ('satisfied', 'not_evaluable', 'missing_evidence'))
        self.assertTrue(self.findings(res, 'missing_evidence', 'REQ-PF-01')); self.assertTrue(self.findings(res, 'potential_risk', 'REQ-PF-01'))

    def test_s3_data_residency_and_compliance(self):
        res = self.plan_change()
        self.assertEqual(self.req(res, 'REQ-RES-02')['proposed']['value'], 'AU'); self.assertEqual(self.req(res, 'REQ-RES-02')['overall'], 'breached')
        self.assertIn('REQ-RES-01', res['obligations'])                                              # the A1 obligation it derives from is exposed
        f = self.findings(res, 'confirmed_breach', 'REQ-RES-02')[0]
        self.assertIn('owner', f['decision'])                                                        # only its owner changes a residency requirement

    def test_s4_real_time_processing_capability(self):
        res = self.plan_change()
        self.assertEqual(self.req(res, 'REQ-RT-02')['overall'], 'breached')                          # no event streaming on the new platform
        rt1 = self.req(res, 'REQ-RT-01')
        self.assertIn('allocated', rt1['in_scope_because']); self.assertEqual(rt1['overall'], 'missing_evidence')
        a2 = [f for f in self.findings(res, 'assumption') if f['layer'] == 'A2']
        self.assertTrue(a2 and 'SD-PE' in a2[0]['records'])                                          # SD-PE has no approved link: an assumption to validate

    def test_s5_disaster_recovery_degradation(self):
        res = self.plan_change()
        self.assertEqual(self.req(res, 'REQ-RC-02')['overall'], 'breached')                          # no second-region replica
        self.assertEqual(self.req(res, 'REQ-RC-01')['current']['result'], 'satisfied')               # 1h against <= 2h, durations compared
        self.assertEqual(self.req(res, 'REQ-RC-01')['overall'], 'missing_evidence')

    def test_end_to_end_a4_change_to_authorised_implementation(self):
        """A4 platform change → structural impact → requirements → risks → A1–A4 assessments → architect → authorised implementation."""
        v = self.rehost()
        self.assertEqual(sorted(self.breaches()), ['RF-BREACH-REQ-AV-02', 'RF-BREACH-REQ-RC-02', 'RF-BREACH-REQ-RES-02', 'RF-BREACH-REQ-RT-02'])
        with self.assertRaises(CE): self.e.plan('CE-001', ORCH, P)
        self.assess_all(extra_a4=['ART-PAYHUB-IMG'], a2_missing=['SD-PE REALIZED_BY CMP-PAY-EXEC'])
        with self.assertRaises(CE) as c: self.e.accept_validation('CE-001', P, 'ok', authorise=True)
        self.assertIn('RR-K04', str(c.exception))
        self.e.accept_validation('CE-001', P, 'rehost accepted with named residual risks', authorise=True,
                                 accept_risks={x: 'temporary, until the provider confirms; owner informed' for x in self.breaches()})
        v = self.e.validation('CE-001')
        self.assertEqual(len(v['acceptance']['accepted_residual_risks']), 4)
        work = self.e.plan('CE-001', ORCH, P)['work_items']
        self.assertEqual(sorted(w['records'][0] for w in work), ['APP-PAY-HUB', 'ART-PAYHUB-IMG', 'CMP-PAY-EXEC'])   # the artifact the A4 agent found


class Acceptance(Base):
    def test_at_rr_01_the_registry_is_checked(self):
        reg = R.load(self.ws); ds = self.e.datasets()
        self.assertEqual(R.check(reg, ds), [])
        bad = json.loads(json.dumps(reg)); bad['requirements'].append(dict(bad['requirements'][0]))
        bad['requirements'][1]['subject'] = 'NOPE'; bad['requirements'][2]['history'][-1]['version'] = 9
        issues = R.check(bad, ds)
        self.assertTrue(any('defined twice' in i for i in issues)); self.assertTrue(any('NOPE' in i for i in issues)); self.assertTrue(any('history ends' in i for i in issues))
        self.assertEqual(sdem('check', '--workspace', self.ws, '--json')[1]['ok'], True)

    def test_at_rr_02_requirements_are_governed(self):
        f = self.tmp / 'r.json'
        f.write_text(json.dumps({'id': 'REQ-SEC-01', 'name': 'Encrypted at rest', 'statement': 'Payment data is encrypted at rest.', 'owner_layer': 'A4', 'category': 'security',
                                 'scope': 'component', 'subject': 'INF-PG-PAY-PROD', 'condition': {'metric': 'encrypted_at_rest', 'operator': '==', 'value': True}, 'evidence': ['policy:SEC-7']}))
        sdem('requirements', 'propose', f, '--workspace', self.ws, '--person', P, '--agent', AGENT['A4'], '--json')
        r = next(x for x in R.load(self.ws)['requirements'] if x['id'] == 'REQ-SEC-01')
        self.assertEqual((r['version'], r['status'], r['provenance']['by']), (1, 'proposed', f"{AGENT['A4']} for {P}"))
        code, d = sdem('requirements', 'confirm', 'REQ-SEC-01', '--workspace', self.ws, '--person', AGENT['A4'], '--json', ok=(1,))
        self.assertEqual(d['error']['code'], 'needs_person')                                          # an agent never confirms
        sdem('requirements', 'confirm', 'REQ-SEC-01', '--workspace', self.ws, '--person', P, '--json')
        sdem('requirements', 'propose', f, '--workspace', self.ws, '--person', P, '--json')            # a new version starts proposed again
        r = next(x for x in R.load(self.ws)['requirements'] if x['id'] == 'REQ-SEC-01')
        self.assertEqual((r['version'], r['status'], [h['status'] for h in r['history']]), (2, 'proposed', ['proposed', 'confirmed', 'proposed']))

    def test_loading_a_registry_through_governed_commands(self):   # RR-D03: bulk, yet every requirement proposed and confirmed by a person
        src = R.load(self.ws); (self.ws / 'requirements.json').unlink()
        f, mf = self.tmp / 'reqs.json', self.tmp / 'meas.json'
        f.write_text(json.dumps({'requirements': src['requirements']})); mf.write_text(json.dumps({'measurements': src['measurements']}))
        sdem('requirements', 'propose', f, '--workspace', self.ws, '--person', P, '--json')
        reg = R.load(self.ws)
        self.assertEqual({r['status'] for r in reg['requirements']}, {'proposed'})                   # whatever the file said
        self.assertTrue(all(r['provenance']['by'] == P and len(r['history']) == 1 for r in reg['requirements']))
        ids = [r['id'] for r in reg['requirements'] if r['id'] != 'REQ-CAP-01']
        sdem('requirements', 'confirm', *ids, '--workspace', self.ws, '--person', P, '--json')
        sdem('requirements', 'measure', '--from', mf, '--workspace', self.ws, '--person', P, '--json')
        reg = R.load(self.ws)
        self.assertEqual(len(reg['measurements']), len(src['measurements'])); self.assertTrue(all(m['provenance']['by'] == P for m in reg['measurements']))
        self.assertEqual(sorted(self.breaches_of(self.plan_change())), ['RF-BREACH-REQ-AV-02', 'RF-BREACH-REQ-RC-02', 'RF-BREACH-REQ-RES-02', 'RF-BREACH-REQ-RT-02'])

    def test_assessments_made_before_the_analysis_must_be_redone(self):   # a v0.10.0 validation: assessments carry no evidence checksum
        self.rehost(); self.assess_all()
        f = self.ws / 'coordination' / 'validations' / 'IV-001.json'; v = json.loads(f.read_text())
        for l in v['layers'].values():
            for x in l['assessments']: x.pop('inputs_sha256', None); x.pop('additional_records', None)
        v.pop('analysis'); f.write_text(json.dumps(v))
        self.e.analyse('CE-001', ORCH, P)
        code, d = sdem('events', 'show', 'CE-001', '--workspace', self.ws, '--json')
        self.assertTrue(all(r['stale'] for r in d['summary']['layers'].values()))
        with self.assertRaises(CE) as c: self.e.accept_validation('CE-001', P, 'ok', authorise=True, accept_risks={x: 'r' for x in self.breaches()})
        self.assertIn('before the requirements and risk analysis existed', str(c.exception))

    def test_at_rr_03_traceability_across_layers(self):
        code, d = sdem('requirements', 'trace', 'REQ-AV-02', '--workspace', self.ws, '--json')
        self.assertEqual(d['derived_from'], ['REQ-AV-01'])
        served = {n['id'] for n in d['records']['INF-K8S-PAY-PROD']['serves']}
        self.assertTrue({'APP-PAY-HUB', 'SD-PI', 'PRC-PAY-01'} <= served)                             # A4 → A3 → A2 → A1
        a1 = json.loads((self.ws / 'a1-business.json').read_text())                                  # an existing A1.BusinessRequirement as the source
        a1['instances'].append({'id': 'BREQ-PAY-01', 'type': 'A1.BusinessRequirement', 'version': '1', 'name': 'Always-on payments', 'lifecycle_status': 'active'})
        (self.ws / 'a1-business.json').write_text(json.dumps(a1))
        reg = R.load(self.ws); next(x for x in reg['requirements'] if x['id'] == 'REQ-AV-01')['derived_from'] = ['BREQ-PAY-01']
        self.assertEqual(R.check(reg, self.e.datasets()), [])
        R.save(self.ws, reg)
        self.assertIn('BREQ-PAY-01', self.plan_change()['obligations'])

    def test_at_rr_04_scope_says_why(self):
        reg = R.load(self.ws); next(x for x in reg['requirements'] if x['id'] == 'REQ-RES-01')['subject'] = 'VSS-P1'   # a subject the change does not reach
        next(x for x in reg['requirements'] if x['id'] == 'REQ-RES-01')['allocated_to'] = []; R.save(self.ws, reg)
        why = {e['requirement']: e['in_scope_because'] for e in self.plan_change()['requirements']}
        self.assertIn('subject INF-K8S-PAY-PROD is changed', why['REQ-AV-02']); self.assertIn('subject PRC-PAY-01 is affected', why['REQ-AV-01'])
        self.assertIn('allocated to', why['REQ-RT-01']); self.assertIn('REQ-RES-02 is derived from it', why['REQ-RES-01'])   # traceability upward

    def test_at_rr_05_an_allocated_figure_never_satisfies_an_end_to_end_requirement(self):
        e = self.req(self.plan_change(), 'REQ-AV-01')
        self.assertEqual(e['current']['result'], 'not_evaluable')
        self.assertTrue(any('do not establish this end-to-end requirement' in n for n in e['notes']))

    def test_at_rr_06_comparisons_are_exact(self):
        m = lambda v, u=None: {'value': v, **({'unit': u} if u else {})}
        self.assertTrue(R.compare({'operator': '<=', 'value': '2h'}, m('1h')))
        self.assertFalse(R.compare({'operator': '<=', 'value': 300, 'unit': 'ms'}, m(0.5, 's')))      # 500 ms
        self.assertTrue(R.compare({'operator': 'in', 'value': ['NZ']}, m('NZ'))); self.assertFalse(R.compare({'operator': 'in', 'value': ['NZ']}, m('AU')))
        self.assertIsNone(R.compare({'operator': '>=', 'value': 99.95, 'unit': '%'}, m(3, 'ms')))     # different units: no guess
        self.assertFalse(R.compare({'operator': '==', 'value': True}, m(False)))

    def test_at_rr_07_the_proposed_architecture_comes_from_the_change_set(self):
        self.rehost()
        an = self.e.validation('CE-001')['analysis']
        self.assertEqual(an['substitution'].get('INF-K8S-PAY-PROD'), 'INF-K8S-PAY-PROD2')
        self.assertEqual(self.req(an, 'REQ-AV-02')['proposed_subject'], 'INF-K8S-PAY-PROD2')

    def test_at_rr_08_no_registry_is_not_satisfied(self):
        (self.ws / 'requirements.json').unlink()
        res = self.plan_change()
        self.assertEqual(res['registry'], 'missing')
        self.assertEqual({x['status'] for x in res['layers'].values()}, {'requirements_registry_missing'})
        self.assertTrue(self.findings(res, 'missing_evidence'))
        code, d = sdem('requirements', 'list', '--workspace', self.ws, '--json', ok=(1, 2))
        self.assertIn('not evidence that none apply', d['error']['message'])

    def test_at_rr_09_a_reached_layer_without_requirements_is_flagged(self):
        reg = R.load(self.ws); reg['requirements'] = [r for r in reg['requirements'] if r['owner_layer'] != 'A2']; R.save(self.ws, reg)
        res = self.plan_change()
        self.assertEqual(res['layers']['A2']['status'], 'no_requirements_recorded')
        self.assertTrue(any(f['layer'] == 'A2' and f['type'] == 'missing_evidence' for f in res['risks']))

    def test_at_rr_10_unconfirmed_requirements_are_not_obligations(self):
        res = self.plan_change()
        self.assertEqual(self.req(res, 'REQ-CAP-01')['overall'], 'not_confirmed')
        self.assertFalse([f for f in res['risks'] if f.get('requirement') == 'REQ-CAP-01'])

    def test_at_rr_11_findings_invent_nothing(self):
        res = self.plan_change()
        self.assertTrue(all(f['type'] in R.FINDING_TYPES for f in res['risks']))
        banned = {'likelihood', 'probability', 'loss', 'score', 'impact_value', 'severity'}
        self.assertFalse(banned & {k for f in res['risks'] for k in f})
        rules = json.loads((ROOT / 'schema' / 'risk-rules.json').read_text())
        self.assertFalse(banned & {k for r in rules['rules'] for k in r})

    def test_at_rr_12_a_breach_carries_its_evidence_rule_and_decision(self):
        f = self.findings(self.plan_change(), 'confirmed_breach', 'REQ-RC-02')[0]
        self.assertEqual(f['rule'], 'RR-RC-01'); self.assertTrue(f['decision']); self.assertTrue(f['mitigations'])
        self.assertIn('MEAS-010', f['evidence'])

    def test_at_rr_13_incomplete_links_are_assumptions(self):
        a = self.findings(self.plan_change(), 'assumption')
        self.assertEqual(sorted(f['layer'] for f in a), ['A1', 'A2', 'A3', 'A4'])

    def test_at_rr_14_the_analysis_lives_in_the_validation_record(self):
        v = self.rehost()
        self.assertEqual(v['analysis']['registry'], 'present'); self.assertTrue(v['analysis']['risks'])
        v2 = self.e.analyse('CE-001', ORCH, P)
        self.assertEqual(len(v2['analysis_history']), 1); self.assertEqual(v2['analysis']['by']['agent'], ORCH)
        self.assertEqual(sdem('check', '--workspace', self.ws, '--json')[1]['ok'], True)

    def test_at_rr_15_a_stale_assessment_needs_revalidation(self):
        self.rehost(); self.assess_all()
        sdem('requirements', 'measure', '--record', 'APP-PAY-HUB', '--metric', 'p95_latency', '--value', '240', '--unit', 'ms', '--state', 'proposed',
             '--evidence', 'performance_test:PT-PAYHUB-PROD2', '--workspace', self.ws, '--person', P, '--agent', AGENT['A3'], '--json')
        with self.assertRaises(CE) as c: self.e.accept_validation('CE-001', P, 'ok', authorise=True, accept_risks={x: 'r' for x in self.breaches()})
        self.assertIn('changed since the analysis', str(c.exception))
        before = set(self.breaches())
        self.e.analyse('CE-001', ORCH, P)
        self.assertEqual(self.req(self.e.validation('CE-001')['analysis'], 'REQ-PF-01')['overall'], 'satisfied')   # the new evidence counts
        self.assertEqual(set(self.breaches()), before)                                               # finding ids are stable across re-analysis
        code, d = sdem('events', 'show', 'CE-001', '--workspace', self.ws, '--json')
        self.assertTrue(all(r['stale'] for r in d['summary']['layers'].values()))
        with self.assertRaises(CE) as c: self.e.accept_validation('CE-001', P, 'ok', authorise=True, accept_risks={x: 'r' for x in self.breaches()})
        self.assertIn('re-assess', str(c.exception))
        self.assess_all()
        self.e.accept_validation('CE-001', P, 'ok', authorise=True, accept_risks={x: 'r' for x in self.breaches()})

    def test_at_rr_16_breaches_are_decided_by_a_person(self):
        self.rehost(); self.assess_all()
        with self.assertRaises(CE): self.e.accept_validation('CE-001', P, 'ok', authorise=True, accept_risks={self.breaches()[0]: 'r'})   # not all
        with self.assertRaises(CE): self.e.accept_validation('CE-001', AGENT['A4'], 'ok', authorise=True, accept_risks={x: 'r' for x in self.breaches()})
        code, d = sdem('events', 'accept', 'CE-001', '--reason', 'ok', '--authorise', '--accept-risk', *[f'{x}=temporary' for x in self.breaches()],
                       '--workspace', self.ws, '--person', P, '--json')
        acc = self.e.validation('CE-001')['acceptance']
        self.assertEqual({x['finding'] for x in acc['accepted_residual_risks']}, set(self.breaches()))
        self.assertTrue(all(x['by'] == P for x in acc['accepted_residual_risks']))
        self.assertIn('potential_risk', acc['findings_acknowledged'])

    def test_at_rr_17_a_change_after_acceptance_voids_it(self):
        self.rehost(); self.assess_all()
        self.e.accept_validation('CE-001', P, 'ok', authorise=True, accept_risks={x: 'r' for x in self.breaches()})
        reg = R.load(self.ws); reg['requirements'][0]['statement'] += ' (edited)'; R.save(self.ws, reg)
        with self.assertRaises(CE) as c: self.e.plan('CE-001', ORCH, P)
        self.assertIn('changed after', str(c.exception))

    def test_at_rr_18_additional_records_stay_visible_and_actionable(self):
        v = self.rehost()
        self.assertIn('ART-PAYHUB-IMG', v['layers']['A4']['calculated']['related_within_layer'])    # linked inside A4, not followed by the rules
        self.assess_all(extra_a4=['ART-PAYHUB-IMG'], a2_missing=['SD-PE REALIZED_BY CMP-PAY-EXEC'])
        code, d = sdem('events', 'show', 'CE-001', '--workspace', self.ws, '--json')
        self.assertEqual(d['summary']['layers']['A4']['additional_records'], ['ART-PAYHUB-IMG'])
        self.assertEqual(d['summary']['layers']['A4']['assessment'], 'impact_confirmed')              # agreeing, yet naming more
        self.assertEqual(d['summary']['layers']['A2']['missing_relationships'], ['SD-PE REALIZED_BY CMP-PAY-EXEC'])

    def test_at_rr_19_no_downstream_change_before_authorisation(self):
        self.rehost()
        a3 = json.loads((ROOT / '.github' / 'skills' / 'sdem-change-sets' / 'example-a3-repoint.json').read_text())
        with self.assertRaises(CE) as c: self.e.propose(a3, AGENT['A3'], P)                          # no work item: refused
        self.assertIn('not yet accepted and authorised', str(c.exception))
        cs, _ = self.e.propose(a3, 'architect', P)                                                   # a person may still make an initial change, on record
        self.assertEqual(cs['trigger'], 'initial')

    def test_at_rr_20_the_infrastructure_architect_sees_everything(self):
        """The final criterion: one command answers every question an infrastructure architect has before changing a platform."""
        code, d = sdem('requirements', 'evaluate', '--workspace', self.ws, '--record', 'INF-K8S-PAY-PROD', '--change', 'rehost', '--proposed', 'INF-K8S-PAY-PROD2', '--json')
        cov = d['coverage']
        self.assertTrue([r for r in cov['A3']['records']])                                           # dependent A3 applications
        self.assertTrue([r for r in cov['A2']['records']])                                           # related A2 service domains
        self.assertTrue(d['obligations'])                                                             # A1 obligations
        self.assertTrue(d['requirements'])                                                            # requirements to keep meeting
        self.assertTrue([f for f in d['risks'] if f['type'] == 'confirmed_breach'])
        self.assertTrue([f for f in d['risks'] if f['type'] == 'potential_risk'])
        self.assertTrue([f for f in d['risks'] if f['type'] in ('missing_evidence', 'assumption')])   # missing evidence, incomplete links
        self.assertTrue(all(f.get('decision') for f in d['risks']))                                    # decisions to make
        self.assertEqual(cov['A1']['result'], 'no_impact_by_rule')
        self.assertNotEqual(d['layers']['A1']['status'], 'satisfied')                                  # no structural change is never no risk
        self.rehost(); self.assess_all()
        self.e.accept_validation('CE-001', P, 'ok', authorise=True, accept_risks={x: 'r' for x in self.breaches()})
        code, d = sdem('events', 'show', 'CE-001', '--workspace', self.ws, '--json')
        self.assertEqual(d['summary']['phase'], 'implementation_authorised')                          # assessments, acceptance, readiness
        acc = d['validation']['acceptance']
        self.assertEqual(acc['identity']['named_person'], P); self.assertIn('not authenticated', acc['identity']['note'])


if __name__ == '__main__':
    unittest.main()
