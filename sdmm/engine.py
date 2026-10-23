"""Deprecated alias of sdem.inference (SDMM → SDEM, v0.7.0)."""
import warnings
warnings.warn("sdmm.engine is deprecated; use sdem.inference", DeprecationWarning, stacklevel=2)
from sdem.inference import *  # noqa: F401,F403
from sdem.inference import main  # noqa: F401

if __name__ == '__main__':
    raise SystemExit(main())
