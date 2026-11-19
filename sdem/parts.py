"""BIAN as a horizontal extension (docs/design/sdem-bian-extension-spec.md, BX-01…BX-51): whether the A2 Service Domain layer — its
types, within-layer rules, the link types and inference rules that touch it — is part of the metamodel for the work at hand.

Off (BX-13) only where a person chose it — `sdem new --core`, or `sdem profile exclude ext:bian` — recorded in workspace.json
(`core_only`); including `ext:bian` turns it on again. Every other workspace is on, as in 0.19 — with an A2 file or without one (AID
brings service domains in from the catalogue) — and so is the work outside a workspace (BX-10…BX-12)."""
from pathlib import Path

A2, A2_FILE, EXT_BIAN = 'A2', 'a2-service-domain.json', 'ext:bian'
_STATE = {'bian': True, 'why': 'no workspace (BX-12)'}


def bian_on(): return _STATE['bian']


def why(): return _STATE['why']


def a2(t): return str(t or '').startswith('A2.')


def _set(on, why):
    changed = _STATE['bian'] != bool(on)
    _STATE.update(bian=bool(on), why=why)
    if changed:
        from . import conformance
        try: conformance.model.cache_clear()
        except AttributeError: pass


def included(merged):
    return any(a.get('name') == EXT_BIAN for a in ((merged or {}).get('aspects') or []))


def for_workspace(folder, merged=None):
    """BX-10, BX-11, BX-13: decide for this workspace — before its profile is resolved, so a pack's link types that require BIAN (BX-50)
    are kept or left out by the right answer: the includes are read from the profile file itself."""
    import json
    f = Path(folder) / 'sdem-profile.json'
    try: raw = json.loads(f.read_text(encoding='utf-8')).get('includes') or [] if f.exists() else []
    except (OSError, ValueError): raw = []
    if included(merged) or EXT_BIAN in raw: _set(True, 'the profile includes ext:bian (BX-10)'); return
    try: core = json.loads((Path(folder) / 'workspace.json').read_text(encoding='utf-8')).get('core_only') is True
    except (OSError, ValueError): core = False
    if core: _set(False, 'a person chose a core-only design — sdem new --core or sdem profile exclude ext:bian (BX-13)'); return
    _set(True, 'every workspace is a BIAN design unless a person chose otherwise, as in 0.19 — on until a person includes ext:bian (BX-11)')


def reset(): _set(True, 'no workspace (BX-12)')


def keep(rows, ends):
    """Rows of a registry or rule set that stay with BIAN off: those whose ends name no A2 type. `ends(row)` gives the types it names."""
    if bian_on(): return rows
    return [r for r in rows if not any(a2(t) for t in ends(r))]
