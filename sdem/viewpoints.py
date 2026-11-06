"""`sdem diagram` — ArchiMate viewpoint diagrams of a workspace, from SDEM's templates (docs/design/sdem-diagram-spec.md, DG-01…DG-14).

The templates (`viewpoints.json`) are data: which metamodel types, in which rows, what is drawn inside what, which stored links are
drawn. The layout is computed here, deterministically (DG-05); the SVG carries its own styles and loads nothing (DG-06). Only records
and stored links are drawn — links inside a layer, and approved connections between layers (DG-03); what has no link is said (DG-04).
"""
import argparse, hashlib, html, json, sys
from pathlib import Path

TEMPLATES_FILE = Path(__file__).with_name('viewpoints.json')
FILES = {'A1': 'a1-business.json', 'A2': 'a2-service-domain.json', 'A3': 'a3-application.json', 'A4': 'a4-technology.json'}
NEST = ('composition', 'aggregation')
LEAF_W, LEAF_H, PAD, GAP, TITLE, CH, LEFT, MAXROW = 172, 58, 14, 16, 34, 96, 150, 4
LAYER_CLASS = {'A1': 'bus', 'A2': 'bian', 'A3': 'app', 'A4': 'tec'}
e = html.escape


def templates():
    return json.loads(TEMPLATES_FILE.read_text(encoding='utf-8'))


def template(tid):
    t = next((t for t in templates()['templates'] if t['id'] == tid), None)
    if not t: raise ValueError(f"{tid}: no such diagram template — one of {', '.join(x['id'] for x in templates()['templates'])}")
    return t


# ---------- the workspace, read once ----------
class Data:
    def __init__(self, ws):
        self.ws = Path(ws); self.rec, self.rels, self.present = {}, [], []
        for l, f in FILES.items():
            p = self.ws / f
            if not p.exists(): continue
            self.present.append(l)
            d = json.loads(p.read_text(encoding='utf-8'))
            for i in d.get('instances', []):
                self.rec[i['id']] = {**i, 'layer': l, 't': i['type']}
            self.rels += d.get('relationships', [])
        self.rels = [r for r in self.rels if r.get('source') in self.rec and r.get('target') in self.rec]
        reg = self.ws / 'mappings.json'
        maps = json.loads(reg.read_text(encoding='utf-8')).get('mappings', []) if reg.exists() else []
        self.maps = [m for m in maps if m.get('status') == 'approved' and m['source']['id'] in self.rec and m['target']['id'] in self.rec]
        self.children = {}
        for r in self.rels:
            if r['kind'] in NEST: self.children.setdefault(r['source'], []).append(r['target'])
        self.parent = {}
        for r in sorted((r for r in self.rels if r['kind'] in NEST), key=lambda r: r['kind'] != 'composition'):   # composition owns the part
            self.parent.setdefault(r['target'], r['source'])


# ---------- layout ----------
def _node(D, i, nest, keep):
    kids = [_node(D, c, nest, keep) for c in D.children.get(i, []) if D.rec[c]['t'] in nest and D.parent.get(c) == i and _has(D, c, keep)] if nest else []
    n = {'id': i, 'r': D.rec[i], 'kids': kids}
    if kids:
        rows = [kids[k:k + MAXROW] for k in range(0, len(kids), MAXROW)]
        n['w'] = PAD * 2 + max(sum(k['w'] for k in r) + GAP * (len(r) - 1) for r in rows)
        n['h'] = TITLE + sum(max(k['h'] for k in r) for r in rows) + GAP * (len(rows) - 1) + PAD
    else:
        n['w'], n['h'] = LEAF_W, LEAF_H
    return n


def _has(D, i, keep):
    return keep is None or i in keep or any(_has(D, c, keep) for c in D.children.get(i, []) if D.parent.get(c) == i)


def _place(n, x, y):
    n['x'], n['y'] = x, y
    cy = y + TITLE
    for r in [n['kids'][k:k + MAXROW] for k in range(0, len(n['kids']), MAXROW)]:
        cx = x + PAD
        for k in r:
            _place(k, cx, cy); cx += k['w'] + GAP
        cy += max(k['h'] for k in r) + GAP


def _walk(n):
    yield n
    for k in n['kids']: yield from _walk(k)


def _links(D, T, notation):
    """(source, target, style, ref) for every stored link the template draws."""
    rel = T['links'].get('relationships')
    out = [(m['source']['id'], m['target']['id'], notation['relationships'].get(m['relationship'], {'line': 'association', 'arrow': None, 'words': m['relationship'].lower()}), m['mapping_id'])
           for m in D.maps if rel is None or m['relationship'] in rel]
    if T['links'].get('inside_layers'):
        out += [(r['source'], r['target'], notation['kinds'][r['kind']], r['kind']) for r in D.rels if r['kind'] in notation['kinds']]
    return out


def _focus_set(D, fid):
    """DG-08: the element, what it contains, what it is inside, and what is linked to any of them (and their containers)."""
    if fid not in D.rec: raise ValueError(f'{fid}: no such record in {D.ws}')
    core, todo = {fid}, [fid]
    while todo:
        i = todo.pop()
        for c in D.children.get(i, []):
            if D.parent.get(c) == i and c not in core: core.add(c); todo.append(c)
    pairs = [(r['source'], r['target']) for r in D.rels] + [(m['source']['id'], m['target']['id']) for m in D.maps]
    near = {o for s, t in pairs for a, o in ((s, t), (t, s)) if a in core}
    keep = core | near
    for i in list(keep):
        while i in D.parent: i = D.parent[i]; keep.add(i)
    return keep


def build(D, tid, focus=None):
    """The diagram for one template: {'template', 'svg', 'notes', 'elements', 'lines', 'missing_layers'} (DG-01…DG-12)."""
    T, nt = template(tid), templates()['notation']
    keep = _focus_set(D, focus) if focus else None
    rows, drawn, missing = [], {}, []
    for row in T['rows']:
        layer, groups = row['layer'], row['groups']
        if layer not in D.present:
            if layer not in missing: missing.append(layer)
            continue
        conn = row.get('connected_to')
        rel = T['links'].get('relationships')
        items = []
        for g in groups:
            nest = g.get('contains', [])
            for i, r in D.rec.items():
                if r['layer'] != layer or r['t'] != g['type'] or not _has(D, i, keep): continue
                p = D.parent.get(i)
                if p and any(D.rec[p]['t'] == h['type'] and g['type'] in h.get('contains', []) for h in groups): continue   # drawn inside its whole
                if conn and not any(i in (m['source']['id'], m['target']['id']) and {D.rec[m['source']['id']]['layer'], D.rec[m['target']['id']]['layer']} == {layer, conn}
                                    and (rel is None or m['relationship'] in rel) for m in D.maps): continue
                items.append(_node(D, i, nest, keep))
        rows.append((layer, row.get('label', ''), items))
    # order each row by where its linked shapes sit in the rows above (DG-10)
    pairs = [(m['source']['id'], m['target']['id']) for m in D.maps] + [(r['source'], r['target']) for r in D.rels if r['kind'] not in NEST]
    pos = {}
    for bi, (layer, label, items) in enumerate(rows):
        if bi and not T.get('keep_order'):
            def bary(n):
                mine = {d['id'] for d in _walk(n)}
                xs = [pos[o] for a, b in pairs for me, o in ((a, b), (b, a)) if me in mine and o in pos]
                return (sum(xs) / len(xs) if xs else 1e9)
            items.sort(key=bary)
        for k, n in enumerate(items):
            for j, d in enumerate(_walk(n)): pos[d['id']] = k * 1000 + j
    y, bands = 70, []
    for layer, label, items in rows:
        x, hmax = LEFT, max([n['h'] for n in items] or [LEAF_H])
        for n in items:
            _place(n, x, y + (hmax - n['h'])); x += n['w'] + 30
            for d in _walk(n): drawn[d['id']] = d
        bands.append((layer, label, y - 22, hmax + 44))
        y += hmax + CH
    W = max([d['x'] + d['w'] for d in drawn.values()] + [700]) + 40
    H = max(y - CH + 50, 160)
    edges = _route(D, T, nt, drawn)
    uid = hashlib.sha1(f'{tid}|{focus}'.encode()).hexdigest()[:6]
    svg = _svg(D, T, drawn, edges, bands, W, H, uid)
    notes = []
    for l in missing: notes.append(f'The workspace has no {l} dataset ({FILES[l]}), so its part of this view is empty.')
    ns = T.get('note_no_sequence')
    if ns and any(r['t'] == ns for r in D.rec.values() if r['id'] in drawn) and not any(r['kind'] == 'triggering' and D.rec[r['source']]['t'] == ns for r in D.rels):
        notes.append('No sequence is recorded between the activities (no triggering links), so they are drawn side by side without arrows — add the links and the flow appears.')
    linked = {x['s'] for x in edges} | {x['t'] for x in edges}
    def touched(d): return d['id'] in linked or any(touched(k) for k in d['kids'])
    dpar = {k['id']: d['id'] for d in drawn.values() for k in d['kids']}
    lonely = [d['r']['name'] for d in drawn.values() if not touched(d) and d['id'] not in dpar]
    if lonely and len(drawn) > 1: notes.append(f'{len(lonely)} element(s) have no stored link to anything else in this view: ' + ', '.join(lonely) + '.')
    if not drawn: notes.append('Nothing to draw: the workspace has no records of the types this view shows.')
    return {'template': tid, 'code': T['code'], 'name': T['name'], 'viewpoint': T['viewpoint'], 'layer': T['layer'], 'focus': focus,
            'svg': svg, 'notes': notes, 'missing_layers': missing, 'elements': list(drawn),
            'lines': [{'source': x['s'], 'target': x['t'], 'line': x['style'], 'label': x['label'], 'stands_for': x['refs']} for x in edges]}


def _route(D, T, nt, drawn):
    dpar = {k['id']: d['id'] for d in drawn.values() for k in d['kids']}
    def inside(c, p):
        while c in dpar:
            c = dpar[c]
            if c == p: return True
        return False
    def visible(i):
        while i and i not in drawn: i = D.parent.get(i)
        return i
    lvl = T.get('lines_at', {})
    def lift(i):
        if D.rec[i]['t'] in lvl:
            j = i
            while j and D.rec[j]['t'] != lvl[D.rec[i]['t']]: j = D.parent.get(j)
            return j or i
        return i
    agg, order = {}, []
    for s, t, st, ref in _links(D, T, nt):
        if st['line'] in NEST and inside(t, s): continue                       # the part is drawn inside its whole (DG-09)
        vs, vt = visible(lift(s)), visible(lift(t))
        if not vs or not vt or vs == vt or inside(vs, vt) and st['line'] in NEST: continue
        if not T['links'].get('inside_layers') and D.rec[vs]['layer'] == D.rec[vt]['layer']: continue
        k = (vs, vt, st['line'], st['arrow'], st['words'])
        if k not in agg: agg[k] = []; order.append(k)
        agg[k].append(ref)
    keys = sorted(order, key=lambda k: (drawn[k[0]]['y'], drawn[k[0]]['x'], drawn[k[1]]['x'], k[2], k[4]))
    outn, inn, oi, ii, lane, edges = {}, {}, {}, {}, {}, []
    for k in keys: outn[k[0]] = outn.get(k[0], 0) + 1; inn[k[1]] = inn.get(k[1], 0) + 1
    for k in keys:
        s, t = drawn[k[0]], drawn[k[1]]
        oi[k[0]] = oi.get(k[0], 0) + 1; ii[k[1]] = ii.get(k[1], 0) + 1
        up, lo = (s, t) if s['y'] + s['h'] <= t['y'] else (t, s) if t['y'] + t['h'] <= s['y'] else (None, None)
        if up is None:
            a, b = (s, t) if s['x'] < t['x'] else (t, s)
            y0 = a['y'] + a['h'] / 2
            between = [d for d in drawn.values() if d is not a and d is not b and d['x'] >= a['x'] + a['w'] - 1 and d['x'] + d['w'] <= b['x'] + 1 and d['y'] < y0 < d['y'] + d['h']]
            if between or inside(a['id'], b['id']) or inside(b['id'], a['id']) or b['x'] < a['x'] + a['w']:
                key = ('u', round(y0)); lane[key] = lane.get(key, 0) + 1
                yb = max(d['y'] + d['h'] for d in [a, b] + between) + 16 + (lane[key] % 4) * 9
                pts = [(a['x'] + a['w'] / 2, a['y'] + a['h']), (a['x'] + a['w'] / 2, yb), (b['x'] + b['w'] / 2, yb), (b['x'] + b['w'] / 2, b['y'] + b['h'])]
                ly = yb
            else:
                pts = [(a['x'] + a['w'], y0), (b['x'], b['y'] + b['h'] / 2)]; ly = y0
            if a is not s: pts.reverse()
        else:
            ux = up['x'] + up['w'] * ((oi[k[0]] if up is s else ii[k[1]]) / ((outn[k[0]] if up is s else inn[k[1]]) + 1))
            lx = lo['x'] + lo['w'] * ((ii[k[1]] if lo is t else oi[k[0]]) / ((inn[k[1]] if lo is t else outn[k[0]]) + 1))
            key = round(lo['y']); lane[key] = lane.get(key, 0) + 1
            cy = max(lo['y'] - 26 - (lane[key] % 5) * 11, up['y'] + up['h'] + 12)
            pts = [(ux, up['y'] + up['h']), (ux, cy), (lx, cy), (lx, lo['y'])]
            if up is not s: pts.reverse()                                      # points run from the stored source to the stored target
            ly = cy
        if k[3] == 'source': pts = pts[::-1]                                   # A REALIZED_BY B: B realizes A, the triangle on A
        n = len(agg[k])
        edges.append({'s': k[0], 't': k[1], 'pts': pts, 'style': k[2], 'label': k[4] + (f' ×{n}' if n > 1 else ''), 'refs': agg[k], 'ly': ly})
    return edges


# ---------- drawing ----------
def _wrap(s, n=20):
    lines, cur = [], ''
    for w in str(s).split():
        if len(cur) + len(w) + 1 > n and cur: lines.append(cur); cur = w
        else: cur = (cur + ' ' + w).strip()
    lines.append(cur)
    if len(lines) > 2: lines = [lines[0], (lines[1] + ' ' + ' '.join(lines[2:]))[:n - 1] + '…']
    return lines


def _icon(t, x, y):
    t = t.split('.', 1)[-1]
    if t in ('BusinessProcess', 'BusinessActivity'): return f'<path class="dv-ic" d="M{x-18} {y+8}h10v-4l7 7-7 7v-4h-10z"/>'
    if t == 'BusinessCapability': return f'<path class="dv-ic" d="M{x-20} {y+18}h6v-5h6v-5h6v15h-18z"/>'
    if t == 'BusinessRole': return f'<path class="dv-ic" d="M{x-16} {y+6}h8a5 5 0 0 1 0 10h-8a5 5 0 0 1 0-10z M{x-8} {y+6}a5 5 0 0 1 0 10"/>'
    if t == 'BusinessActor': return f'<circle class="dv-ic" cx="{x-10}" cy="{y+7}" r="3"/><path class="dv-ic" d="M{x-10} {y+10}v6 M{x-14} {y+12}h8 M{x-10} {y+16}l-3 4 M{x-10} {y+16}l3 4"/>'
    if t in ('BusinessService', 'ApplicationService', 'TechnologyService'): return f'<rect class="dv-ic" x="{x-21}" y="{y+7}" width="15" height="9" rx="4.5"/>'
    if t in ('ApplicationComponent', 'SolutionBuildingBlock'): return f'<path class="dv-ic" d="M{x-16} {y+5}h12v14h-12z M{x-20} {y+8}h7v3h-7z M{x-20} {y+13}h7v3h-7z"/>'
    if t in ('ApplicationInterface', 'TechnologyInterface', 'SemanticAPI'): return f'<path class="dv-ic" d="M{x-20} {y+12}h7"/><circle class="dv-ic" cx="{x-9}" cy="{y+12}" r="4.5"/>'
    if t == 'ApplicationFunction': return f'<path class="dv-ic" d="M{x-18} {y+18}v-8l6-5 6 5v8l-6-4z"/>'
    if t == 'SystemSoftware': return f'<circle class="dv-ic" cx="{x-10}" cy="{y+13}" r="6"/><path class="dv-ic" d="M{x-14} {y+6}a7 7 0 0 1 9 0"/>'
    if t == 'Deployment': return f'<path class="dv-ic" d="M{x-19} {y+9}l9-4 9 4-9 4z M{x-19} {y+9}v8l9 4v-8 M{x-1} {y+9}v8l-9 4"/>'
    if t == 'Device': return f'<rect class="dv-ic" x="{x-20}" y="{y+5}" width="14" height="9" rx="2"/><path class="dv-ic" d="M{x-22} {y+17}h18"/>'
    if t in ('CommunicationNetwork', 'Path'): return f'<path class="dv-ic" d="M{x-20} {y+15}l5-6h8l-5 6z"/>'
    if t == 'Artifact': return f'<path class="dv-ic" d="M{x-17} {y+4}h7l4 4v11h-11z M{x-10} {y+4}v4h4"/>'
    if t == 'ServiceDomain': return f'<text class="dv-tag" x="{x-8}" y="{y+16}" text-anchor="end">SD</text>'
    if t == 'BusinessScenario': return f'<path class="dv-ic" d="M{x-20} {y+12}h14 M{x-10} {y+7}l5 5-5 5"/>'
    if t == 'Event': return f'<path class="dv-ic" d="M{x-21} {y+7}h11a5 5 0 0 1 0 10h-11l4-5z"/>'
    return ''


def _shape(n, D):
    r = n['r']; x, y, w, h, t = n['x'], n['y'], n['w'], n['h'], r['t'].split('.', 1)[-1]
    cls = LAYER_CLASS[r['layer']]
    tip = f'<title>{e(r["name"])} — {e(r["type"])} · {e(n["id"])}</title>'
    head = f'<g class="dv-node" data-id="{e(n["id"])}" tabindex="0" role="link" aria-label="{e(r["name"])}">'
    if n['kids']:
        if t in ('DeploymentEnvironment', 'Node'):
            body = (f'<path class="dv-box dv-cont {cls}" d="M{x} {y+10}l10-10h{w-10}v{h-10}l-10 10h-{w-10}z"/>'
                    f'<path class="dv-edge3d {cls}" d="M{x} {y+10}h{w-10}l10-10 M{x+w-10} {y+10}v{h-10}"/>')
        else:
            body = f'<rect class="dv-box dv-cont {cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="16"/>'
        title = r['name'] if len(r['name']) * 7.2 < w - 50 else r['name'][:int((w - 50) / 7.2)] + '…'
        return head + body + f'<text class="dv-ctitle" x="{x + w/2}" y="{y + 21}" text-anchor="middle">{e(title)}</text>' + _icon(t, x + w - 6, y + 6) + tip + '</g>'
    if t in ('ValueStream', 'ValueStreamStage'):
        body = f'<path class="dv-box {cls}" d="M{x} {y}h{w-16}l16 {h/2}-16 {h/2}h-{w-16}l14-{h/2}z"/>'
    elif t in ('ApplicationService', 'BusinessService', 'TechnologyService'):
        body = f'<rect class="dv-box {cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="{h/2}"/>'
    elif t in ('BusinessObject', 'DataEntity', 'BusinessObjectAttribute', 'ControlRecord'):
        body = f'<rect class="dv-box {cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="6"/><path class="dv-band {cls}" d="M{x} {y+13}h{w}"/>'
    elif t in ('SystemSoftware', 'Node', 'DeploymentEnvironment', 'Device'):
        body = f'<path class="dv-box {cls}" d="M{x} {y+9}l9-9h{w-9}v{h-9}l-9 9h-{w-9}z"/><path class="dv-edge3d {cls}" d="M{x} {y+9}h{w-9}l9-9 M{x+w-9} {y+9}v{h-9}"/>'
    else:
        body = f'<rect class="dv-box {cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="10"/>'
    lines = _wrap(r['name'])
    ty = y + h / 2 - (len(lines) - 1) * 8 + 1
    txt = ''.join(f'<text class="dv-name" x="{x + w/2 - 9}" y="{ty + i*16}" text-anchor="middle">{e(s)}</text>' for i, s in enumerate(lines))
    txt += f'<text class="dv-id" x="{x + w/2 - 4}" y="{y + h - 7}" text-anchor="middle">{e(n["id"])}</text>'
    return head + body + _icon(t, x + w - 4, y + 4) + txt + tip + '</g>'


CSS = """.sdv{--dv-bg:#fff;--dv-card:#fff;--dv-text:#1f2933;--dv-muted:#5f6c7b;--dv-line:#4b5563;--dv-pill:#1f2933;--dv-pilltext:#fff;
--dv-bus:#b38f00;--dv-bus-f:#fff9db;--dv-bian:#d9822b;--dv-bian-f:#fff1e3;--dv-app:#1c8fc0;--dv-app-f:#e6f6fd;--dv-tec:#2f9e63;--dv-tec-f:#e8f7ee;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
@media (prefers-color-scheme:dark){.sdv{--dv-bg:#232a3b;--dv-card:#2c3348;--dv-text:#e7ebf3;--dv-muted:#9aa4b8;--dv-line:#c9d1e3;--dv-pill:#f4f6fb;--dv-pilltext:#1d2232;
--dv-bus:#f2c94c;--dv-bus-f:rgba(242,201,76,.10);--dv-bian:#f2994a;--dv-bian-f:rgba(242,153,74,.10);--dv-app:#56ccf2;--dv-app-f:rgba(86,204,242,.10);--dv-tec:#6fcf97;--dv-tec-f:rgba(111,207,151,.10)}}
.sdv .dv-bg{fill:var(--dv-bg)}
.sdv .dv-lane{stroke-width:1;stroke-dasharray:2 6}.sdv .dv-lane.bus{fill:var(--dv-bus-f);stroke:var(--dv-bus)}.sdv .dv-lane.bian{fill:var(--dv-bian-f);stroke:var(--dv-bian)}.sdv .dv-lane.app{fill:var(--dv-app-f);stroke:var(--dv-app)}.sdv .dv-lane.tec{fill:var(--dv-tec-f);stroke:var(--dv-tec)}
.sdv .dv-lanelabel{font-weight:700;font-size:13px;letter-spacing:.04em;text-transform:uppercase}.sdv .dv-lanelabel.bus{fill:var(--dv-bus)}.sdv .dv-lanelabel.bian{fill:var(--dv-bian)}.sdv .dv-lanelabel.app{fill:var(--dv-app)}.sdv .dv-lanelabel.tec{fill:var(--dv-tec)}
.sdv .dv-box{fill:var(--dv-card);stroke-width:1.6}.sdv .dv-box.dv-cont{stroke-width:2.6}
.sdv .dv-box.bus{stroke:var(--dv-bus)}.sdv .dv-box.bian{stroke:var(--dv-bian)}.sdv .dv-box.app{stroke:var(--dv-app)}.sdv .dv-box.tec{stroke:var(--dv-tec)}
.sdv .dv-cont.bus{fill:var(--dv-bus-f)}.sdv .dv-cont.bian{fill:var(--dv-bian-f)}.sdv .dv-cont.app{fill:var(--dv-app-f)}.sdv .dv-cont.tec{fill:var(--dv-tec-f)}
.sdv .dv-band,.sdv .dv-edge3d{fill:none;stroke-width:1.4}.sdv .dv-band.bus,.sdv .dv-edge3d.bus{stroke:var(--dv-bus)}.sdv .dv-band.bian,.sdv .dv-edge3d.bian{stroke:var(--dv-bian)}.sdv .dv-band.app,.sdv .dv-edge3d.app{stroke:var(--dv-app)}.sdv .dv-band.tec,.sdv .dv-edge3d.tec{stroke:var(--dv-tec)}
.sdv .dv-name{fill:var(--dv-text);font-size:12.5px;font-weight:600}.sdv .dv-id{fill:var(--dv-muted);font-size:9.5px;letter-spacing:.03em}.sdv .dv-ctitle{fill:var(--dv-text);font-size:13px;font-weight:700}
.sdv .dv-ic{fill:none;stroke:var(--dv-muted);stroke-width:1.4}.sdv .dv-tag{fill:var(--dv-bian);font-size:10px;font-weight:700}
.sdv .dv-link path{fill:none;stroke:var(--dv-line);stroke-width:1.4}.sdv .dv-link.dash path{stroke-dasharray:6 4}.sdv .dv-link.dot path{stroke-dasharray:2 3}
.sdv .dv-mk-hollow{fill:var(--dv-card);stroke:var(--dv-line);stroke-width:1.3}.sdv .dv-mk-fill{fill:var(--dv-line)}.sdv .dv-mk-line{fill:none;stroke:var(--dv-line);stroke-width:1.4}
.sdv .dv-pill{fill:var(--dv-pill)}.sdv .dv-plabel{fill:var(--dv-pilltext);font-size:10.5px;font-weight:600}
.sdv .dv-node{cursor:pointer;outline:none}.sdv .dv-node:focus>.dv-box,.sdv .dv-node:hover>.dv-box{stroke-width:3}
.sdv.dv-focus .dv-node,.sdv.dv-focus .dv-link{opacity:.18}.sdv.dv-focus .dv-on{opacity:1}"""

LINE = {'realization': ('tri', 'dash'), 'serving': ('open', ''), 'access': ('small', 'dot'), 'assignment': ('fill', ''), 'triggering': ('fill', ''),
        'flow': ('fill', 'dash'), 'association': (None, ''), 'composition': (None, ''), 'aggregation': (None, ''), 'specialization': ('tri', '')}


def _svg(D, T, drawn, edges, bands, W, H, uid):
    m = lambda k: f'dv{uid}-{k}'
    out = [f'<svg class="sdv" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" width="{W:.0f}" height="{H:.0f}" role="img" aria-label="{e(T["name"])}">',
           f'<style>{CSS}</style><defs>'
           f'<marker id="{m("tri")}" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="12" markerHeight="12" orient="auto-start-reverse"><path d="M1 1L11 6L1 11z" class="dv-mk-hollow"/></marker>'
           f'<marker id="{m("open")}" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="11" markerHeight="11" orient="auto-start-reverse"><path d="M1 1L11 6L1 11" class="dv-mk-line"/></marker>'
           f'<marker id="{m("fill")}" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="11" markerHeight="11" orient="auto-start-reverse"><path d="M1 1L11 6L1 11z" class="dv-mk-fill"/></marker>'
           f'<marker id="{m("dot")}" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="8" markerHeight="8"><circle cx="5" cy="5" r="3.5" class="dv-mk-fill"/></marker>'
           f'<marker id="{m("small")}" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M1 2L11 6L1 10" class="dv-mk-line"/></marker>'
           f'<marker id="{m("dia")}" viewBox="0 0 14 12" refX="1" refY="6" markerWidth="13" markerHeight="11" orient="auto-start-reverse"><path d="M1 6L7 1L13 6L7 11z" class="dv-mk-fill"/></marker>'
           f'<marker id="{m("odia")}" viewBox="0 0 14 12" refX="1" refY="6" markerWidth="13" markerHeight="11" orient="auto-start-reverse"><path d="M1 6L7 1L13 6L7 11z" class="dv-mk-hollow"/></marker>'
           '</defs>', f'<rect class="dv-bg" width="{W:.0f}" height="{H:.0f}" rx="12"/>']
    for layer, label, by, bh in bands:
        if label:
            out.append(f'<rect class="dv-lane {LAYER_CLASS[layer]}" x="12" y="{by}" width="{W-24:.0f}" height="{bh}" rx="18"/>'
                       f'<text class="dv-lanelabel {LAYER_CLASS[layer]}" x="28" y="{by + bh/2 + 5:.0f}">{e(label)}</text>')
    for n in sorted(drawn.values(), key=lambda d: (-(d['w'] * d['h']), d['y'], d['x'])):
        out.append(_shape(n, D))
    pills = []
    for x in edges:
        mk, dash = LINE.get(x['style'], (None, ''))
        d = 'M' + ' L'.join(f'{a:.0f} {b:.0f}' for a, b in x['pts'])
        attrs = f' marker-end="url(#{m(mk)})"' if mk else ''
        if x['style'] == 'assignment': attrs += f' marker-start="url(#{m("dot")})"'
        if x['style'] in NEST: attrs += f' marker-start="url(#{m("dia" if x["style"] == "composition" else "odia")})"'
        p1, p2 = (x['pts'][1], x['pts'][2]) if len(x['pts']) > 2 else (x['pts'][0], x['pts'][1])
        tw, ly = len(x['label']) * 6.2 + 16, x['ly']
        for f in (0.5, 0.3, 0.7, 0.15, 0.85, 0.5):
            mx = p1[0] + (p2[0] - p1[0]) * f
            if not any(abs(mx - px) < (tw + pw) / 2 + 4 and abs(ly - py) < 20 for px, py, pw in pills): break
        else:
            ly += 20
        pills.append((mx, ly, tw))
        out.append(f'<g class="dv-link {dash}" data-s="{e(x["s"])}" data-t="{e(x["t"])}"><path d="{d}"{attrs}/>'
                   f'<rect class="dv-pill" x="{mx - tw/2:.0f}" y="{ly - 9:.0f}" width="{tw:.0f}" height="18" rx="9"/>'
                   f'<text class="dv-plabel" x="{mx:.0f}" y="{ly + 4:.0f}" text-anchor="middle">{e(x["label"])}</text>'
                   f'<title>{e(", ".join(x["refs"]))}</title></g>')
    out.append('</svg>')
    return ''.join(out)


# highlight a shape's lines and neighbours; a host page may also open the record on click
SCRIPT = """function sdemDiagrams(root,open){root.querySelectorAll('svg.sdv').forEach(s=>{const nodes=[...s.querySelectorAll('.dv-node')],links=[...s.querySelectorAll('.dv-link')];
const on=id=>{s.classList.add('dv-focus');nodes.forEach(n=>n.classList.toggle('dv-on',n.dataset.id===id||n.querySelector('[data-id="'+CSS.escape(id)+'"]')!==null));
links.forEach(l=>{const hit=l.dataset.s===id||l.dataset.t===id;l.classList.toggle('dv-on',hit);if(hit)nodes.forEach(n=>{if(n.dataset.id===l.dataset.s||n.dataset.id===l.dataset.t)n.classList.add('dv-on')})})};
const off=()=>s.classList.remove('dv-focus');
nodes.forEach(n=>{n.addEventListener('mouseenter',e=>{e.stopPropagation();on(n.dataset.id)});n.addEventListener('mouseleave',off);n.addEventListener('focus',()=>on(n.dataset.id));n.addEventListener('blur',off);
if(open){n.addEventListener('click',e=>{e.stopPropagation();open(n.dataset.id)});n.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();open(n.dataset.id)}})}})})}"""


def page(d, ws_name):
    notes = ''.join(f'<p class="note">{e(n)}</p>' for n in d['notes'])
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(d["name"])} — {e(ws_name)}</title>'
            '<style>body{margin:0;padding:20px;font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#f5f6f8;color:#1f2933}'
            '@media (prefers-color-scheme:dark){body{background:#1d2232;color:#e7ebf3}}h1{font-size:18px;margin:0 0 4px}.sub{opacity:.7;font-size:13px;margin-bottom:10px}'
            '.note{border-left:3px solid #d9a400;padding:6px 10px;background:rgba(242,201,76,.12);border-radius:4px;font-size:13px}.frame{overflow:auto}</style></head><body>'
            f'<h1>{e(d["code"])} · {e(d["name"])}</h1><div class="sub">{e(ws_name)} · {e(d["viewpoint"])} · {len(d["elements"])} elements · {len(d["lines"])} lines'
            f'{" · focus " + e(d["focus"]) if d["focus"] else ""} · generated by sdem diagram from stored, approved links only</div>{notes}<div class="frame">{d["svg"]}</div>'
            f'<script>{SCRIPT};sdemDiagrams(document)</script></body></html>')


# ---------- DG-02: the templates against the metamodel ----------
def check():
    from .metamodel import Metamodel
    from .validate import load_registry
    mm = Metamodel.load(); tf = templates()
    types = set(mm.entities)
    kinds = {k['kind'] if isinstance(k, dict) else k for k in mm.relationships.get('kinds', [])}
    rels = {r['relationship'] for r in load_registry()['relationships']}
    bad = []
    for k in tf['notation']['kinds']:
        if k not in kinds: bad.append(f'notation: link kind {k} is not in the metamodel')
    for r in tf['notation']['relationships']:
        if r not in rels: bad.append(f'notation: relationship {r} is not in the relationship rules')
    ids = [t['id'] for t in tf['templates']]
    if len(ids) != len(set(ids)): bad.append('two templates share an id')
    for t in tf['templates']:
        if t['layer'] not in (*FILES, 'all'): bad.append(f"{t['id']}: layer {t['layer']}")
        for r in t['links'].get('relationships') or []:
            if r not in rels: bad.append(f"{t['id']}: relationship {r} is not in the relationship rules")
        for x in list(t.get('lines_at', {})) + list(t.get('lines_at', {}).values()) + ([t['note_no_sequence']] if t.get('note_no_sequence') else []):
            if x not in types: bad.append(f"{t['id']}: type {x} is not in the metamodel")
        for row in t['rows']:
            if row['layer'] not in FILES: bad.append(f"{t['id']}: row layer {row['layer']}")
            for g in row['groups']:
                for x in [g['type']] + g.get('contains', []):
                    if x not in types: bad.append(f"{t['id']}: type {x} is not in the metamodel")
                    elif not x.startswith(row['layer'] + '.'): bad.append(f"{t['id']}: type {x} in a {row['layer']} row")
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem diagram', formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description='Draw a workspace in ArchiMate notation from one of SDEM\'s diagram templates — the same views in every workspace: '
                                             'capabilities and value stream, business process, BIAN service domains, application cooperation, technology and '
                                             'deployment, and the layered view. Only records and stored, approved links are drawn; gaps are said. Read-only.',
                                 epilog='Examples:\n  sdem diagram --workspace examples/payment-initiation --template layered -o work/layered.svg\n'
                                        '  sdem diagram --workspace examples/payment-initiation --template process --focus PRC-PAY-01 --format html -o work/process.html\n'
                                        '  sdem diagram --list')
    ap.add_argument('--workspace', metavar='DIR')
    ap.add_argument('--template', default='layered', metavar='ID', help='the template (sdem diagram --list); default layered')
    ap.add_argument('--focus', metavar='ID', help='draw only this record, what it contains and is inside, and what is linked to them')
    ap.add_argument('--format', choices=('svg', 'html', 'json'), default=None, help='default from the -o extension, else svg')
    ap.add_argument('-o', '--out', metavar='FILE', help='write here (default: print)')
    ap.add_argument('--list', action='store_true', help='the templates')
    ap.add_argument('--check', action='store_true', help='check the templates against the metamodel (as sdem model check)')
    ap.add_argument('--json', action='store_true', help='with --list or --check: JSON')
    a = ap.parse_args(argv)
    if a.check or (not a.list and not a.workspace and argv == []):
        bad = check()
        if a.json: print(json.dumps({'templates': len(templates()['templates']), 'problems': bad}, indent=2))
        else: print('\n'.join(f'ERROR: {b}' for b in bad) or f"diagram templates: {len(templates()['templates'])} match the metamodel")
        return 1 if bad else 0
    if a.list:
        rows = [{k: t[k] for k in ('id', 'code', 'name', 'layer', 'viewpoint')} for t in templates()['templates']]
        print(json.dumps(rows, indent=2) if a.json else '\n'.join(f"{r['id']:<13} {r['code']:<6} {r['layer']:<4} {r['name']} ({r['viewpoint']})" for r in rows)); return 0
    if not a.workspace: ap.error('--workspace is needed (or --list / --check)')
    ws = Path(a.workspace)
    D = Data(ws)
    if not D.present: print(f'ERROR: {ws}: not a workspace (no layer datasets)', file=sys.stderr); return 2
    try:
        d = build(D, a.template, a.focus)
    except ValueError as x:
        print(f'ERROR: {x}', file=sys.stderr); return 2
    fmt = a.format or (Path(a.out).suffix.lstrip('.') if a.out and Path(a.out).suffix.lstrip('.') in ('svg', 'html', 'json') else 'svg')
    text = d['svg'] if fmt == 'svg' else page(d, ws.name) if fmt == 'html' else json.dumps({k: v for k, v in d.items() if k != 'svg'}, indent=2, ensure_ascii=False)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True); Path(a.out).write_text(text, encoding='utf-8')
        print(f"wrote {a.out} — {d['code']} {d['name']}: {len(d['elements'])} elements, {len(d['lines'])} lines" + ''.join(f'\n  note: {n}' for n in d['notes']))
    else:
        print(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
