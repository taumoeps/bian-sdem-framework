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
from .identity import load as _jload  # DL-11: a design's files read through one boundary (docs/design/sdem-data-layer-spec.md)
from .identity import T as _T, layer as _L  # ST-01…ST-05: layers and types by id (docs/design/sdem-stable-identity-spec.md)
import argparse, json, sys
from pathlib import Path

# the primary hierarchy of each layer: (parent type, link kind, child type) in order of precedence, and the groups by kind (C3, C4)
HIERARCHY = {
    _L('bian'): {
        'nest': [(_T('bian.BusinessArea'), 'composition', _T('bian.BusinessDomain')), (_T('bian.BusinessDomain'), 'composition', _T('bian.ServiceDomain')),
                 (_T('bian.ServiceDomain'), 'composition', _T('bian.ServiceGroup')), (_T('bian.ServiceDomain'), 'aggregation', _T('bian.ControlRecord')),
                 (_T('bian.ServiceGroup'), 'composition', _T('bian.ServiceOperation')), (_T('bian.ControlRecord'), 'composition', _T('bian.BehaviorQualifier')),
                 (_T('bian.BOMModel'), 'aggregation', _T('bian.BusinessObject')), (_T('bian.BusinessObject'), 'composition', _T('bian.BusinessObjectAttribute'))],
        'containers': [_T('bian.BusinessArea'), _T('bian.BusinessDomain'), _T('bian.ServiceDomain'), _T('bian.ServiceGroup'), _T('bian.ControlRecord'), _T('bian.BOMModel'), _T('bian.BusinessObject')],
        'kinds': {_T('bian.BusinessArea'): 'Business area', _T('bian.BusinessDomain'): 'Business domain', _T('bian.ServiceDomain'): 'Service domain',
                  _T('bian.ServiceGroup'): 'Service group', _T('bian.ControlRecord'): 'Control record', _T('bian.BOMModel'): 'Business object model',
                  _T('bian.BusinessObject'): 'Business object'},
        'groups': [('Business scenarios', [_T('bian.BusinessScenario')]),
                   ('Business object model', [_T('bian.BOMModel'), _T('bian.BusinessObject'), _T('bian.BusinessObjectAttribute')]),
                   ('Asset types and patterns', [_T('bian.AssetType'), _T('bian.FunctionalPattern')]),
                   ('Semantic APIs', [_T('bian.SemanticAPI')])],
        'not_in': 'Not in the service landscape',
        'skip': [_T('bian.BusinessObjectAttribute')],   # metamodel 0.15.0 (TL-03): a business object's fields are not shapes — BIAN 14.0.0 gives hundreds
    },
    _L('business'): {   # the capability map (ArchiMate Capability Map viewpoint; TOGAF, BIZBOK)
        'nest': [(_T('business.BusinessCapability'), 'composition', _T('business.BusinessCapability')), (_T('business.BusinessCapability'), 'aggregation', _T('business.BusinessCapability')),
                 (_T('business.BusinessProcess'), 'composition', _T('business.BusinessProcess')), (_T('business.BusinessProcess'), 'composition', _T('business.BusinessActivity')),
                 (_T('business.BusinessActivity'), 'composition', _T('business.BusinessActivity')),
                 (_T('business.BusinessCapability'), 'realization', _T('business.BusinessProcess'), 'up'), (_T('business.BusinessCapability'), 'realization', _T('business.BusinessActivity'), 'up'),
                 (_T('business.ValueStream'), 'composition', _T('business.ValueStreamStage')),
                 (_T('business.BusinessActor'), 'composition', _T('business.BusinessActor')), (_T('business.BusinessActor'), 'aggregation', _T('business.BusinessActor')),
                 (_T('business.BusinessRole'), 'composition', _T('business.BusinessRole')), (_T('business.BusinessRole'), 'aggregation', _T('business.BusinessRole')),
                 (_T('business.BusinessObject'), 'composition', _T('business.BusinessObject')), (_T('business.BusinessObject'), 'aggregation', _T('business.BusinessObject')),
                 (_T('business.BusinessService'), 'composition', _T('business.BusinessService')), (_T('business.BusinessRequirement'), 'composition', _T('business.BusinessRequirement')),
                 (_T('business.Product'), 'composition', _T('business.Product')), (_T('business.Product'), 'aggregation', _T('business.BusinessService'))],   # metamodel 0.17.0: a product holds its services
        'containers': [_T('business.BusinessCapability'), _T('business.BusinessProcess'), _T('business.ValueStream'), _T('business.Product')],
        'kinds': {_T('business.BusinessCapability'): 'Capability', _T('business.BusinessProcess'): 'Process', _T('business.BusinessActivity'): 'Activity', _T('business.ValueStream'): 'Value stream', _T('business.Product'): 'Product'},
        'groups': [('Products', [_T('business.Product')]), ('Value streams', [_T('business.ValueStream'), _T('business.ValueStreamStage')]), ('Events', [_T('business.BusinessEvent')]), ('Channels', [_T('business.BusinessInterface')]),
                   ('Actors and roles', [_T('business.BusinessActor'), _T('business.BusinessRole')]),
                   ('Business objects', [_T('business.BusinessObject')]),
                   ('Business services', [_T('business.BusinessService')]),
                   ('Requirements', [_T('business.BusinessRequirement')])],
        'not_in': 'Not in the capability map',
    },
    _L('application'): {   # the application structure (ArchiMate Application Structure viewpoint; TOGAF)
        'nest': [(_T('application.SolutionBuildingBlock'), 'composition', _T('application.SolutionBuildingBlock')), (_T('application.SolutionBuildingBlock'), 'aggregation', _T('application.ApplicationComponent')),
                 (_T('application.ApplicationComponent'), 'composition', _T('application.ApplicationComponent')), (_T('application.ApplicationComponent'), 'aggregation', _T('application.ApplicationComponent')),
                 (_T('application.ApplicationComponent'), 'composition', _T('application.ApplicationInterface')), (_T('application.ApplicationComponent'), 'assignment', _T('application.ApplicationFunction')),
                 (_T('application.ApplicationComponent'), 'realization', _T('application.ApplicationService')), (_T('application.ApplicationFunction'), 'composition', _T('application.ApplicationFunction')),
                 (_T('application.ApplicationFunction'), 'realization', _T('application.ApplicationService')),
                 (_T('application.ApplicationInterface'), 'composition', _T('application.APIOperation')), (_T('application.ApplicationComponent'), 'composition', _T('application.APIOperation')),
                 (_T('application.DataEntity'), 'composition', _T('application.DataEntity')), (_T('application.DataEntity'), 'aggregation', _T('application.DataEntity'))],
        'containers': [_T('application.SolutionBuildingBlock'), _T('application.ApplicationComponent'), _T('application.ApplicationInterface'), _T('application.ApplicationFunction')],
        'always': [_T('application.SolutionBuildingBlock')],
        'kinds': {_T('application.SolutionBuildingBlock'): 'Solution building block', _T('application.ApplicationComponent'): 'Application', _T('application.ApplicationInterface'): 'Interface',
                  _T('application.ApplicationFunction'): 'Function'},
        'groups': [('Data entities', [_T('application.DataEntity')]), ('Events', [_T('application.Event')]),
                   ('Applications', [_T('application.ApplicationComponent')]), ('Services', [_T('application.ApplicationService')]), ('Interfaces', [_T('application.ApplicationInterface')]),
                   ('Functions', [_T('application.ApplicationFunction')])],
        'not_in': 'Not in the application structure',
        'skip': [_T('application.DataAttribute')],   # metamodel 0.15.0 (TL-03): a data entity's fields are not shapes — documents and the workbench show them with their entity
    },
}


class ContainmentError(ValueError):
    pass


def layout(doc, layer, mm=None):
    """The containment layout of one layer's document — JSON-ready, coordinates as fractions of the plate (as sdem/zone_layout.py)."""
    from .metamodel import Metamodel
    mm = mm or Metamodel.load()
    if layer == _L('technology'):
        from .zone_layout import layout as zl
        return zl(doc, mm)
    H = HIERARCHY.get(layer)
    if not H: raise ContainmentError(f'layer {layer}: no containment hierarchy for this layer')
    recs = {i['id']: i for i in doc.get('instances', []) if not any(mm.is_a(i['type'], t) for t in H.get('skip', ()))}
    typ = {x: r['type'] for x, r in recs.items()}
    is_ = lambda x, t: x in typ and mm.is_a(typ[x], t)
    # the primary parent of each record: the first nesting row (in order) that links a parent to it (C3)
    parent, used = {}, set()
    # a row (parent type, kind, child type[, 'up']): 'up' when the child is the link's SOURCE — a process realises the capability it sits in
    for row in H['nest']:
        pt, kind, ct = row[:3]; up = len(row) > 3 and row[3] == 'up'
        cands = {}
        for r in doc.get('relationships', []):
            a, b = (r['target'], r['source']) if up else (r['source'], r['target'])   # a: the parent, b: the child
            if r['kind'] == kind and is_(a, pt) and is_(b, ct) and b not in parent and a != b:
                cands.setdefault(b, []).append((a, (r['source'], r['target'])))
        for b, opts in cands.items():   # two owners by the same row: the most specific one (the deepest in its own hierarchy)
            def depth(x, seen=()):
                return 0 if x not in parent or x in seen else 1 + depth(parent[x], seen + (x,))
            a, link = max(opts, key=lambda o: (depth(o[0]), o[0]))
            parent[b] = a; used.add(link)
    owners = set(parent.values())   # a region: a record of a listed container type itself, or a record that does hold others (an activity is a kind of process, but a region only if it has parts)
    always = H.get('always', H['containers'])   # A1, A2: a capability or service domain is a region even when empty (an empty one is a gap worth seeing); A3: only when it holds something
    containers = {x for x in recs if typ[x] in always or (x in owners and any(is_(x, t) for t in H['containers']))}
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
    # C8 (the owner's screenshots of v2, 2026-11-16: shapes on top of each other, a region's record over its heading): sized from the inside out.
    # Each region needs room for its own shapes on a grid of at least CW x CH (one shape and its label), a heading line, and — when the region is
    # a record — that record's own row under the heading; regions are packed in rows, then stretched to fill the plate. When the plate is too small
    # at full size, everything is scaled by `fit` (< 1) and the viewer draws the shapes that much smaller, so nothing overlaps.
    CW, CH, LBL, PAD, GAP, CHAR = 0.09, 0.06, 0.035, 0.01, 0.012, 0.0034
    def label(z):
        if z.startswith('G:'): return z[2:]
        x = z[2:]; return f"{H['kinds'].get(typ.get(x), typ.get(x, '').split('.')[-1])} · {recs[x].get('name', x)}"
    def head(z):   # (height, width) of the band above a region's contents: its heading, and beside it (right) the region's own record
        lw = min(0.26, len(label(z)) * CHAR + 0.02)
        return (CH, lw + CW) if z.startswith('R:') else (LBL, lw)
    def block(n, ratio=1.6):   # (cols, rows) of a grid of n shapes, a little wider than tall
        if not n: return 0, 0
        cols = max(1, min(n, round((n * ratio * CH / CW) ** 0.5))); return cols, -(-n // cols)
    def shelves(items, gap=GAP, square=False):   # items: (key, w, h) — rows of items, the tightest of several row widths
        if not items: return [], 0, 0
        def rows_for(target):
            rows, cur, cw = [], [], 0
            for it in sorted(items, key=lambda t: (-t[2], t[0])):
                if cur and cw + gap + it[1] > target + 1e-9: rows.append(cur); cur, cw = [], 0
                cw += (gap if cur else 0) + it[1]; cur.append(it)
            if cur: rows.append(cur)
            W = max(sum(w for _, w, _ in r) + gap * (len(r) - 1) for r in rows); Hh = sum(max(h for _, _, h in r) for r in rows) + gap * (len(rows) - 1)
            return rows, W, Hh
        lo, hi = max(w for _, w, _ in items), sum(w for _, w, _ in items) + gap * (len(items) - 1)
        tries = [rows_for(lo + (hi - lo) * i / 24) for i in range(25)]
        score = (lambda t: (max(t[1], t[2]), t[1] * t[2])) if square else (lambda t: (t[1] * t[2] + 0.15 * max(t[1], t[2]) ** 2, t[1]))
        return min(tries, key=score)
    need = {}
    def size(z):
        if z in need: return need[z]
        mine, ks = own.get(z, []), kids.get(z, [])
        c, r_ = block(len(mine))
        items = ([('own', c * CW, r_ * CH)] if mine else []) + [(k, *size(k)) for k in ks]
        rows, w, h = shelves(items)
        hh, hw = head(z)
        need[z] = (max(w, hw) + 2 * PAD, hh + h + PAD + (0 if items else 0.01)); need[z + '#rows'] = rows
        return need[z]
    def fill(rows, x0, y0, x1, y1, gap):   # lay rows out in [x0,x1]×[y0,y1], sharing the spare room in proportion
        if not rows: return []
        hs = [max(h for _, _, h in r) for r in rows]; sy = ((y1 - y0) - gap * (len(rows) - 1)) / (sum(hs) or 1)
        out, y = [], y0
        for r, h in zip(rows, hs):
            ws = [w for _, w, _ in r]; sx = ((x1 - x0) - gap * (len(r) - 1)) / (sum(ws) or 1); x = x0
            for (k, w, _), ww in zip(r, ws):
                out.append((k, (x, y, x + ww * sx, y + h * sy))); x += ww * sx + gap
            y += h * sy + gap
        return out
    def grid(xs, x0, y0, x1, y1):
        n = len(xs)
        if not n: return
        w, h = max(x1 - x0, 1e-6), max(y1 - y0, 1e-6)
        ok = [c for c in range(1, n + 1) if w / c >= CW - 1e-9 and h / -(-n // c) >= CH - 1e-9] or [max(1, min(n, int(w / CW + 1e-9)))]
        cols = min(ok, key=lambda c: abs((w / c) / (h / -(-n // c)) - CW / CH)); rows = -(-n // cols)   # cells at least CW x CH, shaped like one
        for i, x in enumerate(xs):
            c, r_ = i % cols, i // cols
            pos[x] = (x0 + w * (c + 0.5) / cols, y0 + h * (r_ + 0.5) / rows)
    def place(z, x0, y0, x1, y1, lv):
        rects[z] = (x0, y0, x1, y1); level[z] = lv
        hh, _ = head(z)
        if z.startswith('R:'): pos[z[2:]] = (x1 - PAD - CW / 2, y0 + CH / 2)   # the container's own record: right of its heading, which the region is wide enough to clear — lines to it end on it
        for it, (a0, b0, a1, b1) in fill(need[z + '#rows'], x0 + PAD, y0 + hh, x1 - PAD, y1 - PAD, GAP):
            if it == 'own': grid(own.get(z, []), a0, b0, a1, b1)
            else: part_of[it] = z; place(it, a0, b0, a1, b1, lv + 1)
    strip = None
    for t in tops: size(t)
    lc, lr = block(len(lone), 6)
    rows, W, Hh = shelves([(t, *need[t]) for t in tops], 2 * GAP, square=True)
    Hl = (lr * CH + 0.04) if lone else 0
    fit = min(1.0, 1 / max(W, 1e-6), 1 / max(Hh + Hl, 1e-6))   # 1: everything fits at full size
    cw_, ch_ = 1 / fit, 1 / fit   # the plate, in full-size units
    y_end = ch_ - Hl
    for z, (a0, b0, a1, b1) in fill(rows, 0.0, 0.0, cw_, y_end - (0.01 if lone else 0), 2 * GAP):
        place(z, a0, b0, a1, b1, 0)
    if lone:
        grid(lone, 0.02, y_end + 0.03, cw_ - 0.02, ch_ - 0.01)
    pos = {k: (x * fit, y * fit) for k, (x, y) in pos.items()}
    rects = {k: tuple(v * fit for v in q) for k, q in rects.items()}
    if lone:
        strip = {'label': H['not_in'], 'not_in_a_zone': lone, 'rect': [0.0, round(y_end * fit + 0.005, 4), 1.0, 1.0]}
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
        while x and not is_(x, _T('bian.ServiceDomain')): x = parent.get(x)
        return x
    conns, seen = [], set()
    for sc in [x for x in recs if layer == _L('bian') and is_(x, _T('bian.BusinessScenario'))]:
        sds = sorted({domain(r['target']) for r in doc.get('relationships', []) if r['source'] == sc and r['kind'] == 'aggregation'} - {None})
        for i, a in enumerate(sds):
            for b in sds[i + 1:]:
                if (a, b) not in seen: seen.add((a, b)); conns.append({'from': R(a), 'to': R(b), 'rule': 'derived (potential)', 'via': sc})
    return {'viewpoint': 'containment', 'layer': layer, 'model_id': doc.get('model_id'), 'zones': zones, 'runs_on': [],
            'not_in_a_zone': strip['rect'] if strip else None, 'strip': strip, 'shapes': sorted(shapes, key=lambda s: s['id']), 'links': links,
            'connections': conns, 'left_out': [], 'fit': round(fit, 4)}


FILES = {_L('business'): 'a1-business.json', _L('bian'): 'a2-service-domain.json', _L('application'): 'a3-application.json', _L('technology'): 'a4-technology.json'}


def load(workspace, layer, environment='production'):
    f = Path(workspace) / FILES.get(layer, '')
    if layer not in FILES or not f.exists(): raise ContainmentError(f'{workspace}: no {FILES.get(layer, layer)} — nothing to lay out')
    if layer == _L('technology'):
        from .zone_layout import load as zl
        return zl(workspace, environment)
    return layout(_jload(f), layer)


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
    print(f"{a.layer} drawn {'by network zone' if a.layer == _L('technology') else 'by what owns what'} — {len(lay['zones'])} region(s), {len(lay['shapes'])} record(s)")
    for z in lay['zones']:
        held = [s['id'] for s in lay['shapes'] if s['zone'] == z['id'] and s['id'] != (z.get('record') or '')]
        print(f"{'  ' * (z['level'] or 0)}{z['label']}" + (f"  — {', '.join(held)}" if held else ''))
    for c in lay['connections']: print(f"  {c['from'][2:]} ↔ {c['to'][2:]}  ({c['rule']}{', via ' + c['via'] if c.get('via') else ''})")
    if lay['strip'] and lay['strip'].get('not_in_a_zone'): print(f"{lay['strip']['label']}: {', '.join(lay['strip']['not_in_a_zone'])}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
