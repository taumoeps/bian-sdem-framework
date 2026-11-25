"""CTL-22 — the inference engine and the metamodel agree (gap G-A, partly closed 2026-10-28).

The engine applies only rules that are in the metamodel (metamodel/relationship-rules.json), each at the step the metamodel
assigns it (fill_step), unless the difference is a documented exception below; and every rule the metamodel says the
engine applies is implemented. How a rule *matches* is still only in the engine's code — its description in words cannot
be checked by machine. A change to the engine or the metamodel that breaks the agreement fails this test."""
import glob, json, re, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys as _s2, pathlib as _pl2; _s2.path.insert(0, str(_pl2.Path(__file__).resolve().parent)); from needs import EXAMPLES  # noqa: E402 — SDEM's examples and sdem-bian's (R-D6)
sys.path.insert(0, str(ROOT))
from sdem.rules_engine import RulesEngine  # noqa: E402
from sdem.store import GraphReader  # noqa: E402

from sdem.rules_engine import _rules  # noqa: E402
RULES = _rules()   # the metamodel's rules the engine reads — BIAN's with them from sdem-bian where installed (BX-15, MX-55)
NOT_APPLIED = {'not_encodable', 'historical_method', 'subsumed', 'not_a_mapping', 'bian_internal'}   # rule decisions the engine never applies
ENGINE_ONLY = {'DESIGN'}   # the engine's design mode (DEC-E-05) — not a metamodel rule
# (rule, step the metamodel assigns, step the engine used) → why it is allowed
ALLOWED = {
    ('S01', 3, 5): "the metamodel's own fallback: 'fallback step 5 requires the full A2 landscape …' (data_needed)",
    ('S24', 2, 'design'): 'design mode — test case M2 (DEC-E-05)',
    ('S32', 1, 'design'): 'design mode — test case M2 (DEC-E-05)',
    ('S06', 1, 4): 'by design (owner, 2026-11-11; closes finding G-A-2): an activity whose invokes names an operation is joined in step 1, as fill_step says; one that names none is matched by verb and asset type in step 4, which needs the A2 structure — the split the metamodel record\'s reasoning gives',
}


def engine_log():
    log = []
    for d in sorted(glob.glob(str(EXAMPLES) + '/*/')):
        if not (Path(d) / 'mappings.json').exists(): continue   # examples/designs/ is not a workspace
        if 'reference-structure' in d: continue
        files = sorted(glob.glob(d + 'a*.json')) + [d + 'mappings.json']
        log += _full().infer(GraphReader.from_exports(files), {'id': 'CTL22'})['log']   # the core's rules with BIAN's (sdem-bian, BX-15)
    return log



def _full():   # the whole engine: SDEM's core rules with BIAN's steps from the installed sdem-bian (skipped without it)
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from test_acceptance import full_engine
    return full_engine()

import sys as _s, pathlib as _pl; _s.path.insert(0, str(_pl.Path(__file__).resolve().parent)); from needs import bian as _needs_bian  # noqa: E402 — BX-15: tests that need sdem-bian

@_needs_bian
class EngineMetamodelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.log = engine_log()

    def test_engine_applies_only_metamodel_rules(self):
        unknown = {a['plan_id'] for a in self.log} - set(RULES) - ENGINE_ONLY
        self.assertFalse(unknown, f'the engine applies rules that are not in the metamodel: {sorted(unknown)}')

    def test_each_rule_runs_at_its_assigned_step(self):
        drift = {(a['plan_id'], a['step_assigned'], a['step_used']) for a in self.log
                 if a['plan_id'] in RULES and a['step_used'] != RULES[a['plan_id']]['fill_step'] and not a['fallback']}
        self.assertFalse(drift - set(ALLOWED), f'engine steps differ from the metamodel, undocumented: {sorted(drift - set(ALLOWED), key=str)}')
        for a in self.log:   # the step the engine records as assigned is the metamodel's
            if a['plan_id'] in RULES: self.assertEqual(a['step_assigned'], RULES[a['plan_id']]['fill_step'], a['plan_id'])

    def test_every_applicable_rule_is_implemented(self):
        try: import sdem_bian
        except ImportError: self.skipTest('needs sdem-bian installed: BIAN\'s rules are in its rules_bian.py (BX-15)')
        src = (ROOT / 'sdem' / 'rules_engine.py').read_text(encoding='utf-8') + (Path(sdem_bian.__file__).parent / 'rules_bian.py').read_text(encoding='utf-8')   # 0.22 step 3b: BIAN's rules in their own module
        named = set(re.findall(r"'([SB]\d\d)'", src))
        applicable = {k for k, r in RULES.items() if r.get('fill_step') not in (0, None) and r['rule_decision'] not in NOT_APPLIED}
        self.assertFalse(applicable - named, f'rules the metamodel says the engine applies, but the engine never names: {sorted(applicable - named)}')

    def test_documented_exceptions_still_occur(self):
        """An exception that no longer happens must be removed from ALLOWED, so the list stays true."""
        seen = {(a['plan_id'], a['step_assigned'], a['step_used']) for a in self.log}
        for k in ALLOWED: self.assertIn(k, seen, f'exception {k} no longer occurs — remove it')


if __name__ == '__main__':
    unittest.main()
