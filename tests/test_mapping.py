import copy, json, unittest
from pathlib import Path
from sdmm.validate import validate, validate_registry, validate_files, load_registry, check_schema, load_schema
from sdmm.reference import StaticReferenceResolver, ReferenceBinding, NullReferenceResolver

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / 'examples/customer-onboarding/mappings.json').read_text())
REGISTRY = load_registry()


def first_issue_matching(data, needle):
    return next((x for x in validate(data) if needle in x), None)


class FixtureTests(unittest.TestCase):
    def test_registry_is_well_formed(self):
        self.assertEqual(validate_registry(REGISTRY), [])

    def test_example_document_is_valid(self):
        self.assertEqual(validate(DATA), [])

    def test_example_covers_every_relationship_type(self):
        used = {(m['source']['type'], m['relationship'], m['target']['type']) for m in DATA['mappings']}
        defined = {(r['source_type'], r['relationship'], r['target_type']) for r in REGISTRY['relationships']}
        self.assertEqual(defined, used)

    def test_example_covers_each_perspective_and_lifecycle_state(self):
        self.assertEqual({m['perspective'] for m in DATA['mappings']}, {'process', 'information', 'architecture'})
        self.assertTrue({'approved', 'superseded', 'proposed', 'needs_review'} <= {m['status'] for m in DATA['mappings']})


class SchemaTests(unittest.TestCase):
    def mutate(self, fn):
        data = copy.deepcopy(DATA)
        fn(data)
        return data

    def test_unknown_field_rejected(self):
        data = self.mutate(lambda d: d['mappings'][0].__setitem__('evidnce', ['x']))
        self.assertIsNotNone(first_issue_matching(data, "unknown property 'evidnce'"))

    def test_bad_type_prefix_rejected(self):
        data = self.mutate(lambda d: d['mappings'][0]['source'].__setitem__('type', 'BusinessCapability'))
        self.assertIsNotNone(first_issue_matching(data, 'does not match pattern'))

    def test_missing_required_field(self):
        data = self.mutate(lambda d: d['mappings'][0].pop('rationale'))
        self.assertIsNotNone(first_issue_matching(data, "missing required property 'rationale'"))

    def test_empty_evidence_rejected(self):
        data = self.mutate(lambda d: d['mappings'][0].__setitem__('evidence', []))
        self.assertIsNotNone(first_issue_matching(data, 'at least 1 item'))

    def test_blank_evidence_entry_rejected(self):
        data = self.mutate(lambda d: d['mappings'][0].__setitem__('evidence', ['  ']))
        self.assertIsNotNone(first_issue_matching(data, 'evidence[0]'))

    def test_invalid_status_rejected(self):
        data = self.mutate(lambda d: d['mappings'][0].__setitem__('status', 'done'))
        self.assertIsNotNone(first_issue_matching(data, 'status: must be one of'))

    def test_confidence_bounds_and_bool(self):
        data = self.mutate(lambda d: d['mappings'][8].__setitem__('confidence', 1.5))
        self.assertIsNotNone(first_issue_matching(data, 'confidence: must be <= 1'))
        data = self.mutate(lambda d: d['mappings'][8].__setitem__('confidence', True))
        self.assertIsNotNone(first_issue_matching(data, 'confidence: expected number'))

    def test_non_list_mappings_does_not_crash(self):
        for bad in ('oops', {'a': 1}, None, 42):
            self.assertTrue(any('mappings' in x for x in validate({'mappings': bad})))
        self.assertTrue(validate([]))
        self.assertTrue(validate({}))

    def test_minimal_schema_engine_handles_refs(self):
        self.assertEqual(check_schema(DATA, load_schema()), [])


class RuleTests(unittest.TestCase):
    def mutate(self, fn):
        data = copy.deepcopy(DATA)
        fn(data)
        return data

    def test_reject_invalid_edge(self):
        data = self.mutate(lambda d: d['mappings'][0]['target'].__setitem__('type', 'A4.InfrastructureComponent'))
        self.assertIsNotNone(first_issue_matching(data, 'not in the registry'))

    def test_duplicate_mapping_id(self):
        data = self.mutate(lambda d: d['mappings'][1].__setitem__('mapping_id', 'MAP-001'))
        self.assertEqual(sum('duplicate mapping_id' in x for x in validate(data)), 2)

    def test_approved_requires_reviewer(self):
        data = self.mutate(lambda d: d['mappings'][0].pop('reviewer_id'))
        self.assertIsNotNone(first_issue_matching(data, 'approved mapping requires reviewer_id'))

    def test_rejected_requires_reviewer(self):
        data = self.mutate(lambda d: d['mappings'][8].__setitem__('status', 'rejected'))
        self.assertIsNotNone(first_issue_matching(data, 'rejected mapping requires reviewer_id'))

    def test_bian_authority_requires_release(self):
        data = self.mutate(lambda d: d['mappings'][0].pop('bian_release'))
        self.assertIsNotNone(first_issue_matching(data, 'requires bian_release'))

    def test_enterprise_rule_does_not_require_release(self):
        data = self.mutate(lambda d: d['mappings'][1].pop('bian_release', None))
        self.assertIsNone(first_issue_matching(data, 'requires bian_release'))

    def test_perspective_must_match_registry(self):
        data = self.mutate(lambda d: d['mappings'][0].__setitem__('perspective', 'process'))
        self.assertIsNotNone(first_issue_matching(data, 'does not match registry'))

    def test_dangling_previous_mapping_id(self):
        data = self.mutate(lambda d: d['mappings'][2].__setitem__('previous_mapping_id', 'MAP-999'))
        self.assertIsNotNone(first_issue_matching(data, "previous_mapping_id 'MAP-999' not found"))

    def test_self_referencing_previous_mapping_id(self):
        data = self.mutate(lambda d: d['mappings'][2].__setitem__('previous_mapping_id', 'MAP-003'))
        self.assertIsNotNone(first_issue_matching(data, 'cannot reference itself'))

    def test_superseded_requires_successor(self):
        data = self.mutate(lambda d: d['mappings'][2].pop('previous_mapping_id'))
        self.assertIsNotNone(first_issue_matching(data, 'superseded mapping has no successor'))

    def test_registry_version_mismatch(self):
        data = self.mutate(lambda d: d.__setitem__('registry_version', '0.0.1'))
        self.assertIsNotNone(first_issue_matching(data, 'does not match loaded registry'))


class RegistryRuleTests(unittest.TestCase):
    def mutate(self, fn):
        reg = copy.deepcopy(REGISTRY)
        fn(reg)
        return reg

    def test_duplicate_edge(self):
        reg = self.mutate(lambda r: r['relationships'].append(copy.deepcopy(r['relationships'][0]) | {'mapping_type_id': 'X'}))
        self.assertTrue(any('duplicate edge' in x for x in validate_registry(reg)))

    def test_non_adjacent_layers(self):
        reg = self.mutate(lambda r: r['relationships'][0].__setitem__('target_type', 'A4.InfrastructureComponent'))
        self.assertTrue(any('A(n) to A(n+1)' in x for x in validate_registry(reg)))

    def test_same_layer_rejected(self):
        reg = self.mutate(lambda r: r['relationships'][0].__setitem__('target_type', 'A1.ValueStream'))
        self.assertTrue(any('A(n) to A(n+1)' in x for x in validate_registry(reg)))

    def test_unknown_authority(self):
        reg = self.mutate(lambda r: r['relationships'][0].__setitem__('authority', 'BIAN_DEFINITION'))
        self.assertTrue(any('authority must be one of' in x for x in validate_registry(reg)))

    def test_missing_rule_metadata(self):
        reg = self.mutate(lambda r: r['relationships'][0].pop('owner'))
        self.assertTrue(any('missing owner' in x for x in validate_registry(reg)))


class ReferenceResolverTests(unittest.TestCase):
    def test_resolver_flags_unknown_canonical_id(self):
        resolver = StaticReferenceResolver([ReferenceBinding('DEMO-BIAN-SD-ONBOARDING', 'DEMO-RELEASE', 'ServiceDomain')])
        issues = validate(DATA, resolver=resolver)
        self.assertTrue(any("'DEMO-BIAN-SCENARIO-ONBOARD' not found" in x for x in issues))
        self.assertFalse(any("'DEMO-BIAN-SD-ONBOARDING' not found" in x for x in issues))

    def test_null_resolver_resolves_nothing(self):
        self.assertTrue(any('not found in BIAN release' in x for x in validate(DATA, resolver=NullReferenceResolver())))

    def test_no_resolver_skips_reference_checks(self):
        self.assertEqual(validate(DATA), [])


class MultiFileTests(unittest.TestCase):
    def test_all_shipped_examples_validate_together(self):
        report = validate_files(sorted((ROOT / 'examples').glob('*/mappings.json')))
        self.assertGreaterEqual(len(report), 2)
        self.assertEqual({k: v for k, v in report.items() if v}, {})


    def test_cross_file_duplicate_ids(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / 'a.json', Path(tmp) / 'b.json'
            a.write_text(json.dumps(DATA)); b.write_text(json.dumps(DATA))
            report = validate_files([a, b])
            self.assertEqual(report[str(a)], [])
            self.assertTrue(any('also defined in' in x for x in report[str(b)]))

    def test_unreadable_file_reported_not_raised(self):
        report = validate_files(['/nonexistent/mappings.json'])
        self.assertTrue(report['/nonexistent/mappings.json'][0].startswith('cannot read'))


if __name__ == '__main__':
    unittest.main()


class V021RuleTests(unittest.TestCase):
    """Validator hardening: approval timestamp, canonical anchoring, typed evidence, entity resolution."""
    def mutate(self, fn):
        data = copy.deepcopy(DATA)
        fn(data)
        return data

    def test_reviewed_statuses_require_approved_at(self):
        for idx, status in ((0, 'approved'), (7, 'superseded')):
            data = self.mutate(lambda d: d['mappings'][idx].pop('approved_at'))
            self.assertIsNotNone(first_issue_matching(data, f'{status} mapping requires approved_at'))

    def test_bian_mapping_requires_canonical_id_on_l1_endpoint(self):
        data = self.mutate(lambda d: d['mappings'][0]['target'].pop('canonical_id'))
        self.assertIsNotNone(first_issue_matching(data, 'requires canonical_id on its A2 target'))

    def test_enterprise_mapping_does_not_require_canonical_id(self):
        self.assertIsNone(first_issue_matching(DATA, 'requires canonical_id'))

    def test_unanchored_fake_domain_is_rejected(self):
        # the reviewer's SD-NOT-REAL case: bian-guided, no canonical_id, no resolver
        data = self.mutate(lambda d: (d['mappings'][0]['target'].__setitem__('id', 'SD-NOT-REAL'),
                                      d['mappings'][0]['target'].pop('canonical_id')))
        self.assertIsNotNone(first_issue_matching(data, 'requires canonical_id'))

    def test_typed_evidence_missing_required_kind(self):
        data = self.mutate(lambda d: d['mappings'][0].__setitem__('evidence', ['business_architecture_document:X']))
        self.assertIsNotNone(first_issue_matching(data, "missing required kind(s) ['domain_scope_assessment']"))

    def test_untyped_evidence_is_a_warning_not_an_error(self):
        data = self.mutate(lambda d: d['mappings'][0].__setitem__('evidence', ['SOME-DOC']))
        warnings = []
        self.assertEqual([x for x in validate(data, warnings=warnings) if 'evidence' in x], [])
        self.assertTrue(any('evidence is untyped' in w for w in warnings))

    def test_example_evidence_is_fully_typed(self):
        warnings = []
        self.assertEqual(validate(DATA, warnings=warnings), [])
        self.assertEqual(warnings, [])

    def test_entity_resolver_flags_unknown_endpoint(self):
        from sdmm.reference import CatalogueEntityResolver
        fraud = ROOT / 'examples/card-fraud-alerts'
        doc = json.loads((fraud / 'mappings.json').read_text())
        resolver = CatalogueEntityResolver.from_file(fraud / 'entities.json')
        self.assertEqual(validate(doc, entity_resolver=resolver), [])
        doc['mappings'][0]['target']['id'] = 'SD-NOT-REAL'
        doc['mappings'][0]['target']['canonical_id'] = 'X'
        self.assertTrue(any('SD-NOT-REAL@1.0 not found in level model' in x for x in validate(doc, entity_resolver=resolver)))


class DiffTests(unittest.TestCase):
    def setUp(self):
        from sdmm.diff import diff
        self.diff = diff
        self.old = copy.deepcopy(DATA)

    def changed(self, fn):
        new = copy.deepcopy(self.old)
        fn(new)
        return self.diff(self.old, new)

    def test_identical_documents_are_clean(self):
        self.assertEqual(self.diff(self.old, copy.deepcopy(self.old)), [])

    def test_removed_record_is_flagged(self):
        self.assertTrue(any('record removed' in x for x in self.changed(lambda d: d['mappings'].pop(0))))

    def test_editing_approved_record_is_flagged(self):
        issues = self.changed(lambda d: d['mappings'][0].__setitem__('rationale', 'edited after approval'))
        self.assertTrue(any("approved record is immutable" in x and "['rationale']" in x for x in issues))

    def test_approved_to_superseded_with_valid_to_is_allowed(self):
        def fn(d):
            d['mappings'][0]['status'] = 'superseded'; d['mappings'][0]['valid_to'] = '2026-12-31'
        self.assertEqual(self.changed(fn), [])

    def test_approved_back_to_proposed_is_illegal(self):
        issues = self.changed(lambda d: d['mappings'][0].__setitem__('status', 'proposed'))
        self.assertTrue(any("'approved' -> 'proposed' is not permitted" in x for x in issues))

    def test_proposed_to_approved_is_allowed(self):
        def fn(d):
            m = d['mappings'][8]; m['status'] = 'approved'; m['reviewer_id'] = 'r'; m['approved_at'] = '2026-10-22'
        self.assertEqual(self.changed(fn), [])

    def test_rejected_is_terminal(self):
        self.old['mappings'][8]['status'] = 'rejected'
        issues = self.changed(lambda d: d['mappings'][8].__setitem__('status', 'proposed'))
        self.assertTrue(any("'rejected' -> 'proposed' is not permitted" in x for x in issues))

    def test_retyping_evidence_on_approved_record_is_allowed(self):
        self.old['mappings'][0]['evidence'] = ['SYNTHETIC-BA-001']
        issues = self.changed(lambda d: d['mappings'][0].__setitem__('evidence', ['business_architecture_document:SYNTHETIC-BA-001', 'domain_scope_assessment:SYNTHETIC-BA-001']))
        self.assertEqual(issues, [])

    def test_changing_evidence_artefact_on_approved_record_is_flagged(self):
        issues = self.changed(lambda d: d['mappings'][0].__setitem__('evidence', ['business_architecture_document:OTHER-DOC']))
        self.assertTrue(any("['evidence']" in x for x in issues))

    def test_new_record_is_fine(self):
        self.assertEqual(self.changed(lambda d: d['mappings'].append(copy.deepcopy(d['mappings'][8]) | {'mapping_id': 'NEW-1'})), [])


class TraceTests(unittest.TestCase):
    def setUp(self):
        from sdmm.trace import load_edges, walk, paths
        self.load_edges, self.walk, self.paths = load_edges, walk, paths
        self.fraud = json.loads((ROOT / 'examples/card-fraud-alerts/mappings.json').read_text())
        self.edges = load_edges([self.fraud])

    def chain(self, tree):
        return [i for i, _ in self.paths(tree)[0]]

    def test_only_approved_edges_by_default(self):
        self.assertEqual(sorted(e['mapping_id'] for e in self.edges), ['FRD-001', 'FRD-002', 'FRD-005'])

    def test_downstream_reaches_new_host_not_old(self):
        chain = self.chain(self.walk(self.edges, 'CAP-310', 'down'))
        self.assertEqual(chain, ['CAP-310', 'SD-044', 'APP-FRAUD-ENGINE', 'INF-CLOUD-K8S-PROD'])
        self.assertNotIn('INF-ONPREM-VM-CLUSTER-B', chain)

    def test_upstream_from_new_host_reaches_capability(self):
        self.assertEqual(self.chain(self.walk(self.edges, 'INF-CLOUD-K8S-PROD', 'up')),
                         ['INF-CLOUD-K8S-PROD', 'APP-FRAUD-ENGINE', 'SD-044', 'CAP-310'])

    def test_old_host_has_no_upstream_when_only_superseded_edge_points_there(self):
        self.assertEqual(self.walk(self.edges, 'INF-ONPREM-VM-CLUSTER-B', 'up')['children'], [])

    def test_including_superseded_restores_history(self):
        edges = self.load_edges([self.fraud], ('approved', 'superseded'))
        self.assertEqual(self.chain(self.walk(edges, 'INF-ONPREM-VM-CLUSTER-B', 'up'))[-1], 'CAP-310')

    def test_every_hop_carries_provenance(self):
        for p in self.paths(self.walk(self.edges, 'CAP-310', 'down')):
            self.assertTrue(all(v['mapping_id'] for _, v in p[1:]))

    def test_cycle_is_cut(self):
        edges = self.edges + [{'mapping_id': 'LOOP', 'relationship': 'X', 'status': 'approved', 'baseline_id': 'b',
                               'source': {'id': 'INF-CLOUD-K8S-PROD', 'type': 'A4.X', 'version': '1'},
                               'target': {'id': 'CAP-310', 'type': 'A1.X', 'version': '1'}}]
        self.assertEqual(self.chain(self.walk(edges, 'CAP-310', 'down')), ['CAP-310', 'SD-044', 'APP-FRAUD-ENGINE', 'INF-CLOUD-K8S-PROD'])

    def test_cli_unknown_entity_exit_code(self):
        from sdmm.trace import main
        import io, contextlib
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(['NOPE', str(ROOT / 'examples/card-fraud-alerts/mappings.json')]), 1)


class LevelAliasTests(unittest.TestCase):
    """v0.3.1: L0-L3 prefixes are aliases of A1-A4; old documents validate and a rename is not an edit."""
    def legacy(self):
        import re
        data = copy.deepcopy(DATA)
        down = lambda t: re.sub(r'^A([1-4])\.', lambda m: f'L{int(m.group(1))-1}.', t)
        for m in data['mappings']:
            for end in ('source', 'target'):
                m[end]['type'] = down(m[end]['type'])
        return data

    def test_registry_declares_levels_and_aliases(self):
        self.assertEqual([lv['code'] for lv in REGISTRY['levels']], ['A1', 'A2', 'A3', 'A4'])
        self.assertEqual(REGISTRY['type_aliases']['L1.'], 'A2.')

    def test_legacy_prefixed_document_validates(self):
        self.assertEqual(validate(self.legacy()), [])

    def test_alias_rename_is_not_an_immutable_edit(self):
        from sdmm.diff import diff
        self.assertEqual(diff(self.legacy(), DATA), [])

    def test_unknown_prefix_rejected(self):
        data = copy.deepcopy(DATA)
        data['mappings'][0]['source']['type'] = 'X9.BusinessCapability'
        self.assertTrue(any('does not match pattern' in x for x in validate(data)))
