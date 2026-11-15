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


class FoundBuildingV2Tests(unittest.TestCase):   # Payment Initiation v2 (2026-11-16)
    def test_aid_records_its_writes_as_change_sets(self):   # AID-W10, CTL-20
        import subprocess, sys
        from sdem.aid_fill import fill
        from sdem.agents import Estate
        ws = ws_copy()
        cs = {'layer': 'A1', 'reason': 'a test change', 'changes': [{'op': 'add', 'record': {'id': 'BEV-T', 'type': 'A1.BusinessEvent', 'version': '1.0', 'name': 'Test event', 'lifecycle_status': 'active'}}]}
        f = ws / 'cs.json'; f.write_text(json.dumps(cs))
        r = subprocess.run([sys.executable, '-m', 'sdem', 'change', 'propose', str(f), '--workspace', str(ws), '--agent', 'architect', '--person', 'a tester'],
                           capture_output=True, text=True, cwd=ROOT, env={**__import__('os').environ, 'PYTHONPATH': str(ROOT)})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        a2 = json.loads((ws / 'a2-service-domain.json').read_text(encoding='utf-8'))   # a typed business object with no data entity yet: AID infers one into A3
        a2['instances'].append({'id': 'BBO-T', 'type': 'A2.BusinessObject', 'version': '1.0', 'name': 'Test Thing', 'lifecycle_status': 'active', 'attributes': {'attributes': ['ThingId']}})
        a2['instances'].append({'id': 'BBOA-T-1', 'type': 'A2.BusinessObjectAttribute', 'version': '1.0', 'name': 'ThingId', 'lifecycle_status': 'active', 'attributes': {'data_type': 'identifier', 'identifier': True}})
        a2['relationships'].append({'source': 'BBO-T', 'kind': 'composition', 'target': 'BBOA-T-1'})
        (ws / 'a2-service-domain.json').write_text(json.dumps(a2))
        subprocess.run([sys.executable, '-m', 'sdem', 'change', 'adopt', '--workspace', str(ws), '--layer', 'A2', '--person', 'a tester', '--reason', 'test'],
                       capture_output=True, text=True, cwd=ROOT, env={**__import__('os').environ, 'PYTHONPATH': str(ROOT)})
        run = fill(ws, 'a tester', now='2026-11-16T00:00:00+00:00')
        self.assertIn('A3', run['added'])
        r = subprocess.run([sys.executable, '-m', 'sdem', 'check', '--workspace', str(ws)], capture_output=True, text=True, cwd=ROOT, env={**__import__('os').environ, 'PYTHONPATH': str(ROOT)})
        self.assertNotIn('CTL-20', r.stdout + r.stderr)

    def test_a_location_is_never_placed_in_a_zone(self):
        from sdem.conformance import zones_of
        mm = Metamodel.load()
        doc = {'level': 'A4', 'instances': [{'id': 'LOC-1', 'type': 'A4.Location'}, {'id': 'N-1', 'type': 'A4.Node'}, {'id': 'Z-1', 'type': 'A4.NetworkZone'}],
               'relationships': [{'source': 'LOC-1', 'kind': 'aggregation', 'target': 'N-1'}, {'source': 'Z-1', 'kind': 'aggregation', 'target': 'N-1'}]}
        shapes, _, _ = zones_of(doc, mm)
        self.assertNotIn('LOC-1', shapes); self.assertEqual(shapes['N-1'], ['Z-1'])


if __name__ == '__main__':
    unittest.main()
