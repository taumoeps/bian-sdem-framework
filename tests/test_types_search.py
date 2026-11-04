"""`sdem types` and `sdem bian search` (docs/design/sdem-types-search-spec.md, TS-01…TS-06), and the fixes the agent baseline
found (2026-11-02). Synthetic data only."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
ENV = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}


def sdem(*args, cwd=ROOT, ok=(0,)):
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], cwd=cwd, capture_output=True, text=True, env=ENV)
    assert r.returncode in ok, f'sdem {" ".join(map(str, args))}: exit {r.returncode}\n{r.stdout[-900:]}\n{r.stderr[-900:]}'
    return r.returncode, r.stdout + r.stderr, (json.loads(r.stdout) if r.stdout.strip().startswith('{') else None)


class TypesTests(unittest.TestCase):
    def test_a_type_lists_its_fields_values_and_links(self):  # TS-01, TS-02
        _, _, d = sdem('types', 'A1.BusinessProcess', '--json')
        a = {x['name']: x for x in d['attributes']}
        self.assertEqual(a['criticality']['allowed_values'], ['high', 'medium', 'low'])          # the values the baseline agents guessed
        self.assertEqual(a['invokes']['refers_to'], ['A2.ServiceOperation'])
        self.assertIn({'kind': 'realization', 'to': 'A1.BusinessCapability', 'rule': 'RA1-08'}, d['links_out'])
        self.assertTrue(any(r['relationship'] == 'USES_DOMAIN' and r['evidence_needed'] == ['process_model'] for r in d['link_types_to_other_layers']))
        _, _, d = sdem('types', 'A1.BusinessRequirement', '--json')
        self.assertEqual({x['name']: x for x in d['attributes']}['requirement_kind']['allowed_values'], ['requirement', 'constraint', 'principle'])

    def test_a_layer_and_the_overview(self):  # TS-01
        _, _, d = sdem('types', 'A1', '--json')
        self.assertIn('A1.ValueStreamStage', [t['type'] for t in d['types']])
        _, out, _ = sdem('types')
        self.assertIn('A4', out); self.assertIn('sdem bian search', out)
        code, out, _ = sdem('types', 'A1.Proces', ok=(2,)); self.assertIn('did you mean', out)

    def test_the_requirement_and_change_set_formats(self):  # TS-03
        _, _, d = sdem('types', 'requirement', '--json')
        self.assertIn('performance', d['category']); self.assertIn('>=', d['condition']['operator']); self.assertEqual(d['owner_layer'], ['A1', 'A2', 'A3', 'A4'])
        self.assertIn('provenance', d['set_by_sdem'])
        _, _, d = sdem('types', 'change-set', '--json'); self.assertIn('relationships', d['shape'])

    def test_a_workspace_profile_is_included(self):  # TS-05
        tmp = Path(tempfile.mkdtemp())
        try:
            sdem('profile', 'example', '--out', tmp / 'p', cwd=tmp); sdem('new', '--workspace', tmp / 'ws', '--person', 'steven', cwd=tmp)
            shutil.copy(tmp / 'p' / 'bank-base.json', tmp / 'ws' / 'sdem-profile.json')
            _, _, d = sdem('types', 'A3.ApplicationComponent', '--workspace', tmp / 'ws', '--json', cwd=tmp)
            self.assertIn('risk_tier', [x['name'] for x in d['attributes']]); self.assertIn('BANK-R01', [r['id'] for r in d['organisation_rules']])
            _, _, d = sdem('types', 'requirement', '--workspace', tmp / 'ws', '--json', cwd=tmp); self.assertIn('operational_resilience', d['category'])
        finally: shutil.rmtree(tmp, ignore_errors=True)


class SearchTests(unittest.TestCase):
    def test_plain_words_find_domains_and_the_ids_aid_uses(self):  # TS-04
        _, _, d = sdem('bian', 'search', 'ledger', 'posting', '--json')
        r = d['results'][0]
        self.assertEqual((r['service_domain'], r['id']), ('Financial Accounting', 'SD-FINANCIAL-ACCOUNTING'))
        self.assertIn('SO-FINANCIAL-ACCOUNTING-CAPTURE-LEDGER-POSTING', [o['id'] for o in r['operations']])
        _, _, d = sdem('bian', 'search', 'loan', '--json'); self.assertEqual(d['results'][0]['service_domain'], 'Loan')          # the domain named
        _, _, d = sdem('bian', 'search', 'reconcile', '--json'); self.assertEqual(d['results'][0]['service_domain'], 'Account Reconciliation')   # stems meet
        _, _, d = sdem('bian', 'search', 'customer', '--json'); self.assertNotIn('Custody Administration', [x['service_domain'] for x in d['results']])

    def test_the_ids_are_the_ones_import_writes(self):  # TS-04: search, import and aid agree
        tmp = Path(tempfile.mkdtemp())
        try:
            _, _, d = sdem('bian', 'search', 'account', 'reconciliation', '--json')
            sdem('bian', 'import', '--base', '--only', d['results'][0]['service_domain'], '-o', tmp / 'a2.json', cwd=tmp)
            ids = {i['id'] for i in json.loads((tmp / 'a2.json').read_text())['instances']}
            self.assertIn(d['results'][0]['id'], ids)
            self.assertTrue({o['id'] for o in d['results'][0]['operations']} <= ids)
        finally: shutil.rmtree(tmp, ignore_errors=True)

    def test_words_bian_does_not_use_are_named(self):
        _, _, d = sdem('bian', 'search', 'zebra', 'ledger', '--json'); self.assertEqual(d['words_bian_does_not_use'], ['zebra'])


    def test_all_operations_of_a_domain_on_request(self):   # found by the after-change measurement: matching operations only, by default
        _, _, d = sdem('bian', 'search', 'ledger', 'posting', '--all-operations', '--json')
        r = d['results'][0]; self.assertEqual(len(r['operations']), r['operations_total'])
        self.assertEqual(r['operations'][0]['id'], 'SO-FINANCIAL-ACCOUNTING-CAPTURE-LEDGER-POSTING')   # the matching ones still first

    def test_the_command_list_shows_link_as_it_is_run(self):
        _, _, d = sdem('commands', '--json')
        self.assertNotIn('engine', [x['name'] for x in d['commands']['link']['positionals']])
        self.assertIn('--baseline', [x['name'] for x in d['commands']['link']['options']])

class BaselineFixTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); sdem('new', '--workspace', self.tmp / 'ws', '--person', 'steven', '--example', 'payment-initiation', cwd=self.tmp)

    def tearDown(self): shutil.rmtree(self.tmp, ignore_errors=True)

    def test_a_requirement_with_an_unknown_layer_or_field_is_refused(self):
        req = {'id': 'REQ-X-01', 'name': 'x', 'statement': 'x', 'owner_layer': 'X', 'category': 'other', 'scope': 'component', 'subject': 'APP-PAY-HUB',
               'condition': {'metric': 'm', 'operator': '>=', 'value': 1}, 'foo': 1}
        (self.tmp / 'r.json').write_text(json.dumps(req))
        code, out, _ = sdem('requirements', 'propose', self.tmp / 'r.json', '--workspace', self.tmp / 'ws', '--person', 'steven', cwd=self.tmp, ok=(1, 2))
        self.assertIn("owner_layer 'X' is not a layer of this workspace", out); self.assertIn('unknown field(s) foo', out)

    def test_an_aid_dry_run_says_what_it_would_write(self):
        (self.tmp / 'ws' / 'a3-application.json').unlink()
        code, out, d = sdem('aid', '--workspace', self.tmp / 'ws', '--person', 'steven', '--dry-run', '--json', cwd=self.tmp, ok=(0, 2))
        self.assertEqual(d['error']['code'], 'refused')                                                   # approved links to records no longer held — refused, not a crash


    def test_a_healthy_aid_dry_run_lists_would_write_and_writes_nothing(self):
        ws = self.tmp / 'gl'; sdem('new', '--workspace', ws, '--person', 'steven', cwd=self.tmp)
        cs = {'layer': 'A1', 'reason': 'ledger', 'changes': [{'op': 'add', 'record': {'id': 'PRC-GL-POST', 'type': 'A1.BusinessProcess', 'version': '1', 'name': 'Post financial transactions',
              'lifecycle_status': 'planned', 'attributes': {'invokes': ['SO-FINANCIAL-ACCOUNTING-CAPTURE-LEDGER-POSTING']}}}]}
        (self.tmp / 'cs.json').write_text(json.dumps(cs)); sdem('change', 'propose', self.tmp / 'cs.json', '--workspace', ws, '--agent', 'sdem-a1-business', '--person', 'steven', cwd=self.tmp)
        before = sorted(p.name for p in ws.rglob('*'))
        _, _, d = sdem('aid', '--workspace', ws, '--person', 'steven', '--dry-run', '--json', cwd=self.tmp)
        self.assertTrue(any(w.endswith('a2-service-domain.json') for w in d['would_write']))
        self.assertEqual(sorted(p.name for p in ws.rglob('*')), before)

if __name__ == '__main__':
    unittest.main()
