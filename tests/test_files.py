"""Safe writes (sdem/files.py) give files normal permissions: a new file 0666 less the umask, a rewritten file its own.
mkstemp makes its temporary copy owner-only; before this was fixed every file SDEM wrote ended up owner-only."""
import os, shutil, tempfile, unittest
from pathlib import Path

from sdem.files import Batch, write_text


class SafeWriteTests(unittest.TestCase):
    def setUp(self): self.d = Path(tempfile.mkdtemp())
    def tearDown(self): shutil.rmtree(self.d, ignore_errors=True)

    @unittest.skipIf(os.name == 'nt', 'POSIX file permissions')
    def test_new_files_get_normal_permissions(self):
        umask = os.umask(0o022); 
        try:
            write_text(self.d / 'a.json', '{}'); b = Batch(); b.text(self.d / 'b.md', 'x'); b.commit()
        finally: os.umask(umask)
        for f in ('a.json', 'b.md'):
            self.assertEqual(os.stat(self.d / f).st_mode & 0o777, 0o644, f)

    @unittest.skipIf(os.name == 'nt', 'POSIX file permissions')
    def test_a_rewritten_file_keeps_its_permissions(self):
        write_text(self.d / 'a.json', '{}'); os.chmod(self.d / 'a.json', 0o600)
        write_text(self.d / 'a.json', '{"x": 1}')
        self.assertEqual(os.stat(self.d / 'a.json').st_mode & 0o777, 0o600)
        self.assertEqual((self.d / 'a.json').read_text(), '{"x": 1}')

    def test_no_temporary_files_left(self):
        write_text(self.d / 'a.json', '{}'); b = Batch(); b.json(self.d / 'c.json', {}); b.commit()
        self.assertEqual(sorted(p.name for p in self.d.iterdir()), ['a.json', 'c.json'])


if __name__ == '__main__':
    unittest.main()
