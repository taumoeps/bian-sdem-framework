"""SDEM extensions (docs/design/sdem-extensions-spec.md, EXT-15): `sdem <name>` runs an installed extension sdem-<name> with the
rest of the line untouched, and `sdem extensions` lists them. SDEM knows none by name. A made-up extension is used here."""
import json, os, stat, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

HELLO = '''#!{py}
import json, sys
if sys.argv[1:] == ['--manifest']:
    print(json.dumps({{"name": "hello", "command": "sdem-hello", "version": "0.0.1", "description": "says hello", "sdem": ">=0.18", "data": "none"}})); sys.exit(0)
print(json.dumps(sys.argv[1:])); sys.exit(7 if 'fail' in sys.argv else 0)
'''
STRAY = '#!/bin/sh\necho stray\n'   # a program called sdem-stray that is not an SDEM extension (no --manifest)


class ExtensionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bin = Path(tempfile.mkdtemp(prefix='sdem-ext-'))
        for name, text in (('sdem-hello', HELLO.format(py=sys.executable)), ('sdem-stray', STRAY)):
            p = cls.bin / name; p.write_text(text); p.chmod(p.stat().st_mode | stat.S_IEXEC)
        cls.env = {**os.environ, 'PATH': str(cls.bin) + os.pathsep + os.environ.get('PATH', ''),
                   'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}

    def sdem(self, *args):
        return subprocess.run([sys.executable, '-m', 'sdem', *args], capture_output=True, text=True, env=self.env, cwd=ROOT)

    def test_sdem_name_runs_the_extension_with_the_line_untouched(self):
        r = self.sdem('hello', 'create', 'ws', '--dry-run', '--json', '--help')   # SDEM's own --dry-run, --json and --help are not taken
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), ['create', 'ws', '--dry-run', '--json', '--help'])
        self.assertEqual(self.sdem('hello', 'fail').returncode, 7)                  # its exit code is SDEM's

    def test_sdem_extensions_lists_only_real_extensions(self):
        r = self.sdem('extensions', '--json')
        self.assertEqual(r.returncode, 0, r.stderr)
        names = [x['name'] for x in json.loads(r.stdout)['items']]
        self.assertIn('hello', names); self.assertNotIn('stray', names)
        self.assertIn('says hello', self.sdem('extensions').stdout)

    def test_a_stray_program_or_an_unknown_command_is_not_run(self):
        for name in ('stray', 'nothing-here'):
            r = self.sdem(name)
            self.assertEqual(r.returncode, 2, name); self.assertIn(f"unknown command '{name}'", r.stderr); self.assertNotIn('stray', r.stdout)

    def test_sdems_own_commands_and_programs_win(self):
        from sdem import extensions
        self.assertIsNone(extensions.find('graph'))                                 # sdem-graph is SDEM's own program, never an extension
        self.assertEqual(self.sdem('releases', '--since', '0.18.0').returncode, 0)  # a command of SDEM's own is SDEM's


if __name__ == '__main__':
    unittest.main()
