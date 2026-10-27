"""Use-case example 2 (docs/use-case-example-2.md): AID baseline re-run on every change.
Run 1 must meet its sealed expectations; runs 2–5 and CTL-16/17 are not built yet — update this test as they are built."""
import sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))


class UseCaseExample2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from use_case_example_2 import run
        cls.R = run()

    def test_run1_meets_sealed_expectations(self):
        for check, ok in self.R['runs'][0]['checks']: self.assertTrue(ok, check)

    def test_not_built_parts_are_reported_not_hidden(self):
        self.assertEqual([r['status'] for r in self.R['runs'][1:]], ['not built'] * 4)
        self.assertEqual({s['status'] for s in self.R['safety']}, {'not built'})


if __name__ == '__main__':
    unittest.main()
