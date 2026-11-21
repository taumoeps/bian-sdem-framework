"""P3 (DL-21): a made-up design with no banking content — examples/0.20/library-holds, SDEM's default four layers without BIAN
(A1 Business, A2 Data, A3 Application, A4 Technology) — runs every command that applies to it, end to end, in the 0.20 form."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EX = ROOT / 'examples' / '0.20' / 'library-holds'
ME = 'jane.architect'
ENV = {**os.environ, 'PYTHONPATH': str(ROOT), 'PYTHONIOENCODING': 'utf-8'}
ENV.pop('SDEM_FORM', None)   # the default form (DL-D9): 0.20


def sdem(*args, cwd, ok=(0,)):
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], capture_output=True, text=True, encoding='utf-8', env=ENV, cwd=cwd)
    assert r.returncode in ok, f"sdem {' '.join(map(str, args))}: exit {r.returncode}\n{r.stdout[-1200:]}\n{r.stderr[-1200:]}"
    return r.stdout


class LibraryHolds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp()); cls.ws = cls.tmp / 'ws'
        cls.started = sdem('new', '--workspace', cls.ws, '--person', ME, '--core', '--from', EX, cwd=cls.tmp)
        sdem('build', '--workspace', cls.ws, '--out', cls.ws / 'graph', cwd=cls.tmp)

    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.tmp, ignore_errors=True)

    def run_(self, *args, ok=(0,)): return sdem(*args, cwd=self.tmp, ok=ok)

    def test_it_is_the_default_four_layers_with_data_its_own(self):
        self.assertIn('A1 12 record(s), A2 1 record(s), A3 4 record(s), A4 8 record(s), 7 connection(s)', self.started)
        self.assertEqual(sorted(p.name for p in self.ws.glob('*.json') if p.name not in ('mappings.json', 'workspace.json', 'sdem-ledger.json')),
                         ['application.json', 'business.json', 'data.json', 'technology.json'])
        from sdem import api
        self.assertEqual([(l['code'], l['name']) for l in api.layers_in_use(self.ws)], [('A1', 'Business'), ('A2', 'Data'), ('A3', 'Application'), ('A4', 'Technology')])

    def test_check_status_and_the_review_lists(self):
        out = self.run_('check', '--workspace', self.ws, '--require-recorded')
        self.assertNotIn('ERROR', out)
        s = json.loads(self.run_('status', '--workspace', self.ws, '--json', ok=(0, 1)))   # exits 1 while a design has gaps to decide
        self.assertEqual([l['level'] for l in s['layers']], ['A1', 'A2', 'A3', 'A4'])
        self.assertTrue(json.loads(self.run_('handback', '--workspace', self.ws, '--json')))
        self.assertIn('summary', json.loads(self.run_('comply', '--workspace', self.ws, '--json', ok=(0, 1))))
        self.run_('link', '--workspace', self.ws, '--out', self.ws / 'links')
        self.run_('aid', '--workspace', self.ws, '--person', ME, '--dry-run', '--json')

    def test_the_graph_trace_impact_and_query(self):
        g = self.ws / 'graph'
        self.run_('build', '--workspace', self.ws, '--out', g)   # current: another test may have changed the design since
        down = self.run_('trace', 'PRC-PLACE-HOLD', '--direction', 'down', '--graph', g)   # a trace follows the connections between layers
        self.assertIn('APS-HOLDS', down)
        up = self.run_('trace', 'SYS-CATALOGUE-DB', '--direction', 'up', '--graph', g)
        for rid in ('DE-HOLD', 'BO-HOLD'): self.assertIn(rid, up)   # the database ← the data it stores ← the business object
        self.assertIn('APP-CIRC', self.run_('trace', 'DE-HOLD', '--direction', 'down', '--graph', g))   # ACCESSED_BY points down the stack: data → application (DL-04)
        imp = json.loads(self.run_('impact', 'SYS-CATALOGUE-DB', '--change', 'retire', '--graph', g, '--json'))
        self.assertIn('DE-HOLD', json.dumps(imp))
        q = self.run_('query', '--graph', g, '--type', 'application.ApplicationComponent', '--json')
        q = json.loads(q[q.index('{'):])   # after the line that names the store
        self.assertEqual(([r['id'] for r in q['items']], q['items'][0]['level']), (['APP-CIRC'], 'A3'))   # by its id; Application is A3 without BIAN

    def test_the_documents_and_pages(self):
        doc = self.run_('document', '--workspace', self.ws)
        self.assertIn('Circulation system', doc)
        for args in (('view', '--graph', self.ws / 'graph', '-o', self.tmp / 'view.html'), ('dashboard', '--workspace', self.ws, '-o', self.tmp / 'dash.html'),
                     ('workbench', '--workspace', self.ws, '-o', self.tmp / 'wb.html'), ('diagram', '--workspace', self.ws),
                     ('zones', '--workspace', self.ws, '--json'), ('layout', '--layer', 'A4', '--workspace', self.ws),
                     ('home', '--workspace', self.ws, '-o', self.tmp / 'home')):
            with self.subTest(command=args[0]): self.run_(*args)
        for page in ('view.html', 'dash.html', 'wb.html', 'home/index.html'): self.assertTrue((self.tmp / page).exists(), page)

    def test_a_change_through_a_change_set_and_its_events(self):
        rec = next(i for i in json.loads((self.ws / 'application.json').read_text(encoding='utf-8'))['instances'] if i['id'] == 'APP-CIRC')
        cs = self.tmp / 'cs.json'
        cs.write_text(json.dumps({'layer': 'application', 'reason': 'a made-up change', 'changes': [{'op': 'update', 'record': {**rec, 'description': 'Keeps loans, renewals, holds and fines.'}}]}))
        self.run_('change', 'propose', cs, '--workspace', self.ws, '--agent', 'sdem-a3-application', '--person', ME)
        self.assertNotIn('ERROR', self.run_('check', '--workspace', self.ws, '--require-recorded'))   # the chain of change sets is whole
        self.run_('events', 'show', 'CE-001', '--workspace', self.ws)

    def test_the_copy_in_0_19s_form_for_a_consumer_built_on_it(self):
        from sdem import api
        api.export_019(self.ws, self.tmp / 'old')
        self.assertTrue((self.tmp / 'old' / 'a2-service-domain.json').exists())   # 0.19 always had the BIAN layer: here empty
        out = sdem('check', '--workspace', self.tmp / 'old', '--require-recorded', cwd=self.tmp)
        self.assertNotIn('ERROR', out); self.assertFalse((self.tmp / 'old' / 'coordination').exists())   # the design, not its history (CTL-20 is checked in the workspace)


if __name__ == '__main__':
    unittest.main()
