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
        data = self.mutate(lambda d: d['mappings'][0]['target'].__setitem__('type', 'L3.InfrastructureComponent'))
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
        reg = self.mutate(lambda r: r['relationships'][0].__setitem__('target_type', 'L3.InfrastructureComponent'))
        self.assertTrue(any('L(n) to L(n+1)' in x for x in validate_registry(reg)))

    def test_same_layer_rejected(self):
        reg = self.mutate(lambda r: r['relationships'][0].__setitem__('target_type', 'L0.ValueStream'))
        self.assertTrue(any('L(n) to L(n+1)' in x for x in validate_registry(reg)))

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
