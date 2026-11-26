"""MX-56: an extension called in SDEM's own process (SDEM_EXTENSIONS_IN_PROCESS) — where no program can be started (Pyodide, in DESNRE's
workbench). Found, listed, run and asked as a program is, with the same answers, and SDEM's own state as it was after each call."""
import json, os, re, shutil, subprocess, sys, tempfile, textwrap, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'tests'))
from needs import bian as _needs_bian, EXAMPLES  # noqa: E402

FAKE = '''
import json, sys
MANIFEST = {"name": "hello-inproc", "command": "sdem-hello-inproc", "version": "0.0.1", "kind": ["checker"], "sdem": ">=0.0",
            "description": "a test extension, called in-process"}
def entry(argv):
    if argv[:1] == ["--manifest"]: print(json.dumps(MANIFEST)); return 0
    from sdem import profile
    profile.ACTIVE = {"left": "behind"}   # an extension that changes SDEM's state: SDEM puts it back
    print("hello " + " ".join(argv)); print("to stderr", file=sys.stderr)
    return 3
'''


class InProcess(unittest.TestCase):   # no sdem-bian needed: a made-up extension module
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); (self.tmp / 'sdem_hello_inproc.py').write_text(textwrap.dedent(FAKE), encoding='utf-8')
        (self.tmp / 'empty').mkdir()
        sys.path.insert(0, str(self.tmp))
        self.env = {k: os.environ.get(k) for k in ('SDEM_EXTENSIONS_IN_PROCESS', 'SDEM_EXTENSIONS_PATH')}
        os.environ['SDEM_EXTENSIONS_IN_PROCESS'] = 'sdem_hello_inproc'; os.environ['SDEM_EXTENSIONS_PATH'] = str(self.tmp / 'empty')

    def tearDown(self):
        sys.path.remove(str(self.tmp)); sys.modules.pop('sdem_hello_inproc', None)
        for k, v in self.env.items():
            if v is None: os.environ.pop(k, None)
            else: os.environ[k] = v
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_found_listed_and_run_in_this_process(self):
        from sdem import extensions as x, profile
        self.assertEqual(x.find('hello-inproc'), 'python:sdem_hello_inproc')
        self.assertEqual([(i['name'], i['program']) for i in x.installed()], [('hello-inproc', 'python:sdem_hello_inproc')])
        before = profile.ACTIVE
        r = x._call(x.find('hello-inproc'), ['a', 'b'])
        self.assertEqual((r.returncode, r.stdout, r.stderr), (3, 'hello a b\n', 'to stderr\n'))   # its exit code and output, as from a program
        self.assertIs(profile.ACTIVE, before)   # SDEM's state as it was

    def test_a_module_that_is_not_there_is_not_found_as_an_extension(self):
        from sdem import extensions as x
        os.environ['SDEM_EXTENSIONS_IN_PROCESS'] = 'sdem_no_such_module'
        self.assertEqual(x.installed(), [])
        self.assertEqual(x._call('python:sdem_no_such_module', ['--manifest']).returncode, 127)


@_needs_bian
class SameAnswers(unittest.TestCase):   # sdem-bian in-process answers as sdem-bian the program
    def test_link_check_and_search_are_the_same(self):
        empty = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, empty, True)
        out = {}
        for mode in ('program', 'in-process'):
            d = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, d, True)
            shutil.copytree(EXAMPLES / '0.20' / 'payment-initiation', d / 'ws', ignore=shutil.ignore_patterns('graph'))
            m = json.loads((d / 'ws' / 'mappings.json').read_text(encoding='utf-8')); m['mappings'] = []   # every link to propose again — BIAN's rules among them
            (d / 'ws' / 'mappings.json').write_text(json.dumps(m), encoding='utf-8')
            env = {**os.environ, 'PYTHONPATH': str(ROOT), 'PYTHONIOENCODING': 'utf-8'}
            if mode == 'in-process': env.update({'SDEM_EXTENSIONS_PATH': str(empty), 'SDEM_EXTENSIONS_IN_PROCESS': 'sdem_bian'})
            res = []
            for args in (['check', '--workspace', 'ws', '--json'], ['link', '--workspace', 'ws', '--out', 'links', '--no-review', '--json'],
                         ['bian', 'search', 'payment', 'order', '--json']):
                r = subprocess.run([sys.executable, '-m', 'sdem', *args], capture_output=True, text=True, encoding='utf-8', env=env, cwd=d)
                res.append((r.returncode, re.sub(re.escape(str(d)), '<ws>', r.stdout).replace('\\\\', '/')))
            out[mode] = res
        self.assertEqual(out['program'], out['in-process'])
        self.assertEqual([c for c, _ in out['in-process']], [0, 0, 0])
        self.assertGreater(json.loads(out['in-process'][1][1])['count'], 0)
        props = json.loads((d / 'links' / 'proposals.json').read_text(encoding='utf-8'))['mappings']   # the in-process run's
        self.assertIn('USES_DOMAIN', {p['relationship'] for p in props})   # BIAN's rules ran in this process


if __name__ == '__main__':
    unittest.main()
