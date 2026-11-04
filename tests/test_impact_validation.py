"""Four-layer impact validation (docs/design/sdem-agent-platform-spec.md §11, AG-V01…AG-V10), on the made-up Payment Initiation
example: an A4 change does not reach downstream implementation until every layer's specialist has assessed the calculated impact and
a person has accepted it and authorised implementation. T1…T12 are the acceptance criteria of the requirement."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem import agents  # noqa: E402

PAY = ROOT / 'examples' / 'payment-initiation'
REHOST = ROOT / '.github' / 'skills' / 'sdem-change-sets' / 'example-a4-rehost.json'
A3REPOINT = ROOT / '.github' / 'skills' / 'sdem-change-sets' / 'example-a3-repoint.json'
AGENT = {'A1': 'sdem-a1-business', 'A2': 'sdem-a2-bian', 'A3': 'sdem-a3-application', 'A4': 'sdem-a4-technology'}
ORCH, P = 'sdem-orchestrator', 'jane.architect'
CE = agents.CoordinationError


def sdem(*args, ok=(0,)):
    env = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], capture_output=True, text=True, env=env)
    data = json.loads(r.stdout) if r.stdout.strip().startswith('{') else None
    assert r.returncode in ok, f'sdem {" ".join(map(str, args))}: exit {r.returncode}\n{r.stdout[-600:]}\n{r.stderr[-600:]}'
    return r.returncode, data


class ImpactValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); self.ws = self.tmp / 'ws'
        shutil.copytree(PAY, self.ws, ignore=shutil.ignore_patterns('graph', 'coordination', 'migrations', 'requirements.json'))   # the workflow alone; requirements: test_requirements_risk.py
        self.e = agents.Estate(self.ws)
        self.e.propose(json.loads(REHOST.read_text()), AGENT['A4'], P)                          # CS-001 → CE-001

    def tearDown(self): shutil.rmtree(self.tmp, ignore_errors=True)

    def assess_as_calculated(self, event='CE-001', skip=()):
        v = self.e.validation(event)
        for l in ('A1', 'A2', 'A3', 'A4'):
            if l in skip: continue
            c = v['layers'][l]['calculated']
            if c['classification'] == 'no_impact':
                self.e.assess(event, l, 'no_impact_confirmed', AGENT[l], P, 'a hosting change does not change this layer', evidence=[f'design_review:{l}'],
                              uncertainty='records without links are not on the changed path' if c['evidence'] == 'incomplete' else '')
            else:
                self.e.assess(event, l, 'impact_confirmed', AGENT[l], P, 'as calculated', evidence=[f'design_review:{l}'])

    def test_t1_the_calculation_and_its_coverage(self):
        ev = self.e.events()[0]
        got = {r['id']: r['classification'] for r in ev['impact']['records']}
        self.assertEqual((got['APP-PAY-HUB'], got['CMP-PAY-EXEC']), ('design_change_required', 'design_change_required'))
        cov = ev['impact']['coverage']
        self.assertEqual({l: cov[l]['result'] for l in cov}, {'A1': 'no_impact_by_rule', 'A2': 'no_impact_by_rule', 'A3': 'impact_detected', 'A4': 'impact_detected'})
        self.assertTrue(all(c['confirmed'] is False for c in cov.values()))                             # detected is never confirmed
        self.assertTrue(all(r.get('rule') for r in ev['impact']['records']))                            # the rule behind every classification
        self.assertEqual(ev['impact']['basis']['rules_version'], json.loads((ROOT / 'metamodel' / 'impact-rules.json').read_text())['$schema_version']
                         if (ROOT / 'metamodel' / 'impact-rules.json').exists() else ev['impact']['basis']['rules_version'])
        self.assertIn('a4-technology.json', ev['impact']['basis']['files'])

    def test_t2_the_orchestrator_opens_all_four_layers(self):
        with self.assertRaises(CE): self.e.request_validation('CE-001', AGENT['A3'], P)            # a layer agent does not open it
        with self.assertRaises(CE): self.e.request_validation('CE-001', ORCH, 'sdem-agent')          # CTL-20
        v, new = self.e.request_validation('CE-001', ORCH, P)
        self.assertTrue(new); self.assertEqual(sorted(v['layers']), ['A1', 'A2', 'A3', 'A4'])         # including the no-impact layers
        self.assertEqual(v['history'][-1]['phase'], 'validation_pending')
        self.assertFalse(self.e.request_validation('CE-001', ORCH, P)[1])                             # idempotent

    def test_t3_each_specialist_assesses_its_own_layer(self):
        self.e.request_validation('CE-001', ORCH, P)
        self.assess_as_calculated()
        v = self.e.validation('CE-001')
        self.assertEqual({l: v['layers'][l]['assessments'][-1]['agent'] for l in v['layers']}, AGENT)
        self.assertEqual(v['history'][-1]['phase'], 'validation_complete')

    def test_t4_a_specialist_disputes_no_impact_with_evidence(self):
        self.e.request_validation('CE-001', ORCH, P)
        with self.assertRaises(CE): self.e.assess('CE-001', 'A2', 'impact_disputed', AGENT['A2'], P, 'r', recommended='design_change_required')   # no evidence
        with self.assertRaises(CE): self.e.assess('CE-001', 'A2', 'impact_disputed', AGENT['A2'], P, 'r', recommended='design_change_required', evidence=['x:y'])   # no records
        self.assess_as_calculated(skip=('A2',))
        self.e.assess('CE-001', 'A2', 'impact_disputed', AGENT['A2'], P, 'the rehost moves the clearing cut-off, which the service domain owns',
                      recommended='design_change_required', evidence=['bian:SD-PI#controls'], records=['SD-PI'], confidence='medium')
        v = self.e.validation('CE-001')
        self.assertEqual(v['history'][-1]['phase'], 'architect_review_required')
        with self.assertRaises(CE): self.e.accept_validation('CE-001', P, 'ok', authorise=True)        # the dispute is decided first
        self.e.accept_validation('CE-001', P, 'A2 owns the cut-off', final={'A2': 'design_change_required'}, resolutions={'A2': 'agreed with the A2 agent'}, authorise=True)
        r = self.e.plan('CE-001', ORCH, P)
        self.assertIn(('A2', ['SD-PI']), [(w['layer'], w['records']) for w in r['work_items']])        # work the engine did not calculate, from the accepted assessment

    def test_t5_missing_links_are_uncertainty_not_confirmation(self):
        reg = json.loads((self.ws / 'mappings.json').read_text())
        reg['mappings'] = [m for m in reg['mappings'] if m['mapping_id'] != 'PAY-106']                 # SD-PI REALIZED_BY APP-PAY-HUB gone
        (self.ws / 'mappings.json').write_text(json.dumps(reg))
        shutil.rmtree(self.ws / 'coordination'); (self.ws / 'a4-technology.json').write_text((PAY / 'a4-technology.json').read_text())
        e = agents.Estate(self.ws); e.propose(json.loads(REHOST.read_text()), AGENT['A4'], P)
        cov = e.events()[0]['impact']['coverage']['A2']
        self.assertFalse(cov['reached']); self.assertEqual(cov['result'], 'evidence_incomplete'); self.assertEqual(cov['evidence'], 'incomplete')
        self.assertNotEqual(cov['result'], 'no_impact_detected')                                      # not reached is not no impact
        self.assertTrue(cov['unmapped_records'])
        e.request_validation('CE-001', ORCH, P)
        with self.assertRaises(CE) as c: e.assess('CE-001', 'A2', 'no_impact_confirmed', AGENT['A2'], P, 'nothing points here', evidence=['bian:SD-PI'])
        self.assertIn('incomplete', str(c.exception))                                                 # a gap cannot be confirmed away silently

    def test_t6_no_implementation_before_acceptance_and_authorisation(self):
        with self.assertRaises(CE) as c: self.e.plan('CE-001', ORCH, P)
        self.assertIn('AG-V08', str(c.exception))
        self.e.request_validation('CE-001', ORCH, P)
        self.assess_as_calculated(skip=('A1',))
        with self.assertRaises(CE): self.e.plan('CE-001', ORCH, P)                                     # an assessment is missing
        with self.assertRaises(CE): self.e.accept_validation('CE-001', P, 'ok')
        self.e.assess('CE-001', 'A1', 'further_investigation_required', AGENT['A1'], P, 'cannot confirm', missing=['VSS-P1 ALIGNED_TO'])
        with self.assertRaises(CE): self.e.plan('CE-001', ORCH, P)                                     # unresolved
        self.e.accept_validation('CE-001', P, 'A1 reviewed', final={'A1': 'review_required'}, resolutions={'A1': 'process owner reviews the cutover'})
        with self.assertRaises(CE): self.e.plan('CE-001', ORCH, P)                                     # accepted, not authorised
        self.e.authorise('CE-001', P)
        self.assertEqual(len(self.e.plan('CE-001', ORCH, P)['work_items']), 2)

    def test_t7_agents_cannot_accept_or_act_as_a_person(self):
        self.e.request_validation('CE-001', ORCH, P)
        with self.assertRaises(CE): self.e.assess('CE-001', 'A2', 'no_impact_confirmed', AGENT['A3'], P, 'r', evidence=['x:y'])   # not its layer (CTL-19)
        with self.assertRaises(CE): self.e.assess('CE-001', 'A2', 'no_impact_confirmed', ORCH, P, 'r', evidence=['x:y'])          # the orchestrator does not assess
        self.assess_as_calculated()
        for who in (AGENT['A3'], ORCH, 'architect', 'sdem-agent'):
            with self.assertRaises(CE): self.e.accept_validation('CE-001', who, 'ok', authorise=True)
        code, d = sdem('events', 'accept', 'CE-001', '--reason', 'ok', '--workspace', self.ws, '--person', AGENT['A2'], '--json', ok=(1,))
        self.assertEqual(d['error']['code'], 'needs_person')
        self.e.accept_validation('CE-001', P, 'ok')
        with self.assertRaises(CE): self.e.authorise('CE-001', ORCH)

    def test_t8_after_acceptance_the_layer_agents_change_their_layer(self):
        self.e.request_validation('CE-001', ORCH, P); self.assess_as_calculated(); self.e.accept_validation('CE-001', P, 'ok', authorise=True)
        work = self.e.plan('CE-001', ORCH, P)['work_items']
        for w in work: self.e.transition(w['id'], 'in_progress', AGENT['A3'], P)
        cs, ev = self.e.propose(json.loads(A3REPOINT.read_text()), AGENT['A3'], P, [w['id'] for w in work])
        self.assertEqual((cs['layer'], ev['round']), ('A3', 2))

    def test_t9_a_follow_on_event_is_validated_again(self):
        self.test_t8_after_acceptance_the_layer_agents_change_their_layer()
        with self.assertRaises(CE) as c: self.e.plan('CE-002', ORCH, P)
        self.assertIn('CE-002 has no impact validation', str(c.exception))
        self.e.request_validation('CE-002', ORCH, P)
        self.assertEqual(self.e.validation('CE-002')['round'], 2)

    def test_t10_events_from_before_validation_stay_readable(self):
        f = self.ws / 'coordination' / 'events' / 'CE-001.json'
        ev = json.loads(f.read_text()); ev['impact'].pop('coverage'); ev['impact'].pop('basis')
        for r in ev['impact']['records']: r.pop('rule', None)
        f.write_text(json.dumps(ev))                                                                   # as v0.9.14 wrote it
        rows = agents.Estate(self.ws).status()
        self.assertEqual(rows[0]['validation'], 'not requested')
        self.assertEqual(sdem('check', '--workspace', self.ws, '--json')[1]['ok'], True)
        v, _ = self.e.request_validation('CE-001', ORCH, P)
        self.assertTrue(v['legacy']); self.assertIn('recomputed', v['calculated']['coverage_source'])
        self.assertNotIn('acceptance', v)                                                              # nothing fabricated
        self.assertEqual(v['layers']['A3']['calculated']['result'], 'impact_detected')

    def test_t11_check_reads_validation_records_and_flags_tampering(self):
        self.e.request_validation('CE-001', ORCH, P); self.assess_as_calculated(); self.e.accept_validation('CE-001', P, 'ok', authorise=True)
        self.assertEqual(sdem('check', '--workspace', self.ws, '--json')[1]['ok'], True)
        f = self.ws / 'coordination' / 'validations' / 'IV-001.json'
        v = json.loads(f.read_text()); v['acceptance']['by'] = ORCH; v['layers']['A2']['assessments'][-1]['agent'] = AGENT['A3']
        f.write_text(json.dumps(v))
        code, d = sdem('check', '--workspace', self.ws, '--json', ok=(1,))
        issues = [x for k, xs in d['report'].items() for x in xs]
        self.assertTrue(any('CTL-21' in x for x in issues)); self.assertTrue(any('CTL-19' in x for x in issues))

    def test_t12_the_cli_shows_everything_behind_the_final_classification(self):
        sdem('events', 'validate', 'CE-001', '--workspace', self.ws, '--agent', ORCH, '--person', P, '--json')
        code, d = sdem('events', 'pending', '--workspace', self.ws, '--layer', 'A2', '--json')
        self.assertEqual([r['layer'] for r in d['pending']], ['A2'])
        for l, how in (('A1', ['--status', 'no_impact_confirmed', '--uncertainty', 'gaps off path']), ('A2', ['--status', 'no_impact_confirmed', '--uncertainty', 'gaps off path']),
                       ('A3', ['--status', 'impact_confirmed', '--record', 'APP-PAY-HUB', 'CMP-PAY-EXEC']), ('A4', ['--status', 'impact_confirmed'])):
            sdem('events', 'assess', 'CE-001', '--layer', l, *how, '--evidence', f'design_review:{l}', '--mapping', 'PAY-108', '--reasoning', 'checked',
                 '--workspace', self.ws, '--agent', AGENT[l], '--person', P, '--json')
        code, d = sdem('work', 'plan', '--event', 'CE-001', '--workspace', self.ws, '--agent', ORCH, '--person', P, '--json', ok=(1,))
        self.assertEqual(d['error']['code'], 'refused'); self.assertIn('AG-V08', d['error']['message'])
        sdem('events', 'accept', 'CE-001', '--reason', 'as assessed', '--authorise', '--workspace', self.ws, '--person', P, '--json')
        code, d = sdem('events', 'show', 'CE-001', '--workspace', self.ws, '--json')
        calc, v = d['calculated_impact'], d['validation']
        self.assertTrue(all(r['rule'] and 'via' in r for r in calc['records']))                       # the rule and the approved path of every record
        self.assertTrue(calc['basis']['approved_links_sha256'])                                       # what the calculation rested on
        self.assertEqual(v['acceptance']['final']['A3'], 'design_change_required'); self.assertEqual(v['acceptance']['by'], P)
        self.assertEqual(d['summary']['phase'], 'implementation_authorised')
        self.assertEqual([h['phase'] for h in v['history']][-2:], ['architect_accepted', 'implementation_authorised'])
        code, d = sdem('work', 'plan', '--event', 'CE-001', '--workspace', self.ws, '--agent', ORCH, '--person', P, '--json')
        self.assertEqual(sorted(w['records'][0] for w in d['work_items']), ['APP-PAY-HUB', 'CMP-PAY-EXEC'])


if __name__ == '__main__':
    unittest.main()
