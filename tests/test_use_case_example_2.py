"""Use-case example 2 (docs/evidence/use-case-example-2.md): AID re-run on every change.
Every run must meet the expectations sealed before any run (commit 17dbd33), and every safety test (CTL-16, CTL-17) must pass."""
import json, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))


class UseCaseExample2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from use_case_example_2 import run
        cls.R = run()

    def test_every_run_meets_its_sealed_expectations(self):
        self.assertEqual([r['run'] for r in self.R['runs']], [1, 2, 3, 4, 5])
        for r in self.R['runs']:
            self.assertTrue(r['checks'], f"run {r['run']} has no checks")
            for check, ok in r['checks']: self.assertTrue(ok, f"run {r['run']}: {check}")

    def test_safety_controls_hold_with_good_and_bad_data(self):
        self.assertEqual({s['control'] for s in self.R['safety']}, {'CTL-16', 'CTL-17'})
        self.assertEqual({s['data'] for s in self.R['safety']}, {'good', 'bad'})
        for s in self.R['safety']: self.assertTrue(s['pass'], f"{s['control']} {s['test']}: should be {s['should']}, was {s['did']}")


    def test_aid_refuses_inputs_that_fail_the_dataset_check(self):
        import copy, json
        from sdem import aid
        a1 = json.loads((ROOT / 'examples' / 'payment-initiation' / 'a1-business.json').read_text(encoding='utf-8'))
        with self.assertRaises(ValueError): aid.project({})
        bad = copy.deepcopy(a1); bad['instances'].append({'id': 'PRJ-CAP-X', 'type': 'A1.BusinessCapability', 'version': '1.0', 'name': 'x'})
        with self.assertRaisesRegex(ValueError, 'CTL-16'): aid.project({'A1': bad})

    def test_projection_schema_rejects_a_bad_package(self):
        import copy, json
        from sdem import aid
        from sdem.validate import check_schema
        sys.path.insert(0, str(ROOT / 'scripts'))
        from use_case_example_2 import catalogue, LEVELS, EST
        a1 = json.loads((EST / LEVELS['A1']).read_text(encoding='utf-8'))
        pkg = aid.project({'A1': a1}, catalogue(), created_at='2026-10-28T00:00:00+00:00')
        schema = json.loads(aid.SCHEMA.read_text(encoding='utf-8'))
        self.assertEqual(check_schema(pkg, schema), [])
        bad = copy.deepcopy(pkg); bad['links']['links'][0]['status'] = 'approved'; bad['layers']['A3']['instances'][0]['projection'].pop('source_reference')
        issues = check_schema(bad, schema)
        self.assertTrue(any('status' in i for i in issues) and any('source_reference' in i for i in issues), issues)

    def test_view_and_trace_label_projections(self):
        import re
        html = self.R['views']['run2-view.html']
        data = json.loads(re.search(r'const D=(\{.*?\});const NS', html, re.S).group(1).replace('<\\/', '</'))
        self.assertTrue(any(n.get('prj') for n in data['nodes']) and any(e['scope'] == 'p' for e in data['edges']))
        self.assertTrue(all(not n.get('prj') for n in data['nodes'] if n['lvl'] == 'A1'))  # the architect's real layer is never marked projected

if __name__ == '__main__':
    unittest.main()
