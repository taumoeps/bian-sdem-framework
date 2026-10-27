"""Use-case example 3 (docs/use-case-example-3.md): the agent platform's records, commands and controls, re-run on every change.
The sealed criteria (spec AT-AG-01…08, commit 5cbb0ed) must all pass, and every control test (CTL-19, CTL-20, CTL-16, governance)."""
import sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))


class UseCaseExample3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from use_case_example_3 import run
        cls.R = run()

    def test_every_sealed_criterion_is_met(self):
        self.assertEqual([c['id'] for c in self.R['criteria']], [f'AT-AG-0{i}' for i in range(1, 9)])
        for c in self.R['criteria']: self.assertTrue(c['pass'], f"{c['id']}: {c['did']}")

    def test_controls_with_good_and_bad_data(self):
        self.assertEqual({x['data'] for x in self.R['controls_tests'] if x['control'] in ('CTL-19', 'CTL-20')}, {'good', 'bad'})
        for x in self.R['controls_tests']: self.assertTrue(x['pass'], f"{x['control']} {x['test']}: should be {x['should']}, was {x['did']} — {x['message']}")

    def test_agent_files_match_the_platform_rules(self):
        """The orchestrator may call only the four layer agents; layer agents may call none (no direct messages, AG-D02)."""
        import re
        agents = {p.name.split('.')[0]: p.read_text(encoding='utf-8') for p in (ROOT / '.github' / 'agents').glob('*.agent.md')}
        self.assertEqual(set(agents), {'sdem-orchestrator', 'sdem-a1-business', 'sdem-a2-bian', 'sdem-a3-application', 'sdem-a4-technology'})
        for name, text in agents.items():
            front = text.split('---')[1]
            tools = next(l for l in front.splitlines() if l.startswith('tools:'))
            self.assertIn(f'name: {name}', front)
            if name == 'sdem-orchestrator':
                self.assertIn("'agent'", tools); self.assertIn("agents: ['sdem-a1-business', 'sdem-a2-bian', 'sdem-a3-application', 'sdem-a4-technology']", front)
            else:
                self.assertIn('\nagents: []', front); self.assertNotIn("'agent'", tools)
            for cmd in re.findall(r'`sdem ([a-z]+)', text):  # every sdem command an agent file names exists (WB-C06)
                from sdem import cli
                self.assertIn(cmd, cli.JOURNEYS, f'{name} names unknown command sdem {cmd}')


if __name__ == '__main__':
    unittest.main()
