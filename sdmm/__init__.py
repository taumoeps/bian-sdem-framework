"""Deprecated: SDMM was renamed SDEM (Service Domain Enterprise Metamodel) in v0.7.0.

`import sdmm` and `python -m sdmm.<module>` keep working for one release and warn; use `sdem` instead.
"""
import warnings
warnings.warn("the 'sdmm' package is deprecated; use 'sdem' (Service Domain Enterprise Metamodel)", DeprecationWarning, stacklevel=2)
