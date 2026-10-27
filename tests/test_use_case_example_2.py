"""Use-case example 2 (docs/use-case-example-2.md): AID re-run on every change.
Every run must meet the expectations sealed before any run (commit 17dbd33), and every safety test (CTL-16, CTL-17) must pass."""
import sys, unittest
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

if __name__ == '__main__':
    unittest.main()
