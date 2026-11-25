"""AID proposes the direct A1→A3 links and field matches; BIAN families; onboarding of the new kinds (the owner's approvals 2, 2b, 3, 4,
2026-11-16; docs/design/aid-spec.md AID-L01…L06, AID-I05, AID-I06, AID-K01, AID-K02). Made-up data: examples/payment-initiation-v2."""
import json, shutil, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / 'examples/payment-initiation-v2'
STATED = {'SERVED_BY', 'AUTOMATED_BY', 'REALIZED_BY', 'ALIGNED_TO', 'STORED_IN'}


import sys as _s, pathlib as _pl; _s.path.insert(0, str(_pl.Path(__file__).resolve().parent)); from needs import bian as _needs_bian  # noqa: E402 — BX-15: tests that need sdem-bian

@_needs_bian
class AidLinksTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from sdem import profile as _p0; _p0.deactivate()   # 0.22 (BX-15): as a command run alone — no workspace left open by a test before
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


@_needs_bian
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


@_needs_bian
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


@_needs_bian
class ConnectedAndPlacedTests(unittest.TestCase):   # the owner's screenshots of v2 (2026-11-16): unconnected shapes, A4 shapes stacked
    def test_every_shape_of_v2_is_connected_inside_its_layer(self):
        from sdem.containment import layout
        from sdem.metamodel import Metamodel
        mm = Metamodel.load()
        for L, f in (('A1', 'a1-business.json'), ('A2', 'a2-service-domain.json'), ('A3', 'a3-application.json'), ('A4', 'a4-technology.json')):
            d = json.loads((V2 / f).read_text(encoding='utf-8')); shapes = {s['id'] for s in layout(d, L, mm)['shapes']}
            linked = {x for r in d['relationships'] if r['source'] in shapes and r['target'] in shapes for x in (r['source'], r['target'])}
            self.assertEqual(shapes - linked, set(), L)

    def test_a_narrow_zone_wraps_its_shapes_instead_of_stacking_them(self):
        from sdem.containment import layout
        from sdem.metamodel import Metamodel
        for ex in ('payment-initiation-v2', 'payment-initiation', 'customer-onboarding'):
            pts = [s['at'] for s in layout(json.loads((ROOT / 'examples' / ex / 'a4-technology.json').read_text(encoding='utf-8')), 'A4', Metamodel.load())['shapes']]
            close = [(a, b) for i, a in enumerate(pts) for b in pts[i + 1:] if abs(a[0] - b[0]) < 0.07 and abs(a[1] - b[1]) < 0.05]
            self.assertEqual(close, [], ex)

    def test_the_import_links_a_control_record_to_the_objects_it_refers_to(self):
        try: from sdem_bian.bian import read_domain, build
        except ImportError: self.skipTest('needs sdem-bian installed (BX-15)')
        from sdem.metamodel import Metamodel
        d, _ = build([read_domain(ROOT / 'tests/fixtures/bian-release-typed/SamplePaymentOrder.yaml')], Metamodel.load().version, objects=True)
        self.assertIn(('CR-SAMPLE-PAYMENT-ORDER', 'association', 'BBO-PAYMENT-TRANSACTION'), {(r['source'], r['kind'], r['target']) for r in d['relationships']})

    def test_aid_has_a_table_nobody_uses_accessed_by_its_domains_component(self):   # AID-I07
        try: from sdem_bian.aid_bian import propose_access
        except ImportError: self.skipTest('needs sdem-bian installed: AID-I01…I07 are BIAN\'s (BX-15)')
        from sdem.metamodel import Metamodel
        a2 = {'instances': [], 'relationships': [{'source': 'SD-1', 'kind': 'aggregation', 'target': 'CR-1'}, {'source': 'CR-1', 'kind': 'association', 'target': 'BO-1'}]}
        a3 = {'instances': [{'id': 'ENT-1', 'type': 'A3.DataEntity', 'version': '1', 'name': 't'}], 'relationships': []}
        maps = [{'source': {'id': 'BO-1', 'type': 'A2.BusinessObject'}, 'relationship': 'MAPPED_TO', 'target': {'id': 'ENT-1', 'type': 'A3.DataEntity'}, 'status': 'approved'},
                {'source': {'id': 'SD-1', 'type': 'A2.ServiceDomain'}, 'relationship': 'REALIZED_BY', 'target': {'id': 'APP-1', 'type': 'A3.ApplicationComponent'}, 'status': 'approved'}]
        got = propose_access({'A2': a2, 'A3': a3}, maps, Metamodel.load(), lambda r, w, f: {'rule': r})
        self.assertEqual([(x['source'], x['kind'], x['target'], x['inferred']['rule']) for x in got], [('APP-1', 'access', 'ENT-1', 'AID-I07')])


@_needs_bian
class PathAsLineTests(unittest.TestCase):   # PL-01 — the owner (2026-11-16): a path read as a network
    def test_a_path_between_two_drawn_nodes_is_a_line_not_a_shape(self):
        from sdem.zone_layout import layout
        from sdem.metamodel import Metamodel
        L = layout(json.loads((V2 / 'a4-technology.json').read_text(encoding='utf-8')), Metamodel.load())
        self.assertNotIn('PATH-PAY-CORE-HSM', {s['id'] for s in L['shapes']})
        self.assertEqual([(p['id'], p['from'], p['to'], p.get('protocol')) for p in L['paths']], [('PATH-PAY-CORE-HSM', 'INF-CORE-LEDGER-HOST', 'DEV-PAY-HSM', 'tls')])
        self.assertFalse(any('PATH-PAY-CORE-HSM' in (l['source'], l['target']) for l in L['links']))


@_needs_bian
class A4ReviewTests(unittest.TestCase):   # ZL-01…ZL-04 — the owner's review of v2's A4 (2026-11-17)
    def setUp(self):
        from sdem import profile as _p0; _p0.deactivate()   # 0.22 (BX-15): as a command run alone — no workspace left open by a test before

    def lay(self, **kw):
        from sdem.zone_layout import layout
        from sdem.metamodel import Metamodel
        return layout(json.loads((V2 / 'a4-technology.json').read_text(encoding='utf-8')), Metamodel.load(), **kw)

    def test_the_zones_fill_the_plate_when_nothing_is_outside_them(self):   # ZL-01
        L = self.lay(headings=True)
        self.assertIsNone(L['strip']); self.assertEqual(max(z['rect'][3] for z in L['zones']), 1.0)

    def test_what_a_host_serves_but_is_not_drawn_under_it_gets_a_line(self):   # ZL-02
        x = [l for l in self.lay()['links'] if (l['source'], l['target']) == ('DEV-PAY-HSM', 'TS-HSM-SIGN')]
        self.assertEqual([l['shown_by'] for l in x], ['line'])

    def test_networks_and_the_one_environment_are_headings_not_shapes(self):   # ZL-03
        L = self.lay(headings=True); ids = {s['id'] for s in L['shapes']}
        self.assertFalse(ids & {'NET-PAY-PRIVATE', 'ENV-PAY-PROD'})
        self.assertIn('Level 2 · Payments private network zone · 10.20.0.0/16', [z['label'] for z in L['zones']])
        self.assertIn('NET-PAY-PRIVATE', {s['id'] for s in self.lay()['shapes']})   # sdem view keeps drawing it

    def test_a_top_zone_names_the_one_place_its_shapes_are_in(self):   # ZL-04
        labels = [z['label'] for z in self.lay()['zones'] if not z['part_of']]
        self.assertEqual(labels, ['Level 0 · Cloud — payments · Cloud region A', 'Level 0 · On premises — core banking · Data centre DC-1'])


if __name__ == '__main__':
    unittest.main()
