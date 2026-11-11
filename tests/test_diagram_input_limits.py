"""Damaged, oversized or unexpected diagram files (PR-28a): `sdem pattern extract` refuses them with a plain error — never a traceback,
never reading without limit, never writing anything — synthetic files only."""
import base64, io, os, shutil, subprocess, sys, tempfile, unittest, zipfile, zlib
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem import patterns  # noqa: E402

SAMPLES = ROOT / 'examples' / 'profiles' / 'patterns' / 'diagrams'


def drawio_compressed(xml_bytes):
    c = zlib.compressobj(9, zlib.DEFLATED, -15); raw = c.compress(xml_bytes) + c.flush()
    return f'<mxfile><diagram name="p">{base64.b64encode(raw).decode()}</diagram></mxfile>'


def vsdx(parts):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, data in parts.items(): z.writestr(name, data)
    return buf.getvalue()


class DiagramInputTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, self.tmp, True)

    def refused(self, name, data, *say):
        f = self.tmp / name; f.write_bytes(data if isinstance(data, bytes) else data.encode())
        before = sorted(p.name for p in self.tmp.rglob('*'))
        with self.assertRaises(ValueError) as cm: patterns.read(f)
        for s in say: self.assertIn(s, str(cm.exception))
        self.assertEqual(sorted(p.name for p in self.tmp.rglob('*')), before)   # nothing written beside it
        return str(cm.exception)

    def test_the_samples_still_read(self):
        for f in sorted(SAMPLES.glob('secure-api-edge.*')):
            self.assertTrue(patterns.read(f)['shapes'], f.name)

    def test_damaged_files_are_refused_plainly(self):
        self.refused('a.vsdx', b'not a zip at all', 'not a diagram SDEM can read', 'BadZipFile')
        self.refused('b.vsdx', vsdx({'visio/document.xml': '<x/>'}), 'not a diagram SDEM can read', 'KeyError')   # no pages
        self.refused('c.vsdx', vsdx({'visio/pages/pages.xml': '<Pages', 'visio/pages/_rels/pages.xml.rels': '<x/>'}), 'ParseError')
        self.refused('d.drawio', '<mxfile><diagram>%%%not base64%%%</diagram></mxfile>', 'd.drawio')
        self.refused('e.drawio', '<mxfile><diagram>' + base64.b64encode(b'not deflate data').decode() + '</diagram></mxfile>', 'not a diagram SDEM can read')
        self.refused('f.drawio', '<mxfile><diagram', 'ParseError')
        self.refused('g.txt', 'hello', 'SDEM reads draw.io')

    def test_a_compressed_page_that_inflates_too_far_is_refused(self):
        bomb = drawio_compressed(b'<mxGraphModel>' + b' ' * 200_000 + b'</mxGraphModel>')   # small on disk, large inflated
        with mock.patch.object(patterns, 'MAX_BYTES', 100_000):
            self.refused('bomb.drawio', bomb, 'inflates to more than 100000 bytes')

    def test_an_oversized_file_or_part_is_not_read(self):
        with mock.patch.object(patterns, 'MAX_BYTES', 1_000):
            self.refused('big.puml', '@startuml\n' + 'a -> b\n' * 500 + '@enduml\n', 'larger than SDEM reads')
        big = vsdx({'visio/pages/pages.xml': '<Pages>' + ' ' * 5_000 + '</Pages>', 'visio/pages/_rels/pages.xml.rels': '<x/>'})   # compresses below the file limit
        with mock.patch.object(patterns, 'MAX_BYTES', 2_000):
            self.assertLess(len(big), 2_000)
            self.refused('part.vsdx', big, 'inside the .vsdx — larger than SDEM reads')

    def test_a_path_in_the_archive_is_never_written(self):   # entries are read in memory by name; nothing is extracted
        self.refused('t.vsdx', vsdx({'../../escape.txt': 'x', 'visio/pages/pages.xml': '<Pages', 'visio/pages/_rels/pages.xml.rels': '<x/>'}), 'ParseError')
        self.assertFalse((self.tmp.parent / 'escape.txt').exists())

    def test_the_command_says_error_not_a_traceback(self):
        f = self.tmp / 'broken.vsdx'; f.write_bytes(b'PK\x03\x04 damaged')
        env = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}
        r = subprocess.run([sys.executable, '-m', 'sdem', 'pattern', 'extract', '--from', str(f), '--workspace', str(ROOT / 'examples' / 'payment-initiation'),
                            '--id', 'PAT-X', '--owner', 'pattern.owner', '--anchor', 'Application', '--profile', str(ROOT / 'examples' / 'profiles' / 'bank-with-standards.json')],
                           capture_output=True, text=True, env=env, cwd=self.tmp)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr); self.assertIn('ERROR:', r.stderr); self.assertNotIn('Traceback', r.stderr)


if __name__ == '__main__':
    unittest.main()
