"""AID's inference rules against the full base BIAN (docs/design/aid-spec.md AID-R05…R07, S06 with no asset type): downstream and
upstream, no AI — the same input gives the same output; no domain guessed from an id fragment or a name that does not cover a
domain's subject."""
import sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem.aid import project  # noqa: E402
from sdem.metamodel import Metamodel  # noqa: E402
from sdem.new import base_layer  # noqa: E402


def ds(level, instances):
    return {'level': level, 'model_id': f'T-{level}', 'model_version': '1', 'metamodel_version': Metamodel.load().version, 'source_system': 'T',
            'instances': instances, 'relationships': []}


def names(pkg, level, kind):
    return sorted(i['name'] for i in pkg['layers'].get(level, {}).get('instances', []) if i['type'] == kind)


class AidInferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.cat, _ = base_layer()

    def test_upstream_from_a_deployment_named_after_its_application(self):  # AID-R05, R06, R03: A4 → A3 → A2 → A1
        dep = {'id': 'DEP-1', 'type': 'A4.Deployment', 'version': '1', 'name': 'Term Deposit Engine — production', 'lifecycle_status': 'planned',
               'attributes': {'component_id': 'APP-TD'}}
        pkg = project({'A4': ds('A4', [dep])}, self.cat)
        self.assertEqual(names(pkg, 'A3', 'A3.ApplicationComponent'), ['Term Deposit Engine'])        # named from its deployment
        self.assertEqual(names(pkg, 'A2', 'A2.ServiceDomain'), ['Term Deposit'])
        self.assertEqual(names(pkg, 'A1', 'A1.BusinessCapability'), ['Term Deposit (capability candidate)'])
        self.assertEqual(project({'A4': ds('A4', [dep])}, self.cat)['layers']['A2'], pkg['layers']['A2'])   # rules, not AI: the same every time

    def test_no_domain_from_an_id_fragment_or_a_name_that_does_not_say(self):  # AID-R06
        a4 = [{'id': 'INF-K8S', 'type': 'A4.SystemSoftware', 'version': '1', 'name': 'Kubernetes', 'lifecycle_status': 'active',
               'attributes': {'hosts': ['APP-PAY-HUB']}},
              {'id': 'DEP-HUB', 'type': 'A4.Deployment', 'version': '1', 'name': 'Payments Hub — production', 'lifecycle_status': 'planned',
               'attributes': {'component_id': 'APP-PAY-HUB'}}]
        pkg = project({'A4': ds('A4', a4)}, self.cat)
        self.assertEqual(names(pkg, 'A3', 'A3.ApplicationComponent'), ['Payments Hub'])
        self.assertEqual(names(pkg, 'A2', 'A2.ServiceDomain'), [])                                   # 'pay', 'payments' alone say too little
        self.assertTrue(any('does not say which BIAN service domain' in e for e in pkg['projection']['projection_ends']))

    def test_downstream_reaches_a_domain_bian_publishes_no_subject_for(self):  # S06: no asset type → the domain's name
        act = {'id': 'ACT-1', 'type': 'A1.BusinessActivity', 'version': '1', 'name': 'Execute credit risk operations', 'lifecycle_status': 'active',
               'attributes': {'sequence': 1}}
        pkg = project({'A1': ds('A1', [act])}, self.cat)
        self.assertEqual(names(pkg, 'A2', 'A2.ServiceDomain'), ['Credit Risk Operations'])


if __name__ == '__main__':
    unittest.main()
