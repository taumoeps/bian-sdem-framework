"""Use-case example 1 (docs/use-case-example-1.md): the rulebook tests re-run on every change."""
import sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))


class UseCaseExample1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from use_case_example_1 import run
        cls.R = run()

    def test_every_rulebook_test_passes(self):
        for x in self.R['tests']: self.assertTrue(x['pass'], f"{x['area']}: {x['data']} — should {x['should']}, did {x['did']}")

    def test_all_links_found_and_correct(self):
        self.assertEqual(len(self.R['links']), 18); self.assertTrue(all(l['correct'] for l in self.R['links']))

    def test_trace_reaches_top_and_bottom(self):
        self.assertIn('CAP-PAY-010', {n for _, _, n in self.R['trace']['up']})
        self.assertIn('INF-K8S-PAY-PROD', {n for _, _, n in self.R['trace']['down']})


if __name__ == '__main__':
    unittest.main()
