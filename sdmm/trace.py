"""Deprecated alias of sdem.trace (SDMM → SDEM, v0.7.0)."""
import warnings
warnings.warn("sdmm.trace is deprecated; use sdem.trace", DeprecationWarning, stacklevel=2)
from sdem.trace import *  # noqa: F401,F403
from sdem.trace import main  # noqa: F401

if __name__ == '__main__':
    raise SystemExit(main())
