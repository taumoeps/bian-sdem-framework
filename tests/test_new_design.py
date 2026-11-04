"""New-design onboarding (docs/sdem-new-design.md): the skill sdem-new-design, its example change set, the Copilot prompt
/sdem-new-design, and the dry-run notice people read first. Synthetic data only."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}
SKILL = ROOT / '.github' / 'skills' / 'sdem-new-design'


def sdem(*args, cwd, ok=(0,)):
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], cwd=cwd, capture_output=True, text=True, env=ENV)
    assert r.returncode in ok, f'sdem {" ".join(map(str, args))}: exit {r.returncode}\n{r.stdout[-900:]}\n{r.stderr[-900:]}'
    return r.returncode, r.stdout + r.stderr, (json.loads(r.stdout) if r.stdout.strip().startswith('{') else None)


class NewDesignTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); sdem('new', '--workspace', self.tmp / 'ws', '--person', 'steven', cwd=self.tmp)

    def tearDown(self): shutil.rmtree(self.tmp, ignore_errors=True)

    def test_the_skills_example_lands_and_aid_takes_it_further(self):
        ex = SKILL / 'example-a1-new-design.json'
        sdem('change', 'propose', ex, '--workspace', self.tmp / 'ws', '--agent', 'sdem-a1-business', '--person', 'steven', cwd=self.tmp)
        self.assertEqual(sdem('check', '--workspace', self.tmp / 'ws', '--require-recorded', cwd=self.tmp)[0], 0)
        _, _, d = sdem('aid', '--workspace', self.tmp / 'ws', '--person', 'steven', '--dry-run', '--json', cwd=self.tmp)
        self.assertIn('SD-FINANCIAL-ACCOUNTING', d['added'].get('A2', []))                                                 # its BIAN operation brings in Financial Accounting

    def test_every_bian_id_in_the_example_is_one_search_returns(self):
        ex = json.loads((SKILL / 'example-a1-new-design.json').read_text())
        ids = {x for c in ex['changes'] for x in (c['record'].get('attributes') or {}).get('invokes', [])}
        _, _, d = sdem('bian', 'search', 'ledger', 'posting', '--all-operations', '--json', cwd=self.tmp)
        self.assertTrue(ids <= {o['id'] for r in d['results'] for o in r['operations']})

    def test_the_skill_and_prompt_install_for_every_agent(self):
        site = self.tmp / 'site'; site.mkdir()
        sdem('agents', 'install', '--to', site, cwd=self.tmp)
        for f in ('.claude/skills/sdem-new-design/SKILL.md', '.agents/skills/sdem-new-design/SKILL.md', '.github/skills/sdem-new-design/SKILL.md',
                  '.github/skills/sdem-new-design/example-a1-new-design.json', '.github/prompts/sdem-new-design.prompt.md'):
            self.assertTrue((site / f).exists(), f)
        self.assertIn('sdem-new-design', (site / 'AGENTS.md').read_text())

    def test_a_dry_run_says_so_before_anything_else(self):
        _, out, _ = sdem('change', 'propose', SKILL / 'example-a1-new-design.json', '--workspace', self.tmp / 'ws', '--agent', 'sdem-a1-business',
                         '--person', 'steven', '--dry-run', cwd=self.tmp)
        self.assertTrue(out.startswith('DRY RUN — a preview: nothing below was written'))
        self.assertEqual(json.loads((self.tmp / 'ws' / 'a1-business.json').read_text())['instances'], [])


if __name__ == '__main__':
    unittest.main()
