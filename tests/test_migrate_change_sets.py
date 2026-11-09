"""Two bugs found on 2026-11-09 (owner's request to fix, 2026-11-10):
RV-07 — a migration in a workspace with change sets is recorded as a change set, so `sdem check` does not report it as an edit outside one;
WS-07 — the catalogue `sdem aid` chooses from does not hold the same BIAN element twice when the workspace has it under its own id."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem import migrate as M  # noqa: E402
from sdem.agents import Estate, check_coordination  # noqa: E402
from sdem.graph import LevelGraph  # noqa: E402
from sdem.metamodel import Metamodel  # noqa: E402
from sdem.new import catalogue  # noqa: E402

ENV = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}
EXAMPLES = sorted(p for p in (ROOT / 'examples').iterdir() if (p / 'mappings.json').exists())


def _j(p): return json.loads(Path(p).read_text(encoding='utf-8'))


def back_to(ws, version):
    for f in Path(ws).glob('*.json'):
        d = _j(f)
        if isinstance(d, dict) and 'metamodel_version' in d: d['metamodel_version'] = version; f.write_text(json.dumps(d, indent=2))


class MigrateWithChangeSetsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); self.ws = self.tmp / 'ws'
        shutil.copytree(ROOT / 'examples' / 'payment-initiation', self.ws, ignore=shutil.ignore_patterns('graph', 'migrations', 'm1-*'))
        op = next(i for i in _j(self.ws / 'a3-application.json')['instances'] if i['id'] == 'API-PI-01')
        Estate(self.ws).propose({'layer': 'A3', 'reason': 'a change set, so the layer has a chain',
                                 'changes': [{'op': 'update', 'record': {**{k: op[k] for k in ('id', 'type', 'version', 'name')}, 'description': 'Create one.'}}]},
                                'sdem-a3-application', 'jane.architect')
        self.previous = next(m['from'] for m in _j(ROOT / 'metamodel' / 'migrations.json')['migrations'] if m['to'] == Metamodel.load().version)

    def tearDown(self): shutil.rmtree(self.tmp, ignore_errors=True)

    def coordination_issues(self): return [i for i in check_coordination(self.ws)[0] if 'AG-S08' in i or 'missing' in i]

    def test_a_layer_in_step_gets_the_migration_recorded(self):
        back_to(self.ws, self.previous)   # the whole workspace on the previous metamodel; the A3 chain no longer matches the file …
        last = Estate(self.ws)._last_change_set('A3')
        snap = self.ws / 'coordination' / 'snapshots' / f"{last['id']}.json"
        d = _j(snap); d['metamodel_version'] = self.previous; snap.write_text(json.dumps(d, indent=2))   # … so put the chain in step, as on that metamodel
        from sdem.agents import _content_sha, _file_sha
        cs_file = self.ws / 'coordination' / 'change-sets' / f"{last['id']}.json"; cs = _j(cs_file)
        cs['dataset']['after_sha256'] = _file_sha(self.ws / 'a3-application.json'); cs_file.write_text(json.dumps(cs, indent=2))
        self.assertEqual(self.coordination_issues(), [])
        res = M.migrate(self.ws, 'jane.architect')
        self.assertEqual(len(res.get('change_sets', [])), 1, res); self.assertNotIn('note', res)
        self.assertEqual(self.coordination_issues(), [])                  # the bug: AG-S08 reported the migration as an edit outside a change set
        ev = next(e for e in Estate(self.ws).status() if e['change_set'] == res['change_sets'][0])
        self.assertTrue(ev['planned']); self.assertIn('no record changed', ev['validation'])   # nothing to plan or validate

    def test_an_earlier_edit_outside_a_change_set_is_not_hidden(self):
        p = self.ws / 'a3-application.json'; d = _j(p); d['instances'][0]['description'] = 'edited by hand'; p.write_text(json.dumps(d, indent=2))
        back_to(self.ws, self.previous)
        res = M.migrate(self.ws, 'jane.architect')
        self.assertNotIn('change_sets', res); self.assertIn('A3', res['note']); self.assertIn('sdem change adopt', res['note'])
        self.assertTrue(any('AG-S08' in i for i in self.coordination_issues()))   # still the person's to adopt


class CatalogueTests(unittest.TestCase):
    def test_every_examples_catalogue_passes_the_dataset_check(self):     # sdem aid refused 5 of the 8 before
        mm = Metamodel.load()
        for ws in EXAMPLES:
            with self.subTest(ws=ws.name):
                self.assertEqual(LevelGraph(catalogue(ws), mm).validate(), [])

    def test_the_workspaces_own_record_is_kept_and_referenced(self):
        cat = catalogue(ROOT / 'examples' / 'digital-lending')
        loans = [i for i in cat['instances'] if i['type'] == 'A2.AssetType' and i['name'] == 'Consumer Loan']
        self.assertEqual([i['id'] for i in loans], ['AT-LO'])                 # the workspace's id, once
        ids = {i['id'] for i in cat['instances']}
        self.assertTrue(all(r['source'] in ids and r['target'] in ids for r in cat['relationships']))

    def test_sdem_aid_runs_on_digital_lending(self):
        with tempfile.TemporaryDirectory() as d:
            ws = Path(d) / 'dl'; shutil.copytree(ROOT / 'examples' / 'digital-lending', ws, ignore=shutil.ignore_patterns('graph'))
            r = subprocess.run([sys.executable, '-m', 'sdem', 'aid', '--workspace', str(ws), '--person', 'jane.architect', '--dry-run'], capture_output=True, text=True, env=ENV, cwd=d)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr); self.assertIn('would add', r.stdout)


if __name__ == '__main__':
    unittest.main()
