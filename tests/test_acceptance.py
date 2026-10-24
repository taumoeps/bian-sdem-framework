"""Inference-engine acceptance (sdem/acceptance.py; relationship-rules-spec.md §8, DEC-E-01)."""
import json, unittest
from pathlib import Path

from sdem.acceptance import ReplayEngine, load_cases, run

ROOT = Path(__file__).resolve().parents[1]


class HarnessTests(unittest.TestCase):
    def test_replaying_the_hand_runs_passes_every_case(self):
        """The harness is right only if the hand-executed runs, replayed, pass every case and validate."""
        rows = run(ReplayEngine())
        self.assertEqual(len(rows), 8)
        for r in rows: self.assertTrue(r['passed'], f"{r['case']}: {r['issues'][:3]} {r['score']} vs {r['floor']}")

    def test_inputs_never_include_the_answers(self):
        for c in load_cases():
            self.assertNotIn('gold', c['given']); self.assertNotEqual(c['given'], 'mappings.json')


class RulesEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from sdem.rules_engine import RulesEngine
        cls.rows = {r['case']: r for r in run(RulesEngine())}

    def test_cases_marked_passing_pass(self):
        for c in load_cases():
            if c['engine_status'] == 'passing':
                r = self.rows[c['id']]; self.assertTrue(r['passed'], f"{c['id']}: {r['score']} vs {r['floor']} {r['issues'][:3]}")

    def test_no_case_loses_precision(self):
        """Whatever the engine proposes so far must be at least as precise as the hand-run (no false proposals introduced)."""
        for cid, r in self.rows.items():
            for k, s in r['score'].items():
                if s['proposed']: self.assertGreaterEqual(s['precision'] + 1e-9, r['floor'][k]['precision'], f'{cid} {k}: {r["detail"][k]["false_proposals"][:3]}')

    def test_every_proposal_validates(self):
        for cid, r in self.rows.items(): self.assertEqual(r['issues'], [], cid)

    def test_log_covers_every_output(self):
        for cid, r in self.rows.items():
            ids = {a['proposal_id'] for a in r['result']['log'] if a['proposal_id']}
            for m in r['result']['proposals'] + r['result']['candidates']: self.assertIn(m['mapping_id'], ids, cid)


if __name__ == '__main__':
    unittest.main()
