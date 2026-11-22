"""The metamodel's health (docs/design/sdem-metamodel-stability.md, MS-01…MS-08): what is not yet settled, what workspaces actually
use, and whether the core changed only as the stability policy allows.

  sdem model status            every part of SDEM's metamodel that is not fully settled — with its source and what would settle it
  sdem model usage             which types, link types, within-layer kinds and attributes the given workspaces use
  sdem model stability         the core against its last freeze (metamodel/stability.json): what changed, and whether the policy allows it
  sdem model freeze            record the core as it now is — after an approved, versioned change (maintainers)

Read-only except `freeze`. Everything here reads SDEM's own metamodel (never a workspace's profile, unless asked for usage).
"""
from .identity import load as _jload, type_id, T, layer as _L  # DL-11: a design's files read through one boundary (docs/design/sdem-data-layer-spec.md)
import argparse, collections, json, sys
from pathlib import Path

from .paths import DATA_ROOT

MM = DATA_ROOT / 'metamodel'
LINKS = DATA_ROOT / 'schema' / 'relationship-types.json'
STABILITY = MM / 'stability.json'
LEVEL_FILES = ('a1-business.json', 'a2-service-domain.json', 'a3-application.json', 'a4-technology.json')

# MS-02: what would settle each kind of unsettled item — in plain words
SETTLE = {
    'pending_release_validation': 'confirm against the named BIAN release (a licensed or public copy of that release)',
    'proposed_extension': "SDEM's own extension of a standard concept — keep or drop it on evidence of use (sdem model usage) and the owner's decision",
    'sdem_definition_grounded': "SDEM's own definition, grounded in a checked ArchiMate pattern — confirm on real designs that the record it points to is used as defined",
    'sdem_definition': "SDEM's own definition, not a standard's — state the reasoning fully, test it on real designs, and have the owner confirm it",
    'verified_intent_or_target_only': 'the standard states the intent or the target only — confirm the full relationship on real designs',
    'unverified_w135': 'the cited source is login-gated and was not read — verify against its text',
    'unverified_togaf': 'verify against the TOGAF text',
    'sdem_reading': "SDEM's reading of the standard — have a second reviewer confirm it",
    'medium': 'medium confidence — check the public source and record what it says',
    'low': 'low confidence — find a source or mark it as SDEM\'s own choice',
    'open_gap': 'a difference from the high-level specification not yet decided — the owner decides',
}


def _j(p): return _jload(Path(p))


def _entities(): return [e for f in LEVEL_FILES for e in _j(MM / f)['entities']]


def _ref(r):
    r = r or {}
    return ' · '.join(x for x in (r.get('standard'), r.get('release') and f"release {r['release']}", r.get('concept'), r.get('locator')) if x) or '—'


def status():
    """MS-01, MS-02: every unsettled item of SDEM's metamodel — entity types, cross-layer link types, within-layer rules, attributes,
    open gaps — with its source and what would settle it. Summary counts first."""
    items = []
    for e in _entities():
        why = [w for w in (e.get('evidence_status') if e.get('evidence_status') != 'interpreted_from_official_source' else None,
                           e.get('confidence') if e.get('confidence') in ('medium', 'low') else None) if w]
        if why: items.append({'area': 'entity type', 'id': e['type'], 'layer': e['level'], 'status': why, 'source': _ref(e.get('reference')),
                              'settle': [SETTLE.get(w, w) for w in why], 'basis': e.get('confidence_basis', '')})
    for r in _j(LINKS)['relationships']:
        why = [w for w in (r.get('verification') if r.get('verification') not in ('verified', 'verified_against_archi') else None, r.get('confidence') if r.get('confidence') in ('medium', 'low') else None) if w]
        if why: items.append({'area': 'cross-layer link type', 'id': f"{r['source_type']} {r['relationship']} {r['target_type']}", 'layer': r['source_type'][:2] + '→' + r['target_type'][:2],
                              'status': why, 'source': r.get('source_reference', '—'), 'settle': [SETTLE.get(w, w) for w in why], 'basis': r.get('confidence_basis', ''),
                              'authority': r.get('authority')})
    for c in _j(MM / 'level-relationships.json')['constraints']:
        why = [w for w in (c.get('verification') if c.get('verification') not in ('verified', 'verified_against_archi') else None,
                           c.get('confidence') if c.get('confidence') in ('medium', 'low') else None) if w]
        if why: items.append({'area': 'within-layer rule', 'id': f"{c['id']} {c['source_type']} {c['kind']} {c['target_type']}", 'layer': c['level'], 'status': why,
                              'source': c.get('reference_source') or c.get('basis', '—'), 'settle': [SETTLE.get(w, w) for w in why], 'basis': c.get('confidence_basis', '')})
    for a in _j(MM / 'entity-attributes.json')['attributes']:
        if a.get('status') == 'active' and a.get('confidence') in ('medium', 'low'):
            items.append({'area': 'attribute', 'id': f"{a['entity']}.{a['name']}", 'layer': a['entity'][:2], 'status': [a['confidence']], 'source': _ref(a.get('reference')) if isinstance(a.get('reference'), dict) else a.get('source', '—'),
                          'settle': [SETTLE[a['confidence']]], 'basis': a.get('confidence_basis', '')})
    for g in _j(MM / 'metamodel-spec-gaps.json')['gaps']:
        if not str(g.get('status', '')).startswith(('decided', 'built', 'as designed', 'noted')):
            items.append({'area': 'spec gap', 'id': g['id'], 'layer': '—', 'status': ['open_gap'], 'source': g.get('high_level_section', '—'), 'settle': [SETTLE['open_gap']], 'basis': g.get('status', '')})
    totals = {'entity type': len(_entities()), 'cross-layer link type': len(_j(LINKS)['relationships']),   # rows: DEPLOYED_ON has one per target type 'within-layer rule': len(_j(MM / 'level-relationships.json')['constraints']),
              'attribute': sum(1 for a in _j(MM / 'entity-attributes.json')['attributes'] if a.get('status') == 'active'), 'spec gap': len(_j(MM / 'metamodel-spec-gaps.json')['gaps'])}
    summary = {k: {'total': n, 'unsettled': sum(1 for i in items if i['area'] == k)} for k, n in totals.items()}
    by_status = collections.Counter(s for i in items for s in i['status'])
    return {'metamodel_version': _j(MM / 'a1-business.json')['metamodel_version'], 'summary': summary, 'by_status': dict(by_status.most_common()), 'items': items}


# ------------------------------------------------------------------ usage (MS-03)

def usage(workspaces):
    """MS-03: what the given workspaces use — each entity type (records, and through subtypes), each cross-layer link type (approved
    and proposed connections), each within-layer kind, each attribute — and which of SDEM's types and link types no workspace uses,
    the unsettled ones first. Each workspace is read under its own profile."""
    from . import profile as _p
    from .metamodel import Metamodel
    from .layers import layers
    types, links, kinds, attrs, core_used = collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter()
    core = [(r['source_type'], r['relationship'], r['target_type']) for r in _j(LINKS)['relationships']]
    per_ws = []
    for ws in workspaces:
        ws = Path(ws)
        if not (ws / 'mappings.json').exists(): raise ValueError(f'{ws}: not a workspace (no mappings.json)')
        _p.activate_from(ws); mm = Metamodel.load(); n = 0
        for l in layers():
            f = ws / l['file']
            if not f.exists(): continue
            d = _j(f)
            for i in d.get('instances', []):
                if i.get('lifecycle_status') == 'retired': continue
                n += 1
                for t in [i['type']] + mm.ancestors(i['type']): types[type_id(t) or t] += 1   # by id: workspaces in either form count together
                for k in (i.get('attributes') or {}): attrs[f"{i['type']}.{k}"] += 1
            for r in d.get('relationships', []): kinds[f"{l['code']} {r['kind']}"] += 1
        for m in _j(ws / 'mappings.json').get('mappings', []):
            if m.get('status') in ('approved', 'proposed'):
                s, rel, tg = m['source']['type'], m['relationship'], m['target']['type']
                links[f'{s} {rel} {tg}'] += 1
                for cs, cr, ct in core:   # the SDEM link type it is an instance of — by type or subtype
                    if cr == rel and mm.is_a(s, cs) and mm.is_a(tg, ct): core_used[f'{cs} {cr} {ct}'] += 1
        per_ws.append({'workspace': str(ws), 'records': n, 'profile': (_p.record() or {}).get('name')})
    core_types = [e['type'] for e in _entities() if not e.get('abstract')]   # named as the workspaces read them (the last one opened)
    types = collections.Counter({(T(k) if type_id(k) == k else k): v for k, v in types.items()})
    _p.deactivate()
    st = {i['id']: i['status'] for i in status()['items']}
    core_links = [f"{r['source_type']} {r['relationship']} {r['target_type']}" for r in _j(LINKS)['relationships']]
    unused_types = sorted((t for t in core_types if not types[t]), key=lambda t: (t not in st, t))
    unused_links = sorted((cl for cl in core_links if not core_used[cl]), key=lambda c: (c not in st, c))
    return {'workspaces': per_ws, 'entity_types': dict(types.most_common()), 'link_types': dict(links.most_common()), 'within_layer_kinds': dict(kinds.most_common()),
            'attributes': dict(attrs.most_common()),
            'unused_core_types': [{'type': t, 'unsettled': st.get(t, [])} for t in unused_types],
            'unused_core_link_types': [{'link_type': c, 'unsettled': st.get(c, [])} for c in unused_links]}


# ------------------------------------------------------------------ stability (MS-04…MS-07)

def snapshot():
    """The core as it now is: every entity type, cross-layer link type, within-layer rule and attribute, with its status."""
    ents = {e['type']: e.get('status', 'active') for e in _entities()}
    reg = _j(LINKS)
    data = LINKS.with_name('relationship-types-data.json')   # DL-04: the Data layer's link types (ACCESSED_BY) are core link types too (MS-04)
    extra = _j(data)['relationships'] if data.exists() else []
    links = {r['mapping_type_id']: r.get('status', 'active') for r in reg['relationships'] + reg.get('deprecated_relationships', []) + extra}
    rules = {c['id']: c.get('status', 'active') for c in _j(MM / 'level-relationships.json')['constraints']}
    ea = _j(MM / 'entity-attributes.json')
    attrs = {a['id']: a.get('status', 'active') for a in ea['attributes'] + ea.get('common_attributes', [])}   # common attributes (CA-…) are core too (MS-04)
    return {'metamodel_version': _j(MM / 'a1-business.json')['metamodel_version'], 'entity_types': ents, 'link_types': links, 'within_layer_rules': rules, 'attributes': attrs}


def _v(s): return tuple(int(x) for x in s.split('.'))


def stability():
    """MS-05, MS-06: the core against its last freeze. Returns {changed, added, removed, deprecated, issues}. A change is allowed when the
    metamodel version moved on, a migration to the new version is recorded, and anything removed was already deprecated at the freeze."""
    if not STABILITY.exists(): return {'frozen': None, 'issues': ['no freeze recorded (metamodel/stability.json) — run sdem model freeze'], 'added': {}, 'removed': {}, 'deprecated': {}}
    frozen, now = _j(STABILITY), snapshot()
    added, removed, deprecated = {}, {}, {}
    for k in ('entity_types', 'link_types', 'within_layer_rules', 'attributes'):
        a, b = frozen[k], now[k]
        if set(b) - set(a): added[k] = sorted(set(b) - set(a))
        if set(a) - set(b): removed[k] = sorted(set(a) - set(b))
        dep = sorted(i for i in set(a) & set(b) if b[i] == 'deprecated' and a[i] != 'deprecated')
        if dep: deprecated[k] = dep
    issues = []
    changed = bool(added or removed or deprecated)
    if changed and _v(now['metamodel_version']) <= _v(frozen['metamodel_version']):
        issues.append(f"the core changed since the freeze at {frozen['metamodel_version']} but metamodel_version is still {now['metamodel_version']} — raise it (MS-05)")
    if changed and not any(m['to'] == now['metamodel_version'] for m in _j(MM / 'migrations.json')['migrations']):
        issues.append(f"no migration to {now['metamodel_version']} in metamodel/migrations.json — record one, with the owner's approval (MS-05)")
    for k, ids in removed.items():
        early = [i for i in ids if frozen[k][i] != 'deprecated']
        if early: issues.append(f"{k}: removed without being deprecated first (mark them deprecated, freeze, and remove in a later version — MS-06): {', '.join(early)}")
    if not changed and now['metamodel_version'] != frozen['metamodel_version']:
        issues.append(f"metamodel_version moved to {now['metamodel_version']} but the core did not change since the freeze at {frozen['metamodel_version']}")
    return {'frozen': frozen['metamodel_version'], 'frozen_by': frozen.get('frozen_by'), 'frozen_at': frozen.get('frozen_at'), 'current': now['metamodel_version'],
            'needs_freeze': changed and not issues, 'added': added, 'removed': removed, 'deprecated': deprecated, 'issues': issues}


def freeze(person, now=None):
    """MS-07: record the core as it now is — after an approved change passes stability (or for the first freeze)."""
    import datetime
    from .validate import is_person
    if not is_person(person): raise ValueError(f"--person {person!r}: a freeze records the owner's approval — give a person's name")
    st = stability() if STABILITY.exists() else {'issues': []}
    if st['issues']: raise ValueError('the core cannot be frozen as it is:\n  ' + '\n  '.join(st['issues']))
    from .files import write_json
    snap = snapshot()
    doc = {'note': 'The core of SDEM\'s metamodel at its last freeze (docs/design/sdem-metamodel-stability.md). Written by `sdem model freeze` after an approved, '
                   'versioned change; CI fails if the core changes without one.', 'frozen_by': person.strip(),
           'frozen_at': now or datetime.date.today().isoformat(), **snap}
    write_json(STABILITY, doc)
    return doc


# ------------------------------------------------------------------ the CLI

def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem model', description="The metamodel's health: what is not yet settled, what workspaces use, and whether the core changed as the stability policy allows.")
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('status', help="every part of SDEM's metamodel that is not fully settled, with its source and what would settle it")
    s.add_argument('--area', choices=['entity type', 'cross-layer link type', 'within-layer rule', 'attribute', 'spec gap'], help='one area only'); s.add_argument('--json', action='store_true')
    u = sub.add_parser('usage', help='which types, link types, kinds and attributes the given workspaces use — and which of SDEM\'s no workspace uses')
    u.add_argument('--workspace', dest='estates', action='append', metavar='DIR'); u.add_argument('--root', metavar='DIR', help='every workspace in a folder'); u.add_argument('--json', action='store_true')
    t = sub.add_parser('stability', help='the core against its last freeze — fails if it changed in a way the policy does not allow'); t.add_argument('--json', action='store_true')
    g = sub.add_parser('integrity', help='a design in the metamodel integrity reference shape: core, extensions, the federated graph and each graph (read-only)')
    g.add_argument('--workspace', required=True, metavar='DIR'); g.add_argument('--json', action='store_true')
    g.add_argument('--metamodel', action='store_true', help='the Metamodel Core and its Extensions drawn: each kind of record as a shape, each link the metamodel allows as a line — what the Metamodel view draws (JSON)')
    g.add_argument('--graph', action='store_true', help='every record and every link inside and between the graphs, each record placed on its plate — what the Metamodel views draw (JSON)')
    g.add_argument('--check', action='store_true', help="SDEM's verdict: each rule of the metamodel integrity design that can be checked from the design, met or not — exit 1 if one is not")
    f = sub.add_parser('freeze', help='record the core as it now is, after an approved change (maintainers)'); f.add_argument('--person', required=True); f.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    try:
        if a.cmd == 'status':
            r = status()
            if a.area: r['items'] = [i for i in r['items'] if i['area'] == a.area]
            if a.json: print(json.dumps(r, indent=2, ensure_ascii=False)); return 0
            print(f"SDEM metamodel {r['metamodel_version']} — what is not yet settled")
            for k, v in r['summary'].items(): print(f"  {k:<22} {v['unsettled']:>4} of {v['total']:<4} unsettled")
            print('  by reason: ' + ', '.join(f'{k} {n}' for k, n in r['by_status'].items()))
            for area in ('cross-layer link type', 'entity type', 'within-layer rule', 'spec gap', 'attribute'):
                rows = [i for i in r['items'] if i['area'] == area]
                if not rows: continue
                print(f"\n{area.upper()}S ({len(rows)})" + ('' if area != 'attribute' or a.area else ' — first 10; --area attribute for all'))
                for i in rows[:10 if area == 'attribute' and not a.area else None]:
                    print(f"  {i['id']:<64} {', '.join(i['status'])}\n      source: {i['source'][:110]}\n      to settle: {i['settle'][0]}")
            return 0
        if a.cmd == 'usage':
            ws = list(a.estates or [])
            if a.root: ws += sorted(str(p.parent) for p in Path(a.root).glob('*/mappings.json'))
            if not ws: raise ValueError('give --workspace DIR (repeatable) or --root DIR')
            r = usage(ws)
            if a.json: print(json.dumps(r, indent=2, ensure_ascii=False)); return 0
            print(f"{len(r['workspaces'])} workspace(s), {sum(w['records'] for w in r['workspaces'])} record(s)")
            print('\nENTITY TYPES USED (records, counting subtypes)'); [print(f'  {n:>5}  {t}') for t, n in list(r['entity_types'].items())[:25]]
            print('\nCROSS-LAYER LINK TYPES USED (approved and proposed connections)'); [print(f'  {n:>5}  {t}') for t, n in r['link_types'].items()]
            print(f"\nSDEM TYPES NO WORKSPACE USES ({len(r['unused_core_types'])}) — unsettled ones first")
            for x in r['unused_core_types']: print(f"  {x['type']:<36} {', '.join(x['unsettled']) or 'settled'}")
            print(f"\nSDEM LINK TYPES NO WORKSPACE USES ({len(r['unused_core_link_types'])})")
            for x in r['unused_core_link_types']: print(f"  {x['link_type']:<70} {', '.join(x['unsettled']) or 'settled'}")
            return 0
        if a.cmd == 'stability':
            r = stability()
            if a.json: print(json.dumps(r, indent=2)); return 1 if r['issues'] else 0
            print(f"core frozen at {r['frozen']} ({r.get('frozen_by')}, {r.get('frozen_at')}); current {r.get('current')}")
            for k in ('added', 'deprecated', 'removed'):
                for area, ids in r[k].items(): print(f"  {k} {area}: {', '.join(ids)}")
            for i in r['issues']: print(f'ERROR: {i}')
            if not r['issues']: print('OK: ' + ('changed as the policy allows — run sdem model freeze --person <owner> to record it' if r['needs_freeze'] else 'the core is as frozen'))
            return 1 if r['issues'] else 0
        if a.cmd == 'integrity' and a.metamodel:   # what may be: the kinds of record and the links allowed
            v = integrity_metamodel(a.workspace)
            if a.json: print(json.dumps(v, ensure_ascii=False)); return 0
            c = v['counts']; print(f"metamodel {v['metamodel']} ({v['stability']}) with its extensions: {c['records']} kinds of record in {len(v['graphs'])} graphs ({c['from_extensions']} from extensions); {c['inside']} links allowed inside a layer, {c['between']} between layers"); return 0
        if a.cmd == 'integrity' and a.graph:   # the Metamodel views' data: every record and link, from the graphs
            v = integrity_graph(a.workspace)
            if a.json: print(json.dumps(v, ensure_ascii=False)); return 0
            c = v['counts']; print(f"{v['design']}: {c['records']} records in {len(v['graphs'])} graphs; {c['inside']} links inside the graphs, {c['between']} approved links between them" + (f", {c['proposed']} proposed" if c['proposed'] else '')); return 0
        if a.cmd == 'integrity' and a.check:   # MID-01…MID-10: SDEM's verdict on the design
            v = integrity_check(a.workspace)
            if a.json: print(json.dumps(v, indent=2, ensure_ascii=False)); return 0 if v['met'] else 1
            print(f"{v['design']}: the metamodel integrity design — " + ('MET' if v['met'] else 'NOT MET: ' + ', '.join(v['not_met'])) + f" ({v['checked']} rules checked from the design)")
            for x in v['rules']: print(f"  {x['id']:<7} {({'met': 'met', 'not met': 'NOT MET', 'view': 'view'})[x['status']]:<8} {x['title']} — {x['evidence']}")
            return 0 if v['met'] else 1
        if a.cmd == 'integrity':   # MID-01…MID-10: the reference architecture, filled in for this design
            r = integrity(a.workspace)
            if a.json: print(json.dumps(r, indent=2, ensure_ascii=False)); return 0
            c = r['core']; print(f"Metamodel Core {c['metamodel']} — {c['stability'] or 'stability unknown'}; " + ', '.join(f"{l['code']} {l['types']} kinds" for l in c['layers']))
            for e in r['extensions']: print(f"Extension {e['name']} {e.get('version') or '(built in)'} — {e['pattern']}, {e['placement']}" + (f", layer {e['layer']}" if e.get('layer') else '') + f", {e['types']} kinds")
            fd = r['federated']; print(f"Federated Knowledge Graph — {fd['links'].get('approved', 0)} approved links between layers, {fd['link_types_in_use']} link types")
            for g in r['graphs']: print(f"  {g['code']:<3} {g['graph']:<9} {g['records']:>4} records, {g['links_inside']:>4} links inside" + (f"  ({g['extension']})" if g['extension'] else ''))
            return 0
        if a.cmd == 'freeze':
            d = freeze(a.person)
            print(json.dumps({'frozen': d['metamodel_version'], 'by': d['frozen_by']}) if a.json else f"froze the core at metamodel {d['metamodel_version']} ({d['frozen_by']}) — metamodel/stability.json")
            return 0
    except ValueError as e:
        print(f'ERROR: {e}', file=sys.stderr); return 2


if __name__ == '__main__':
    sys.exit(main())


def integrity(workspace):
    """MID-01…MID-10 (docs/design/metamodel-integrity-design.md §1): a design in the reference architecture's own shape, read-only — the
    Metamodel Core (and whether it is as frozen), the Metamodel Extensions merged into it (each with its pattern, H1 / H2 / V1, and what it
    adds), the Federated Knowledge Graph (the approved links between layers, each with its ArchiMate kind) and each layer's and extension's
    own graph (its records and links inside). A view draws it; it works nothing out (MID-02)."""
    import collections
    from . import profile as _p, parts, notation
    from .layers import layers
    from .identity import load as _jload
    from .metamodel import Metamodel
    ws = Path(workspace)
    _p.activate_from(ws)
    mm = Metamodel.load()
    rows = layers()
    froz = json.loads((Path(__file__).resolve().parents[1] / 'metamodel' / 'stability.json').read_text(encoding='utf-8')) if (Path(__file__).resolve().parents[1] / 'metamodel' / 'stability.json').exists() else {}
    try: st = stability(); stable = 'as frozen' if not st['issues'] and not st['needs_freeze'] else ('changed as the policy allows' if not st['issues'] else 'changed — ' + '; '.join(st['issues']))
    except Exception: stable = None
    packs = []
    for a in (_p.ACTIVE or {}).get('aspects') or []:
        try: pk = json.loads(Path(a['file']).read_text(encoding='utf-8'))
        except (OSError, ValueError, KeyError, TypeError): pk = {}
        packs.append((a, pk))
    pack_types = {t['type']: a.get('extension') or a.get('name') for a, pk in packs for t in pk.get('types') or []}
    def origin(l):
        s = str(l.get('source') or 'SDEM')
        if s == 'SDEM': return None
        if s == parts.EXT_BIAN: return 'bian'
        return next((a.get('extension') or a.get('name') for a, pk in packs if any(x.get('code') == l['code'] for x in pk.get('layers') or [])), s.split(' ')[0])
    graphs, by_code, code_of = [], {}, {}
    for l in rows:
        f = ws / l['file']
        try: d = _jload(f) if f.exists() else {}
        except (OSError, ValueError): d = {}
        recs = [i for i in d.get('instances') or [] if isinstance(i, dict)]
        live = [i for i in recs if i.get('lifecycle_status') != 'retired']
        for i in live: code_of[i.get('id')] = l['code']   # a retired record has left the design — and its links with it
        g = {'code': l['code'], 'name': l.get('name'), 'file': l['file'], 'graph': 'extension' if origin(l) else 'layer', 'extension': origin(l),
             'position': 'across' if l.get('across') else 'stack', 'records': len(live), 'retired': len(recs) - len(live), 'links_inside': len(d.get('relationships') or []),
             'by_type': dict(collections.Counter(str(i.get('type', '')).split('.')[-1] for i in live).most_common()),
             'by_kind': dict(collections.Counter(r.get('kind') for r in d.get('relationships') or []).most_common()),
             'types': sum(1 for e in mm.entities.values() if e.get('level') == l['code'] and not e.get('abstract'))}
        graphs.append(g); by_code[l['code']] = g
    core_layers = [{'code': g['code'], 'name': g['name'], 'types': sum(1 for t, e in mm.entities.items() if e.get('level') == g['code'] and not e.get('abstract') and t not in pack_types),
                    'rules_inside': sum(1 for c in mm.relationships.get('constraints', []) if c.get('level') == g['code'])} for g in graphs if not g['extension']]
    exts = []
    if parts.bian_on():
        a2 = next((g for g in graphs if g['extension'] == 'bian'), None)
        exts.append({'name': 'bian', 'built_in': True, 'pattern': 'H1', 'placement': 'a layer in the stack', 'layer': a2 and a2['code'],
                     'types': a2['types'] if a2 else 0, 'rules_inside': sum(1 for c in mm.relationships.get('constraints', []) if a2 and c.get('level') == a2['code']),
                     'trace_rules': sum(1 for r in mm.trace['rules'] if str(r.get('source_type', '')).startswith(('bian.', _L('bian') + '.'))), 'why_on': parts.why()})
    for a, pk in packs:
        lay = [x for x in pk.get('layers') or []]
        h2 = [t for t in pk.get('types') or [] if t.get('extends')]
        pat = 'V1' if any(x.get('position') == 'across' for x in lay) else 'H1' if lay else 'H2'
        exts.append({'name': a.get('extension') or a.get('name'), 'version': a.get('version'), 'pattern': pat,
                     'placement': {'V1': 'a layer beside the stack', 'H1': 'a layer in the stack', 'H2': 'kinds of record inside a layer'}[pat],
                     'layer': lay[0]['code'] if lay else None, 'types': len(pk.get('types') or []), 'types_in_core_layers': len(h2),
                     'link_types': len(pk.get('link_types') or []), 'link_kinds': len(pk.get('link_kinds') or []),
                     'link_types_by_archimate': dict(collections.Counter(x.get('archimate') or '—' for x in pk.get('link_types') or [])),
                     'trace_rules': len(pk.get('trace_rules') or []), 'rules': len(pk.get('rules') or []), 'computed_rules': len(pk.get('computed_rules') or []),
                     'requires': sorted({r for k in ('types', 'link_types') for x in pk.get(k) or [] for r in ([x['requires']] if isinstance(x.get('requires'), str) else x.get('requires') or [])})})
    try: maps = json.loads((ws / 'mappings.json').read_text(encoding='utf-8')).get('mappings') or []
    except (OSError, ValueError): maps = []
    maps = [m for m in maps if (m.get('source') or {}).get('id') in code_of and (m.get('target') or {}).get('id') in code_of]   # links between the design's live records only
    ok = [m for m in maps if m.get('status') == 'approved']
    by_rel = collections.Counter(m['relationship'] for m in ok)
    pairs = {}   # the links between each two graphs — what a view draws as the federated graph's joins
    for m in maps:
        a, b = code_of.get((m.get('source') or {}).get('id')), code_of.get((m.get('target') or {}).get('id'))
        if not a or not b or a == b: continue
        x = pairs.setdefault((a, b), {'from': a, 'to': b, 'approved': 0, 'proposed': 0, 'rejected': 0, 'by_relationship': collections.Counter()})
        st = m.get('status')
        if st == 'approved': x['approved'] += 1; x['by_relationship'][m['relationship']] += 1
        elif st == 'proposed': x['proposed'] += 1
        elif st in ('rejected', 'superseded'): x['rejected'] += 1
    order = {g['code']: n for n, g in enumerate(graphs)}
    return {'format': 'sdem-integrity/1', 'design': ws.resolve().name,
            'core': {'metamodel': mm.version, 'stability': stable, 'frozen_at': froz.get('frozen_at'), 'frozen_by': froz.get('frozen_by'),
                     'frozen': {k: len(froz.get(k) or {}) for k in ('entity_types', 'link_types', 'within_layer_rules', 'attributes')},
                     'layers': core_layers, 'trace_rules': len([r for r in mm.trace['rules'] if not str(r.get('source_type', '')).startswith(('bian.', _L('bian') + '.'))])},
            'extensions': exts,
            'federated': {'links': dict(collections.Counter(m.get('status') for m in maps)), 'link_types_in_use': len(by_rel),
                          'by_relationship': [{'relationship': r, 'archimate': notation.for_relationship(r), 'approved': n} for r, n in by_rel.most_common()],
                          'graphs': [g['code'] for g in graphs],
                          'pairs': [{**x, 'by_relationship': dict(x['by_relationship'].most_common())} for _, x in sorted(pairs.items(), key=lambda kv: (order.get(kv[0][0], 99), order.get(kv[0][1], 99)))]},
            'graphs': graphs}


def _version():
    try:
        from . import __version__; return __version__
    except Exception:
        return None


def _graph_store(ws, files):
    """The graph store SDEM builds for the design (`sdem build`): each graph's file with its nodes and edges, the file it was built from (its
    model version and fingerprint), the build's number, time, result and findings — built in a temporary folder, in this process."""
    import contextlib, io, tempfile
    from .cli import main as _main
    from . import profile as _p
    with tempfile.TemporaryDirectory() as t:
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            try: _main(['build', '--workspace', str(ws), '-o', str(Path(t) / 'g'), '--json'])
            except SystemExit: pass
    _p.activate_from(ws)
    try: b = json.loads(out.getvalue())
    except ValueError: return None
    by_file = {Path(f).name: c for c, f in files.items()}
    inputs = {Path(x.get('path', '')).name: x for x in b.get('inputs') or []}
    graphs = []
    for o in b.get('outputs') or []:
        stem = o['file'].split('.graph.json')[0]
        src = next((f for f in by_file if Path(f).stem == stem), None) or next((Path(f).name for c, f in files.items() if c.lower() == stem), None)   # a profile layer's graph is named by its code (s.graph.json)
        code = 'federated' if stem == 'federated' else (by_file.get(src) if src else stem.upper())
        i = inputs.get(src) or {}
        graphs.append({'graph': code, 'file': o['file'], 'nodes': o.get('nodes'), 'edges': o.get('edges'), 'sha256': o.get('sha256'),
                       **({'built_from': src, 'model_id': i.get('model_id'), 'model_version': i.get('model_version'), 'input_sha256': i.get('sha256')} if src else
                          {'built_from': 'mappings.json and the graphs above'} if code == 'federated' else {})})
    return {'build': b.get('build'), 'at': b.get('at'), 'result': b.get('result') or ('accepted' if not b.get('errors') else 'rejected'),
            'sdem': (b.get('sdem') or {}).get('version') if isinstance(b.get('sdem'), dict) else b.get('sdem'), 'metamodel': b.get('metamodel_version'),
            'errors': len(b.get('errors') or []), 'warnings': len(b.get('warnings') or []), 'graphs': graphs}


def integrity_check(workspace):
    """MID-01…MID-10 (docs/design/metamodel-integrity-design.md §4): SDEM's verdict on a design — each rule that can be checked from the
    design itself, met or not, with its evidence; the rules about how a view draws the design (MID-01, MID-02, MID-06, MID-09) are said to be
    the views' to show, never guessed here. Read-only; `sdem model integrity --check` exits 1 when a rule is not met."""
    import contextlib, io, tempfile, types
    from . import profile as _p, notation
    from .metamodel import Metamodel
    ws = Path(workspace)
    d = integrity(ws)
    mm = Metamodel.load()
    def run(*a):   # SDEM's own commands, in this process — it starts no program (PRIVACY.md §2)
        from .cli import main as _main
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            try: rc = _main([str(x) for x in a])
            except SystemExit as e: rc = e.code if isinstance(e.code, int) else 1
        _p.activate_from(ws)   # the workspace this verdict is about, again
        return types.SimpleNamespace(returncode=rc or 0, stdout=out.getvalue())
    rules = []
    def rule(i, title, ok, evidence): rules.append({'id': i, 'title': title, 'status': 'met' if ok else 'not met', 'evidence': evidence})
    # MID-03 — the core is not changed by an extension: it is as frozen
    st = d['core'].get('stability') or 'unknown'
    rule('MID-03', 'The core is not changed by an extension', st == 'as frozen' or st.startswith('changed as the policy allows'), f"core {st} at metamodel {d['core']['metamodel']}")
    # MID-04 — each graph built from its entities and checked by the metamodel; links between layers only through the registry
    c = run('check', '--workspace', ws, '--json')
    try: cj = json.loads(c.stdout); errs = sum(len(v or []) for v in (cj.get('report') or {}).values()); ok4 = bool(cj.get('ok', c.returncode == 0)) and not errs
    except ValueError: cj, errs, ok4 = {}, None, False
    rule('MID-04', 'Each graph built from its entities and checked by the metamodel', ok4, f"sdem check: {'no errors' if ok4 else (str(errs) + ' error(s)' if errs is not None else 'did not run')}")
    # MID-05 — every shape accounted for: reached, or listed as a design gap or a rule gap; met when there is neither
    with tempfile.TemporaryDirectory() as t:
        b = run('build', '--workspace', ws, '-o', Path(t) / 'g')
        g = run('trace', 'GAPS', '--graph', Path(t) / 'g', '--json') if b.returncode == 0 else None
    try: gj = json.loads(g.stdout) if g else {}
    except ValueError: gj = {}
    ok5 = bool(gj) and gj.get('rule_gaps') == 0 and gj.get('design_gaps') == 0
    rule('MID-05', 'Every shape accounted for', ok5, (f"{gj['complete']} of {gj['records']} records reach every other layer; {gj['design_gaps']} design gap(s), {gj['rule_gaps']} rule gap(s)" if gj else 'the graph could not be built'))
    # MID-07 — every type an ArchiMate element (own or inherited), every link an ArchiMate relationship — the extensions' too
    no_el = [t for t in mm.entities if t.count('.') >= 1 and not mm.entities[t].get('abstract') and not (notation.for_type(mm, t) or {}).get('element')]
    no_rel = [x['relationship'] for x in d['federated']['by_relationship'] if not x['archimate']]
    no_pack = [f"{x.get('source_type')} {x.get('relationship')} {x.get('target_type')}" for x in ((_p.ACTIVE or {}).get('link_types') or []) if not x.get('archimate')]
    AK = {'composition', 'aggregation', 'assignment', 'realization', 'serving', 'access', 'influence', 'triggering', 'flow', 'specialization', 'association'}   # ArchiMate 3.2 §5
    no_rel += sorted({str(x.get('kind') or x.get('relationship')) for x in integrity_graph(ws)['links'] if x.get('archimate') not in AK} - set(no_rel))   # 0.21.13: every link in the graph, inside a layer too
    rule('MID-07', 'Every link and type labelled by its standard', not (no_el or no_rel or no_pack),
         'every type an ArchiMate element and every link an ArchiMate relationship' if not (no_el or no_rel or no_pack) else
         '; '.join(filter(None, [no_el and f"types with no element: {', '.join(no_el[:5])}", no_rel and f"links with no kind: {', '.join(no_rel)}", no_pack and f"pack link types with no kind: {', '.join(no_pack[:5])}"])))
    # MID-08 — extensions by pattern: each declares where it sits (H1 / H2 / V1)
    bad8 = [e['name'] for e in d['extensions'] if e.get('pattern') not in ('H1', 'H2', 'V1')]
    rule('MID-08', 'Extensions by pattern, not by name', not bad8, ', '.join(f"{e['name']} {e['pattern']}" for e in d['extensions']) or 'no extension' if not bad8 else 'no pattern: ' + ', '.join(bad8))
    # MID-10 — an extension may require another: what requires one that is off is left out and said, never an error
    left = [x for x in ((_p.ACTIVE or {}).get('left_out') or []) if x.get('requires')]
    rule('MID-10', 'An extension may require another', True, (f"{len(left)} item(s) left out and said, each requiring an extension that is off" if left else 'every requirement between extensions is met'))
    for i, t in (('MID-01', 'Two sources of truth'), ('MID-02', 'One place computes'), ('MID-06', 'Views are of the source'), ('MID-09', 'A vertical extension is an overlay')):
        rules.append({'id': i, 'title': t, 'status': 'view', 'evidence': 'about how a view draws the design — shown and tested by the view (DESNRE), not decided here'})
    rules.sort(key=lambda r: int(r['id'].split('-')[1]))
    checked = [r for r in rules if r['status'] != 'view']
    return {'format': 'sdem-integrity-check/1', 'design': d['design'], 'met': all(r['status'] == 'met' for r in checked),
            'checked': len(checked), 'not_met': [r['id'] for r in checked if r['status'] != 'met'], 'rules': rules}


def integrity_graph(workspace):
    """MID-01, MID-02 (docs/design/metamodel-integrity-design.md): the design's records and links as the knowledge graphs hold them, for a
    view to draw — every record of every graph (each layer's and each extension's, retired ones left out), every link inside a graph (its kind
    and ArchiMate relationship) and every link between graphs (approved, or proposed and waiting), each record placed on its graph's plate
    (fractions 0–1), grouped by its kind. The Metamodel views are drawn from this alone; nothing is worked out by the view."""
    import collections, math
    from . import notation
    from .identity import load as _jload
    d = integrity(workspace)   # activates the workspace's profile, and names the graphs
    ws = Path(workspace)
    from .layers import layers
    files = {l['code']: l['file'] for l in layers()}
    records, links, zones, live, code_of = [], [], {}, set(), {}
    for g in d['graphs']:
        f = ws / files.get(g['code'], g['file'])
        try: doc = _jload(f) if f.exists() else {}
        except (OSError, ValueError): doc = {}
        recs = [i for i in doc.get('instances') or [] if isinstance(i, dict) and i.get('lifecycle_status') != 'retired']
        groups = collections.OrderedDict()
        for k, n in sorted(collections.Counter(str(i.get('type', '')).split('.')[-1] for i in recs).items(), key=lambda kv: (-kv[1], kv[0])): groups[k] = []
        for i in sorted(recs, key=lambda i: i['id']): groups[str(i.get('type', '')).split('.')[-1]].append(i)
        cols = max(6, math.ceil(math.sqrt(max(1, len(recs))) * 1.6))
        rows = sum(math.ceil(len(v) / cols) for v in groups.values()) or 1
        top, gap = 0.06, 0.88 / rows
        r0, zs = 0, []
        for k, items in groups.items():
            n_rows = math.ceil(len(items) / cols)
            for j, i in enumerate(items):
                rr, cc = r0 + j // cols, j % cols
                records.append({'id': i['id'], 'name': i.get('name') or i['id'], 'type': i.get('type'), 'kind': k, 'graph': g['code'], 'group': k,
                                'lifecycle_status': i.get('lifecycle_status'), 'at': [round(0.04 + (cc + 0.5) * 0.92 / cols, 4), round(top + (rr + 0.5) * gap, 4)]})
                live.add(i['id']); code_of[i['id']] = g['code']
            zs.append({'id': f"T:{g['code']}:{k}", 'label': f"{k} · {len(items)}", 'rect': [0.02, round(top + r0 * gap, 4), 0.98, round(top + (r0 + n_rows) * gap, 4)]})
            r0 += n_rows
        zones[g['code']] = zs
        for x in doc.get('relationships') or []:
            if x.get('source') in live and x.get('target') in live:
                links.append({'source': x['source'], 'target': x['target'], 'scope': 'inside', 'graph': g['code'], 'kind': x.get('kind'),
                              'archimate': notation.for_relationship(x.get('kind')) or x.get('kind'), 'status': 'stated'})
    try: maps = json.loads((ws / 'mappings.json').read_text(encoding='utf-8')).get('mappings') or []
    except (OSError, ValueError): maps = []
    for m in maps:
        a, b = (m.get('source') or {}).get('id'), (m.get('target') or {}).get('id')
        if m.get('status') not in ('approved', 'proposed') or a not in live or b not in live or code_of[a] == code_of[b]: continue
        links.append({'source': a, 'target': b, 'scope': 'between', 'from': code_of[a], 'to': code_of[b], 'relationship': m['relationship'],
                      'archimate': notation.for_relationship(m['relationship']), 'status': m['status']})
    store = _graph_store(ws, files)
    return {'format': 'sdem-integrity-graph/1', 'design': d['design'], **({'store': store} if store else {}),
            'graphs': [{k: g[k] for k in ('code', 'name', 'graph', 'extension', 'position')} for g in d['graphs']], 'zones': zones,
            'records': records, 'links': links,
            'counts': {'records': len(records), 'inside': sum(1 for x in links if x['scope'] == 'inside'),
                       'between': sum(1 for x in links if x['scope'] == 'between' and x['status'] == 'approved'),
                       'proposed': sum(1 for x in links if x['scope'] == 'between' and x['status'] == 'proposed')}}


def integrity_metamodel(workspace):
    """The Metamodel Core and the Extensions merged into it, drawn as SDEM holds them (docs/design/metamodel-integrity-design.md §1, the top
    of the reference model): each graph's kinds of record as shapes — where each comes from (the core or an extension), its ArchiMate element and
    how many records the design has of it — and the links the metamodel allows as lines: the rules inside a layer (their ArchiMate kind) and the
    link types between layers (their ArchiMate relationship), each kind placed on its graph's plate. What *may be*; `--graph` is what *is*."""
    import collections, math
    from . import notation
    from .metamodel import Metamodel
    from .validate import load_registry
    d = integrity(workspace)   # activates the workspace's profile: the core with its extensions merged in
    mm = Metamodel.load()
    from . import profile as _p
    ext_of = {}
    for a in (_p.ACTIVE or {}).get('aspects') or []:
        try: pk = json.loads(Path(a['file']).read_text(encoding='utf-8'))
        except (OSError, ValueError, KeyError, TypeError): pk = {}
        for t in pk.get('types') or []: ext_of[t['type']] = a.get('extension') or a.get('name')
    gcode = {g['code']: g for g in d['graphs']}
    count = {}
    for g in d['graphs']:
        for k, n in (g.get('by_type') or {}).items(): count[(g['code'], k)] = n
    kinds, records = {}, []
    for code, g in gcode.items():
        ts = sorted(t for t, e in mm.entities.items() if e.get('level') == code and not e.get('abstract'))
        cols = max(4, math.ceil(math.sqrt(max(1, len(ts))) * 1.4)); rows = math.ceil(len(ts) / cols) or 1
        for j, t in enumerate(ts):
            short = t.split('.')[-1]
            src = ext_of.get(t) or (g['extension'] if g['extension'] else 'core')
            el = (notation.for_type(mm, t) or {}).get('element')
            rr, cc = j // cols, j % cols
            kinds[t] = code
            records.append({'id': t, 'name': short, 'type': t, 'kind': short, 'graph': code, 'group': src, 'archimate': el, 'source': src,
                            'records_in_design': count.get((code, short), 0),
                            'at': [round(0.05 + (cc + 0.5) * 0.9 / cols, 4), round(0.1 + (rr + 0.5) * 0.8 / rows, 4)]})
    links, seen = [], set()
    def resolve(t):   # a rule on an abstract kind applies to each concrete kind below it
        return [t] if t in kinds else [k for k in kinds if mm.is_a(k, t)]
    for c in mm.relationships.get('constraints', []):
        for a in resolve(c.get('source_type')):
            for b in resolve(c.get('target_type')):
                if kinds.get(a) != kinds.get(b): continue
                key = (a, c['kind'], b)   # a kind may link to its own kind (a process flows to the next, a capability holds sub-capabilities)
                if key in seen: continue
                seen.add(key)
                links.append({'source': a, 'target': b, 'scope': 'inside', 'graph': kinds[a], 'kind': c['kind'], 'rule': c.get('id'),
                              'archimate': notation.for_relationship(c['kind']) or c['kind'], 'status': 'allowed'})
    for r in load_registry()['relationships']:
        for a in resolve(r['source_type']):
            for b in resolve(r['target_type']):
                if kinds.get(a) == kinds.get(b): continue
                key = (a, r['relationship'], b)
                if key in seen: continue
                seen.add(key)
                links.append({'source': a, 'target': b, 'scope': 'between', 'from': kinds[a], 'to': kinds[b], 'relationship': r['relationship'],
                              'archimate': notation.for_relationship(r['relationship']), 'status': 'allowed', 'evidence_needed': r.get('required_evidence')})
    zones = {code: [{'id': f'K:{code}', 'label': f"{sum(1 for x in records if x['graph'] == code)} kinds of record", 'rect': [0.02, 0.06, 0.98, 0.94]}] for code in gcode}
    return {'format': 'sdem-integrity-metamodel/1', 'design': d['design'], 'metamodel': d['core']['metamodel'], 'stability': d['core'].get('stability'),
            'graphs': [{k: g[k] for k in ('code', 'name', 'graph', 'extension', 'position')} for g in d['graphs']], 'zones': zones,
            'records': records, 'links': links,
            'counts': {'records': len(records), 'inside': sum(1 for x in links if x['scope'] == 'inside'), 'between': sum(1 for x in links if x['scope'] == 'between'), 'proposed': 0,
                       'from_extensions': sum(1 for x in records if x['source'] != 'core')}}
