"""Deprecated alias of sdem.graph (SDMM → SDEM, v0.7.0)."""
import warnings
warnings.warn("sdmm.graph is deprecated; use sdem.graph", DeprecationWarning, stacklevel=2)
from sdem.graph import *  # noqa: F401,F403
from sdem.graph import main  # noqa: F401

if __name__ == '__main__':
    raise SystemExit(main())
