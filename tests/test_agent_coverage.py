"""Agents know when to use every command (AG-S01…AG-S03): each command and subcommand — except the SDEM owner's maintenance commands
(`sdem model …`) — is named in the agents' instructions (templates/agents/AGENTS.md) or a skill, so a new command cannot ship without
agents being told when to use it; the generated `sdem-scenarios` skill is current and installed for every agent; `sdem commands <name>`
gives one command's entry."""
import contextlib, io, json, os, re, subprocess, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem import agent, scenarioskill   # noqa: E402
from sdem.cli import JOURNEYS, _run   # noqa: E402


def sdem(*args):
    env = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}
    r = subprocess.run([sys.executable, '-m', 'sdem', *args], cwd=ROOT, capture_output=True, text=True, env=env)
    return r.returncode, r.stdout, r.stderr


class AgentCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            cls.cmds = agent.catalogue({k: v for k, v in JOURNEYS.items() if k != 'commands'}, _run)['commands']
        cls.text = (ROOT / 'templates' / 'agents' / 'AGENTS.md').read_text(encoding='utf-8') + ''.join(
            p.read_text(encoding='utf-8') for p in sorted((ROOT / '.github' / 'skills').glob('*/SKILL.md')))

    def test_every_command_is_named_for_agents(self):   # AG-S01
        named = lambda k: f'sdem {k}' in self.text
        missing = []
        for k, c in self.cmds.items():
            if k.split()[0] in ('model',) or named(k) or (c.get('description') or '').startswith('the old name'): continue   # an old name: agents use the new one
            if 'group' in c and all(named(g) for g in c['group']): continue
            missing.append(k)
        self.assertFalse(missing, 'commands no agent instruction or skill names — add them to docs/sdem-scenarios.md (then sdem model regenerate) '
                                  'or to the skill for their job: ' + ', '.join(sorted(missing)))

    def test_the_scenarios_skill_is_generated_and_installed(self):   # AG-S02
        t = scenarioskill.render()
        for o in scenarioskill.OUTS: self.assertEqual(o.read_text(encoding='utf-8'), t, f'{o} is stale — sdem model regenerate')
        self.assertTrue(t.startswith('---\nname: sdem-scenarios\ndescription: '))
        self.assertNotIn('](reference/', t)   # links are from the skill's folder, pinned to the version on install
        for target in re.findall(r'\]\((\.\./[^)#]+)', t): self.assertTrue((scenarioskill.OUTS[0].parent / target).exists(), target)
        from sdem import copilot
        self.assertIn('skills/sdem-scenarios/SKILL.md', copilot.files())   # what sdem agents install ships
        agents_md = (ROOT / 'templates' / 'agents' / 'AGENTS.md').read_text(encoding='utf-8')
        for skill in sorted(p.parent.name for p in (ROOT / '.github' / 'skills').glob('*/SKILL.md')):
            self.assertIn(f'`{skill}`', agents_md, f'AGENTS.md does not point to the skill {skill}')

    def test_one_command_on_request(self):   # AG-S03
        code, out, _ = sdem('commands', 'events', 'assess', '--json')
        self.assertEqual(code, 0); self.assertEqual(list(json.loads(out)['commands']), ['events assess'])
        code, out, _ = sdem('commands', 'bian inference', '--json')
        self.assertIn('bian inference accept', json.loads(out)['commands'])
        self.assertLess(len(out), 20000)
        code, _, err = sdem('commands', 'evnts', 'assess')
        self.assertEqual(code, 2); self.assertIn('did you mean: events assess', err)


if __name__ == '__main__':
    unittest.main()
