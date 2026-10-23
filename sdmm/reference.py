"""Deprecated alias of sdem.reference (SDMM → SDEM, v0.7.0)."""
import warnings
warnings.warn("sdmm.reference is deprecated; use sdem.reference", DeprecationWarning, stacklevel=2)
from sdem.reference import *  # noqa: F401,F403
