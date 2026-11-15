"""Metamodel 0.16.0, slice 2 — links (docs/design/sdem-full-design-metamodel-design.md XL-01…XL-09, WL-04, AT-01; the owner's D9). Made-up data."""
import copy, json, shutil, tempfile, unittest
from pathlib import Path
from sdem.graph import FederatedGraph
from sdem.metamodel import Metamodel

ROOT = Path(__file__).resolve().parents[1]
ONB = ROOT / 'examples/customer-onboarding'


def ws_copy():
    ws = Path(tempfile.mkdtemp()) / 'ws'; shutil.copytree(ONB, ws, ignore=shutil.ignore_patterns('graph')); return ws


class SkipLevelTests(unittest.TestCase):   # D9
    def test_only_a_named_a1_to_a3_type_may_skip_a_layer(self):
        from sdem.validate import validate_registry
        reg = json.loads((ROOT / 'schema/relationship-types.json').read_text(encoding='utf-8'))
        self.assertEqual(validate_registry(reg, Metamodel.load()), [])
        skips = {(r['source_type'], r['relationship'], r['target_type']) for r in reg['relationships'] if r.get('skips_level')}
        self.assertEqual({(s[:2], t[:2]) for s, _, t in skips}, {('A1', 'A3')})
        self.assertIn(('A1.BusinessObject', 'MAPPED_TO', 'A3.DataEntity'), skips)
        bad = copy.deepcopy(reg)
        r = next(x for x in bad['relationships'] if x['relationship'] == 'AUTOMATED_BY'); r.pop('skips_level')
        self.assertTrue(any('A(n+1)' in i for i in validate_registry(bad, Metamodel.load())))
        r['skips_level'] = True; r['target_type'] = 'A4.Node'; r['mapping_type_id'] += '-X'
        self.assertTrue(any('only a link type marked skips_level, from A1 to A3' in i for i in validate_registry(bad, Metamodel.load())))

    def test_every_new_link_has_an_approved_example_and_checks_clean(self):
        fg = FederatedGraph.load(sorted(ONB.glob('a*.json')) + [ONB / 'mappings.json'])
        self.assertEqual({k: v for k, v in fg.check().items() if v}, {})
        rels = {m['relationship'] for m in json.loads((ONB / 'mappings.json').read_text(encoding='utf-8'))['mappings'] if m['status'] == 'approved'}
        self.assertTrue({'SERVED_BY', 'AUTOMATED_BY', 'STORED_IN', 'FIELD_MAPPED_TO'} <= rels)


class AttributesAsEvidenceTests(unittest.TestCase):   # AT-01: AID-A01…A03, LC-28
    def test_aid_proposes_what_attributes_say_and_links_a_path_to_its_ends(self):
        from sdem.aid_fill import fill
        ws = ws_copy()
        m = json.loads((ws / 'mappings.json').read_text(encoding='utf-8'))
        m['mappings'] = [x for x in m['mappings'] if x['relationship'] != 'STORED_IN']; (ws / 'mappings.json').write_text(json.dumps(m))
        a3 = json.loads((ws / 'a3-application.json').read_text(encoding='utf-8'))
        next(i for i in a3['instances'] if i['id'] == 'ENT-001').setdefault('attributes', {})['stored_in'] = ['INF-002']
        (ws / 'a3-application.json').write_text(json.dumps(a3))
        a4 = json.loads((ws / 'a4-technology.json').read_text(encoding='utf-8'))
        nodes = [i['id'] for i in a4['instances'] if i['type'] == 'A4.Node']
        a4['instances'].append({'id': 'PATH-001', 'type': 'A4.Path', 'version': '1.0', 'name': 'portal to database', 'lifecycle_status': 'active',
                                'attributes': {'from': nodes[0], 'to': nodes[1], 'protocol': 'tcp/5432', 'encrypted': True}})
        zone = 'ZONE-ONB-INTERNAL'
        a4['relationships'].append({'source': zone, 'kind': 'aggregation', 'target': 'PATH-001'})
        (ws / 'a4-technology.json').write_text(json.dumps(a4))
        run = fill(ws, 'a tester', now='2026-11-16T00:00:00+00:00')
        got = {(x['source']['id'], x['relationship'], x['target']['id']) for x in json.loads((ws / run['proposals']).read_text(encoding='utf-8'))['mappings']}
        self.assertIn(('ENT-001', 'STORED_IN', 'INF-002'), got)                       # AID-A01
        rels = json.loads((ws / 'a4-technology.json').read_text(encoding='utf-8'))['relationships']
        ends = {(r['source'], r['target']) for r in rels if r['kind'] == 'association' and r['source'] == 'PATH-001'}
        self.assertEqual(ends, {('PATH-001', nodes[0]), ('PATH-001', nodes[1])})       # AID-A03, marked inferred
        self.assertTrue(all(r.get('inferred', {}).get('rule') == 'AID-A03' for r in rels if r['source'] == 'PATH-001' and r['kind'] == 'association'))

    def test_an_attribute_that_disagrees_with_the_approved_link_is_reported(self):   # LC-28
        ws = ws_copy()
        a3 = json.loads((ws / 'a3-application.json').read_text(encoding='utf-8'))
        next(i for i in a3['instances'] if i['id'] == 'ENT-001').setdefault('attributes', {})['stored_in'] = ['INF-001']   # the approved STORED_IN says INF-002
        (ws / 'a3-application.json').write_text(json.dumps(a3))
        fg = FederatedGraph.load(sorted(ws.glob('a*.json')) + [ws / 'mappings.json']); fg.check()
        w = ' | '.join(x for v in fg.warnings.values() for x in v)
        self.assertIn('ENT-001: stored_in names INF-001 but its approved STORED_IN links are to INF-002', w)


if __name__ == '__main__':
    unittest.main()
