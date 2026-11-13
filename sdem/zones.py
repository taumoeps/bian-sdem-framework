"""`sdem zones` — a workspace's network zones: each zone, what it holds, and how the zones connect (ZC-01…ZC-04; metamodel 0.11.0).

Read-only. The zone connections are worked out from the zone structure — never stored as records:
  ZC-01 level-0 zones with each other (on premises ↔ cloud) · ZC-02 the level-1 zones of one level 0 with each other (DMZ ↔ internal) ·
  ZC-03 a zone with the zone it is part of · ZC-04 a shape reaches another through their zones (`sdem zones path A B`).

  sdem zones --workspace examples/payment-initiation
  sdem zones path INF-APIGW-PAY INF-PG-PAY-PROD --workspace examples/payment-initiation
"""
import argparse, json, sys
from pathlib import Path


def collect(workspace):
    """The zones, their placements (direct and through a host, inferred or confirmed) and the connections — JSON-ready."""
    from .conformance import zones_of
    from .hosting import zone_connections
    from .metamodel import Metamodel
    from . import profile as _p
    ws = Path(workspace); f = ws / 'a4-technology.json'
    if not f.exists(): raise ValueError(f'{ws}: no a4-technology.json — no technology layer, so no network zones')
    _p.activate_from(ws)
    doc = json.loads(f.read_text(encoding='utf-8')); mm = Metamodel.load()
    byid = {i['id']: i for i in doc.get('instances', [])}
    shapes, parent, direct = zones_of(doc, mm)
    zones = [{'id': z, 'name': byid[z]['name'], 'level': (byid[z].get('attributes') or {}).get('zone_level'), 'kind': (byid[z].get('attributes') or {}).get('zone_kind'),
              'part_of': parent.get(z), 'holds': sorted(direct.get(z, [])),
              'inferred': isinstance((byid[z].get('attributes') or {}).get('inferred'), dict)}
             for z, i in byid.items() if mm.is_a(i['type'], 'A4.NetworkZone')]
    marks = {(r['source'], r['target']): r['inferred'] for r in doc.get('relationships', []) if isinstance(r.get('inferred'), dict)}
    placed = [{'shape': x, 'zone': zs[0] if zs else None, 'how': ('directly' if x in {y for v in direct.values() for y in v} else 'through its host') if zs else 'in no zone',
               **({'inferred': marks[(zs[0], x)]} if zs and (zs[0], x) in marks else {})} for x, zs in sorted(shapes.items())]
    conns = [{'from': a, 'to': b, 'rule': r} for a, b, r in zone_connections(doc, mm)]
    return {'workspace': ws.as_posix(), 'zones': sorted(zones, key=lambda z: (z['level'] if z['level'] is not None else 9, z['id'])), 'placements': placed, 'connections': conns}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ['path']:
        ap = argparse.ArgumentParser(prog='sdem zones path', description='How one shape reaches another through their network zones (ZC-04).')
        ap.add_argument('a', metavar='SHAPE', help='the shape to start from'); ap.add_argument('b', metavar='SHAPE', help='the shape to reach')
        ap.add_argument('--workspace', dest='estate', required=True, metavar='DIR'); ap.add_argument('--json', action='store_true')
        a = ap.parse_args(argv[1:])
        from .hosting import path
        from .metamodel import Metamodel
        f = Path(a.estate) / 'a4-technology.json'
        if not f.exists(): print(f'ERROR: {a.estate}: no a4-technology.json', file=sys.stderr); return 2
        route = path(json.loads(f.read_text(encoding='utf-8')), Metamodel.load(), a.a, a.b)
        if a.json: print(json.dumps({'from': a.a, 'to': a.b, 'path': route}, indent=2)); return 0 if route else 1
        if not route: print(f'{a.a} does not reach {a.b} through network zones — one of them is in no zone (sdem check, LC-16)'); return 1
        print(' → '.join(route)); return 0
    ap = argparse.ArgumentParser(prog='sdem zones', formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description="A workspace's network zones: each zone and what it holds, and how the zones connect (ZC-01…ZC-03, worked out from the structure). Read-only.",
                                 epilog=__doc__.split('\n\n')[2])
    ap.add_argument('--workspace', dest='estate', required=True, metavar='DIR'); ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    try: res = collect(a.estate)
    except ValueError as e: print(f'ERROR: {e}', file=sys.stderr); return 2
    if a.json: print(json.dumps(res, indent=2)); return 0
    if not res['zones']:
        print(f"{a.estate}: no network zones recorded — start them with sdem new --hosting (a new workspace) or let sdem aid propose them"); return 0
    for z in res['zones']:
        print(f"{'  ' * (z['level'] or 0)}{z['id']}  level {z['level']} {z['kind']}  {z['name']}{'  (inferred)' if z['inferred'] else ''}"
              + (f"  holds: {', '.join(z['holds'])}" if z['holds'] else ''))
    print('connections (worked out from the structure):')
    for c in res['connections']: print(f"  {c['from']} — {c['to']}  ({c['rule']})")
    loose = [p['shape'] for p in res['placements'] if p['how'] == 'in no zone']
    waiting = [p['shape'] for p in res['placements'] if p.get('inferred', {}).get('status') == 'proposed']
    if loose: print(f"in no zone ({len(loose)}): {', '.join(loose)} — LC-16")
    if waiting: print(f"inferred placements to decide ({len(waiting)}): {', '.join(waiting)} — sdem aid confirm|reject <shape>")
    return 0


if __name__ == '__main__':
    sys.exit(main())
