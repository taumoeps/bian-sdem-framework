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
