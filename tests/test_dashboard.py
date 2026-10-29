"""The dashboard and its CLI outputs (docs/design/sdem-dashboard-spec.md AT-DB-01…05): `sdem dashboard`, `sdem matrix`, `sdem impact --report`.
The page only displays what SDEM's functions computed, so each figure is checked against the CLI's own answer."""
import contextlib, glob, io, json, re, shutil, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem import cli, dashboard  # noqa: E402
from sdem.store import GraphReader  # noqa: E402

PAY = ROOT / 'examples' / 'payment-initiation'


def sdem(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try: code = cli.main([str(a) for a in argv])
        except SystemExit as e: code = e.code if isinstance(e.code, int) else 1
    return code, out.getvalue(), err.getvalue()


class DashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix='sdem-dash-'))
        cls.data = dashboard.collect(PAY)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_generates_for_every_example_offline(self):   # AT-DB-01
        for d in sorted(glob.glob(str(ROOT / 'examples') + '/*/')):
            if 'reference-structure' in d or not (Path(d) / 'mappings.json').exists(): continue   # examples/designs/ is not a workspace
            out = self.tmp / (Path(d).name + '.html')
            code, _, err = sdem('dashboard', '--workspace', d, '-o', out)
            self.assertEqual(code, 0, err)
            h = out.read_text(encoding='utf-8')
            self.assertFalse(re.search(r'(?:src|href)="https?://', h), 'the page loads nothing from the network')
            data = json.loads(re.search(r'const D = (\{.*?\});\nconst TABS', h, re.S).group(1).replace('<\\/', '</'))
            self.assertEqual(set(data) >= {'layers', 'coverage', 'review', 'records', 'matrix', 'changes', 'controls'}, True)

    def test_overview_equals_check_and_unmapped(self):   # AT-DB-02
        code, out, _ = sdem('check', '--workspace', PAY)
        for l in self.data['layers']:
            self.assertEqual(len(l['errors']), 0); self.assertIn(f"OK: level {l['level']}", out)
            self.assertEqual(len(l['advice']), sum(1 for x in out.splitlines() if x.startswith(f"WARN: level {l['level']}")))
        reader = GraphReader.from_exports([str(PAY / f) for f in dashboard.FILES] + [str(PAY / 'mappings.json')])
        for lvl, c in self.data['coverage'].items():
            self.assertEqual(sorted(u['id'] for u in c['unmapped']), sorted(n['id'] for n in reader.unmapped(lvl)))

    def test_trace_and_impact_equal_the_cli(self):   # AT-DB-03
        r = self.data['records']['APP-PAY-HUB']
        imp = json.loads(sdem('impact', 'APP-PAY-HUB', '--change', 'replace', '--workspace', PAY, '--json')[1])
        self.assertEqual({(x['id'], x['classification']) for x in r['impact']['replace']['rows']}, {(x['id'], x['classification']) for x in imp['instances']})
        self.assertEqual(r['impact']['replace']['supersede'], imp['mappings_to_supersede'])
        tr = json.loads(sdem('trace', 'APP-PAY-HUB', '--direction', 'down', '--workspace', PAY, '--json')[1])['down']
        ids = lambda n: {n['id']} | {i for c in n['children'] for i in ids(c['node'])}
        self.assertEqual(ids(r['down']), ids(tr))

    def test_matrix_chain(self):   # AT-DB-04
        chain = self.data['matrix']['chain']
        self.assertIn(('CAP-PAY-010', 'SD-PI', 'APP-PAY-HUB', 'INF-K8S-PAY-PROD'), {(c['capability'], c['domain'], c['application'], c['technology']) for c in chain})
        md = self.tmp / 'm.md'; self.assertEqual(sdem('matrix', '--workspace', PAY, '--md', md)[0], 0)
        self.assertIn('| Initiate Payment `CAP-PAY-010` | Payment Initiation', md.read_text())

    def test_review_equals_sdem_review(self):   # AT-DB-05
        est = self.tmp / 'est'; shutil.copytree(PAY, est, ignore=shutil.ignore_patterns('graph'))
        reg = json.loads((est / 'mappings.json').read_text()); reg['mappings'] = [m for m in reg['mappings'] if m['mapping_id'] != 'PAY-106']
        (est / 'mappings.json').write_text(json.dumps(reg))
        data = dashboard.collect(est)
        sdem('link', '--workspace', est, '--out', self.tmp / 'l')
        rev = json.loads(sdem('review', self.tmp / 'l' / 'proposals.json', '--json')[1])
        self.assertEqual([(r['source'], r['rel'], r['target']) for r in data['review']['rows']], [(r['source'], r['relationship'], r['target']) for r in rev])
        self.assertTrue(all(r['evidence_needed'] for r in data['review']['rows']))
        self.assertIn('proposed link(s) to review', ' '.join(a['text'] for a in data['attention']))

    def test_impact_report(self):   # DB-K02
        f = self.tmp / 'r.md'
        self.assertEqual(sdem('impact', 'INF-K8S-PAY-PROD', '--change', 'rehost', '--workspace', PAY, '--report', f)[0], 0)
        t = f.read_text()
        self.assertIn('# Impact report — rehost of INF-K8S-PAY-PROD', t); self.assertIn('`PAY-108`', t)
        self.assertIn('an architect confirms before any design changes', t)


if __name__ == '__main__':
    unittest.main()
