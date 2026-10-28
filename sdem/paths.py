"""Where SDEM's data lives: `schema/` and `metamodel/`.

Run from a checkout, they are the repository folders. Installed as a package (pip install), the same files are
bundled under `sdem/data/` (see `[tool.setuptools]` in pyproject.toml), so every command works from any directory.
"""
from pathlib import Path

_PKG = Path(__file__).resolve().parent
_REPO = _PKG.parent
DATA_ROOT = _REPO if (_REPO / 'schema').is_dir() and (_REPO / 'metamodel').is_dir() else _PKG / 'data'
CHECKOUT = DATA_ROOT == _REPO
REPO_URL = 'https://github.com/taumoeps/bian-sdem-framework'   # also [project.urls] in pyproject.toml   # running from a clone of the repository (examples/, docs/, scripts/ present)


def repo_path(*parts):
    """A path inside the repository (examples, docs/evidence, scripts) — only in a checkout; None when installed."""
    if not CHECKOUT: return None
    p = _REPO.joinpath(*parts)
    return p if p.exists() else None


def version():
    """SDEM's version: the installed package's metadata, or pyproject.toml in a checkout."""
    try:
        from importlib.metadata import version as _v, PackageNotFoundError
        try: return _v('sdem')
        except PackageNotFoundError: pass
    except ImportError: pass
    if CHECKOUT and (_REPO / 'pyproject.toml').exists():
        import re
        m = re.search(r'^version = "([^"]+)"', (_REPO / 'pyproject.toml').read_text(encoding='utf-8'), re.M)
        if m: return m.group(1)
    return 'unknown'
