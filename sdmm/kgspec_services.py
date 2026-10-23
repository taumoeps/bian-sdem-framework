"""Deprecated alias of sdem.kgspec_services (SDMM → SDEM, v0.7.0); removed in v0.8.0."""
import warnings
warnings.warn("sdmm.kgspec_services is deprecated; use sdem.kgspec_services", DeprecationWarning, stacklevel=2)
from sdem.kgspec_services import *  # noqa: F401,F403
