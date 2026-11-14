"""Hosting and zone connectivity (metamodel 0.11.0; docs/design/sdem-hosting-inference-design.md, the owner's decisions H1–H8, 2026-11-14):
the organisation's default (PR-32), sdem new --hosting (WS-12), zone placements proposed from the evidence for a person to decide
(AID-Z01…Z04; LC-19, LC-20), and the zone connections SDEM works out (ZC-01…ZC-04). Synthetic examples only."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem.conformance import check_level             # noqa: E402
from sdem.hosting import evidence, judge, path, zone_connections   # noqa: E402
from sdem.metamodel import Metamodel                  # noqa: E402

PAY, LEDGER = ROOT / 'examples' / 'payment-initiation', ROOT / 'examples' / 'legacy-core-ledger'


def sdem(*args, cwd):
    env = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], cwd=cwd, capture_output=True, text=True, env=env)
    return r.returncode, r.stdout, r.stderr


def a4(ws): return json.loads((ws / 'a4-technology.json').read_text(encoding='utf-8'))


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, self.tmp, True); self.mm = Metamodel.load()

    def without_zones(self, src):
        ws = self.tmp / src.name; shutil.copytree(src, ws, ignore=shutil.ignore_patterns('graph'))
        d = a4(ws); d['instances'] = [i for i in d['instances'] if i['type'] != 'A4.NetworkZone']
        ids = {i['id'] for i in d['instances']}; d['relationships'] = [r for r in d['relationships'] if r['source'] in ids and r['target'] in ids]
        (ws / 'a4-technology.json').write_text(json.dumps(d, indent=2), encoding='utf-8'); return ws


class EvidenceTests(Base):   # HS-01…HS-10
    def test_the_evidence_and_the_default(self):
        led = {i['id']: i for i in a4(LEDGER)['instances']}
        kind, conf, used = judge(evidence(led['INF-MF-LPAR-PROD'], a4(LEDGER), self.mm), 'cloud')
        self.assertEqual((kind, conf), ('on_premises', 'high')); self.assertEqual({u['id'] for u in used}, {'HS-01', 'HS-02'})
        pay = {i['id']: i for i in a4(PAY)['instances']}
        self.assertEqual(judge(evidence(pay['INF-K8S-PAY-PROD'], a4(PAY), self.mm), 'on_premises')[:2], ('cloud', 'high'))   # region (HS-06) beats the default
        bare = {'id': 'X', 'type': 'A4.Node', 'name': 'Host 7', 'attributes': {}}
        self.assertEqual(judge(evidence(bare, {'instances': [bare], 'relationships': []}, self.mm), 'cloud')[:2], ('cloud', 'low'))   # HS-10

    def test_evidence_both_ways_is_never_guessed(self):
        both = {'id': 'X', 'type': 'A4.Node', 'name': 'Mainframe gateway', 'attributes': {'region': 'region-a'}}
        kind, conf, used = judge(evidence(both, {'instances': [both], 'relationships': []}, self.mm), 'cloud')
        self.assertEqual((kind, conf), (None, 'unresolved')); self.assertEqual({u['points_to'] for u in used}, {'cloud', 'on_premises'})


class ProposalTests(Base):   # AID-Z01…Z04, LC-19
    def test_aid_proposes_a_zone_from_the_evidence(self):
        ws = self.without_zones(LEDGER)
        code, out, err = sdem('aid', '--workspace', ws, '--person', 'jane.architect', cwd=self.tmp)
        self.assertEqual(code, 0, err); self.assertIn('placed in a proposed zone (AID-Z01)', out)
        d = a4(ws); zones = {i['id']: i['attributes'] for i in d['instances'] if i['type'] == 'A4.NetworkZone'}
        self.assertEqual(sorted(z['zone_kind'] for z in zones.values()), ['internal', 'on_premises'])
        self.assertTrue(all('inferred' in z for z in zones.values()))
        placed = [r for r in d['relationships'] if r.get('inferred')]
        self.assertEqual([r['target'] for r in placed], ['INF-MF-LPAR-PROD'])   # the DB2, MQ and the deployment on it are in its zone (AID-Z04)
        self.assertIn('HS-02', placed[0]['inferred']['source']); self.assertEqual(placed[0]['inferred']['confidence'], 'high')
        self.assertIn('LC-19', sdem('check', '--workspace', ws, cwd=self.tmp)[1] + sdem('check', '--workspace', ws, cwd=self.tmp)[2])

    def test_a_person_decides_each_placement(self):
        ws = self.without_zones(LEDGER); sdem('aid', '--workspace', ws, '--person', 'jane.architect', cwd=self.tmp)
        code, out, err = sdem('aid', 'reject', 'INF-MF-LPAR-PROD', '--workspace', ws, '--person', 'jane.architect', '--reason', 'moving to the cloud', cwd=self.tmp)
        self.assertEqual(code, 0, err); self.assertFalse([r for r in a4(ws)['relationships'] if r.get('inferred')])
        sdem('aid', '--workspace', ws, '--person', 'jane.architect', cwd=self.tmp)                       # a rejected placement is not proposed again
        self.assertFalse([r for r in a4(ws)['relationships'] if r.get('inferred')])
        ws2 = self.without_zones(PAY); sdem('aid', '--workspace', ws2, '--person', 'jane.architect', cwd=self.tmp)
        code, out, err = sdem('aid', 'confirm', 'INF-APIGW-PAY', '--workspace', ws2, '--person', 'jane.architect', cwd=self.tmp)
        self.assertEqual(code, 0, err)
        r = next(r for r in a4(ws2)['relationships'] if r.get('inferred') and r['target'] == 'INF-APIGW-PAY')
        self.assertEqual((r['inferred']['status'], r['inferred']['confirmed_by']), ('confirmed', 'jane.architect'))
        self.assertTrue(r['source'].endswith('-DMZ'))                                                       # internet facing (AID-Z02)


class PolicyTests(Base):   # PR-32, WS-12
    def test_the_hosting_policy_is_the_organisations(self):
        from sdem import profile as P
        prof = self.tmp / 'p.json'
        prof.write_text(json.dumps({'format': 'sdem-profile/1', 'name': 'onprem-first', 'version': 1, 'hosting': {'default': 'on_premises'}}))
        P.activate_file(prof); self.addCleanup(P.deactivate)
        from sdem.hosting import policy
        self.assertEqual(policy()['default'], 'on_premises')
        bad = P.resolve(prof); bad['hosting'] = {'default': 'moon'}
        self.assertTrue(any('hosting.default' in i for i in P.hosting_issues(bad)))

    def test_a_new_workspace_starts_with_its_hosting_template(self):
        code, out, err = sdem('new', '--workspace', 'ledger', '--person', 'jane.architect', '--hosting', 'hybrid', cwd=self.tmp)
        self.assertEqual(code, 0, err)
        d = a4(self.tmp / 'ledger'); kinds = sorted(i['attributes']['zone_kind'] for i in d['instances'])
        self.assertEqual(kinds, ['cloud', 'dmz', 'dmz', 'internal', 'internal', 'on_premises'])
        self.assertFalse(any('inferred' in i['attributes'] for i in d['instances']))                         # the person's choice
        self.assertEqual(sdem('check', '--workspace', self.tmp / 'ledger', cwd=self.tmp)[0], 0)


class ConnectionTests(Base):   # ZC-01…ZC-04
    def test_the_zone_connections_are_worked_out(self):
        c = {(a, b): r for a, b, r in zone_connections(a4(PAY), self.mm)}
        self.assertEqual(c[('ZONE-PAY-CLOUD', 'ZONE-PAY-ONPREM')], 'ZC-01')
        self.assertEqual(c[('ZONE-PAY-DMZ', 'ZONE-PAY-INTERNAL')], 'ZC-02')
        self.assertEqual(c[('ZONE-PAY-INTERNAL', 'NET-PAY-PRIVATE')], 'ZC-03')
        self.assertEqual(path(a4(PAY), self.mm, 'INF-APIGW-PAY', 'INF-CORE-LEDGER-HOST'),
                         ['INF-APIGW-PAY', 'ZONE-PAY-DMZ', 'ZONE-PAY-CLOUD', 'ZONE-PAY-ONPREM', 'ZONE-PAY-ONPREM-INTERNAL', 'INF-CORE-LEDGER-HOST'])
        code, out, _ = sdem('zones', 'path', 'INF-APIGW-PAY', 'INF-PG-PAY-PROD', '--workspace', PAY, cwd=self.tmp)
        self.assertEqual((code, out.strip()), (0, 'INF-APIGW-PAY → ZONE-PAY-DMZ → ZONE-PAY-INTERNAL → NET-PAY-PRIVATE → INF-PG-PAY-PROD'))

    def test_a_shape_placed_against_strong_evidence_is_named(self):   # LC-20
        d = a4(PAY); next(i for i in d['instances'] if i['id'] == 'INF-PG-PAY-PROD')['attributes']['site'] = 'DC-1'
        _, w, _ = check_level(d, self.mm)
        self.assertTrue(any(x.startswith('instance INF-PG-PAY-PROD: is in a cloud zone, but HS-01') for x in w), w)


class EvidenceAgainstTheExamplesTests(unittest.TestCase):   # G1–G3 (HS-11…HS-13): with its zones removed, each example's hosting is inferred as recorded
    def test_every_example_reinferred_as_recorded(self):
        from sdem.hosting import propose
        from sdem.conformance import zones_of
        from sdem.metamodel import Metamodel
        mm = Metamodel.load()
        for ws in sorted(p.parent for p in (ROOT / 'examples').glob('*/a4-technology.json')):
            if ws.name == 'reference-structure': continue
            with self.subTest(ws.name):
                d = json.loads((ws / 'a4-technology.json').read_text(encoding='utf-8'))
                at = {i['id']: (i.get('attributes') or {}) for i in d['instances']}
                shapes, parent, direct = zones_of(d, mm)
                def top(z):
                    while parent.get(z): z = parent[z]
                    return z
                want = {x: at[top(zs[0])].get('zone_kind') for x, zs in shapes.items() if zs and any(x in v for v in direct.values())}
                zid = {i['id'] for i in d['instances'] if i['type'] == 'A4.NetworkZone'}
                bare = {**d, 'instances': [i for i in d['instances'] if i['id'] not in zid], 'relationships': [r for r in d['relationships'] if r['source'] not in zid and r['target'] not in zid]}
                zones, links, unresolved = propose(bare, mm, 'T', 'jane.architect', '2026-11-14')
                kind = {z['id']: z['attributes']['zone_kind'] for z in zones}; par = {l['target']: l['source'] for l in links if l['kind'] == 'composition'}
                got = {l['target']: kind[par.get(l['source'], l['source'])] for l in links if l['kind'] == 'aggregation'}
                self.assertEqual({x: got.get(x) for x in want}, want); self.assertEqual(unresolved, [])

    def test_the_new_signals_read_what_the_record_says(self):
        from sdem.hosting import evidence
        from sdem.metamodel import Metamodel
        mm = Metamodel.load()
        fx = json.loads((ROOT / 'examples/fx-dealing/a4-technology.json').read_text(encoding='utf-8'))
        cf = json.loads((ROOT / 'examples/card-fraud-alerts/a4-technology.json').read_text(encoding='utf-8'))
        ids = lambda doc, x: {e['id'] for e in evidence(next(i for i in doc['instances'] if i['id'] == x), doc, mm)}
        self.assertIn('HS-11', ids(cf, 'INF-ONPREM-VM-CLUSTER-B'))   # "On-prem VM cluster B"
        self.assertIn('HS-11', ids(fx, 'NODE-RATEGW-01'))            # "co-location rack"
        self.assertIn('HS-13', ids(fx, 'NODE-RATEGW-01'))            # virtualisation: physical
        self.assertIn('HS-12', ids(fx, 'SYS-PG-FX-PROD'))            # in the private-cloud, data-centre environment


class S37Tests(unittest.TestCase):   # G4–G6: the network of the component's platform, not the deprecated network_zone
    def test_trade_finance_needs_no_network_zone(self):
        a3 = json.loads((ROOT / 'examples/trade-finance/a3-application.json').read_text(encoding='utf-8'))
        self.assertFalse([i['id'] for i in a3['instances'] if 'network_zone' in (i.get('attributes') or {})])
        from sdem.acceptance import run
        from sdem.rules_engine import RulesEngine
        c3 = next(r for r in run(RulesEngine(), ids=['C3']) if r['case'] == 'C3') if 'ids' in run.__code__.co_varnames else next(r for r in run(RulesEngine()) if r['case'] == 'C3')
        self.assertTrue(c3['passed']); self.assertEqual(c3['score']['candidates']['fn'], 0)


if __name__ == '__main__':
    unittest.main()
