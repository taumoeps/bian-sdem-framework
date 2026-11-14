"""Edge exposure and A4 connections (metamodel 0.12.0; docs/design/sdem-edge-exposure-design.md, the owner's decisions X1–X6, 2026-11-14):
EXPOSED_THROUGH between an internet-facing A3 interface and an A4 edge platform (LC-22, AID-X01), and at A4 a proposed connection for every
shape linked to nothing (AID-C01…C06). Synthetic examples only."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
EX = ROOT / 'examples'


def sdem(*args, cwd):
    env = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], cwd=cwd, capture_output=True, text=True, env=env)
    return r.returncode, r.stdout, r.stderr


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, self.tmp, True)

    def copy(self, name):
        ws = self.tmp / name; shutil.copytree(EX / name, ws, ignore=shutil.ignore_patterns('graph')); return ws

    def j(self, ws, f): return json.loads((ws / f).read_text(encoding='utf-8'))

    def w(self, ws, f, d): (ws / f).write_text(json.dumps(d, indent=2), encoding='utf-8')


class ExposureTests(Base):   # X1–X5, LC-22, AID-X01
    def test_the_payment_api_is_exposed_through_the_gateway(self):
        m = next(x for x in self.j(EX / 'payment-initiation', 'mappings.json')['mappings'] if x['relationship'] == 'EXPOSED_THROUGH')
        self.assertEqual((m['source']['id'], m['target']['id'], m['status']), ('IFC-PAY-API', 'INF-APIGW-PAY', 'approved'))
        self.assertTrue(m['evidence'][0].startswith('network_design:'))
        code, out, err = sdem('check', '--workspace', EX / 'payment-initiation', cwd=self.tmp)
        self.assertEqual(code, 0, err); self.assertNotIn('LC-22', out + err); self.assertNotIn('LC-21', out + err)

    def test_an_internet_facing_interface_exposed_through_nothing_is_named_and_proposed(self):
        ws = self.copy('payment-initiation'); d = self.j(ws, 'mappings.json')
        d['mappings'] = [x for x in d['mappings'] if x['relationship'] != 'EXPOSED_THROUGH']; self.w(ws, 'mappings.json', d)
        out = ''.join(sdem('check', '--workspace', ws, cwd=self.tmp)[1:])
        self.assertIn('instance IFC-PAY-API: is internet facing but exposed through nothing', out)
        code, out, err = sdem('aid', '--workspace', ws, '--person', 'jane.architect', cwd=self.tmp)
        self.assertEqual(code, 0, err)
        props = [m for f in (ws / 'aid').glob('AID-*-proposals.json') for m in self.j(ws / 'aid', f.name)['mappings'] if m['relationship'] == 'EXPOSED_THROUGH']
        self.assertEqual([(m['source']['id'], m['target']['id'], m['status']) for m in props], [('IFC-PAY-API', 'INF-APIGW-PAY', 'proposed')])   # a person approves it

    def test_two_edge_platforms_are_never_guessed(self):
        from sdem.a4_connect import propose_exposure
        from sdem.metamodel import Metamodel
        a3 = self.j(EX / 'payment-initiation', 'a3-application.json'); a4 = self.j(EX / 'payment-initiation', 'a4-technology.json')
        a4['instances'].append({'id': 'INF-WAF', 'type': 'A4.Node', 'version': '1', 'name': 'Web application firewall', 'lifecycle_status': 'active', 'attributes': {'internet_facing': True}})
        pairs, unresolved = propose_exposure(a3, a4, [], Metamodel.load())
        self.assertEqual(pairs, []); self.assertEqual(unresolved[0]['id'], 'IFC-PAY-API'); self.assertEqual(sorted(unresolved[0]['candidates']), ['INF-APIGW-PAY', 'INF-WAF'])


class ConnectionTests(Base):   # X6, AID-C01…C06
    def unlinked(self):   # acquired-fintech as it was before its A4 links were recorded (2026-11-14): its platforms linked to nothing inside A4
        ws = self.copy('acquired-fintech'); d = self.j(ws, 'a4-technology.json')
        lone = {'INF-EKS-ZIPPA-PROD', 'INF-PG-ZIPPA-PROD', 'INF-REDIS-ZIPPA-PROD', 'TS-QUEUE'}
        d['relationships'] = [r for r in d['relationships'] if not ({r['source'], r['target']} & lone)]; self.w(ws, 'a4-technology.json', d)
        return ws

    def test_every_a4_shape_linked_to_nothing_gets_a_proposed_connection(self):
        ws = self.unlinked()
        before = ''.join(sdem('check', '--workspace', ws, cwd=self.tmp)[1:]).count('LC-21')
        self.assertGreater(before, 0)
        code, out, err = sdem('aid', '--workspace', ws, '--person', 'jane.architect', cwd=self.tmp)
        self.assertEqual(code, 0, err); self.assertIn('connection(s) proposed for shapes linked to nothing', out)
        links = [r for r in self.j(ws, 'a4-technology.json')['relationships'] if (r.get('inferred') or {}).get('rule', '').startswith('AID-C')]
        self.assertTrue(links and all(r['inferred']['status'] == 'proposed' and r['inferred']['source'] for r in links))
        self.assertEqual(''.join(sdem('check', '--workspace', ws, cwd=self.tmp)[1:]).count('LC-21'), 0)

    def test_a_person_decides_them_by_the_shape(self):
        ws = self.unlinked(); sdem('aid', '--workspace', ws, '--person', 'jane.architect', cwd=self.tmp)
        code, out, err = sdem('aid', 'reject', 'TS-QUEUE', '--workspace', ws, '--person', 'jane.architect', '--reason', 'serves another platform', cwd=self.tmp)
        self.assertEqual(code, 0, err)
        self.assertFalse([r for r in self.j(ws, 'a4-technology.json')['relationships'] if 'TS-QUEUE' in (r['source'], r['target']) and r.get('inferred')])
        sdem('aid', '--workspace', ws, '--person', 'jane.architect', cwd=self.tmp)   # not proposed again
        self.assertFalse([r for r in self.j(ws, 'a4-technology.json')['relationships'] if r['source'] == 'TS-QUEUE' and r.get('inferred')])

    def test_a_deployment_runs_on_its_components_platform(self):   # AID-C01
        from sdem.a4_connect import propose_connections
        from sdem.metamodel import Metamodel
        ws = EX / 'payment-initiation'; a4 = self.j(ws, 'a4-technology.json')
        a4['relationships'] = [r for r in a4['relationships'] if not (r['source'] == 'INF-K8S-PAY-PROD' and r['target'] == 'DEP-PAYEXEC-PROD')]
        a4['relationships'] = [r for r in a4['relationships'] if not (r['target'] == 'DEP-PAYEXEC-PROD' or r['source'] == 'DEP-PAYEXEC-PROD')]
        links, _ = propose_connections(self.j(ws, 'a3-application.json'), a4, self.j(ws, 'mappings.json')['mappings'], Metamodel.load(), 'AID-T', 'jane.architect', '2026-11-14')
        self.assertIn(('INF-K8S-PAY-PROD', 'assignment', 'DEP-PAYEXEC-PROD', 'AID-C01', 'high'),
                      [(r['source'], r['kind'], r['target'], r['inferred']['rule'], r['inferred']['confidence']) for r in links])

    def test_a_deployment_runs_on_the_platform_its_record_names(self):   # AID-C01, platform_id first
        from sdem.a4_connect import propose_connections
        from sdem.metamodel import Metamodel
        ws = EX / 'trade-finance'; a4 = self.j(ws, 'a4-technology.json')
        a4['relationships'] = [r for r in a4['relationships'] if not (r['kind'] == 'assignment' and r['target'] == 'DEP-DOC-PROD')]
        links, _ = propose_connections(self.j(ws, 'a3-application.json'), a4, self.j(ws, 'mappings.json')['mappings'], Metamodel.load(), 'AID-T', 'jane.architect', '2026-11-14')
        self.assertIn(('NODE-TF-PROD', 'assignment', 'DEP-DOC-PROD', 'AID-C01'), [(r['source'], r['kind'], r['target'], r['inferred']['rule']) for r in links])

    def test_an_edge_platform_fronts_the_deployment_of_what_it_exposes(self):   # AID-C06, LC-21 counts only links inside A4
        from sdem.a4_connect import propose_connections
        from sdem.metamodel import Metamodel
        ws = self.copy('payment-initiation'); a4 = self.j(ws, 'a4-technology.json')
        a4['relationships'] = [r for r in a4['relationships'] if not (r['source'] == 'INF-APIGW-PAY' and r['kind'] == 'association')]; self.w(ws, 'a4-technology.json', a4)
        out = ''.join(sdem('check', '--workspace', ws, cwd=self.tmp)[1:])
        self.assertIn('instance INF-APIGW-PAY: is internet facing but fronts nothing inside A4', out)   # EXPOSED_THROUGH (another layer) does not count
        links, _ = propose_connections(self.j(ws, 'a3-application.json'), a4, self.j(ws, 'mappings.json')['mappings'], Metamodel.load(), 'AID-T', 'jane.architect', '2026-11-14')
        self.assertIn(('INF-APIGW-PAY', 'association', 'DEP-PAYHUB-PROD', 'AID-C06', 'high'),
                      [(r['source'], r['kind'], r['target'], r['inferred']['rule'], r['inferred']['confidence']) for r in links])   # production, not UAT


class DatabaseConnectionTests(Base):   # LC-21 counts only links to another shape; AID-C02 reads stored_in lists and the environment
    def test_a_database_on_a_network_but_used_by_no_shape_is_named_and_proposed(self):
        from sdem.a4_connect import propose_connections
        from sdem.metamodel import Metamodel
        ws = self.copy('payment-initiation'); a4 = self.j(ws, 'a4-technology.json')
        a4['relationships'] = [r for r in a4['relationships'] if not (r['source'] == 'INF-K8S-PAY-PROD' and r['target'] == 'INF-PG-PAY-PROD')]
        self.w(ws, 'a4-technology.json', a4)   # left: its environment, its zone and its network — none of them a shape that uses it
        out = ''.join(sdem('check', '--workspace', ws, cwd=self.tmp)[1:])
        self.assertIn('instance INF-PG-PAY-PROD: is connected to nothing inside A4', out)
        links, _ = propose_connections(self.j(ws, 'a3-application.json'), a4, self.j(ws, 'mappings.json')['mappings'], Metamodel.load(), 'AID-T', 'jane.architect', '2026-11-14')
        self.assertEqual([(r['source'], r['target'], r['inferred']['rule'], r['inferred']['confidence']) for r in links],
                         [('INF-K8S-PAY-PROD', 'INF-PG-PAY-PROD', 'AID-C02', 'medium')])   # the production cluster — not the UAT one

class BuiltAsTests(Base):   # metamodel 0.14.0: an application BUILT_AS its artifact (AID-X02)
    def test_the_payment_hub_is_built_as_its_image(self):
        m = next(x for x in self.j(EX / 'payment-initiation', 'mappings.json')['mappings'] if x['relationship'] == 'BUILT_AS')
        self.assertEqual((m['source']['id'], m['target']['id'], m['status']), ('APP-PAY-HUB', 'ART-PAYHUB-IMG', 'approved'))
        self.assertTrue(m['evidence'][0].startswith('build_pipeline:'))
        from sdem.graph import FederatedGraph
        P = EX / 'payment-initiation'
        fg = FederatedGraph.load(sorted(P.glob('a[1-4]-*.json')) + [P / 'mappings.json'])
        hit = {r['id'] for r in fg.impact('ART-PAYHUB-IMG', 'modify')['instances'] if r['classification'] != 'no_impact'}
        self.assertIn('APP-PAY-HUB', hit)   # a rebuilt image reaches the application

    def test_sdem_aid_proposes_it_from_what_the_records_say(self):
        from sdem.a4_connect import propose_builds
        from sdem.metamodel import Metamodel
        mm = Metamodel.load()
        tf = EX / 'trade-finance'
        got = propose_builds(self.j(tf, 'a3-application.json'), self.j(tf, 'a4-technology.json'), self.j(tf, 'mappings.json')['mappings'], mm)
        self.assertEqual([(c, a) for c, a, _ in got], [('APP-DOC', 'ART-DOC-IMG'), ('APP-LC', 'ART-LC-IMG')])
        ws = self.copy('payment-initiation'); d = self.j(ws, 'mappings.json')
        d['mappings'] = [x for x in d['mappings'] if x['relationship'] != 'BUILT_AS']; self.w(ws, 'mappings.json', d)
        got = propose_builds(self.j(ws, 'a3-application.json'), self.j(ws, 'a4-technology.json'), d['mappings'], mm)
        self.assertEqual([(c, a) for c, a, _ in got], [('APP-PAY-HUB', 'ART-PAYHUB-IMG')])   # the image is in the hub's deployment (RA4-35)
        self.assertIn('RA4-35', got[0][2])

if __name__ == '__main__':
    unittest.main()
