"""`sdem layout` — a layer drawn by what owns what: the containment layout (docs/design/sdem-layer-containment-design.md; the owner's
decisions C1–C6, 2026-11-15). One layout for every drawing — the 3D view, `sdem view`, any site that reads the JSON.

A4 is drawn by its network zones (sdem/zone_layout.py). A1–A3 are drawn by each framework's own hierarchy, without deviating from it:

  · the regions are existing standard records — for A2, BIAN's service landscape: business area → business domain → service domain →
    service group → service operation, and the control record (in its service domain) → its behaviour qualifiers (RA2-01…05, RA2-11);
  · a record is drawn inside a region only through a structural link — composition, aggregation, assignment or realisation (C2) —
    in ONE primary hierarchy (C3); its other links are lines;
  · what has no structural owner stays in a group of its kind (C4) — for A2, business scenarios, the business object model, asset types
    and functional patterns, semantic APIs;
  · links between regions are derived (potential), never stored (C5) — for A2, service domain ↔ service domain when a business scenario
    aggregates operations of both.

  sdem layout --layer A2 --workspace examples/payment-initiation
"""
import argparse, json, sys
from pathlib import Path

# the primary hierarchy of each layer: (parent type, link kind, child type) in order of precedence, and the groups by kind (C3, C4)
HIERARCHY = {
    'A2': {
        'nest': [('A2.BusinessArea', 'composition', 'A2.BusinessDomain'), ('A2.BusinessDomain', 'composition', 'A2.ServiceDomain'),
                 ('A2.ServiceDomain', 'composition', 'A2.ServiceGroup'), ('A2.ServiceDomain', 'aggregation', 'A2.ControlRecord'),
                 ('A2.ServiceGroup', 'composition', 'A2.ServiceOperation'), ('A2.ControlRecord', 'composition', 'A2.BehaviorQualifier'),
                 ('A2.BOMModel', 'aggregation', 'A2.BusinessObject'), ('A2.BusinessObject', 'composition', 'A2.BusinessObjectAttribute')],
        'containers': ['A2.BusinessArea', 'A2.BusinessDomain', 'A2.ServiceDomain', 'A2.ServiceGroup', 'A2.ControlRecord', 'A2.BOMModel', 'A2.BusinessObject'],
        'kinds': {'A2.BusinessArea': 'Business area', 'A2.BusinessDomain': 'Business domain', 'A2.ServiceDomain': 'Service domain',
                  'A2.ServiceGroup': 'Service group', 'A2.ControlRecord': 'Control record', 'A2.BOMModel': 'Business object model',
                  'A2.BusinessObject': 'Business object'},
        'groups': [('Business scenarios', ['A2.BusinessScenario']),
                   ('Business object model', ['A2.BOMModel', 'A2.BusinessObject', 'A2.BusinessObjectAttribute']),
                   ('Asset types and patterns', ['A2.AssetType', 'A2.FunctionalPattern']),
                   ('Semantic APIs', ['A2.SemanticAPI'])],
        'not_in': 'Not in the service landscape',
    },
}


class ContainmentError(ValueError):
    pass


def layout(doc, layer, mm=None):
    """The containment layout of one layer's document — JSON-ready, coordinates as fractions of the plate (as sdem/zone_layout.py)."""
    from .metamodel import Metamodel
    mm = mm or Metamodel.load()
    if layer == 'A4':
        from .zone_layout import layout as zl
        return zl(doc, mm)
    H = HIERARCHY.get(layer)
    if not H: raise ContainmentError(f'layer {layer}: no containment hierarchy yet — A2 is built (A1 and A3 follow, C6)')
    recs = {i['id']: i for i in doc.get('instances', [])}
    typ = {x: r['type'] for x, r in recs.items()}
    is_ = lambda x, t: x in typ and mm.is_a(typ[x], t)
    # the primary parent of each record: the first nesting row (in order) that links a parent to it (C3)
    parent, used = {}, set()
    for pt, kind, ct in H['nest']:
        for r in doc.get('relationships', []):
            a, b = r['source'], r['target']
            if r['kind'] == kind and is_(a, pt) and is_(b, ct) and b not in parent and a != b:
                parent[b] = a; used.add((a, b))
    containers = {x for x in recs if any(is_(x, t) for t in H['containers'])}
    group_of = {}
    for label, types in H['groups']:
        for x in recs:
            if x not in group_of and any(is_(x, t) for t in types): group_of[x] = label
    # the regions: each container record (C1), and a group for each kind with no structural owner (C4)
    R = lambda x: 'R:' + x
    G = lambda lab: 'G:' + lab
    kids, own = {}, {}
    def region_of(x):   # the region a record sits in: its primary parent's region, else its kind's group
        p = parent.get(x)
        if p in containers: return R(p)
        return G(group_of[x]) if group_of.get(x) else None
    for x in recs:
        if x in containers:
            own.setdefault(R(x), [])   # the record IS the region (ArchiMate's nested notation): it is placed at its heading, not in the grid
            up = region_of(x)
            if up: kids.setdefault(up, []).append(R(x))
        else:
            up = region_of(x)
            if up: own.setdefault(up, []).append(x)
    tops = sorted({R(x) for x in containers if not region_of(x)} | {G(g) for g in set(group_of.values()) if own.get(G(g)) or kids.get(G(g))},
                  key=lambda z: (z.startswith('G:'), z))   # the landscape first, then the groups by kind
    lone = sorted(x for x in recs if x not in containers and not region_of(x))
    weight = {}
    def wt(z):
        if z not in weight: weight[z] = 1 + len(own.get(z, [])) + sum(wt(k) for k in kids.get(z, []))
        return weight[z]
    pos, rects, part_of, level = {}, {}, {}, {}
    HDR, PAD, GAP = 0.08, 0.01, 0.014
    def grid(xs, x0, y0, x1, y1):
        n = len(xs)
        if not n: return
        w, h = max(x1 - x0, 1e-6), max(y1 - y0, 1e-6)
        cols = max(1, min(n, round((n * w / h) ** 0.5))); rows = -(-n // cols)
        for i, x in enumerate(xs):
            c, r_ = i % cols, i // cols
            pos[x] = (x0 + w * (c + 0.5) / cols, y0 + h * (r_ + 0.5) / rows)
    def split(items, x0, y0, x1, y1):   # share [x0,x1]×[y0,y1] among items by weight, along the longer side
        tot = sum(wt_ for _, wt_ in items) or 1
        horiz = (x1 - x0) >= (y1 - y0)
        span = (x1 - x0 if horiz else y1 - y0) - GAP * (len(items) - 1)
        a_ = x0 if horiz else y0; out = []
        for it, wt_ in items:
            d = span * wt_ / tot
            out.append((it, (a_, y0, a_ + d, y1) if horiz else (x0, a_, x1, a_ + d))); a_ += d + GAP
        return out
    def place(z, x0, y0, x1, y1, lv):
        rects[z] = (x0, y0, x1, y1); level[z] = lv
        if z.startswith('R:'): pos[z[2:]] = (x1 - min(0.05, (x1 - x0) / 2), y0 + min(HDR, y1 - y0) / 2)   # the container's own record: in its header band, right of the heading — lines to it end on it
        ix0, iy0, ix1, iy1 = x0 + PAD, y0 + HDR, x1 - PAD, y1 - PAD
        mine, ks = own.get(z, []), kids.get(z, [])
        parts = ([('own', len(mine))] if mine else []) + [(k, wt(k)) for k in ks]
        for it, (a0, b0, a1, b1) in split(parts, ix0, iy0, ix1, iy1):
            if it == 'own': grid(mine, a0, b0, a1, b1)
            else: part_of[it] = z; place(it, a0, b0, a1, b1, lv + 1)
    strip = None
    y_end = 1.0 - (0.1 if lone else 0)
    for z, (a0, b0, a1, b1) in split([(t, max(wt(t), 0.12 * sum(wt(u) for u in tops))) for t in tops], 0.0, 0.0, 1.0, y_end):
        place(z, a0, b0, a1, b1, 0)
    if lone:
        strip = {'label': H['not_in'], 'not_in_a_zone': lone, 'rect': [0.0, round(y_end + 0.01, 4), 1.0, 1.0]}
        grid(lone, 0.02, y_end + 0.03, 0.98, 0.99)
    def label(z):
        if z.startswith('G:'): return z[2:]
        x = z[2:]; return f"{H['kinds'].get(typ.get(x), typ.get(x, '').split('.')[-1])} · {recs[x].get('name', x)}"
    r4 = lambda q: [round(v, 4) for v in q]
    zones = [{'id': z, 'record': z[2:] if z.startswith('R:') else None, 'name': z[2:] if z.startswith('G:') else recs[z[2:]].get('name', z[2:]), 'label': label(z),
              'level': level[z], 'kind': 'group' if z.startswith('G:') else typ.get(z[2:]), 'part_of': part_of.get(z), 'rect': r4(rects[z])} for z in rects]
    inner = {x: z for z, xs in own.items() for x in xs}
    inner.update({z[2:]: z for z in rects if z.startswith('R:')})
    shapes = [{'id': x, 'name': recs[x].get('name', x), 'type': typ[x], 'zone': inner.get(x), 'at': r4(p)} for x, p in pos.items()]
    links = [{'source': r['source'], 'kind': r['kind'], 'target': r['target'], 'shown_by': 'position' if (r['source'], r['target']) in used else 'line'}
             for r in doc.get('relationships', []) if r['source'] in pos and r['target'] in pos]
    # C5: service domain ↔ service domain when a business scenario aggregates operations of both — derived (potential), never stored
    def domain(x):
        while x and not is_(x, 'A2.ServiceDomain'): x = parent.get(x)
        return x
    conns, seen = [], set()
    for sc in [x for x in recs if is_(x, 'A2.BusinessScenario')]:
        sds = sorted({domain(r['target']) for r in doc.get('relationships', []) if r['source'] == sc and r['kind'] == 'aggregation'} - {None})
        for i, a in enumerate(sds):
            for b in sds[i + 1:]:
                if (a, b) not in seen: seen.add((a, b)); conns.append({'from': R(a), 'to': R(b), 'rule': 'derived (potential)', 'via': sc})
    return {'viewpoint': 'containment', 'layer': layer, 'model_id': doc.get('model_id'), 'zones': zones, 'runs_on': [],
            'not_in_a_zone': strip['rect'] if strip else None, 'strip': strip, 'shapes': sorted(shapes, key=lambda s: s['id']), 'links': links,
            'connections': conns, 'left_out': []}


FILES = {'A1': 'a1-business.json', 'A2': 'a2-service-domain.json', 'A3': 'a3-application.json', 'A4': 'a4-technology.json'}


def load(workspace, layer, environment='production'):
    f = Path(workspace) / FILES.get(layer, '')
    if layer not in FILES or not f.exists(): raise ContainmentError(f'{workspace}: no {FILES.get(layer, layer)} — nothing to lay out')
    if layer == 'A4':
        from .zone_layout import load as zl
        return zl(workspace, environment)
    return layout(json.loads(f.read_text(encoding='utf-8')), layer)


def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem layout', formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description='A layer drawn by what owns what — each region an existing standard record, nesting only through structural links '
                                             '(the containment layout; A4 by its network zones). The layout every drawing uses. Read-only.',
                                 epilog=__doc__.split('\n\n')[-1])
    ap.add_argument('--layer', required=True, choices=sorted(FILES), help='the layer')
    ap.add_argument('--workspace', dest='estate', required=True, metavar='DIR')
    ap.add_argument('--environment', default='production', metavar='NAME', help='A4 only: the one environment drawn (default production; all for every one)')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    try: lay = load(a.estate, a.layer, a.environment)
    except (ContainmentError, ValueError) as e: print(f'ERROR: {e}', file=sys.stderr); return 2
    if a.json: print(json.dumps(lay, indent=2)); return 0
    print(f"{a.layer} drawn {'by network zone' if a.layer == 'A4' else 'by what owns what'} — {len(lay['zones'])} region(s), {len(lay['shapes'])} record(s)")
    for z in lay['zones']:
        held = [s['id'] for s in lay['shapes'] if s['zone'] == z['id'] and s['id'] != (z.get('record') or '')]
        print(f"{'  ' * (z['level'] or 0)}{z['label']}" + (f"  — {', '.join(held)}" if held else ''))
    for c in lay['connections']: print(f"  {c['from'][2:]} ↔ {c['to'][2:]}  ({c['rule']}{', via ' + c['via'] if c.get('via') else ''})")
    if lay['strip'] and lay['strip'].get('not_in_a_zone'): print(f"{lay['strip']['label']}: {', '.join(lay['strip']['not_in_a_zone'])}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
