import os
"""Tests that need the sdem-bian extension installed (SDEM 0.22, BX-15): BIAN's designs, code and data are its own. Without it they are
skipped — SDEM's core suite runs, and passes, with no sdem-bian (CI's core job); with it, everything runs.

    from needs import bian
    @bian
    class MyTests(unittest.TestCase): …
"""
import importlib.util, sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bare_python import bian_dirs  # noqa: E402


def installed():
    return bool(bian_dirs()) and importlib.util.find_spec('sdem_bian') is not None


bian = unittest.skipUnless(installed(), 'needs sdem-bian installed (BIAN is its own since SDEM 0.22, BX-15)')


def _merged_examples():
    """SDEM's examples and the installed sdem-bian's (0.22, R-D6: the banking designs moved there), as one folder — linked where the system
    allows, copied where it does not (Windows without the right) — so a test reads `EXAMPLES / 'payment-initiation'` as it read the repository's."""
    import atexit, os, shutil, tempfile
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    from sdem import parts
    out = Path(tempfile.mkdtemp(prefix='sdem-examples-')); atexit.register(shutil.rmtree, out, True)

    def put(src, dst):
        if dst.exists(): return
        try: os.symlink(src, dst, target_is_directory=src.is_dir())
        except OSError: (shutil.copytree if src.is_dir() else shutil.copy2)(src, dst)

    for r in parts.example_roots():
        if not r.is_dir(): continue
        for c in sorted(r.iterdir()):
            if c.name == '0.20' and c.is_dir():
                (out / '0.20').mkdir(exist_ok=True)
                for cc in sorted(c.iterdir()): put(cc, out / '0.20' / cc.name)
            else: put(c, out / c.name)
    return out


EXAMPLES = _merged_examples()
os.environ.setdefault('SDEM_EXAMPLES_DIR', str(EXAMPLES))   # scripts the tests run (use cases, golden capture, agent evals) read it too
