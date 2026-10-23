"""Deprecated alias of sdem.structure (SDMM → SDEM, v0.7.0); removed in v0.8.0."""
import warnings
warnings.warn("sdmm.structure is deprecated; use sdem.structure", DeprecationWarning, stacklevel=2)
from sdem.structure import *  # noqa: F401,F403
from sdem.structure import main  # noqa: F401

if __name__ == '__main__':
    raise SystemExit(main())
