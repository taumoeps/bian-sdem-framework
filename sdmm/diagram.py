"""Deprecated alias of sdem.diagram (SDMM → SDEM, v0.7.0); removed in v0.8.0."""
import warnings
warnings.warn("sdmm.diagram is deprecated; use sdem.diagram", DeprecationWarning, stacklevel=2)
from sdem.diagram import *  # noqa: F401,F403
from sdem.diagram import main  # noqa: F401

if __name__ == '__main__':
    raise SystemExit(main())
