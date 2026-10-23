"""Where SDEM's data lives: `schema/` and `metamodel/`.

Run from a checkout, they are the repository folders. Installed as a package (pip install), the same files are
bundled under `sdem/data/` (see `[tool.setuptools]` in pyproject.toml), so every command works from any directory.
"""
from pathlib import Path

_PKG = Path(__file__).resolve().parent
_REPO = _PKG.parent
DATA_ROOT = _REPO if (_REPO / 'schema').is_dir() and (_REPO / 'metamodel').is_dir() else _PKG / 'data'
