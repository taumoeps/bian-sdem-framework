"""A Python for running SDEM with no extension beside it — a virtual environment with nothing installed (no pip), SDEM from the checkout
on PYTHONPATH. SDEM looks for extensions first in the folder its own Python runs from (EXT-15), so a test that needs an extension present or
absent runs SDEM with this one and decides it with PATH alone."""
import os, venv
from pathlib import Path


def bare_python(folder):
    folder = Path(folder) / 'bare-python'
    if not folder.exists():
        venv.EnvBuilder(with_pip=False, symlinks=os.name != 'nt').create(folder)
    return folder / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def bian_dirs():
    """The folders an installed sdem-bian is found in — the Python's own folder first, then PATH (EXT-15)."""
    import shutil, sys
    out = []
    for p in [str(Path(sys.executable).parent), *os.environ.get('PATH', '').split(os.pathsep)]:
        if p and p not in out and shutil.which('sdem-bian', path=p): out.append(p)
    return out
