"""Deprecated alias of sdem.diff (SDMM → SDEM, v0.7.0); removed in v0.8.0."""
import warnings
warnings.warn("sdmm.diff is deprecated; use sdem.diff", DeprecationWarning, stacklevel=2)
from sdem.diff import *  # noqa: F401,F403
from sdem.diff import main  # noqa: F401

if __name__ == '__main__':
    raise SystemExit(main())
