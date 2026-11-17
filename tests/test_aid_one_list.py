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
            self.assertIn('sdem bian add', l)
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


class SecondPassTests(unittest.TestCase):   # AID-M03 after approvals — the public twin's run 2, F15 (2026-11-17)
    def test_a_rejection_does_not_bring_in_the_next_best_name_match(self):
        import json, os, shutil, subprocess, sys, tempfile
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]; tmp = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, tmp, True); ws = tmp / 'ws'
        env = {**os.environ, 'PYTHONPATH': str(root) + os.pathsep + os.environ.get('PYTHONPATH', '')}
        def sdem(*a):
            r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, a)], cwd=tmp, capture_output=True, text=True, env=env)
            self.assertEqual(r.returncode, 0, r.stderr[-600:]); return r.stdout
        R = lambda i, t, n, **a: {'op': 'add', 'record': {'id': i, 'type': t, 'version': '1', 'name': n, 'lifecycle_status': 'planned', 'attributes': a}}
        cs = lambda layer, recs, rels=(): {'layer': layer, 'reason': 'test', 'changes': recs, 'relationships': {'add': [dict(zip(('source', 'kind', 'target'), r)) for r in rels]}}
        sdem('new', '--workspace', ws, '--person', 'jane.architect')
        (tmp / 'a1.json').write_text(json.dumps(cs('A1', [R('PROC-SUBMIT', 'A1.BusinessProcess', 'Receive the payment', invokes=['SO-PAYMENT-ORDER-INITIATION-INITIATE'])])))
        (tmp / 'a3.json').write_text(json.dumps(cs('A3', [R('APP-EDGE', 'A3.ApplicationComponent', 'API ingress'), R('IFC', 'A3.ApplicationInterface', 'Payment Initiation API'),
                                                          R('OP', 'A3.APIOperation', 'Create domestic payment', method='POST', path='/domestic-payments', payload_fields=['ConsentId', 'DomesticPaymentId', 'Status']),
                                                          R('OP2', 'A3.APIOperation', 'Read domestic payment', method='GET', path='/domestic-payments/{DomesticPaymentId}', payload_fields=['DomesticPaymentId', 'Status']),
                                                          R('DATA-PAYMENT', 'A3.DataEntity', 'PaymentLedger', attributes=['payment_id', 'payment_status'])],
                                               [('APP-EDGE', 'composition', 'IFC'), ('IFC', 'composition', 'OP'), ('IFC', 'composition', 'OP2'), ('OP', 'access', 'DATA-PAYMENT'), ('OP2', 'access', 'DATA-PAYMENT')])))
        sdem('change', 'propose', tmp / 'a1.json', '--workspace', ws, '--agent', 'sdem-a1-business', '--person', 'jane.architect')
        sdem('change', 'propose', tmp / 'a3.json', '--workspace', ws, '--agent', 'sdem-a3-application', '--person', 'jane.architect')
        sdem('bian', 'add', 'Payment Order Initiation', '--workspace', ws, '--person', 'jane.architect')
        named = lambda run: [i for i in run['added'].get('A2', []) if 'PARTY-AUTHENTICATION' not in i and 'FRAUD-EVALUATION' not in i and i != 'FP-ASSESS']   # not the domains the payment-initiation pattern names (AID-D05, CPL-16): those, and their functional pattern, rest on the pattern, not on a name
        self.assertEqual(named(json.loads(sdem('aid', '--workspace', ws, '--person', 'jane.architect', '--dry-run', '--json'))), [])
        sdem('link', '--workspace', ws, '--out', ws / 'links', '--no-review')
        pf = ws / 'links' / 'proposals.json'; props = json.loads(pf.read_text(encoding='utf-8'))['mappings']
        wrong = [p['mapping_id'] for p in props if p['relationship'] == 'REALIZED_BY' and p['target']['id'] == 'APP-EDGE']
        self.assertTrue(wrong, f"the test needs the ingress proposed as realising the domain — {[(p['source']['id'], p['relationship'], p['target']['id']) for p in props]}")
        for p in props:
            if p['relationship'] == 'USES_DOMAIN':
                sdem('approve', p['mapping_id'], '--proposals', pf, '--workspace', ws, '--reviewer', 'jane.architect', '--evidence', 'process_model:D#3', '--evidence', 'bian_alignment_guidance:D#4', '--bian-release', '14.0.0')
        sdem('reject', *wrong, '--proposals', pf, '--workspace', ws, '--reviewer', 'jane.architect', '--reason', 'the ingress only terminates the channel')
        second = json.loads(sdem('aid', '--workspace', ws, '--person', 'jane.architect', '--dry-run', '--json'))
        self.assertEqual(named(second), [])   # a rejection, with the business links approved, must not turn the next-best name match into a record
        self.assertTrue(any(e.startswith('not added') for e in second['projection_ends']), second['projection_ends'])
