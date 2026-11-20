"""`sdem viewpoint` — the viewpoints SDEM defines, as data (docs/design/sdem-architecture-viewpoint-spec.md §10, ARV-18…ARV-22): which
records each plate draws (a type's subtypes too, ARV-19), how they group, which links connect them, what is left out and why, and the
layout each plate uses (named, not encoded — ARV-20). Viewers (DESNRE's 3D view and the Design document's figures) draw from them."""
from .identity import load as _jload  # DL-11: a design's files read through one boundary (docs/design/sdem-data-layer-spec.md)
from .identity import T as _T, layer as _L  # ST-01…ST-05: layers and types by id (docs/design/sdem-stable-identity-spec.md)
import argparse, json, sys
from .paths import DATA_ROOT

DIR = DATA_ROOT / 'metamodel'
LAYOUTS = {'rows-by-kind', 'nested-groupings', 'zones-nodes-deployments'}


def names(): return sorted(p.stem[len('viewpoint-'):] for p in DIR.glob('viewpoint-*.json'))


def load(name):
    f = DIR / f'viewpoint-{name}.json'
    if not f.is_file(): raise ValueError(f"no viewpoint {name!r} — SDEM defines: {', '.join(names()) or 'none'}")
    return _jload(f)


def check(mm, d):
    """ARV-21: every type a definition names is one SDEM knows; every connection a link kind, a relationship or 'type:<a type>'; every
    layout one viewers implement; every core type of a plate's layer is drawn, grouped or left out — none silently dropped (ARV-05)."""
    from .notation import load as notation
    known_k = set(notation()['within_layer']) | set(notation()['cross_layer'])
    out = []
    for p in d.get('plates', []):
        here = list(p.get('shapes', [])) + [g['type'] for g in p.get('groupings', [])] + [x['of'] for g in p.get('groupings', []) for x in g['holds']] \
               + [t for lo in p.get('left_out', []) for t in lo['types']] + [c[5:] for c in p.get('connections', []) if c.startswith('type:')]
        out += [f"{p['code']}: {t} is not a type SDEM knows" for t in here if t not in mm.entities]
        out += [f"{p['code']}: connection {c!r} is neither a link kind nor a relationship SDEM knows" for c in p.get('connections', []) if not c.startswith('type:') and c not in known_k]
        if p.get('layout') not in LAYOUTS: out.append(f"{p['code']}: layout {p.get('layout')!r} is not one viewers implement ({', '.join(sorted(LAYOUTS))})")
        layer = p['code'].split('-')[0]
        covered = {t for t in here}
        missing = [t for t, e in mm.entities.items() if e.get('level') == layer and t.count('.') == 1 and not e.get('abstract') and t not in covered
                   and not any(a in covered for a in mm.ancestors(t))]
        if layer != _L('application'): out += [f"{p['code']}: {t} is neither drawn nor named as left out (ARV-05)" for t in missing]
    a3 = [p for p in d.get('plates', []) if p['code'].startswith(_L('application'))]
    if a3:   # A3 is drawn on two plates: together they cover the layer
        cov = {t for p in a3 for t in list(p.get('shapes', [])) + [g['type'] for g in p.get('groupings', [])] + [t for lo in p.get('left_out', []) for t in lo['types']]}
        out += [f'{_L("application")}: {t} is neither drawn nor named as left out (ARV-05)' for t, e in mm.entities.items() if e.get('level') == _L('application') and t.count('.') == 1 and not e.get('abstract') and t not in cov]
    out += [f'between plates: {r} is not a relationship SDEM knows' for r in d.get('between_plates', []) if r not in notation()['cross_layer']]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem viewpoint', description=__doc__.split('\n\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('list', help='the viewpoints SDEM defines').add_argument('--json', action='store_true')
    s = sub.add_parser('show', help='one viewpoint: its plates, what each draws and leaves out, its layouts'); s.add_argument('name'); s.add_argument('--json', action='store_true')
    c = sub.add_parser('check', help="check every viewpoint and the ArchiMate notation against SDEM's metamodel (ARV-16, ARV-21)"); c.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    try:
        if a.cmd == 'list':
            items = [{'name': n, 'title': load(n).get('title'), 'plates': [p['code'] for p in load(n)['plates']]} for n in names()]
            print(json.dumps({'viewpoints': items}, indent=2) if a.json else '\n'.join(f"{x['name']:<14} {x['title']} — plates {', '.join(x['plates'])}" for x in items)); return 0
        if a.cmd == 'show':
            d = load(a.name)
            if a.json: print(json.dumps(d, indent=2, ensure_ascii=False)); return 0
            print(f"{d['title']} viewpoint ({d['notation']}), version {d['version']}")
            for p in d['plates']:
                print(f"\n{p['code']} {p['name']} — {p['answers']}  [layout: {p['layout']}]\n  shapes: {', '.join(p['shapes'])}")
                for g in p['groupings']: print(f"  grouping {g['type']} holds " + ', '.join(f"{x['of']} ({x['kind']})" for x in g['holds']))
                print(f"  connections: {', '.join(p['connections'])}")
                for lo in p['left_out']: print(f"  left out: {', '.join(lo['types'])} — {lo['why']}")
            return 0
        from .metamodel import Metamodel
        from .validate import load_registry
        from . import notation
        mm = Metamodel.base(); probs = notation.check(mm, load_registry()) + [f'{n}: {x}' for n in names() for x in check(mm, load(n))]
        if a.json: print(json.dumps({'ok': not probs, 'problems': probs}, indent=2)); return 1 if probs else 0
        for x in probs: print(f'ERROR: {x}')
        if not probs: print(f"OK: the ArchiMate notation and {len(names())} viewpoint(s) agree with SDEM's metamodel")
        return 1 if probs else 0
    except ValueError as e:
        print(f'ERROR: {e}', file=sys.stderr); return 2


if __name__ == '__main__':
    sys.exit(main())
