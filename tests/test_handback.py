"""`sdem handback` (AG-H01…H03; owner's decision D7, 2026-11-09): what a workspace leaves open for a person, read from the workspace."""
import copy, json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem import handback  # noqa: E402

ENV = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}


def _j(p): return json.loads(Path(p).read_text(encoding='utf-8'))


class HandbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); self.ws = self.tmp / 'ws'
        shutil.copytree(ROOT / 'examples' / 'payment-initiation', self.ws, ignore=shutil.ignore_patterns('graph', 'm1-*'))

    def tearDown(self): shutil.rmtree(self.tmp, ignore_errors=True)

    def edit(self, fn):
        p = self.ws / 'a3-application.json'; d = _j(p); fn(d); p.write_text(json.dumps(d, indent=2))

    def test_a_clean_workspace_waits_on_nobody(self):
        h = handback.collect(self.ws)
        self.assertEqual(h['commands_for_the_person'], [])
        self.assertEqual(h['summary']['missing_required'], 0); self.assertEqual(h['summary']['possible_duplicates'], 0)
        self.assertIn('Nothing is waiting on a person', handback.render(h))

    def test_what_is_left_open_is_listed_with_the_commands(self):
        def change(d):
            op = next(i for i in d['instances'] if i['id'] == 'API-PI-01'); op['lifecycle_status'] = 'planned'; op['attributes'].pop('path')
            op2 = next(i for i in d['instances'] if i['id'] == 'API-PI-02'); op2['attributes']['operation_id'] = 'TBD'
            c = next(i for i in d['instances'] if i['type'] == 'A3.ApplicationComponent')
            d['instances'].append({**copy.deepcopy(c), 'id': 'CMP-DUP', 'name': c['name'].upper()})
            d['instances'].append({'id': 'AID-SVC-1', 'type': 'A3.ApplicationService', 'version': '1.0', 'name': 'Payment service (inferred)', 'lifecycle_status': 'planned',
                                   'attributes': {'inferred': {'by': 'sdem aid', 'run': 'AID-001', 'rule': 'name', 'confidence': '0.4', 'evidence_class': 'name_token', 'reasoning': 'its name'}}})
        self.edit(change)
        h = handback.collect(self.ws); s = h['summary']
        miss = {(m['id'], m['attribute']): m for m in h['missing_values']}
        self.assertEqual(miss[('API-PI-01', 'path')]['why'], 'absent'); self.assertEqual(miss[('API-PI-01', 'path')]['lifecycle_status'], 'planned')
        self.assertEqual(miss[('API-PI-02', 'operation_id')]['why'], 'placeholder'); self.assertFalse(miss[('API-PI-02', 'operation_id')]['required'])
        self.assertEqual(s['unconfirmed_inferred'], 1); self.assertEqual(s['weak_inferred'], 1)
        self.assertTrue(any(set(x['ids']) >= {'CMP-DUP'} and x['rule'] == 'LC-09n' for x in h['possible_duplicates']))
        self.assertTrue(any('sdem aid confirm' in c for c in h['commands_for_the_person']))
        self.assertTrue(any('possible duplicate' in c for c in h['commands_for_the_person']))
        text = handback.render(h)
        for want in ('Values nobody knows yet', 'WEAK: a name or description only', 'Possible duplicates', 'the agent does not run these'): self.assertIn(want, text)

    def test_sources_are_counted(self):
        self.edit(lambda d: d['relationships'][0].update(source_id='document:DESIGN.md#4'))
        h = handback.collect(self.ws)
        self.assertEqual(h['links']['with_source'], 1)
        self.assertEqual(h['summary']['links_without_source'], h['links']['total'] - 1)

    def test_the_command(self):
        r = subprocess.run([sys.executable, '-m', 'sdem', 'handback', '--workspace', str(self.ws), '--json'], capture_output=True, text=True, env=ENV, cwd=self.tmp)
        self.assertEqual(r.returncode, 0, r.stderr); self.assertIn('summary', json.loads(r.stdout))
        (self.tmp / 'empty').mkdir()
        self.assertEqual(subprocess.run([sys.executable, '-m', 'sdem', 'handback', '--workspace', str(self.tmp / 'empty')], capture_output=True, env=ENV, cwd=self.tmp).returncode, 2)


if __name__ == '__main__':
    unittest.main()
