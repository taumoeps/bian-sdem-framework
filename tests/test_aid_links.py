"""AID proposes the direct A1→A3 links and field matches; BIAN families; onboarding of the new kinds (the owner's approvals 2, 2b, 3, 4,
2026-11-16; docs/design/aid-spec.md AID-L01…L06, AID-I05, AID-I06, AID-K01, AID-K02). Made-up data: examples/payment-initiation-v2."""
import json, shutil, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / 'examples/payment-initiation-v2'
STATED = {'SERVED_BY', 'AUTOMATED_BY', 'REALIZED_BY', 'ALIGNED_TO', 'STORED_IN'}


class AidLinksTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from sdem.aid_fill import fill
        cls.ws = Path(tempfile.mkdtemp()) / 'ws'; shutil.copytree(V2, cls.ws, ignore=shutil.ignore_patterns('graph'))
        m = json.loads((cls.ws / 'mappings.json').read_text(encoding='utf-8'))
        key = lambda x: (x['source']['id'], x['relationship'], x['target']['id'])
        cls.owner = {key(x) for x in m['mappings'] if x['mapping_id'] >= 'PAY-140'}   # what the owner stated by hand in v2
        m['mappings'] = [x for x in m['mappings'] if x['mapping_id'] < 'PAY-140' and not (x['relationship'] in STATED and x['mapping_id'] >= 'PAY-100')]
        (cls.ws / 'mappings.json').write_text(json.dumps(m), encoding='utf-8')
        run = fill(cls.ws, 'a tester', now='2026-11-16T00:00:00+00:00')
        cls.props = json.loads((cls.ws / run['proposals']).read_text(encoding='utf-8'))['mappings']
        cls.got = {key(x): x for x in cls.props}

    def rule(self, k): return self.got[k]['evidence'][0].split()[-1]

    def test_the_direct_links_the_owner_stated_are_proposed(self):   # AID-L01…L05
        for k, rule in [(('PRC-PAY-01', 'SERVED_BY', 'SVC-PAY-INIT'), 'AID-L01'), (('ACTOR-CUSTOMER', 'SERVED_BY', 'SVC-PAY-INIT'), 'AID-L01'),
                        (('PRC-PAY-01', 'AUTOMATED_BY', 'AFN-PAY-VALIDATE'), 'AID-L02'), (('BSV-MAKE-PAYMENT', 'REALIZED_BY', 'SVC-PAY-INIT'), 'AID-L03'),
                        (('BEV-PAY-EXECUTED', 'REALIZED_BY', 'EVT-PAY-STATUS'), 'AID-L04'), (('CHN-OBAPI', 'REALIZED_BY', 'IFC-PAY-API'), 'AID-L05'),
                        (('APP-PAY-HUB', 'SERVED_BY', 'TS-MQ'), 'AID-L06'), (('BO-ACCOUNT', 'ALIGNED_TO', 'BBO-ACCOUNT'), 'AID-I05')]:
            self.assertIn(k, self.got, k); self.assertEqual(self.rule(k), rule)
            self.assertTrue(all(isinstance(self.got[k]['confidence'], float) for _ in [0]))

    def test_no_guess_where_the_path_does_not_hold(self):
        self.assertNotIn(('PRC-PAY-02', 'AUTOMATED_BY', 'AFN-PAY-VALIDATE'), self.got)        # the function does not do what the process says
        self.assertNotIn(('BEV-PAY-RECEIVED', 'REALIZED_BY', 'EVT-PAY-STATUS'), self.got)    # an event that starts a process is not what its software raises
        self.assertNotIn(('BEV-PAY-CUTOFF', 'REALIZED_BY', 'EVT-PAY-STATUS'), self.got)

    def test_an_existing_table_is_matched_before_a_new_one_is_inferred(self):   # AID-K02
        self.assertEqual(self.rule(('BBO-PAYMENT-TRANSACTION', 'MAPPED_TO', 'ENT-PAY-INSTR')), 'AID-K02')
        self.assertEqual(self.rule(('BBO-ACCOUNT', 'MAPPED_TO', 'ENT-ACCOUNT-CACHE')), 'AID-K02')
        a3 = json.loads((self.ws / 'a3-application.json').read_text(encoding='utf-8'))
        self.assertNotIn('AID-ENT-PAYMENT-TRANSACTION-NEW', {i['id'] for i in a3['instances']})

    def test_fields_are_matched_once_and_the_ambiguous_ones_left_to_a_person(self):   # AID-K01
        k = [x for x in self.props if 'AID-K01' in x['evidence'][0]]
        self.assertIn(('BBOA-PAYMENT-TRANSACTION-PAYMENT-TRANSACTION-STATUS', 'FIELD_MAPPED_TO', 'F-PAY-INSTR-PAYMENT-STATUS'), self.got)
        self.assertIn(('BBOA-ACCOUNT-ACCOUNT-CURRENCY', 'FIELD_MAPPED_TO', 'F-ACCOUNT-CACHE-CURRENCY'), self.got)
        targets = [x['target']['id'] for x in k]; sources = [x['source']['id'] for x in k]
        self.assertEqual(len(targets), len(set(targets))); self.assertEqual(len(sources), len(set(sources)))   # one field, one column
        self.assertFalse(any(x['target']['id'] == 'F-PAY-INSTR-DEBTOR-ACCOUNT-REFERENCE' for x in k))     # two BIAN fields fit equally: never a guess
        self.assertFalse(any(x['target']['id'] == 'F-PAY-INSTR-AUTHORISATION-STATUS' for x in k))         # one word of two is not enough


class FamilyAndOnboardingTests(unittest.TestCase):
    def test_a_bian_field_is_its_objects_own_or_from_a_parent(self):   # fix 3
        from sdem.aid_links import family
        self.assertEqual(family('PaymentTransactionAmount', 'Payment Transaction'), 'own')
        self.assertEqual(family('FinancialTransactionAmount', 'Payment Transaction'), 'inherited')
        from sdem.document import document, markdown
        md = markdown(document(V2, 'A2'))
        self.assertIn('BIAN family', md); self.assertIn('from a parent object', md)

    def test_onboarding_knows_the_new_kinds(self):   # fix 4
        r = json.loads((ROOT / 'metamodel/transform-rules.json').read_text(encoding='utf-8'))
        types = {t['type'] for t in r['tables']} | {s['type'] for s in r['diagram_shapes']}
        for t in ('A1.BusinessEvent', 'A1.Product', 'A1.BusinessInterface', 'A4.Location', 'A3.DataEntity'): self.assertIn(t, types)


class TraceDisplayTests(unittest.TestCase):   # the two display issues the v2 report noted
    def test_trace_lists_real_links_and_names_each_zone_once(self):
        import io, contextlib, subprocess, sys, os
        g = Path(tempfile.mkdtemp()) / 'graph'
        subprocess.run([sys.executable, '-m', 'sdem.graph', 'build', *sorted(str(p) for p in V2.glob('a*.json')), str(V2 / 'mappings.json'), '--out', str(g)],
                       check=True, capture_output=True, cwd=ROOT, env={**os.environ, 'PYTHONPATH': str(ROOT)})
        out = subprocess.run([sys.executable, '-m', 'sdem', 'trace', 'BBOA-PAYMENT-TRANSACTION-PAYMENT-TRANSACTION-AMOUNT', '--graph', str(g), '--follow-composition'],
                             capture_output=True, text=True, cwd=ROOT, env={**os.environ, 'PYTHONPATH': str(ROOT)}).stdout
        self.assertNotIn('? -?-> ?', out)
        self.assertIn('ALSO FOLLOWED, inside A4', out); self.assertIn('RA4-38 a shape in its network zone', out)
        branch = out.split('UPSTREAM')[0].split('└─ -PART_OF-> BBO-PAYMENT-TRANSACTION')[0]
        self.assertEqual(branch.count("ZONE-PAY-INTERNAL 'Internal network"), 1)   # once — not also as PART_OF


if __name__ == '__main__':
    unittest.main()
