"""Deprecated alias of sdem.validate (SDMM → SDEM, v0.7.0)."""
import warnings
warnings.warn("sdmm.validate is deprecated; use sdem.validate", DeprecationWarning, stacklevel=2)
from sdem.validate import *  # noqa: F401,F403
from sdem.validate import main  # noqa: F401

if __name__ == '__main__':
    raise SystemExit(main())
