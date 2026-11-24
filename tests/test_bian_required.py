"""R-D2 (the 0.22 plan, step 4a): BIAN comes only from the sdem-bian extension. Without it installed, a design that uses BIAN — a BIAN layer
file, or a profile that includes ext:bian — is refused by every command, with what to install; a design that does not is a core design,
and a new design is one. Run here with no sdem-bian on PATH, whatever is installed on this machine. Synthetic data only."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from bare_python import bare_python, bian_dirs  # noqa: E402
BANK = ROOT / 'examples' / '0.20' / 'payment-initiation'


def without_bian():
    path = [p for p in os.environ.get('PATH', '').split(os.pathsep) if p and p not in bian_dirs()]
    return {**os.environ, 'PYTHONPATH': str(ROOT), 'PYTHONIOENCODING': 'utf-8', 'PATH': os.pathsep.join(path)}


class BianRequired(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp()); cls.env = without_bian(); cls.py = bare_python(cls.tmp)   # its own folder holds no sdem-bian

    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.tmp, ignore_errors=True)

    def sdem(self, *args):
        r = subprocess.run([str(self.py), '-m', 'sdem', *map(str, args)], cwd=self.tmp, capture_output=True, text=True, encoding='utf-8', env=self.env)
        return r.returncode, r.stdout, r.stderr

    def test_rd2_a_design_with_a_bian_layer_is_refused_by_every_command(self):
        for cmd in (['status'], ['check'], ['aid', '--person', 'steven', '--dry-run'], ['link', '--out', self.tmp / 'links']):
            code, _, err = self.sdem(*cmd, '--workspace', BANK)
            self.assertEqual(code, 2, (cmd, err))
            self.assertIn('uses the BIAN extension — install sdem-bian', err, cmd)

    def test_rd2_a_profile_that_includes_ext_bian_is_refused(self):
        ws = self.tmp / 'included'
        self.assertEqual(self.sdem('new', '--workspace', ws, '--person', 'steven')[0], 0)
        p = json.loads((ws / 'sdem-profile.json').read_text(encoding='utf-8')); p['includes'] = [*p.get('includes', []), 'ext:bian']
        (ws / 'sdem-profile.json').write_text(json.dumps(p), encoding='utf-8')
        code, _, err = self.sdem('status', '--workspace', ws)
        self.assertEqual(code, 2, err); self.assertIn('its profile includes ext:bian', err)

    def test_rd2_a_banking_baseline_is_refused_when_starting_a_design(self):
        code, _, err = self.sdem('new', '--workspace', self.tmp / 'bank', '--person', 'steven', '--example', 'payment-initiation')
        self.assertEqual(code, 2, err); self.assertIn('install sdem-bian', err)
        self.assertFalse((self.tmp / 'bank').exists())

    def test_rd2_a_new_design_is_a_core_one_and_works(self):
        ws = self.tmp / 'core'
        code, out, err = self.sdem('new', '--workspace', ws, '--person', 'steven', '--json')
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)['bian']['selection'], 'none')
        self.assertFalse(any((ws / f).exists() for f in ('bian.json', 'a2-service-domain.json')))
        code, _, err = self.sdem('check', '--workspace', ws)
        self.assertEqual(code, 0, err)


if __name__ == '__main__':
    unittest.main()
