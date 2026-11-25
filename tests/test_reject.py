"""sdem reject — a person rejects a proposed link between layers (docs/design/sdem-public-twin-follow-up-design.md RJ-01…RJ-07;
the public twin's first run, F14). Synthetic examples only."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys as _s2, pathlib as _pl2; _s2.path.insert(0, str(_pl2.Path(__file__).resolve().parent)); from needs import EXAMPLES  # noqa: E402 — SDEM's examples and sdem-bian's (R-D6)
sys.path.insert(0, str(ROOT))
EX = EXAMPLES / 'payment-initiation'


def sdem(*args, cwd):
    env = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], cwd=cwd, capture_output=True, text=True, env=env)
    return r.returncode, r.stdout, r.stderr


import sys as _s, pathlib as _pl; _s.path.insert(0, str(_pl.Path(__file__).resolve().parent)); from needs import bian as _needs_bian  # noqa: E402 — BX-15: tests that need sdem-bian

@_needs_bian
class RejectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, self.tmp, True)
        self.ws = self.tmp / 'ws'; shutil.copytree(EX, self.ws, ignore=shutil.ignore_patterns('graph'))
        m = json.loads((self.ws / 'mappings.json').read_text(encoding='utf-8'))
        self.gone = next(x for x in m['mappings'] if x['relationship'] == 'DEPLOYED_AS')   # an approved link taken out, so the engine proposes it again
        m['mappings'] = [x for x in m['mappings'] if x is not self.gone]; (self.ws / 'mappings.json').write_text(json.dumps(m, indent=2), encoding='utf-8')
        self.key = (self.gone['source']['id'], 'DEPLOYED_AS', self.gone['target']['id'])

    def link(self):
        code, out, err = sdem('link', '--workspace', self.ws, '--out', self.ws / 'links', '--no-review', cwd=self.tmp)
        self.assertEqual(code, 0, err)
        return json.loads((self.ws / 'links' / 'proposals.json').read_text(encoding='utf-8'))['mappings'], err

    def pid(self):
        return next(p['mapping_id'] for p in self.link()[0] if (p['source']['id'], p['relationship'], p['target']['id']) == self.key)

    def reject(self, pid, *extra, who='jane.architect'):
        return sdem('reject', pid, '--proposals', self.ws / 'links' / 'proposals.json', '--workspace', self.ws, '--reviewer', who, *extra, cwd=self.tmp)

    def test_a_person_rejects_with_a_reason(self):   # RJ-01
        pid = self.pid()
        code, out, err = self.reject(pid, '--reason', 'not how it is deployed', who='sdem-a3-application')
        self.assertEqual(code, 1); self.assertIn('CTL-21', err)
        code, out, err = self.reject(pid)
        self.assertNotEqual(code, 0); self.assertIn('--reason', err)
        code, out, err = self.reject(pid, '--reason', 'not how it is deployed', '--dry-run')
        self.assertEqual(code, 0, err); self.assertIn('would reject', out)
        self.assertNotIn('rejected', {m['status'] for m in json.loads((self.ws / 'mappings.json').read_text(encoding='utf-8'))['mappings']})

    def test_it_is_recorded_remembered_and_never_an_arrow(self):   # RJ-02, RJ-03, RJ-06
        pid = self.pid()
        code, out, err = self.reject(pid, '--reason', 'not how it is deployed')
        self.assertEqual(code, 0, err)
        r = next(m for m in json.loads((self.ws / 'mappings.json').read_text(encoding='utf-8'))['mappings'] if m['status'] == 'rejected')
        self.assertEqual(((r['source']['id'], r['relationship'], r['target']['id']), r['reviewer_id']), (self.key, 'jane.architect'))
        self.assertTrue(r['approved_at']); self.assertIn('not how it is deployed', r['rationale'])
        gd = [json.loads(f.read_text(encoding='utf-8')) for f in (self.ws / 'decisions').glob('GD-*.json')]
        self.assertEqual([(g['kind'], g['subject'], g['details']['reason']) for g in gd if g['kind'] == 'reject_link'], [('reject_link', r['mapping_id'], 'not how it is deployed')])
        self.assertEqual(sdem('validate', '--workspace', self.ws, cwd=self.tmp)[0], 0)
        props, err = self.link()
        self.assertNotIn(self.key, {(p['source']['id'], p['relationship'], p['target']['id']) for p in props})   # RJ-03: not proposed again
        self.assertIn('1 link(s) a person rejected', err)                                                       # …and said
        code, out, err = sdem('review', self.ws / 'links' / 'proposals.json', '--workspace', self.ws, cwd=self.tmp)   # RJ-07: the old proposals file, read with the workspace
        self.assertNotIn(pid + ' ', out.split('not listed')[-1] if 'not listed' in out else out)
        hb = json.loads(sdem('handback', '--workspace', self.ws, '--json', cwd=self.tmp)[1])
        self.assertEqual([(x['link'], x['by']) for x in hb['links_rejected']], [(' '.join(self.key), 'jane.architect')]); self.assertEqual(hb['summary']['links_rejected'], 1)
        from sdem.graph import FederatedGraph
        fg = FederatedGraph.load(sorted(self.ws.glob('a*.json')) + [self.ws / 'mappings.json'])
        self.assertNotIn(self.key, {(e['source']['id'], e['relationship'], e['target']['id']) for e in fg.edges()})   # RJ-06

    def test_a_link_to_a_bian_record_is_rejected_without_naming_a_bian_release(self):   # RJ-02 — found when sdem intake declined a proposal to a service domain
        m = json.loads((self.ws / 'mappings.json').read_text(encoding='utf-8'))
        bian = next(x for x in m['mappings'] if x['relationship'] in ('USES_DOMAIN', 'SUPPORTED_BY', 'REALIZED_BY') and (x['source']['type'].startswith('A2.') or x['target']['type'].startswith('A2.')))
        prop = {**{k: v for k, v in bian.items() if k not in ('bian_release', 'reviewer_id', 'approved_at')}, 'mapping_id': 'P-BIAN', 'status': 'proposed'}
        m['mappings'] = [x for x in m['mappings'] if x is not bian]; (self.ws / 'mappings.json').write_text(json.dumps(m, indent=2), encoding='utf-8')
        pf = self.tmp / 'p.json'; pf.write_text(json.dumps({'mappings': [prop]}), encoding='utf-8')
        code, out, err = sdem('reject', 'P-BIAN', '--proposals', pf, '--workspace', self.ws, '--reviewer', 'jane.architect', '--reason', 'not this domain', cwd=self.tmp)
        self.assertEqual(code, 0, out + err)   # a rejection relies on no BIAN release: it says the link is not there

    def test_approving_it_later_overrides_the_rejection(self):   # RJ-05
        pid = self.pid(); self.reject(pid, '--reason', 'not yet')
        props = {'mappings': [self.gone | {'mapping_id': 'P-RUN-900', 'status': 'proposed'}]}
        p = self.tmp / 'again.json'; p.write_text(json.dumps(props), encoding='utf-8')
        ev = next(e for e in self.gone['evidence'] if not e.startswith('engine_rationale'))
        code, out, err = sdem('approve', 'P-RUN-900', '--proposals', p, '--workspace', self.ws, '--reviewer', 'jane.architect', '--evidence', ev, cwd=self.tmp)
        self.assertEqual(code, 0, err)
        ms = [m for m in json.loads((self.ws / 'mappings.json').read_text(encoding='utf-8'))['mappings'] if (m['source']['id'], m['relationship'], m['target']['id']) == self.key]
        self.assertEqual(sorted(m['status'] for m in ms), ['approved', 'rejected'])   # the rejection stays as it was, named by the approval that overrides it
        self.assertEqual(next(m for m in ms if m['status'] == 'approved')['previous_mapping_id'], next(m for m in ms if m['status'] == 'rejected')['mapping_id'])
        self.assertEqual(sdem('validate', '--workspace', self.ws, cwd=self.tmp)[0], 0)

    def test_aid_puts_nothing_in_the_place_of_a_rejected_mapping(self):   # RJ-04
        try: from sdem_bian.aid_bian import propose_information
        except ImportError: self.skipTest('needs sdem-bian installed: AID-I01…I07 are BIAN\'s (BX-15)')
        R = lambda i, t, **a: {'id': i, 'type': t, 'version': '1', 'name': i, 'attributes': a}
        a2 = {'instances': [R('BO-1', 'A2.BusinessObject'), R('BOA-1', 'A2.BusinessObjectAttribute', data_type='identifier', identifier=True)],
              'relationships': [{'source': 'BO-1', 'kind': 'composition', 'target': 'BOA-1'}]}
        a3 = {'instances': [R('ENT-1', 'A3.DataEntity', attributes=['x'])], 'relationships': []}
        M = lambda status: [{'source': {'id': 'BO-1'}, 'relationship': 'MAPPED_TO', 'target': {'id': 'ENT-1'}, 'status': status}]
        mark = lambda rule, why, frm: {'rule': rule}
        inst, _, _, skipped = propose_information(a2, a3, M('rejected'), mark)
        self.assertEqual(inst, []); self.assertEqual([(s['id'], s['why']) for s in skipped], [('BO-1', 'a person rejected its mapping to ENT-1 (RJ-04)')])
        self.assertEqual(propose_information(a2, a3, M('proposed'), mark)[0], [])    # still to decide: nothing inferred beside it
        self.assertEqual([i['id'] for i in propose_information(a2, a3, [], mark)[0]][0], 'AID-ENT-BO-1')   # never proposed: AID-I01 as before


if __name__ == '__main__':
    unittest.main()
