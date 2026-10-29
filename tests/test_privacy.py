"""PRIVACY.md's claims about the software, checked on every push: SDEM imports no networking library, starts only git and
on-device text recognition, and the HTML pages it writes load nothing from the internet."""
import ast, contextlib, io, re, shutil, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem import cli  # noqa: E402

NETWORK = {'urllib.request', 'http', 'http.client', 'http.server', 'socket', 'socketserver', 'ssl', 'ftplib', 'smtplib', 'poplib',
           'imaplib', 'telnetlib', 'xmlrpc', 'webbrowser', 'requests', 'httpx', 'aiohttp', 'urllib3'}
PROGRAMS = {'git', 'osascript', 'tesseract'}   # PRIVACY.md §2


def sdem(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try: code = cli.main([str(a) for a in argv])
        except SystemExit as e: code = e.code if isinstance(e.code, int) else 1
    return code


class PrivacyTests(unittest.TestCase):
    def test_no_networking_library(self):
        for f in sorted((ROOT / 'sdem').rglob('*.py')):
            for node in ast.walk(ast.parse(f.read_text(encoding='utf-8'))):
                names = [a.name for a in node.names] if isinstance(node, ast.Import) else [m for a in node.names for m in (node.module or '', f'{node.module}.{a.name}')] if isinstance(node, ast.ImportFrom) else []
                for n in names:
                    self.assertFalse(n in NETWORK or n.split('.')[0] in NETWORK - {'http'} or n.startswith('http.'), f'{f.name} imports {n}')

    def test_only_the_named_programs_are_started(self):
        started = set()
        for f in (ROOT / 'sdem').rglob('*.py'):
            src = f.read_text(encoding='utf-8')
            self.assertNotRegex(src, r'os\.(system|popen|exec\w*|spawn\w*)\(', f.name)
            started |= set(re.findall(r"subprocess\.\w+\(\s*\[\s*'([\w.-]+)'", src))
            self.assertEqual(len(re.findall(r'subprocess\.\w+\(', src)), len(re.findall(r"subprocess\.\w+\(\s*\[\s*'", src)),
                             f'{f.name}: every program SDEM starts is named literally')
        self.assertLessEqual(started, PROGRAMS)

    def test_pages_load_nothing_from_the_internet(self):
        tmp = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, tmp, True)
        estate = ROOT / 'examples' / 'payment-initiation'
        self.assertEqual(sdem('build', '--estate', estate, '--out', tmp / 'g'), 0)
        self.assertEqual(sdem('view', '--graph', tmp / 'g'), 0)
        self.assertEqual(sdem('dashboard', '--estate', estate, '-o', tmp / 'dash.html'), 0)
        self.assertEqual(sdem('home', '--estate', estate, '-o', tmp / 'site'), 0)
        pages = list(tmp.rglob('*.html')); self.assertGreaterEqual(len(pages), 4)
        for p in pages:
            html = p.read_text(encoding='utf-8')
            self.assertIsNone(re.search(r'''(src|href|action)\s*=\s*["']?(https?:)?//|url\(\s*["']?(https?:)?//|@import''', html, re.I), p.name)
            self.assertIsNone(re.search(r'\bfetch\(|XMLHttpRequest|sendBeacon|new WebSocket|new EventSource', html), p.name)

    def test_no_dependencies(self):   # standard library only — nothing fetched from a package index at run time
        self.assertRegex((ROOT / 'pyproject.toml').read_text(encoding='utf-8'), r'(?m)^dependencies = \[\]$')


if __name__ == '__main__':
    unittest.main()
