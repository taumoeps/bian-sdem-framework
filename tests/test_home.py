"""The main dashboard, `sdem home` (docs/sdem-dashboard-spec.md DB-H01…H06): SDEM itself and every project in use."""
import json, re, shutil, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem import home  # noqa: E402


class HomeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix='sdem-home-'))
        cls.page, cls.data = home.write(cls.tmp / 'site', [str(ROOT / 'examples')])
        cls.html = cls.page.read_text(encoding='utf-8')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_offline_and_linked_to_every_project(self):
        self.assertFalse(re.search(r'(?:src|href)="https?://', self.html))
        names = sorted(p.name for p in (ROOT / 'examples').iterdir() if p.is_dir() and (p / 'mappings.json').exists())
        self.assertEqual(sorted(p['name'] for p in self.data['projects']), names)
        for p in self.data['projects']:
            page = self.page.parent / p['page']; self.assertTrue(page.exists(), p['page'])
            self.assertIn('"home": "../index.html"', page.read_text(encoding='utf-8'))

    def test_metamodel_equals_the_rulebook(self):
        m = self.data['metamodel']
        self.assertEqual(len(m['within']), len(json.loads((ROOT / 'metamodel' / 'level-relationships.json').read_text())['constraints']))
        self.assertEqual(len(m['cross']), len(json.loads((ROOT / 'schema' / 'relationship-types.json').read_text())['relationships']))
        self.assertEqual(len(m['rules']), len(json.loads((ROOT / 'metamodel' / 'relationship-rules.json').read_text())['mappings']))
        types = {e['type'] for f in (ROOT / 'metamodel').glob('a[1-4]-*.json') for e in json.loads(f.read_text())['entities']}
        self.assertEqual({e['type'] for e in m['entities']}, types)
        comp = next(e for e in m['entities'] if e['type'] == 'A3.ApplicationComponent')
        self.assertIn('deployed_on', [a['name'] for a in comp['attributes'] + comp['inherited']])
        self.assertTrue(any(x.startswith('REALIZED_BY') for x in comp['cross']))

    def test_health_is_live(self):
        h = self.data['health']
        self.assertTrue(all(g['current'] for g in h['generators']), 'generated documents must be current')
        self.assertEqual(len(h['acceptance']), 8); self.assertTrue(all(a['passed'] for a in h['acceptance']))
        self.assertEqual(h['controls_total'], len(json.loads((ROOT / 'metamodel' / 'controls.json').read_text())['controls']))

    def test_picture_has_every_link_type(self):
        rels = {e['rel'] for e in self.data['entity_picture']['edges']}
        self.assertEqual(rels, {x['relationship'] for x in self.data['metamodel']['cross']})


    def test_architecture_picture_shows_every_component(self):
        a = self.data['architecture']; ids = {b['id'] for b in a['boxes']}
        self.assertTrue({'bian', 'history', 'metamodel', 'engine', 'validation', 'kg', 'a1', 'a2', 'a3', 'a4', 'aid', 'projections', 'coordination', 'workbench'} <= ids)
        st = {b['id']: b['status'] for b in a['boxes']}
        self.assertEqual(st['history'], 'not built'); self.assertEqual(st['bian'], 'partial'); self.assertEqual(st['aid'], 'built')
        for e in a['edges']: self.assertIn(e['s'], ids); self.assertIn(e['t'], ids)
        self.assertIn('show((location.hash||"#picture").slice(1))', self.html)   # the architecture is the landing view

if __name__ == '__main__':
    unittest.main()
