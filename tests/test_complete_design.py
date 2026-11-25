"""A complete design: every record connected — SDEM's own standard, shipped with it (docs/design/sdem-completeness-design.md CPL-01…CPL-06;
the public twin's audit, 2026-11-17). It is an ordinary standards file read by the profile mechanism (PR-13); nothing here is new machinery
but the `sdem:` include, the default for new workspaces and the one-line summary. Synthetic data only."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(Path(__file__).resolve().parent))
from forms import migrated   # noqa: E402 — a layer's number in either form


def sdem(*args, cwd):
    env = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], cwd=cwd, capture_output=True, text=True, env=env)
    return r.returncode, r.stdout, r.stderr


R = lambda i, t, n, **a: {'op': 'add', 'record': {'id': i, 'type': t, 'version': '1', 'name': n, 'lifecycle_status': a.pop('status', 'planned'), 'attributes': a}}
CS = lambda layer, recs, rels=(): {'layer': layer, 'reason': 'test', 'changes': recs, 'relationships': {'add': [dict(zip(('source', 'kind', 'target'), r)) for r in rels]}}


import sys as _s, pathlib as _pl; _s.path.insert(0, str(_pl.Path(__file__).resolve().parent)); from needs import bian as _needs_bian  # noqa: E402 — BX-15: tests that need sdem-bian

@_needs_bian
class CompletenessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, self.tmp, True); self.ws = self.tmp / 'ws'

    def new(self, *extra):
        code, out, err = sdem('new', '--with', 'bian', '--workspace', self.ws, '--person', 'jane.architect', *extra, cwd=self.tmp); self.assertEqual(code, 0, err)

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
        self.propose(CS('application', [R('APP-LEDGER', 'A3.ApplicationComponent', 'Account ledger'), R('API-LEDGER', 'A3.ApplicationInterface', 'Ledger internal API'),
                               R('API-RISK', 'A3.ApplicationInterface', 'Risk internal API', status='active'), R('API-OK', 'A3.ApplicationInterface', 'Posting API')],
                        [('APP-LEDGER', 'composition', 'API-OK')]), 'sdem-a3-application')
        code, out, err = sdem('check', '--workspace', self.ws, cwd=self.tmp)
        self.assertEqual(code, 0, out + err)                                   # sdem check: is the design wrong? — a gap is not, so it never fails
        self.assertNotIn('API-LEDGER: CPL-', out); self.assertIn(f"WARN: level {'A4' if migrated(self.ws) else 'A3'} (WS-A3): instance API-RISK: CPL-A3-01", out)   # Application's number; the rule id stays   # planned: silent · active: a warning
        c = json.loads(sdem('comply', '--workspace', self.ws, '--json', cwd=self.tmp)[1])
        got = {(f['record'], f['outcome']) for f in c['findings'] if f['rule'] == 'CPL-A3-01'}
        self.assertEqual(got, {('API-LEDGER', 'unresolved'), ('API-RISK', 'non_compliant'), ('API-OK', 'compliant')})   # planned: to do · active: not met (a warning)

    def test_status_says_it_in_one_line(self):   # CPL-05
        self.new()
        self.propose(CS('application', [R('APP-LEDGER', 'A3.ApplicationComponent', 'Account ledger'), R('API-LEDGER', 'A3.ApplicationInterface', 'Ledger internal API'),
                               R('API-RISK', 'A3.ApplicationInterface', 'Risk internal API'), R('API-OK', 'A3.ApplicationInterface', 'Posting API')],
                        [('APP-LEDGER', 'composition', 'API-OK')]), 'sdem-a3-application')
        s = json.loads(sdem('status', '--workspace', self.ws, '--json', cwd=self.tmp)[1])
        self.assertEqual((s['completeness']['gaps'], s['completeness']['by_rule'][0]['rule'], s['completeness']['by_rule'][0]['records']), (3, 'CPL-A3-01', ['API-LEDGER', 'API-RISK']))   # two interfaces with no component — and the component has no deployment yet (CPL-X-01)
        self.assertFalse([u for u in s['unresolved'] if 'CPL-' in u['text']])   # one summary, not a line per gap
        text = sdem('status', '--workspace', self.ws, cwd=self.tmp)[1]
        self.assertRegex(text, r'Completeness: 1 of 4 records connected \(25%\) — 3 gaps')
        self.assertIn('2 × an interface belongs to the component that offers it', text)

    def test_status_says_it_once_for_active_records_too(self):   # CPL-05 — found loading a design through sdem transform: its records are active, and each gap was also a warning line
        self.new()
        self.propose(CS('application', [R('APP-LEDGER', 'A3.ApplicationComponent', 'Account ledger', status='active'), R('API-ONE', 'A3.ApplicationInterface', 'One', status='active'),
                               R('API-TWO', 'A3.ApplicationInterface', 'Two', status='active')]), 'sdem-a3-application')
        s = json.loads(sdem('status', '--workspace', self.ws, '--json', cwd=self.tmp)[1])
        self.assertEqual(s['completeness']['by_rule'][0]['records'], ['API-ONE', 'API-TWO'])
        self.assertFalse([x['text'] for x in s['warnings'] + s['unresolved'] + s['blocking'] if 'CPL-' in x['text']])
        self.assertIn('CPL-A3-01', sdem('check', '--workspace', self.ws, cwd=self.tmp)[1])   # sdem check still says each one

    def test_at_least_one_of_several_links(self):   # PR-35, CPL-07: an actor, an image
        self.new()
        self.propose(CS('business', [R('ACTOR-MERCHANT', 'A1.BusinessActor', 'Merchant'), R('ACTOR-CUSTOMER', 'A1.BusinessActor', 'Customer'), R('ACTOR-TPP', 'A1.BusinessActor', 'Provider'),
                               R('ROLE-PAYER', 'A1.BusinessRole', 'Payer'), R('IF-WEB', 'A1.BusinessInterface', 'Web channel', channel_kind='web')],
                        [('ACTOR-CUSTOMER', 'assignment', 'ROLE-PAYER'), ('IF-WEB', 'serving', 'ACTOR-TPP')]), 'sdem-a1-business')
        self.propose(CS('technology', [R('ART-A', 'A4.Artifact', 'hub image'), R('ART-B', 'A4.Artifact', 'api image'), R('NODE-1', 'A4.Node', 'compute')], [('NODE-1', 'assignment', 'ART-B')]), 'sdem-a4-technology')
        c = json.loads(sdem('comply', '--workspace', self.ws, '--json', cwd=self.tmp)[1])
        got = {(f['rule'], f['record']): f['outcome'] for f in c['findings'] if f['rule'] in ('CPL-A1-05', 'CPL-A4-02')}
        self.assertEqual(got, {('CPL-A1-05', 'ACTOR-MERCHANT'): 'unresolved', ('CPL-A1-05', 'ACTOR-CUSTOMER'): 'compliant', ('CPL-A1-05', 'ACTOR-TPP'): 'compliant',
                               ('CPL-A4-02', 'ART-A'): 'unresolved', ('CPL-A4-02', 'ART-B'): 'compliant'})
        why = next(f['detail'] for f in c['findings'] if f['record'] == 'ACTOR-MERCHANT' and f['rule'] == 'CPL-A1-05')
        self.assertIn('none of: assignment to any record · serving from any record · approved SERVED_BY to any record', why)

    def test_a_rule_that_names_no_link_is_refused(self):   # PR-35
        self.new()
        p = self.ws / 'sdem-profile.json'; d = json.loads(p.read_text(encoding='utf-8'))
        d['rules'] = [{'id': 'X-1', 'entity': 'A1.BusinessActor', 'any_link': [{'direction': 'in'}, {'kind': 'no-such-kind'}], 'message': 'x'}]; p.write_text(json.dumps(d), encoding='utf-8')
        code, out, err = sdem('profile', 'check', '--workspace', self.ws, cwd=self.tmp)
        self.assertNotEqual(code, 0); self.assertIn('each any_link names a kind', out + err); self.assertIn("any_link kind 'no-such-kind'", out + err)

    def test_a_product_and_an_application_event_are_checked_too(self):   # CPL-20 — found in the picture of a design SDEM had called 100% connected
        self.new()
        self.propose(CS('business', [R('PROD-A', 'A1.Product', 'Account'), R('PROD-B', 'A1.Product', 'Other'), R('SVC-1', 'A1.BusinessService', 'Service'), R('PROC-1', 'A1.BusinessProcess', 'Do it')],
                        [('PROD-A', 'aggregation', 'SVC-1'), ('PROC-1', 'realization', 'SVC-1')]), 'sdem-a1-business')
        self.propose(CS('application', [R('APP-1', 'A3.ApplicationComponent', 'App'), R('EVT-A', 'A3.Event', 'Raised'), R('EVT-B', 'A3.Event', 'Orphan')], [('APP-1', 'triggering', 'EVT-A')]), 'sdem-a3-application')
        c = json.loads(sdem('comply', '--workspace', self.ws, '--json', cwd=self.tmp)[1])
        got = {(f['rule'], f['record']): f['outcome'] for f in c['findings'] if f['rule'] in ('CPL-A1-06', 'CPL-A3-06')}
        self.assertEqual(got, {('CPL-A1-06', 'PROD-A'): 'compliant', ('CPL-A1-06', 'PROD-B'): 'unresolved', ('CPL-A3-06', 'EVT-A'): 'compliant', ('CPL-A3-06', 'EVT-B'): 'unresolved'})

    def test_no_kind_of_record_is_left_unchecked(self):   # CPL-20: the hole is closed for good — a kind of record the standard has no rule for cannot be called connected
        from sdem.metamodel import Metamodel
        mm = Metamodel.base(); rules = json.loads((ROOT / 'standards' / 'sdem-completeness.json').read_text(encoding='utf-8'))['rules']
        unchecked = [t for t, e in sorted(mm.entities.items()) if e['level'] in ('A1', 'A3', 'A4') and not e.get('abstract') and not e.get('artefact')
                     and not any(mm.is_a(t, r['entity']) for r in rules)]
        self.assertEqual(unchecked, [], 'every kind of record an author may write has a completeness rule')

    def test_an_existing_workspace_is_not_changed(self):   # CPL-06
        ws = self.tmp / 'old'; shutil.copytree(ROOT / 'examples' / 'payment-initiation', ws, ignore=shutil.ignore_patterns('graph'))
        self.assertFalse((ws / 'sdem-profile.json').exists())
        s = json.loads(sdem('status', '--workspace', ws, '--json', cwd=self.tmp)[1])
        self.assertIsNone(s.get('completeness'))


if __name__ == '__main__':
    unittest.main()
