"""Deprecated alias of sdem.spec (SDMM → SDEM, v0.7.0)."""
import warnings
warnings.warn("sdmm.spec is deprecated; use sdem.spec", DeprecationWarning, stacklevel=2)
from sdem.spec import *  # noqa: F401,F403
from sdem.spec import main  # noqa: F401

if __name__ == '__main__':
    raise SystemExit(main())
