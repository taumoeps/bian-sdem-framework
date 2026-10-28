"""SDEM installed as a package works from any directory — without the repository's docs/, examples/ or scripts/.

Builds the layout `pip install .` produces (the sdem package plus the data files pyproject.toml's package-data selects,
under sdem/data/) in a temporary folder, then runs the main journeys from outside the repository. A module that finds
its files through the repository layout instead of `paths.DATA_ROOT` fails here (the audit's finding of 2026-10-29)."""
import glob, os, re, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def package_data():
    """The package-data globs of pyproject.toml: {'schema': [...], 'metamodel': [...]}."""
    text = (ROOT / 'pyproject.toml').read_text()
    out = {}
    for pkg, src in (('sdem.data.schema', 'schema'), ('sdem.data.metamodel', 'metamodel')):
        m = re.search(r'"' + re.escape(pkg) + r'"\s*=\s*\[([^\]]*)\]', text.split('[tool.setuptools.package-data]')[1])
        out[src] = re.findall(r'"([^"]+)"', m.group(1))
    return out


class InstalledLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        site = cls.tmp / 'site'
        shutil.copytree(ROOT / 'sdem', site / 'sdem', ignore=shutil.ignore_patterns('__pycache__'))
        for src, globs in package_data().items():
            for g in globs:
                for f in glob.glob(str(ROOT / src / g)):
                    dest = site / 'sdem' / 'data' / src / Path(f).relative_to(ROOT / src)
                    dest.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(f, dest)
        cls.work = cls.tmp / 'work'; cls.work.mkdir()
        shutil.copytree(ROOT / 'examples' / 'payment-initiation', cls.work / 'est', ignore=shutil.ignore_patterns('graph'))
        shutil.copytree(ROOT / 'tests' / 'fixtures' / 'confluence-folder-export', cls.work / 'export')
        cls.env = {**os.environ, 'PYTHONPATH': str(site)}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def sdem(self, *args):
        r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], cwd=self.work, env=self.env, capture_output=True, text=True, timeout=300)
        return r.returncode, r.stdout + r.stderr

    def test_data_is_the_bundled_copy(self):
        r = subprocess.run([sys.executable, '-c', 'from sdem import paths; print(paths.DATA_ROOT, paths.CHECKOUT)'], cwd=self.work, env=self.env, capture_output=True, text=True)
        self.assertIn(str(self.tmp / 'site' / 'sdem' / 'data'), r.stdout); self.assertIn('False', r.stdout)

    def test_journeys_run_installed(self):
        for args in (['--version'], ['check', '--estate', 'est'], ['build', '--estate', 'est', '--out', 'graph'], ['trace', 'CAP-PAY-010', '--graph', 'graph'],
                     ['impact', 'INF-K8S-PAY-PROD', '--change', 'retire', '--graph', 'graph'], ['matrix', '--estate', 'est'],
                     ['link', '--estate', 'est', '--out', 'links'], ['dashboard', '--estate', 'est', '-o', 'dash.html'], ['home', '--estate', 'est', '-o', 'site'],
                     ['events', '--estate', 'est'], ['transform', 'run', 'export', '-o', 'history', '--ocr', 'off'],
                     ['load', 'history', '--estate', 'hist', '--person', 'jane.architect', '--exclude', 'HIS-A3-PAYMENT-ORDER'],
                     ['designs', '--estate', 'hist', '--gaps'], ['explain', 'P-RUN-001', '--proposals', 'links/proposals.json']):
            code, out = self.sdem(*args)
            self.assertIn(code, (0, 1), f'sdem {" ".join(args)} → {code}\n{out[-800:]}')
            self.assertNotIn('Traceback', out, f'sdem {" ".join(args)}')
            self.assertNotIn('FileNotFoundError', out, f'sdem {" ".join(args)}')

    def test_maintainer_commands_say_they_need_a_checkout(self):
        code, out = self.sdem('model', 'check')
        self.assertEqual(code, 2); self.assertIn('need a checkout', out)
        code, out = self.sdem('home', '-o', 'h')
        self.assertEqual(code, 2); self.assertIn('--root', out)


if __name__ == '__main__':
    unittest.main()
