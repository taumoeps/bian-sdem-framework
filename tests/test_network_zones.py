"""Network zones (metamodel 0.10.0; docs/design/sdem-network-zones-design.md, the owner's decisions Z1–Z6, 2026-11-14): level 0 on premises or
cloud, level 1 internal or DMZ inside it, level 2 a private network inside that; every shape in one zone (LC-16), the structure checked
(LC-17), internet-facing shapes in a DMZ (LC-18), and a change to a zone reaching everything in it (KG-Q-08). Synthetic examples only."""
import copy, json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem.conformance import check_level, zones_of   # noqa: E402
from sdem.metamodel import Metamodel                  # noqa: E402

PAY = ROOT / 'examples' / 'payment-initiation'
FILES = ['a1-business.json', 'a2-service-domain.json', 'a3-application.json', 'a4-technology.json', 'mappings.json']


def a4():
    return json.loads((PAY / 'a4-technology.json').read_text(encoding='utf-8'))


def found(doc, *ids):
    e, w, _ = check_level(doc, Metamodel.load())
    return [x for x in e + w if any(f'LC-{i}' in x for i in ids)]


class ModelTests(unittest.TestCase):
    def test_a_zone_is_a_network_with_a_level_and_a_kind(self):
        mm = Metamodel.load()
        self.assertTrue(mm.is_a('A4.NetworkZone', 'A4.CommunicationNetwork'))
        rows = {c['id']: c for c in json.loads((ROOT / 'metamodel' / 'level-relationships.json').read_text(encoding='utf-8'))['constraints']}
        self.assertEqual((rows['RA4-38']['source_type'], rows['RA4-38']['kind']), ('A4.NetworkZone', 'aggregation'))
        at = {a['id']: a for a in json.loads((ROOT / 'metamodel' / 'entity-attributes.json').read_text(encoding='utf-8'))['attributes']}
        self.assertEqual(at['AT-A4-35']['values'], ['on_premises', 'cloud', 'internal', 'dmz', 'private'])
        self.assertEqual(at['AT-A3-07']['status'], 'deprecated')   # a component's zone is its platform's (Z3)


class PlacementTests(unittest.TestCase):   # LC-16
    def test_the_payment_example_places_every_shape(self):
        shapes, parent, _ = zones_of(a4(), Metamodel.load())
        self.assertEqual({x for x, z in shapes.items() if not z}, set())
        self.assertEqual(shapes['DEP-PAYHUB-PROD'], ['NET-PAY-PRIVATE'])   # through the cluster it runs on
        self.assertEqual(shapes['TS-MQ'], ['ZONE-PAY-INTERNAL'])
        self.assertNotIn('ENV-PAY-PROD', shapes)                            # environments are not placed (Z2)
        self.assertEqual(parent, {'ZONE-PAY-INTERNAL': 'ZONE-PAY-CLOUD', 'ZONE-PAY-DMZ': 'ZONE-PAY-CLOUD', 'NET-PAY-PRIVATE': 'ZONE-PAY-INTERNAL',
                                  'ZONE-PAY-ONPREM-INTERNAL': 'ZONE-PAY-ONPREM'})   # hybrid since 0.11.0
        self.assertEqual(found(a4(), 15, 16, 17, 18), [])

    def test_a_shape_in_no_zone_is_named(self):
        d = a4(); d['relationships'] = [r for r in d['relationships'] if not (r['source'] == 'ZONE-PAY-INTERNAL' and r['target'] == 'TS-MQ')]
        self.assertEqual(found(d, 16), ['instance TS-MQ: is in no network zone — place it, or what it runs on, in an internal, DMZ or private zone (RA4-38, LC-16)'])

    def test_a_workspace_with_no_zones_is_told_once(self):
        doc = {'level': 'A4', 'model_id': 't', 'model_version': '1', 'metamodel_version': Metamodel.load().version, 'source_system': 'T',
               'instances': [{'id': 'N', 'type': 'A4.Node', 'version': '1', 'name': 'N', 'lifecycle_status': 'active'}], 'relationships': []}
        w = found(doc, 16); self.assertEqual(len(w), 1); self.assertIn('no network zones recorded', w[0])


class StructureTests(unittest.TestCase):   # LC-17
    def test_a_kind_wrong_for_its_level_is_an_error(self):
        d = a4(); next(i for i in d['instances'] if i['id'] == 'ZONE-PAY-DMZ')['attributes']['zone_kind'] = 'private'
        e, _, _ = check_level(d, Metamodel.load())
        self.assertIn("instance ZONE-PAY-DMZ: a level-1 zone is internal or dmz, not 'private' (LC-17)", e)

    def test_a_level_1_zone_outside_a_level_0_is_an_error(self):
        d = a4(); d['relationships'] = [r for r in d['relationships'] if not (r['source'] == 'ZONE-PAY-CLOUD' and r['target'] == 'ZONE-PAY-DMZ')]
        e, _, _ = check_level(d, Metamodel.load())
        self.assertTrue(any(x.startswith('instance ZONE-PAY-DMZ: a level-1 zone is part of a level-0 zone') for x in e), e)

    def test_two_internal_zones_contradict_and_none_is_incomplete(self):
        d = a4(); z = copy.deepcopy(next(i for i in d['instances'] if i['id'] == 'ZONE-PAY-INTERNAL')); z.update(id='ZONE-X', name='Second internal')
        d['instances'].append(z); d['relationships'].append({'source': 'ZONE-PAY-CLOUD', 'kind': 'composition', 'target': 'ZONE-X'})
        e, _, _ = check_level(d, Metamodel.load())
        self.assertIn('instance ZONE-PAY-CLOUD: a level-0 zone has exactly one internal zone, not 2 (LC-17)', e)
        d = a4(); d['relationships'] = [r for r in d['relationships'] if not (r['source'] == 'ZONE-PAY-CLOUD' and r['target'] == 'ZONE-PAY-INTERNAL')]
        _, w, _ = check_level(d, Metamodel.load())
        self.assertTrue(any('a level-0 zone has no internal zone yet' in x for x in w), w)


class DmzTests(unittest.TestCase):   # LC-18
    def test_internet_facing_belongs_in_a_dmz_and_only_there(self):
        d = a4(); next(i for i in d['instances'] if i['id'] == 'INF-APIGW-PAY')['attributes']['internet_facing'] = False
        self.assertEqual(found(d, 18), ['instance INF-APIGW-PAY: is in DMZ ZONE-PAY-DMZ but not internet facing — a DMZ holds only internet-facing shapes (LC-18)'])
        d = a4(); next(i for i in d['instances'] if i['id'] == 'INF-PG-PAY-PROD')['attributes']['internet_facing'] = True
        self.assertEqual(found(d, 18), ['instance INF-PG-PAY-PROD: is internet facing but in NET-PAY-PRIVATE, not a DMZ (LC-18)'])


class ImpactTests(unittest.TestCase):   # KG-Q-08 with zones
    def test_retiring_the_cloud_zone_reaches_everything_in_it(self):
        env = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}
        r = subprocess.run([sys.executable, '-m', 'sdem', 'impact', 'ZONE-PAY-CLOUD', '--change', 'retire', *FILES, '--json'], cwd=PAY, capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        got = {x['id']: x for x in json.loads(r.stdout)['instances']}
        for rid in ('ZONE-PAY-INTERNAL', 'ZONE-PAY-DMZ', 'NET-PAY-PRIVATE', 'INF-K8S-PAY-PROD', 'TS-MQ', 'INF-APIGW-PAY', 'APP-PAY-HUB', 'CAP-PAY-010'): self.assertIn(rid, got)
        self.assertEqual(got['ZONE-PAY-INTERNAL']['via'], ['RA4-27'])


class UnconnectedTests(unittest.TestCase):   # LC-21
    def test_a_shape_connected_to_nothing_is_named(self):
        docs = {f: json.loads((PAY / f).read_text(encoding='utf-8')) for f in FILES}
        tmp = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, tmp, True)
        for f, d in docs.items():
            if f == 'a4-technology.json': d['relationships'] = [r for r in d['relationships'] if r['source'] != 'INF-APIGW-PAY']
            if f == 'mappings.json': d['mappings'] = [m for m in d['mappings'] if m['target']['id'] != 'INF-APIGW-PAY']   # what it exposes (EXPOSED_THROUGH) goes too
            (tmp / f).write_text(json.dumps(d), encoding='utf-8')
        code, out, err = sdem_in(tmp, 'check', '--workspace', tmp)
        self.assertIn('instance INF-APIGW-PAY: is internet facing but fronts nothing — link it to what it exposes (LC-21)', out + err)
        code, out, err = sdem_in(PAY, 'check', '--workspace', PAY)
        self.assertNotIn('LC-21', out + err)                                                     # every shape in the example is connected


def sdem_in(cwd, *args):
    env = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], cwd=cwd, capture_output=True, text=True, env=env)
    return r.returncode, r.stdout, r.stderr


if __name__ == '__main__':
    unittest.main()
