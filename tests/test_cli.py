"""The `sdem` command — SDEM's only interface (docs/design/sdem-workbench-spec.md §3, WB-K01…K06; acceptance AT-WB-09)."""
import contextlib, io, json, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem import cli  # noqa: E402

E = ROOT / 'examples' / 'payment-initiation'


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try: code = cli.main(list(argv))
        except SystemExit as e: code = e.code
    return code, out.getvalue(), err.getvalue()


class CliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix='sdem-cli-'))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_workspace_option_and_its_old_name(self):   # "estate" was renamed "workspace" (2026-10-30); --estate still works when typed
        ws = str(ROOT / 'examples' / 'payment-initiation')
        for opt in ('--workspace', '--estate'):
            self.assertEqual(run('check', opt, ws)[0], 0, opt)
            self.assertEqual(run('dashboard', opt, ws, '-o', str(Path(tempfile.mkdtemp()) / 'd.html'))[0], 0, opt)

    def test_link_shows_its_proposals_for_review(self):   # sdem link then sdem review in one step; --no-review just writes them
        out = Path(tempfile.mkdtemp()); ws = out / 'ws'   # the example as it was before its links were approved
        shutil.copytree(ROOT / 'examples' / 'payment-initiation', ws, ignore=shutil.ignore_patterns('graph', 'migrations'))
        shutil.copy(ws / 'm1-mappings-given.json', ws / 'mappings.json')
        code, text, _ = run('link', '--workspace', str(ws), '--out', str(out / 'a'))
        self.assertEqual(code, 0); self.assertIn('weakest first', text); self.assertIn('Review again any time: sdem review', text)
        code, text, _ = run('link', '--workspace', str(ws), '--out', str(out / 'b'), '--no-review')
        self.assertEqual(code, 0); self.assertNotIn('weakest first', text); self.assertIn('next: sdem review', text)
        self.assertEqual(json.loads((out / 'a' / 'proposals.json').read_text()), json.loads((out / 'b' / 'proposals.json').read_text()))

    def test_trace_names_the_layer_and_the_connections_it_followed(self):
        code, out, _ = run('trace', 'PRC-PAY-01', '--direction', 'down', '--graph', str(ROOT / 'examples' / 'payment-initiation' / 'graph'))
        self.assertEqual(code, 0)
        self.assertIn("'Capture and validate payment instruction'  [A1 Business · Business Process]", out)
        self.assertIn('[A2 BIAN · Service Domain]', out); self.assertIn('[A4 Technology ·', out)
        self.assertIn('CONNECTIONS FOLLOWED', out); self.assertRegex(out, r'PAY-003 .*: approved by [a-z.]+ on \d{4}-\d{2}-\d{2}; evidence ')

    def test_trace_a_whole_layer(self):   # TR-L01…L04
        G = str(ROOT / 'examples' / 'payment-initiation' / 'graph')
        code, out, _ = run('trace', 'A4', '--direction', 'upstream', '--graph', G)
        self.assertEqual(code, 0); self.assertIn('A4 Technology — 12 record(s), traced up', out); self.assertIn('connected from above: 5 of 12', out)
        self.assertIn("INF-PG-PAY-PROD 'Managed PostgreSQL — payments'", out)                       # a gap: supports nothing above
        self.assertIn('Payments Hub ← Payment Initiation (synthetic selection) ← Initiate Payment', out)
        code, out, _ = run('trace', 'a2', '--direction', 'up', '--only-gaps', '--graph', G)            # only kinds that can connect up count as gaps
        self.assertIn('(gaps): 3', out); self.assertIn("SD-PE 'Payment Execution (synthetic selection)'", out); self.assertNotIn('AT-AUTH', out); self.assertNotIn('CHAINS', out)
        code, out, _ = run('trace', 'A2', '--direction', 'all', '--to', 'A3', '--graph', G)            # --to applies only in its own direction
        self.assertIn('traced down to A3 Application', out); self.assertIn('A2 BIAN — 24 record(s), traced up\n', out)
        f = Path(tempfile.mkdtemp()) / 'chains.csv'
        code, out, _ = run('trace', 'A1', '--direction', 'downstream', '--csv', str(f), '--graph', G)
        self.assertEqual(code, 0); rows = f.read_text().splitlines()
        self.assertEqual(rows[0].split(',')[:3], ['direction', 'start_layer', 'start_id']); self.assertTrue(any('gap: connected to nothing' in r for r in rows))

    def test_help_lists_every_journey(self):
        code, out, _ = run('--help')
        self.assertEqual(code, 0)
        for name in cli.JOURNEYS: self.assertIn(f'  {name} ', out)
        for j in ('J1', 'J2', 'J3', 'J4', 'J5', 'J6', 'J7', 'J8'): self.assertIn(j, out)

    def test_every_subcommand_help_has_an_example_and_the_sdem_name(self):
        for name in cli.JOURNEYS:
            code, out, _ = run(name, '--help')
            self.assertEqual(code, 0, name)
            self.assertIn(f'sdem {name}', out, name)
            self.assertIn('Example', out, name)

    def test_exit_codes(self):
        self.assertEqual(run()[0], 2)
        self.assertEqual(run('no-such-command')[0], 2)
        self.assertEqual(run('check', *map(str, sorted(E.glob('a*.json'))), str(E / 'mappings.json'))[0], 0)

    def test_link_review_and_explain(self):
        out = self.tmp / 'links'
        levels = [str(E / f) for f in ('a1-business.json', 'a2-service-domain.json', 'a3-application.json')]
        code, text, _ = run('link', *levels, '--out', str(out))
        self.assertEqual(code, 0); self.assertTrue((out / 'proposals.json').exists())
        n = len(json.loads((out / 'proposals.json').read_text())['mappings'])
        code, text, _ = run('review', str(out / 'proposals.json'), '--json')
        rows = json.loads(text)
        self.assertEqual(len(rows), n)
        self.assertEqual([r['confidence'] for r in rows], sorted(r['confidence'] for r in rows))  # weakest first
        self.assertTrue(all(r['rule'] != '—' and r['reasoning'] for r in rows))
        code, text, _ = run('review', str(out / 'proposals.json'))
        self.assertIn('To approve (a person', text); self.assertIn('sdem approve', text)
        code, text, _ = run('explain', rows[0]['mapping_id'], '--proposals', str(out / 'proposals.json'), '--json')
        self.assertEqual(code, 0); self.assertEqual(json.loads(text)[0]['id'], rows[0]['mapping_id'])
        self.assertEqual(run('explain', 'NOT-THERE', '--proposals', str(out / 'proposals.json'))[0], 1)

    def test_python_dash_m_sdem_works_without_installing(self):
        r = subprocess.run([sys.executable, '-m', 'sdem', '--help'], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0); self.assertIn('Journeys', r.stdout)

    def test_model_check_matches_ci(self):
        code, out, _ = run('model', 'check')
        self.assertEqual(code, 0, out)
        for g in cli.GENERATORS: self.assertIn(g, out)


if __name__ == '__main__':
    unittest.main()
