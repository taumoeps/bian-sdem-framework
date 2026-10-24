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


    def test_design_exports_are_valid_level_exports(self):
        from sdem.graph import LevelGraph
        from sdem.metamodel import Metamodel
        mm = Metamodel.load(); design = self.rows['M2']['result'].get('design', [])
        self.assertEqual({d['level'] for d in design}, {'A3', 'A4'})
        for d in design:
            self.assertEqual(LevelGraph(d, mm).validate(), [], d['level'])
            for i in d['instances']: self.assertEqual(i['lifecycle_status'], 'planned')
        for m in self.rows['M2']['result']['proposals']:
            self.assertEqual(m['confidence'], 0.4); self.assertIn('TARGET DESIGN, not a mapping', m['rationale'])

    def test_no_design_where_exports_exist(self):
        for cid, r in self.rows.items():
            if cid != 'M2': self.assertNotIn('design', r['result'], cid)

    def test_deterministic(self):
        from sdem.rules_engine import RulesEngine
        again = {r['case']: r for r in run(RulesEngine(), ['M1', 'C2'])}
        for cid in again: self.assertEqual(again[cid]['result'], self.rows[cid]['result'], cid)

    def test_beats_the_baseline(self):
        from sdem.inference import NameOverlapBaseline
        base = {r['case']: r for r in run(NameOverlapBaseline())}
        for cid, r in self.rows.items(): self.assertGreaterEqual(r['score']['registry']['f1'], base[cid]['score']['registry']['f1'], cid)


class CommandTests(unittest.TestCase):
    def test_sdem_infer_rules_on_a_store(self):
        import contextlib, io, tempfile
        from sdem.inference import main
        from sdem.store import build
        with tempfile.TemporaryDirectory() as t:
            e = ROOT / 'examples' / 'payment-initiation'
            build(sorted(str(p) for p in e.glob('a[1-4]-*.json')) + [str(e / 'm1-mappings-given.json')], Path(t) / 'g')
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf): self.assertEqual(main(['rules', '--graph', str(Path(t) / 'g'), '--out', str(Path(t) / 'o')]), 0)
            self.assertEqual(len(json.loads(buf.getvalue())['mappings']), 13)
            self.assertTrue((Path(t) / 'o' / 'inference-log.json').exists())

if __name__ == '__main__':
    unittest.main()
