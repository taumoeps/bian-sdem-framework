"""The order of a complete first draft is in the tool, not in anyone's memory (docs/design/sdem-completeness-design.md CPL-16…CPL-18; the
skill `sdem-complete-draft`): `sdem aid` consults every pattern SDEM ships that fits, included or not, and names them; `sdem status` prints
the steps in the skill's order; a pattern's block says where the draft stands as well as what is confirmed. Synthetic data only."""
import json, os, re, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}
SKILL = ROOT / '.github' / 'skills' / 'sdem-complete-draft' / 'SKILL.md'
ORDER = ['sdem profile include', 'sdem aid --workspace', 'sdem link --workspace', 'sdem aid confirm', 'sdem approve']   # steps 4, 5, 6, 9


def rec(i, t, n, **a): return {'id': i, 'type': t, 'version': '1', 'name': n, 'lifecycle_status': 'planned', 'attributes': a}


import sys as _s, pathlib as _pl; _s.path.insert(0, str(_pl.Path(__file__).resolve().parent)); from needs import bian as _needs_bian  # noqa: E402 — BX-15: tests that need sdem-bian

@_needs_bian
class Order(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, self.tmp, True); self.ws = self.tmp / 'ws'

    def sdem(self, *a, ok=True):
        r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, a)], cwd=self.tmp, capture_output=True, text=True, env=ENV)
        if ok: self.assertEqual(r.returncode, 0, (r.stdout + r.stderr)[-800:])
        return r.stdout

    def propose(self, layer, agent, recs, rels=()):
        f = self.tmp / f'{layer}.json'
        f.write_text(json.dumps({'layer': layer, 'reason': 'test', 'changes': [{'op': 'add', 'record': r} for r in recs],
                                 'relationships': {'add': [dict(zip(('source', 'kind', 'target'), r)) for r in rels]}}), encoding='utf-8')
        self.sdem('change', 'propose', f, '--workspace', self.ws, '--agent', agent, '--person', 'jane.architect')

    def design(self):
        self.sdem('new', '--with', 'bian', '--workspace', self.ws, '--person', 'jane.architect')
        self.sdem('bian', 'add', 'Payment Order Initiation', '--workspace', self.ws, '--person', 'jane.architect')
        self.propose('business', 'sdem-a1-business', [rec('PROC-PAY', 'A1.BusinessProcess', 'Take the payment'), rec('PROC-SCREEN', 'A1.BusinessProcess', 'Screen for fraud')])
        self.propose('application', 'sdem-a3-application', [rec('APP-HUB', 'A3.ApplicationComponent', 'Payments hub'), rec('API-HUB', 'A3.ApplicationInterface', 'Hub API'), rec('API-X', 'A3.ApplicationInterface', 'Other')])
        self.propose('technology', 'sdem-a4-technology', [rec('DEP-HUB', 'A4.Deployment', 'Payments hub — production', component_id='APP-HUB')])

    def test_the_skill_lists_the_steps_in_this_order(self):   # CPL-18
        text = SKILL.read_text(encoding='utf-8'); at = [text.index(c) for c in ORDER]
        self.assertEqual(at, sorted(at), 'the skill must name the steps in the order: include, infer, list the links, confirm, approve')
        self.assertIn('Never run step 5 before step 4', text); self.assertIn('--complete-draft', text)
        for f in ('.claude', '.agents'):   # every agent platform gets the same skill
            self.assertEqual((ROOT / f / 'skills' / 'sdem-complete-draft' / 'SKILL.md').read_text(encoding='utf-8'), text)

    def test_status_prints_them_in_the_same_order(self):   # CPL-17, CPL-18
        self.design()
        nxt = [n['command'] for n in json.loads(self.sdem('status', '--workspace', self.ws, '--json'))['next']]
        at = [next((i for i, c in enumerate(nxt) if c.startswith(o)), None) for o in ORDER[:3]]
        self.assertNotIn(None, at, nxt); self.assertEqual(at, sorted(at), nxt)
        self.assertIn('--complete-draft', nxt[at[1]])
        self.sdem('aid', '--workspace', self.ws, '--person', 'jane.architect', '--complete-draft'); self.sdem('link', '--workspace', self.ws, '--out', self.ws / 'links', '--no-review')
        nxt = [n['command'] for n in json.loads(self.sdem('status', '--workspace', self.ws, '--json'))['next']]
        at = [next((i for i, c in enumerate(nxt) if c.startswith(o)), None) for o in ('sdem profile include', 'sdem aid confirm', 'sdem approve')]
        self.assertNotIn(None, at, nxt); self.assertEqual(at, sorted(at), nxt)

    def test_aid_consults_every_pattern_that_fits_and_names_them(self):   # CPL-16
        self.design()   # nobody has included a pattern
        run = json.loads(self.sdem('aid', '--workspace', self.ws, '--person', 'jane.architect', '--json'))
        got = {(p['id'], p['included']) for p in run['draft']['patterns_consulted']}
        self.assertEqual(got, {('PAT-PAYMENT-INITIATION', False), ('PAT-BIAN-TRANSACT', False)})
        self.assertIn('SD-FRAUD-EVALUATION', run['draft']['domains_added'])   # the pattern was asked first: its domain, not a name match's
        self.assertNotIn('sdem:sdem-pattern-payment-initiation.json', json.loads((self.ws / 'sdem-profile.json').read_text(encoding='utf-8'))['includes'])   # consulting is not including
        text = self.sdem('aid', '--workspace', self.ws, '--person', 'jane.architect', '--dry-run')
        self.assertRegex(text, r'patterns consulted: .*Payment initiation \(fits the design; not in the profile')

    def test_a_pattern_says_where_the_draft_stands_too(self):   # CPL-15 for patterns
        self.design()
        self.sdem('profile', 'include', 'sdem:sdem-pattern-bian-transact.json', '--workspace', self.ws, '--person', 'jane.architect')
        self.sdem('aid', '--workspace', self.ws, '--person', 'jane.architect'); self.sdem('link', '--workspace', self.ws, '--out', self.ws / 'links', '--no-review')
        s = json.loads(self.sdem('status', '--workspace', self.ws, '--json'))
        p = next(x for x in s['patterns'] if x['pattern'] == 'PAT-BIAN-TRANSACT')
        self.assertGreater(p['draft_in_place'], p['in_place'])   # the deployment is proposed, not approved: in the draft, not yet in place
        self.assertRegex(self.sdem('status', '--workspace', self.ws), r'Pattern BIAN Transact .*: \d+ of \d+ parts in place — \d+ to decide; in the draft: \d+ of \d+')


if __name__ == '__main__':
    unittest.main()
