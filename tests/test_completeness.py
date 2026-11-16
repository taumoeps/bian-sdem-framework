"""A complete design: every record connected — SDEM's own standard, shipped with it (docs/design/sdem-completeness-design.md CPL-01…CPL-06;
the public twin's audit, 2026-11-17). It is an ordinary standards file read by the profile mechanism (PR-13); nothing here is new machinery
but the `sdem:` include, the default for new workspaces and the one-line summary. Synthetic data only."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def sdem(*args, cwd):
    env = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], cwd=cwd, capture_output=True, text=True, env=env)
    return r.returncode, r.stdout, r.stderr


R = lambda i, t, n, **a: {'op': 'add', 'record': {'id': i, 'type': t, 'version': '1', 'name': n, 'lifecycle_status': a.pop('status', 'planned'), 'attributes': a}}
CS = lambda layer, recs, rels=(): {'layer': layer, 'reason': 'test', 'changes': recs, 'relationships': {'add': [dict(zip(('source', 'kind', 'target'), r)) for r in rels]}}


class CompletenessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, self.tmp, True); self.ws = self.tmp / 'ws'

    def new(self, *extra):
        code, out, err = sdem('new', '--workspace', self.ws, '--person', 'jane.architect', *extra, cwd=self.tmp); self.assertEqual(code, 0, err)

    def propose(self, cs, agent):
        f = self.tmp / 'cs.json'; f.write_text(json.dumps(cs), encoding='utf-8')
        code, out, err = sdem('change', 'propose', f, '--workspace', self.ws, '--agent', agent, '--person', 'jane.architect', cwd=self.tmp); self.assertEqual(code, 0, err)

    def test_the_standard_ships_with_sdem_and_is_an_ordinary_standard(self):   # CPL-01, CPL-02
        from sdem.profile import shipped
        f = shipped('sdem:sdem-completeness.json'); d = json.loads(f.read_text(encoding='utf-8'))
        self.assertEqual((d['format'], d['standard']['id']), ('sdem-standard/1', 'SDEM-COMPLETE'))
        self.assertTrue(all(r['severity'] == 'warning' and r['id'].startswith('CPL-') and r.get('message') for r in d['rules']))   # never an error: a gap is not a wrong design
        with self.assertRaises(Exception): shipped('sdem:../pyproject.toml')

    def test_a_new_workspace_is_checked_for_completeness_without_setup(self):   # CPL-03
        self.new()
        p = json.loads((self.ws / 'sdem-profile.json').read_text(encoding='utf-8'))
        self.assertEqual(p['includes'], ['sdem:sdem-completeness.json'])
        self.assertEqual(sdem('profile', 'check', '--workspace', self.ws, cwd=self.tmp)[0], 0)
        self.assertEqual(sdem('check', '--workspace', self.ws, cwd=self.tmp)[0], 0)

    def test_a_new_organisation_starts_with_it_in_its_base(self):   # CPL-03
        code, out, err = sdem('new', '--organisation', 'bank-xyz', '--person', 'jane.architect', cwd=self.tmp); self.assertEqual(code, 0, err)
        base = json.loads((self.tmp / 'bank-xyz' / 'profiles' / 'bank-xyz-base.json').read_text(encoding='utf-8'))
        self.assertIn('sdem:sdem-completeness.json', base['includes'])

    def test_a_gap_is_a_decision_to_take_never_a_failed_check(self):   # CPL-04
        self.new()
        self.propose(CS('A3', [R('APP-LEDGER', 'A3.ApplicationComponent', 'Account ledger'), R('API-LEDGER', 'A3.ApplicationInterface', 'Ledger internal API'),
                               R('API-RISK', 'A3.ApplicationInterface', 'Risk internal API', status='active'), R('API-OK', 'A3.ApplicationInterface', 'Posting API')],
                        [('APP-LEDGER', 'composition', 'API-OK')]), 'sdem-a3-application')
        code, out, err = sdem('check', '--workspace', self.ws, cwd=self.tmp)
        self.assertEqual(code, 0, out + err)                                   # sdem check: is the design wrong? — a gap is not, so it never fails
        self.assertNotIn('API-LEDGER: CPL-', out); self.assertIn('WARN: level A3 (WS-A3): instance API-RISK: CPL-A3-01', out)   # planned: silent · active: a warning
        c = json.loads(sdem('comply', '--workspace', self.ws, '--json', cwd=self.tmp)[1])
        got = {(f['record'], f['outcome']) for f in c['findings'] if f['rule'] == 'CPL-A3-01'}
        self.assertEqual(got, {('API-LEDGER', 'unresolved'), ('API-RISK', 'non_compliant'), ('API-OK', 'compliant')})   # planned: to do · active: not met (a warning)

    def test_status_says_it_in_one_line(self):   # CPL-05
        self.new()
        self.propose(CS('A3', [R('APP-LEDGER', 'A3.ApplicationComponent', 'Account ledger'), R('API-LEDGER', 'A3.ApplicationInterface', 'Ledger internal API'),
                               R('API-RISK', 'A3.ApplicationInterface', 'Risk internal API'), R('API-OK', 'A3.ApplicationInterface', 'Posting API')],
                        [('APP-LEDGER', 'composition', 'API-OK')]), 'sdem-a3-application')
        s = json.loads(sdem('status', '--workspace', self.ws, '--json', cwd=self.tmp)[1])
        self.assertEqual((s['completeness']['gaps'], s['completeness']['by_rule'][0]['rule'], s['completeness']['by_rule'][0]['records']), (3, 'CPL-A3-01', ['API-LEDGER', 'API-RISK']))   # two interfaces with no component — and the component has no deployment yet (CPL-X-01)
        self.assertFalse([u for u in s['unresolved'] if 'CPL-' in u['text']])   # one summary, not a line per gap
        text = sdem('status', '--workspace', self.ws, cwd=self.tmp)[1]
        self.assertRegex(text, r'Completeness: 1 of 4 records connected \(25%\) — 3 gaps')
        self.assertIn('2 × an interface belongs to the component that offers it', text)

    def test_an_existing_workspace_is_not_changed(self):   # CPL-06
        ws = self.tmp / 'old'; shutil.copytree(ROOT / 'examples' / 'payment-initiation', ws, ignore=shutil.ignore_patterns('graph'))
        self.assertFalse((ws / 'sdem-profile.json').exists())
        s = json.loads(sdem('status', '--workspace', ws, '--json', cwd=self.tmp)[1])
        self.assertIsNone(s.get('completeness'))


if __name__ == '__main__':
    unittest.main()
