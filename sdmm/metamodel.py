"""Deprecated alias of sdem.metamodel (SDMM → SDEM, v0.7.0)."""
import warnings
warnings.warn("sdmm.metamodel is deprecated; use sdem.metamodel", DeprecationWarning, stacklevel=2)
from sdem.metamodel import *  # noqa: F401,F403
