"""Hardening of the data architecture and tools — group 1 and group 2 (docs/design/sdem-agent-platform-principles.md; spec AG-R06, AG-R07, WB-K07, WB-K08):
D1 coordination ids scoped to the Git branch, one file per record; D2 `sdem check` checks the coordination records;
T3 a warning when a graph store is older than its data; T4 `--estate` and `*` patterns handled by sdem itself;
T1 / AG-S08 direct dataset edits detected and adopted by a person; T2 `sdem approve` and CTL-21 (a person approves)."""
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


    # T1 / AG-S08
    def test_direct_edit_is_detected_and_adopted_by_a_person(self):
        self.propose()
        p = self.est / 'a3-application.json'; d = json.loads(p.read_text())
        d['instances'][0]['description'] = 'edited by hand'; p.write_text(json.dumps(d, indent=2))
        self.assertEqual(sdem('check', '--estate', self.est)[0], 0)          # A3 has no change sets yet: its content is the starting point
        a4 = self.est / 'a4-technology.json'; d = json.loads(a4.read_text()); d['instances'][0]['name'] = 'renamed by hand'; a4.write_text(json.dumps(d, indent=2))
        code, out, _ = sdem('check', '--estate', self.est)
        self.assertEqual(code, 1); self.assertIn('CTL-20 (AG-S08): a4-technology.json was changed outside a change set since CS-001', out)
        self.assertNotEqual(sdem('change', 'adopt', '--estate', self.est, '--layer', 'A4', '--person', 'sdem-a4-technology', '--reason', 'x')[0], 0)
        code, out, err = sdem('change', 'adopt', '--estate', self.est, '--layer', 'A4', '--person', 'jane.architect', '--reason', 'renamed after review')
        self.assertEqual(code, 0, err); self.assertIn("records jane.architect's direct edit of A4: 1 update", out)
        self.assertEqual(sdem('check', '--estate', self.est)[0], 0)
        self.assertNotEqual(sdem('change', 'adopt', '--estate', self.est, '--layer', 'A4', '--person', 'jane.architect', '--reason', 'again')[0], 0)  # nothing to adopt

    # T2 / CTL-21
    def test_approve_writes_a_valid_record_and_only_for_a_person(self):
        reg = json.loads((self.est / 'mappings.json').read_text()); reg['mappings'] = [m for m in reg['mappings'] if m['mapping_id'] != 'PAY-106']
        (self.est / 'mappings.json').write_text(json.dumps(reg, indent=2))
        sdem('link', '--estate', self.est, '--out', self.tmp / 'l'); props = self.tmp / 'l' / 'proposals.json'
        base = ('approve', 'P-RUN-001', '--proposals', props, '--estate', self.est)
        code, _, err = sdem(*base, '--reviewer', 'sdem-orchestrator', '--evidence', 'application_architecture_document:X'); self.assertEqual(code, 1); self.assertIn('CTL-21', err)
        code, _, err = sdem(*base, '--reviewer', 'copilot', '--evidence', 'application_architecture_document:X'); self.assertEqual(code, 1)
        code, _, err = sdem(*base, '--reviewer', 'jane.architect', '--evidence', 'deployment_design:X'); self.assertEqual(code, 1); self.assertIn('nothing was written', err)
        self.assertNotIn('P-RUN-001', (self.est / 'mappings.json').read_text())
        code, out, err = sdem(*base, '--reviewer', 'jane.architect', '--evidence', 'application_architecture_document:AA#s3', '--date', '2026-10-28')
        self.assertEqual(code, 0, err); self.assertIn('approved PAY-114', out)
        self.assertEqual(sdem('validate', '--strict', '--estate', self.est)[0], 0)
        self.assertEqual(sdem(*base, '--reviewer', 'jane.architect', '--evidence', 'application_architecture_document:AA')[0], 1)   # already approved

    def test_validate_rejects_an_agent_as_reviewer(self):
        reg = json.loads((self.est / 'mappings.json').read_text()); reg['mappings'][0]['reviewer_id'] = 'sdem-a1-business'
        (self.tmp / 'r.json').write_text(json.dumps(reg))
        code, out, err = sdem('validate', self.tmp / 'r.json')
        self.assertEqual(code, 1); self.assertIn('CTL-21', out + err)

    # T5 / AG-K06
    def test_round_limit_is_a_cap_an_agent_cannot_raise(self):  # AG-S07
        self.propose(); e = agents.Estate(self.est)
        with self.assertRaises(agents.CoordinationError) as c: e.plan('CE-001', 'sdem-orchestrator', 'jane', max_rounds=agents.MAX_ROUNDS + 1)
        self.assertIn('never raise it', str(c.exception))
        self.assertIn('stopped', e.plan('CE-001', 'sdem-orchestrator', 'jane', max_rounds=0))       # lowering is allowed
        r = agents.Estate(self.est).plan('CE-001', 'architect', 'jane', max_rounds=agents.MAX_ROUNDS + 2)   # the architect may raise it
        self.assertNotIn('stopped', r)

    def test_revert_restores_the_layer_exactly_and_on_record(self):
        orig = (self.est / 'a4-technology.json').read_text()
        self.propose(); agents.Estate(self.est).plan('CE-001', 'sdem-orchestrator', 'jane')
        self.assertNotEqual(sdem('change', 'revert', 'CS-001', '--estate', self.est, '--agent', 'sdem-a3-application', '--person', 'jane')[0], 0)   # CTL-19
        self.assertNotEqual(sdem('change', 'revert', 'CS-001', '--estate', self.est, '--agent', 'sdem-a4-technology', '--person', '')[0], 0)       # CTL-20
        code, out, err = sdem('change', 'revert', 'CS-001', '--estate', self.est, '--agent', 'sdem-a4-technology', '--person', 'jane', '--reason', 'postponed')
        self.assertEqual(code, 0, err); self.assertIn('CS-002 reverts CS-001', out); self.assertIn('cancelled open work items WI-001, WI-002', out)
        self.assertEqual((self.est / 'a4-technology.json').read_text(), orig)
        self.assertEqual(sdem('check', '--estate', self.est)[0], 0)
        self.assertIn('not the latest change set', sdem('change', 'revert', 'CS-001', '--estate', self.est, '--agent', 'sdem-a4-technology', '--person', 'jane')[2])

if __name__ == '__main__':
    unittest.main()
