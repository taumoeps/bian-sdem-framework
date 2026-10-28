"""Use-case example 1 (docs/evidence/use-case-example-1.md): the rulebook tests re-run on every change."""
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


    def test_every_cited_control_is_registered_and_every_rule_area_is_covered(self):
        import json
        reg = json.loads((ROOT / 'metamodel' / 'controls.json').read_text(encoding='utf-8'))
        ids = {c['id'] for c in reg['controls']}
        for x in self.R['tests']:
            for c in [c.strip() for c in x['controls'].split(',') if c.strip().startswith('CTL-')]: self.assertIn(c, ids, x['data'])
        areas = {c['rule_area'].split(' ')[0] for c in reg['controls']}
        for n in '1234567': self.assertIn(n, areas, f'rule area {n} has no control')

    def test_controls_register_is_current(self):
        import contextlib, io
        from sdem.controls import main
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(main(['--check']), 0)

if __name__ == '__main__':
    unittest.main()
