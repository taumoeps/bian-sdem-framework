"""The metamodel's health (docs/design/sdem-metamodel-stability.md, MS-01…MS-08): what is not yet settled, what workspaces actually
use, and whether the core changed only as the stability policy allows.

  sdem model status            every part of SDEM's metamodel that is not fully settled — with its source and what would settle it
  sdem model usage             which types, link types, within-layer kinds and attributes the given workspaces use
  sdem model stability         the core against its last freeze (metamodel/stability.json): what changed, and whether the policy allows it
  sdem model freeze            record the core as it now is — after an approved, versioned change (maintainers)

Read-only except `freeze`. Everything here reads SDEM's own metamodel (never a workspace's profile, unless asked for usage).
"""
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


def _j(p): return json.loads(Path(p).read_text(encoding='utf-8'))


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
                for t in [i['type']] + mm.ancestors(i['type']): types[t] += 1
                for k in (i.get('attributes') or {}): attrs[f"{i['type']}.{k}"] += 1
            for r in d.get('relationships', []): kinds[f"{l['code']} {r['kind']}"] += 1
        for m in _j(ws / 'mappings.json').get('mappings', []):
            if m.get('status') in ('approved', 'proposed'):
                s, rel, tg = m['source']['type'], m['relationship'], m['target']['type']
                links[f'{s} {rel} {tg}'] += 1
                for cs, cr, ct in core:   # the SDEM link type it is an instance of — by type or subtype
                    if cr == rel and mm.is_a(s, cs) and mm.is_a(tg, ct): core_used[f'{cs} {cr} {ct}'] += 1
        per_ws.append({'workspace': str(ws), 'records': n, 'profile': (_p.record() or {}).get('name')})
    _p.deactivate()
    st = {i['id']: i['status'] for i in status()['items']}
    core_types = [e['type'] for e in _entities() if not e.get('abstract')]
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
    links = {r['mapping_type_id']: r.get('status', 'active') for r in reg['relationships'] + reg.get('deprecated_relationships', [])}
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
        if a.cmd == 'freeze':
            d = freeze(a.person)
            print(json.dumps({'frozen': d['metamodel_version'], 'by': d['frozen_by']}) if a.json else f"froze the core at metamodel {d['metamodel_version']} ({d['frozen_by']}) — metamodel/stability.json")
            return 0
    except ValueError as e:
        print(f'ERROR: {e}', file=sys.stderr); return 2


if __name__ == '__main__':
    sys.exit(main())
