import copy, json, unittest
from pathlib import Path
from sdmm.graph import FederatedGraph, load_impact_rules, IMPACT_RULES
from sdmm.engine import NameOverlapBaseline, proposal
from sdmm.evaluate import evaluate
from sdmm.validate import validate

ROOT = Path(__file__).resolve().parents[1]
F = ROOT / 'examples/card-fraud-alerts'
LEVELS = sorted(F.glob('a*.json'))
GOLD = json.loads((F / 'mappings.json').read_text())


class EngineInterfaceTests(unittest.TestCase):
    def setUp(self):
        self.graph = FederatedGraph.load(LEVELS)
        self.props = NameOverlapBaseline().propose(self.graph)

    def test_baseline_emits_only_proposed_records_that_validate(self):
        self.assertTrue(self.props)
        self.assertTrue(all(m['status'] == 'proposed' for m in self.props))
        warnings = []
        self.assertEqual(validate({'mappings': self.props}, warnings=warnings), [])

    def test_proposals_cite_engine_rationale_and_confidence(self):
        for m in self.props:
            self.assertTrue(m['evidence'][0].startswith('engine_rationale:'))
            self.assertTrue(0 <= m['confidence'] <= 1)
            self.assertEqual(m['created_by'], NameOverlapBaseline.name)

    def test_engine_never_invents_instances(self):
        ids = {i['id'] for g in self.graph.levels.values() for i in g.doc['instances']}
        for m in self.props:
            self.assertIn(m['source']['id'], ids); self.assertIn(m['target']['id'], ids)

    def test_proposal_missing_required_evidence_is_a_warning_not_an_error(self):
        doc = {'mappings': [proposal('P1', {'id': 'CAP-310', 'type': 'A1.BusinessCapability', 'version': '1.0'}, 'SUPPORTED_BY',
                                     {'id': 'SD-044', 'type': 'A2.ServiceDomain', 'version': '1.0', 'canonical_id': 'X'}, 0.5, 'test', 'eng')]}
        doc['mappings'][0]['bian_release'] = 'R'
        warnings = []
        issues = validate(doc, warnings=warnings)
        self.assertEqual([x for x in issues if 'evidence' in x], [])
        self.assertTrue(any('proposal lacks required evidence' in w for w in warnings))


class EvaluationTests(unittest.TestCase):
    def test_baseline_scores_as_expected_on_fraud_example(self):
        props = {'mappings': NameOverlapBaseline().propose(FederatedGraph.load(LEVELS))}
        r = evaluate([GOLD], [props])
        self.assertEqual((r['overall']['tp'], r['overall']['fp'], r['overall']['fn']), (4, 2, 1))
        self.assertEqual(r['missed'], [['APP-FRAUD-ENGINE', 'DEPLOYED_ON', 'INF-CLOUD-K8S-PROD']])

    def test_perfect_proposals_score_one(self):
        props = copy.deepcopy(GOLD)
        for m in props['mappings']:
            m['status'] = 'proposed' if m['status'] == 'approved' else 'rejected'
        r = evaluate([GOLD], [props])
        self.assertEqual(r['overall']['f1'], 1.0); self.assertEqual(r['missed'], []); self.assertEqual(r['false_proposals'], [])

    def test_only_approved_records_form_the_gold_set(self):
        r = evaluate([GOLD], [{'mappings': []}])
        self.assertEqual(r['overall']['gold'], 5)   # FRD-003 superseded and FRD-004 proposed are not gold

    def test_empty_proposals_zero_recall(self):
        r = evaluate([GOLD], [{'mappings': []}])
        self.assertEqual(r['overall']['recall'], 0.0)


class ImpactRulesAsDataTests(unittest.TestCase):
    def test_rules_loaded_from_schema_file(self):
        doc = load_impact_rules()
        self.assertEqual(set(doc['kinds']), set(IMPACT_RULES))
        self.assertEqual(doc['kinds']['rehost']['rules'], {'self': 'design_change_required', 'up1': 'design_change_required'})

    def test_unknown_class_in_rules_file_rejected(self):
        import tempfile
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
            json.dump({'$schema_version': 'x', 'classes': ['no_impact'], 'kinds': {'k': {'reason': '', 'rules': {'self': 'explode'}}}}, f)
        with self.assertRaises(ValueError):
            load_impact_rules(f.name)


class LevelDescriptionTests(unittest.TestCase):
    def test_shipped_levels_carry_descriptions(self):
        for p in LEVELS:
            for i in json.loads(p.read_text())['instances']:
                self.assertTrue(i.get('description'), f"{p.name}:{i['id']}")


if __name__ == '__main__':
    unittest.main()
