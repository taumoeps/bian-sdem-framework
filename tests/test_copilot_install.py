"""`sdem copilot install` — SDEM's Copilot files in the estate repository (docs/design/sdem-copilot-install-design.md, CI-*)."""
import json, re, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

from sdem import copilot
from sdem.cli import JOURNEYS
from sdem.paths import REPO_URL, version

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'templates' / 'estate-repo'


class CopilotInstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); self.repo = self.tmp / 'estates-repo'
        shutil.copytree(TEMPLATE, self.repo)
        self.own = {p.relative_to(self.repo).as_posix(): p.read_bytes() for p in (self.repo / '.github').rglob('*') if p.is_file()}

    def tearDown(self): shutil.rmtree(self.tmp, ignore_errors=True)

    def run_sdem(self, *a):
        r = subprocess.run([sys.executable, '-m', 'sdem', 'copilot', 'install', '--to', str(self.repo), *a], cwd=ROOT, capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr

    def installed(self):
        gh = self.repo / '.github'
        return {p.relative_to(gh).as_posix(): p for p in gh.rglob('*') if p.is_file() and p.relative_to(self.repo).as_posix() not in self.own}

    def test_installs_the_copilot_files_but_not_example_only_ones(self):  # CI-02, CI-D3
        code, out = self.run_sdem()
        self.assertEqual(code, 0, out); self.assertIn(f'for SDEM {version()}', out)
        got = set(self.installed())
        for must in ('copilot-instructions.md', 'agents/sdem-orchestrator.agent.md', 'prompts/sdem-explain.prompt.md',
                     'skills/sdem-onboard-designs/SKILL.md', 'skills/sdem-approve-links/evidence-by-link-type.md', copilot.RECORD):
            self.assertIn(must, got)
        self.assertNotIn('prompts/example3-rehost.prompt.md', got)

    def test_leaves_the_teams_own_files_alone(self):  # CI-06
        self.run_sdem()
        for rel, data in self.own.items():
            self.assertEqual((self.repo / rel).read_bytes(), data, rel)

    def test_every_reference_works_in_an_estate_repository(self):  # CI-03
        self.run_sdem()
        for rel, p in self.installed().items():
            if p.suffix != '.md': continue
            text = p.read_text(encoding='utf-8')
            plain = re.sub(r'\[[^\]]*\]\([^)]*\)', '', text)                      # outside links …
            self.assertIsNone(re.search(r'`(?:docs|metamodel|schema|examples|templates)/', plain), rel)   # … no bare project paths
            for target in re.findall(r'\]\(([^)\s]+)\)', text):
                if target.startswith(REPO_URL):
                    m = re.match(re.escape(REPO_URL) + r'/(?:blob|tree)/v([^/]+)/([^#]+)', target)
                    self.assertTrue(m, target); self.assertEqual(m.group(1), version())
                    self.assertTrue((ROOT / m.group(2)).exists(), f'{rel}: {target}')   # the file exists at this version
                elif not re.match(r'^(https?:|mailto:|#)', target):
                    self.assertTrue((p.parent / target.split('#')[0]).exists(), f'{rel}: {target}')

    def test_every_command_named_exists(self):  # CI-04
        self.run_sdem()
        named = set()
        for p in self.installed().values():
            if p.suffix == '.md': named |= set(re.findall(r'`sdem ([a-z]+)\b', p.read_text(encoding='utf-8')))   # commands are written as code
        self.assertTrue(named)
        self.assertEqual(sorted(n for n in named if n not in JOURNEYS), [])

    def test_upgrades_keep_what_the_team_changed(self):  # CI-05
        self.run_sdem()
        code, out = self.run_sdem(); self.assertIn('wrote 0 Copilot file(s)', out)                 # nothing changed, nothing written
        mine = self.repo / '.github' / 'prompts' / 'sdem-explain.prompt.md'
        mine.write_text(mine.read_text() + '\nOur team: always cite the estate.\n', encoding='utf-8')
        code, out = self.run_sdem()
        self.assertIn('kept 1 file(s) your team changed', out); self.assertIn('Our team', mine.read_text())
        code, out = self.run_sdem('--force')
        self.assertNotIn('Our team', mine.read_text())

    def test_dry_run_writes_nothing(self):  # CI-02
        code, out = self.run_sdem('--dry-run')
        self.assertEqual(code, 0); self.assertIn('would write', out)
        self.assertEqual(self.installed(), {})

    def test_the_template_uses_it(self):  # CI-07
        readme = (TEMPLATE / 'README.md').read_text(encoding='utf-8')
        self.assertGreaterEqual(readme.count('sdem copilot install'), 2)
        self.assertNotIn('copy `.github/copilot-instructions.md`', readme)
        self.assertEqual((TEMPLATE / '.vscode' / 'extensions.json').read_text(), (ROOT / '.vscode' / 'extensions.json').read_text())


if __name__ == '__main__':
    unittest.main()
