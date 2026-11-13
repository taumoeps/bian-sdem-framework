"""A platform's network is a link (RA4-37), checked (LC-15) and followed by trace and impact (KG-Q-08); a network's `connects`
list becomes those links on migration (metamodel 0.8.1 → 0.9.0; the owner's decision, 2026-11-14). Synthetic examples only."""
import collections, copy, json, os, subprocess, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem import migrate                     # noqa: E402
from sdem.conformance import check_level     # noqa: E402
from sdem.metamodel import Metamodel         # noqa: E402

PAY = ROOT / 'examples' / 'payment-initiation'
FILES = ['a1-business.json', 'a2-service-domain.json', 'a3-application.json', 'a4-technology.json', 'mappings.json']


def sdem(*args):
    env = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], cwd=PAY, capture_output=True, text=True, env=env)
    return r.returncode, r.stdout, r.stderr


def a4(instances, relationships):
    return {'level': 'A4', 'model_id': 't', 'model_version': '1', 'metamodel_version': Metamodel.load().version, 'source_system': 'TEST',
            'instances': [{'id': i, 'type': t, 'version': '1.0', 'name': i, 'lifecycle_status': 'active'} for i, t in instances],
            'relationships': [{'source': s, 'kind': k, 'target': t} for s, k, t in relationships]}


class RuleTests(unittest.TestCase):   # RA4-37
    def test_a_platform_is_connected_to_a_network_by_a_rule_of_its_own(self):
        mm = Metamodel.load()
        row = next(c for c in json.loads((ROOT / 'metamodel' / 'level-relationships.json').read_text(encoding='utf-8'))['constraints'] if c['id'] == 'RA4-37')
        self.assertEqual((row['source_type'], row['kind'], row['target_type']), ('A4.InfrastructureComponent', 'association', 'A4.CommunicationNetwork'))
        for t in ('A4.Node', 'A4.Device', 'A4.SystemSoftware'): self.assertTrue(mm.is_a(t, row['source_type']), t)

    def test_connects_is_deprecated(self):
        at = next(a for a in json.loads((ROOT / 'metamodel' / 'entity-attributes.json').read_text(encoding='utf-8'))['attributes'] if a['id'] == 'AT-A4-07')
        self.assertEqual((at['name'], at['status']), ('connects', 'deprecated'))


class OnANetworkTests(unittest.TestCase):   # LC-15
    def warnings(self, doc):
        return [w for w in check_level(doc, Metamodel.load())[1] if 'LC-15' in w]

    def test_a_hosting_platform_on_no_network_is_a_warning(self):
        doc = a4([('K8S', 'A4.SystemSoftware'), ('DEP', 'A4.Deployment'), ('NET', 'A4.CommunicationNetwork')], [('K8S', 'assignment', 'DEP')])
        w = self.warnings(doc)
        self.assertEqual(len(w), 1); self.assertIn('instance K8S: hosts DEP but is on no communication network', w[0])   # the deployment is not warned: it is on its platform's
        doc['relationships'].append({'source': 'K8S', 'kind': 'association', 'target': 'NET'})
        self.assertEqual(self.warnings(doc), [])

    def test_the_network_of_the_node_it_runs_on_counts(self):
        doc = a4([('NODE', 'A4.Node'), ('PG', 'A4.SystemSoftware'), ('ENV', 'A4.DeploymentEnvironment'), ('NET', 'A4.CommunicationNetwork')],
                 [('NODE', 'assignment', 'PG'), ('ENV', 'aggregation', 'PG'), ('NODE', 'association', 'NET')])
        self.assertEqual(self.warnings(doc), [])

    def test_a_platform_hosting_nothing_is_not_checked(self):
        self.assertEqual(self.warnings(a4([('SPARE', 'A4.Node')], [])), [])

    def test_the_payment_example_has_every_platform_on_a_network(self):
        code, out, err = sdem('check', '--workspace', '.')
        self.assertEqual(code, 0, err); self.assertNotIn('LC-15', out + err)


class FollowedTests(unittest.TestCase):   # KG-Q-08
    def impact(self, rid, change='retire'):
        code, out, err = sdem('impact', rid, '--change', change, *FILES, '--json')
        self.assertEqual(code, 0, err); return json.loads(out)

    def test_retiring_the_network_reaches_the_applications_and_the_business(self):
        r = self.impact('NET-PAY-PRIVATE'); got = {x['id']: x for x in r['instances']}
        for rid in ('INF-K8S-PAY-PROD', 'INF-K8S-PAY-UAT', 'INF-PG-PAY-PROD', 'APP-PAY-HUB', 'CMP-PAY-EXEC', 'SD-PI', 'CAP-PAY-010'): self.assertIn(rid, got)
        self.assertEqual(got['INF-K8S-PAY-PROD']['classification'], 'design_change_required')
        self.assertEqual(got['APP-PAY-HUB']['via'], ['RA4-37', 'PAY-108'])
        self.assertEqual(r['mappings_to_supersede'], [])   # a network hop is not a mapping
        self.assertEqual(got['INF-K8S-PAY-UAT']['classification'], 'design_change_required')   # UAT is on the same network

    def test_a_trace_down_reaches_the_network(self):
        code, out, err = sdem('trace', 'APP-PAY-HUB', '--direction', 'down', *FILES)
        self.assertEqual(code, 0, err); self.assertIn('CONNECTED_TO', out); self.assertIn('NET-PAY-PRIVATE', out)


class MigrationTests(unittest.TestCase):   # 0.8.1 → 0.9.0
    def test_connects_becomes_links_once(self):
        step = next(m for m in migrate._j(migrate.RECORD)['migrations'] if m['to'] == '0.9.0')['steps']
        doc = a4([('N1', 'A4.Node'), ('N2', 'A4.Node'), ('NET', 'A4.CommunicationNetwork')], [('N2', 'association', 'NET')])
        doc['instances'][2]['attributes'] = {'connects': ['N1', 'N2', 'GONE']}
        counts = collections.Counter(); out = copy.deepcopy(doc)
        migrate._apply_dataset(out, step, counts)
        self.assertNotIn('connects', out['instances'][2]['attributes'])
        self.assertEqual(sorted((r['source'], r['target']) for r in out['relationships']), [('N1', 'NET'), ('N2', 'NET')])   # N2 not doubled; GONE not invented
        self.assertEqual(counts['attribute_to_links'], 1)


if __name__ == '__main__':
    unittest.main()
