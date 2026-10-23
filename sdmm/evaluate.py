"""Deprecated alias of sdem.evaluate (SDMM → SDEM, v0.7.0); removed in v0.8.0."""
import warnings
warnings.warn("sdmm.evaluate is deprecated; use sdem.evaluate", DeprecationWarning, stacklevel=2)
from sdem.evaluate import *  # noqa: F401,F403
from sdem.evaluate import main  # noqa: F401

if __name__ == '__main__':
    raise SystemExit(main())
