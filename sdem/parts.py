"""BIAN as a horizontal extension (docs/design/sdem-bian-extension-spec.md, BX-01…BX-51): whether the A2 Service Domain layer — its
types, within-layer rules, the link types and inference rules that touch it — is part of the metamodel for the work at hand.

Off (BX-13) only where a person chose it — `sdem new --core`, or `sdem profile exclude ext:bian` — recorded in workspace.json
(`core_only`); including `ext:bian` turns it on again. Every other workspace is on, as in 0.19 — with an A2 file or without one (AID
brings service domains in from the catalogue) — and so is the work outside a workspace (BX-10…BX-12)."""
from .identity import load as _jload  # DL-11: a design's files read through one boundary (docs/design/sdem-data-layer-spec.md)
from .identity import T as _T, layer as _L  # ST-01…ST-05: layers and types by id (docs/design/sdem-stable-identity-spec.md)
from pathlib import Path

A2_FILE, EXT_BIAN = 'a2-service-domain.json', 'ext:bian'


def a2_code():
    """BIAN's layer code as read now (A2 where it is on; DL-06)."""
    return _L('bian')
_STATE = {'bian': None, 'why': 'no workspace (BX-12)', 'migrated': False}   # bian None: decided when first asked (whether sdem-bian is installed)

LAYER_FILES = ('bian.json', A2_FILE)   # BIAN's layer file in the 0.20 form and in 0.19's


def bian_on():
    if _STATE['bian'] is None:
        import os
        if os.environ.get('SDEM_CORE_DOCS'): _STATE.update(bian=True, content=False, why="SDEM's own documents: the core's content, BIAN's place kept (BX-15)")   # and in every process they start
        else: _STATE['bian'] = usable()
    return _STATE['bian']


def usable():
    """0.22, R-D2: is sdem-bian installed and usable here (it names its data and supports this SDEM)? BIAN comes only from it."""
    p = package()
    return bool(p and p.get('data'))


def uses_bian(folder):
    """R-D2: does the design in this folder use BIAN — a BIAN layer file (in either form), here or in its sdem/ folder?"""
    f = Path(folder)
    return any((d / n).is_file() for d in (f, f / 'sdem') for n in LAYER_FILES)


def missing(what):
    """R-D2: the refusal for a design that uses BIAN where sdem-bian is not installed (or not usable) — every command gives it."""
    from .errors import SdemError
    p = package() or {}
    why = f" — the installed one is not usable: {p['refused']}" if p.get('refused') else ''
    return SdemError('refused', f'{what} uses the BIAN extension — install sdem-bian{why}',
                     hint='pip install sdem-bian (from the sdem-extensions repository); or start a core design: sdem new --core')


def migrated():
    """DL-10…DL-12: is the workspace at hand migrated (workspace.json "names": "ids")? It decides the files' names and what they store."""
    return _STATE['migrated']


def _set_form(m):
    if _STATE['migrated'] != bool(m):
        _STATE['migrated'] = bool(m)
        from . import identity; identity.changed()


def why(): return _STATE['why']


def a2(t): return str(t or '').startswith((_L('bian') + '.'))


def _set(on, why):
    changed = _STATE['bian'] != bool(on)
    _STATE.update(bian=bool(on), why=why)
    if changed:
        from . import identity; identity.changed()   # DL-06: the layers in use changed — every computed name too
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
    try: raw = _jload(f).get('includes') or [] if f.exists() else []
    except (OSError, ValueError): raw = []
    from .identity import _ids_folder
    _set_form(_ids_folder(str(Path(folder).resolve())))   # DL-10…DL-12: the workspace's form, before anything is read
    import os
    if os.environ.get('SDEM_CORE_DOCS'): _STATE['content'] = False; _set(True, "SDEM's own documents (BX-15)"); return   # an example read for them: the core's content too
    if included(merged) or EXT_BIAN in raw:
        if not usable(): raise missing(f'{folder}: the design (its profile includes ext:bian)')
        _set(True, 'the profile includes ext:bian (BX-10)'); return
    try: core = _jload(Path(folder) / 'workspace.json').get('core_only') is True
    except (OSError, ValueError): core = False
    if core: _set(False, 'a person chose a core-only design — sdem new --core or sdem profile exclude ext:bian (BX-13)'); return
    if uses_bian(folder):
        if not usable(): raise missing(f'{folder}: the design (it has a BIAN layer)')
        _set(True, 'the design has a BIAN layer, and sdem-bian is installed (BX-11, R-D2)'); return
    if usable(): _set(True, 'every workspace is a BIAN design where sdem-bian is installed, unless a person chose otherwise (BX-11)'); return
    _set(False, 'a core design: no BIAN layer, its profile does not include ext:bian, and sdem-bian is not installed (0.22, R-D2)')


def reset():
    import os
    if os.environ.get('SDEM_CORE_DOCS'): _STATE['content'] = False; _set(True, "SDEM's own documents (BX-15)"); _set_form(False); return
    _set(usable(), 'no workspace (BX-12)'); _set_form(False)


def keep(rows, ends):
    """Rows of a registry or rule set that stay with BIAN off: those whose ends name no A2 type. `ends(row)` gives the types it names."""
    if bian_on(): return rows
    return [r for r in rows if not any(a2(t) for t in ends(r))]


# ---- step 2 of 0.20: BIAN in its own package, sdem-bian (docs/design/sdem-bian-package-spec.md, BP-01…BP-11)
PKG_FILES = {'metamodel': A2_FILE, 'within': 'within-layer-rules.json', 'link_types': 'link-types.json', 'rules': 'inference-rules.json'}
PKG_OPTIONAL = {'attributes': 'attributes.json', 'order': 'order.json', 'notation': 'notation.json', 'viewpoints': 'viewpoints.json', 'viewpoint_plates': 'viewpoint-plates.json'}   # order (MX-55): where each of its rows sits among the core's   # a package built before carries none: then SDEM's own copy is used (BP-10)
CATALOGUE = 'catalogue'   # the BIAN catalogue, its inferences and licence, in the package's data folder


def bian_constraint(c): return c.get('level') == a2_code() or a2(c.get('source_type')) or a2(c.get('target_type'))


def bian_link(r): return a2(r.get('source_type')) or a2(r.get('target_type'))


def bian_rule(m):
    import json
    return (_L('bian') + '.') in json.dumps(m)


_PKG = {}


def package():
    """BP-05: the installed sdem-bian, when it names its data and supports this SDEM — {'version', 'data', 'manifest'}; None when not
    installed; {'refused': why} when installed but not usable (then the built-in copy is used and `sdem extensions` says why)."""
    if 'v' in _PKG: return _PKG['v']
    from . import extensions as x
    prog, res = x.find('bian'), None
    if prog:
        m = x.manifest(prog) or {}
        from .paths import version
        from .upgrade import satisfies
        d = Path(m.get('bian_data') or '')
        if not m.get('bian_data') or not all((d / f).is_file() for f in PKG_FILES.values()) or not (d / CATALOGUE).is_dir():
            res = {'refused': f"sdem-bian {m.get('version', '')} does not name a complete data folder — reinstall it"}
        elif not {'link', 'aid-phases'} <= set(m.get('infers') or []) or not m.get('commands'):   # BX-15 (0.22): BIAN's rules, its part of sdem aid and its commands — all its own now
            res = {'refused': f"sdem-bian {m.get('version', '')} predates SDEM 0.22 (it gives no BIAN rules or part of sdem aid) — upgrade it to 1.2 or later"}
        elif m.get('sdem') and version() != 'unknown' and not satisfies(version(), m['sdem']):   # a checkout run from elsewhere knows no version: not a reason to refuse
            res = {'refused': f"sdem-bian {m.get('version', '')} supports SDEM {m['sdem']}; this is SDEM {version()}"}
        else:
            res = {'version': m.get('version', ''), 'data': d, 'manifest': m,
                   'code': bool(m.get('commands')) and api_supported(m.get('api'))}   # ST-22: it runs `sdem bian` with its own code
    _PKG['v'] = res
    return res


def identity_changed():
    from . import identity; identity.changed()
    from . import conformance   # its model is built from the rows in use — BIAN's or not, the core's alone or not
    try: conformance.model.cache_clear()
    except AttributeError: pass


def leave_core_docs():
    """The end of SDEM's own documents' core-only mode: BIAN's content as before, decided afresh."""
    import os
    os.environ.pop('SDEM_CORE_DOCS', None); _STATE.pop('content', None); _STATE['bian'] = None
    identity_changed()


def core_only_content():
    """SDEM's own documents (sdem model regenerate|check, BX-15): the core's content in SDEM's own numbering — BIAN's layer keeps its
    place (A2 in 0.19's numbering) but nothing of BIAN is read, so they are the same with sdem-bian installed or not."""
    import os
    os.environ['SDEM_CORE_DOCS'] = '1'   # the processes they start (sdem <command> --help) too
    _STATE['content'] = False
    _set(True, "SDEM's own documents: the core's content, BIAN's place kept (BX-15)")
    identity_changed()


def _pkg_data():
    if _STATE.get('content') is False: return None
    p = package()
    if not (p and p.get('data')): return None
    from . import identity
    key = ('data', identity._VERSION[0])   # its names read in the numbering now in use (DL-22): a workspace in the 0.20 form numbers Application A4
    if key not in _PKG:
        for k in [k for k in _PKG if isinstance(k, tuple) and k[0] == 'data']: del _PKG[k]
        _PKG[key] = {**{k: _jload(p['data'] / f) for k, f in PKG_FILES.items()}, **{k: _jload(p['data'] / f) for k, f in PKG_OPTIONAL.items() if (p['data'] / f).is_file()}}
    return _PKG[key]


def splice(rows, is_bian, key, kind):
    """BP-02: SDEM's rows with BIAN's from the installed package — in SDEM's order: each BIAN row is replaced by the package's row of
    the same key; a row the package adds comes after; one it drops is gone. Without the package (BP-10), the rows as they are."""
    d = _pkg_data()
    if d is None or not bian_on() or kind not in d: return rows   # a package without this kind (built before it carried one): SDEM's own rows
    anchors = ((d.get('order') or {}).get(kind))
    if isinstance(anchors, list) and len(anchors) == len(d[kind]):   # MX-55: each of its rows after the core row it names — the core's own order kept
        FIRST = object(); after = {}
        for row, a in zip(d[kind], anchors): after.setdefault(FIRST if a is None else key(a), []).append(row)
        out = list(after.pop(FIRST, []))
        for r in rows:
            if is_bian(r): continue   # a core file that still holds BIAN's own rows (before 0.22): the package's stand in for them
            out.append(r); out += after.pop(key(r), [])
        return out + [x for xs in after.values() for x in xs]   # a row whose core row is gone: at the end
    by = {key(r): r for r in d[kind]}; used, out = set(), []
    for r in rows:
        if not is_bian(r): out.append(r)
        elif key(r) in by: out.append(by[key(r)]); used.add(key(r))
    return out + [r for r in d[kind] if key(r) not in used]


def metamodel_doc(doc=None):
    """BP-02, BX-15: the A2 metamodel file — the installed sdem-bian's (SDEM ships none since 0.22); `doc` where none is installed."""
    d = _pkg_data()
    return d['metamodel'] if d is not None and bian_on() else doc


def catalogue_dir():
    """BP-02: the folder of the BIAN catalogue (base-<release>.json, inferences-<release>.json, LICENSE) — the package's when installed."""
    p = package()
    if p and p.get('data'): return p['data'] / CATALOGUE
    raise missing("BIAN's catalogue")   # BX-15 (0.22): it ships only with sdem-bian


def api_supported(spec):
    """ST-20: does this SDEM's sdem.api satisfy an extension's "api" range? No range — it does not use sdem.api."""
    if not spec: return False
    from .api import VERSION
    from .upgrade import satisfies
    return satisfies(VERSION, spec)
