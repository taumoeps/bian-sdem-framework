"""The deployment-zones viewpoint (sdem/zone_layout.py; `sdem zones --layout`; `sdem view`) and the examples' physical completeness gate.
Synthetic examples only."""
import json, os, re, subprocess, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
EX = ROOT / 'examples'
from sdem.zone_layout import load, LayoutError


def inside(a, b, tol=1e-3):   # rect a within rect b
    return a[0] >= b[0] - tol and a[1] >= b[1] - tol and a[2] <= b[2] + tol and a[3] <= b[3] + tol


class LayoutTests(unittest.TestCase):
    def test_payment_production(self):
        lay = load(EX / 'payment-initiation')
        zones = {z['id']: z for z in lay['zones']}
        self.assertEqual(len(zones), 6)
        for z in zones.values():   # a zone fills inside the zone it is part of
            if z['part_of']: self.assertTrue(inside(z['rect'], zones[z['part_of']]['rect']), z['id'])
        for s in lay['shapes']:    # every shape sits inside its zone
            r = zones[s['zone']]['rect']; self.assertTrue(r[0] <= s['at'][0] <= r[2] and r[1] <= s['at'][1] <= r[3], s['id'])
        self.assertEqual({(c['from'], c['to'], c['rule']) for c in lay['connections']},
                         {('ZONE-PAY-CLOUD', 'ZONE-PAY-ONPREM', 'ZC-01'), ('ZONE-PAY-DMZ', 'ZONE-PAY-INTERNAL', 'ZC-02')})
        self.assertIn('ENV-PAY-UAT', lay['left_out']); self.assertNotIn('INF-K8S-PAY-UAT', {s['id'] for s in lay['shapes']})   # production only
        self.assertIsNone(lay['strip'])
        self.assertTrue(any(l['shown_by'] == 'line' and l['source'] == 'INF-APIGW-PAY' for l in lay['links']))

    def test_every_example_with_a4_lays_out_with_nothing_missing_a_zone(self):
        for ws in sorted(p.parent for p in EX.glob('*/a4-technology.json')):
            if ws.name == 'reference-structure': continue   # synthetic: one record per type, not a deployment
            with self.subTest(ws.name):
                lay = load(ws, 'all')
                self.assertEqual((lay['strip'] or {}).get('not_in_a_zone', []), [])
                for s in lay['shapes']: self.assertTrue(0 <= s['at'][0] <= 1 and 0 <= s['at'][1] <= 1, s['id'])

    def test_networks_sit_in_the_zone_holding_what_they_connect(self):
        at = {s['id']: s['zone'] for s in load(EX / 'fx-dealing', 'all')['shapes']}
        self.assertEqual(at['NET-COLO-LL'], 'ZONE-FX-COLO'); self.assertEqual(at['NET-MKT-PRIVATE'], 'ZONE-FX-ONPREM-INTERNAL')
        strip = load(EX / 'trade-finance', 'all')['strip']   # a network joining the cloud and a branch spans zones — not missing one
        self.assertEqual((strip['label'], strip['not_in_a_zone']), ('Across zones', []))

    def test_no_zones_is_said_plainly(self):
        doc = json.loads((EX / 'payment-initiation' / 'a4-technology.json').read_text(encoding='utf-8'))
        doc['instances'] = [i for i in doc['instances'] if i['type'] != 'A4.NetworkZone']
        from sdem.zone_layout import layout
        with self.assertRaises(LayoutError): layout(doc)

    def test_cli_and_view(self):
        env = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}
        r = subprocess.run([sys.executable, '-m', 'sdem', 'zones', '--layout', '--workspace', str(EX / 'payment-initiation'), '--json'], capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr); self.assertEqual(json.loads(r.stdout)['viewpoint'], 'deployment-zones')
        from sdem.view import render
        page = render(EX / 'fx-dealing' / 'graph', now='2026-11-14 00:00:00')
        self.assertIn('A4 Technology — by network zone', page); self.assertIn('Level 2 · Co-location rack — markets', page)


class ExamplesPhysicallyCompleteTests(unittest.TestCase):   # the gate: no physical gap in any example (LC-15, LC-16, LC-21, LC-22)
    def test_no_physical_gap_in_any_example(self):
        from sdem.graph import FederatedGraph
        for ws in sorted(p.parent for p in EX.glob('*/mappings.json')):
            with self.subTest(ws.name):
                fg = FederatedGraph.load(sorted(ws.glob('a[1-4]-*.json')) + [ws / 'mappings.json'])
                fg.check()
                gaps = [w for ws_ in fg.warnings.values() for w in ws_ if re.search(r'\bLC-(15|16|21|22)\b', w)]
                if ws.name == 'reference-structure': gaps = [w for w in gaps if 'LC-16' not in w and 'LC-15' not in w]   # one record per type: no deployment to place
                self.assertEqual(gaps, [])


if __name__ == '__main__':
    unittest.main()
