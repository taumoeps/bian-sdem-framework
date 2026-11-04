"""The layer registry (docs/design/sdem-layers-spec.md, LR-01…LR-10): a profile adds layers above A1 or below A4, each with its
own file, types and link types to its neighbour; every command works across them. Synthetic data only."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem import profile as P  # noqa: E402

ENV = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}


def sdem(*args, cwd, ok=(0,)):
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], cwd=cwd, capture_output=True, text=True, env=ENV)
    assert r.returncode in ok, f'sdem {" ".join(map(str, args))}: exit {r.returncode}\n{r.stdout[-1200:]}\n{r.stderr[-1200:]}'
    return r.returncode, r.stdout + r.stderr, (json.loads(r.stdout) if r.stdout.strip().startswith('{') else None)


A0 = {'layer': 'A0', 'reason': 'strategy for faster payments', 'changes': [
    {'op': 'add', 'record': {'id': 'GOAL-01', 'type': 'BANK.A0.Goal', 'version': '1', 'name': 'Customers pay instantly', 'lifecycle_status': 'active'}},
    {'op': 'add', 'record': {'id': 'OUT-01', 'type': 'BANK.A0.Outcome', 'version': '1', 'name': '95% of payments settled in 10 seconds', 'lifecycle_status': 'active'}}],
    'relationships': {'add': [{'source': 'OUT-01', 'kind': 'realization', 'target': 'GOAL-01'}]}}
A5 = {'layer': 'A5', 'reason': 'data centres', 'changes': [
    {'op': 'add', 'record': {'id': 'FAC-DC1', 'type': 'BANK.A5.Facility', 'version': '1', 'name': 'Data centre 1', 'lifecycle_status': 'active', 'attributes': {'region': 'region-a'}}},
    {'op': 'add', 'record': {'id': 'EQP-RACK7', 'type': 'BANK.A5.Equipment', 'version': '1', 'name': 'Rack 7', 'lifecycle_status': 'active'}}],
    'relationships': {'add': [{'source': 'FAC-DC1', 'kind': 'composition', 'target': 'EQP-RACK7'}]}}


class LayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """The synthetic payments example, under the strategy-and-sites profile (A0 above, A5 below), with records and links in both."""
        cls.tmp = Path(tempfile.mkdtemp()); t = cls.tmp; ws = cls.ws = t / 'ex'
        sdem('profile', 'example', '--out', t / 'profiles', cwd=t)
        sdem('new', '--workspace', ws, '--person', 'steven', '--example', 'payment-initiation', cwd=t)
        doc = json.loads((t / 'profiles' / 'strategy-and-sites-team.json').read_text()); doc['extends'] = '../profiles/bank-base.json'
        (ws / 'sdem-profile.json').write_text(json.dumps(doc))
        _, _, cls.adopted = sdem('profile', 'adopt', '--workspace', ws, '--person', 'steven', '--reason', 'team standard', '--json', cwd=t)
        f = ws / 'a3-application.json'; d = json.loads(f.read_text())
        for i in d['instances']:
            if i['type'] == 'A3.ApplicationComponent': i.setdefault('attributes', {}).setdefault('owner', 'ROLE-PAY-OFFICER'); i['attributes'].setdefault('risk_tier', '2')
        f.write_text(json.dumps(d))
        sdem('change', 'adopt', '--workspace', ws, '--layer', 'A3', '--person', 'steven', '--reason', 'bank risk tiers', cwd=t)
        for name, cs, agent in (('a0.json', A0, 'sdem-layer-a0'), ('a5.json', A5, 'sdem-layer-a5')):
            (t / name).write_text(json.dumps(cs)); sdem('change', 'propose', t / name, '--workspace', ws, '--agent', agent, '--person', 'steven', cwd=t)
        sdem('connect', 'OUT-01', 'REALIZED_BY', 'CAP-PAY-010', '--workspace', ws, '--person', 'steven', '--evidence', 'strategy_document:STRAT-2027#3', '--rationale', 'the capability delivers it', cwd=t)
        sdem('connect', 'INF-K8S-PAY-PROD', 'HOUSED_IN', 'FAC-DC1', '--workspace', ws, '--person', 'steven', '--evidence', 'site_register:SR-DC1', '--rationale', 'the cluster runs in DC1', cwd=t)
        sdem('build', '--workspace', ws, '--out', ws / 'graph', cwd=t)

    @classmethod
    def tearDownClass(cls): P.deactivate(); shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_adopting_a_profile_adds_its_layers_on_record(self):  # LR-03
        self.assertEqual(self.adopted['layers_added'], ['a0-strategy.json', 'a5-physical.json'])
        gd = json.loads((self.ws / 'decisions' / f"{self.adopted['decision']}.json").read_text()); self.assertEqual(gd['kind'], 'adopt_profile')
        _, out, d = sdem('check', '--workspace', self.ws, '--require-recorded', '--json', cwd=self.tmp)
        self.assertTrue(d['ok']); self.assertEqual(d['unrecorded_edits'], [])                         # the new files are in the ledger

    def test_a_new_workspace_starts_with_every_layer(self):  # LR-03
        nw = self.tmp / 'nw'
        _, out, _ = sdem('new', '--workspace', nw, '--person', 'steven', '--profile', self.tmp / 'profiles' / 'strategy-and-sites-team.json', cwd=self.tmp)
        self.assertIn('all 6 layers empty', out)
        for f in ('a0-strategy.json', 'a5-physical.json'): self.assertEqual(json.loads((nw / f).read_text())['instances'], [])
        self.assertEqual(json.loads((nw / 'sdem-profile.json').read_text())['extends'], '../profiles/bank-base.json')   # the base is still found
        self.assertEqual(sdem('check', '--workspace', nw, '--require-recorded', cwd=self.tmp)[0], 0)

    def test_trace_runs_through_every_layer(self):  # LR-04, LR-09
        _, out, _ = sdem('trace', 'OUT-01', '--direction', 'down', '--graph', self.ws / 'graph', cwd=self.tmp)
        for rid in ('CAP-PAY-010', 'SD-PI', 'APP-PAY-HUB', 'INF-K8S-PAY-PROD', 'FAC-DC1'): self.assertIn(rid, out)   # A0 → A1 → A2 → A3 → A4 → A5
        self.assertIn('[A0 Strategy · Outcome (BANK)]', out); self.assertIn('[A5 Physical · Facility (BANK)]', out)
        _, _, d = sdem('trace', 'A5', '--direction', 'up', '--graph', self.ws / 'graph', '--json', cwd=self.tmp)
        self.assertTrue(d['items'])
        self.assertTrue((self.ws / 'graph' / 'a5.graph.json').exists())                               # LR-05: one graph file per layer

    def test_impact_reaches_every_layer(self):  # LR-04, LR-07
        _, _, d = sdem('impact', 'FAC-DC1', '--change', 'retire', '--graph', self.ws / 'graph', '--json', cwd=self.tmp)
        self.assertEqual(list(d['coverage']), ['A0', 'A1', 'A2', 'A3', 'A4', 'A5'])
        self.assertEqual(d['coverage']['A0']['result'], 'impact_detected')                            # retiring a data centre reaches the strategy outcome

    def test_each_layer_has_its_own_agent_and_validation(self):  # LR-07, CTL-19
        (self.tmp / 'r.json').write_text(json.dumps({'layer': 'A5', 'reason': 'DC1 closes', 'changes': [{'op': 'retire', 'kind': 'retire', 'record': {**A5['changes'][0]['record'], 'lifecycle_status': 'retired'}}]}))
        code, out, _ = sdem('change', 'propose', self.tmp / 'r.json', '--workspace', self.ws, '--agent', 'sdem-a3-application', '--person', 'steven', cwd=self.tmp, ok=(1, 2))
        self.assertIn('CTL-19: agent sdem-a3-application may change only A3, not A5', out)
        sdem('change', 'propose', self.tmp / 'r.json', '--workspace', self.ws, '--agent', 'sdem-layer-a5', '--person', 'steven', cwd=self.tmp)
        ev = sorted(p.stem for p in (self.ws / 'coordination' / 'events').glob('CE-*.json'))[-1]
        _, out, _ = sdem('events', 'validate', ev, '--workspace', self.ws, '--agent', 'sdem-orchestrator', '--person', 'steven', cwd=self.tmp)
        for l in ('A0', 'A1', 'A2', 'A3', 'A4', 'A5'): self.assertIn(f'  {l}  calculated', out)
        sdem('events', 'assess', ev, '--layer', 'A0', '--status', 'impact_confirmed', '--reasoning', 'the outcome depends on DC1', '--workspace', self.ws, '--agent', 'sdem-layer-a0', '--person', 'steven', cwd=self.tmp)
        code, out, _ = sdem('events', 'assess', ev, '--layer', 'A0', '--status', 'impact_confirmed', '--reasoning', 'x', '--workspace', self.ws, '--agent', 'sdem-layer-a5', '--person', 'steven', cwd=self.tmp, ok=(1, 2))
        self.assertIn('CTL-19: agent sdem-layer-a5 may assess only A5, not A0', out)

    def test_a_requirement_can_sit_on_a_profile_layer(self):  # LR-08
        f = self.ws / 'requirements.json'; reg = json.loads(f.read_text()); saved = f.read_bytes()   # restored byte for byte (write_text would change line endings on Windows)
        r = json.loads(json.dumps(reg['requirements'][0]))
        r.update(id='REQ-SITE-01', name='Data centre power resilience', owner_layer='A5', subject='FAC-DC1', allocated_to=[], derived_from=[], category='recovery', scope='component')
        reg['requirements'].append(r); f.write_text(json.dumps(reg))
        try:
            _, out, _ = sdem('check', '--workspace', self.ws, cwd=self.tmp)
            self.assertIn('OK: requirements (11 requirement(s))', out)
        finally: f.write_bytes(saved)

    def test_a_profile_cannot_put_a_layer_between_or_leave_it_unlinked(self):  # LR-01, LR-06
        bad = json.loads((self.tmp / 'profiles' / 'strategy-and-sites-team.json').read_text())
        bad['layers'].append({'code': 'A3', 'name': 'mine', 'position': 'below', 'file': 'x.json'})
        bad['layers'].append({'code': 'X9', 'name': 'island', 'position': 'below', 'file': 'x9.json'}); bad['types'].append({'type': 'BANK.X9.Thing'})
        bad['link_types'].append({'source_type': 'BANK.A0.Goal', 'relationship': 'SKIPS_TO', 'target_type': 'A3.ApplicationComponent', 'required_evidence': ['memo']})
        bad['link_types'].append({'source_type': 'A1.BusinessCapability', 'relationship': 'NEW_CORE_LINK', 'target_type': 'A2.ServiceDomain', 'required_evidence': ['memo']})
        (self.tmp / 'profiles' / 'bad.json').write_text(json.dumps(bad))
        _, _, d = sdem('profile', 'check', '--file', self.tmp / 'profiles' / 'bad.json', '--json', cwd=self.tmp, ok=(1,))
        issues = ' | '.join(d['issues'])
        self.assertIn('layer A3: a core layer', issues)
        self.assertIn('layer X9: no link type joins it to its neighbour', issues)
        self.assertIn('BANK.A0.Goal SKIPS_TO A3.ApplicationComponent: links a layer to the layer directly below it', issues)
        self.assertIn("both layers are SDEM's", issues)

    def test_agents_install_writes_an_agent_per_profile_layer(self):  # LR-07
        site = self.tmp / 'site'; site.mkdir(exist_ok=True)
        _, _, d = sdem('agents', 'install', '--to', site, '--workspace', self.ws, '--json', cwd=self.tmp)
        self.assertIn('agents/sdem-layer-a5.agent.md', d['copilot']['written'])
        a5 = (site / '.github' / 'agents' / 'sdem-layer-a5.agent.md').read_text()
        self.assertIn('name: sdem-layer-a5', a5); self.assertIn('--layer A5', a5); self.assertNotIn('A4', a5)
        self.assertIn("'sdem-layer-a0', 'sdem-layer-a5']", (site / '.github' / 'agents' / 'sdem-orchestrator.agent.md').read_text())
        _, _, d = sdem('agents', 'install', '--to', site, '--workspace', self.ws, '--json', cwd=self.tmp)
        self.assertEqual(d['copilot']['written'], []); self.assertEqual(d['copilot']['kept'], [])       # a reinstall changes nothing

    def test_a_profile_type_in_a_core_layer_lands_through_a_change_set(self):  # fixed in v0.15.0: the layer is the metamodel's, not the name's first part
        cs = {'layer': 'A3', 'reason': 'a bank microservice', 'changes': [{'op': 'add', 'record': {'id': 'APP-PAY-MS', 'type': 'BANK.A3.PaymentsMicroservice', 'version': '1',
              'name': 'Payment notifications', 'lifecycle_status': 'active', 'attributes': {'owner': 'ROLE-PAY-OFFICER', 'risk_tier': '1', 'owning_team': 'payments-core'}}}]}
        (self.tmp / 'ms.json').write_text(json.dumps(cs))
        sdem('change', 'propose', self.tmp / 'ms.json', '--workspace', self.ws, '--agent', 'sdem-a3-application', '--person', 'steven', cwd=self.tmp)
        sdem('connect', 'APP-PAY-MS', 'DEPLOYED_ON', 'INF-K8S-PAY-PROD', '--workspace', self.ws, '--person', 'steven', '--evidence', 'deployment_design:DD-1', '--rationale', 'runs on the cluster', cwd=self.tmp)

    def test_a_workspace_without_layers_is_unchanged(self):  # LR-10
        plain = self.tmp / 'plain'; sdem('new', '--workspace', plain, '--person', 'steven', '--example', 'payment-initiation', cwd=self.tmp)
        self.assertFalse((plain / 'a0-strategy.json').exists())
        sdem('build', '--workspace', plain, '--out', plain / 'graph', cwd=self.tmp)
        _, _, d = sdem('impact', 'INF-K8S-PAY-PROD', '--change', 'rehost', '--graph', plain / 'graph', '--json', cwd=self.tmp)
        self.assertEqual(list(d['coverage']), ['A1', 'A2', 'A3', 'A4'])


if __name__ == '__main__':
    unittest.main()
