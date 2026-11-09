"""The B1 review of the cross-layer link types (docs/design/b1-cross-layer-link-review.md; metamodel 0.8.0): DEPLOYED_ON targets
only what hosts software, verified against ArchiMate 3.2; the old row deprecated, not removed; the migration narrows connections
that named the supertype; `sdem migrate` covers a profile's added layers. Synthetic data only."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem.metamodel import Metamodel  # noqa: E402
CURRENT = Metamodel.load().version   # the metamodel a migration ends at
from sdem.validate import validate, load_registry  # noqa: E402

ENV = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}


def sdem(*args, cwd, ok=(0,)):
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], cwd=cwd, capture_output=True, text=True, env=ENV)
    assert r.returncode in ok, f'sdem {" ".join(map(str, args))}: exit {r.returncode}\n{r.stdout[-900:]}\n{r.stderr[-900:]}'
    return r.returncode, r.stdout + r.stderr, (json.loads(r.stdout) if r.stdout.strip().startswith('{') else None)


def back_to_070(ws):
    """The workspace as it was written under metamodel 0.7.0 — every dataset and the registry."""
    for f in list(ws.glob('a*-*.json')) + [ws / 'mappings.json']:
        d = json.loads(f.read_text()); d['metamodel_version'] = '0.7.0'; f.write_text(json.dumps(d))


class B1Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); self.ws = self.tmp / 'ws'
        sdem('new', '--workspace', self.ws, '--person', 'steven', '--example', 'payment-initiation', cwd=self.tmp)

    def tearDown(self):
        from sdem import profile as P; P.deactivate(); shutil.rmtree(self.tmp, ignore_errors=True)

    def test_deployed_on_targets_only_what_hosts_software(self):
        reg = load_registry()
        targets = {r['target_type'] for r in reg['relationships'] if r['relationship'] == 'DEPLOYED_ON'}
        self.assertEqual(targets, {'A4.Node', 'A4.Device', 'A4.SystemSoftware'})
        self.assertTrue(all(r['verification'] == 'verified_against_archi' and r['confidence'] == 'high' for r in reg['relationships'] if r['relationship'] == 'DEPLOYED_ON'))
        self.assertEqual(next(r for r in reg['relationships'] if r['mapping_type_id'] == 'VALUE_STREAM_ALIGNED_TO_SCENARIO')['authority'], 'enterprise_rule')

    def test_a_connection_to_a_technology_service_warns_until_0_9_0(self):
        doc = json.loads((self.ws / 'mappings.json').read_text())
        m = next(x for x in doc['mappings'] if x['relationship'] == 'DEPLOYED_ON' and x['status'] == 'approved')
        m['target'] = {**m['target'], 'id': 'TS-MQ', 'type': 'A4.TechnologyService', 'version': '1'}
        warnings = []
        issues = [i for i in validate({'mappings': [m]}, warnings=warnings) if 'TS-MQ' in i or 'TechnologyService' in i]
        self.assertEqual(issues, [])
        self.assertTrue(any('allowed only by the deprecated link type COMPONENT_DEPLOYED_ON_INFRASTRUCTURE' in w and '0.9.0' in w for w in warnings))

    def test_the_migration_gives_a_supertype_connection_its_records_type(self):
        doc = json.loads((self.ws / 'mappings.json').read_text())
        m = next(x for x in doc['mappings'] if x['relationship'] == 'DEPLOYED_ON' and x['target']['id'] == 'INF-K8S-PAY-PROD')
        m['target']['type'] = 'A4.InfrastructureComponent'; (self.ws / 'mappings.json').write_text(json.dumps(doc))
        back_to_070(self.ws)
        _, _, r = sdem('migrate', '--workspace', self.ws, '--person', 'steven', '--json', cwd=self.tmp)
        self.assertEqual(r['changes'].get('narrow_endpoint_type'), 1)
        after = json.loads((self.ws / 'mappings.json').read_text())
        self.assertEqual(next(x for x in after['mappings'] if x['mapping_id'] == m['mapping_id'])['target']['type'], 'A4.SystemSoftware')
        self.assertEqual(after['metamodel_version'], CURRENT)   # migrated through 0.8.0 (B1) to the current version

    def test_migrate_covers_a_profiles_added_layers(self):
        prof = {'format': 'sdem-profile/1', 'name': 'sites', 'version': 1,   # one added layer, no other rules
                'layers': [{'code': 'A5', 'name': 'A5 Physical', 'position': 'below', 'file': 'a5-physical.json'}],
                'types': [{'type': 'ORG.A5.Facility', 'definition': 'a site'}],
                'link_types': [{'source_type': 'A4.InfrastructureComponent', 'relationship': 'HOUSED_IN', 'target_type': 'ORG.A5.Facility', 'required_evidence': ['site_register']}]}
        (self.ws / 'sdem-profile.json').write_text(json.dumps(prof))
        sdem('profile', 'adopt', '--workspace', self.ws, '--person', 'steven', '--reason', 'test', cwd=self.tmp)
        back_to_070(self.ws)
        _, _, r = sdem('migrate', '--workspace', self.ws, '--person', 'steven', '--json', cwd=self.tmp)
        self.assertIn('a5-physical.json', [f['file'] for f in r['files']])
        self.assertEqual(json.loads((self.ws / 'a5-physical.json').read_text())['metamodel_version'], CURRENT)


    def test_a_narrowed_endpoint_keeps_an_approved_record_immutable_otherwise(self):   # the registry diff in CI (sdem diff)
        import copy
        from sdem.diff import diff
        a = {'mappings': [{'mapping_id': 'M1', 'status': 'approved', 'source': {'id': 'A', 'type': 'A3.ApplicationComponent', 'version': '1'},
                           'target': {'id': 'X', 'type': 'A4.InfrastructureComponent', 'version': '1'}}]}
        b = copy.deepcopy(a); b['mappings'][0]['target']['type'] = 'A4.SystemSoftware'
        self.assertEqual(diff(a, b), [])                                                               # the migration's narrowing
        c = copy.deepcopy(b); c['mappings'][0]['target']['id'] = 'Y'
        self.assertTrue(diff(a, c))                                                                    # another record: refused
        d = copy.deepcopy(a); d['mappings'][0]['target']['type'] = 'A2.ServiceDomain'
        self.assertTrue(diff(a, d))                                                                    # not a subtype: refused

if __name__ == '__main__':
    unittest.main()
