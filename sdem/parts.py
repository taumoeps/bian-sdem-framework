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
_STATE = {'bian': True, 'why': 'no workspace (BX-12)', 'migrated': False}


def bian_on(): return _STATE['bian']


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
    if included(merged) or EXT_BIAN in raw: _set(True, 'the profile includes ext:bian (BX-10)'); return
    try: core = _jload(Path(folder) / 'workspace.json').get('core_only') is True
    except (OSError, ValueError): core = False
    if core: _set(False, 'a person chose a core-only design — sdem new --core or sdem profile exclude ext:bian (BX-13)'); return
    _set(True, 'every workspace is a BIAN design unless a person chose otherwise, as in 0.19 — on until a person includes ext:bian (BX-11)')


def reset(): _set(True, 'no workspace (BX-12)'); _set_form(False)


def keep(rows, ends):
    """Rows of a registry or rule set that stay with BIAN off: those whose ends name no A2 type. `ends(row)` gives the types it names."""
    if bian_on(): return rows
    return [r for r in rows if not any(a2(t) for t in ends(r))]


# ---- step 2 of 0.20: BIAN in its own package, sdem-bian (docs/design/sdem-bian-package-spec.md, BP-01…BP-11)
PKG_FILES = {'metamodel': A2_FILE, 'within': 'within-layer-rules.json', 'link_types': 'link-types.json', 'rules': 'inference-rules.json'}
PKG_OPTIONAL = {'attributes': 'attributes.json'}   # a package built before carries none: then SDEM's own copy is used (BP-10)
CATALOGUE = 'catalogue'   # the BIAN catalogue, its inferences and licence, in the package's data folder


def bian_constraint(c): return c.get('level') == a2_code() or a2(c.get('source_type')) or a2(c.get('target_type'))


def bian_link(r): return a2(r.get('source_type')) or a2(r.get('target_type'))


def bian_rule(m):
    import json
    return (_L('bian') + '.') in json.dumps(m)


def builtin_data():
    """BP-02, BP-10: BIAN's data as SDEM ships it — what the package carries, and the fallback when it is not installed."""
    import json
    from .paths import DATA_ROOT
    rd = lambda *p: _jload(DATA_ROOT.joinpath(*p))
    return {'metamodel': rd('metamodel', A2_FILE),
            'within': [c for c in rd('metamodel', 'level-relationships.json')['constraints'] if bian_constraint(c)],
            'link_types': [r for r in rd('schema', 'relationship-types.json')['relationships'] if bian_link(r)],
            'rules': [m for m in rd('metamodel', 'relationship-rules.json')['mappings'] if bian_rule(m)],
            'attributes': [x for x in rd('metamodel', 'entity-attributes.json')['attributes'] if a2(x.get('entity'))]}   # BIAN's attributes, with BIAN


def write_package_data(pkg):
    """sdem-bian's package folder (sdem_bian/) from SDEM's built-in copy (scripts/bian_package.py): data/ — the four files and the
    catalogue, verbatim — and the `sdem bian` commands written against sdem.api (ST-22). Returns the files, relative to the folder."""
    import json, shutil
    from .paths import DATA_ROOT
    pkg = Path(pkg); out = pkg / 'data'; out.mkdir(parents=True, exist_ok=True)
    for k, v in builtin_data().items():
        (out / {**PKG_FILES, **PKG_OPTIONAL}[k]).write_bytes((json.dumps(v, indent=1, ensure_ascii=False) + '\n').encode('utf-8'))   # LF on every platform (BP-11)
    for f, src in package_code().items():   # ST-22: the commands, beside the data folder (sdem_bian/<file>)
        (pkg / f).write_bytes(src.encode('utf-8'))
    if (out / CATALOGUE).exists(): shutil.rmtree(out / CATALOGUE)
    shutil.copytree(DATA_ROOT / 'bian', out / CATALOGUE)
    return sorted([*(f'data/{p.relative_to(out).as_posix()}' for p in out.rglob('*') if p.is_file()), *CODE_FILES])


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
        elif m.get('sdem') and not satisfies(version(), m['sdem']):
            res = {'refused': f"sdem-bian {m.get('version', '')} supports SDEM {m['sdem']}; this is SDEM {version()}"}
        else:
            res = {'version': m.get('version', ''), 'data': d, 'manifest': m,
                   'code': bool(m.get('commands')) and api_supported(m.get('api'))}   # ST-22: it runs `sdem bian` with its own code
    _PKG['v'] = res
    return res


def _pkg_data():
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
    by = {key(r): r for r in d[kind]}; used, out = set(), []
    for r in rows:
        if not is_bian(r): out.append(r)
        elif key(r) in by: out.append(by[key(r)]); used.add(key(r))
    return out + [r for r in d[kind] if key(r) not in used]


def metamodel_doc(doc):
    """BP-02: the A2 metamodel file — the package's when installed."""
    d = _pkg_data()
    return d['metamodel'] if d is not None and bian_on() else doc


def catalogue_dir():
    """BP-02: the folder of the BIAN catalogue (base-<release>.json, inferences-<release>.json, LICENSE) — the package's when installed."""
    from .paths import DATA_ROOT
    p = package()
    return p['data'] / CATALOGUE if p and p.get('data') else DATA_ROOT / 'bian'


def api_supported(spec):
    """ST-20: does this SDEM's sdem.api satisfy an extension's "api" range? No range — it does not use sdem.api."""
    if not spec: return False
    from .api import VERSION
    from .upgrade import satisfies
    return satisfies(VERSION, spec)


CODE_FILES = ('bian.py', 'inferences.py', 'rules_bian.py', 'aid_bian.py')   # 0.22 step 3b: BIAN's link rules too   # ST-22, ST-D7: the sdem bian commands; the engines' BIAN steps move in step 5


def package_code():
    """The `sdem bian` commands written against sdem.api — what sdem-bian carries ({file name: source}). Every relative import of
    SDEM's becomes `from sdem.api import …`; the two modules' imports of each other stay relative (ST-21)."""
    import re
    from .paths import DATA_ROOT
    own = {f[:-3] for f in CODE_FILES}
    out = {}
    for f in CODE_FILES:
        src = (Path(__file__).parent / f).read_text(encoding='utf-8')
        def sub(m):
            mod = m.group(2)
            return m.group(0) if mod in own else f"{m.group(1)}from sdem.api import {m.group(3)}"
        src = re.sub(r'^(\s*)from \.(\w*) import (.+)$', sub, src, flags=re.M)
        out[f] = src
    return out
