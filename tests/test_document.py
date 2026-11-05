"""`sdem document` (UX-D01…UX-D08): a layer's design as a readable document — deterministic, nothing invented, every record
with its source, gaps listed; Markdown, self-contained HTML and JSON."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}


def sdem(*args, cwd):
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], cwd=cwd, capture_output=True, text=True, env=ENV)
    return r.returncode, r.stdout, r.stderr


class DocumentTests(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        shutil.copytree(ROOT / 'examples' / 'payment-initiation', self.d / 'ws', ignore=shutil.ignore_patterns('graph', 'migrations'))
        p = self.d / 'ws' / 'a3-application.json'; a3 = json.loads(p.read_text(encoding='utf-8'))
        api = next(i for i in a3['instances'] if i['id'] == 'API-PI-06')
        api['attributes']['path'] = '/TBD'                                       # a placeholder
        app = next(i for i in a3['instances'] if i['id'] == 'APP-PAY-HUB')
        app['attributes']['source_id'] = 'document:DESIGN.md#4'                  # a document citation
        p.write_text(json.dumps(a3, indent=2), encoding='utf-8')

    def tearDown(self): shutil.rmtree(self.d, ignore_errors=True)

    def doc(self, layer):
        code, out, err = sdem('document', '--workspace', 'ws', '--layer', layer, '--json', cwd=self.d)
        self.assertEqual(code, 0, err)
        return json.loads(out)

    def test_it_is_deterministic(self):                                                  # UX-D01
        a = sdem('document', '--workspace', 'ws', '--layer', 'A3', cwd=self.d)[1]
        b = sdem('document', '--workspace', 'ws', '--layer', 'A3', cwd=self.d)[1]
        self.assertEqual(a, b); self.assertIn('# A3 Application Architecture', a)

    def test_every_record_and_nothing_else(self):                                        # UX-D02
        a3 = json.loads((self.d / 'ws' / 'a3-application.json').read_text(encoding='utf-8'))
        d = self.doc('A3')
        shown = [r['id'] for s in d['sections'] for r in s['records']]
        self.assertEqual(sorted(shown), sorted(i['id'] for i in a3['instances']))
        self.assertEqual(d['summary']['records'], len(a3['instances']))

    def test_sources_and_approved_connections(self):                                     # UX-D04, UX-D03
        rec = {r['id']: r for s in self.doc('A3')['sections'] for r in s['records']}
        self.assertEqual(rec['APP-PAY-HUB']['provenance'], 'from the design document DESIGN.md#4')
        links = {(c['relationship'], c['id'], c['status']) for c in rec['APP-PAY-HUB']['connections']}
        self.assertIn(('DEPLOYED_ON', 'INF-K8S-PAY-PROD', 'approved'), links)

    def test_gaps_are_listed(self):                                                      # UX-D05
        g = self.doc('A3')['gaps']
        self.assertIn({'id': 'API-PI-06', 'fields': ['path']}, g['placeholders'])
        self.assertIn('CMP-PAY-CAPTURE', g['no_connection'])                            # planted: no deployment, no link
        self.assertNotIn('APP-PAY-HUB', g['no_connection'])

    def test_requirements_of_the_layer(self):                                            # UX-D06
        ids = [q['id'] for q in self.doc('A3')['requirements']]
        self.assertIn('REQ-PF-01', ids)

    def test_html_is_self_contained(self):                                               # UX-D07
        code, out, err = sdem('document', '--workspace', 'ws', '--format', 'html', '-o', 'out', cwd=self.d)
        self.assertEqual(code, 0, err)
        files = sorted(p.name for p in (self.d / 'out').iterdir())
        self.assertEqual(files, ['a1-design.html', 'a2-design.html', 'a3-design.html', 'a4-design.html'])
        page = (self.d / 'out' / 'a3-design.html').read_text(encoding='utf-8')
        self.assertNotIn('<script', page); self.assertNotIn('src=', page); self.assertNotIn('<link', page); self.assertNotIn('href=', page)   # loads nothing
        self.assertIn('<h2>', page)

    def test_an_unknown_layer_is_an_error(self):
        code, out, err = sdem('document', '--workspace', 'ws', '--layer', 'A9', cwd=self.d)
        self.assertEqual(code, 2); self.assertIn('not a layer', err)


if __name__ == '__main__':
    unittest.main()
