"""The containment layout (sdem/containment.py; docs/design/sdem-layer-containment-design.md, the owner's decisions C1–C6): A1, A2 and A3 drawn by what owns what (A2 as
BIAN's service landscape). Synthetic examples only."""
import copy, json, os, subprocess, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
EX = ROOT / 'examples'
from sdem.containment import layout, load, ContainmentError


def a2(name='payment-initiation'):
    return json.loads((EX / name / 'a2-service-domain.json').read_text(encoding='utf-8'))


import sys as _s, pathlib as _pl; _s.path.insert(0, str(_pl.Path(__file__).resolve().parent)); from needs import bian as _needs_bian  # noqa: E402 — BX-15: tests that need sdem-bian

@_needs_bian
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
        with self.assertRaises(ContainmentError): layout({'instances': [], 'relationships': []}, 'A0')   # a layer with no hierarchy (a profile's own) says so

    def test_cli_and_view(self):
        env = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}
        r = subprocess.run([sys.executable, '-m', 'sdem', 'layout', '--layer', 'A2', '--workspace', str(EX / 'payment-initiation'), '--json'], capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr); self.assertEqual(json.loads(r.stdout)['viewpoint'], 'containment')
        r = subprocess.run([sys.executable, '-m', 'sdem', 'layout', '--layer', 'A4', '--workspace', str(EX / 'payment-initiation'), '--json'], capture_output=True, text=True, env=env)
        self.assertEqual(json.loads(r.stdout)['viewpoint'], 'deployment-zones')       # A4: by its network zones
        from sdem.view import render
        page = render(EX / 'payment-initiation' / 'graph', now='2026-11-15 00:00:00')
        self.assertIn('A2 Service Domain (BIAN) — by what owns what', page); self.assertIn('Service group · Instruction', page)



class A1CapabilityMapTests(unittest.TestCase):   # C3, C4: capability → sub-capability → realising process → activity
    def test_payment_is_drawn_as_a_capability_map(self):
        lay = load(EX / 'payment-initiation', 'A1')
        z = {x['id']: x for x in lay['zones']}
        self.assertEqual(z['R:CAP-PAY-010']['part_of'], 'R:CAP-PAY-000')                 # sub-capability (RA1-01)
        self.assertEqual(z['R:PRC-PAY-01']['part_of'], 'R:CAP-PAY-010')                  # the process sits in the capability it realises (RA1-08)
        at = {s['id']: s['zone'] for s in lay['shapes']}
        self.assertEqual(at['ACT-PAY-01a'], 'R:PRC-PAY-01')                              # an activity in its process (RA1-24)
        self.assertNotIn('R:ACT-PAY-01a', z)                                              # an activity is a region only if it has parts
        self.assertEqual(at['VSS-P1'], 'R:VS-MAKE-PAYMENT'); self.assertEqual(z['R:VS-MAKE-PAYMENT']['part_of'], 'G:Value streams')   # C4: beside the map
        self.assertEqual(at['ROLE-PAY-OFFICER'], 'G:Actors and roles')
        realise = [l for l in lay['links'] if l['source'] == 'PRC-PAY-01' and l['target'] == 'CAP-PAY-010']
        self.assertEqual([l['shown_by'] for l in realise], ['position'])                  # nesting stands for the realisation
        self.assertIsNone(lay['strip'])

    def test_a_process_realising_two_capabilities_sits_in_the_most_specific(self):   # C3
        d = json.loads((EX / 'payment-initiation' / 'a1-business.json').read_text(encoding='utf-8'))
        d['relationships'].append({'source': 'PRC-PAY-01', 'kind': 'realization', 'target': 'CAP-PAY-000'})
        lay = layout(d, 'A1'); z = {x['id']: x for x in lay['zones']}
        self.assertEqual(z['R:PRC-PAY-01']['part_of'], 'R:CAP-PAY-010')
        other = [l for l in lay['links'] if l['source'] == 'PRC-PAY-01' and l['target'] == 'CAP-PAY-000']
        self.assertEqual([l['shown_by'] for l in other], ['line'])                        # its other capability: a line


@_needs_bian
class A3ApplicationStructureTests(unittest.TestCase):   # application → components, services, functions, interfaces → API operations
    def test_payment_is_drawn_as_its_application_structure(self):
        lay = load(EX / 'payment-initiation', 'A3')
        z = {x['id']: x for x in lay['zones']}
        at = {s['id']: s['zone'] for s in lay['shapes']}
        self.assertEqual(z['R:IFC-PAY-API']['part_of'], 'R:APP-PAY-HUB')                # the interface in its application (RA3-03)
        self.assertEqual(at['API-PI-01'], 'R:IFC-PAY-API')                               # an API operation in its interface (RA3-27)
        self.assertEqual(at['CMP-PAY-CAPTURE'], 'R:APP-PAY-HUB'); self.assertNotIn('R:CMP-PAY-CAPTURE', z)   # a component with no parts: a block, not an empty region
        self.assertEqual(at['SVC-PAY-INIT'], 'R:APP-PAY-HUB')                            # the service it realises (RA3-06)
        self.assertEqual(at['ENT-PAY-INSTR'], 'G:Data entities'); self.assertEqual(at['EVT-PAY-STATUS'], 'G:Events')   # accessed or triggered, not owned (C4)
        assign = [l for l in lay['links'] if l['source'] == 'IFC-PAY-API' and l['target'] == 'SVC-PAY-INIT']
        self.assertEqual([l['shown_by'] for l in assign], ['line'])                      # the service's second owner: a line

    def test_a_solution_building_block_holds_its_applications(self):
        z = {x['id']: x for x in load(EX / 'trade-finance', 'A3')['zones']}
        self.assertEqual(z['R:APP-LC']['part_of'], z['R:APP-DOC']['part_of'])
        self.assertTrue(z['R:APP-LC']['part_of'].startswith('R:SBB'))


@_needs_bian
class SpacingTests(unittest.TestCase):   # C8 — the owner's screenshots of v2 (2026-11-16): shapes on top of each other, records over headings
    SITE_W, SITE_H = 0.9 / 5.6 * 0.5, 0.5 / 5.4 * 0.5   # DESNRE's shape (0.9 x 0.5) on its plate (5.6 x 5.4) at shape size 0.5, as fractions of the plate

    def test_no_two_shapes_overlap_and_each_sits_in_its_region(self):
        for ex in sorted(p.name for p in EX.iterdir() if (p / 'a2-service-domain.json').exists()):
            for layer in ('A1', 'A2', 'A3'):
                try: lay = load(EX / ex, layer)
                except (FileNotFoundError, ContainmentError): continue
                f = lay['fit']; self.assertTrue(0 < f <= 1)
                pts = [(s['id'], s['at']) for s in lay['shapes']]
                for i, (a, pa) in enumerate(pts):
                    for b, pb in pts[i + 1:]:
                        self.assertFalse(abs(pa[0] - pb[0]) < self.SITE_W * f and abs(pa[1] - pb[1]) < self.SITE_H * f, f'{ex} {layer}: {a} on {b}')
                z = {x['id']: x['rect'] for x in lay['zones']}
                for s in lay['shapes']:
                    if s['zone']:
                        r = z[s['zone']]; self.assertTrue(r[0] <= s['at'][0] <= r[2] and r[1] <= s['at'][1] <= r[3], f'{ex} {layer}: {s["id"]}')

    def test_v2_bian_layer_is_drawn_at_most_a_fifth_smaller(self):
        self.assertGreaterEqual(load(EX / 'payment-initiation-v2', 'A2')['fit'], 0.8)


if __name__ == '__main__':
    unittest.main()
