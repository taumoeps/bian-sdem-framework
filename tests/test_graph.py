import copy, json, unittest
from pathlib import Path
from sdmm.graph import LevelGraph, FederatedGraph, IMPACT_RULES
from sdmm.metamodel import Metamodel

ROOT = Path(__file__).resolve().parents[1]
F = ROOT / 'examples/card-fraud-alerts'
FILES = sorted(F.glob('a*.json')) + [F / 'mappings.json']


class LevelGraphTests(unittest.TestCase):
    def setUp(self):
        self.mm = Metamodel.load()
        self.a2 = json.loads((F / 'a2-service-domain.json').read_text())
        self.a4 = json.loads((F / 'a4-technology.json').read_text())

    def test_shipped_levels_validate(self):
        for p in F.glob('a*.json'):
            self.assertEqual(LevelGraph.load(p, self.mm).validate(), [], p.name)

    def test_abstract_entity_rejected_as_instance_type(self):
        d = copy.deepcopy(self.a4); d['instances'][0]['type'] = 'A4.InfrastructureComponent'
        self.assertTrue(any('is abstract' in x for x in LevelGraph(d, self.mm).validate()))

    def test_wrong_level_entity_rejected(self):
        d = copy.deepcopy(self.a4); d['instances'][0]['type'] = 'A3.ApplicationComponent'
        self.assertTrue(any('is not an A4 entity' in x for x in LevelGraph(d, self.mm).validate()))

    def test_unknown_relationship_kind_rejected(self):
        d = copy.deepcopy(self.a4); d['relationships'][0]['kind'] = 'depends'
        self.assertTrue(any("kind 'depends' is not catalogued" in x for x in LevelGraph(d, self.mm).validate()))

    def test_a2_relationship_must_follow_bian_structure(self):
        d = copy.deepcopy(self.a2); d['relationships'].append({'source': 'SO-044-07', 'kind': 'composition', 'target': 'BD-FRAUD'})
        self.assertTrue(any('does not match the BIAN structure constraints' in x for x in LevelGraph(d, self.mm).validate()))

    def test_dangling_relationship_endpoint(self):
        d = copy.deepcopy(self.a2); d['relationships'].append({'source': 'SD-044', 'kind': 'composition', 'target': 'SG-NOPE'})
        self.assertTrue(any('endpoint not in this model' in x for x in LevelGraph(d, self.mm).validate()))

    def test_duplicate_instance(self):
        d = copy.deepcopy(self.a2); d['instances'].append(copy.deepcopy(d['instances'][0]))
        self.assertTrue(any('duplicate' in x for x in LevelGraph(d, self.mm).validate()))


class FederatedGraphTests(unittest.TestCase):
    def setUp(self):
        self.fg = FederatedGraph.load(FILES)

    def test_check_is_clean(self):
        self.assertEqual({k: v for k, v in self.fg.check().items() if v}, {})

    def test_resolver_uses_is_a(self):
        # mapping says A4.InfrastructureComponent (abstract); level model says A4.SystemSoftware
        self.assertIsNotNone(self.fg.resolve_entity('INF-CLOUD-K8S-PROD', 'A4.InfrastructureComponent', '1.3'))
        self.assertIsNotNone(self.fg.resolve_entity('INF-CLOUD-K8S-PROD', 'A4.SystemSoftware', '1.3'))
        self.assertIsNone(self.fg.resolve_entity('INF-CLOUD-K8S-PROD', 'A4.Node', '1.3'))
        self.assertIsNone(self.fg.resolve_entity('INF-CLOUD-K8S-PROD', 'A4.SystemSoftware', '9.9'))

    def test_legacy_prefix_resolves_through_alias(self):
        self.assertIsNotNone(self.fg.resolve_entity('SD-044', 'L1.ServiceDomain', '1.0'))

    def test_mapping_to_missing_instance_is_reported(self):
        docs = copy.deepcopy(self.fg.mapping_docs); docs[0]['mappings'][0]['target']['id'] = 'SD-NOT-REAL'
        fg = FederatedGraph(list(self.fg.levels.values()), docs, self.fg.mm)
        self.assertTrue(any('SD-NOT-REAL@1.0 not found in level model' in x for x in fg.check()['mappings #1']))

    def test_trace_carries_names_and_concrete_types(self):
        t = self.fg.trace('CAP-310', 'down')
        leaf = t['children'][0]['node']['children'][0]['node']['children'][0]['node']
        self.assertEqual(t['name'], 'Card Fraud Alerts')
        self.assertEqual(leaf['id'], 'INF-CLOUD-K8S-PROD'); self.assertEqual(leaf['concrete_type'], 'A4.SystemSoftware'); self.assertTrue(leaf['resolved'])

    def classes(self, result):
        return {r['id']: r['classification'] for r in result['instances']}

    def test_rehost_touches_a4_and_a3_only(self):
        r = self.fg.impact('INF-CLOUD-K8S-PROD', 'rehost')
        self.assertEqual(self.classes(r), {'INF-CLOUD-K8S-PROD': 'design_change_required', 'APP-FRAUD-ENGINE': 'design_change_required',
                                           'SD-044': 'no_impact', 'CAP-310': 'no_impact', 'PRC-310-01': 'no_impact'})
        self.assertEqual(r['mappings_to_supersede'], ['FRD-005'])

    def test_retire_domain(self):
        c = self.classes(self.fg.impact('SD-044', 'retire'))
        self.assertEqual(c['CAP-310'], 'design_change_required'); self.assertEqual(c['APP-FRAUD-ENGINE'], 'review_required'); self.assertEqual(c['INF-CLOUD-K8S-PROD'], 'no_impact')

    def test_modify_only_reaches_direct_neighbours(self):
        c = self.classes(self.fg.impact('APP-FRAUD-ENGINE', 'modify'))
        self.assertEqual(c, {'APP-FRAUD-ENGINE': 'design_change_required', 'SD-044': 'review_required', 'INF-CLOUD-K8S-PROD': 'review_required', 'DEP-FRAUD-PROD': 'review_required', 'CAP-310': 'no_impact', 'PRC-310-01': 'no_impact'})

    def test_unknown_change_kind(self):
        with self.assertRaises(ValueError):
            self.fg.impact('SD-044', 'explode')

    def test_every_change_kind_has_rules_and_reason(self):
        from sdmm.graph import IMPACT_REASONS
        self.assertEqual(set(IMPACT_RULES), set(IMPACT_REASONS))

    def test_load_rejects_unclassifiable_file(self):
        with self.assertRaises(ValueError):
            FederatedGraph.load([ROOT / 'schema/relationship-types.json'])


if __name__ == '__main__':
    unittest.main()


class V051Tests(unittest.TestCase):
    def test_graph_trace_exits_1_on_empty_trace(self):
        from sdmm.graph import main
        import io, contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['trace', 'INF-ONPREM-VM-CLUSTER-B', '--direction', 'up'] + [str(p) for p in FILES]), 1)
            self.assertEqual(main(['trace', 'CAP-310', '--direction', 'down'] + [str(p) for p in FILES]), 0)

    def test_duplicate_arrow_collapses_to_one_hop(self):
        from sdmm.trace import load_edges, walk
        doc = json.loads((F / 'mappings.json').read_text())
        dup = dict(doc['mappings'][0]); dup = json.loads(json.dumps(dup)); dup['mapping_id'] = 'DUP-1'; dup['status'] = 'proposed'
        edges = load_edges([{'mappings': doc['mappings'] + [dup]}], ('approved', 'proposed'))
        t = walk(edges, 'CAP-310', 'down')
        self.assertEqual(len(t['children']), 1)
        self.assertEqual(t['children'][0]['via'].get('also'), ['DUP-1'])

    def test_strict_does_not_promote_draft_warnings(self):
        from sdmm.validate import main
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main(['--strict', str(F / 'proposals-baseline.json')])
        self.assertEqual(code, 0); self.assertIn('WARNING', buf.getvalue())

    def test_four_bian_constraints_now_encoded(self):
        mm = Metamodel.load()
        for s, k, t in [('A2.ControlRecord', 'composition', 'A2.BehaviorQualifier'), ('A2.ControlRecord', 'association', 'A2.BusinessObject'),
                        ('A2.ServiceOperation', 'access', 'A2.ControlRecord'), ('A2.ServiceDomain', 'flow', 'A2.ServiceDomain')]:
            self.assertIsNone(mm.relationship_issue('A2', s, k, t), (s, k, t))

    def test_enriched_exports_carry_join_keys(self):
        fg = FederatedGraph.load(FILES)
        self.assertEqual({k: v for k, v in fg.check().items() if v}, {})
        app = fg.instance('APP-FRAUD-ENGINE'); self.assertIn('INF-CLOUD-K8S-PROD', app['attributes']['deployed_on'])
        self.assertEqual(fg.instance('DEP-FRAUD-PROD')['attributes']['component_id'], 'APP-FRAUD-ENGINE')
        self.assertEqual(fg.instance('SO-044-07')['attributes']['action_term'], 'Notify')
        self.assertEqual(fg.instance('POST /fraud/alerts')['attributes']['method'], 'POST')


class PaymentInitiationExampleTests(unittest.TestCase):
    P = ROOT / 'examples/payment-initiation'

    def test_exports_and_mappings_check_clean(self):
        fg = FederatedGraph.load(sorted(self.P.glob('a*.json')) + [self.P / 'mappings.json'])
        self.assertEqual({k: v for k, v in fg.check().items() if v}, {})

    def test_given_and_gold_partition_the_union(self):
        u = {m['mapping_id'] for m in json.loads((self.P / 'mappings.json').read_text())['mappings']}
        g = {m['mapping_id'] for m in json.loads((self.P / 'm1-mappings-given.json').read_text())['mappings']}
        d = {m['mapping_id'] for m in json.loads((self.P / 'm1-gold-mappings.json').read_text())['mappings']}
        self.assertEqual(g | d, u); self.assertEqual(g & d, set()); self.assertEqual(len(d), 13)

    def test_planted_mismatch_is_in_the_data(self):
        a3 = json.loads((self.P / 'a3-application.json').read_text())
        api = next(i for i in a3['instances'] if i['id'] == 'API-PI-04'); self.assertEqual(api['attributes']['method'], 'POST')
        a2 = json.loads((self.P / 'a2-service-domain.json').read_text())
        op = next(i for i in a2['instances'] if i['id'] == 'SO-PI-04'); self.assertEqual(op['attributes']['action_term'], 'Retrieve')
