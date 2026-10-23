"""Deprecated alias of sdem.relationships (SDMM → SDEM, v0.7.0)."""
import warnings
warnings.warn("sdmm.relationships is deprecated; use sdem.relationships", DeprecationWarning, stacklevel=2)
from sdem.relationships import *  # noqa: F401,F403
from sdem.relationships import main  # noqa: F401

if __name__ == '__main__':
    raise SystemExit(main())
