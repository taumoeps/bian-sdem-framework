"""Deprecated alias of sdem.kgspec (SDMM → SDEM, v0.7.0); removed in v0.8.0."""
import warnings
warnings.warn("sdmm.kgspec is deprecated; use sdem.kgspec", DeprecationWarning, stacklevel=2)
from sdem.kgspec import *  # noqa: F401,F403
from sdem.kgspec import main  # noqa: F401

if __name__ == '__main__':
    raise SystemExit(main())
