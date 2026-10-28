"""The GitHub Copilot set-up in .github/ (docs/sdem-workbench-spec.md WB-C01…C06; docs/sdem-agent-platform-design.md §7.2):
agents, prompt files and skills load only if their names and frontmatter are right, and they must name only real sdem commands."""
import re, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem import cli  # noqa: E402

GH = ROOT / '.github'
NAME = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')


def front(text):
    parts = text.split('---')
    return dict(re.findall(r'^([a-z-]+):\s*(.*)$', parts[1], re.M)) if text.startswith('---') and len(parts) > 2 else {}


def commands(text):
    return set(re.findall(r'`sdem ([a-z]+)', text))


class CopilotSetupTests(unittest.TestCase):
    def test_instructions_exist(self):
        self.assertTrue((GH / 'copilot-instructions.md').exists())

    def test_agents(self):
        names = set()
        for p in (GH / 'agents').glob('*.agent.md'):
            f = front(p.read_text(encoding='utf-8'))
            self.assertEqual(f.get('name'), p.name[:-len('.agent.md')], p.name)
            self.assertTrue(f.get('description'), p.name)
            names.add(f['name'])
        self.assertEqual(len(names), 5)

    def test_prompts_name_a_real_agent(self):
        agents = {p.name[:-len('.agent.md')] for p in (GH / 'agents').glob('*.agent.md')}
        prompts = list((GH / 'prompts').glob('*.prompt.md'))
        self.assertGreaterEqual(len(prompts), 9)
        for p in prompts:
            f = front(p.read_text(encoding='utf-8'))
            self.assertEqual(f.get('name'), p.name[:-len('.prompt.md')], p.name)
            self.assertRegex(f['name'], NAME)
            self.assertTrue(f.get('description'), p.name)
            self.assertIn(f.get('agent'), agents | {'ask', 'agent', 'plan'}, p.name)

    def test_skills_load(self):
        """Skill names: lowercase letters, numbers and hyphens, matching the folder — otherwise they silently fail to load."""
        skills = [d for d in (GH / 'skills').iterdir() if d.is_dir()]
        self.assertGreaterEqual(len(skills), 4)
        for d in skills:
            text = (d / 'SKILL.md').read_text(encoding='utf-8'); f = front(text)
            self.assertEqual(f.get('name'), d.name); self.assertRegex(d.name, NAME); self.assertLessEqual(len(d.name), 64)
            self.assertTrue(0 < len(f.get('description', '')) <= 1024, d.name)
            for link in re.findall(r'\]\(\./([^)]+)\)', text):  # files a skill references must exist
                self.assertTrue((d / link).exists(), f'{d.name}: {link}')

    def test_every_named_sdem_command_exists(self):
        files = [GH / 'copilot-instructions.md'] + list(GH.glob('agents/*.md')) + list(GH.glob('prompts/*.md')) + list(GH.glob('skills/*/SKILL.md'))
        for p in files:
            for c in commands(p.read_text(encoding='utf-8')):
                self.assertIn(c, cli.JOURNEYS, f'{p.relative_to(ROOT)} names unknown command: sdem {c}')


    def test_codeowners_cover_what_matters(self):  # a person reviews the rulebook, approved links, data and the agents' powers
        text = (ROOT / '.github' / 'CODEOWNERS').read_text()
        for pattern in ('/metamodel/', '/schema/', '**/mappings.json', '**/a3-application.json', '**/loads/', '**/coordination/', '/.github/'):
            self.assertRegex(text, r'(?m)^' + re.escape(pattern) + r'\s+@\S+', pattern)

    def test_agents_know_imports_and_never_load(self):  # AG-A07: built skills → agents → prompts
        skill = (GH / 'skills' / 'sdem-onboard-designs' / 'SKILL.md').read_text(encoding='utf-8')
        self.assertIn('You never run `sdem load`', skill); self.assertIn('--dry-run', skill); self.assertIn('CTL-17', skill)
        for p in (GH / 'agents').glob('*.agent.md'):
            text = p.read_text(encoding='utf-8')
            self.assertRegex(text, r'Never run[^\n]*`sdem load`', p.name)
            if p.name != 'sdem-a2-bian.agent.md': self.assertIn('sdem-onboard-designs', text, p.name)
        prompt = (GH / 'prompts' / 'sdem-onboarding-review.prompt.md').read_text(encoding='utf-8')
        self.assertIn('Never run `sdem load` without `--dry-run`', prompt); self.assertIn('sdem-onboard-designs', prompt)
        self.assertIn('sdem load', (GH / 'copilot-instructions.md').read_text(encoding='utf-8'))

    def test_no_mcp_no_ai_client(self):  # WB-C07: no MCP server, no AI API client, no API key in SDEM
        self.assertFalse((ROOT / '.vscode' / 'mcp.json').exists())
        for f in (ROOT / '.vscode').glob('*.json'):
            self.assertNotIn('mcpServers', f.read_text(encoding='utf-8'), f.name)
        for f in (ROOT / 'sdem').glob('*.py'):
            src = f.read_text(encoding='utf-8')
            self.assertIsNone(re.search(r'^\s*(import|from)\s+(anthropic|openai|google\.generativeai|requests|httpx)\b', src, re.M), f.name)
            self.assertIsNone(re.search(r'(ANTHROPIC|OPENAI)_API_KEY|api_key\s*=', src), f.name)
        for f in GH.glob('agents/*.md'):
            self.assertNotIn('mcp', front(f.read_text(encoding='utf-8')).get('tools', '').lower(), f.name)

if __name__ == '__main__':
    unittest.main()
