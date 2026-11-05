"""AID-M03 and AID-W09 (owner's decisions 2026-11-06, from the core-agent validation): when the business layer names its BIAN
domains, a domain only an application's name points to is a note, not a record; and `sdem link` is the one list to approve from,
saying how many of AID's proposals it reproduces."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
W = 'workspaces/ledger'


def sdem(*args, cwd):
    env = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], cwd=cwd, capture_output=True, text=True, env=env)
    return r.returncode, r.stdout + r.stderr


def rec(i, t, n, **a): return {'id': i, 'type': t, 'version': '1', 'name': n, 'lifecycle_status': 'planned', 'attributes': a}


class AidOneListTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = Path(tempfile.mkdtemp())
        assert sdem('new', '--workspace', W, '--person', 'jane.architect', cwd=cls.d)[0] == 0
        ws = cls.d / W
        a1 = json.loads((ws / 'a1-business.json').read_text(encoding='utf-8'))
        a1['instances'] = [rec('PRC-POST', 'A1.BusinessProcess', 'Post journal entries', invokes=['SO-FINANCIAL-ACCOUNTING-CAPTURE-LEDGER-POSTING'])]
        (ws / 'a1-business.json').write_text(json.dumps(a1))
        a3 = json.loads((ws / 'a3-application.json').read_text(encoding='utf-8'))   # an application whose data names share one word with an unrelated domain
        a3['instances'] = [rec('APP-GL', 'A3.ApplicationComponent', 'General Ledger'), rec('DE-ACC', 'A3.DataEntity', 'account_cache')]
        a3['relationships'] = [{'source': 'APP-GL', 'kind': 'access', 'target': 'DE-ACC'}]
        (ws / 'a3-application.json').write_text(json.dumps(a3))
        cls.aid = sdem('aid', '--workspace', W, '--person', 'jane.architect', cwd=cls.d)

    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.d, ignore_errors=True)

    def domains(self):
        return {i['id'] for i in json.loads((self.d / W / 'a2-service-domain.json').read_text(encoding='utf-8'))['instances'] if i['type'] == 'A2.ServiceDomain'}

    def test_the_domain_the_business_layer_names_is_added(self):
        self.assertEqual(self.aid[0], 0, self.aid[1])
        self.assertIn('SD-FINANCIAL-ACCOUNTING', self.domains())

    def test_a_domain_only_a_name_points_to_is_a_note(self):                            # AID-M03
        notes = [l for l in self.aid[1].splitlines() if l.startswith('NOTE: not added')]
        self.assertIn('SD-ACCOUNT-RECONCILIATION', ' '.join(notes))                       # matched on 'account' only
        for l in notes:                                                                  # each one named, and not added
            dom = l.split('not added — ', 1)[1].split(' ', 1)[0]
            self.assertNotIn(dom, self.domains(), l)
            self.assertIn('sdem bian custom', l)
        self.assertFalse({d for d in self.domains() if d != 'SD-FINANCIAL-ACCOUNTING'} - {d for d in self.domains() if 'ACCOUNTING' in d}, self.domains())

    def test_link_is_the_one_list_and_says_what_it_covers(self):                        # AID-W09
        self.assertIn('sdem link --workspace', self.aid[1])
        code, out = sdem('link', '--workspace', W, '--out', f'{W}/links', '--json', cwd=self.d)
        self.assertEqual(code, 0, out)
        cover = json.loads(out).get('aid_proposals')
        self.assertTrue(cover and cover['total'] >= 1, out[:400])
        self.assertEqual(cover['included'] + len(cover['not_included']), cover['total'])


if __name__ == '__main__':
    unittest.main()
