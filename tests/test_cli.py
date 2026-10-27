"""The `sdem` command — SDEM's only interface (docs/sdem-workbench-spec.md §3, WB-K01…K06; acceptance AT-WB-09)."""
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
        self.assertIn('A person approves', text)
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
