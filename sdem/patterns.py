"""Reference-architecture patterns as structures — roles and connectors (docs/design/sdem-structural-patterns-design.md, PR-21…PR-31;
the owner's decisions S1–S6, 2026-11-10).

A pattern file (`sdem-pattern/1`) may carry a `structure`: the parts of the pattern (roles, each a type SDEM or the profile knows),
the connectors between them (a link the metamodel allows — inside a layer, or an approved link between layers) and the zones parts sit
in. SDEM fills the roles from a workspace deterministically, starting from each record the pattern applies to (the anchor); a record may
name its role in SDEM's own `conforms_to` ("PAT-SECURE-API#api-gateway"). It never guesses: two candidates for one part are reported.

The structure is usually drawn, not written: `sdem pattern extract` reads the organisation's diagram — draw.io, Visio (.vsdx),
PlantUML or Mermaid — with the standard library only, and writes a DRAFT pattern file and a report; a person approves it (PR-30).
`sdem pattern draw` draws the pattern, and over a workspace's design, which part is there and which is missing (PR-25).
"""
import argparse, base64, html, json, re, sys, urllib.parse, zipfile, zlib
import xml.etree.ElementTree as ET
from pathlib import Path

MAX_BYTES = 50_000_000   # one diagram file, one part inside a .vsdx, or a compressed draw.io page once inflated — larger is not read (as sdem/office.py)

e = html.escape
OUTCOMES = ('compliant', 'non_compliant', 'unresolved', 'exception_approved', 'not_applicable')


# ====================================================================== checking a structure (PR-21, PR-22)

def _types_api(all_types, base_mm):
    from .profile import _ancestors
    def anc(t): return [t] + _ancestors(all_types, t)
    def is_a(t, a): return a in anc(t)
    def sdem_type(t): return next((x for x in anc(t) if x in base_mm.entities), None)
    return anc, is_a, sdem_type


def connector_issue(c, src_t, tgt_t, all_types, base_mm, merged):
    """None when the metamodel (or the profile's own link kinds and link types) allows the connector between the two types, else why."""
    from .profile import load_registry_rows
    anc, is_a, sdem_type = _types_api(all_types, base_mm)
    ls, lt = all_types[src_t]['level'], all_types[tgt_t]['level']
    if c.get('kind'):
        if ls != lt: return f"{c['kind']} is a link inside one layer, and {src_t} ({ls}) and {tgt_t} ({lt}) are in two — use the link type between the layers (relationship)"
        for k in merged.get('link_kinds', []):
            if k['kind'] == c['kind'] and is_a(src_t, k['source_type']) and is_a(tgt_t, k['target_type']): return None
        a, b = sdem_type(src_t), sdem_type(tgt_t)
        if not a or not b: return f"{src_t} or {tgt_t} has no SDEM type to check the link against"
        why = base_mm.relationship_issue(ls, a, c['kind'], b)
        return None if why is None else f"{src_t} -{c['kind']}-> {tgt_t}: the metamodel does not allow it ({why})"
    rel = c.get('relationship')
    rows = [(r['source_type'], r['relationship'], r['target_type']) for r in load_registry_rows()] + \
           [(x['source_type'], x['relationship'], x['target_type']) for x in merged.get('link_types', [])]
    if not any(r == rel for _, r, _ in rows): return f"{rel} is not a link type between layers ({', '.join(sorted({r for _, r, _ in rows}))})"
    fits = lambda t, row_t: row_t in all_types and (is_a(t, row_t) or is_a(row_t, t))
    if any(r == rel and fits(src_t, s) and fits(tgt_t, t) for s, r, t in rows): return None
    return f"{src_t} {rel} {tgt_t}: the metamodel has no such link (its {rel} links: {', '.join(f'{s} → {t}' for s, r, t in rows if r == rel)})"


def structure_issues(st, all_types, base_mm, merged, known_attr):
    pat, S = st['pattern'], st['structure']
    who = f"pattern {pat['id']} structure"
    out = []
    _, is_a, _ = _types_api(all_types, base_mm)
    roles = {}
    for r in S.get('roles', []):
        if not r.get('id') or not r.get('type'): out.append(f"{who}: a role needs an id and a type"); continue
        if r['id'] in roles: out.append(f"{who}: role {r['id']} is declared twice"); continue
        roles[r['id']] = r
        if r['type'] not in all_types: out.append(f"{who}: role {r['id']}: {r['type']} is not a type SDEM or the profile knows"); continue
        lo, hi = r.get('min', 1), r.get('max', 1)
        if not isinstance(lo, int) or lo < 0 or (hi is not None and (not isinstance(hi, int) or hi < max(lo, 1))):
            out.append(f"{who}: role {r['id']}: min {lo} and max {hi} — min 0 or more, max at least min (or null for any number)")
        for n in r.get('require', []):
            if not known_attr(r['type'], n): out.append(f"{who}: role {r['id']} requires {n!r}, which is not an attribute of {r['type']}")
        if r.get('check') and not known_attr(r['type'], r['check']['attribute']): out.append(f"{who}: role {r['id']} checks {r['check']['attribute']!r}, which is not an attribute of {r['type']}")
    zones = {z['id']: z for z in S.get('zones', [])}
    for z in zones.values():
        if z.get('entity') and z['entity'] not in all_types: out.append(f"{who}: zone {z['id']}: {z['entity']} is not a type")
    for r in roles.values():
        if r.get('zone') and r['zone'] not in zones: out.append(f"{who}: role {r['id']} is in zone {r['zone']!r}, which is not declared")
        z = zones.get(r.get('zone'))
        if z and z.get('check') and r['type'] in all_types and _zone_applies(z, r['type'], is_a) and not known_attr(r['type'], z['check']['attribute']):
            out.append(f"{who}: zone {z['id']} checks {z['check']['attribute']!r}, which is not an attribute of role {r['id']} ({r['type']})")
    anchor = roles.get(S.get('anchor'))
    if not anchor: out.append(f"{who}: anchor {S.get('anchor')!r} is not one of its roles — name the role the pattern applies to")
    elif anchor['type'] in all_types:
        ent = (pat.get('applies_when') or {}).get('entity')
        if ent in all_types and not is_a(anchor['type'], ent): out.append(f"{who}: the anchor {anchor['id']} is a {anchor['type']}, but the pattern applies to {ent}")
    ids = set()
    for c in S.get('connectors', []):
        if c.get('id') in ids: out.append(f"{who}: connector {c.get('id')} is declared twice")
        ids.add(c.get('id'))
        if bool(c.get('kind')) == bool(c.get('relationship')):
            out.append(f"{who}: connector {c.get('id')}: give a kind (a link inside a layer) or a relationship (a link between layers), one of them"); continue
        ends = [roles.get(c.get('from')), roles.get(c.get('to'))]
        if not all(ends): out.append(f"{who}: connector {c.get('id')}: {c.get('from') if not ends[0] else c.get('to')} is not a role"); continue
        if any(x['type'] not in all_types for x in ends): continue
        why = connector_issue(c, ends[0]['type'], ends[1]['type'], all_types, base_mm, merged)
        if why: out.append(f"{who}: connector {c['id']} ({c['from']} → {c['to']}): {why} — a pattern never adds a link the metamodel does not allow (PR-22)")
    reach, todo = {S.get('anchor')}, True
    while todo:
        todo = False
        for c in S.get('connectors', []):
            for a, b in ((c.get('from'), c.get('to')), (c.get('to'), c.get('from'))):
                if a in reach and b not in reach and b in roles: reach.add(b); todo = True
    for r in roles:
        if r not in reach: out.append(f"{who}: role {r} is not connected to the anchor — SDEM finds a part through its connectors")
    return out


def _zone_applies(z, t, is_a): return not z.get('entity') or is_a(t, z['entity'])


def map_issues(dm, all_types, base_mm, merged, known_attr):
    out = []
    kinds = {k['kind'] for k in base_mm.relationships['kinds']} | {k['kind'] for k in merged.get('link_kinds', [])}
    from .profile import load_registry_rows
    rels = {r['relationship'] for r in load_registry_rows()} | {x['relationship'] for x in merged.get('link_types', [])}
    for m in dm.get('shapes', []):
        if not any(m.get(k) for k in ('label', 'stereotype', 'stencil')): out.append('diagram_map shape: give a label, stereotype or stencil to match')
        if m.get('type') not in all_types: out.append(f"diagram_map shape {m.get('label') or m.get('stereotype') or m.get('stencil')!r}: {m.get('type')!r} is not a type")
    for m in dm.get('connectors', []):
        if bool(m.get('kind')) == bool(m.get('relationship')): out.append(f"diagram_map connector {m.get('label')!r}: give a kind or a relationship, one of them")
        elif m.get('kind') and m['kind'] not in kinds: out.append(f"diagram_map connector {m.get('label')!r}: {m['kind']!r} is not a link kind")
        elif m.get('relationship') and m['relationship'] not in rels: out.append(f"diagram_map connector {m.get('label')!r}: {m['relationship']!r} is not a link type between layers")
    for z in dm.get('zones', []):
        if z.get('entity') and z['entity'] not in all_types: out.append(f"diagram_map zone {z.get('label')!r}: {z['entity']} is not a type")
        elif z.get('check') and z.get('entity') and not known_attr(z['entity'], z['check']['attribute']):
            out.append(f"diagram_map zone {z.get('label')!r}: {z['check']['attribute']!r} is not an attribute of {z['entity']}")
    return out


# ====================================================================== filling the roles, and the outcomes (PR-23, PR-24)

def _conforms(inst):
    v = (inst.get('attributes') or {}).get('conforms_to') or []
    return v if isinstance(v, list) else [v]


def bind(anchor_id, S, pid, recs, inside, across, mm):
    """{role: [record ids]} from the anchor through the connectors, and how each role was reached. A record that names a role of this
    pattern in conforms_to ("PID#role") is that role (and no other); candidates are sorted, so the result is the same every time."""
    roles = {r['id']: r for r in S['roles']}
    bound, via = {S['anchor']: [anchor_id]}, {}
    def ends(c, ids, forward):
        out = []
        table = inside if c.get('kind') else across
        key = c.get('kind') or c.get('relationship')
        for x in ids: out += table.get((x, key, 'out' if forward else 'in'), [])
        return out
    changed = True
    while changed:
        changed = False
        for c in S.get('connectors', []):
            for a, b, fwd in ((c['from'], c['to'], True), (c['to'], c['from'], False)):
                if a in bound and b not in bound and b in roles:
                    want = roles[b]['type']; tag = f'{pid}#{b}'
                    cands = sorted({x for x in ends(c, bound[a], fwd) if x in recs and mm.known(recs[x][1]['type']) and mm.is_a(recs[x][1]['type'], want)})
                    cands = [x for x in cands if not any(t.startswith(pid + '#') and t != tag for t in _conforms(recs[x][1]))]
                    named = [x for x in cands if tag in _conforms(recs[x][1])]
                    bound[b] = named or cands; via[b] = (c['id'], a, bool(named)); changed = True
    return bound, via


def evaluate(datasets, maps, mm, structures, exceptions=(), as_of=None):
    """Every structured pattern × anchor record: one finding per role and per connector, with the binding — the same outcomes and
    exceptions as sdem comply (PR-24). Findings carry `rule` "<pattern>/<role or connector id>"."""
    from .comply import today, date_of, test, _unknown, describe_check, _ref
    from . import profile as _p
    as_of = as_of or today()
    recs = {i['id']: (l, i) for l, d in datasets.items() for i in d.get('instances', [])}
    inside, across = {}, {}
    for d in datasets.values():
        for r in d.get('relationships', []):
            inside.setdefault((r['source'], r['kind'], 'out'), []).append(r['target']); inside.setdefault((r['target'], r['kind'], 'in'), []).append(r['source'])
    for s, rel, t in maps:
        across.setdefault((s, rel, 'out'), []).append(t); across.setdefault((t, rel, 'in'), []).append(s)
    exc = {}
    for x in exceptions or []:
        for rid in x.get('records', []): exc.setdefault((x['rule'], rid), []).append(x)
    findings, bindings = [], []
    for st in structures:
        pat, S = st['pattern'], st['structure']; pid = pat['id']
        roles = {r['id']: r for r in S['roles']}; zones = {z['id']: z for z in S.get('zones', [])}
        aw = pat.get('applies_when') or {}
        eff = date_of(pat.get('effective_from'), as_of); not_yet = eff is not None and as_of < eff
        for rid, (layer, inst) in sorted(recs.items()):
            t = inst['type']
            if not mm.known(t) or not mm.is_a(t, roles[S['anchor']]['type']) or not mm.is_a(t, aw.get('entity', t)): continue
            if not _p.applies({'when': aw.get('when') or {}}, inst): continue
            bound, via = bind(rid, S, pid, recs, inside, across, mm)
            bindings.append({'pattern': pid, 'anchor': rid, 'roles': {r: bound.get(r) for r in roles}})
            planned = inst.get('lifecycle_status') == 'planned'
            def emit(part_id, kind, label, outcome, detail, fails, sev):
                f = {'rule': f'{pid}/{part_id}', 'standard': None, 'pattern': _ref(pat), 'layer': layer, 'record': rid, 'name': inst.get('name'),
                     'severity': 'warning' if not_yet else sev, 'message': f"{pat['title']}: {label}", 'outcome': outcome, 'detail': detail, 'parts': fails,
                     'part': {'kind': kind, 'id': part_id, 'label': label}}
                if outcome == 'non_compliant' and planned: f.update(outcome='unresolved', detail='planned — ' + detail)
                if f['outcome'] in ('non_compliant', 'unresolved'):
                    for x in exc.get((f['rule'], rid), []):
                        exp = date_of(x.get('expires'), as_of)
                        if exp is not None and as_of <= exp: f.update(outcome='exception_approved', exception={'id': x['id'], 'expires': x['expires'], 'approved_by': x.get('approved_by')}); break
                        f['detail'] += f"; exception {x['id']} expired on {x.get('expires')}"
                findings.append(f)
            sev0 = pat.get('severity', 'error')
            for r in S['roles']:
                label, sev = r.get('label') or r['id'], r.get('severity', sev0)
                lo, hi = r.get('min', 1), r.get('max', 1)
                got = bound.get(r['id'])
                if got is None:
                    nb = next((c for c in S.get('connectors', []) if r['id'] in (c['from'], c['to'])), None)
                    other = nb and (nb['to'] if nb['from'] == r['id'] else nb['from'])
                    if lo == 0: emit(r['id'], 'role', label, 'not_applicable', f'optional — not reached ({other} is missing)', [], sev)
                    else: emit(r['id'], 'role', label, 'non_compliant', f"no {label} — it is found through {other}, which is missing", [f'no {label}'], sev)
                    continue
                if len(got) < lo or (not got and lo):
                    c = S and via.get(r['id']); cid = c[0] if c else ''
                    why = f"no {label} ({r['type']}) {'linked' if len(got) == 0 else f'— {len(got)} found, needs at least {lo}'}" + (f" through {cid} from {', '.join(bound.get(c[1]) or [])}" if c else '')
                    emit(r['id'], 'role', label, 'non_compliant', why, [why], sev); continue
                if not got: emit(r['id'], 'role', label, 'not_applicable', 'optional — none in the design', [], sev); continue
                if hi is not None and len(got) > hi:
                    emit(r['id'], 'role', label, 'unresolved', f"ambiguous: {' or '.join(got)} could each be the {label} — name it with conforms_to \"{pid}#{r['id']}\" (SDEM never guesses)", [], sev); continue
                fails, unknown = [], []
                z = zones.get(r.get('zone'))
                checks = ([r['check']] if r.get('check') else []) + ([z['check']] if z and z.get('check') and (not z.get('entity') or any(mm.is_a(recs[x][1]['type'], z['entity']) for x in got)) else [])
                for x in got:
                    at = recs[x][1].get('attributes') or {}
                    miss = [n for n in r.get('require', []) if _unknown(at, n)]
                    if miss: fails.append(f"{x}: missing {', '.join(miss)}")
                    for c in checks:
                        ok = test(c, recs[x][1].get(c['attribute'], at.get(c['attribute'])), as_of)
                        where = f" ({z['label']})" if z and c is z.get('check') else ''
                        if ok is None: unknown.append(f"{x}: {c['attribute']} not known{where}")
                        elif not ok: fails.append(f"{x}: {c['attribute']} is {at.get(c['attribute'])!r} — must be {describe_check(c)[len(c['attribute']) + 1:]}{where}")
                inferred = [x for x in got if isinstance((recs[x][1].get('attributes') or {}).get('inferred'), dict) and recs[x][1]['attributes']['inferred'].get('status') != 'confirmed']
                if fails: emit(r['id'], 'role', label, 'non_compliant', '; '.join(fails), fails, sev)
                elif unknown or inferred: emit(r['id'], 'role', label, 'unresolved', '; '.join(unknown + [f'{x}: inferred, not yet confirmed' for x in inferred]), [], sev)
                else: emit(r['id'], 'role', label, 'compliant', ', '.join(got), [], sev)
            for c in S.get('connectors', []):
                label = c.get('label') or c.get('kind') or c.get('relationship')
                a, b = bound.get(c['from']) or [], bound.get(c['to']) or []
                sev = c.get('severity', sev0)
                if not a or not b:
                    emit(c['id'], 'connector', label, 'not_applicable', f"{c['from'] if not a else c['to']} is missing — reported under that part", [], sev); continue
                table = inside if c.get('kind') else across
                key = c.get('kind') or c.get('relationship')
                n = sum(1 for x in a for y in table.get((x, key, 'out'), []) if y in b)
                if n >= c.get('min', 1): emit(c['id'], 'connector', label, 'compliant', f"{n} {key} link(s)", [], sev)
                else:
                    why = f"no {'approved ' if c.get('relationship') else ''}{key} link from {', '.join(a)} to {', '.join(b)}"
                    emit(c['id'], 'connector', label, 'non_compliant', why, [why], sev)
    return findings, bindings


def part_ids(structures):
    """Every role and connector id a person may grant an exception to (PR-24)."""
    return {f"{st['pattern']['id']}/{x['id']}": st for st in structures for x in st['structure'].get('roles', []) + st['structure'].get('connectors', [])}


# ====================================================================== reading diagrams (PR-27)

def _text(s):
    s = re.sub(r'<br\s*/?>|</div>|</p>', '\n', s or '', flags=re.I)
    s = html.unescape(re.sub(r'<[^>]+>', '', s))
    return [x.strip() for x in s.split('\n') if x.strip()]


def _style(s):
    out = {}
    for part in (s or '').split(';'):
        if '=' in part: k, v = part.split('=', 1); out[k.strip()] = v.strip()
        elif part.strip(): out[part.strip()] = '1'
    return out


def read_drawio(path):
    root = ET.parse(path).getroot()
    diagram = root.find('diagram') if root.tag == 'mxfile' else None
    model = root if root.tag == 'mxGraphModel' else (diagram.find('mxGraphModel') if diagram is not None else None)
    if model is None and diagram is not None and (diagram.text or '').strip():   # compressed: base64 + raw deflate + URL encoding
        inflate = zlib.decompressobj(-15); raw = inflate.decompress(base64.b64decode(diagram.text.strip()), MAX_BYTES)
        if inflate.unconsumed_tail: raise ValueError(f'{path}: the compressed diagram inflates to more than {MAX_BYTES} bytes — larger than SDEM reads')
        raw = raw.decode('utf-8')
        model = ET.fromstring(urllib.parse.unquote(raw))
    if model is None: raise ValueError(f'{path}: no draw.io diagram found')
    cells, props = [], {}
    for el in model.iter():
        if el.tag in ('object', 'UserObject'):
            c = el.find('mxCell')
            if c is None: continue
            c = dict(c.attrib); c['id'] = el.get('id'); c['value'] = el.get('label', ''); props[c['id']] = {k: v for k, v in el.attrib.items() if k not in ('id', 'label')}
            g = el.find('mxCell/mxGeometry'); cells.append((c, g))
        elif el.tag == 'mxCell': cells.append((dict(el.attrib), el.find('mxGeometry')))
    byid = {c['id']: (c, g) for c, g in cells}
    edges_ids = {c['id'] for c, _ in cells if c.get('edge') == '1'}
    def geom(cid):
        c, g = byid[cid]
        if g is None: return None
        x, y = float(g.get('x', 0)), float(g.get('y', 0))
        p = c.get('parent')
        if p in byid and byid[p][0].get('vertex') == '1':
            pg = geom(p)
            if pg: x += pg[0]; y += pg[1]
        return (x, y, float(g.get('width', 0)), float(g.get('height', 0)))
    shapes, edges, edge_labels, annotations = [], [], {}, []
    for c, g in cells:
        if c.get('vertex') == '1' and c.get('parent') in edges_ids:
            edge_labels.setdefault(c['parent'], []).extend(_text(c.get('value'))); continue
        if c.get('vertex') == '1':
            st = _style(c.get('style'))
            if 'text' in st and 'shape' not in st:   # a text box: an annotation on the drawing, not a part
                annotations.append({'where': f"{Path(path).name}#{c['id']}", 'text': ' '.join(_text(c.get('value')))}); continue
            stencil = st.get('shape', '')
            sub = st.get('appType') or st.get('techType') or st.get('busType') or st.get('otherType') or ''
            shapes.append({'id': c['id'], 'lines': _text(c.get('value')), 'stencil': f'{stencil}:{sub}' if sub else stencil, 'stereotype': (props.get(c['id']) or {}).get('stereotype', ''),
                           'hint': props.get(c['id']) or {}, 'parent': c.get('parent'), 'geom': geom(c['id']),
                           'container': st.get('container') == '1' or 'swimlane' in st or st.get('shape') == 'mxgraph.archimate3.grouping' or 'group' in st,
                           'dashed': st.get('dashed') == '1', 'where': f"{Path(path).name}#{c['id']}"})
        elif c.get('edge') == '1':
            st = _style(c.get('style'))
            edges.append({'id': c['id'], 'source': c.get('source'), 'target': c.get('target'), 'lines': _text(c.get('value')),
                          'style': st, 'hint': props.get(c['id']) or {}, 'where': f"{Path(path).name}#{c['id']}"})
    for x in edges:
        x['lines'] = x['lines'] + edge_labels.get(x['id'], [])
    title = (diagram.get('name') if diagram is not None else None) or Path(path).stem
    return {'format': 'drawio', 'title': title, 'shapes': shapes, 'edges': edges, 'ignored': [], 'annotations': annotations}


VNS = {'v': 'http://schemas.microsoft.com/office/visio/2012/main', 'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}


def _zread(z, name):
    if z.getinfo(name).file_size > MAX_BYTES: raise ValueError(f'{name}: {z.getinfo(name).file_size} bytes inside the .vsdx — larger than SDEM reads')
    return z.read(name)


def read_vsdx(path, page=1):
    z = zipfile.ZipFile(path)
    names = set(z.namelist())
    masters = {}
    if 'visio/masters/masters.xml' in names:
        for m in ET.fromstring(_zread(z, 'visio/masters/masters.xml')).findall('v:Master', VNS): masters[m.get('ID')] = m.get('NameU') or m.get('Name') or ''
    pages = ET.fromstring(_zread(z, 'visio/pages/pages.xml'))
    rels = ET.fromstring(_zread(z, 'visio/pages/_rels/pages.xml.rels'))
    target = {r.get('Id'): r.get('Target') for r in rels}
    plist = pages.findall('v:Page', VNS)
    if page > len(plist): raise ValueError(f'{path}: has {len(plist)} page(s), not {page}')
    pg = plist[page - 1]
    rid = pg.find('v:Rel', VNS).get('{%s}id' % VNS['r'])
    doc = ET.fromstring(_zread(z, 'visio/pages/' + target[rid]))
    ph = 11.0
    for c in pg.iter('{%s}Cell' % VNS['v']):
        if c.get('N') == 'PageHeight': ph = float(c.get('V'))
    def cells(sh): return {c.get('N'): c.get('V') for c in sh.findall('v:Cell', VNS)}
    connects = {}
    for c in doc.findall('.//v:Connects/v:Connect', VNS):
        connects.setdefault(c.get('FromSheet'), {})['source' if c.get('FromCell') == 'BeginX' else 'target'] = c.get('ToSheet')
    shapes, edges = [], []
    for sh in doc.findall('.//v:Shapes/v:Shape', VNS):
        sid, cv = sh.get('ID'), cells(sh)
        t = sh.find('v:Text', VNS)
        lines = [x.strip() for x in ''.join(t.itertext()).split('\n') if x.strip()] if t is not None else []
        master = masters.get(sh.get('Master'), '')
        props = {r.get('N'): (r.find('v:Cell[@N="Value"]', VNS).get('V') if r.find('v:Cell[@N="Value"]', VNS) is not None else None)
                 for r in sh.findall('v:Section[@N="Property"]/v:Row', VNS)}
        where = f"{Path(path).name}#page{page}/shape-{sid}"
        if sid in connects or 'BeginX' in cv:
            ends = connects.get(sid, {})
            edges.append({'id': sid, 'source': ends.get('source'), 'target': ends.get('target'), 'lines': lines, 'style': {'master': master}, 'hint': {k: v for k, v in props.items() if v}, 'where': where})
            continue
        w, h = float(cv.get('Width', 0)), float(cv.get('Height', 0)); x, y = float(cv.get('PinX', 0)), float(cv.get('PinY', 0))
        geom = ((x - w / 2) * 96, (ph - y - h / 2) * 96, w * 96, h * 96)
        shapes.append({'id': sid, 'lines': lines, 'stencil': master, 'stereotype': props.get('stereotype') or '', 'hint': {k: v for k, v in props.items() if v},
                       'parent': None, 'geom': geom, 'container': 'container' in master.lower() or 'zone' in master.lower() or 'group' in master.lower(), 'dashed': False, 'where': where})
    return {'format': 'vsdx', 'title': pg.get('NameU') or pg.get('Name') or Path(path).stem, 'shapes': shapes, 'edges': edges, 'ignored': []}


PUML_ELEMENT = re.compile(r'^(component|node|database|rectangle|package|frame|cloud|folder|artifact|queue|interface|agent|boundary|collections)\s+'
                          r'(?:"([^"]+)"\s+as\s+(\w+)|(\w+)\s+as\s+"([^"]+)"|"([^"]+)"|(\w+))\s*(<<[^>]+>>)?\s*(\{)?\s*$', re.I)
PUML_MACRO = re.compile(r'^(\w+?)(?:_(?:Up|Down|Left|Right))?\(\s*(\w+)\s*,\s*"([^"]*)"(?:\s*,\s*"([^"]*)")?\s*\)\s*(\{)?\s*$')
PUML_ARROW = re.compile(r'^(\w+)\s+([-.=]+(?:\[[^\]]*\])?(?:up|down|left|right)?[-.=]*(?:>|\|>|\*|o)?|<[-.=]+)\s+(\w+)\s*(?::\s*(.*))?$')


def read_plantuml(path):
    lines = Path(path).read_text(encoding='utf-8').splitlines()
    shapes, edges, ignored, stack, title = [], [], [], [], Path(path).stem
    def where(n): return f"{Path(path).name}:{n}"
    for n, raw in enumerate(lines, 1):
        s = raw.strip()
        if not s or s.startswith("'") or s.startswith('!') or s.startswith('@') or s.lower().startswith(('skinparam', 'hide ', 'show ', 'left to right', 'top to bottom', 'legend', 'endlegend', 'caption', 'note ', 'end note', 'sprite')):
            continue
        if s.lower().startswith('title '): title = s[6:].strip().strip('"'); continue
        if s == '}':
            if stack: stack.pop()
            continue
        rel = re.match(r'^Rel(?:_([A-Za-z]+?))?(?:_(?:Up|Down|Left|Right))?\(\s*(\w+)\s*,\s*(\w+)\s*(?:,\s*"([^"]*)")?[^)]*\)\s*$', s)
        if rel:   # ArchiMate for PlantUML: Rel_Flow(a, b, "label"), Rel_Serving_Down(…), Rel(a, b, "label")
            edges.append({'id': f'L{n}', 'source': rel.group(2), 'target': rel.group(3), 'lines': [rel.group(4)] if rel.group(4) else [],
                          'style': {'kind': (rel.group(1) or '').lower()}, 'hint': {}, 'where': where(n)})
            continue
        m = PUML_MACRO.match(s)
        if m:
            macro, eid, label = m.group(1), m.group(2), m.group(3)
            shapes.append({'id': eid, 'lines': [label], 'stencil': macro, 'stereotype': '', 'hint': {}, 'parent': stack[-1] if stack else None, 'geom': None,
                           'container': macro.lower() in ('grouping', 'group', 'boundary', 'location') or bool(m.group(5)), 'dashed': False, 'where': where(n)})
            if m.group(5): stack.append(eid)
            continue
        m = PUML_ELEMENT.match(s)
        if m:
            kw = m.group(1).lower()
            label = m.group(2) or m.group(5) or m.group(6) or m.group(7)
            eid = m.group(3) or m.group(4) or re.sub(r'\W+', '_', label)
            stereo = (m.group(8) or '').strip('<> ')
            shapes.append({'id': eid, 'lines': [x.strip() for x in label.replace('\\n', '\n').split('\n') if x.strip()], 'stencil': kw, 'stereotype': stereo, 'hint': {},
                           'parent': stack[-1] if stack else None, 'geom': None, 'container': bool(m.group(9)), 'dashed': False, 'where': where(n)})
            if m.group(9): stack.append(eid)
            continue
        m = PUML_ARROW.match(s)
        if m:
            a, arrow, b, label = m.group(1), m.group(2), m.group(3), (m.group(4) or '').strip()
            if arrow.startswith('<'): a, b = b, a
            edges.append({'id': f'L{n}', 'source': a, 'target': b, 'lines': [label] if label else [], 'style': {'dashed': '1' if '.' in arrow else '0'}, 'hint': {}, 'where': where(n)})
            continue
        ignored.append({'where': where(n), 'line': s, 'why': 'not in the PlantUML subset SDEM reads (elements, ArchiMate macros, arrows, { } nesting)'})
    return {'format': 'plantuml', 'title': title, 'shapes': shapes, 'edges': edges, 'ignored': ignored}


MMD_NODE = re.compile(r'(\w+)\s*(\[\[|\[\(|\(\[|\(\(|\[/|\[\\|\[|\(|\{\{|\{|>)\s*(?:"([^"]*)"|([^\]\)\}"]*?))\s*(\]\]|\)\]|\]\)|\)\)|/\]|\\\]|\]|\)|\}\}|\})(?::::(\w+))?')
MMD_EDGE = re.compile(r'\s*(-->|---|-\.->|-\.-|==>|===|--\s*[^-]+?\s*-->|-\.\s*[^.]+?\s*\.->|==\s*[^=]+?\s*==>)\s*(?:\|([^|]*)\|)?\s*')


def read_mermaid(path):
    text = Path(path).read_text(encoding='utf-8')
    fence = re.search(r'```mermaid\s*\n(.*?)```', text, re.S)
    if fence: text = fence.group(1)
    shapes, edges, ignored, stack, title, known = [], [], [], [], Path(path).stem, {}
    def where(n): return f"{Path(path).name}:{n}"
    def node(tok, n):
        tok = tok.strip()
        m = MMD_NODE.fullmatch(tok)
        if m:
            nid, label, cls = m.group(1), (m.group(3) if m.group(3) is not None else m.group(4) or '').strip(), m.group(6) or ''
            shape = {'[(': 'database', '((': 'circle', '([': 'stadium', '{{': 'hexagon', '{': 'decision'}.get(m.group(2), 'box')
        else:
            m2 = re.fullmatch(r'(\w+)(?::::(\w+))?', tok)
            if not m2: return None
            nid, label, cls, shape = m2.group(1), None, m2.group(2) or '', None
        if nid not in known:
            known[nid] = {'id': nid, 'lines': [label or nid], 'stencil': shape or 'box', 'stereotype': cls, 'hint': {}, 'parent': stack[-1] if stack else None,
                          'geom': None, 'container': False, 'dashed': False, 'where': where(n)}
            shapes.append(known[nid])
        else:
            if label: known[nid]['lines'] = [label]
            if shape: known[nid]['stencil'] = shape
            if cls: known[nid]['stereotype'] = cls
        return nid
    for n, raw in enumerate(text.splitlines(), 1):
        s = raw.strip().rstrip(';')
        if not s or s.startswith('%%') or re.match(r'^(flowchart|graph)\b', s) or s.startswith(('style ', 'linkStyle ', 'click ', 'direction ')): continue
        if s.startswith('title'): title = s.split(':', 1)[-1].strip() if ':' in s else s[5:].strip(); continue
        if s.startswith('---'): continue
        m = re.match(r'^classDef\s+\S+', s)
        if m: continue
        m = re.match(r'^class\s+([\w,]+)\s+(\w+)$', s)
        if m:
            for nid in m.group(1).split(','):
                if nid in known: known[nid]['stereotype'] = m.group(2)
            continue
        m = re.match(r'^subgraph\s+(\w+)\s*(?:\[\s*"?([^\]"]+)"?\s*\])?\s*$', s) or re.match(r'^subgraph\s+"?([^"]+?)"?\s*$', s)
        if m:
            sid = m.group(1) if m.lastindex and m.lastindex >= 1 and re.fullmatch(r'\w+', m.group(1)) else re.sub(r'\W+', '_', m.group(1))
            label = (m.group(2) if m.lastindex == 2 else None) or m.group(1)
            known[sid] = {'id': sid, 'lines': [label], 'stencil': 'subgraph', 'stereotype': '', 'hint': {}, 'parent': stack[-1] if stack else None,
                          'geom': None, 'container': True, 'dashed': False, 'where': where(n)}
            shapes.append(known[sid]); stack.append(sid); continue
        if s == 'end':
            if stack: stack.pop()
            continue
        parts = MMD_EDGE.split(s)
        if len(parts) >= 4:   # a chain: node (arrow label node)+
            ids = [node(parts[0], n)]
            ok = ids[0] is not None
            for i in range(1, len(parts) - 1, 3):
                arrow, label, nxt = parts[i], parts[i + 1], parts[i + 2]
                inline = re.match(r'^(?:--|-\.|==)\s*(.+?)\s*(?:-->|\.->|==>)$', arrow)
                lab = (label or (inline.group(1) if inline else '') or '').strip()
                b = node(nxt, n)
                if b is None: ok = False; break
                edges.append({'id': f'L{n}.{len(edges)}', 'source': ids[-1], 'target': b, 'lines': [lab] if lab else [], 'style': {'dashed': '1' if '.' in arrow else '0'},
                              'hint': {}, 'where': where(n)})
                ids.append(b)
            if ok: continue
        if node(s, n): continue
        ignored.append({'where': where(n), 'line': s, 'why': 'not in the Mermaid flowchart subset SDEM reads (nodes, edges, subgraph, class)'})
    return {'format': 'mermaid', 'title': title, 'shapes': shapes, 'edges': edges, 'ignored': ignored}


READERS = {'.drawio': read_drawio, '.xml': read_drawio, '.vsdx': read_vsdx, '.puml': read_plantuml, '.plantuml': read_plantuml, '.pu': read_plantuml,
           '.mmd': read_mermaid, '.mermaid': read_mermaid, '.md': read_mermaid}


def read(path):
    r = READERS.get(Path(path).suffix.lower())
    if not r: raise ValueError(f"{path}: SDEM reads draw.io (.drawio), Visio (.vsdx), PlantUML (.puml) and Mermaid (.mmd, or a ```mermaid block in .md) — not {Path(path).suffix or 'this file'}")
    size = Path(path).stat().st_size
    if size > MAX_BYTES: raise ValueError(f'{path}: {size} bytes — larger than SDEM reads ({MAX_BYTES})')
    try: return r(path)
    except ValueError as err:
        if str(path) in str(err): raise
        raise ValueError(f'{path}: {err}') from None
    except (zlib.error, zipfile.BadZipFile, ET.ParseError, KeyError, AttributeError, IndexError, TypeError) as err:   # a damaged or unexpected file: say so, never a traceback
        raise ValueError(f'{path}: not a diagram SDEM can read — damaged, or not what its name says ({type(err).__name__}: {err})') from None


# ====================================================================== from a diagram to a draft pattern (PR-27…PR-29)

MULT = re.compile(r'\s*\((optional|0\.\.1|1\.\.1|0\.\.n|1\.\.n|0\.\.\*|1\.\.\*|\d+\.\.\d+|\d+\.\.n)\)\s*$', re.I)
DRAWIO_SUB = {'comp': 'ApplicationComponent', 'serv': 'ApplicationService', 'interface': 'ApplicationInterface', 'func': 'ApplicationFunction', 'event': 'Event',
              'node': 'Node', 'device': 'Device', 'sysSw': 'SystemSoftware', 'commNetwork': 'CommunicationNetwork', 'network': 'CommunicationNetwork', 'artifact': 'Artifact',
              'path': 'Path', 'capability': 'BusinessCapability', 'role': 'BusinessRole', 'actor': 'BusinessActor', 'process': 'BusinessProcess'}


def _norm(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())


def _slug(s): return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', (s or '').lower())).strip('-') or 'part'


def _mult(label):
    m = MULT.search(label or '')
    if not m: return label, 1, 1
    v = m.group(1).lower().replace('*', 'n'); base = label[:m.start()].strip()
    if v == 'optional': return base, 0, 1
    lo, hi = v.split('..')
    return base, int(lo), None if hi == 'n' else int(hi)


def _builtin_type(shape, mm, sdem_types):
    st = shape['stencil'] or ''
    if ':' in st and 'archimate' in st:
        sub = st.split(':', 1)[1]
        name = DRAWIO_SUB.get(sub)
        if name: return next((t for t in sdem_types if t.split('.', 1)[1] == name), None)
    key = _norm(st.split('.')[-1].replace('Technology_', '').replace('Application_', '').replace('Business_', '')) if st else ''
    for t in sdem_types:
        loc = _norm(t.split('.', 1)[1])
        if key and (key == loc or _norm(st) in (loc, _norm(t.replace('.', '')), _norm('technology' + loc), _norm('application' + loc), _norm('business' + loc))): return t
    return None


def extract(path, merged, base_mm, meta, anchor=None):
    """A diagram → (a draft pattern file, a report). Nothing is guessed: an unmapped shape, a connector the metamodel does not allow, or a
    line outside the subset SDEM reads is in the report; the draft is checked with the profile (PR-27…PR-29)."""
    from .metamodel import Metamodel
    from . import profile as _p
    G = read(path)
    dm = merged.get('diagram_map') or {}
    mm = base_mm
    all_types = dict(base_mm.entities)
    for t in merged.get('types', []): all_types[t['type']] = {**(all_types.get(t.get('extends')) or {}), **t, 'level': (all_types.get(t.get('extends')) or {}).get('level') or t['type'].split('.')[1]}
    sdem_types = sorted(base_mm.entities)
    report = {'source': str(path), 'format': G['format'], 'title': G['title'], 'roles': [], 'connectors': [], 'zones': [], 'unmapped_shapes': [], 'refused_connectors': [],
              'unmapped_connectors': [], 'ignored_lines': G['ignored'], 'notes': [f"text {a['text']!r} ({a['where']}) is an annotation, not a part" for a in G.get('annotations', [])]}
    byid = {s['id']: s for s in G['shapes']}
    # zones: containers the mapping table names, or any container — membership by nesting, else by geometry
    def zone_entry(s):
        lab = ' '.join(s['lines'])
        return next((z for z in dm.get('zones', []) if _norm(z.get('label')) and _norm(z['label']) == _norm(lab)), None)
    containers = [s for s in G['shapes'] if s['container'] or zone_entry(s)]
    cont_ids = {s['id'] for s in containers}
    def inside(s, c):
        if s.get('parent') == c['id']: return True
        a, b = s.get('geom'), c.get('geom')
        return bool(a and b) and s['id'] != c['id'] and a[0] >= b[0] - 1 and a[1] >= b[1] - 1 and a[0] + a[2] <= b[0] + b[2] + 1 and a[1] + a[3] <= b[1] + b[3] + 1
    zones, used = [], set()
    for c in containers:
        lab = ' '.join(c['lines']) or c['id']; zid = _slug(lab)
        while zid in used: zid += '-2'
        used.add(zid); ze = zone_entry(c)
        z = {'id': zid, 'label': lab, 'source': c['where']}
        if ze and ze.get('check'): z['check'] = ze['check']
        if ze and ze.get('entity'): z['entity'] = ze['entity']
        if not ze: report['notes'].append(f"zone {lab!r} ({c['where']}) is drawn, with no check — add it to the profile's diagram_map zones to give it one")
        zones.append(z); c['_zone'] = zid
    # roles
    roles, rid_of, used = [], {}, set()
    for s in G['shapes']:
        if s['id'] in cont_ids: continue
        raw = s['lines'][0] if s['lines'] else ''
        label, lo, hi = _mult(raw)
        if not label:
            report['unmapped_shapes'].append({'shape': s['where'], 'label': '', 'why': 'a shape with no label — SDEM cannot tell what part it is'}); continue
        t, how = None, None
        hint = (s.get('hint') or {}).get('sdem_type')
        if hint: t, how = hint, 'the shape names its type (sdem_type)'
        if not t and s.get('stereotype'):
            m = next((x for x in dm.get('shapes', []) if x.get('stereotype') and _norm(x['stereotype']) == _norm(s['stereotype'])), None)
            if m: t, how = m['type'], f"stereotype «{s['stereotype']}» (diagram_map)"
        if not t:
            m = next((x for x in dm.get('shapes', []) if x.get('label') and _norm(x['label']) == _norm(label)), None)
            if m: t, how = m['type'], f"label {label!r} (diagram_map)"
        if not t and s.get('stencil'):
            m = next((x for x in dm.get('shapes', []) if x.get('stencil') and _norm(x['stencil']) == _norm(s['stencil'])), None)
            if m: t, how = m['type'], f"stencil {s['stencil']!r} (diagram_map)"
        if not t:
            t = _builtin_type(s, mm, sdem_types)
            if t: how = f"ArchiMate shape {s['stencil']!r}"
        if not t or t not in all_types:
            report['unmapped_shapes'].append({'shape': s['where'], 'label': label, 'stencil': s.get('stencil'), 'stereotype': s.get('stereotype'),
                                              'why': f"{t!r} is not a type" if t else "no entry in the profile's diagram_map (by label, stereotype or stencil) and not an ArchiMate shape"}); continue
        rid = (s.get('hint') or {}).get('sdem_role') or _slug(label)
        while rid in used: rid += '-2'
        used.add(rid); rid_of[s['id']] = rid
        r = {'id': rid, 'label': label, 'type': t}
        if lo != 1: r['min'] = lo
        if hi != 1: r['max'] = hi
        zone = next((c['_zone'] for c in sorted(containers, key=lambda c: (c['geom'] or (0, 0, 0, 0))[2] * (c['geom'] or (0, 0, 0, 0))[3]) if inside(s, c)), None)
        if zone: r['zone'] = zone
        r['source'] = s['where']
        roles.append(r); report['roles'].append({'role': rid, 'type': t, 'how': how, 'source': s['where']})
    # connectors
    conns, n = [], 0
    rtype = {r['id']: r['type'] for r in roles}
    for x in G['edges']:
        a, b = rid_of.get(x.get('source')), rid_of.get(x.get('target'))
        raw = ' '.join(x['lines']); label, lo, _ = _mult(raw)
        if not a or not b:
            why = 'it does not join two shapes' if not (x.get('source') and x.get('target')) else f"an end is not a mapped part ({x.get('source') if not a else x.get('target')})"
            report['unmapped_connectors'].append({'connector': x['where'], 'label': label, 'why': why}); continue
        kind = rel = None; how = None
        m = next((c for c in dm.get('connectors', []) if c.get('label') and _norm(c['label']) == _norm(label)), None)
        if m: kind, rel, how = m.get('kind'), m.get('relationship'), f"label {label!r} (diagram_map)"
        elif x['style'].get('kind'): kind, how = x['style']['kind'], f"ArchiMate relationship Rel_{x['style']['kind'].title()}"
        elif _norm(label) in {_norm(k['kind']) for k in mm.relationships['kinds']}: kind, how = next(k['kind'] for k in mm.relationships['kinds'] if _norm(k['kind']) == _norm(label)), 'the label is an ArchiMate kind'
        else:
            from .profile import load_registry_rows
            r2 = next((r['relationship'] for r in load_registry_rows() if _norm(r['relationship']) == _norm(label)), None)
            if r2: rel, how = r2, 'the label is a link type between layers'
        if not kind and not rel:
            report['unmapped_connectors'].append({'connector': x['where'], 'label': label, 'from': a, 'to': b, 'why': "no entry in the profile's diagram_map connectors for this label, and it is not an ArchiMate relationship"}); continue
        n += 1
        c = {'id': f'C{n}', 'from': a, 'to': b, **({'kind': kind} if kind else {'relationship': rel}), 'label': label or kind or rel}
        if lo == 0: c['min'] = 0
        c['source'] = x['where']
        why = connector_issue(c, rtype[a], rtype[b], all_types, base_mm, merged)
        if why:
            report['refused_connectors'].append({'connector': x['where'], 'label': label, 'from': a, 'to': b, 'why': why}); n -= 1; continue
        conns.append(c); report['connectors'].append({'connector': c['id'], 'from': a, 'to': b, 'link': kind or rel, 'how': how, 'source': x['where']})
    # the anchor
    anc = None
    if anchor:
        anc = next((r['id'] for r in roles if anchor in (r['id'], r['label'])), None)
        if not anc: report['notes'].append(f"--anchor {anchor!r}: no role with that id or label ({', '.join(r['label'] for r in roles)})")
    else:
        marked = [r['id'] for r in roles if (byid[next(k for k, v in rid_of.items() if v == r['id'])].get('hint') or {}).get('sdem_anchor') or
                  'anchor' in _norm(byid[next(k for k, v in rid_of.items() if v == r['id'])].get('stereotype'))]
        anc = marked[0] if len(marked) == 1 else None
        if not anc: report['notes'].append('no anchor — name the part the pattern applies to with --anchor <label> (or mark the shape «anchor»)')
    report['zones'] = [{'zone': z['id'], 'check': z.get('check'), 'roles': [r['id'] for r in roles if r.get('zone') == z['id']]} for z in zones]
    layout = {}
    for s in G['shapes']:
        g = s.get('geom')
        if not g: continue
        if s['id'] in rid_of: layout.setdefault('roles', {})[rid_of[s['id']]] = [round(v, 1) for v in g]
        elif s.get('_zone'): layout.setdefault('zones', {})[s['_zone']] = [round(v, 1) for v in g]
    pid = meta['id']
    pattern = {'id': pid, 'title': meta.get('title') or G['title'], 'version': meta.get('version', '1.0'), 'owner': meta.get('owner', ''),
               'source': f"extracted from {Path(path).name} by sdem pattern extract — a draft for the pattern owner's review (PR-30)"}
    if anc: pattern['applies_when'] = {'entity': rtype[anc], 'when': {'conforms_to': pid}}
    structure = {'anchor': anc, 'zones': zones, 'roles': roles, 'connectors': conns}
    if layout: structure['layout'] = layout
    draft = {'format': _p.PATTERN_FORMAT, 'description': f"{pattern['title']} — drafted from {Path(path).name}; review before including it in the profile.",
             'pattern': pattern, 'structure': structure, 'requires': []}
    report['issues'] = draft_issues(draft, merged, base_mm) if anc else []
    report['clean'] = not (report['unmapped_shapes'] or report['refused_connectors'] or report['unmapped_connectors'] or report['ignored_lines'] or report['issues'] or not anc)
    return draft, report


def draft_issues(draft, merged, base_mm):
    """The draft as the profile would include it — every issue the profile check would find with it (PR-29)."""
    import copy, tempfile, os
    from . import profile as _p
    m = copy.deepcopy(merged); m['_issues'] = list(m.get('_issues', []))
    fd, tmp = tempfile.mkstemp(suffix='.json'); os.close(fd)
    try:
        Path(tmp).write_text(json.dumps(draft), encoding='utf-8')
        before = len(m['_issues'])
        try: _p.include(m, tmp)
        except _p.ProfileError as err: return [str(err).replace(tmp, 'the draft')]
        return [i for i in _p.check(m, base_mm) if draft['pattern']['id'] in i or i in m['_issues'][before:]]
    finally: os.unlink(tmp)


def compare(old, new):
    """PR-31: what changed between the included pattern and a new extraction — roles by id, connectors by their ends and link."""
    def roles(d): return {r['id']: {k: r.get(k) for k in ('label', 'type', 'min', 'max', 'zone')} for r in (d.get('structure') or {}).get('roles', [])}
    def conns(d): return {(c['from'], c['to'], c.get('kind') or c.get('relationship')): {k: c.get(k) for k in ('label', 'min')} for c in (d.get('structure') or {}).get('connectors', [])}
    def zones(d): return {z['id']: {k: z.get(k) for k in ('label', 'check', 'entity')} for z in (d.get('structure') or {}).get('zones', [])}
    out = {}
    for name, f in (('roles', roles), ('connectors', conns), ('zones', zones)):
        a, b = f(old), f(new)
        key = (lambda k: ' → '.join(k[:2]) + f' ({k[2]})') if name == 'connectors' else str
        out[name] = {'added': [key(k) for k in b if k not in a], 'removed': [key(k) for k in a if k not in b],
                     'changed': [{'part': key(k), 'was': a[k], 'now': b[k]} for k in a if k in b and a[k] != b[k]]}
    if (old.get('structure') or {}).get('anchor') != (new.get('structure') or {}).get('anchor'):
        out['anchor'] = {'was': old['structure'].get('anchor'), 'now': new['structure'].get('anchor')}
    out['unchanged'] = not any(v['added'] or v['removed'] or v['changed'] for k, v in out.items() if isinstance(v, dict) and 'added' in v) and 'anchor' not in out
    return out


# ====================================================================== drawing (PR-25)

STATUS_CSS = """.sdv .pt-ok>.dv-box{stroke:#2e7d32;stroke-width:2.6}.sdv .pt-bad>.dv-box{stroke:#c62828;stroke-width:2.6}
.sdv .pt-missing>.dv-box{stroke:#c62828;stroke-width:2.2;stroke-dasharray:6 4;fill:none}.sdv .pt-unres>.dv-box{stroke:#b26a00;stroke-width:2.6}
.sdv .pt-opt>.dv-box{stroke-dasharray:6 4;opacity:.7}.sdv .pt-zone{fill:none;stroke:var(--dv-muted);stroke-width:1.4;stroke-dasharray:8 5}
.sdv .pt-zlabel{fill:var(--dv-muted);font-size:12px;font-weight:700;letter-spacing:.03em}.sdv .pt-badge{font-size:10px;font-weight:700}
.sdv .pt-badge.ok{fill:#2e7d32}.sdv .pt-badge.bad{fill:#c62828}.sdv .pt-badge.unres{fill:#b26a00}.sdv .pt-link.bad path{stroke:#c62828;stroke-dasharray:6 4}
@media (prefers-color-scheme:dark){.sdv .pt-ok>.dv-box{stroke:#6fcf97}.sdv .pt-bad>.dv-box,.sdv .pt-missing>.dv-box{stroke:#ff8a80}.sdv .pt-badge.ok{fill:#6fcf97}.sdv .pt-badge.bad{fill:#ff8a80}}"""


def _auto_layout(S, level_of):
    order = ['A1', 'A2', 'A3', 'A4']
    levels = sorted({level_of(r['type']) for r in S['roles']}, key=lambda l: (order.index(l) if l in order else 9, l))
    L, Z, y = {}, {}, 30
    for lvl in levels:
        x = 30
        rs = [r for r in S['roles'] if level_of(r['type']) == lvl]
        groups = [(None, [r for r in rs if not r.get('zone')])] + [(z['id'], [r for r in rs if r.get('zone') == z['id']]) for z in S.get('zones', [])]
        for zid, members in groups:
            if not members: continue
            pad = 24 if zid else 0
            x0 = x; x += pad
            for r in members: L[r['id']] = [x, y + pad + (10 if zid else 0), 180, 64]; x += 220
            if zid: Z[zid] = [x0, y, x - x0 - 40 + pad + 20, 64 + 2 * pad + 10]; x += 30
        y += 170
    return {'roles': L, 'zones': Z}


def _clip(box, px, py):
    x, y, w, h = box; cx, cy = x + w / 2, y + h / 2
    dx, dy = px - cx, py - cy
    if dx == 0 and dy == 0: return cx, cy
    s = min((w / 2) / abs(dx) if dx else 1e9, (h / 2) / abs(dy) if dy else 1e9)
    return cx + dx * s, cy + dy * s


def draw(st, level_of, status=None, binding=None, names=None, uid='p'):
    """An SVG of the pattern, in SDEM's ArchiMate look; with `status` ({part id: outcome}) and `binding` ({role: [record ids]}), over a design."""
    from .viewpoints import _shape, CSS, LINE
    S, pat = st['structure'], st['pattern']
    lay = S.get('layout') or {}
    if not lay.get('roles') or any(r['id'] not in lay['roles'] for r in S['roles']): lay = _auto_layout(S, level_of)
    boxes = {k: list(v) for k, v in lay['roles'].items()}; zb = {k: list(v) for k, v in (lay.get('zones') or {}).items()}
    xs = [b[0] for b in list(boxes.values()) + list(zb.values())]; ys = [b[1] for b in list(boxes.values()) + list(zb.values())]
    ox, oy = 30 - min(xs), 70 - min(ys)
    for b in list(boxes.values()) + list(zb.values()): b[0] += ox; b[1] += oy
    W = max(b[0] + b[2] for b in list(boxes.values()) + list(zb.values())) + 40
    H = max(b[1] + b[3] for b in list(boxes.values()) + list(zb.values())) + 50
    m = lambda k: f'dv{uid}-{k}'
    out = [f'<svg class="sdv" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" width="{W:.0f}" height="{H:.0f}" role="img" aria-label="{e(pat["title"])}">',
           f'<style>{CSS}\n{STATUS_CSS}</style><defs>'
           f'<marker id="{m("open")}" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="11" markerHeight="11" orient="auto-start-reverse"><path d="M1 1L11 6L1 11" class="dv-mk-line"/></marker>'
           f'<marker id="{m("fill")}" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="11" markerHeight="11" orient="auto-start-reverse"><path d="M1 1L11 6L1 11z" class="dv-mk-fill"/></marker>'
           f'<marker id="{m("tri")}" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="12" markerHeight="12" orient="auto-start-reverse"><path d="M1 1L11 6L1 11z" class="dv-mk-hollow"/></marker>'
           f'<marker id="{m("small")}" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M1 2L11 6L1 10" class="dv-mk-line"/></marker>'
           f'<marker id="{m("dot")}" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="8" markerHeight="8"><circle cx="5" cy="5" r="3.5" class="dv-mk-fill"/></marker>'
           f'<marker id="{m("dia")}" viewBox="0 0 14 12" refX="1" refY="6" markerWidth="13" markerHeight="11" orient="auto-start-reverse"><path d="M1 6L7 1L13 6L7 11z" class="dv-mk-fill"/></marker>'
           '</defs>', f'<rect class="dv-bg" width="{W:.0f}" height="{H:.0f}" rx="12"/>',
           f'<text class="dv-ctitle" x="24" y="32">{e(pat["id"])} · {e(pat["title"])} v{e(str(pat.get("version", "")))}</text>']
    for z in S.get('zones', []):
        if z['id'] not in zb: continue
        x, y, w, h = zb[z['id']]
        chk = f" — {z['check']['attribute']} {z['check']['op']} {z['check'].get('value')}" if z.get('check') else ''
        out.append(f'<rect class="pt-zone" x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" rx="14"/><text class="pt-zlabel" x="{x + 12:.0f}" y="{y + h - 10:.0f}">{e(z["label"] + chk)}</text>')
    roles = {r['id']: r for r in S['roles']}
    pills, labels = [], []
    for c in S.get('connectors', []):
        if c['from'] not in boxes or c['to'] not in boxes: continue
        a, b = boxes[c['from']], boxes[c['to']]
        p1 = _clip(a, b[0] + b[2] / 2, b[1] + b[3] / 2); p2 = _clip(b, a[0] + a[2] / 2, a[1] + a[3] / 2)
        mk, dash = LINE.get(c.get('kind'), ('open', 'dash')) if c.get('kind') else ('open', 'dash')
        attrs = f' marker-end="url(#{m(mk)})"' if mk else ''
        if c.get('kind') == 'composition': attrs += f' marker-start="url(#{m("dia")})"'
        if c.get('kind') == 'assignment': attrs += f' marker-start="url(#{m("dot")})"'
        label = c.get('label') or c.get('kind') or c.get('relationship')
        if c.get('min') == 0: label += ' (optional)'
        stc = (status or {}).get(c['id'])
        cls = ' bad' if stc == 'non_compliant' else ''
        mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
        tw = len(label) * 6.2 + 16
        while any(abs(mx - px) < (tw + pw) / 2 and abs(my - py) < 18 for px, py, pw in pills): my += 20
        pills.append((mx, my, tw))
        tip = f'<title>{e(c["id"])}: {e(c["from"])} → {e(c["to"])} ({e(c.get("kind") or c.get("relationship"))}){" — " + e(stc) if stc else ""}</title>'
        out.append(f'<g class="dv-link pt-link {dash}{cls}"><path d="M{p1[0]:.0f} {p1[1]:.0f} L{p2[0]:.0f} {p2[1]:.0f}"{attrs}/>{tip}</g>')
        labels.append(f'<g class="pt-label"><rect class="dv-pill" x="{mx - tw/2:.0f}" y="{my - 9:.0f}" width="{tw:.0f}" height="18" rx="9"/>'
                      f'<text class="dv-plabel" x="{mx:.0f}" y="{my + 4:.0f}" text-anchor="middle">{e(label)}</text>{tip}</g>')
    for r in S['roles']:
        if r['id'] not in boxes: continue
        x, y, w, h = boxes[r['id']]
        got = (binding or {}).get(r['id'])
        lo, hi = r.get('min', 1), r.get('max', 1)
        mult = '' if (lo, hi) == (1, 1) else ' (optional)' if (lo, hi) == (0, 1) else f" ({lo}..{'n' if hi is None else hi})"
        name = r.get('label', r['id']) + mult + (' ◆' if r['id'] == S.get('anchor') else '')
        sub = ', '.join(got) if got else (r['type'] if binding is None else ('optional — none' if r.get('min', 1) == 0 else 'missing'))
        n = {'id': r['id'], 'x': x, 'y': y, 'w': w, 'h': h, 'kids': [], 'r': {'t': r['type'], 'type': r['type'], 'layer': level_of(r['type']) if level_of(r['type']) in ('A1', 'A2', 'A3', 'A4') else 'A3', 'name': name}}
        svg = _shape(n, None).replace(f'>{e(r["id"])}</text>', f'>{e(sub)}</text>', 1)
        stt = (status or {}).get(r['id'])
        cls = {'compliant': 'pt-ok', 'non_compliant': 'pt-missing' if binding is not None and not got else 'pt-bad', 'unresolved': 'pt-unres', 'exception_approved': 'pt-unres'}.get(stt, 'pt-opt' if r.get('min', 1) == 0 else '')
        svg = svg.replace('class="dv-node"', f'class="dv-node {cls}"', 1)
        if stt:
            badge = {'compliant': ('ok', '✓ meets'), 'non_compliant': ('bad', '✗ ' + ('missing' if not got else 'not met')), 'unresolved': ('unres', '? unresolved'),
                     'exception_approved': ('unres', '⚑ exception'), 'not_applicable': ('unres', '– optional')}[stt]
            svg = svg.replace('</g>', f'<text class="pt-badge {badge[0]}" x="{x + 6:.0f}" y="{y - 5:.0f}">{e(badge[1])}</text></g>', 1) if svg.endswith('</g>') else svg
        out.append(svg)
    out += labels   # connector labels over the shapes, so a short connector's label stays readable
    out.append('</svg>')
    return ''.join(out)


def page(title, sub, svg, rows=()):
    tr = ''.join(f"<tr><td>{e(r['rule'])}</td><td>{e(r['outcome'].replace('_', ' '))}</td><td>{e(r['detail'] or '')}</td></tr>" for r in rows)
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{e(title)}</title><style>body{{margin:0;padding:20px;font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#f5f6f8;color:#1f2933}}'
            '@media (prefers-color-scheme:dark){body{background:#1d2232;color:#e7ebf3}}h1{font-size:18px;margin:0 0 4px}.sub{opacity:.7;font-size:13px;margin-bottom:10px}'
            '.frame{overflow:auto}table{border-collapse:collapse;margin-top:14px;font-size:13px}td{border-top:1px solid rgba(127,127,127,.3);padding:4px 10px 4px 0;vertical-align:top}</style></head><body>'
            f'<h1>{e(title)}</h1><div class="sub">{e(sub)}</div><div class="frame">{svg}</div>' + (f'<table>{tr}</table>' if tr else '') + '</body></html>')


# ====================================================================== the CLI

def _profile_for(a):
    from . import profile as _p
    if a.profile: return _p.resolve(a.profile)
    if a.workspace:
        f = Path(a.workspace) / _p.FILE
        if f.exists(): return _p.resolve(f)
    raise ValueError('name the organisation profile: --profile FILE, or --workspace DIR with an sdem-profile.json (its diagram_map maps the shapes)')


def _level_of(merged, base_mm):
    lv = {t: d['level'] for t, d in base_mm.entities.items()}
    for t in merged.get('types', []): lv[t['type']] = lv.get(t.get('extends')) or t['type'].split('.')[1]
    return lambda t: lv.get(t, t.split('.')[-2] if t.count('.') >= 2 else 'A3')


def main(argv=None):
    from .metamodel import Metamodel
    ap = argparse.ArgumentParser(prog='sdem pattern', formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description="Reference-architecture patterns as structures (PR-21…PR-31): extract a draft pattern from the organisation's diagram "
                                             "(draw.io, Visio, PlantUML, Mermaid), compare it with the pattern the profile includes, and draw a pattern — over a design.",
                                 epilog='Examples:\n  sdem pattern extract --from secure-api.drawio --profile profiles/bank-with-standards.json --id PAT-SECURE-API-S '
                                        '--title "Secure API (structure)" --owner "security architecture" --anchor Application --out draft.json\n'
                                        '  sdem pattern extract --from secure-api.vsdx --workspace workspaces/payments --id PAT-SECURE-API-S --compare profiles/patterns/secure-api-structure.json\n'
                                        '  sdem pattern draw --workspace workspaces/payments --id PAT-SECURE-API-S --anchor APP-PAY-HUB --format html -o work/secure-api.html')
    sub = ap.add_subparsers(dest='cmd', required=True)
    x = sub.add_parser('extract', help="a diagram → a DRAFT pattern file and a report; nothing enters the profile until a person includes it (PR-30)")
    x.add_argument('--from', dest='src', required=True, metavar='DIAGRAM'); x.add_argument('--profile', metavar='FILE'); x.add_argument('--workspace', metavar='DIR')
    x.add_argument('--id', required=True); x.add_argument('--title'); x.add_argument('--version', default='1.0'); x.add_argument('--owner', required=True, help='who owns the pattern (it is theirs to approve)')
    x.add_argument('--anchor', metavar='LABEL', help='the part the pattern applies to (its label or role id)')
    x.add_argument('--out', metavar='FILE', help='write the draft here (otherwise only the report)'); x.add_argument('--compare', metavar='PATTERN.json', help='what changed against this pattern file (PR-31)')
    x.add_argument('--json', action='store_true'); x.add_argument('--dry-run', action='store_true')
    d = sub.add_parser('draw', help='draw a pattern (PR-25) — with --workspace and --anchor, over that design: which part is there, which is missing')
    d.add_argument('--file', metavar='PATTERN.json'); d.add_argument('--id', help="a pattern the workspace's profile includes"); d.add_argument('--workspace', metavar='DIR')
    d.add_argument('--profile', metavar='FILE'); d.add_argument('--anchor', metavar='RECORD', help='draw over the design from this record')
    d.add_argument('--format', choices=('svg', 'html', 'json'), default='svg'); d.add_argument('-o', '--out', metavar='FILE'); d.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    try:
        base = Metamodel.base()
        if a.cmd == 'extract':
            merged = _profile_for(a)
            draft, rep = extract(a.src, merged, base, {'id': a.id, 'title': a.title, 'version': a.version, 'owner': a.owner}, a.anchor)
            if a.compare: rep['compared_with'] = a.compare; rep['changes'] = compare(json.loads(Path(a.compare).read_text(encoding='utf-8')), draft)
            if a.out and not a.dry_run: Path(a.out).write_text(json.dumps(draft, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
            if a.json: print(json.dumps({'report': rep, 'draft': draft, 'written': a.out if a.out and not a.dry_run else None, 'dry_run': a.dry_run}, indent=2, ensure_ascii=False))
            else: print(render_report(rep, draft, a.out if not a.dry_run else None))
            return 0 if rep['clean'] else 1
        merged = _profile_for(a) if (a.profile or a.workspace) else None
        from . import profile as _p
        if a.file:
            fd = json.loads(Path(a.file).read_text(encoding='utf-8'))
            if not fd.get('structure'): raise ValueError(f'{a.file}: the pattern has no structure to draw')
            st = {'pattern': fd['pattern'], 'structure': fd['structure']}
        else:
            if not merged or not a.id: raise ValueError('name the pattern: --file PATTERN.json, or --id with --workspace/--profile')
            st = next((s for s in merged['structures'] if s['pattern']['id'] == a.id), None)
            if not st: raise ValueError(f"{a.id}: the profile includes no structured pattern by that id ({', '.join(s['pattern']['id'] for s in merged['structures']) or 'none'})")
        level_of = _level_of(merged or {}, base)
        status = binding = None; rows = []
        if a.anchor:
            if not a.workspace: raise ValueError('--anchor draws over a design: give --workspace too')
            from .comply import workspace_data
            datasets, maps, mm, _ = workspace_data(a.workspace)
            pid = st['pattern']['id']
            found, bindings = evaluate(datasets, maps, mm, [st], _p.exceptions())
            rows = [f for f in found if f['record'] == a.anchor]
            status = {f['part']['id']: f['outcome'] for f in rows}
            binding = next((b['roles'] for b in bindings if b['anchor'] == a.anchor), None)
            if binding is None: raise ValueError(f"{a.anchor}: the pattern {pid} does not apply to it in {a.workspace} (its applies_when)")
            rows = [f for f in rows if f['outcome'] != 'not_applicable' or f['part']['kind'] == 'role']
        svg = draw(st, level_of, status, binding)
        title = f"{st['pattern']['id']} · {st['pattern']['title']}" + (f' — over {a.anchor}' if a.anchor else '')
        if a.format == 'json' or a.json:
            body = json.dumps({'pattern': st['pattern']['id'], 'anchor': a.anchor, 'binding': binding, 'status': status, 'svg': svg}, indent=2, ensure_ascii=False)
        elif a.format == 'html': body = page(title, 'drawn by sdem pattern draw from the pattern file' + (' over the design (stored, approved links only)' if a.anchor else ''), svg, rows)
        else: body = svg
        if a.out: Path(a.out).write_text(body, encoding='utf-8'); print(f'wrote {a.out}')
        else: print(body)
        return 0
    except (ValueError, KeyError, zipfile.BadZipFile, ET.ParseError) as err:
        from .profile import ProfileError  # noqa: F401
        print(f'ERROR: {err}', file=sys.stderr); return 2
    except Exception as err:
        from .profile import ProfileError
        if isinstance(err, ProfileError): print(f'ERROR: {err}', file=sys.stderr); return 2
        raise


def render_report(rep, draft, written):
    S = draft['structure']
    L = [f"Pattern extraction — {rep['source']} ({rep['format']}): {len(S['roles'])} part(s), {len(S['connectors'])} connector(s), {len(S['zones'])} zone(s); anchor {S['anchor'] or 'NOT SET'}"]
    for r in rep['roles']: L.append(f"  part      {r['role']:<22} {r['type']:<28} {r['how']}  [{r['source']}]")
    for c in rep['connectors']: L.append(f"  connector {c['connector']:<4} {c['from']} → {c['to']} ({c['link']})  {c['how']}  [{c['source']}]")
    for z in rep['zones']: L.append(f"  zone      {z['zone']:<22} {', '.join(z['roles']) or '(no part)'}" + (f"  check {z['check']['attribute']} {z['check']['op']} {z['check'].get('value')}" if z.get('check') else ''))
    for k, title in (('unmapped_shapes', 'NOT MAPPED'), ('unmapped_connectors', 'NOT MAPPED'), ('refused_connectors', 'REFUSED'), ('ignored_lines', 'NOT READ')):
        for x in rep[k]: L.append(f"  {title:<10} {x.get('shape') or x.get('connector') or x.get('where')}: {x.get('label') or x.get('line') or ''} — {x['why']}")
    for i in rep['issues']: L.append(f'  ISSUE      {i}')
    for n in rep['notes']: L.append(f'  note       {n}')
    ch = rep.get('changes')
    if ch:
        L.append(f"\nCompared with {rep['compared_with']}: " + ('no change' if ch['unchanged'] else ''))
        for k in ('roles', 'connectors', 'zones'):
            for what in ('added', 'removed'):
                for p in ch[k][what]: L.append(f"  {what:<8} {k[:-1]} {p}")
            for c in ch[k]['changed']: L.append(f"  changed  {k[:-1]} {c['part']}: {c['was']} → {c['now']}")
        if ch.get('anchor'): L.append(f"  changed  anchor: {ch['anchor']['was']} → {ch['anchor']['now']}")
    L.append('')
    L.append(('Clean: every shape and connector mapped and allowed. ' if rep['clean'] else 'Not clean — see above; nothing was guessed or dropped. ')
             + (f'Draft written to {written} — ' if written else 'No draft written (--out) — ')
             + "the pattern owner reviews it and includes it in the profile (PR-30).")
    return '\n'.join(L)


if __name__ == '__main__':
    sys.exit(main())
