"""SDEM's own documents are made from its core alone (BX-15, 0.22): BIAN's layer keeps its place, nothing of BIAN is read — the same with
sdem-bian installed or not (sdem model regenerate|check). A test that renders one and compares it with the kept copy renders it the same way:
call enter() before (setUpModule / setUpClass) and leave() after."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def enter():
    from sdem import parts, profile
    profile.deactivate(); parts.core_only_content()


def leave():
    from sdem import parts
    parts.leave_core_docs()
