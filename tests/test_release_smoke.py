"""Release smoke tests: SDEM as a new architect gets it — a built wheel in a clean environment, run outside the repository, with no
clone (v0.11.3 release readiness). Installation, a new workspace, agent support (and a reinstall that keeps a customised file), the
synthetic example that ships with SDEM, structured output, and the governance safeguards — without real keys or real workspaces."""
import json, os, re, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd, cwd, ok=(0,), env=None):
    r = subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=True, env=env, timeout=900)
    if r.returncode not in ok: raise AssertionError(f"{' '.join(map(str, cmd))}: exit {r.returncode}\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}")
    return r


class ReleaseSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix='sdem-smoke-'))
        dist = cls.tmp / 'dist'
        run([sys.executable, '-m', 'pip', 'wheel', ROOT, '--no-deps', '-w', dist, '-q'], cwd=cls.tmp)
        cls.wheel = next(dist.glob('sdem-*.whl'))
        run([sys.executable, '-m', 'venv', cls.tmp / 'venv'], cwd=cls.tmp)
        bindir = cls.tmp / 'venv' / ('Scripts' if os.name == 'nt' else 'bin')
        cls.py = bindir / ('python.exe' if os.name == 'nt' else 'python')
        run([cls.py, '-m', 'pip', 'install', '-q', '--no-index', cls.wheel], cwd=cls.tmp)
        cls.sd = bindir / ('sdem.exe' if os.name == 'nt' else 'sdem')
        cls.home = cls.tmp / 'my-sdem'; cls.home.mkdir()
        cls.env = {k: v for k, v in os.environ.items() if k != 'PYTHONPATH'}   # the installed package only — never the checkout

    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.tmp, ignore_errors=True)

    def sdem(self, *args, ok=(0,)):
        r = run([self.sd, *args], cwd=self.home, ok=ok, env=self.env)
        return r, (json.loads(r.stdout) if r.stdout.strip().startswith('{') else None)

    def test_1_the_package_installs_and_answers(self):
        from sdem.paths import version
        r, _ = self.sdem('--version'); self.assertEqual(r.stdout.strip(), f'sdem {version()}')
        self.assertIn('usage: sdem', self.sdem('--help')[0].stdout)
        _, d = self.sdem('commands', '--json'); self.assertIn('requirements evaluate', d['commands']); self.assertIn('governance verify', d['commands'])
        r = run([self.py, '-c', 'import sdem, pathlib; d = pathlib.Path(sdem.__file__).parent / "data"; print(sorted(p.name for p in d.iterdir() if p.is_dir()))'], cwd=self.home, env=self.env)
        for res in ('schema', 'metamodel', 'bian', 'copilot', 'agents', 'examples'): self.assertIn(res, r.stdout)
        self.assertNotIn(str(ROOT), run([self.py, '-c', 'import sdem; print(sdem.__file__)'], cwd=self.home, env=self.env).stdout)   # not the checkout

    def test_2_a_new_workspace_is_empty_valid_and_recorded(self):
        _, d = self.sdem('new', '--workspace', 'workspaces/payments', '--person', 'steven', '--json')
        ws = self.home / 'workspaces' / 'payments'
        for f in ('a1-business.json', 'a3-application.json', 'a4-technology.json', 'mappings.json', 'workspace.json', 'sdem-ledger.json'): self.assertTrue((ws / f).exists(), f)
        self.assertEqual(json.loads((ws / 'a1-business.json').read_text())['instances'], [])
        _, d = self.sdem('check', '--workspace', 'workspaces/payments', '--require-recorded', '--json'); self.assertTrue(d['ok']); self.assertEqual(d['unrecorded_edits'], [])

    def test_3_agent_support_installs_and_keeps_your_changes(self):
        site = self.home / 'agents-site'; site.mkdir()
        _, d = self.sdem('agents', 'install', '--to', site, '--dry-run', '--json'); self.assertTrue(d['dry_run']); self.assertFalse((site / 'AGENTS.md').exists())
        self.sdem('agents', 'install', '--to', site, '--json')
        for f in ('AGENTS.md', 'CLAUDE.md', '.claude/skills/sdem-impact-validation/SKILL.md', '.agents/skills/sdem-requirements-risk/SKILL.md', '.gemini/settings.json',
                  '.github/copilot-instructions.md', '.github/agents/sdem-orchestrator.agent.md', '.github/skills/sdem-records/SKILL.md'):
            self.assertTrue((site / f).exists(), f)
        (site / 'AGENTS.md').write_text((site / 'AGENTS.md').read_text() + '\n## Our team rule\n')
        _, d = self.sdem('agents', 'install', '--to', site, '--json')
        self.assertIn('AGENTS.md', d['kept']); self.assertIn('Our team rule', (site / 'AGENTS.md').read_text())   # never overwritten silently

    def test_4_the_synthetic_example_runs_from_the_package(self):
        _, d = self.sdem('new', '--workspace', 'workspaces/example', '--person', 'steven', '--example', 'payment-initiation', '--json')
        _, d = self.sdem('check', '--workspace', 'workspaces/example', '--require-recorded', '--json'); self.assertTrue(d['ok'])
        self.sdem('build', '--workspace', 'workspaces/example', '--out', 'workspaces/example/graph', '--json')
        _, t = self.sdem('trace', 'A4', '--direction', 'up', '--graph', 'workspaces/example/graph', '--json'); self.assertTrue(t['items'])
        _, i = self.sdem('impact', 'INF-K8S-PAY-PROD', '--change', 'rehost', '--graph', 'workspaces/example/graph', '--json')
        self.assertEqual(i['coverage']['A3']['result'], 'impact_detected')
        _, e = self.sdem('requirements', 'evaluate', '--workspace', 'workspaces/example', '--record', 'INF-K8S-PAY-PROD', '--change', 'rehost', '--proposed', 'INF-K8S-PAY-PROD2', '--json')
        self.assertEqual(len([f for f in e['risks'] if f['type'] == 'confirmed_breach']), 4)

    def test_5_governance_safeguards_hold(self):
        _, d = self.sdem('new', '--workspace', 'workspaces/x', '--person', 'sdem-orchestrator', '--json', ok=(2,)); self.assertEqual(d['error']['code'], 'needs_person')
        self.sdem('new', '--workspace', 'workspaces/gov', '--person', 'steven', '--example', 'payment-initiation', '--json')
        _, d = self.sdem('governance', 'verify', '--workspace', 'workspaces/gov', '--json')
        self.assertEqual(d['verified'], 0); self.assertTrue(all(r['status'] == 'no_policy' for r in d['decisions']))     # attribution only: never "verified"
        _, d = self.sdem('governance', 'verify', '--workspace', 'workspaces/gov', '--require-verified', '--json', ok=(1,))

    def test_6_documentation_does_not_present_attribution_as_identity(self):
        banned = [r'built into the software\s*—\s*SDEM refuses', r'SDEM authenticates', r'proves? who', r'agents? (can ?not|cannot) (approve|decide|accept)',
                  r'impossible for an agent', r'guarantees? that (only )?a (human|person)']
        files = [ROOT / f for f in ('README.md', 'SECURITY.md', 'PRIVACY.md')] + list((ROOT / 'docs').glob('*.md')) + [ROOT / 'docs' / 'design' / 'sdem-governance.md', ROOT / 'templates' / 'agents' / 'AGENTS.md']
        hits = [f'{f.relative_to(ROOT)}: {m.group(0)}' for f in files for p in banned for m in re.finditer(p, f.read_text(encoding='utf-8'), re.I)]
        self.assertEqual(hits, [])
        gov = (ROOT / 'docs' / 'design' / 'sdem-governance.md').read_text(encoding='utf-8')
        self.assertIn('attribution, not authentication', gov); self.assertIn('not a security boundary', gov)

    def test_8_the_guides_walkthrough_runs_on_the_installed_package(self):   # the user guide §4a, as a reader copies it, on the wheel
        sys.path.insert(0, str(ROOT / 'tests')); from test_navigation import guide_steps
        walk = self.home / 'walkthrough'; walk.mkdir()
        for step in guide_steps():
            if step[0] == 'file': (walk / step[1]).write_text(step[2])
            else: run([self.sd, *step[1][1:]], cwd=walk, env=self.env)
        self.assertTrue((walk / 'work' / 'sdem' / 'workspaces' / 'payments-graph.html').exists())
        self.assertIn('APP-PAY-NOTIFY', (walk / 'workspaces' / 'payments' / 'links' / 'proposals.json').read_text())   # step 11's proposal
        run([self.sd, 'new', '--workspace', 'explore/payments', '--person', 'jane', '--example', 'payment-initiation', '--explore'], cwd=walk, env=self.env)
        self.assertTrue((walk / 'work' / 'sdem' / 'index.html').exists())

    def test_7_the_source_distribution_builds(self):
        if subprocess.run([sys.executable, '-m', 'build', '--version'], capture_output=True, cwd=self.tmp).returncode != 0:
            self.skipTest('the build tool is not installed here — the CI package job builds the source distribution')
        dist = self.tmp / 'sdist'
        run([sys.executable, '-m', 'build', '--sdist', '--outdir', dist, ROOT], cwd=self.tmp)
        self.assertTrue(list(dist.glob('sdem-*.tar.gz')))


if __name__ == '__main__':
    unittest.main()
