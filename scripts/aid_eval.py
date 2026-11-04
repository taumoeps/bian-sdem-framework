"""How well AID infers across BIAN — every service domain of the base BIAN, both directions (docs/design/aid-spec.md AID-E01).

Downstream: a business activity named as an architect would — "<action term> <what the domain is about>", e.g. "Initiate term
deposit" — must lead to exactly that service domain. Upstream: a deployment named after its application — "<what the domain is
about> Engine — production" — must lead up to that domain and a capability candidate. The names follow the domain's own subject,
so this measures the rules, not an architect's wording; real designs are messier.

  python scripts/aid_eval.py [--limit N] [--json]
"""
import argparse, json, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem.aid import project, subject_words  # noqa: E402
from sdem.metamodel import Metamodel  # noqa: E402
from sdem.new import base_layer  # noqa: E402


def dataset(level, instances, rels=()):
    return {'level': level, 'model_id': f'EVAL-{level}', 'model_version': '1', 'metamodel_version': Metamodel.load().version, 'source_system': 'EVAL',
            'instances': instances, 'relationships': list(rels)}


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument('--limit', type=int, default=0); ap.add_argument('--json', action='store_true'); a = ap.parse_args(argv)
    cat, _ = base_layer(); by = {i['id']: i for i in cat['instances']}
    out = {}
    for r in cat['relationships']:
        out.setdefault(r['source'], []).append(r['target'])
    def ops_of(d):
        todo, seen, ops = list(out.get(d, [])), set(), []
        while todo:
            x = todo.pop()
            if x in seen or x not in by: continue
            seen.add(x)
            if by[x]['type'] == 'A2.ServiceOperation': ops.append(by[x])
            elif by[x]['type'] == 'A2.ServiceGroup': todo += out.get(x, [])
        return ops
    class P:  # what subject_words needs
        cat_by_id = by
    doms = sorted((i for i in cat['instances'] if i['type'] == 'A2.ServiceDomain'), key=lambda i: i['name'])
    if a.limit: doms = doms[:a.limit]
    res = {'down': Counter(), 'up': Counter()}; misses = {'down': [], 'up': []}
    for d in doms:
        subject = ' '.join(sorted(subject_words(P, d))) and ((by.get((d.get('attributes') or {}).get('asset_type')) or {}).get('name') or d['name'])
        ops = ops_of(d["id"])
        term = next((o['attributes'].get('action_term') for o in ops if o['attributes'].get('action_term') == 'Initiate'), None) or (ops[0]['attributes'].get('action_term') if ops else None)
        if term:   # downstream
            act = {'id': 'ACT-1', 'type': 'A1.BusinessActivity', 'version': '1', 'name': f'{term} {subject.lower()}', 'lifecycle_status': 'active', 'attributes': {'sequence': 1}}
            pkg = project({'A1': dataset('A1', [act])}, cat)
            got = {i['id'] for i in pkg['layers'].get('A2', {}).get('instances', []) if i['type'] == 'A2.ServiceDomain'}
            k = 'exact' if got == {d['id']} else 'among others' if d['id'] in got else 'none' if not got else 'wrong'
            res['down'][k] += 1
            if k != 'exact': misses['down'].append((d['name'], act['name'], sorted(by[g]['name'] for g in got)[:4]))
        else: res['down']['no operations'] += 1
        dep = {'id': 'DEP-1', 'type': 'A4.Deployment', 'version': '1', 'name': f'{subject} Engine — production', 'lifecycle_status': 'planned', 'attributes': {'component_id': 'APP-EVAL'}}
        pkg = project({'A4': dataset('A4', [dep])}, cat)
        got = {i['id'] for i in pkg['layers'].get('A2', {}).get('instances', []) if i['type'] == 'A2.ServiceDomain'}
        caps = [i for i in pkg['layers'].get('A1', {}).get('instances', []) if i['type'] == 'A1.BusinessCapability']
        k = ('exact' if got == {d['id']} else 'among others' if d['id'] in got else 'none' if not got else 'wrong') + (' + capability' if caps else '')
        res['up'][k] += 1
        if not k.startswith('exact'): misses['up'].append((d['name'], dep['name'], sorted(by[g]['name'] for g in got)[:4]))
    if a.json: print(json.dumps({'domains': len(doms), 'down': res['down'], 'up': res['up'], 'misses': misses}, indent=1)); return 0
    print(f'{len(doms)} BIAN service domains')
    for w in ('down', 'up'):
        print(f"  {w}stream: " + ', '.join(f'{k} {v}' for k, v in res[w].most_common()))
    for w in ('down', 'up'):
        for m in misses[w][:8]: print(f'  {w} miss: {m[0]!r} from {m[1]!r} → {m[2]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
