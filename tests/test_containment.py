"""The containment layout (sdem/containment.py; docs/design/sdem-layer-containment-design.md, the owner's decisions C1–C6): A2 drawn as
BIAN's service landscape. Synthetic examples only."""
import copy, json, os, subprocess, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
EX = ROOT / 'examples'
from sdem.containment import layout, load, ContainmentError


def a2(name='payment-initiation'):
    return json.loads((EX / name / 'a2-service-domain.json').read_text(encoding='utf-8'))


class A2LandscapeTests(unittest.TestCase):
    def test_payment_is_drawn_as_bians_landscape(self):
        lay = load(EX / 'payment-initiation', 'A2')
        z = {x['id']: x for x in lay['zones']}
        self.assertEqual(z['R:SD-PI']['part_of'], 'R:BD-PAYMENTS')                      # business domain → service domain (RA2-02)
        self.assertEqual({k for k, v in z.items() if v['part_of'] == 'R:SD-PI'}, {'R:SG-PI-1', 'R:SG-PI-2', 'R:CR-PI'})   # its groups and control record
        at = {s['id']: s['zone'] for s in lay['shapes']}
        self.assertEqual(at['SO-PI-01'], 'R:SG-PI-1'); self.assertEqual(at['SO-PI-02'], 'R:SG-PI-2')   # each operation in its service group (RA2-04)
        self.assertEqual(at['BQ-VALIDATION'], 'R:CR-PI')                                 # a qualifier in its control record (RA2-11)
        self.assertEqual(at['BS-CREDIT-TRANSFER'], 'G:Business scenarios')              # a scenario cuts across: its own group (C4)
        self.assertEqual(z['R:SD-PI']['label'], 'Service domain · Payment Initiation (synthetic selection)')   # BIAN's names, no level numbers (C3)
        self.assertIsNone(lay['strip'])

    def test_every_record_sits_inside_its_region(self):
        for name in ('payment-initiation', 'fx-dealing', 'card-fraud-alerts', 'trade-finance', 'digital-lending'):
            p = EX / name / 'a2-service-domain.json'
            if not p.exists(): continue
            with self.subTest(name):
                lay = load(EX / name, 'A2'); z = {x['id']: x['rect'] for x in lay['zones']}
                for s in lay['shapes']:
                    if s['zone']:
                        r = z[s['zone']]; self.assertTrue(r[0] <= s['at'][0] <= r[2] and r[1] <= s['at'][1] <= r[3], s['id'])
                for x in lay['zones']:
                    if x['part_of']:
                        o, i = z[x['part_of']], x['rect']; self.assertTrue(o[0] <= i[0] and o[1] <= i[1] and i[2] <= o[2] and i[3] <= o[3], x['id'])

    def test_only_structural_links_nest_and_each_record_once(self):   # C2, C3
        lay = load(EX / 'payment-initiation', 'A2')
        kinds = {l['kind'] for l in lay['links'] if l['shown_by'] == 'position'}
        self.assertTrue(kinds <= {'composition', 'aggregation', 'assignment', 'realization'}, kinds)
        held = [s['id'] for s in lay['shapes']]; self.assertEqual(len(held), len(set(held)))
        scen = [l for l in lay['links'] if l['source'] == 'BS-CREDIT-TRANSFER']
        self.assertTrue(scen and all(l['shown_by'] == 'line' for l in scen))            # the scenario's aggregation: a line, not nesting

    def test_service_domains_a_scenario_spans_are_linked_derived(self):   # C5
        d = a2(); d['relationships'].append({'source': 'BS-CREDIT-TRANSFER', 'kind': 'aggregation', 'target': 'SO-PE-X'})
        d['instances'].append({'id': 'SG-PE-1', 'type': 'A2.ServiceGroup', 'version': '1', 'name': 'Execution', 'lifecycle_status': 'active'})
        d['instances'].append({'id': 'SO-PE-X', 'type': 'A2.ServiceOperation', 'version': '1', 'name': 'Execute', 'lifecycle_status': 'active'})
        d['relationships'] += [{'source': 'SD-PE', 'kind': 'composition', 'target': 'SG-PE-1'}, {'source': 'SG-PE-1', 'kind': 'composition', 'target': 'SO-PE-X'}]
        conns = layout(d, 'A2')['connections']
        self.assertEqual([(c['from'], c['to'], c['rule'], c['via']) for c in conns], [('R:SD-PE', 'R:SD-PI', 'derived (potential)', 'BS-CREDIT-TRANSFER')])

    def test_a_record_with_no_owner_is_said(self):
        d = a2(); d['instances'].append({'id': 'SO-LOOSE', 'type': 'A2.ServiceOperation', 'version': '1', 'name': 'Loose operation', 'lifecycle_status': 'active'})
        strip = layout(d, 'A2')['strip']
        self.assertEqual((strip['label'], strip['not_in_a_zone']), ('Not in the service landscape', ['SO-LOOSE']))

    def test_a_layer_not_built_yet_says_so(self):
        with self.assertRaises(ContainmentError): layout({'instances': [], 'relationships': []}, 'A1')

    def test_cli_and_view(self):
        env = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}
        r = subprocess.run([sys.executable, '-m', 'sdem', 'layout', '--layer', 'A2', '--workspace', str(EX / 'payment-initiation'), '--json'], capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr); self.assertEqual(json.loads(r.stdout)['viewpoint'], 'containment')
        r = subprocess.run([sys.executable, '-m', 'sdem', 'layout', '--layer', 'A4', '--workspace', str(EX / 'payment-initiation'), '--json'], capture_output=True, text=True, env=env)
        self.assertEqual(json.loads(r.stdout)['viewpoint'], 'deployment-zones')       # A4: by its network zones
        from sdem.view import render
        page = render(EX / 'payment-initiation' / 'graph', now='2026-11-15 00:00:00')
        self.assertIn('A2 Service Domain (BIAN) — by what owns what', page); self.assertIn('Service group · Instruction', page)


if __name__ == '__main__':
    unittest.main()
