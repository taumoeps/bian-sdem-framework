"""The deployment-zones viewpoint: how A4 is laid out by its network zones (metamodel 0.10.0–0.12.0; the owner, 2026-11-14).

SDEM owns the layout so every drawing of A4 agrees — `sdem zones --layout`, `sdem view`, and any site that reads the JSON (the DESNRE
hero). The rules, which the owner set while reviewing the 3D view:

  · a zone is a REGION, not a shape: level-0 zones (cloud, on premises) share the plate side by side, each at least 30% wide; level-1
    zones (DMZ first, then internal) fill their level 0; level-2 private zones fill their level 1;
  · each shape sits in the zone that holds it (RA4-38), or in its host's zone stacked under the host ("runs on" group); the shapes of a
    zone are spread evenly over its space and kept inside it;
  · an environment, a network or a path is not deployed, but is drawn in the smallest zone holding everything it groups or connects;
    one environment at a time
    (default production): the others, and what only they run, are left out;
  · a retired shape is left out (it is not deployed any more);
  · placement and nesting are shown by position — no line; zone connections are arrows between regions (ZC-01, ZC-02 — sdem/hosting.py);
    a shape no zone holds goes in a "Not in a zone" strip (LC-16 names it); a network or path joining shapes in different level-0
    zones goes in the same strip, labelled "Across zones" — it is not missing a zone.

Coordinates are fractions of the plate: x left → right, y far → near, both 0…1.
"""
import json

UNPLACED = ('A4.CommunicationNetwork', 'A4.NetworkZone', 'A4.DeploymentEnvironment', 'A4.Path')
_X0, _X1, _Z0, _Z1 = -2.8, 2.8, -2.7, 2.7   # the working plate; the constants below are tuned to it


class LayoutError(ValueError):
    pass


def only_environment(doc, keep):
    """A4 for one deployment environment: drop the other environments, what they group, and what only those run on or hold.
    `keep` matches an environment's name or its environment_kind (case-insensitive); 'all' keeps everything. Returns (doc, dropped ids)."""
    if not keep or keep.lower() == 'all': return doc, set()
    recs = {r['id']: r for r in doc.get('instances', [])}; rels = doc.get('relationships', [])
    envs = [r for r in recs.values() if r['type'] == 'A4.DeploymentEnvironment']
    if not envs: return doc, set()
    match = lambda e: keep.lower() in (e['name'].lower(), str((e.get('attributes') or {}).get('environment_kind', '')).lower())
    kept_envs = {e['id'] for e in envs if match(e)}
    if not kept_envs: raise LayoutError(f"environment {keep!r}: none is called that — {', '.join(e['name'] for e in envs)} (or all)")
    members = lambda e: {r['target'] for r in rels if r['source'] == e and r['kind'] == 'aggregation'}
    kept = set().union(*[members(e) for e in kept_envs])
    drop = {e['id'] for e in envs if e['id'] not in kept_envs}
    drop |= set().union(*[members(e) for e in drop] or [set()]) - kept
    while True:   # what only dropped records run on or hold goes too (a deployment's image stays if a kept platform holds it)
        more = {r['target'] for r in rels if r['source'] in drop and r['kind'] in ('assignment', 'composition', 'aggregation') and r['target'] not in drop and r['target'] not in kept
                and not any(x['target'] == r['target'] and x['source'] not in drop and x['kind'] in ('assignment', 'composition', 'aggregation') for x in rels)}
        if not more: break
        drop |= more
    return {**doc, 'instances': [r for r in doc['instances'] if r['id'] not in drop],
            'relationships': [r for r in rels if r['source'] not in drop and r['target'] not in drop]}, drop


def _place(recs, rels, x0=_X0, x1=_X1, z0=_Z0, z1=_Z1):
    """The layout in plate units: ({id: (x, z)}, regions, links shown by position, zone pairs side by side, {shape: innermost zone})."""
    typ = {r['id']: r['type'] for r in recs}; name = {r['id']: r['name'] for r in recs}
    at = {r['id']: (r.get('attributes') or {}) for r in recs}
    zones_ = [r['id'] for r in recs if r['type'] == 'A4.NetworkZone']
    parent, direct, hosts, implied = {}, {}, {}, set()
    for r in rels:
        a, b, k = r['source'], r['target'], r['kind']
        if a not in typ or b not in typ: continue
        if a in zones_ and k == 'composition' and b in zones_: parent[b] = a; continue
        if a in zones_ and k == 'aggregation' and typ[b] not in UNPLACED: direct.setdefault(a, []).append(b); continue
        if typ[a] in UNPLACED or typ[b] in UNPLACED: continue
        if k in ('assignment', 'composition', 'aggregation', 'realization') and b not in hosts: hosts[b] = a
    hosted = {}
    for b, a in hosts.items(): hosted.setdefault(a, []).append(b)
    def stack(x, seen=()):
        out = [x]
        for y in hosted.get(x, []):
            if y not in seen and not any(y in v for v in direct.values()): out += stack(y, seen + (x,))
        return out
    for x, ys in hosted.items():
        for y in ys: implied.add((x, y))
    kids = {z: [k for k in zones_ if parent.get(k) == z] for z in zones_}
    order = lambda z: (0 if at[z].get('zone_kind') == 'dmz' else 1, z)
    ROW, PAD, LBL = 0.42, 0.34, 0.26   # PAD: the gap between neighbouring zones — room for the arrow that connects them
    def need(z):
        groups = [stack(x) for x in direct.get(z, [])]
        rows = max([len(g) for g in groups] or [0])
        return LBL + max(rows, 1) * ROW + 0.05 + sum(need(k) + PAD for k in sorted(kids[z], key=order)) + 0.05
    zone_of, spanning = {}, set()
    for z, xs in direct.items():
        for x in xs:
            for q in stack(x): zone_of.setdefault(q, z)
    def chain(z):
        out = []
        while z: out.append(z); z = parent.get(z)
        return out
    for r in recs:   # an environment, a network or a path is not deployed: drawn in the smallest zone holding everything it groups or connects
        if r['type'] not in ('A4.DeploymentEnvironment', 'A4.CommunicationNetwork', 'A4.Path'): continue
        ends = (r.get('attributes') or {})
        members = [x['target'] for x in rels if x['source'] == r['id'] and x['kind'] == 'aggregation' and x['target'] in zone_of]
        if r['type'] != 'A4.DeploymentEnvironment':
            members += [x['source'] if x['target'] == r['id'] else x['target'] for x in rels if r['id'] in (x['source'], x['target'])
                        and x['kind'] in ('association', 'aggregation', 'composition') and (x['target'] if x['source'] == r['id'] else x['source']) in zone_of]
            members += [ends[k] for k in ('from', 'to') if ends.get(k) in zone_of]
        if not members: continue
        common = chain(zone_of[members[0]])
        for m in members[1:]: common = [c for c in common if c in chain(zone_of[m])]
        if common: direct.setdefault(common[0], []).append(r['id'])
        else: spanning.add(r['id'])   # it connects shapes in different level-0 zones — drawn across them, not missing a zone
    pos, regions = {}, []
    MX, MZ = 0.32, 0.2   # a shape's half footprint: kept this far inside its zone
    def own_need(z):
        groups = [stack(x) for x in direct.get(z, [])]
        return max([len(g) for g in groups] or [0]) * ROW + 0.35 if groups else 0.55
    def place(z, xa, za, xb, zb):
        regions.append({'kind': 'zone', 'id': z, 'rect': (xa, za, xb, zb)})
        groups = [stack(x) for x in direct.get(z, [])]
        ks = sorted(kids[z], key=order)
        want = [own_need(z)] + [need(k) for k in ks]
        if groups or not ks:
            f = ((zb - za) - PAD * len(ks) - (0.1 if ks else 0)) / (sum(want) or 1)
            own_h = want[0] * f
        else:   # no shapes of its own: only its heading's room — the zones inside it fill the rest
            own_h = LBL + 0.06
            f = ((zb - za) - own_h - PAD * len(ks) + PAD - 0.1) / (sum(want[1:]) or 1)
        if groups:
            gx0, gx1 = xa + MX, xb - MX
            gz0, gz1 = za + 0.3 + MZ, za + own_h - MZ - 0.1
            if gz1 < gz0: gz1 = gz0
            n = len(groups)
            for i, g in enumerate(groups):
                cx = gx0 + (gx1 - gx0) * ((i + 0.5) / n) if n > 1 or gx1 > gx0 else (gx0 + gx1) / 2
                L = len(g); step = min(ROW * 1.6, (gz1 - gz0) / max(L - 1, 1)) if L > 1 else 0
                top = (gz0 + gz1) / 2 - step * (L - 1) / 2
                for j, q in enumerate(g): pos[q] = (cx, top + j * step)
                if L > 1:
                    hw = min(0.45, (gx1 - gx0) / (2 * n) + MX - 0.05)
                    regions.append({'kind': 'runs_on', 'platform': g[0], 'holds': g[1:], 'rect': (cx - hw, top - MZ - 0.06, cx + hw, top + step * (L - 1) + MZ + 0.06)})
        y = za + own_h
        for i, (k, h) in enumerate(zip(ks, want[1:])):
            gap = PAD if (groups or i) else 0
            place(k, xa + 0.12, y + gap, xb - 0.12, y + gap + h * f); y += gap + h * f
    tops = sorted([z for z in zones_ if z not in parent], key=lambda z: (at[z].get('zone_kind') != 'cloud', z))
    def weight(z):
        return max(1, len(direct.get(z, []))) + sum(weight(k) for k in kids[z])
    rest = [r['id'] for r in recs if r['type'] != 'A4.NetworkZone' and r['id'] not in zone_of and not any(r['id'] in v for v in direct.values())]
    zb_top = z1 - (0.6 if rest else 0)
    raw = [weight(t) / (sum(weight(u) for u in tops) or 1) for t in tops]
    share = [max(r, 0.3) if len(tops) > 1 else 1 for r in raw]; share = [x / sum(share) for x in share]   # each level-0 zone at least 30% wide
    xa = x0
    for i, t in enumerate(tops):
        xb = xa + (x1 - x0) * share[i]
        place(t, xa + (0.17 if i else 0), z0, xb - (0.17 if i < len(tops) - 1 else 0), zb_top); xa = xb
    rest = [r['id'] for r in recs if r['id'] not in pos and r['type'] != 'A4.NetworkZone']
    if rest:   # only what no zone holds, even through its host (LC-16 names it)
        lone = [q for q in rest if q not in spanning]
        label = 'Not in a zone' if not spanning & set(rest) else 'Across zones' if not lone else 'Not in a zone · across zones'
        regions.append({'kind': 'not_in_a_zone', 'label': label, 'lone': lone, 'rect': (x0, zb_top + 0.1, x1, z1)})
        for i, q in enumerate(rest): pos[q] = (x0 + (x1 - x0) * (i + 0.5) / len(rest), (zb_top + 0.1 + z1) / 2)
    implied |= {(b, a) for a, b in implied}
    for z, xs in direct.items():
        for x in xs: implied |= {(z, x), (x, z)}
    implied |= {(p, c) for c, p in parent.items()} | {(c, p) for c, p in parent.items()}
    inner_zone = {}
    for z, xs in direct.items():
        for x in xs:
            for q in stack(x): inner_zone.setdefault(q, z)
    return pos, regions, implied, inner_zone, name, at


def layout(doc, mm=None, environment='production'):
    """The deployment-zones layout of an A4 document — JSON-ready, coordinates as fractions of the plate."""
    from .hosting import zone_connections
    from .metamodel import Metamodel
    mm = mm or Metamodel.load()
    doc, dropped = only_environment(doc, environment)
    gone = {i['id'] for i in doc.get('instances', []) if i.get('lifecycle_status') == 'retired'}   # not deployed any more: not drawn (as LC-16, LC-21)
    if gone:
        dropped |= gone
        doc = {**doc, 'instances': [i for i in doc['instances'] if i['id'] not in gone],
               'relationships': [r for r in doc.get('relationships', []) if r['source'] not in gone and r['target'] not in gone]}
    recs = doc.get('instances', []); rels = doc.get('relationships', [])
    if not any(r['type'] == 'A4.NetworkZone' for r in recs):
        raise LayoutError('no network zones recorded — place each shape in a zone first (RA4-38, LC-16; sdem aid proposes them)')
    pos, regions, implied, inner_zone, name, at = _place(recs, rels)
    u = lambda x: round((x - _X0) / (_X1 - _X0), 4); v = lambda z: round((z - _Z0) / (_Z1 - _Z0), 4)
    rect = lambda r: [u(r[0]), v(r[1]), u(r[2]), v(r[3])]
    parent = {r['target']: r['source'] for r in rels if r['kind'] == 'composition' and r['source'] in at and r['target'] in at
              and at[r['source']].get('zone_level') is not None and at[r['target']].get('zone_level') is not None}
    typ = {r['id']: r['type'] for r in recs}
    zones = [{'id': g['id'], 'name': name[g['id']], 'label': f"Level {at[g['id']].get('zone_level', '?')} · {name[g['id']]}",
              'level': at[g['id']].get('zone_level'), 'kind': at[g['id']].get('zone_kind'), 'part_of': parent.get(g['id']), 'rect': rect(g['rect'])}
             for g in regions if g['kind'] == 'zone']
    zone_ids = {z['id'] for z in zones}
    shapes = [{'id': x, 'name': name[x], 'type': typ[x], 'zone': inner_zone.get(x), 'at': [u(p[0]), v(p[1])]} for x, p in pos.items() if x not in zone_ids]
    links = [{'source': r['source'], 'kind': r['kind'], 'target': r['target'], 'shown_by': 'position' if (r['source'], r['target']) in implied else 'line'}
             for r in rels if r['source'] not in zone_ids and r['target'] not in zone_ids and r['source'] in pos and r['target'] in pos]
    return {'viewpoint': 'deployment-zones', 'model_id': doc.get('model_id'), 'environment': environment or 'all', 'left_out': sorted(dropped),
            'zones': zones,
            'runs_on': [{'platform': g['platform'], 'holds': g['holds'], 'rect': rect(g['rect'])} for g in regions if g['kind'] == 'runs_on'],
            'not_in_a_zone': next((rect(g['rect']) for g in regions if g['kind'] == 'not_in_a_zone'), None),
            'strip': next(({'label': g['label'], 'not_in_a_zone': g['lone'], 'rect': rect(g['rect'])} for g in regions if g['kind'] == 'not_in_a_zone'), None),
            'shapes': sorted(shapes, key=lambda s: s['id']), 'links': links,
            'connections': [{'from': a, 'to': b, 'rule': r} for a, b, r in zone_connections(doc, mm) if r in ('ZC-01', 'ZC-02') and a in zone_ids and b in zone_ids]}


def load(workspace, environment='production'):
    from pathlib import Path
    f = Path(workspace) / 'a4-technology.json'
    if not f.exists(): raise LayoutError(f'{workspace}: no a4-technology.json — no technology layer to lay out')
    return layout(json.loads(f.read_text(encoding='utf-8')), environment=environment)
