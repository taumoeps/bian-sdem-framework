import re
import copy, json, unittest
from pathlib import Path
from sdem.graph import LevelGraph, FederatedGraph, IMPACT_RULES
from sdem.metamodel import Metamodel

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
        from sdem.graph import IMPACT_REASONS
        self.assertEqual(set(IMPACT_RULES), set(IMPACT_REASONS))

    def test_load_rejects_unclassifiable_file(self):
        with self.assertRaises(ValueError):
            FederatedGraph.load([ROOT / 'schema/relationship-types.json'])


if __name__ == '__main__':
    unittest.main()


class V051Tests(unittest.TestCase):
    def test_graph_trace_exits_1_on_empty_trace(self):
        from sdem.graph import main
        import io, contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['trace', 'INF-ONPREM-VM-CLUSTER-B', '--direction', 'up'] + [str(p) for p in FILES]), 1)
            self.assertEqual(main(['trace', 'CAP-310', '--direction', 'down'] + [str(p) for p in FILES]), 0)

    def test_duplicate_arrow_collapses_to_one_hop(self):
        from sdem.trace import load_edges, walk
        doc = json.loads((F / 'mappings.json').read_text())
        dup = dict(doc['mappings'][0]); dup = json.loads(json.dumps(dup)); dup['mapping_id'] = 'DUP-1'; dup['status'] = 'proposed'
        edges = load_edges([{'mappings': doc['mappings'] + [dup]}], ('approved', 'proposed'))
        t = walk(edges, 'CAP-310', 'down')
        self.assertEqual(len(t['children']), 1)
        self.assertEqual(t['children'][0]['via'].get('also'), ['DUP-1'])

    def test_strict_does_not_promote_draft_warnings(self):
        from sdem.validate import main
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


class LegacyLedgerExampleTests(unittest.TestCase):
    P = ROOT / 'examples/legacy-core-ledger'

    def test_exports_and_mappings_check_clean(self):
        fg = FederatedGraph.load(sorted(self.P.glob('a*.json')) + [self.P / 'mappings.json'])
        self.assertEqual({k: v for k, v in fg.check().items() if v}, {})

    def test_given_is_empty_and_gold_is_the_union(self):
        u = {m['mapping_id'] for m in json.loads((self.P / 'mappings.json').read_text())['mappings']}
        g = json.loads((self.P / 'h1-mappings-given.json').read_text())['mappings']
        d = {m['mapping_id'] for m in json.loads((self.P / 'h1-gold-mappings.json').read_text())['mappings']}
        self.assertEqual(g, []); self.assertEqual(d, u); self.assertEqual(len(d), 28)

    def test_all_soap_operations_are_post_and_batch_jobs_are_not_http(self):
        a3 = json.loads((self.P / 'a3-application.json').read_text())
        ops = [i for i in a3['instances'] if i['type'] == 'A3.APIOperation']
        self.assertEqual({i['attributes']['method'] for i in ops if i['id'].startswith('OP-')}, {'POST'})
        self.assertEqual({i['attributes']['method'] for i in ops if i['id'].startswith('JOB-')}, {'BATCH'})


class FollowCompositionTests(unittest.TestCase):
    P = ROOT / 'examples/legacy-core-ledger'

    def test_trace_continues_from_module_to_whole_to_platform(self):
        fg = FederatedGraph.load(sorted(self.P.glob('a*.json')) + [self.P / 'mappings.json'])
        plain = fg.trace('CAP-ACCT-SVC', 'down')
        leaf = plain['children'][0]['node']['children'][0]['node']
        self.assertEqual(leaf['id'], 'LM-ACCT'); self.assertEqual(leaf['children'], [])
        full = fg.trace('CAP-ACCT-SVC', 'down', follow_composition=True)
        mod = full['children'][0]['node']['children'][0]['node']
        whole = mod['children'][0]
        self.assertEqual(whole['via']['relationship'], 'PART_OF'); self.assertEqual(whole['node']['id'], 'APP-LEDGER')
        self.assertEqual({c['node']['id'] for c in whole['node']['children']}, {'INF-MF-LPAR-PROD', 'DEP-LM-PROD'})

    def test_upstream_from_platform_descends_into_modules(self):
        fg = FederatedGraph.load(sorted(self.P.glob('a*.json')) + [self.P / 'mappings.json'])
        t = fg.trace('INF-MF-LPAR-PROD', 'up', follow_composition=True)
        ledger = t['children'][0]['node']
        kinds = {c['via']['relationship'] for c in ledger['children']}
        self.assertIn('COMPOSES', kinds)
        modules = {c['node']['id'] for c in ledger['children'] if c['via']['relationship'] == 'COMPOSES'}
        self.assertIn('LM-ACCT', modules)


class AcquiredFintechExampleTests(unittest.TestCase):
    P = ROOT / 'examples/acquired-fintech'

    def test_three_level_export_checks_clean_without_a1(self):
        files = sorted(self.P.glob('a*.json'))
        self.assertEqual([f.name[:2] for f in files], ['a2', 'a3', 'a4'])
        fg = FederatedGraph.load(files + [self.P / 'mappings.json'])
        self.assertEqual({k: v for k, v in fg.check().items() if v}, {})

    def test_gold_is_the_union_and_given_is_empty(self):
        u = {m['mapping_id'] for m in json.loads((self.P / 'mappings.json').read_text())['mappings']}
        d = {m['mapping_id'] for m in json.loads((self.P / 'h2-gold-mappings.json').read_text())['mappings']}
        self.assertEqual(json.loads((self.P / 'h2-mappings-given.json').read_text())['mappings'], [])
        self.assertEqual(d, u); self.assertEqual(len(d), 41)

    def test_run2_aliases_savings_decoded_fraud_not(self):
        a2 = json.loads((self.P / 'a2-service-domain.json').read_text())
        at = {i['id']: i.get('attributes', {}).get('aliases') for i in a2['instances'] if i['type'] == 'A2.AssetType'}
        self.assertIn('vault', at['AT-SA']); self.assertIsNone(at['AT-FD']); self.assertIn('zap', at['AT-PE'])
        a3 = json.loads((self.P / 'a3-application.json').read_text())
        zap = next(i for i in a3['instances'] if i['id'] == 'IFC-zap')
        self.assertEqual(zap['attributes']['field_aliases']['sender'], 'debtor_account_reference')


class CustomerOnboardingExampleTests(unittest.TestCase):
    P = ROOT / 'examples/customer-onboarding'

    def _fg(self):
        return FederatedGraph.load(sorted(self.P.glob('a*.json')) + [self.P / 'mappings.json'])

    def test_exports_cover_every_mapped_id(self):
        self.assertEqual({k: v for k, v in self._fg().check().items() if v}, {})

    def test_e2_1_two_a4_arrows_from_the_component(self):
        t = self._fg().trace('CAP-001', 'down')
        app = t['children'][0]['node']['children'][0]['node']
        self.assertEqual(app['id'], 'APP-001')
        self.assertEqual({c['node']['id'] for c in app['children']}, {'INF-001', 'DEP-001'})

    def test_e2_4_upstream_from_entity_is_information_only(self):
        t = self._fg().trace('ENT-001', 'up')
        ids = set(); stack = [t]
        while stack:
            n = stack.pop(); ids.add(n['id']); stack += [c['node'] for c in n['children']]
        self.assertEqual(ids, {'ENT-001', 'BBO-001', 'BO-001'})

    def test_e2_5_replace_component(self):
        rows = {r['id']: r['classification'] for r in self._fg().impact('APP-001', 'replace')['instances']}
        self.assertEqual(rows['SD-001'], 'design_change_required')
        self.assertEqual(rows['INF-001'], 'review_required'); self.assertEqual(rows['DEP-001'], 'review_required')
        self.assertNotIn('BBO-001', rows); self.assertNotIn('ENT-001', rows)


class DigitalLendingExampleTests(unittest.TestCase):
    P = ROOT / 'examples/digital-lending'

    def test_two_level_export_checks_clean(self):
        files = sorted(self.P.glob('a*.json'))
        self.assertEqual([f.name[:2] for f in files], ['a1', 'a2'])
        fg = FederatedGraph.load(files + [self.P / 'mappings.json'])
        self.assertEqual({k: v for k, v in fg.check().items() if v}, {})

    def test_design_gold_uses_the_dsn_convention_and_names_no_platform(self):
        g = json.loads((self.P / 'm2-gold-design.json').read_text())['mappings']
        self.assertEqual(len(g), 12)
        self.assertTrue(all(m['target']['id'].startswith('DSN-') for m in g))
        self.assertNotIn('DEPLOYED_ON', {m['relationship'] for m in g}); self.assertNotIn('MAPPED_TO', {m['relationship'] for m in g})
        self.assertTrue(all(m['rationale'].startswith('TARGET DESIGN') and m['confidence'] <= 0.4 for m in g))


class DesignTraceMarkerTests(unittest.TestCase):
    P = ROOT / 'examples/digital-lending'

    def test_trace_marks_planned_instances(self):
        from sdem.graph import render_trace
        files = sorted(self.P.glob('a*.json')) + sorted(self.P.glob('m2-design-a*.json')) + [self.P / 'mappings.json', self.P / 'm2-proposals.json']
        fg = FederatedGraph.load(files)
        out = render_trace(fg.trace('CAP-LEND', 'down', ('approved', 'proposed')), 'down')
        self.assertIn('DSN-APP-SD-LO', out); self.assertIn('[DESIGN — planned, not observed]', out)
        self.assertNotIn('DESIGN', render_trace(fg.trace('CAP-LEND', 'down'), 'down'))


class TradeFinanceCoverageTests(unittest.TestCase):
    P = ROOT / 'examples/trade-finance'

    def test_exports_and_registry_mappings_check_clean(self):
        fg = FederatedGraph.load(sorted(self.P.glob('a*.json')) + [self.P / 'mappings.json'])
        self.assertEqual({k: v for k, v in fg.check().items() if v}, {})

    def test_cases_partition_the_registry_and_candidate_gold(self):
        reg = {m['mapping_id'] for m in json.loads((self.P / 'mappings.json').read_text())['mappings']}
        cand = json.loads((self.P / 'candidates.json').read_text())['mappings']
        covered = set()
        for uc in ('c1', 'c2', 'c3'):
            g = {m['mapping_id'] for m in json.loads((self.P / f'{uc}-mappings-given.json').read_text())['mappings']}
            d = {m['mapping_id'] for m in json.loads((self.P / f'{uc}-gold-mappings.json').read_text())['mappings']}
            self.assertEqual(g | d, reg); self.assertEqual(g & d, set())
            covered |= {m['relationship'] for m in json.loads((self.P / f'{uc}-gold-candidates.json').read_text())['mappings']}
        self.assertEqual(covered, {m['relationship'] for m in cand})
        self.assertEqual(len(covered), 39)

    def test_every_previously_untested_plan_row_has_gold(self):
        untested = set("S03 S07 S08 S09 S13 S14 S15 S16 S18 S19 S21 S26 S27 S28 S29 S31 S34 S35 S37 S38 S39 S42 S43 S44 S46 S48 S51 S52 S53 S54".split())
        cand = {m['relationship'] for m in json.loads((self.P / 'candidates.json').read_text())['mappings']}
        reg = {re.match(r'\[(S\d+)\]', m['rationale']).group(1) for m in json.loads((self.P / 'mappings.json').read_text())['mappings']}
        self.assertEqual(untested - (cand | reg), set())


class WithinLevelConstraintTests(unittest.TestCase):
    def test_every_level_has_a_constraint_set(self):
        from sdem.metamodel import Metamodel
        mm = Metamodel.load()
        levels = {c['level'] for c in mm.relationships['constraints']}
        self.assertEqual(levels, {'A1', 'A2', 'A3', 'A4'})

    def test_archimate_kind_is_enforced_and_association_is_generic(self):
        from sdem.metamodel import Metamodel
        mm = Metamodel.load()
        self.assertIsNone(mm.relationship_issue('A3', 'A3.ApplicationComponent', 'assignment', 'A3.ApplicationFunction'))
        self.assertIsNotNone(mm.relationship_issue('A3', 'A3.ApplicationComponent', 'composition', 'A3.ApplicationFunction'))
        self.assertIsNone(mm.relationship_issue('A3', 'A3.ApplicationComponent', 'association', 'A3.Event'))
        self.assertIsNone(mm.relationship_issue('A1', 'A1.BusinessCapability', 'serving', 'A1.ValueStream'))
        self.assertIsNotNone(mm.relationship_issue('A1', 'A1.ValueStream', 'realization', 'A1.BusinessCapability'))
        self.assertIsNone(mm.relationship_issue('A4', 'A4.Node', 'assignment', 'A4.Artifact'))


class ReferenceStructureTests(unittest.TestCase):
    """Every enforceable within-level row is exercised on committed data and accepted by the checker."""
    P = ROOT / 'examples/reference-structure'

    def test_generated_estate_is_current(self):
        from sdem.structure import render, FILES
        docs = render()
        for lvl, name in FILES.items():
            self.assertEqual(json.loads((self.P / name).read_text(encoding='utf-8')), docs[lvl])

    def test_every_enforceable_row_occurs_and_checks_clean(self):
        fg = FederatedGraph.load(sorted(self.P.glob('a*.json')) + [self.P / 'mappings.json'])
        self.assertEqual({k: v for k, v in fg.check().items() if v}, {})
        lr = json.loads((ROOT / 'metamodel/level-relationships.json').read_text(encoding='utf-8'))
        enforceable = {c['id'] for c in lr['constraints'] if c.get('enforceable') is not False}
        present = {r['name'] for f in self.P.glob('a*.json') for r in json.loads(f.read_text(encoding='utf-8'))['relationships']}
        self.assertEqual(enforceable - present, set())
        self.assertEqual(len(enforceable), 129)
