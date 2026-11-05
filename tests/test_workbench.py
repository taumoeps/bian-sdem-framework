"""`sdem workbench` (docs/design/sdem-workbench-ux-spec.md, UX-N01…N15): one offline page per workspace, the Solution Workspace
and the SDEM Framework, every fact from SDEM's own functions; it copes with missing layers and empty workspaces; SDEM Home links it."""
import json, os, re, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}
sys.path.insert(0, str(ROOT))


def sdem(*args, cwd):
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], cwd=cwd, capture_output=True, text=True, env=ENV)
    return r.returncode, r.stdout, r.stderr


def page_data(html):
    m = re.search(r'const D=(\{.*?\}), F=D\.framework;', html, re.S)
    return json.loads(m.group(1).replace('<\\/', '</'))


class WorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        shutil.copytree(ROOT / 'examples' / 'payment-initiation', self.d / 'ws', ignore=shutil.ignore_patterns('graph', 'migrations'))

    def tearDown(self): shutil.rmtree(self.d, ignore_errors=True)

    def build(self, ws='ws'):
        code, out, err = sdem('workbench', '--workspace', ws, '-o', 'wb.html', cwd=self.d)
        self.assertEqual(code, 0, err)
        html = (self.d / 'wb.html').read_text(encoding='utf-8')
        return html, page_data(html)

    def test_every_record_and_the_framework(self):                                       # UX-N02, N03, N09, N11
        html, d = self.build()
        n = sum(len(json.loads((self.d / 'ws' / f).read_text(encoding='utf-8'))['instances'])
                for f in ('a1-business.json', 'a2-service-domain.json', 'a3-application.json', 'a4-technology.json'))
        self.assertEqual(len(d['records']), n)
        self.assertEqual(d['present'], ['A1', 'A2', 'A3', 'A4']); self.assertEqual(d['missing'], [])
        self.assertEqual(len(d['framework']['types']), 44)
        self.assertEqual(len(d['framework']['within']), 132)
        self.assertTrue(d['framework']['cross'] and all(c['required_evidence'] for c in d['framework']['cross']))
        self.assertEqual(len(d['registry']), len(json.loads((self.d / 'ws' / 'mappings.json').read_text(encoding='utf-8'))['mappings']))
        self.assertTrue(all(d['docs'][l]['html'] for l in ('A1', 'A2', 'A3', 'A4')))      # the documents (UX-D)
        self.assertTrue(all(r['source_text'] for r in d['records']))                       # the Catalog says where each came from
        self.assertTrue(any(q.get('allocated_to') for q in d['reqs']))                     # and the requirements allocated to a record

    def test_the_page_loads_nothing(self):                                               # UX-P02
        html, _ = self.build()
        for bad in ('<script src', '<link', '@import', 'url(', 'http://', 'https://cdn', 'fetch('):
            self.assertNotIn(bad, html.split('const D=')[0] + html.split('</script>')[-1], bad)
        self.assertLess(len(html), 2_000_000)                                           # size budget (UX-Q04)

    def test_the_template_knows_no_workspace(self):                                      # UX-P03: nothing hard-coded
        t = (ROOT / 'sdem' / 'workbench.html').read_text(encoding='utf-8')
        for word in ('INF-K8S', 'APP-PAY', 'Payments Hub', 'payment-initiation'):
            self.assertNotIn(word, t)

    def test_a_missing_layer_is_said_not_hidden(self):                                   # UX-P03
        (self.d / 'ws' / 'a1-business.json').unlink()
        _, d = self.build()
        self.assertEqual(d['missing'], ['A1']); self.assertNotIn('A1', d['docs'])
        self.assertFalse([r for r in d['records'] if r['layer'] == 'A1'])

    def test_an_empty_workspace(self):
        self.assertEqual(sdem('new', '--workspace', 'empty', '--person', 'jane.architect', cwd=self.d)[0], 0)
        _, d = self.build('empty')
        self.assertEqual(d['records'], []); self.assertEqual(d['graph_state']['state'], 'missing')
        self.assertTrue(d['graph_state']['command'].startswith('sdem build'))

    def test_check_errors_are_said_once_with_the_fix(self):                             # an old workspace: one error, where, and the command
        for f in ('a1-business.json', 'a2-service-domain.json', 'a3-application.json', 'a4-technology.json', 'mappings.json'):
            p = self.d / 'ws' / f; ds = json.loads(p.read_text(encoding='utf-8')); ds['metamodel_version'] = '0.0.1'
            p.write_text(json.dumps(ds), encoding='utf-8')
        _, d = self.build()
        errors = [c for c in d['checks'] if c['level'] == 'error']
        self.assertEqual(len(errors), 1, errors)
        self.assertEqual(errors[0]['where'], ['A1', 'A2', 'A3', 'A4', 'mappings.json'])
        self.assertEqual(d['graph_state']['state'], 'blocked')
        self.assertTrue(d['graph_state']['command'].startswith('sdem migrate'))

    def test_json_summary_and_not_a_workspace(self):
        code, out, err = sdem('workbench', '--workspace', 'ws', '-o', 'wb.html', '--json', cwd=self.d)
        self.assertEqual(code, 0, err)
        s = json.loads(out); self.assertEqual(s['framework']['types'], 44); self.assertEqual(s['layers'], ['A1', 'A2', 'A3', 'A4'])
        (self.d / 'nothing').mkdir()
        self.assertEqual(sdem('workbench', '--workspace', 'nothing', cwd=self.d)[0], 2)

    def test_home_writes_and_links_each_workbench(self):                                 # UX-N13
        code, out, err = sdem('home', '--workspace', 'ws', '-o', 'site', cwd=self.d)
        self.assertEqual(code, 0, err)
        wb = self.d / 'site' / 'workspaces' / 'ws-workbench.html'
        self.assertTrue(wb.exists())
        self.assertEqual(page_data(wb.read_text(encoding='utf-8'))['home'], '../index.html')
        self.assertIn('Open Workbench', (self.d / 'site' / 'index.html').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
