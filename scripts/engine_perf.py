"""Rules-engine performance check (the 2026-10-29 audit: 8,000 records took 7 minutes).

Builds a synthetic workspace by copying examples/payment-initiation — every layer, the links inside them and the attributes
the engine joins on — N times with renamed ids (no approved links, so the engine has everything to propose), then times
`sdem link`'s engine and fails if it is slower than the limit. Usage: python scripts/engine_perf.py [copies] [max_seconds]
"""
import copy, json, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem.graph import FederatedGraph, LevelGraph  # noqa: E402
from sdem.metamodel import Metamodel  # noqa: E402
from sdem.rules_engine import RulesEngine  # noqa: E402
from sdem.store import GraphReader  # noqa: E402

copies = int(sys.argv[1]) if len(sys.argv) > 1 else 30
limit = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0
src = ROOT / 'examples' / 'payment-initiation'
FILES = ['a1-business.json', 'a2-service-domain.json', 'a3-application.json', 'a4-technology.json']
docs = {f: json.loads((src / f).read_text(encoding='utf-8')) for f in FILES}
ids = {i['id'] for d in docs.values() for i in d['instances']}


def ren(v, k):
    if isinstance(v, str) and v in ids: return f'{v}-{k}'
    if isinstance(v, list): return [ren(x, k) for x in v]
    if isinstance(v, dict): return {a: ren(b, k) for a, b in v.items()}
    return v


levels = []
for f, d in docs.items():
    o = copy.deepcopy(d); o['instances'] = []; o['relationships'] = []
    for k in range(copies):
        for i in d['instances']:
            j = ren(copy.deepcopy(i), k); j['id'] = f"{i['id']}-{k}"
            if k: j.pop('canonical_id', None)
            o['instances'].append(j)
        o['relationships'] += [ren(copy.deepcopy(r), k) for r in d.get('relationships', [])]
    levels.append(o)
mm = Metamodel.load()
reader = GraphReader(FederatedGraph([LevelGraph(d, mm) for d in levels], [{'registry_version': '0.4.0', 'metamodel_version': mm.version, 'mappings': []}], mm), 'synthetic')
n = sum(len(d['instances']) for d in levels)
t = time.time(); res = RulesEngine().infer(reader, {'id': 'PERF'}); took = time.time() - t
print(f'rules engine: {n} records, {len(res["proposals"])} proposals in {took:.1f}s (limit {limit:.0f}s)')
sys.exit(0 if took <= limit else 1)
