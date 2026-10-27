"""Group 1 hardening of the data architecture and tools (docs/sdem-agent-platform-principles.md; spec AG-R06, AG-R07, WB-K07, WB-K08):
D1 coordination ids scoped to the Git branch, one file per record; D2 `sdem check` checks the coordination records;
T3 a warning when a graph store is older than its data; T4 `--estate` and `*` patterns handled by sdem itself."""
import contextlib, io, json, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem import agents, cli  # noqa: E402

SRC = ROOT / 'examples' / 'payment-initiation'
CS4 = ROOT / '.github' / 'skills' / 'sdem-change-sets' / 'example-a4-rehost.json'


def sdem(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try: code = cli.main([str(a) for a in argv])
        except SystemExit as e: code = e.code if isinstance(e.code, int) else 1; err.write(str(e.code))
    return code, out.getvalue(), err.getvalue()


def git(d, *a): subprocess.run(['git', *a], cwd=d, check=True, capture_output=True)


class HardeningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='sdem-hard-'))
        self.est = self.tmp / 'est'; shutil.copytree(SRC, self.est, ignore=shutil.ignore_patterns('graph'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def propose(self):
        return sdem('change', 'propose', CS4, '--estate', self.est, '--agent', 'sdem-a4-technology', '--person', 'jane')

    # D1
    def test_ids_are_scoped_to_the_branch_and_one_file_per_record(self):
        git(self.tmp, 'init', '-q'); git(self.tmp, '-c', 'user.email=t@t', '-c', 'user.name=t', 'commit', '-q', '--allow-empty', '-m', 'x')
        git(self.tmp, 'checkout', '-q', '-b', 'feature/Rehost_Payments')
        code, out, err = self.propose()
        self.assertEqual(code, 0, err)
        self.assertTrue((self.est / 'coordination' / 'change-sets' / 'CS-feature-rehost-payments-001.json').exists())
        self.assertTrue((self.est / 'coordination' / 'events' / 'CE-feature-rehost-payments-001.json').exists())
        self.assertFalse((self.est / 'coordination' / 'events.json').exists())
        e = agents.Estate(self.est)
        r = e.plan('CE-feature-rehost-payments-001', 'sdem-orchestrator', 'jane')
        self.assertEqual([w['id'] for w in r['work_items']], ['WI-feature-rehost-payments-001', 'WI-feature-rehost-payments-002'])
        git(self.tmp, 'checkout', '-q', '-b', 'other')          # another branch never reuses the same ids
        self.assertEqual(e._next('CS'), 'CS-other-001')

    def test_outside_git_ids_stay_plain(self):
        self.assertEqual(self.propose()[0], 0)
        self.assertTrue((self.est / 'coordination' / 'change-sets' / 'CS-001.json').exists())

    # D2
    def test_check_includes_the_coordination_records(self):
        self.propose()
        code, out, _ = sdem('check', '--estate', self.est)
        self.assertEqual(code, 0); self.assertIn('OK: coordination (2 records)', out)
        p = self.est / 'coordination' / 'events' / 'CE-001.json'; d = json.loads(p.read_text()); d.pop('person'); p.write_text(json.dumps(d))
        code, out, _ = sdem('check', '--estate', self.est)
        self.assertEqual(code, 1); self.assertIn("events/CE-001: $: missing required property 'person'", out)
        (self.est / 'coordination' / 'events' / 'CE-009.json').write_text(json.dumps({**d, 'id': 'CE-010'}))
        code, out, _ = sdem('check', '--estate', self.est)
        self.assertIn('file name does not match its id', out)

    # T3
    def test_out_of_date_graph_store_is_warned(self):
        g = self.tmp / 'g'
        self.assertEqual(sdem('build', '--estate', self.est, '--out', g)[0], 0)
        self.assertNotIn('out of date', sdem('trace', 'APP-PAY-HUB', '--graph', g)[2])
        code, out, _ = self.propose(); self.assertIn('graph stores built from this estate are now out of date', out)
        _, _, err = sdem('trace', 'APP-PAY-HUB', '--graph', g)
        self.assertIn('WARN: the graph store is out of date', err); self.assertIn('a4-technology.json', err)
        _, _, err = sdem('view', '--graph', g, '-o', self.tmp / 'v.html')
        self.assertIn('out of date', err)

    # T4
    def test_estate_option_and_patterns(self):
        self.assertEqual(sdem('check', '--estate', self.est)[0], 0)
        self.assertEqual(sdem('validate', '--strict', '--estate', self.est)[0], 0)
        self.assertEqual(sdem('link', '--estate', self.est, '--out', self.tmp / 'l')[0], 0)
        self.assertEqual(sdem('trace', 'PRC-PAY-01', '--estate', self.est)[0], 0)
        self.assertEqual(sdem('check', f'{self.est}/a*.json', f'{self.est}/mappings.json')[0], 0)   # unexpanded pattern, as PowerShell passes it
        code, _, err = sdem('check', '--estate', self.tmp / 'nope')
        self.assertNotEqual(code, 0); self.assertIn('not an estate folder', err)


if __name__ == '__main__':
    unittest.main()
