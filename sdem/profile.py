"""Organisation profiles — an organisation's own design specifications on top of SDEM's metamodel (docs/design/sdem-profile-spec.md,
PR-01…PR-20).

A workspace may carry `sdem-profile.json`; it may extend one base profile (`"extends": "<path>"`, e.g. the organisation's standard
profile shared by every team). A profile **adds** to SDEM's metamodel — never removes or redefines it:

  types        its own kinds of thing, each extending an SDEM type (so linking, impact and requirements apply to them unchanged);
  attributes   its own fields on a type and its subtypes — type, allowed values, required or not — enforced by `sdem check`;
  rules        what a type must carry or meet (`require`, `check`, `link`, `compare`, `across` approved cross-layer links), with the
               organisation's own message, severity and effective date;
  includes     the organisation's standards (security, network, technology …) and reference-architecture patterns, each its own
               versioned file with an owner (PR-13, PR-17) — evaluated by `sdem comply`, with exceptions a person grants (PR-18);
  link_kinds   its own within-layer link kinds, each mapped onto an ArchiMate kind SDEM already knows;
  names        its words for the layers and the types, used in every output.

The merged metamodel is what every command sees once the profile is active. A profile is activated from the workspace a command
works on (`--workspace`, the datasets' folder, or the graph store it was built into — a store keeps the profile it was built with).
`sdem profile check` checks a profile; `sdem profile show` prints the merged result; `sdem profile example` writes a synthetic one.
"""
from .identity import load as _jload  # DL-11: a design's files read through one boundary (docs/design/sdem-data-layer-spec.md)
from .identity import T as _T, layer as _L, live as _live, readable as _readable  # ST-01…ST-05: layers and types by id (docs/design/sdem-stable-identity-spec.md)
import argparse, copy, hashlib, json, re, sys
from pathlib import Path

from .paths import DATA_ROOT

FILE = 'sdem-profile.json'
FORMAT = 'sdem-profile/1'
STANDARD_FORMAT, PATTERN_FORMAT = 'sdem-standard/1', 'sdem-pattern/1'   # files a profile includes (PR-13, PR-17)
EXCEPTIONS_FILE = 'exceptions.json'                                     # a workspace's granted exceptions (PR-18)
PRIVATE = ('chain', 'included', '_issues', '_origin', 'aspects', '_numbering')                   # kept with the merged profile, not part of its content
SCHEMA = DATA_ROOT / 'schema' / 'profile.schema.json'
LEVELS = _live(lambda: tuple(dict.fromkeys((_L('business'), _L('bian'), _L('data'), _L('application'), _L('technology')))))
ATTR_TYPES = ('string', 'integer', 'number', 'boolean', 'date', 'enum', 'list<string>', 'map<string,string>')
MAP_KINDS = ('shapes', 'connectors', 'zones')   # PR-28: the diagram mapping table — the organisation's shapes, connector labels and zones
LISTS = ('layers', 'types', 'attributes', 'rules', 'link_kinds', 'link_types', 'requirement_categories')   # what a profile adds to its base
ACTIVE = None          # the resolved, merged profile the current command works under (None: SDEM's metamodel alone)
_ACTIVE_KEY = None     # its content hash — the metamodel cache key
_RAW = None            # the active profile as resolved, before it is numbered for the workspace (DL-25)
ACTIVE_EXCEPTIONS = []  # the active workspace's granted exceptions (PR-18)


class ProfileError(ValueError):
    pass


# ------------------------------------------------------------------ reading and resolving

def read(path):
    path = Path(path)
    try: doc = _jload(path)
    except FileNotFoundError: raise ProfileError(f'{path}: no such profile')
    except ValueError as e: raise ProfileError(f'{path}: not valid JSON — {e}')
    if doc.get('format') != FORMAT: raise ProfileError(f"{path}: not an SDEM profile (format {doc.get('format')!r}; expected {FORMAT!r})")
    return doc


def _format_of(path):
    try: return _jload(Path(path)).get('format')
    except (OSError, ValueError, AttributeError): return None


EXT = 'ext:'   # MX-01, MX-10: an include that names an installed metamodel extension's pack — "ext:security"
SHIPPED = 'sdem:'   # CPL-02: an include that names a standard or pattern shipped with SDEM — "sdem:sdem-completeness.json"


def shipped(name):
    """The file of a standard or pattern shipped with SDEM (the folder `standards/`; `sdem/data/standards/` when installed)."""
    base = (DATA_ROOT / 'standards').resolve(); f = (base / name[len(SHIPPED):]).resolve()
    if base not in f.parents or f.suffix != '.json': raise ProfileError(f'{name}: not a file shipped with SDEM — the ones it ships are in {base}')
    if not f.is_file(): raise ProfileError(f"{name}: SDEM ships no such standard or pattern — it ships: {', '.join(sorted(p.name for p in base.glob('*.json'))) or 'none'}")
    return f


_PACKS = {}


BUILTIN = _live(lambda: {'bian': {'name': 'bian', 'version': '1.0.0', 'kind': ['metamodel'], 'scope': {'within': [_L('bian')]}, 'builtin': True, 'pack_file': 'ext-bian-pack.json',
                   'description': f'BIAN Service Domain Architecture — the {_L("bian")} layer, its types, link types and inference rules (banking; built in, BX-01)'}})


def pack(name):
    """MX-01, MX-10, MX-11a: the pack file of the installed metamodel extension `ext:<name>` — refused, never skipped, when the
    extension is not installed, is not a metamodel extension, or does not support this SDEM."""
    if name in _PACKS: return _PACKS[name]
    ext = name[len(EXT):]
    from . import extensions as _x
    prog = _x.find(ext)
    if ext == 'bian' and prog:   # BP-10: an installed sdem-bian SDEM cannot use — the built-in BIAN instead, and `sdem extensions` says why
        from . import parts
        if (parts.package() or {}).get('refused'): prog = None
    if not prog and ext in BUILTIN:   # BX-01: a metamodel extension shipped inside SDEM (step 1 of 0.20: BIAN)
        _PACKS[name] = (DATA_ROOT / 'metamodel' / BUILTIN[ext]['pack_file'], {k: v for k, v in BUILTIN[ext].items() if k != 'pack_file'}); return _PACKS[name]
    if not prog: raise ProfileError(f"{name}: the profile includes the metamodel extension {ext!r}, but sdem-{ext} is not installed — install it into SDEM's environment (sdem extensions lists what is), or take it out of the profile")
    m = _x.manifest(prog) or {}
    kinds = m.get('kind') if isinstance(m.get('kind'), list) else [m.get('kind')]
    if 'metamodel' not in kinds or not m.get('pack'): raise ProfileError(f"{name}: sdem-{ext} is installed but is not a metamodel extension (its manifest has no kind 'metamodel' and pack)")
    if m.get('sdem'):
        from .paths import version
        from .upgrade import satisfies
        if not satisfies(version(), m['sdem']): raise ProfileError(f"{name}: sdem-{ext} {m.get('version', '')} supports SDEM {m['sdem']}; this is SDEM {version()} — install a version of sdem-{ext} for it (MX-11a)")
    f = Path(m['pack'])
    if not f.is_file(): raise ProfileError(f"{name}: sdem-{ext} names its pack {f}, which is not there — reinstall the extension")
    _PACKS[name] = (f, m); return _PACKS[name]


def shipped_patterns():
    """CPL-09: the patterns shipped with SDEM — [(the name a profile includes it by, the pattern file)]."""
    out = []
    for f in sorted((DATA_ROOT / 'standards').glob('*.json')):
        try: d = _jload(f)
        except ValueError: continue
        if d.get('format') == PATTERN_FORMAT: out.append((SHIPPED + f.name, d))
    return out


def available(datasets, mm):
    """CPL-09: the shipped patterns that fit this design and that its profile does not include — each with the record it would apply to.
    A pattern fits when a record is what its `applies_when` names; one that names no `when` fits nothing in particular and is never offered."""
    have = {x['id'] for x in (ACTIVE or {}).get('included', [])}
    out = []
    for name, d in shipped_patterns():
        pat = d['pattern']; aw = pat.get('applies_when') or {}
        if pat['id'] in have or not aw.get('when'): continue
        hit = sorted(i['id'] for ds in datasets.values() for i in ds.get('instances', [])
                     if mm.known(i['type']) and mm.is_a(i['type'], aw['entity']) and applies({'when': aw['when']}, i))
        if hit: out.append({'include': name, 'id': pat['id'], 'title': pat['title'], 'because': hit[0], 'specific': 'name' in aw['when']})
    return sorted(out, key=lambda x: (not x['specific'], x['include']))   # the pattern for this kind of solution before the one for its kind of domain (CPL-12)


def fitting(datasets, mm):
    """CPL-16: the structures of the shipped patterns that fit this design and that its profile does not include — for `sdem aid`,
    which asks every pattern that fits before it infers anything. Consulting one is not including it."""
    names = {x['include'] for x in available(datasets, mm)}
    return [{'pattern': d['pattern'], 'structure': d['structure'], 'file': n, 'included': False} for n, d in shipped_patterns() if n in names and d.get('structure')]


def shipped_included():
    """The ids of the active profile's standards and patterns that are SDEM's own shipped files (CPL-11)."""
    base = (DATA_ROOT / 'standards').resolve().as_posix() + '/'
    return {x['id'] for x in (ACTIVE or {}).get('included', []) if x['file'].startswith(base)}


def _fragment(path):
    """A standards or pattern file a profile includes (PR-13, PR-17)."""
    try: doc = _jload(Path(path))
    except FileNotFoundError: raise ProfileError(f'{path}: no such standards or pattern file')
    except ValueError as e: raise ProfileError(f'{path}: not valid JSON — {e}')
    kind = {STANDARD_FORMAT: 'standard', PATTERN_FORMAT: 'pattern'}.get(doc.get('format'))
    if not kind: raise ProfileError(f"{path}: not a standards or pattern file (format {doc.get('format')!r}; expected {STANDARD_FORMAT!r} or {PATTERN_FORMAT!r})")
    meta = doc.get(kind) or {}
    missing = [k for k in ('id', 'title', 'version', 'owner') if not meta.get(k)]
    if kind == 'pattern' and not (meta.get('applies_when') or {}).get('entity'): missing.append('applies_when.entity')
    if missing: raise ProfileError(f"{path}: the {kind} needs {', '.join(missing)}")
    return kind, doc


def _add(merged, doc, origin):
    """PR-14: add a profile's (or an included file's) attributes and rules to what its base declared — never change the base: a
    redeclared attribute is refused unless it says `narrows` and its values are a subset; a rule id already used is refused."""
    issues, own = merged['_issues'], merged['_origin']
    for a in doc.get('attributes', []):
        k = f"attribute {a['entity']}.{a['name']}"
        if k not in own:
            if a.get('narrows'): issues.append(f"{k}: narrows, but no base declares it ({origin})")
            own[k] = origin; merged['attributes'].append(dict(a)); continue
        prev = next(x for x in merged['attributes'] if (x['entity'], x['name']) == (a['entity'], a['name']))
        if not a.get('narrows'):
            issues.append(f"{k}: already declared by {own[k]} — {origin} may not change it (to narrow its list of values, give \"narrows\": true)"); continue
        if not (a['type'] == prev['type'] and prev.get('values') and a.get('values') and set(a['values']) <= set(prev['values'])):
            issues.append(f"{k}: {origin} may only narrow it — the same type, and values {sorted(set(a.get('values') or []) - set(prev.get('values') or [])) or a.get('values')} are not among {own[k]}'s {prev.get('values')}"); continue
        prev['values'] = list(a['values']); prev['narrowed_by'] = origin
        if a.get('required'): prev['required'] = True
    for r in doc.get('rules', []):
        k = f"rule {r['id']}"
        if k in own: issues.append(f"{k}: the id is already used by {own[k]} — {origin} gives its rule an id of its own"); continue
        own[k] = origin; merged['rules'].append(r)


def _pattern_rules(doc, merged, origin):
    """PR-17: a pattern's required parts as rules on the records it applies to."""
    pat = doc['pattern']; aw = pat['applies_when']; ent, when = aw['entity'], dict(aw.get('when') or {})
    meta = {k: v for k, v in pat.items() if k != 'applies_when'}
    out = []
    for it in doc.get('requires', []):
        r = {'id': it['id'], 'entity': ent, 'pattern': meta, 'message': it.get('message') or f"{pat['title']} ({pat['id']})"}
        if when: r['when'] = dict(when)
        if it.get('severity'): r['severity'] = it['severity']
        if it.get('rule'):
            ref = next((x for x in merged['rules'] if x['id'] == it['rule']), None)
            if not ref: merged['_issues'].append(f"pattern {pat['id']} item {it['id']}: rule {it['rule']} is not declared — include its standard before the pattern ({origin})"); continue
            if ref['entity'] != ent: merged['_issues'].append(f"pattern {pat['id']} item {it['id']}: rule {it['rule']} is on {ref['entity']}, the pattern applies to {ent}"); continue
            r.update({k: v for k, v in ref.items() if k in ('require', 'check', 'link', 'any_link', 'compare', 'across', 'standard')})
            if ref.get('when'): r['when'] = {**ref['when'], **when}
            if ref.get('message') and not it.get('message'): r['message'] = ref['message']
        for part, key in (('within', 'link'), ('require', 'require'), ('check', 'check'), ('across', 'across'), ('compare', 'compare')):
            if it.get(part) is not None: r[key] = it[part]
        out.append(r)
    return out


def include(merged, ip):
    """PR-13, PR-17, PR-21: fold one standards or pattern file into a merged profile (a pattern's structure is kept whole)."""
    ip = Path(ip).resolve()
    if any(x['file'] == ip.as_posix() for x in merged['included']): return   # included by a base already
    kind, fd = _fragment(ip)
    meta = fd[kind]
    if kind == 'standard': rules = [{**r, 'standard': meta} for r in fd.get('rules', [])]
    else: rules = _pattern_rules(fd, merged, ip.name)
    _add(merged, {'attributes': fd.get('attributes', []), 'rules': rules}, ip.name)
    if kind == 'pattern' and fd.get('structure'):
        merged['structures'].append({'pattern': meta, 'structure': fd['structure'], 'file': ip.name})
    merged['included'].append({'file': ip.as_posix(), 'kind': kind, 'id': meta['id'], 'version': meta['version'], 'title': meta['title'], 'owner': meta['owner']})


def include_pack(merged, name, _seen=(), local=None):
    """MX-01…MX-03: fold a metamodel extension's pack — a profile file of its own (its layers, types, link types, attributes, rules,
    link kinds, requirement categories, names, and the standards it includes) — into a merged profile, adding only (PR-14).
    `local`: the pack as a file the workspace carries (a copy sent with a published design, where the extension is not installed)."""
    f, m = (local, {'name': (read(local).get('name') or local.stem), 'version': read(local).get('version')}) if local else pack(name)
    if any(a['name'] == name for a in merged.setdefault('aspects', [])): return
    p = resolve(f, _seen)
    from . import parts
    # BX-50, MID-10 (docs/design/metamodel-integrity-design.md): anything an extension adds may require another extension ("requires":
    # "ext:<name>", or a list) — kept only where that one is on (BIAN: BIAN on; any other: included before it), else left out and said, never an error
    def off(x):
        req = x.get('requires') if isinstance(x, dict) else None
        for r in ([req] if isinstance(req, str) else req or []):
            on = parts.bian_on() if r == parts.EXT_BIAN else any(a.get('name') == r for a in merged.get('aspects') or [])
            if not on: return r
        return None
    def said(k, x):
        if k == 'link_types': return {'link_type': f"{_readable(x.get('source_type'))} {x.get('relationship')} {_readable(x.get('target_type'))}"}
        return {k[:-1]: x.get('type') or x.get('id') or x.get('name') or x.get('code')}
    for k in LISTS:
        if k in ('attributes', 'rules'): continue
        rows = [x for x in p[k] if not off(x)]
        merged.setdefault('left_out', []).extend({'extension': m['name'], **said(k, x), 'requires': off(x)} for x in p[k] if off(x))
        merged[k] += [{**x, 'source': x.get('source') or f"metamodel extension {m['name']} {m.get('version', '')}".strip()} if k == 'layers' else dict(x) for x in rows]
    ar = {k: [x for x in p[k] if not off(x)] for k in ('attributes', 'rules')}
    merged.setdefault('left_out', []).extend({'extension': m['name'], **said(k, x), 'requires': off(x)} for k in ('attributes', 'rules') for x in p[k] if off(x))
    _add(merged, ar, f"{name} ({f.name})")
    for k in ('layers', 'types'): merged['names'][k].update(p['names'][k])
    merged['included'] += [x for x in p['included'] if x['file'] not in {y['file'] for y in merged['included']}]
    # MX-17: rules the extension computes itself (its own commands, not sdem comply) — named so a person can grant an exception to one
    merged.setdefault('computed_rules', []).extend({**r, 'extension': m['name']} for r in (read(f).get('computed_rules') or []) if r.get('id'))
    merged['structures'] += p['structures']; merged['_issues'] += p['_issues']
    merged['aspects'].append({'name': name, 'extension': m['name'], 'version': m.get('version'), 'file': f.as_posix(), 'pack': p['name'], 'pack_version': p['version']})


def resolve(path, _seen=()):
    """The profile at `path` with its base profiles folded in (base first), then the standards and patterns it includes, then its
    own additions — as one merged profile; `chain` names every profile file, `included` every standards and pattern file."""
    path = Path(path).resolve()
    if path in _seen: raise ProfileError(f'{path}: profiles extend each other in a circle')
    doc = read(path)
    merged = {'format': FORMAT, 'name': doc.get('name', path.stem), 'version': doc.get('version', 1), 'chain': [], 'included': [], '_issues': [], '_origin': {},
              **{k: [] for k in LISTS}, 'names': {'layers': {}, 'types': {}}, 'structures': [], 'diagram_map': {k: [] for k in MAP_KINDS}}
    if doc.get('extends'):
        base = resolve((path.parent / doc['extends']).resolve(), _seen + (path,))
        for k in LISTS: merged[k] = [dict(x) for x in base[k]]
        merged['names'] = {'layers': dict(base['names']['layers']), 'types': dict(base['names']['types'])}
        merged['chain'] = list(base['chain']); merged['included'] = list(base['included'])
        merged['_issues'] = list(base['_issues']); merged['_origin'] = dict(base['_origin'])
        merged['structures'] = [dict(x) for x in base['structures']]
        merged['diagram_map'] = {k: list(v) for k, v in base['diagram_map'].items()}
        if base.get('requires_sdem'): merged['requires_sdem'] = base['requires_sdem']
        if base.get('hosting'): merged['hosting'] = json.loads(json.dumps(base['hosting']))
    for inc in doc.get('includes', []):   # PR-13, PR-17: standards and patterns, after the base and before the profile's own additions
        if str(inc).startswith(EXT): include_pack(merged, inc, _seen + (path,)); continue   # MX-01: a metamodel extension's pack
        ip = shipped(inc) if str(inc).startswith(SHIPPED) else (path.parent / inc).resolve()
        if ip.suffix == '.json' and ip.is_file() and _format_of(ip) == FORMAT:   # MX-01: a pack the workspace carries as a file
            include_pack(merged, f'file:{inc}', _seen + (path,), local=ip); continue
        include(merged, ip)
    _add(merged, doc, path.name)
    own_map = doc.get('diagram_map') or {}   # PR-28: the profile's own entries are matched before its base's
    merged['diagram_map'] = {k: list(own_map.get(k, [])) + merged['diagram_map'][k] for k in MAP_KINDS}
    for k in LISTS:
        if k not in ('attributes', 'rules'): merged[k] += list(doc.get(k, []))
    for k in ('layers', 'types'): merged['names'][k].update((doc.get('names') or {}).get(k, {}))
    if doc.get('hosting'):   # PR-32: the organisation's hosting policy — a team profile may set its own default and add templates and signals
        h = merged.setdefault('hosting', {}); own = doc['hosting']
        if 'default' in own: h['default'] = own['default']
        h['templates'] = {**(h.get('templates') or {}), **(own.get('templates') or {})}
        h['signals'] = list(h.get('signals') or []) + list(own.get('signals') or [])
        if own.get('signal_overrides'):   # PR-33: a team profile's override of the same signal replaces the one above it
            mine = {o.get('id') for o in own['signal_overrides'] if isinstance(o, dict)}
            h['signal_overrides'] = [o for o in (h.get('signal_overrides') or []) if o.get('id') not in mine] + list(own['signal_overrides'])
    merged['chain'].append({'file': path.as_posix(), 'name': doc.get('name', path.stem), 'version': doc.get('version', 1)})
    reqs = [r for r in (merged.get('requires_sdem'), doc.get('requires_sdem')) if r]   # UF-04: every profile in the chain must accept this SDEM
    if reqs: merged['requires_sdem'] = ','.join(reqs)
    return merged


def digest(merged):
    body = {k: v for k, v in merged.items() if k not in PRIVATE}
    if merged.get('_numbering'): body['_numbering'] = merged['_numbering']   # DL-25: numbered for another stack, another metamodel
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


# ------------------------------------------------------------------ checking (PR-02…PR-05)

def check(merged, base_mm):
    """Issues in a merged profile against SDEM's own metamodel: schema, every type extends a known SDEM (or profile) type of the same
    layer, no core type is redefined, attributes well formed on known types, rules name declared attributes, link kinds map onto
    ArchiMate kinds between types of one layer."""
    from .validate import check_schema
    schema = _jload(SCHEMA)
    issues = check_schema({k: v for k, v in merged.items() if k not in PRIVATE and k != 'structures'}, schema)
    if issues: return [f'profile: {i}' for i in issues]
    issues += merged.get('_issues', [])   # PR-14, PR-17
    if merged.get('requires_sdem'):   # UF-04
        from .paths import version
        from .upgrade import satisfies
        if not satisfies(version(), merged['requires_sdem']):
            return [f"profile {merged['name']} requires SDEM {merged['requires_sdem']}; this is SDEM {version()} — use a version it accepts, or update the profile (and its requires_sdem) for this one"]
    from .layers import CORE_CODES, RESERVED_FILES
    own_layers = {}   # LR-01: layers above A1 or below A4 — never between, never a core layer redefined
    for l in merged['layers']:
        if l['code'] in CORE_CODES: issues.append(f"layer {l['code']}: a core layer — a profile adds layers, never redefines SDEM's")
        elif l['code'] in own_layers: issues.append(f"layer {l['code']}: declared twice")
        elif l['file'] in RESERVED_FILES or l['file'] in {x['file'] for x in own_layers.values()}: issues.append(f"layer {l['code']}: file {l['file']} is already used")
        else: own_layers[l['code']] = l
    order = [l['code'] for l in reversed([l for l in own_layers.values() if l['position'] == 'above'])] + list(CORE_CODES) + [l['code'] for l in own_layers.values() if l['position'] == 'below']
    across = {c for c, l in own_layers.items() if l['position'] == 'across'}   # LR-11
    order += sorted(across)
    known = dict(base_mm.entities); declared = {}
    for t in merged['types']:
        m = re.fullmatch(r'[A-Z][A-Z0-9]*\.([A-Z][A-Z0-9]{0,5})\.[A-Za-z0-9]+', t['type'])
        lc = code_of(merged, m.group(1)) if m else None   # DL-25
        if t['type'] in known: issues.append(f"type {t['type']}: redefines an SDEM type — a profile adds types, never changes SDEM's")
        elif t['type'] in declared: issues.append(f"type {t['type']}: declared twice")
        elif not m or lc not in order: issues.append(f"type {t['type']}: a profile type is named <ORG>.<layer>.<Name> with a layer of this workspace ({', '.join(order)}), e.g. BANK.A3.PaymentsMicroservice")
        elif lc in own_layers and not t.get('extends'):   # LR-01: a root type of the profile's own layer
            declared[t['type']] = {'type': t['type'], 'level': lc, 'extends': None, 'abstract': False, 'artefact': False, **t}
        elif not t.get('extends'): issues.append(f"type {t['type']}: a type in a core layer extends an SDEM type")
        else:
            parent = known.get(t['extends']) or declared.get(t['extends'])
            if not parent: issues.append(f"type {t['type']}: extends {t['extends']!r}, which is neither an SDEM type nor a profile type")
            elif lc != parent['level']: issues.append(f"type {t['type']}: its layer is {lc} but it extends an {parent['level']} type")
            else: declared[t['type']] = {**parent, **t, 'level': parent['level'], 'artefact': parent.get('artefact', False), 'abstract': False}
    for code in own_layers:
        if not any(d['level'] == code for d in declared.values()): issues.append(f"layer {code}: declares no types")
    all_types = {**known, **declared}
    attrs = set()
    for a in merged['attributes']:
        if a['entity'] not in all_types: issues.append(f"attribute {a['name']}: {a['entity']} is not a type")
        if a['type'] == 'enum' and not a.get('values'): issues.append(f"attribute {a['entity']}.{a['name']}: an enum needs values")
        if not re.fullmatch(r'[a-z][a-z0-9_]*', a['name']): issues.append(f"attribute {a['entity']}.{a['name']}: a name is lower_snake_case")
        if a['entity'] in all_types and a['name'] in _sdem_attribute_names(a['entity'], all_types, base_mm):   # PR-02, PR-14: SDEM's own attributes are not redefined
            issues.append(f"attribute {a['entity']}.{a['name']}: SDEM already defines {a['name']!r} for {a['entity']} — a profile adds attributes, never redefines SDEM's; "
                          f"use SDEM's (sdem types {a['entity']}) or give yours another name (e.g. {(merged['name'].split('-')[0] or 'org').lower()}_{a['name']})")
        attrs.add((a['entity'], a['name']))
    kinds = {k['kind'] for k in base_mm.relationships['kinds']}
    own_kinds = {k['kind'] for k in merged['link_kinds']}
    for r in merged['rules']:
        if r['entity'] not in all_types: issues.append(f"rule {r['id']}: {r['entity']} is not a type"); continue
        def known_attr(n): return n == 'lifecycle_status' or any((e, n) in attrs for e in [r['entity']] + _ancestors(all_types, r['entity'])) or n in _sdem_attribute_names(r['entity'], all_types, base_mm)
        for n in r.get('require', []):
            if not known_attr(n): issues.append(f"rule {r['id']}: requires {n!r}, which is not an attribute of {r['entity']} (declare it under attributes)")
        for n in r.get('when', {}):
            if n not in RECORD_FIELDS and not known_attr(n): issues.append(f"rule {r['id']}: when {n!r}, which is not an attribute of {r['entity']} (declare it under attributes)")
        for part in ('link', 'compare'):
            k = (r.get(part) or {}).get('kind')
            if k and k not in kinds | own_kinds: issues.append(f"rule {r['id']}: {part} kind {k!r} is neither an ArchiMate kind SDEM knows nor one of the profile's link kinds")
        for lk in r.get('any_link') or []:   # PR-35
            if not (lk.get('kind') or lk.get('relationship')): issues.append(f"rule {r['id']}: each any_link names a kind (inside the layer) or a relationship (between layers)")
            if lk.get('kind') and lk['kind'] not in kinds | own_kinds: issues.append(f"rule {r['id']}: any_link kind {lk['kind']!r} is neither an ArchiMate kind SDEM knows nor one of the profile's link kinds")
            if lk.get('to') and lk['to'] not in all_types: issues.append(f"rule {r['id']}: any_link to {lk['to']!r}, which is not a type")
        to = (r.get('link') or {}).get('to')
        if to and to not in all_types: issues.append(f"rule {r['id']}: link to {to!r}, which is not a type")
        elif to and all_types[to]['level'] != all_types[r['entity']]['level']: issues.append(f"rule {r['id']}: link to {to} — a rule follows within-layer links, so both types are in one layer")
        att = (r.get('compare') or {}).get('attribute')
        if att and not known_attr(att): issues.append(f"rule {r['id']}: compares {att!r}, which is not an attribute of {r['entity']}")
        c = r.get('check')
        if c and not r.get('across') and not known_attr(c['attribute']): issues.append(f"rule {r['id']}: checks {c['attribute']!r}, which is not an attribute of {r['entity']}")
        if c and c['op'] in ('before', 'after') and _date_expr(c.get('value')) is None: issues.append(f"rule {r['id']}: {c['op']} needs a date — an ISO date, today, or today±Nd")
        if c and c['op'] in ('<', '<=', '>', '>=') and not isinstance(c.get('value'), (int, float)): issues.append(f"rule {r['id']}: {c['op']} needs a number")
        if r.get('across'):
            rel = r['across']['relationship']
            known_rels = {x['relationship'] for x in load_registry_rows()} | {x['relationship'] for x in merged['link_types']}
            if rel not in known_rels: issues.append(f"rule {r['id']}: across {rel!r}, which is not a link type between layers ({', '.join(sorted(known_rels))})")
    from .requirements import SCHEMA as REQ_SCHEMA
    sdem_categories = _jload(REQ_SCHEMA)['$defs']['requirement']['properties']['category']['enum']
    seen = set()
    for c in merged['requirement_categories']:
        if c['id'] in sdem_categories: issues.append(f"requirement category {c['id']}: already one of SDEM's")
        elif c['id'] in seen: issues.append(f"requirement category {c['id']}: declared twice")
        seen.add(c['id'])
    for k in merged['link_kinds']:
        if k['maps_to'] not in kinds: issues.append(f"link kind {k['kind']}: maps_to {k['maps_to']!r} is not an ArchiMate kind SDEM knows ({', '.join(sorted(kinds))})")
        in_own = all((all_types.get(k[e]) or {}).get('level') in own_layers for e in ('source_type', 'target_type'))
        if k['kind'] in kinds and not (in_own and k['kind'] == k['maps_to']):   # in a profile layer, ArchiMate's own kinds may be allowed between its types
            issues.append(f"link kind {k['kind']}: that is already an SDEM kind" + ('' if in_own else ' — in a core layer a profile adds kinds, never more rows for SDEM\'s'))
        for t in (k['source_type'], k['target_type']):
            if t not in all_types: issues.append(f"link kind {k['kind']}: {t} is not a type")
        if k['source_type'] in all_types and k['target_type'] in all_types and all_types[k['source_type']]['level'] != all_types[k['target_type']]['level']:
            issues.append(f"link kind {k['kind']}: a within-layer kind joins two types of one layer")
    from .validate import load_registry
    core_edges = {(r['source_type'], r['relationship'], r['target_type']) for r in load_registry(core=True)['relationships']}
    touching = set()
    for x in merged['link_types']:   # LR-06: links between a profile layer and its neighbour
        name = f"link type {x['source_type']} {x['relationship']} {x['target_type']}"
        ends = [all_types.get(x['source_type']), all_types.get(x['target_type'])]
        if not all(ends): issues.append(f"{name}: {x['source_type'] if not ends[0] else x['target_type']} is not a type"); continue
        a, b = ends[0]['level'], ends[1]['level']
        if (a in across) != (b in across): pass   # LR-11: a cross-cutting layer's link types may reach any layer
        elif a in across: issues.append(f"{name}: both ends are in cross-cutting layers — links inside one are its link kinds"); continue
        elif not (a in order and b in order and order.index(b) - order.index(a) == 1): issues.append(f"{name}: links a layer to the layer directly below it ({a} is not directly above {b})")
        elif a not in own_layers and b not in own_layers: issues.append(f"{name}: both layers are SDEM's — links between core layers are SDEM's nine link types")
        elif (x['source_type'], x['relationship'], x['target_type']) in core_edges: issues.append(f"{name}: already an SDEM link type")
        touching |= {a, b}
    for code in own_layers:
        if code not in touching: issues.append(f"layer {code}: no link type joins it to " + ('another layer' if code in across else 'its neighbour') + ' — add one under link_types')
    for l in merged['names']['layers']:
        if l not in order: issues.append(f"names.layers: {l} is not a layer ({', '.join(order)})")
    for t in merged['names']['types']:
        if t not in all_types: issues.append(f"names.types: {t} is not a type")
    def known_attr_of(ent, n):
        return n == 'lifecycle_status' or any((e, n) in attrs for e in [ent] + _ancestors(all_types, ent)) or n in _sdem_attribute_names(ent, all_types, base_mm)
    from .patterns import structure_issues, map_issues
    for st in merged.get('structures', []):   # PR-21, PR-22
        issues += structure_issues(st, all_types, base_mm, merged, known_attr_of)
    issues += map_issues(merged.get('diagram_map') or {}, all_types, base_mm, merged, known_attr_of)   # PR-28
    issues += hosting_issues(merged)   # PR-32
    return issues


def _date_expr(v):
    from .comply import date_of
    return date_of(v) if isinstance(v, str) else None


def load_registry_rows():
    from .validate import load_registry
    return load_registry(core=True)['relationships']


def _ancestors(all_types, t):
    out, cur = [], all_types.get(t)
    while cur and cur.get('extends'):
        out.append(cur['extends']); cur = all_types.get(cur['extends'])
    return out


def _sdem_attribute_names(t, all_types, base_mm):
    from .conformance import model
    byent, common, _ = model(base=True)
    names = set(common)
    for x in [t] + _ancestors(all_types, t): names |= set(byent.get(x, {}))
    return names


# ------------------------------------------------------------------ applying (PR-06)

def apply(mm, merged):
    """SDEM's metamodel with the profile's types, link kinds and names added — a new Metamodel; the base is untouched."""
    from .metamodel import Metamodel
    ents = [copy.deepcopy(e) for e in mm.entities.values()]
    by = {e['type']: e for e in ents}
    for t in merged['types']:
        if not t.get('extends'):   # LR-01: a root type of the profile's own layer
            e = {'type': t['type'], 'level': code_of(merged, t['type'].split('.')[1]), 'extends': None, 'abstract': False, 'artefact': False, 'definition': t.get('definition', ''),
                 'identifier': {'key': ['name'], 'basis': 'SDEM', 'reasoning': 'a unique name within the layer'}, 'alignment_kind': 'organisation_extension',
                 'reference': {'standard': merged['name'], 'concept': t.get('name') or t['type'].split('.')[-1], 'locator': t.get('source', 'organisation profile')},
                 'evidence_status': 'organisation_defined', 'definition_source': 'organisation_profile', 'confidence': 'high',
                 'confidence_basis': f"declared by the organisation's profile {merged['name']}", 'reasoning': t.get('reasoning', "a kind of thing in the organisation's own layer")}
            if t.get('archimate'): e['archimate'] = t['archimate']   # ARV-15: the element it is drawn as, if the profile or extension names one
            ents.append(e); by[e['type']] = e; continue
        parent = by[t['extends']]
        e = {**{k: parent[k] for k in ('level', 'artefact') if k in parent}, 'type': t['type'], 'extends': t['extends'], 'abstract': False,
             'definition': t.get('definition', ''), 'identifier': parent.get('identifier'), 'alignment_kind': 'organisation_extension',
             'reference': {'standard': merged['name'], 'concept': t.get('name') or t['type'].split('.')[-1], 'locator': t.get('source', 'organisation profile')},
             'evidence_status': 'organisation_defined', 'definition_source': 'organisation_profile', 'confidence': 'high',
             'confidence_basis': f"declared by the organisation's profile {merged['name']}", 'reasoning': t.get('reasoning', 'organisation-specific kind, mapped onto an SDEM type')}
        if t.get('archimate'): e['archimate'] = t['archimate']   # ARV-15: else it inherits its parent's notation
        ents.append(e); by[e['type']] = e
    rels = copy.deepcopy(mm.relationships)
    for k in merged['link_kinds']:
        if k['kind'] not in {x['kind'] for x in rels['kinds']}:
            rels['kinds'].append({'kind': k['kind'], 'source': f"organisation profile {merged['name']} (maps onto ArchiMate {k['maps_to']})", 'semantics': k.get('description', ''), 'maps_to': k['maps_to']})
        rels['constraints'].append({'level': by[k['source_type']]['level'], 'source_type': k['source_type'], 'kind': k['kind'], 'target_type': k['target_type'],
                                    'basis': f"organisation profile {merged['name']}", 'id': f"PRF-{k['kind']}-{k['source_type']}-{k['target_type']}", 'description': k.get('description', ''), 'confidence': 'high',
                                    'verification': 'organisation_defined', 'reasoning': f"maps onto ArchiMate {k['maps_to']}"})
    out = Metamodel(ents, rels, mm.version)
    out.profile = merged
    return out


def registry_rows(merged):
    """LR-06: the profile's link types as rows of SDEM's link-type registry (schema/relationship-types.json form)."""
    return [{'mapping_type_id': f"PRF-{x['source_type']}-{x['relationship']}-{x['target_type']}".replace('.', '_'), 'source_type': x['source_type'], 'relationship': x['relationship'],
             'target_type': x['target_type'], 'cardinality': x.get('cardinality', 'many_to_many'), 'perspective': 'architecture', 'authority': 'organisation_profile',
             'direction_semantics': x.get('description', ''), 'required_evidence': x['required_evidence'], 'rule_version': str(merged['version']), 'owner': merged['name'],
             'source_reference': x.get('source', f"organisation profile {merged['name']}"), 'confidence': 'high', 'verification': 'organisation_defined',
             'confidence_basis': f"declared by the organisation's profile {merged['name']}", 'reasoning': x.get('reasoning', 'organisation-defined link between adjacent layers')}
            for x in merged.get('link_types', [])]


def names():
    """The active profile's words for layers and types ({} without one)."""
    return (ACTIVE or {}).get('names') or {'layers': {}, 'types': {}}


def profile_attributes():
    """The active profile's attribute definitions, in entity-attributes form, by entity type."""
    out = {}
    for a in (ACTIVE or {}).get('attributes', []):
        out.setdefault(a['entity'], {})[a['name']] = {'id': f"PRF-{a['entity']}.{a['name']}", 'entity': a['entity'], 'name': a['name'],
                                                      'type': 'string' if a['type'] in ('enum', 'number') else a['type'], 'values': a.get('values'), 'number': a['type'] == 'number',
                                                      'required': bool(a.get('required')), 'description': a.get('description', ''), 'status': 'active', 'source': f"organisation profile {ACTIVE['name']}"}
    return out


def rules():
    return (ACTIVE or {}).get('rules', [])


def hosting():
    """The active profile's hosting policy (PR-32): default (cloud | on_premises), zone templates, extra hosting signals — or None."""
    return (ACTIVE or {}).get('hosting')


def hosting_issues(merged):
    """PR-32: what is wrong with a profile's hosting policy."""
    h = merged.get('hosting') or {}; out = []
    if h.get('default') not in (None, 'cloud', 'on_premises'): out.append(f"hosting.default is {h['default']!r} — cloud or on_premises")
    for t, v in (h.get('templates') or {}).items():
        if not (isinstance(v, list) and v and v[0] in ('cloud', 'on_premises')): out.append(f"hosting.templates.{t}: starts with cloud or on_premises (its level-0 zone)")
    for sg in h.get('signals') or []:
        if not (isinstance(sg, dict) and sg.get('id') and sg.get('points_to') in ('cloud', 'on_premises') and sg.get('confidence') in ('low', 'medium', 'high') and sg.get('read')):
            out.append(f"hosting.signals: {sg.get('id') if isinstance(sg, dict) else sg!r} needs id, points_to (cloud | on_premises), confidence (low | medium | high) and read")
    from .hosting import _sdem_signals
    builtin = {s['id'] for s in _sdem_signals()}
    for o in h.get('signal_overrides') or []:   # PR-33: switch off, or re-weight, one of SDEM's signals — with a reason; never flip its direction
        who = o.get('id') if isinstance(o, dict) else o
        if not isinstance(o, dict) or o.get('id') not in builtin: out.append(f"hosting.signal_overrides: {who!r} is not one of SDEM's signals ({', '.join(sorted(builtin))}) — add your own under hosting.signals instead"); continue
        if not str(o.get('reason') or '').strip(): out.append(f"hosting.signal_overrides: {who} needs a reason — it is shown with every proposal it changes")
        if set(o) - {'id', 'off', 'confidence', 'reason'}: out.append(f"hosting.signal_overrides: {who} may set only off or confidence (and reason) — {', '.join(sorted(set(o) - {'id', 'off', 'confidence', 'reason'}))} not allowed; to point the other way, add your own signal")
        if o.get('off') is not True and o.get('confidence') not in ('low', 'medium', 'high'): out.append(f"hosting.signal_overrides: {who} sets neither off: true nor a confidence (low | medium | high)")
    return out


def structures():
    """The active profile's patterns that carry a structure (PR-21)."""
    return (ACTIVE or {}).get('structures', [])


def exceptions():
    """The active workspace's granted exceptions (PR-18)."""
    return ACTIVE_EXCEPTIONS


def _load_exceptions(folder):
    global ACTIVE_EXCEPTIONS
    f = Path(folder) / EXCEPTIONS_FILE
    try: ACTIVE_EXCEPTIONS = _jload(f).get('exceptions', []) if f.exists() else []
    except ValueError: ACTIVE_EXCEPTIONS = []


def requirement_categories():
    """The requirement categories the active profile adds to SDEM's."""
    return [c['id'] for c in (ACTIVE or {}).get('requirement_categories', [])]


RECORD_FIELDS = ('lifecycle_status', 'name')   # what a `when` may name besides an attribute (PR-10, PR-36)


def applies(rule, inst):
    """Whether a rule's `when` holds for a record: each named attribute (or lifecycle_status) has the value, or one of the values; a list
    attribute (conforms_to …) holds when it contains one of them (PR-10) — so a pattern applies to the records that say they follow it."""
    at = inst.get('attributes') or {}
    for k, want in (rule.get('when') or {}).items():
        have = inst.get(k) if k in RECORD_FIELDS else at.get(k)   # PR-36: a record's name, as its lifecycle status, is the record's own field
        wants = want if isinstance(want, list) else [want]
        if not (any(h in wants for h in have) if isinstance(have, list) else have in wants): return False
    return True


# ------------------------------------------------------------------ activation (PR-07)

def renumber(merged):
    """DL-25: a profile names layers in SDEM 0.19's numbering — A1 Business, A2 BIAN, A3 Application, A4 Technology, and its own layers
    by its own codes — whatever the workspace it is used in (one organisation profile serves workspaces in both forms). In a workspace
    whose layers are numbered otherwise (SDEM 0.20's form: Data its own layer), its core codes are read as the layers they name, and an own
    layer whose code is now a core layer's takes the next free A-number. Type names (BANK.A3.PaymentsMicroservice) are ids and do not
    change; the layer a name gives is read through `_numbering`."""
    from .identity import _index, stack, layer
    old = _index()[0]   # layer id → its 0.19 code
    st = stack()
    core = {c: layer(i) for i, c in old.items() if c and i in st}
    if all(k == v for k, v in core.items()) and len(core) == len([c for c in old.values() if c]): return merged
    taken = set(core.values()) | {layer(i) for i in st}
    num = lambda c: int(c[1:]) if re.fullmatch(r'A\d+', c) else 0
    nxt = max(num(c) for c in taken) + 1
    own = {}
    for l in merged['layers']:
        c = l['code']
        if c in core or c in own: continue   # the check refuses a core code; a code twice is refused there too
        if c in taken: own[c] = f'A{nxt}'; taken.add(own[c]); nxt += 1
    m = {**core, **own}
    out = dict(merged)
    def moved(l):   # a name that begins with its own code ('A5 Physical') follows the code
        c = m.get(l['code'], l['code']); n = l.get('name')
        return {**l, 'code': c, **({'name': c + n[len(l['code']):]} if isinstance(n, str) and n.startswith(l['code'] + ' ') else {})}
    out['layers'] = [moved(l) for l in merged['layers']]
    out['names'] = {**merged['names'], 'layers': {m.get(k, k): v for k, v in merged['names']['layers'].items()}}
    out['_numbering'] = m
    return out


def code_of(merged, name_code):
    """DL-25: the layer a profile type's name gives (the middle of BANK.A3.PaymentsMicroservice), as the workspace numbers it."""
    return ((merged or {}).get('_numbering') or {}).get(name_code, name_code)


def activate_file(path):
    """Make the profile at `path` the active one (resolved and checked). Returns the merged profile."""
    global ACTIVE, _ACTIVE_KEY, _RAW
    raw = resolve(path); merged = renumber(raw)
    from .metamodel import Metamodel
    issues = check(merged, Metamodel.base())
    if issues: raise ProfileError(f'{Path(path).as_posix()}: the profile does not pass its checks:\n  ' + '\n  '.join(issues[:10]))
    key = digest(merged); _RAW = raw
    if key != _ACTIVE_KEY:
        ACTIVE, _ACTIVE_KEY = merged, key
        from . import conformance; conformance.model.cache_clear()
    return merged


def _renumbered(merged):
    """DL-25: the workspace's layers were settled after the profile was activated (BX-50) — number the profile for them."""
    global ACTIVE
    if _RAW is None or ACTIVE is not merged: return merged
    global _ACTIVE_KEY
    again = renumber(_RAW)
    if again.get('_numbering') != merged.get('_numbering'):
        ACTIVE, _ACTIVE_KEY = again, digest(again)
        from . import conformance; conformance.model.cache_clear()
    return ACTIVE


def deactivate():
    global ACTIVE, _ACTIVE_KEY, ACTIVE_EXCEPTIONS, _RAW
    _RAW = None
    ACTIVE_EXCEPTIONS = []
    from . import parts; parts.reset()   # BX-12: no workspace, BIAN on
    if ACTIVE is not None:
        ACTIVE, _ACTIVE_KEY = None, None
        from . import conformance; conformance.model.cache_clear()


class opened:
    """`with opened(folder):` — the workspace's profile and form for one piece of work, and the state before it put back after (a command
    called from Python — sdem.api, a test — leaves the process as it found it)."""
    def __init__(self, folder): self.folder = folder
    def __enter__(self):
        from . import parts
        self._was = (ACTIVE, _ACTIVE_KEY, _RAW, list(ACTIVE_EXCEPTIONS), dict(parts._STATE))
        return activate_from(self.folder)
    def __exit__(self, *exc):
        global ACTIVE, _ACTIVE_KEY, _RAW, ACTIVE_EXCEPTIONS
        from . import parts, identity
        a, k, r, e, st = self._was
        changed = st != parts._STATE or a is not ACTIVE
        ACTIVE, _ACTIVE_KEY, _RAW, ACTIVE_EXCEPTIONS = a, k, r, e
        parts._STATE.clear(); parts._STATE.update(st)
        if changed:
            identity.changed()
            from . import conformance; conformance.model.cache_clear()
        return False


def activate_from(folder):
    """Activate the workspace folder's profile if it has one; otherwise SDEM's metamodel alone. Returns the merged profile or None."""
    from . import parts
    f = Path(folder) / FILE
    parts.for_workspace(folder)   # BX-10…BX-13 first: what the profile resolves to depends on it (BX-50)
    if f.exists():
        merged = activate_file(f); _load_exceptions(folder); parts.for_workspace(folder, merged); return _renumbered(merged)
    deactivate(); parts.for_workspace(folder); return None


def activate_from_paths(paths):
    """Datasets given as files: their folder's profile, when they share one."""
    folders = {Path(p).resolve().parent for p in paths if str(p).endswith('.json')}
    from . import parts
    ws = next((d for d in sorted(folders) if (d / 'workspace.json').exists()), None)   # DL-12: the files' workspace decides their form
    for d in sorted(folders):
        if (d / FILE).exists():
            merged = activate_file(d / FILE); _load_exceptions(d)
            if ws: parts.for_workspace(ws, merged)
            else: _form_of(folders)
            return _renumbered(merged)
    deactivate()
    if ws: parts.for_workspace(ws)
    else: _form_of(folders)
    return None


def _form_of(folders):
    """DL-10: files given without a workspace — their folder's form, by the names of its layer files (a bundled example)."""
    from . import parts
    from .identity import _ids_folder
    parts._set_form(any(_ids_folder(str(d)) for d in folders))


def activate_merged(merged):
    """A merged profile kept with a graph store: activate it as it was built."""
    global ACTIVE, _ACTIVE_KEY
    key = digest(merged)
    if key != _ACTIVE_KEY:
        ACTIVE, _ACTIVE_KEY = merged, key
        from . import conformance; conformance.model.cache_clear()
    return merged


def record():
    """What to note about the active profile (workspace.json, a graph store's load record)."""
    return None if ACTIVE is None else {'name': ACTIVE['name'], 'version': ACTIVE['version'], 'sha256': digest(ACTIVE), 'chain': [c['name'] for c in ACTIVE['chain']]}


# ------------------------------------------------------------------ the CLI

def _O19(layer_id):
    """DL-25: a layer's code in 0.19's numbering — what an organisation profile is written in."""
    from .identity import _index
    return _index()[0][layer_id]


def _T19(type_id):
    """DL-25: a type's 0.19 name — what an organisation profile is written in."""
    from .identity import _index
    return _index()[2][type_id].get('name_0_19') or type_id


EXAMPLE_BASE = _live(lambda: {
    'format': FORMAT, 'name': 'bank-base', 'version': 1,
    'description': "A made-up bank's standard specification on top of SDEM — the base every team's profile extends (synthetic; not a real organisation's).",
    'names': {'layers': {_O19('business'): 'L1 Business', _O19('bian'): 'L2 Service Domains', _O19('application'): 'L3 Applications', _O19('technology'): 'L4 Technology'},
              'types': {_T19('application.ApplicationComponent'): 'Application', _T19('technology.SystemSoftware'): 'Platform'}},
    'types': [
        {'type': 'BANK.A3.PaymentsMicroservice', 'extends': _T19('application.ApplicationComponent'), 'name': 'Payments microservice',
         'definition': 'An independently deployable payments service owned by one team', 'source': 'bank application standard §4.2'},
        {'type': 'BANK.A1.ControlFunction', 'extends': _T19('business.BusinessCapability'), 'name': 'Control function',
         'definition': 'A capability whose purpose is a regulatory or risk control', 'source': 'bank capability model §2'}],
    'attributes': [
        {'entity': _T19('application.ApplicationComponent'), 'name': 'risk_tier', 'type': 'enum', 'values': ['1', '2', '3'], 'required': True, 'description': 'the application risk tier (1 highest)'},
        {'entity': _T19('application.ApplicationComponent'), 'name': 'cost_centre', 'type': 'string', 'required': False, 'description': 'the cost centre that pays for it'},
        {'entity': 'BANK.A3.PaymentsMicroservice', 'name': 'owning_team', 'type': 'string', 'required': True, 'description': 'the team that owns the service'},
        {'entity': _T19('business.BusinessRequirement'), 'name': 'requirement_class', 'type': 'enum', 'values': ['functional', 'non_functional'], 'required': True,
         'description': "functional (what the business must be able to do) or non-functional (how well — measured in requirements.json); SDEM's own requirement_kind stays ArchiMate's requirement / constraint / principle"},
        {'entity': _T19('business.BusinessRequirement'), 'name': 'regulatory_reference', 'type': 'string', 'required': False, 'description': 'the regulation or policy clause it comes from'},
        {'entity': _T19('technology.InfrastructureComponent'), 'name': 'environment', 'type': 'enum', 'values': ['production', 'non_production'], 'required': False, 'description': 'production or not'},
        {'entity': _T19('technology.InfrastructureComponent'), 'name': 'dr_tier', 'type': 'enum', 'values': ['1', '2', '3'], 'required': False, 'description': 'the disaster recovery tier (1: hot standby)'},
        {'entity': _T19('technology.InfrastructureComponent'), 'name': 'dr_region', 'type': 'string', 'required': False, 'description': 'the region it runs in, for DR separation'},
        {'entity': _T19('technology.InfrastructureComponent'), 'name': 'replication_mode', 'type': 'enum', 'values': ['sync', 'async', 'none'], 'required': False, 'description': 'how its data reaches the DR pair'},
        {'entity': _T19('technology.InfrastructureComponent'), 'name': 'failover_tested_on', 'type': 'date', 'required': False, 'description': 'the last successful failover test'}],
    'rules': [{'id': 'BANK-R01', 'entity': _T19('application.ApplicationComponent'), 'require': ['owner', 'risk_tier'], 'message': 'every application names its owner and risk tier (bank application standard §3)'},
              {'id': 'BANK-DR01', 'entity': _T19('technology.InfrastructureComponent'), 'when': {'environment': 'production'}, 'require': ['dr_tier', 'dr_region', 'replication_mode'],
               'message': 'every production platform states its DR tier, region and replication (bank resilience standard §5)'},
              {'id': 'BANK-DR02', 'entity': _T19('technology.InfrastructureComponent'), 'when': {'environment': 'production', 'dr_tier': ['1', '2']}, 'link': {'kind': 'dr_pair_of', 'min': 1},
               'message': 'a tier 1 or 2 production platform has a DR pair (bank resilience standard §5.2)'},
              {'id': 'BANK-DR03', 'entity': _T19('technology.InfrastructureComponent'), 'compare': {'kind': 'dr_pair_of', 'attribute': 'dr_region', 'must': 'differ'},
               'message': 'a platform and its DR pair run in different regions (bank resilience standard §5.3)'}],
    'requirement_categories': [{'id': 'operational_resilience', 'description': 'tolerance for disruption of a critical operation (synthetic)'}],
    'link_kinds': [{'kind': 'dr_pair_of', 'maps_to': 'association', 'source_type': _T19('technology.InfrastructureComponent'), 'target_type': _T19('technology.InfrastructureComponent'),
                    'description': 'a platform and the platform it fails over to'},
                   {'kind': 'operated_by', 'maps_to': 'assignment', 'source_type': _T19('technology.InfrastructureComponent'), 'target_type': _T19('technology.InfrastructureComponent'),
                    'description': 'an infrastructure component is operated by a management platform'}]})

EXAMPLE_TEAM = {
    'format': FORMAT, 'name': 'payments-team', 'version': 1, 'extends': 'bank-base.json',
    'description': "The payments design team's additions to the bank base (synthetic).",
    'types': [{'type': 'BANK.A3.PaymentsGateway', 'extends': 'BANK.A3.PaymentsMicroservice', 'name': 'Payments gateway', 'definition': 'A payments microservice that fronts an external rail', 'source': 'payments design standard §1'}],
    'attributes': [{'entity': 'BANK.A3.PaymentsGateway', 'name': 'rail', 'type': 'enum', 'values': ['SWIFT', 'RTGS', 'Visa'], 'required': True, 'description': 'the external rail it connects to'}]}


# PR-13…PR-17: a made-up bank's standards and one reference-architecture pattern — synthetic, for the form only
EXAMPLE_SECURITY = _live(lambda: {
    'format': STANDARD_FORMAT, 'description': "A made-up bank's API security standard (synthetic; not a real organisation's).",
    'standard': {'id': 'SEC-API', 'title': 'API security standard', 'version': '3.1', 'owner': 'security architecture', 'source': 'synthetic example', 'effective_from': '2026-01-01'},
    'attributes': [{'entity': _T19('application.ApplicationComponent'), 'name': 'exposure', 'type': 'enum', 'values': ['internal', 'partner', 'external'], 'description': 'who may call it'},
                   {'entity': _T19('application.ApplicationComponent'), 'name': 'authentication', 'type': 'enum', 'values': ['none', 'api-key', 'oauth2-mtls', 'oauth2-pkjwt'], 'description': 'how callers are authenticated'}],
    'rules': [{'id': 'SEC-API-01', 'entity': _T19('application.ApplicationComponent'), 'when': {'exposure': ['partner', 'external']}, 'require': ['authentication'],
               'message': 'an application called from outside the bank authenticates its callers (API security standard §2)'},
              {'id': 'SEC-API-02', 'entity': _T19('application.ApplicationComponent'), 'when': {'exposure': 'external'}, 'check': {'attribute': 'authentication', 'op': 'in', 'value': ['oauth2-mtls', 'oauth2-pkjwt']},
               'message': 'an externally exposed application uses OAuth 2 with mTLS or private-key JWT (API security standard §2.3)'}]})
EXAMPLE_NETWORK = _live(lambda: {
    'format': STANDARD_FORMAT, 'description': "A made-up bank's network standard (synthetic).",
    'standard': {'id': 'NET', 'title': 'Network zoning and transport standard', 'version': '2.0', 'owner': 'network architecture', 'source': 'synthetic example', 'effective_from': '2026-01-01'},
    'attributes': [{'entity': _T19('technology.InfrastructureComponent'), 'name': 'network_zone', 'type': 'enum', 'values': ['restricted', 'internal', 'dmz'], 'description': 'the network zone it sits in'},
                   {'entity': _T19('technology.InfrastructureComponent'), 'name': 'monitoring', 'type': 'boolean', 'description': 'monitored by the bank\'s security operations'},
                   {'entity': _T19('technology.InfrastructureComponent'), 'name': 'encryption_in_transit', 'type': 'enum', 'values': ['none', 'tls1.2', 'tls1.3'], 'description': 'transport encryption'}],
    'rules': [{'id': 'NET-07', 'entity': _T19('application.ApplicationComponent'), 'when': {'risk_tier': '1'}, 'across': {'relationship': 'DEPLOYED_ON'},
               'check': {'attribute': 'network_zone', 'op': 'in', 'value': ['restricted']},
               'message': 'a tier 1 application runs only in the restricted zone (network standard §7)'},
              {'id': 'NET-09', 'entity': _T19('technology.InfrastructureComponent'), 'when': {'environment': 'production'}, 'check': {'attribute': 'encryption_in_transit', 'op': 'in', 'value': ['tls1.2', 'tls1.3']},
               'severity': 'warning', 'message': 'production platforms encrypt traffic in transit (network standard §9)'}]})
EXAMPLE_TECHNOLOGY = _live(lambda: {
    'format': STANDARD_FORMAT, 'description': "A made-up bank's technology lifecycle standard (synthetic).",
    'standard': {'id': 'TECH-LC', 'title': 'Technology lifecycle standard', 'version': '1.4', 'owner': 'technology architecture', 'source': 'synthetic example', 'effective_from': '2026-01-01'},
    'rules': [{'id': 'TECH-LC-01', 'entity': _T19('technology.SystemSoftware'), 'when': {'lifecycle_status': 'active'}, 'check': {'attribute': 'end_of_support', 'op': 'after', 'value': 'today+180d'},
               'severity': 'warning', 'message': 'software in use has at least six months of vendor support left (technology lifecycle standard §3)'}]})
EXAMPLE_PATTERN = _live(lambda: {
    'format': PATTERN_FORMAT, 'description': "A made-up bank's reference architecture: secure API integration (synthetic).",
    'pattern': {'id': 'PAT-SECURE-API', 'title': 'Secure API integration', 'version': '2.0', 'owner': 'enterprise architecture', 'source': 'synthetic example',
                'applies_when': {'entity': _T19('application.ApplicationComponent'), 'when': {'exposure': 'external'}}},
    'requires': [{'id': 'PAT-SECURE-API-1', 'rule': 'SEC-API-01'},
                 {'id': 'PAT-SECURE-API-2', 'rule': 'SEC-API-02'},
                 {'id': 'PAT-SECURE-API-3', 'within': {'kind': 'composition', 'direction': 'in', 'to': 'BANK.A3.APIGateway', 'min': 1},
                  'message': 'an externally exposed application sits behind the bank\'s API gateway'},
                 {'id': 'PAT-SECURE-API-4', 'across': {'relationship': 'DEPLOYED_ON'}, 'check': {'attribute': 'monitoring', 'op': '==', 'value': True},
                  'message': 'its platform is monitored by security operations'},
                 {'id': 'PAT-SECURE-API-5', 'across': {'relationship': 'DEPLOYED_ON'}, 'check': {'attribute': 'encryption_in_transit', 'op': '==', 'value': 'tls1.3'},
                  'message': 'its platform encrypts traffic with TLS 1.3'}]})
EXAMPLE_STANDARDS_PROFILE = _live(lambda: {
    'format': FORMAT, 'name': 'bank-with-standards', 'version': 1, 'extends': 'bank-base.json',
    'description': "A team profile that takes the made-up bank's standards and its secure API pattern (synthetic).",
    'includes': ['standards/example-security.json', 'standards/example-network.json', 'standards/example-technology.json', 'patterns/example-secure-api.json'],
    'types': [{'type': 'BANK.A3.APIGateway', 'extends': _T19('application.ApplicationComponent'), 'name': 'API gateway', 'definition': "The bank's API gateway, which fronts external APIs", 'source': 'synthetic example'}],
    'diagram_map': {   # PR-28: how sdem pattern extract reads the bank's pattern diagrams (examples/profiles/patterns/diagrams/)
        'shapes': [{'label': 'API Gateway', 'type': 'BANK.A3.APIGateway'}, {'stereotype': 'gateway', 'type': 'BANK.A3.APIGateway'},
                   {'label': 'Application', 'type': _T19('application.ApplicationComponent')}, {'label': 'Container platform', 'type': _T19('technology.SystemSoftware')},
                   {'label': 'Private network', 'type': _T19('technology.CommunicationNetwork')}, {'label': 'Secrets service', 'type': _T19('technology.TechnologyService')}],
        'connectors': [{'label': 'routes requests to', 'kind': 'flow'}, {'label': 'deployed on', 'relationship': 'DEPLOYED_ON'},
                       {'label': 'connected to', 'kind': 'association'}, {'label': 'serves', 'kind': 'serving'}],
        'zones': [{'label': 'Restricted zone', 'entity': _T19('technology.InfrastructureComponent'), 'check': {'attribute': 'network_zone', 'op': 'in', 'value': ['restricted']}},
                  {'label': 'DMZ', 'entity': _T19('technology.InfrastructureComponent'), 'check': {'attribute': 'network_zone', 'op': 'in', 'value': ['dmz']}}]}})


def adopt(a):
    """LR-03: an existing workspace takes up its sdem-profile.json — each layer the profile adds gets its empty file (recorded in the
    ledger), workspace.json notes the profile, and the decision is on record (adopt_profile, attributed). Existing records are never
    changed; what no longer meets the profile shows in sdem check."""
    import datetime
    from .validate import is_person
    from .layers import layers
    ws = Path(a.estate)
    if not is_person(a.person): raise ProfileError(f"--person {a.person!r}: adopting a profile is a person's decision — give your own name (CTL-21)")
    if not (ws / 'workspace.json').exists(): raise ProfileError(f'{ws}: no such workspace (sdem new starts one)')
    if not (ws / FILE).exists(): raise ProfileError(f'{ws}: no {FILE} — put the profile there first (sdem profile example shows the form)')
    merged = activate_from(ws)
    rec = _jload(ws / 'workspace.json')
    from .metamodel import Metamodel
    mm = Metamodel.load(); today = datetime.date.today().isoformat(); stem = re.sub(r'[^A-Z0-9]+', '-', ws.resolve().name.upper()).strip('-') or 'WORKSPACE'
    new = {l['file']: {'level': l['code'], 'model_id': f"{stem}-{l['code']}", 'model_version': today, 'metamodel_version': mm.version, 'source_system': 'SDEM', 'instances': [], 'relationships': []}
           for l in layers() if not l['core'] and not (ws / l['file']).exists()}
    out = {'workspace': str(ws), 'profile': record(), 'layers_added': sorted(new), 'dry_run': bool(a.dry_run)}
    if not a.dry_run:
        from .files import Batch, record as led
        from .governance import record as gd
        g = gd(ws, 'adopt_profile', a.person, merged['name'], {'version': merged['version'], 'sha256': digest(merged), 'reason': a.reason, 'layers_added': sorted(new)})
        b = Batch()
        for f, d in new.items(): b.json(ws / f, d)
        rec['profile'] = {'file': FILE, **record(), 'adopted_by': a.person, 'decision': g['id']}
        b.json(ws / 'workspace.json', rec); b.commit()
        if new: led([ws / f for f in new], by=f'{a.person} (sdem profile adopt, {g["id"]})', note=a.reason)
        out['decision'] = g['id']
    print(json.dumps(out, indent=2) if a.json else f"{'would adopt' if a.dry_run else 'adopted'} profile {merged['name']} v{merged['version']} in {ws}"
          + (f"; new empty layer file(s): {', '.join(sorted(new))}" if new else '; no new layers') + (f" — decision {out['decision']} (attributed)" if 'decision' in out else '')
          + f'\nNext — sdem check --workspace {ws} shows what does not yet meet the profile')
    return 0


def include_file(a):
    """PR-38: a person adds a standard or pattern to what the workspace's profile includes — a file shipped with SDEM ("sdem:<file>") or one
    of the organisation's (a path from the workspace). The profile is checked as it would be before anything is written; the decision is on
    record (include_in_profile, attributed). A workspace with no profile gets one that holds the include and nothing else."""
    import os, tempfile
    from .validate import is_person
    from .metamodel import Metamodel
    ws = Path(a.estate); name = a.file
    if not is_person(a.person): raise ProfileError(f"--person {a.person!r}: what a workspace's profile includes is a person's decision — give your own name (CTL-21)")
    from .layers import FILES
    if not any((ws / x).exists() for x in FILES.values()): raise ProfileError(f'{ws}: no such workspace (sdem new starts one)')
    if name.startswith(EXT):   # MX-10: switching on an installed metamodel extension in this workspace
        path, man = pack(name); pk = read(path)
        kind, meta = 'metamodel extension', {'id': name, 'title': man.get('description') or pk.get('name', name), 'version': man.get('version') or pk.get('version')}
    else:
        path = shipped(name) if name.startswith(SHIPPED) else (ws / name).resolve()
        kind, fd = _fragment(path); meta = fd[kind]
    f = ws / FILE
    doc = _jload(f) if f.exists() else {
        'format': FORMAT, 'name': ws.resolve().name, 'version': 1,
        'description': f"The {ws.resolve().name} workspace's design specification on top of SDEM's metamodel: the standards and patterns it includes."}
    there = f.exists() and (any(x['name'] == name for x in resolve(f).get('aspects', [])) if name.startswith(EXT) else any(x['file'] == path.resolve().as_posix() for x in resolve(f)['included']))   # by this profile, or by a base it extends
    out = {'workspace': str(ws), 'profile': FILE, 'included': [] if there else [name], 'kind': kind, 'id': meta['id'], 'title': meta['title'], 'version': meta['version'], 'dry_run': bool(a.dry_run)}
    if not there:
        cand = {**doc, 'includes': list(doc.get('includes', [])) + [name]}
        fd_, tmp = tempfile.mkstemp(dir=ws, prefix='.sdem-profile-', suffix='.json')   # checked where it will live: its includes and base are found from the workspace
        try:
            with os.fdopen(fd_, 'w', encoding='utf-8') as h: json.dump(cand, h)
            issues = check(renumber(resolve(tmp)), Metamodel.base())
        finally: os.unlink(tmp)
        if issues: raise ProfileError(f"{name}: with it the profile does not pass its check — nothing written: " + '; '.join(issues[:5]) + (f' (and {len(issues) - 5} more)' if len(issues) > 5 else ''))
        if not a.dry_run:
            from .files import Batch
            from .governance import record as gd
            g = gd(ws, 'include_in_profile', a.person, name, {'kind': kind, 'id': meta['id'], 'title': meta['title'], 'version': meta['version'], 'reason': a.reason})
            b = Batch(); b.json(f, cand)
            if (ws / 'workspace.json').exists():
                rec = _jload(ws / 'workspace.json'); before = json.dumps(rec, sort_keys=True)
                if not rec.get('profile'): rec['profile'] = {'file': FILE, 'from': 'sdem', 'name': cand['name'], 'version': cand['version']}
                if name == 'ext:bian': rec.pop('core_only', None)   # BX-10: BIAN on again
                if json.dumps(rec, sort_keys=True) != before: b.json(ws / 'workspace.json', rec)
            b.commit(); out['decision'] = g['id']
    if a.json: print(json.dumps(out, indent=2))
    elif there: print(f"{name} ({meta['title']}) is already included in {ws}'s profile — nothing to do")
    else: print(f"{'would include' if a.dry_run else 'included'} {name} — the {kind} {meta['id']} {meta['title']} v{meta['version']} — in {ws / FILE}"
                + (f" — decision {out['decision']} (attributed)" if 'decision' in out else '') + f'\nNext — sdem status --workspace {ws} says where the design stands against it'
                + ('\nIf the design is published (e.g. to DESNRE), the published copy changes only when you publish it again (EL-04, EL-05).' if name.startswith(EXT) else ''))
    return 0


def exclude_file(a):
    """MX-16: a person switches a standard, a pattern or a metamodel extension off again — the counterpart of include (PR-38, MX-10).
    For a part that adds layers (e.g. ext:security, or a pack the workspace carries as a file), the layer files, every connection that
    touches their records and the exceptions that name them leave the design together, kept whole in a new archive file
    (archive/<name>-<date>[-n].json — never overwriting one); the connections' ids are kept as retired, so no new link takes one. The
    change is made first on a copy of the workspace and checked there: if the design would not pass, nothing is written."""
    import contextlib, datetime, io, shutil, tempfile
    from .validate import is_person
    ws = Path(a.estate); name = a.file
    if not is_person(a.person): raise ProfileError(f"--person {a.person!r}: what a workspace's profile includes is a person's decision — give your own name (CTL-21)")
    if not (a.reason or '').strip(): raise ProfileError('--reason is required: why it is switched off (kept with the decision)')
    f = ws / FILE
    if not f.exists(): raise ProfileError(f'{ws}: no sdem-profile.json — nothing is included')
    doc = _jload(f)
    if name not in (doc.get('includes') or []): raise ProfileError(f"{name} is not included in {ws}'s profile ({', '.join(doc.get('includes') or []) or 'it includes nothing'})")
    if name.startswith(EXT):
        try: path, _ = pack(name); layers = read(path).get('layers') or []
        except ProfileError as e: raise ProfileError(f'{e} — install it again to switch it off cleanly: its layers and their connections are found from its pack')
    else:   # a standard, a pattern, or a pack the workspace carries as a file (a published copy): its own layers, if it adds any
        pf = (ws / name) if not name.startswith(SHIPPED) else None
        try: layers = (read(pf).get('layers') or []) if pf is not None and pf.is_file() and read(pf).get('format') == FORMAT else []
        except (OSError, ValueError, ProfileError): layers = []
    from . import parts
    if name == parts.EXT_BIAN: layers = [{'code': parts.a2_code(), 'file': parts.A2_FILE}]   # BX-14: BIAN's layer is the reserved A2
    files = [l['file'] for l in layers if l.get('file') and (ws / l['file']).exists()]
    gone = {i['id'] for fn in files for i in _jload(ws / fn).get('instances', [])}
    reg_f = ws / 'mappings.json'
    reg = _jload(reg_f) if reg_f.exists() else None
    out_maps = [m for m in (reg or {}).get('mappings', []) if m['source']['id'] in gone or m['target']['id'] in gone]
    ex_f = ws / 'exceptions.json'; exc = _jload(ex_f) if ex_f.exists() else None
    out_exc = [e for e in (exc or {}).get('exceptions', []) if set(e.get('records') or []) & gone]   # an exception for an archived record goes with it
    keep = {**doc, 'includes': [i for i in doc['includes'] if i != name]}
    day = datetime.date.today().isoformat(); tag = re.sub(r'[^a-z0-9-]+', '-', name.lower()).strip('-')
    arc_name, n = f'archive/{tag}-{day}.json', 2
    while (ws / arc_name).exists(): arc_name = f'archive/{tag}-{day}-{n}.json'; n += 1   # AUD-24: never over an earlier archive
    out = {'workspace': str(ws), 'excluded': name, 'layers_removed': [l['code'] for l in layers], 'files_archived': files, 'records': len(gone),
           'connections_retired': [m['mapping_id'] for m in out_maps], 'exceptions_archived': [e.get('id') for e in out_exc], 'archive': arc_name, 'dry_run': bool(a.dry_run)}
    from .approve import RETIRED
    def write(root, decision):
        from .files import Batch
        arc = {'format': 'sdem-archive/1', 'excluded': name, 'reason': a.reason.strip(), 'by': a.person.strip(), 'decision': decision, 'at': day,
               'files': {fn: _jload(ws / fn) for fn in files}, 'mappings': out_maps, 'exceptions': out_exc,
               'note': 'Switched off by a person (sdem profile exclude, MX-16). To switch it on again: sdem profile include, sdem profile adopt, then restore these files and connections.'}
        rf = root / RETIRED
        ret = _jload(rf) if rf.exists() else {'format': 'sdem-retired-mappings/1', 'note': 'Connections taken out of mappings.json when a layer was switched off; their ids are never given again.', 'mappings': []}
        ret['mappings'] += [{'mapping_id': m['mapping_id'], 'archive': arc_name, 'decision': decision} for m in out_maps]
        b = Batch(); b.json(root / arc_name, arc); b.json(rf, ret); b.json(root / FILE, keep)
        if name == parts.EXT_BIAN and (root / 'workspace.json').exists():   # BX-13, BX-14: a person chose a core-only design
            wrec = _jload(root / 'workspace.json'); wrec['core_only'] = True; b.json(root / 'workspace.json', wrec)
        if reg is not None and out_maps: b.json(root / 'mappings.json', {**reg, 'mappings': [m for m in reg['mappings'] if m not in out_maps]})
        if exc is not None and out_exc: b.json(root / 'exceptions.json', {**exc, 'exceptions': [e for e in exc['exceptions'] if e not in out_exc]})
        b.commit()
        for fn in files: (root / fn).unlink()
    # AUD-26: try it on a copy first — the design must pass its check without the part, or nothing is written
    with tempfile.TemporaryDirectory() as t:
        trial = Path(t) / ws.resolve().name; shutil.copytree(ws, trial, ignore=shutil.ignore_patterns('graph', '.git'))
        write(trial, 'trial')
        from .cli import main as graph_main   # sdem check, in this process — SDEM starts no program it does not name (privacy)
        so, se = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(so), contextlib.redirect_stderr(se): graph_main(['check', '--workspace', str(trial), '--json'])
        except SystemExit: pass
        finally: deactivate()   # the trial's profile was active while it was checked
        try: ok = json.loads(so.getvalue()).get('ok')
        except ValueError: ok = False
        if not ok:
            why = '; '.join(ln.strip() for ln in (so.getvalue() + se.getvalue()).splitlines() if ln.strip().startswith('ERROR'))[:600] or (se.getvalue() or so.getvalue()).strip()[-400:]
            raise ProfileError(f'{name}: without it the design would not pass its check — nothing written: {why}')
    if not a.dry_run:
        from .files import record as ledger
        from .governance import record as gd
        g = gd(ws, 'exclude_from_profile', a.person, name, {'reason': a.reason.strip(), 'layers': out['layers_removed'], 'records': len(gone),
                                                          'connections_retired': out['connections_retired'], 'archive': arc_name})
        write(ws, g['id'])
        ledger([f] + ([reg_f] if out_maps else []) + ([ex_f] if out_exc else []), by=f"{a.person.strip()} (sdem profile exclude, {g['id']})", note=a.reason.strip())
        out['decision'] = g['id']
    if a.json: print(json.dumps(out, indent=2))
    else: print(f"{'would switch off' if a.dry_run else 'switched off'} {name} in {ws} (checked: the design passes without it): "
                + (f"layer(s) {', '.join(out['layers_removed'])} ({out['records']} record(s)), {len(out_maps)} connection(s) and {len(out_exc)} exception(s) kept in {arc_name}" if layers else 'no layers to remove')
                + (f" — decision {out['decision']} (attributed)" if 'decision' in out else '') + f'\nNext — sdem check --workspace {ws}\nIf the design is published (e.g. to DESNRE), the published copy changes only when you publish it again (EL-04, EL-05).')
    return 0


def _check_copy(ws, apply_to):
    """Make a change on a copy of the workspace and run sdem check there, in this process: (ok, why)."""
    import contextlib, io, shutil, tempfile
    with tempfile.TemporaryDirectory() as t:
        trial = Path(t) / Path(ws).resolve().name; shutil.copytree(ws, trial, ignore=shutil.ignore_patterns('graph', '.git'))
        apply_to(trial)
        from .cli import main as sdem_main
        so, se = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(so), contextlib.redirect_stderr(se): sdem_main(['check', '--workspace', str(trial), '--json'])
        except SystemExit: pass
        finally: deactivate()
        try: ok = json.loads(so.getvalue()).get('ok')
        except ValueError: ok = False
        why = '; '.join(ln.strip() for ln in (so.getvalue() + se.getvalue()).splitlines() if ln.strip().startswith('ERROR'))[:600] or (se.getvalue() or so.getvalue()).strip()[-400:]
        return bool(ok), why


def restore_file(a):
    """EL-06: a person switches an extension on again from one of its archives (MX-16) — the include back in the profile, its layer
    files, the connections (with their old ids, never given to others) and the exceptions. Tried on a copy and checked first. A
    connection whose other end has since left the design does not fit: refused, listed, or left in the archive with --skip-unfit."""
    import datetime
    from .validate import is_person
    from .approve import RETIRED
    from .layers import FILES
    ws = Path(a.estate); af = (ws / a.archive) if not Path(a.archive).is_absolute() else Path(a.archive)
    if not is_person(a.person): raise ProfileError(f"--person {a.person!r}: restoring is a person's decision — give your own name (CTL-21)")
    if not (a.reason or '').strip(): raise ProfileError('--reason is required: why it is switched on again')
    if not af.is_file(): raise ProfileError(f'{a.archive}: no such archive in {ws} (sdem profile exclude writes them to archive/)')
    arc = _jload(af)
    if arc.get('format') != 'sdem-archive/1': raise ProfileError(f'{a.archive}: not an SDEM archive')
    if arc.get('restored'): raise ProfileError(f"{a.archive}: already restored on {arc['restored'].get('at')} ({arc['restored'].get('decision')})")
    name = arc['excluded']; f = ws / FILE; doc = _jload(f) if f.exists() else {'format': FORMAT, 'name': ws.resolve().name, 'version': 1, 'includes': []}
    if name in (doc.get('includes') or []): raise ProfileError(f'{name} is already included in {ws} — restore puts back a part that was switched off')
    if name.startswith(EXT): pack(name)   # installed and supported (MX-11a) — or refused here, with the reason
    busy = [fn for fn in arc.get('files', {}) if (ws / fn).exists() and _jload(ws / fn).get('instances')]
    if busy: raise ProfileError(f"{', '.join(busy)} already hold(s) records — restore does not merge into a layer that has been started again")
    have = {i['id'] for fn in FILES.values() if (ws / fn).exists() for i in _jload(ws / fn).get('instances', [])}
    have |= {i['id'] for d in arc.get('files', {}).values() for i in d.get('instances', [])}
    unfit = [m for m in arc.get('mappings', []) if m['source']['id'] not in have or m['target']['id'] not in have]
    if unfit and not a.skip_unfit:
        raise ProfileError(f"{len(unfit)} archived connection(s) no longer fit — a record they join has left the design: "
                           + ', '.join(f"{m['mapping_id']} ({m['source']['id']} {m['relationship']} {m['target']['id']})" for m in unfit[:10])
                           + ' — restore the rest with --skip-unfit (those stay in the archive)')
    back = [m for m in arc.get('mappings', []) if m not in unfit]
    exc_back = [e for e in arc.get('exceptions', []) if set(e.get('records') or []) <= have]
    day = datetime.date.today().isoformat()
    out = {'workspace': str(ws), 'restored': name, 'archive': str(a.archive), 'files': sorted(arc.get('files', {})), 'connections': [m['mapping_id'] for m in back],
           'left_in_archive': [m['mapping_id'] for m in unfit], 'exceptions': [e.get('id') for e in exc_back], 'dry_run': bool(a.dry_run)}
    def write(root, decision):
        from .files import Batch
        b = Batch()
        pf = root / FILE; pd = _jload(pf) if pf.exists() else dict(doc)
        b.json(pf, {**pd, 'includes': list(pd.get('includes') or []) + [name]})
        for fn, d in arc.get('files', {}).items(): b.json(root / fn, d)
        rf = root / 'mappings.json'; reg = _jload(rf) if rf.exists() else {'mappings': []}
        b.json(rf, {**reg, 'mappings': reg['mappings'] + back})
        if exc_back:
            ef = root / 'exceptions.json'; ex = _jload(ef) if ef.exists() else {'format': 'sdem-exceptions/1', 'exceptions': []}
            b.json(ef, {**ex, 'exceptions': ex['exceptions'] + exc_back})
        rt = root / RETIRED
        if rt.exists():   # the restored ids are live again; the ones left in the archive stay retired
            ret = _jload(rt); ids = {m['mapping_id'] for m in back}
            b.json(rt, {**ret, 'mappings': [m for m in ret['mappings'] if m['mapping_id'] not in ids]})
        b.json(root / af.relative_to(ws) if af.is_relative_to(ws) else af, {**arc, 'restored': {'at': day, 'decision': decision, 'by': a.person.strip(), 'left_in_archive': out['left_in_archive']}})
        if name == 'ext:bian' and (root / 'workspace.json').exists():   # BX-10: BIAN on again
            wrec = _jload(root / 'workspace.json')
            if wrec.pop('core_only', None) is not None: b.json(root / 'workspace.json', wrec)
        b.commit()
    ok, why = _check_copy(ws, lambda t: write(t, 'trial'))
    if not ok: raise ProfileError(f'{name}: restored, the design would not pass its check — nothing written: {why}')
    if not a.dry_run:
        from .files import record as ledger
        from .governance import record as gd
        g = gd(ws, 'restore_from_archive', a.person, name, {'reason': a.reason.strip(), 'archive': str(a.archive), 'connections': out['connections'], 'left_in_archive': out['left_in_archive']})
        write(ws, g['id'])
        ledger([f, ws / 'mappings.json'] + [ws / fn for fn in arc.get('files', {})] + ([ws / 'exceptions.json'] if exc_back else []), by=f"{a.person.strip()} (sdem profile restore, {g['id']})", note=a.reason.strip())
        out['decision'] = g['id']
    print(json.dumps(out, indent=2) if a.json else
          f"{'would restore' if a.dry_run else 'restored'} {name} in {ws} from {a.archive} (checked): {len(out['files'])} layer file(s), {len(back)} connection(s), {len(exc_back)} exception(s)"
          + (f"; {len(unfit)} connection(s) left in the archive" if unfit else '') + (f" — decision {out['decision']} (attributed)" if 'decision' in out else '') + '\nIf the design is published (e.g. to DESNRE), the published copy changes only when you publish it again (EL-04, EL-05).')
    return 0


def purge_file(a):
    """EL-16, EL-17: a person deletes the archived data of a part that was switched off — one archive, or every archive of a name.
    Never the default, never part of switching off. The link ids stay retired; the decision records what was deleted, not its content.
    It says what it cannot reach: the workspace's git history, and copies people downloaded."""
    from .validate import is_person
    from .approve import RETIRED
    ws = Path(a.estate)
    if not is_person(a.person): raise ProfileError(f"--person {a.person!r}: purging data is a person's decision — give your own name (CTL-21)")
    if not (a.reason or '').strip(): raise ProfileError('--reason is required: why the data is deleted (kept with the decision)')
    arcs = sorted((ws / 'archive').glob('*.json')) if (ws / 'archive').is_dir() else []
    arcs = [p for p in arcs if p.name != Path(RETIRED).name and (_jload(p).get('format') == 'sdem-archive/1')]
    pick = [p for p in arcs if (a.archive and (p == ws / a.archive or p.name == Path(a.archive).name)) or (a.file and _jload(p).get('excluded') == a.file)]
    if not (a.archive or a.file): raise ProfileError('name what to purge: an archive (--archive archive/<file>.json) or every archive of a part (e.g. ext:security)')
    if not pick: raise ProfileError(f"nothing to purge in {ws}: no archive {'of ' + a.file if a.file else a.archive}")
    summ = []
    for p in pick:
        d = _jload(p)
        summ.append({'archive': p.relative_to(ws).as_posix(), 'excluded': d.get('excluded'), 'records': sum(len(x.get('instances', [])) for x in d.get('files', {}).values()),
                     'connections': len(d.get('mappings', [])), 'exceptions': len(d.get('exceptions', [])), 'restored': bool(d.get('restored'))})
    out = {'workspace': str(ws), 'purged': summ, 'dry_run': bool(a.dry_run),
           'not_reached': ["the workspace's git history, if it is kept in git — SDEM never rewrites it", 'copies people downloaded or exported',
                           'a published copy (e.g. DESNRE): its previous version and document history — the publisher asks the site on the next publish (EL-16)']}
    if not a.dry_run:
        from .governance import record as gd
        from .files import Batch
        g = gd(ws, 'purge_extension_data', a.person, ', '.join(sorted({x['excluded'] or '?' for x in summ})), {'reason': a.reason.strip(), 'archives': [x['archive'] for x in summ],
               'counts': [{k: x[k] for k in ('records', 'connections', 'exceptions')} for x in summ]})
        rt = ws / RETIRED
        if rt.exists():   # the ids stay retired — only the pointer to the deleted archive goes
            ret = _jload(rt); gone = {x['archive'] for x in summ}
            b = Batch(); b.json(rt, {**ret, 'mappings': [({**m, 'archive': None, 'purged': g['id']} if m.get('archive') in gone else m) for m in ret['mappings']]}); b.commit()
        for p in pick: p.unlink()
        out['decision'] = g['id']
    print(json.dumps(out, indent=2) if a.json else
          f"{'would delete' if a.dry_run else 'deleted'} " + '; '.join(f"{x['archive']} ({x['records']} record(s), {x['connections']} connection(s), {x['exceptions']} exception(s))" for x in summ)
          + (f" — decision {out['decision']} (attributed; it keeps no archived content)" if 'decision' in out else '')
          + '\nNot reached by this command: ' + '; '.join(out['not_reached']) + '.')
    return 0


def describe(r):
    """A rule in words: 'A4.InfrastructureComponent where environment = production requires dr_tier, dr_region'."""
    out = r['entity']
    if r.get('when'): out += ' where ' + ' and '.join(f"{k} {'in ' + str(v) if isinstance(v, list) else '= ' + str(v)}" for k, v in r['when'].items())
    parts = []
    if r.get('require'): parts.append('requires ' + ', '.join(r['require']))
    if r.get('link'): l = r['link']; parts.append(f"has ≥{l.get('min', 1)} {l['kind']} link(s) {'from' if l.get('direction') == 'in' else 'to'} {l.get('to', 'any record')}")
    if r.get('any_link'): parts.append('has at least one of: ' + ' · '.join((('approved ' + l['relationship']) if l.get('relationship') else l['kind']) + (' from ' if l.get('direction') == 'in' else ' to ') + l.get('to', 'any record') for l in r['any_link']))
    if r.get('compare'): c = r['compare']; parts.append(f"{c['attribute']} must {c['must']} across {c['kind']}")
    if r.get('across'):
        a = r['across']; parts.append(f"has ≥{a.get('min', 1)} approved {a['relationship']} link(s)" + (f", each with {r['check']['attribute']} {r['check']['op']} {r['check'].get('value')}" if r.get('check') else ''))
    elif r.get('check'): c = r['check']; parts.append(f"{c['attribute']} {c['op']} {c.get('value')}")
    tags = [x for x in ((r.get('standard') or {}).get('id'), (r.get('pattern') or {}).get('id')) if x]
    return out + ' ' + '; '.join(parts) + (f" [{', '.join(tags)}]" if tags else '') + (' (warning)' if r.get('severity') == 'warning' else '')


EXAMPLE_LAYERS = _live(lambda: {
    'format': FORMAT, 'name': 'strategy-and-sites-team', 'version': 1, 'extends': 'bank-base.json',
    'description': 'A design team that also models strategy above the business layer and physical sites below technology (synthetic).',
    'layers': [{'code': 'A0', 'name': 'A0 Strategy', 'position': 'above', 'file': 'a0-strategy.json', 'description': 'goals and outcomes the business pursues', 'source': 'ArchiMate 3.2 ch. 6 Motivation and ch. 7 Strategy'},
               {'code': 'A5', 'name': 'A5 Physical', 'position': 'below', 'file': 'a5-physical.json', 'description': 'sites and equipment technology runs in', 'source': 'ArchiMate 3.2 ch. 11 Physical'}],
    'types': [{'type': 'BANK.A0.Goal', 'name': 'Goal', 'definition': 'An end state the organisation intends to achieve', 'source': 'ArchiMate 3.2 ch. 6 Goal'},
              {'type': 'BANK.A0.Outcome', 'name': 'Outcome', 'definition': 'An end result a goal is measured by', 'source': 'ArchiMate 3.2 ch. 6 Outcome'},
              {'type': 'BANK.A5.Facility', 'name': 'Facility', 'definition': 'A physical site — a data centre or office — that houses equipment', 'source': 'ArchiMate 3.2 ch. 11 Facility'},
              {'type': 'BANK.A5.Equipment', 'name': 'Equipment', 'definition': 'Physical machinery or devices', 'source': 'ArchiMate 3.2 ch. 11 Equipment'}],
    'attributes': [{'entity': 'BANK.A5.Facility', 'name': 'region', 'type': 'string', 'required': True, 'description': 'the region the site is in'},
                   {'entity': 'BANK.A0.Outcome', 'name': 'target_date', 'type': 'date', 'required': False, 'description': 'when the outcome is due'}],
    'link_kinds': [{'kind': 'realization', 'maps_to': 'realization', 'source_type': 'BANK.A0.Outcome', 'target_type': 'BANK.A0.Goal', 'description': 'an outcome realises a goal'},
                   {'kind': 'composition', 'maps_to': 'composition', 'source_type': 'BANK.A5.Facility', 'target_type': 'BANK.A5.Equipment', 'description': 'a facility contains equipment'}],
    'link_types': [{'source_type': 'BANK.A0.Outcome', 'relationship': 'REALIZED_BY', 'target_type': _T19('business.BusinessCapability'), 'required_evidence': ['strategy_document'],
                    'description': 'the capability realises the outcome', 'source': 'ArchiMate 3.2 ch. 7 (a capability realises an outcome)'},
                   {'source_type': _T19('technology.InfrastructureComponent'), 'relationship': 'HOUSED_IN', 'target_type': 'BANK.A5.Facility', 'required_evidence': ['site_register'],
                    'description': 'the platform runs in the facility', 'source': 'ArchiMate 3.2 ch. 11 (a node is assigned to a facility)'}]})


def main(argv=None):
    from .metamodel import Metamodel
    ap = argparse.ArgumentParser(prog='sdem profile', formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description="An organisation's design specification on top of SDEM's metamodel: its own types (extending SDEM's), attributes, rules, "
                                             'within-layer link kinds and names — in the workspace\'s sdem-profile.json, optionally extending a shared base profile.',
                                 epilog='Examples:\n  sdem profile example --out profiles            # a synthetic bank base and team profile\n'
                                        '  sdem profile check --workspace workspaces/payments\n  sdem profile show --workspace workspaces/payments')
    sub = ap.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('check', help='check the workspace\'s profile (and the base it extends) against SDEM\'s metamodel')
    c.add_argument('--workspace', dest='estate', metavar='DIR'); c.add_argument('--file', metavar='FILE', help='a profile file instead of a workspace'); c.add_argument('--json', action='store_true')
    s = sub.add_parser('show', help='the merged profile: every type, attribute, rule, link kind and name it adds')
    s.add_argument('--workspace', dest='estate', metavar='DIR'); s.add_argument('--file', metavar='FILE'); s.add_argument('--json', action='store_true')
    d = sub.add_parser('adopt', help="put the workspace under its sdem-profile.json: the layers it adds start empty, and the adoption is recorded — a person's decision")
    d.add_argument('--workspace', dest='estate', required=True, metavar='DIR'); d.add_argument('--person', required=True, help='your name — a person')
    d.add_argument('--reason', required=True); d.add_argument('--dry-run', action='store_true'); d.add_argument('--json', action='store_true')
    i = sub.add_parser('include', help="add a standard or pattern to what the workspace's profile includes — one shipped with SDEM (sdem:<file>), the organisation's own, or an installed metamodel extension (ext:<name>, MX-10) — a person's decision (PR-38)")
    i.add_argument('file', metavar='FILE', help='"sdem:<file>" for a standard or pattern shipped with SDEM, "ext:<name>" for an installed metamodel extension (e.g. ext:security), or a path from the workspace folder')
    i.add_argument('--workspace', dest='estate', required=True, metavar='DIR'); i.add_argument('--person', required=True, help='your name — a person')
    i.add_argument('--reason', help='why (kept with the decision)'); i.add_argument('--dry-run', action='store_true'); i.add_argument('--json', action='store_true')
    x = sub.add_parser('exclude', help="switch a standard, pattern or metamodel extension off again — its layers and their connections are archived, not lost (MX-16)")
    x.add_argument('file', metavar='FILE', help='as it is written in the profile\'s includes, e.g. ext:security')
    x.add_argument('--workspace', dest='estate', required=True, metavar='DIR'); x.add_argument('--person', required=True, help='your name — a person')
    x.add_argument('--reason', required=True); x.add_argument('--dry-run', action='store_true'); x.add_argument('--json', action='store_true')
    rs = sub.add_parser('restore', help="switch a part back on from one of its archives — layers, connections (their old ids) and exceptions, checked first (EL-06)")
    rs.add_argument('--archive', required=True, metavar='FILE', help='archive/<name>-<date>.json, as sdem profile exclude wrote it')
    rs.add_argument('--workspace', dest='estate', required=True, metavar='DIR'); rs.add_argument('--person', required=True, help='your name — a person')
    rs.add_argument('--reason', required=True); rs.add_argument('--skip-unfit', action='store_true', help='leave in the archive the connections whose other end has left the design')
    rs.add_argument('--dry-run', action='store_true'); rs.add_argument('--json', action='store_true')
    pg = sub.add_parser('purge', help="delete the archived data of a part that was switched off — never the default; the ids stay retired (EL-16)")
    pg.add_argument('file', nargs='?', metavar='FILE', help='every archive of this part, e.g. ext:security'); pg.add_argument('--archive', metavar='FILE', help='one archive')
    pg.add_argument('--workspace', dest='estate', required=True, metavar='DIR'); pg.add_argument('--person', required=True, help='your name — a person')
    pg.add_argument('--reason', required=True); pg.add_argument('--dry-run', action='store_true'); pg.add_argument('--json', action='store_true')
    e = sub.add_parser('example', help='write a synthetic bank base profile, team profiles that extend it (one adds layers), and a team profile with the bank\'s standards and secure API pattern')
    e.add_argument('--out', required=True, metavar='DIR'); e.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    try:
        if a.cmd == 'example':
            from .files import Batch
            out = Path(a.out); b = Batch(); written = []
            for name, doc in (('bank-base.json', EXAMPLE_BASE), ('payments-team.json', EXAMPLE_TEAM), ('strategy-and-sites-team.json', EXAMPLE_LAYERS),
                              ('standards/example-security.json', EXAMPLE_SECURITY), ('standards/example-network.json', EXAMPLE_NETWORK),
                              ('standards/example-technology.json', EXAMPLE_TECHNOLOGY), ('patterns/example-secure-api.json', EXAMPLE_PATTERN),
                              ('bank-with-standards.json', EXAMPLE_STANDARDS_PROFILE)):
                b.json(out / name, doc); written.append(str(out / name))
            b.commit()
            print(json.dumps({'written': written}) if a.json else
                  f'wrote {", ".join(written)} (synthetic) — start a workspace with one: sdem new --workspace <dir> --person <you> --profile {written[1]}')
            return 0
        if a.cmd == 'adopt': return adopt(a)
        if a.cmd == 'include': return include_file(a)
        if a.cmd == 'exclude': return exclude_file(a)
        if a.cmd == 'restore': return restore_file(a)
        if a.cmd == 'purge': return purge_file(a)
        path = Path(a.file) if a.file else Path(a.estate or '.') / FILE
        if not a.file and not a.estate: raise ProfileError('give --workspace DIR or --file FILE')
        merged = renumber(resolve(path)); issues = check(merged, Metamodel.base())
        if a.cmd == 'check':
            if a.json: print(json.dumps({'ok': not issues, 'profile': merged['name'], 'chain': merged['chain'], 'issues': issues}, indent=2)); return 1 if issues else 0
            for i in issues: print(f'ERROR: {i}')
            if not issues: print(f"OK: profile {merged['name']} v{merged['version']} ({' → '.join(c['name'] for c in merged['chain'])}): {len(merged['types'])} type(s), {len(merged['attributes'])} attribute(s), "
                                 f"{len(merged['rules'])} rule(s), {len(merged['link_kinds'])} link kind(s), {len(merged['requirement_categories'])} requirement categor(ies), {len(merged['layers'])} added layer(s), {len(merged['link_types'])} link type(s)")
            return 1 if issues else 0
        if a.json: print(json.dumps(merged, indent=2, ensure_ascii=False)); return 0
        print(f"profile {merged['name']} v{merged['version']} — chain: {' → '.join(c['name'] for c in merged['chain'])}")
        for x in merged.get('included', []): print(f"  {x['kind']:<10} {x['id']:<16} v{x['version']:<6} {x['title']} — owner {x['owner']}")
        for t in merged['types']: print(f"  type       {t['type']:<36} extends {t.get('extends') or '—':<28} {t.get('definition', '')[:60]}")
        for x in merged['attributes']: print(f"  attribute  {x['entity'] + '.' + x['name']:<44} {x['type']:<16} {'required' if x.get('required') else 'optional'}" + (f"  values {x['values']}" if x.get('values') else ''))
        for r in merged['rules']: print(f"  rule       {r['id']:<12} {describe(r)} — {r.get('message', '')}")
        for c in merged['requirement_categories']: print(f"  category   {c['id']:<20} {c.get('description', '')}")
        for k in merged['link_kinds']: print(f"  link kind  {k['kind']:<20} {k['source_type']} → {k['target_type']}  (ArchiMate {k['maps_to']})")
        for l in merged['layers']: print(f"  layer      {l['code']:<6} {l['name']:<20} {l['position']} the core, file {l['file']} — {l.get('description', '')}")
        for x in merged['link_types']: print(f"  link type  {x['source_type']} {x['relationship']} {x['target_type']}  (evidence: {', '.join(x['required_evidence'])})")
        for l, n in merged['names']['layers'].items(): print(f'  name       {l} → {n}')
        for t, n in merged['names']['types'].items(): print(f'  name       {t} → {n}')
        for st in merged.get('structures', []):   # PR-21
            S = st['structure']
            print(f"  structure  {st['pattern']['id']}: {len(S['roles'])} part(s), {len(S.get('connectors', []))} connector(s), {len(S.get('zones', []))} zone(s), anchor {S.get('anchor')}  ({st['file']})")
        for o in (merged.get('hosting') or {}).get('signal_overrides') or []:   # PR-33
            print(f"  hosting    signal {o['id']} {'off' if o.get('off') else 'confidence ' + str(o.get('confidence'))} — {o.get('reason', '')}")
        dm = merged.get('diagram_map') or {}
        if any(dm.values()):   # PR-28
            print(f"  diagram    map: {len(dm.get('shapes', []))} shape(s), {len(dm.get('connectors', []))} connector label(s), {len(dm.get('zones', []))} zone(s) — read by sdem pattern extract")
        if issues: print('ISSUES:\n  ' + '\n  '.join(issues))
        return 1 if issues else 0
    except ProfileError as err:
        from .errors import note
        note('invalid_input' if 'does not pass' in str(err) or 'not an SDEM profile' in str(err) else 'not_found' if 'no such' in str(err) else 'input', f'sdem profile check --file {FILE}')
        print(f'ERROR: {err}', file=sys.stderr); return 2
