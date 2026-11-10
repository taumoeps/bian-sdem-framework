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
import argparse, copy, hashlib, json, re, sys
from pathlib import Path

from .paths import DATA_ROOT

FILE = 'sdem-profile.json'
FORMAT = 'sdem-profile/1'
STANDARD_FORMAT, PATTERN_FORMAT = 'sdem-standard/1', 'sdem-pattern/1'   # files a profile includes (PR-13, PR-17)
EXCEPTIONS_FILE = 'exceptions.json'                                     # a workspace's granted exceptions (PR-18)
PRIVATE = ('chain', 'included', '_issues', '_origin')                   # kept with the merged profile, not part of its content
SCHEMA = DATA_ROOT / 'schema' / 'profile.schema.json'
LEVELS = ('A1', 'A2', 'A3', 'A4')
ATTR_TYPES = ('string', 'integer', 'number', 'boolean', 'date', 'enum', 'list<string>', 'map<string,string>')
MAP_KINDS = ('shapes', 'connectors', 'zones')   # PR-28: the diagram mapping table — the organisation's shapes, connector labels and zones
LISTS = ('layers', 'types', 'attributes', 'rules', 'link_kinds', 'link_types', 'requirement_categories')   # what a profile adds to its base
ACTIVE = None          # the resolved, merged profile the current command works under (None: SDEM's metamodel alone)
_ACTIVE_KEY = None     # its content hash — the metamodel cache key
ACTIVE_EXCEPTIONS = []  # the active workspace's granted exceptions (PR-18)


class ProfileError(ValueError):
    pass


# ------------------------------------------------------------------ reading and resolving

def read(path):
    path = Path(path)
    try: doc = json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError: raise ProfileError(f'{path}: no such profile')
    except ValueError as e: raise ProfileError(f'{path}: not valid JSON — {e}')
    if doc.get('format') != FORMAT: raise ProfileError(f"{path}: not an SDEM profile (format {doc.get('format')!r}; expected {FORMAT!r})")
    return doc


def _fragment(path):
    """A standards or pattern file a profile includes (PR-13, PR-17)."""
    try: doc = json.loads(Path(path).read_text(encoding='utf-8'))
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
            r.update({k: v for k, v in ref.items() if k in ('require', 'check', 'link', 'compare', 'across', 'standard')})
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
    for inc in doc.get('includes', []):   # PR-13, PR-17: standards and patterns, after the base and before the profile's own additions
        include(merged, (path.parent / inc).resolve())
    _add(merged, doc, path.name)
    own_map = doc.get('diagram_map') or {}   # PR-28: the profile's own entries are matched before its base's
    merged['diagram_map'] = {k: list(own_map.get(k, [])) + merged['diagram_map'][k] for k in MAP_KINDS}
    for k in LISTS:
        if k not in ('attributes', 'rules'): merged[k] += list(doc.get(k, []))
    for k in ('layers', 'types'): merged['names'][k].update((doc.get('names') or {}).get(k, {}))
    merged['chain'].append({'file': path.as_posix(), 'name': doc.get('name', path.stem), 'version': doc.get('version', 1)})
    reqs = [r for r in (merged.get('requires_sdem'), doc.get('requires_sdem')) if r]   # UF-04: every profile in the chain must accept this SDEM
    if reqs: merged['requires_sdem'] = ','.join(reqs)
    return merged


def digest(merged):
    body = {k: v for k, v in merged.items() if k not in PRIVATE}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


# ------------------------------------------------------------------ checking (PR-02…PR-05)

def check(merged, base_mm):
    """Issues in a merged profile against SDEM's own metamodel: schema, every type extends a known SDEM (or profile) type of the same
    layer, no core type is redefined, attributes well formed on known types, rules name declared attributes, link kinds map onto
    ArchiMate kinds between types of one layer."""
    from .validate import check_schema
    schema = json.loads(SCHEMA.read_text(encoding='utf-8'))
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
    known = dict(base_mm.entities); declared = {}
    for t in merged['types']:
        m = re.fullmatch(r'[A-Z][A-Z0-9]*\.([A-Z][A-Z0-9]{0,5})\.[A-Za-z0-9]+', t['type'])
        if t['type'] in known: issues.append(f"type {t['type']}: redefines an SDEM type — a profile adds types, never changes SDEM's")
        elif t['type'] in declared: issues.append(f"type {t['type']}: declared twice")
        elif not m or m.group(1) not in order: issues.append(f"type {t['type']}: a profile type is named <ORG>.<layer>.<Name> with a layer of this workspace ({', '.join(order)}), e.g. BANK.A3.PaymentsMicroservice")
        elif m.group(1) in own_layers and not t.get('extends'):   # LR-01: a root type of the profile's own layer
            declared[t['type']] = {'type': t['type'], 'level': m.group(1), 'extends': None, 'abstract': False, 'artefact': False, **t}
        elif not t.get('extends'): issues.append(f"type {t['type']}: a type in a core layer extends an SDEM type")
        else:
            parent = known.get(t['extends']) or declared.get(t['extends'])
            if not parent: issues.append(f"type {t['type']}: extends {t['extends']!r}, which is neither an SDEM type nor a profile type")
            elif m.group(1) != parent['level']: issues.append(f"type {t['type']}: its layer is {m.group(1)} but it extends an {parent['level']} type")
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
            if not known_attr(n): issues.append(f"rule {r['id']}: when {n!r}, which is not an attribute of {r['entity']} (declare it under attributes)")
        for part in ('link', 'compare'):
            k = (r.get(part) or {}).get('kind')
            if k and k not in kinds | own_kinds: issues.append(f"rule {r['id']}: {part} kind {k!r} is neither an ArchiMate kind SDEM knows nor one of the profile's link kinds")
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
    sdem_categories = json.loads(REQ_SCHEMA.read_text(encoding='utf-8'))['$defs']['requirement']['properties']['category']['enum']
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
        if not (a in order and b in order and order.index(b) - order.index(a) == 1): issues.append(f"{name}: links a layer to the layer directly below it ({a} is not directly above {b})")
        elif a not in own_layers and b not in own_layers: issues.append(f"{name}: both layers are SDEM's — links between core layers are SDEM's nine link types")
        elif (x['source_type'], x['relationship'], x['target_type']) in core_edges: issues.append(f"{name}: already an SDEM link type")
        touching |= {a, b}
    for code in own_layers:
        if code not in touching: issues.append(f"layer {code}: no link type joins it to its neighbour — add one under link_types")
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
            e = {'type': t['type'], 'level': t['type'].split('.')[1], 'extends': None, 'abstract': False, 'artefact': False, 'definition': t.get('definition', ''),
                 'identifier': {'key': ['name'], 'basis': 'SDEM', 'reasoning': 'a unique name within the layer'}, 'alignment_kind': 'organisation_extension',
                 'reference': {'standard': merged['name'], 'concept': t.get('name') or t['type'].split('.')[-1], 'locator': t.get('source', 'organisation profile')},
                 'evidence_status': 'organisation_defined', 'definition_source': 'organisation_profile', 'confidence': 'high',
                 'confidence_basis': f"declared by the organisation's profile {merged['name']}", 'reasoning': t.get('reasoning', "a kind of thing in the organisation's own layer")}
            ents.append(e); by[e['type']] = e; continue
        parent = by[t['extends']]
        e = {**{k: parent[k] for k in ('level', 'artefact') if k in parent}, 'type': t['type'], 'extends': t['extends'], 'abstract': False,
             'definition': t.get('definition', ''), 'identifier': parent.get('identifier'), 'alignment_kind': 'organisation_extension',
             'reference': {'standard': merged['name'], 'concept': t.get('name') or t['type'].split('.')[-1], 'locator': t.get('source', 'organisation profile')},
             'evidence_status': 'organisation_defined', 'definition_source': 'organisation_profile', 'confidence': 'high',
             'confidence_basis': f"declared by the organisation's profile {merged['name']}", 'reasoning': t.get('reasoning', 'organisation-specific kind, mapped onto an SDEM type')}
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


def structures():
    """The active profile's patterns that carry a structure (PR-21)."""
    return (ACTIVE or {}).get('structures', [])


def exceptions():
    """The active workspace's granted exceptions (PR-18)."""
    return ACTIVE_EXCEPTIONS


def _load_exceptions(folder):
    global ACTIVE_EXCEPTIONS
    f = Path(folder) / EXCEPTIONS_FILE
    try: ACTIVE_EXCEPTIONS = json.loads(f.read_text(encoding='utf-8')).get('exceptions', []) if f.exists() else []
    except ValueError: ACTIVE_EXCEPTIONS = []


def requirement_categories():
    """The requirement categories the active profile adds to SDEM's."""
    return [c['id'] for c in (ACTIVE or {}).get('requirement_categories', [])]


def applies(rule, inst):
    """Whether a rule's `when` holds for a record: each named attribute (or lifecycle_status) has the value, or one of the values; a list
    attribute (conforms_to …) holds when it contains one of them (PR-10) — so a pattern applies to the records that say they follow it."""
    at = inst.get('attributes') or {}
    for k, want in (rule.get('when') or {}).items():
        have = inst.get(k) if k == 'lifecycle_status' else at.get(k)
        wants = want if isinstance(want, list) else [want]
        if not (any(h in wants for h in have) if isinstance(have, list) else have in wants): return False
    return True


# ------------------------------------------------------------------ activation (PR-07)

def activate_file(path):
    """Make the profile at `path` the active one (resolved and checked). Returns the merged profile."""
    global ACTIVE, _ACTIVE_KEY
    merged = resolve(path)
    from .metamodel import Metamodel
    issues = check(merged, Metamodel.base())
    if issues: raise ProfileError(f'{Path(path).as_posix()}: the profile does not pass its checks:\n  ' + '\n  '.join(issues[:10]))
    key = digest(merged)
    if key != _ACTIVE_KEY:
        ACTIVE, _ACTIVE_KEY = merged, key
        from . import conformance; conformance.model.cache_clear()
    return merged


def deactivate():
    global ACTIVE, _ACTIVE_KEY, ACTIVE_EXCEPTIONS
    ACTIVE_EXCEPTIONS = []
    if ACTIVE is not None:
        ACTIVE, _ACTIVE_KEY = None, None
        from . import conformance; conformance.model.cache_clear()


def activate_from(folder):
    """Activate the workspace folder's profile if it has one; otherwise SDEM's metamodel alone. Returns the merged profile or None."""
    f = Path(folder) / FILE
    if f.exists():
        merged = activate_file(f); _load_exceptions(folder); return merged
    deactivate(); return None


def activate_from_paths(paths):
    """Datasets given as files: their folder's profile, when they share one."""
    folders = {Path(p).resolve().parent for p in paths if str(p).endswith('.json')}
    for d in sorted(folders):
        if (d / FILE).exists():
            merged = activate_file(d / FILE); _load_exceptions(d); return merged
    deactivate(); return None


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

EXAMPLE_BASE = {
    'format': FORMAT, 'name': 'bank-base', 'version': 1,
    'description': "A made-up bank's standard specification on top of SDEM — the base every team's profile extends (synthetic; not a real organisation's).",
    'names': {'layers': {'A1': 'L1 Business', 'A2': 'L2 Service Domains', 'A3': 'L3 Applications', 'A4': 'L4 Technology'},
              'types': {'A3.ApplicationComponent': 'Application', 'A4.SystemSoftware': 'Platform'}},
    'types': [
        {'type': 'BANK.A3.PaymentsMicroservice', 'extends': 'A3.ApplicationComponent', 'name': 'Payments microservice',
         'definition': 'An independently deployable payments service owned by one team', 'source': 'bank application standard §4.2'},
        {'type': 'BANK.A1.ControlFunction', 'extends': 'A1.BusinessCapability', 'name': 'Control function',
         'definition': 'A capability whose purpose is a regulatory or risk control', 'source': 'bank capability model §2'}],
    'attributes': [
        {'entity': 'A3.ApplicationComponent', 'name': 'risk_tier', 'type': 'enum', 'values': ['1', '2', '3'], 'required': True, 'description': 'the application risk tier (1 highest)'},
        {'entity': 'A3.ApplicationComponent', 'name': 'cost_centre', 'type': 'string', 'required': False, 'description': 'the cost centre that pays for it'},
        {'entity': 'BANK.A3.PaymentsMicroservice', 'name': 'owning_team', 'type': 'string', 'required': True, 'description': 'the team that owns the service'},
        {'entity': 'A1.BusinessRequirement', 'name': 'requirement_class', 'type': 'enum', 'values': ['functional', 'non_functional'], 'required': True,
         'description': "functional (what the business must be able to do) or non-functional (how well — measured in requirements.json); SDEM's own requirement_kind stays ArchiMate's requirement / constraint / principle"},
        {'entity': 'A1.BusinessRequirement', 'name': 'regulatory_reference', 'type': 'string', 'required': False, 'description': 'the regulation or policy clause it comes from'},
        {'entity': 'A4.InfrastructureComponent', 'name': 'environment', 'type': 'enum', 'values': ['production', 'non_production'], 'required': False, 'description': 'production or not'},
        {'entity': 'A4.InfrastructureComponent', 'name': 'dr_tier', 'type': 'enum', 'values': ['1', '2', '3'], 'required': False, 'description': 'the disaster recovery tier (1: hot standby)'},
        {'entity': 'A4.InfrastructureComponent', 'name': 'dr_region', 'type': 'string', 'required': False, 'description': 'the region it runs in, for DR separation'},
        {'entity': 'A4.InfrastructureComponent', 'name': 'replication_mode', 'type': 'enum', 'values': ['sync', 'async', 'none'], 'required': False, 'description': 'how its data reaches the DR pair'},
        {'entity': 'A4.InfrastructureComponent', 'name': 'failover_tested_on', 'type': 'date', 'required': False, 'description': 'the last successful failover test'}],
    'rules': [{'id': 'BANK-R01', 'entity': 'A3.ApplicationComponent', 'require': ['owner', 'risk_tier'], 'message': 'every application names its owner and risk tier (bank application standard §3)'},
              {'id': 'BANK-DR01', 'entity': 'A4.InfrastructureComponent', 'when': {'environment': 'production'}, 'require': ['dr_tier', 'dr_region', 'replication_mode'],
               'message': 'every production platform states its DR tier, region and replication (bank resilience standard §5)'},
              {'id': 'BANK-DR02', 'entity': 'A4.InfrastructureComponent', 'when': {'environment': 'production', 'dr_tier': ['1', '2']}, 'link': {'kind': 'dr_pair_of', 'min': 1},
               'message': 'a tier 1 or 2 production platform has a DR pair (bank resilience standard §5.2)'},
              {'id': 'BANK-DR03', 'entity': 'A4.InfrastructureComponent', 'compare': {'kind': 'dr_pair_of', 'attribute': 'dr_region', 'must': 'differ'},
               'message': 'a platform and its DR pair run in different regions (bank resilience standard §5.3)'}],
    'requirement_categories': [{'id': 'operational_resilience', 'description': 'tolerance for disruption of a critical operation (synthetic)'}],
    'link_kinds': [{'kind': 'dr_pair_of', 'maps_to': 'association', 'source_type': 'A4.InfrastructureComponent', 'target_type': 'A4.InfrastructureComponent',
                    'description': 'a platform and the platform it fails over to'},
                   {'kind': 'operated_by', 'maps_to': 'assignment', 'source_type': 'A4.InfrastructureComponent', 'target_type': 'A4.InfrastructureComponent',
                    'description': 'an infrastructure component is operated by a management platform'}]}

EXAMPLE_TEAM = {
    'format': FORMAT, 'name': 'payments-team', 'version': 1, 'extends': 'bank-base.json',
    'description': "The payments design team's additions to the bank base (synthetic).",
    'types': [{'type': 'BANK.A3.PaymentsGateway', 'extends': 'BANK.A3.PaymentsMicroservice', 'name': 'Payments gateway', 'definition': 'A payments microservice that fronts an external rail', 'source': 'payments design standard §1'}],
    'attributes': [{'entity': 'BANK.A3.PaymentsGateway', 'name': 'rail', 'type': 'enum', 'values': ['SWIFT', 'RTGS', 'Visa'], 'required': True, 'description': 'the external rail it connects to'}]}


# PR-13…PR-17: a made-up bank's standards and one reference-architecture pattern — synthetic, for the form only
EXAMPLE_SECURITY = {
    'format': STANDARD_FORMAT, 'description': "A made-up bank's API security standard (synthetic; not a real organisation's).",
    'standard': {'id': 'SEC-API', 'title': 'API security standard', 'version': '3.1', 'owner': 'security architecture', 'source': 'synthetic example', 'effective_from': '2026-01-01'},
    'attributes': [{'entity': 'A3.ApplicationComponent', 'name': 'exposure', 'type': 'enum', 'values': ['internal', 'partner', 'external'], 'description': 'who may call it'},
                   {'entity': 'A3.ApplicationComponent', 'name': 'authentication', 'type': 'enum', 'values': ['none', 'api-key', 'oauth2-mtls', 'oauth2-pkjwt'], 'description': 'how callers are authenticated'}],
    'rules': [{'id': 'SEC-API-01', 'entity': 'A3.ApplicationComponent', 'when': {'exposure': ['partner', 'external']}, 'require': ['authentication'],
               'message': 'an application called from outside the bank authenticates its callers (API security standard §2)'},
              {'id': 'SEC-API-02', 'entity': 'A3.ApplicationComponent', 'when': {'exposure': 'external'}, 'check': {'attribute': 'authentication', 'op': 'in', 'value': ['oauth2-mtls', 'oauth2-pkjwt']},
               'message': 'an externally exposed application uses OAuth 2 with mTLS or private-key JWT (API security standard §2.3)'}]}
EXAMPLE_NETWORK = {
    'format': STANDARD_FORMAT, 'description': "A made-up bank's network standard (synthetic).",
    'standard': {'id': 'NET', 'title': 'Network zoning and transport standard', 'version': '2.0', 'owner': 'network architecture', 'source': 'synthetic example', 'effective_from': '2026-01-01'},
    'attributes': [{'entity': 'A4.InfrastructureComponent', 'name': 'network_zone', 'type': 'enum', 'values': ['restricted', 'internal', 'dmz'], 'description': 'the network zone it sits in'},
                   {'entity': 'A4.InfrastructureComponent', 'name': 'monitoring', 'type': 'boolean', 'description': 'monitored by the bank\'s security operations'},
                   {'entity': 'A4.InfrastructureComponent', 'name': 'encryption_in_transit', 'type': 'enum', 'values': ['none', 'tls1.2', 'tls1.3'], 'description': 'transport encryption'}],
    'rules': [{'id': 'NET-07', 'entity': 'A3.ApplicationComponent', 'when': {'risk_tier': '1'}, 'across': {'relationship': 'DEPLOYED_ON'},
               'check': {'attribute': 'network_zone', 'op': 'in', 'value': ['restricted']},
               'message': 'a tier 1 application runs only in the restricted zone (network standard §7)'},
              {'id': 'NET-09', 'entity': 'A4.InfrastructureComponent', 'when': {'environment': 'production'}, 'check': {'attribute': 'encryption_in_transit', 'op': 'in', 'value': ['tls1.2', 'tls1.3']},
               'severity': 'warning', 'message': 'production platforms encrypt traffic in transit (network standard §9)'}]}
EXAMPLE_TECHNOLOGY = {
    'format': STANDARD_FORMAT, 'description': "A made-up bank's technology lifecycle standard (synthetic).",
    'standard': {'id': 'TECH-LC', 'title': 'Technology lifecycle standard', 'version': '1.4', 'owner': 'technology architecture', 'source': 'synthetic example', 'effective_from': '2026-01-01'},
    'rules': [{'id': 'TECH-LC-01', 'entity': 'A4.SystemSoftware', 'when': {'lifecycle_status': 'active'}, 'check': {'attribute': 'end_of_support', 'op': 'after', 'value': 'today+180d'},
               'severity': 'warning', 'message': 'software in use has at least six months of vendor support left (technology lifecycle standard §3)'}]}
EXAMPLE_PATTERN = {
    'format': PATTERN_FORMAT, 'description': "A made-up bank's reference architecture: secure API integration (synthetic).",
    'pattern': {'id': 'PAT-SECURE-API', 'title': 'Secure API integration', 'version': '2.0', 'owner': 'enterprise architecture', 'source': 'synthetic example',
                'applies_when': {'entity': 'A3.ApplicationComponent', 'when': {'exposure': 'external'}}},
    'requires': [{'id': 'PAT-SECURE-API-1', 'rule': 'SEC-API-01'},
                 {'id': 'PAT-SECURE-API-2', 'rule': 'SEC-API-02'},
                 {'id': 'PAT-SECURE-API-3', 'within': {'kind': 'composition', 'direction': 'in', 'to': 'BANK.A3.APIGateway', 'min': 1},
                  'message': 'an externally exposed application sits behind the bank\'s API gateway'},
                 {'id': 'PAT-SECURE-API-4', 'across': {'relationship': 'DEPLOYED_ON'}, 'check': {'attribute': 'monitoring', 'op': '==', 'value': True},
                  'message': 'its platform is monitored by security operations'},
                 {'id': 'PAT-SECURE-API-5', 'across': {'relationship': 'DEPLOYED_ON'}, 'check': {'attribute': 'encryption_in_transit', 'op': '==', 'value': 'tls1.3'},
                  'message': 'its platform encrypts traffic with TLS 1.3'}]}
EXAMPLE_STANDARDS_PROFILE = {
    'format': FORMAT, 'name': 'bank-with-standards', 'version': 1, 'extends': 'bank-base.json',
    'description': "A team profile that takes the made-up bank's standards and its secure API pattern (synthetic).",
    'includes': ['standards/example-security.json', 'standards/example-network.json', 'standards/example-technology.json', 'patterns/example-secure-api.json'],
    'types': [{'type': 'BANK.A3.APIGateway', 'extends': 'A3.ApplicationComponent', 'name': 'API gateway', 'definition': "The bank's API gateway, which fronts external APIs", 'source': 'synthetic example'}],
    'diagram_map': {   # PR-28: how sdem pattern extract reads the bank's pattern diagrams (examples/profiles/patterns/diagrams/)
        'shapes': [{'label': 'API Gateway', 'type': 'BANK.A3.APIGateway'}, {'stereotype': 'gateway', 'type': 'BANK.A3.APIGateway'},
                   {'label': 'Application', 'type': 'A3.ApplicationComponent'}, {'label': 'Container platform', 'type': 'A4.SystemSoftware'},
                   {'label': 'Private network', 'type': 'A4.CommunicationNetwork'}, {'label': 'Secrets service', 'type': 'A4.TechnologyService'}],
        'connectors': [{'label': 'routes requests to', 'kind': 'flow'}, {'label': 'deployed on', 'relationship': 'DEPLOYED_ON'},
                       {'label': 'connected to', 'kind': 'association'}, {'label': 'serves', 'kind': 'serving'}],
        'zones': [{'label': 'Restricted zone', 'entity': 'A4.InfrastructureComponent', 'check': {'attribute': 'network_zone', 'op': 'in', 'value': ['restricted']}},
                  {'label': 'DMZ', 'entity': 'A4.InfrastructureComponent', 'check': {'attribute': 'network_zone', 'op': 'in', 'value': ['dmz']}}]}}


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
    rec = json.loads((ws / 'workspace.json').read_text(encoding='utf-8'))
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


def describe(r):
    """A rule in words: 'A4.InfrastructureComponent where environment = production requires dr_tier, dr_region'."""
    out = r['entity']
    if r.get('when'): out += ' where ' + ' and '.join(f"{k} {'in ' + str(v) if isinstance(v, list) else '= ' + str(v)}" for k, v in r['when'].items())
    parts = []
    if r.get('require'): parts.append('requires ' + ', '.join(r['require']))
    if r.get('link'): l = r['link']; parts.append(f"has ≥{l.get('min', 1)} {l['kind']} link(s) {'from' if l.get('direction') == 'in' else 'to'} {l.get('to', 'any record')}")
    if r.get('compare'): c = r['compare']; parts.append(f"{c['attribute']} must {c['must']} across {c['kind']}")
    if r.get('across'):
        a = r['across']; parts.append(f"has ≥{a.get('min', 1)} approved {a['relationship']} link(s)" + (f", each with {r['check']['attribute']} {r['check']['op']} {r['check'].get('value')}" if r.get('check') else ''))
    elif r.get('check'): c = r['check']; parts.append(f"{c['attribute']} {c['op']} {c.get('value')}")
    tags = [x for x in ((r.get('standard') or {}).get('id'), (r.get('pattern') or {}).get('id')) if x]
    return out + ' ' + '; '.join(parts) + (f" [{', '.join(tags)}]" if tags else '') + (' (warning)' if r.get('severity') == 'warning' else '')


EXAMPLE_LAYERS = {
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
    'link_types': [{'source_type': 'BANK.A0.Outcome', 'relationship': 'REALIZED_BY', 'target_type': 'A1.BusinessCapability', 'required_evidence': ['strategy_document'],
                    'description': 'the capability realises the outcome', 'source': 'ArchiMate 3.2 ch. 7 (a capability realises an outcome)'},
                   {'source_type': 'A4.InfrastructureComponent', 'relationship': 'HOUSED_IN', 'target_type': 'BANK.A5.Facility', 'required_evidence': ['site_register'],
                    'description': 'the platform runs in the facility', 'source': 'ArchiMate 3.2 ch. 11 (a node is assigned to a facility)'}]}


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
        path = Path(a.file) if a.file else Path(a.estate or '.') / FILE
        if not a.file and not a.estate: raise ProfileError('give --workspace DIR or --file FILE')
        merged = resolve(path); issues = check(merged, Metamodel.base())
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
        dm = merged.get('diagram_map') or {}
        if any(dm.values()):   # PR-28
            print(f"  diagram    map: {len(dm.get('shapes', []))} shape(s), {len(dm.get('connectors', []))} connector label(s), {len(dm.get('zones', []))} zone(s) — read by sdem pattern extract")
        if issues: print('ISSUES:\n  ' + '\n  '.join(issues))
        return 1 if issues else 0
    except ProfileError as err:
        from .errors import note
        note('invalid_input' if 'does not pass' in str(err) or 'not an SDEM profile' in str(err) else 'not_found' if 'no such' in str(err) else 'input', f'sdem profile check --file {FILE}')
        print(f'ERROR: {err}', file=sys.stderr); return 2
