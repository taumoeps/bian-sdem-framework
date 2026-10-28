"""The estate-repository template (templates/estate-repo) works: its CI script passes a good estate, fails a broken one
and an edited approved link; its pin names the current SDEM release; its dashboards build; it carries no real data."""
import json, os, re, shutil, stat, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / 'templates' / 'estate-repo'


class EstateTemplateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); self.repo = self.tmp / 'estates-repo'
        shutil.copytree(T, self.repo)
        shutil.copytree(ROOT / 'examples' / 'payment-initiation', self.repo / 'estates' / 'payments', ignore=shutil.ignore_patterns('graph'))
        bin_ = self.tmp / 'bin'; bin_.mkdir(); shim = bin_ / 'sdem'   # `sdem` as pip would install it
        shim.write_text(f'#!/bin/sh\nexec "{sys.executable}" -m sdem "$@"\n'); shim.chmod(shim.stat().st_mode | stat.S_IEXEC)
        self.env = {**os.environ, 'PATH': f'{bin_}{os.pathsep}{os.environ["PATH"]}', 'PYTHONPATH': str(ROOT),
                    'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@example.com', 'GIT_COMMITTER_NAME': 't', 'GIT_COMMITTER_EMAIL': 't@example.com'}
        self.git('init', '-q'); self.git('add', '-A'); self.git('-c', 'commit.gpgsign=false', 'commit', '-qm', 'base')

    def tearDown(self): shutil.rmtree(self.tmp, ignore_errors=True)

    def git(self, *a): subprocess.run(['git', *a], cwd=self.repo, env=self.env, check=True, capture_output=True)

    def ci(self, base=''):
        r = subprocess.run(['bash', 'ci/check-estates.sh', *([base] if base else [])], cwd=self.repo, env=self.env, capture_output=True, text=True, timeout=300)
        return r.returncode, r.stdout + r.stderr

    def test_a_good_estate_passes(self):
        code, out = self.ci('HEAD')
        self.assertEqual(code, 0, out[-1500:]); self.assertIn('OK: 1 estate(s) pass', out)

    def test_an_edited_approved_link_fails(self):
        p = self.repo / 'estates' / 'payments' / 'mappings.json'; d = json.loads(p.read_text())
        m = next(x for x in d['mappings'] if x.get('status') == 'approved'); m['rationale'] = (m.get('rationale') or '') + ' edited'
        p.write_text(json.dumps(d, indent=2))
        code, out = self.ci('HEAD')
        self.assertEqual(code, 1); self.assertIn('an approved link was edited or removed', out)

    def test_a_broken_estate_fails(self):
        p = self.repo / 'estates' / 'payments' / 'a3-application.json'; d = json.loads(p.read_text())
        d['instances'][0]['type'] = 'A3.NoSuchType'; p.write_text(json.dumps(d))
        code, out = self.ci()
        self.assertEqual(code, 1); self.assertIn('FAIL estates/payments', out)

    def test_dashboards_build_from_the_estates_folder(self):  # the workflow's dashboards job
        r = subprocess.run(['sdem', 'home', '--root', 'estates', '-o', 'site'], cwd=self.repo, env=self.env, capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr); self.assertTrue((self.repo / 'site' / 'index.html').exists())

    def test_the_pin_is_the_current_release(self):
        pin = re.search(r'@v([\d.]+)\s*$', (T / 'requirements.txt').read_text(), re.M).group(1)
        version = re.search(r'^version = "([^"]+)"', (ROOT / 'pyproject.toml').read_text(), re.M).group(1)
        self.assertEqual(pin, version, 'update templates/estate-repo/requirements.txt when releasing')

    def test_the_template_is_safe(self):
        ignored = (T / '.gitignore').read_text().split('\n')
        self.assertIn('work/', ignored)
        self.assertNotIn('plantuml.com', (T / '.vscode' / 'settings.json').read_text())
        wf = (T / '.github' / 'workflows' / 'estate-ci.yml').read_text()
        self.assertIn('fetch-depth: 0', wf); self.assertNotIn('deploy-pages', wf); self.assertNotIn('gh-pages', wf)
        files = [f for f in T.rglob('*') if f.is_file()]
        self.assertFalse([f for f in files if f.suffix == '.json' and f.parent.name != '.vscode'], 'the template carries no data')


if __name__ == '__main__':
    unittest.main()
