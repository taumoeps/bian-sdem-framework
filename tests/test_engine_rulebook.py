"""CTL-22 — the inference engine and the rulebook agree (gap G-A, partly closed 2026-10-28).

The engine applies only rules that are in the rulebook (metamodel/relationship-rules.json), each at the step the rulebook
assigns it (fill_step), unless the difference is a documented exception below; and every rule the rulebook says the
engine applies is implemented. How a rule *matches* is still only in the engine's code — its description in words cannot
be checked by machine. A change to the engine or the rulebook that breaks the agreement fails this test."""
import glob, json, re, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem.rules_engine import RulesEngine  # noqa: E402
from sdem.store import GraphReader  # noqa: E402

RULES = {m['id']: m for m in json.loads((ROOT / 'metamodel' / 'relationship-rules.json').read_text(encoding='utf-8'))['mappings']}
NOT_APPLIED = {'not_encodable', 'historical_method', 'subsumed', 'not_a_mapping', 'bian_internal'}   # rule decisions the engine never applies
ENGINE_ONLY = {'DESIGN'}   # the engine's design mode (DEC-E-05) — not a rulebook rule
# (rule, step the rulebook assigns, step the engine used) → why it is allowed
ALLOWED = {
    ('S01', 3, 5): "the rulebook's own fallback: 'fallback step 5 requires the full A2 landscape …' (data_needed)",
    ('S24', 2, 'design'): 'design mode — test case M2 (DEC-E-05)',
    ('S32', 1, 'design'): 'design mode — test case M2 (DEC-E-05)',
    ('S44', 1, 3): 'FINDING G-A-1 (open, for the owner): S44 is derived from S43 instances, so the engine applies it in step 3; the rulebook says step 1 — the record or the engine should change',
}


def engine_log():
    log = []
    for d in sorted(glob.glob(str(ROOT / 'examples') + '/*/')):
        if not (Path(d) / 'mappings.json').exists(): continue   # examples/designs/ is not an estate
        if 'reference-structure' in d: continue
        files = sorted(glob.glob(d + 'a*.json')) + [d + 'mappings.json']
        log += RulesEngine().infer(GraphReader.from_exports(files), {'id': 'CTL22'})['log']
    return log


class EngineRulebookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.log = engine_log()

    def test_engine_applies_only_rulebook_rules(self):
        unknown = {a['plan_id'] for a in self.log} - set(RULES) - ENGINE_ONLY
        self.assertFalse(unknown, f'the engine applies rules that are not in the rulebook: {sorted(unknown)}')

    def test_each_rule_runs_at_its_assigned_step(self):
        drift = {(a['plan_id'], a['step_assigned'], a['step_used']) for a in self.log
                 if a['plan_id'] in RULES and a['step_used'] != RULES[a['plan_id']]['fill_step'] and not a['fallback']}
        self.assertFalse(drift - set(ALLOWED), f'engine steps differ from the rulebook, undocumented: {sorted(drift - set(ALLOWED), key=str)}')
        for a in self.log:   # the step the engine records as assigned is the rulebook's
            if a['plan_id'] in RULES: self.assertEqual(a['step_assigned'], RULES[a['plan_id']]['fill_step'], a['plan_id'])

    def test_every_applicable_rule_is_implemented(self):
        src = (ROOT / 'sdem' / 'rules_engine.py').read_text(encoding='utf-8')
        named = set(re.findall(r"'([SB]\d\d)'", src))
        applicable = {k for k, r in RULES.items() if r.get('fill_step') not in (0, None) and r['rule_decision'] not in NOT_APPLIED}
        self.assertFalse(applicable - named, f'rules the rulebook says the engine applies, but the engine never names: {sorted(applicable - named)}')

    def test_documented_exceptions_still_occur(self):
        """An exception that no longer happens must be removed from ALLOWED, so the list stays true."""
        seen = {(a['plan_id'], a['step_assigned'], a['step_used']) for a in self.log}
        for k in ALLOWED: self.assertIn(k, seen, f'exception {k} no longer occurs — remove it')


if __name__ == '__main__':
    unittest.main()
