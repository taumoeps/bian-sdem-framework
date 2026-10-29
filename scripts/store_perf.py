"""Graph store performance check (docs/design/graph-store-spec.md GS-X-02, AT-11).

Generates a synthetic estate by replicating examples/reference-structure (every within-level row exercised) until it
reaches the target size, then times build, open and a trace. Usage: python scripts/store_perf.py [target_nodes]
"""
import json, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem.metamodel import Metamodel  # noqa: E402
from sdem.store import GraphReader, build  # noqa: E402

target = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
src = {p.name: json.loads(p.read_text(encoding='utf-8')) for p in (ROOT / 'examples' / 'reference-structure').glob('a[1-4]-*.json')}
per = sum(len(d['instances']) for d in src.values()); copies = -(-target // per)
tmp = Path(tempfile.mkdtemp(prefix='sdem-perf-')); paths = []
for name, d in src.items():
    out = dict(d, instances=[], relationships=[])
    for c in range(copies):
        sfx = f'-c{c}'
        for i in d['instances']:
            j = json.loads(json.dumps(i)); j['id'] += sfx; j['name'] += sfx
            for k, v in list((j.get('attributes') or {}).items()):
                if isinstance(v, str) and v.startswith('RS-'): j['attributes'][k] = v + sfx
                elif isinstance(v, list): j['attributes'][k] = [x + sfx if isinstance(x, str) and x.startswith('RS-') else x for x in v]
            out['instances'].append(j)
        out['relationships'] += [dict(r, source=r['source'] + sfx, target=r['target'] + sfx) for r in d['relationships']]
    (tmp / name).write_text(json.dumps(out), encoding='utf-8'); paths.append(str(tmp / name))
(tmp / 'mappings.json').write_text(json.dumps({'registry_version': '0.4.0', 'metamodel_version': Metamodel.load().version, 'mappings': []}), encoding='utf-8'); paths.append(str(tmp / 'mappings.json'))
nodes = copies * per; edges = copies * sum(len(d['relationships']) for d in src.values())
t = time.perf_counter(); e = build(paths, tmp / 'graph'); tb = time.perf_counter() - t
assert e['result'] == 'accepted', e['errors'][:3]
t = time.perf_counter(); r = GraphReader.from_store(tmp / 'graph'); to = time.perf_counter() - t
start = r.nodes(level='A4')[0]['id']
t = time.perf_counter(); r.fg.trace(start, 'up', follow_composition=True); tt = time.perf_counter() - t
print(json.dumps({'nodes': nodes, 'edges': edges, 'build_s': round(tb, 2), 'open_s': round(to, 2), 'trace_s': round(tt, 2),
                  'targets': {'build_s': 10, 'open_s': 2, 'trace_s': 1}, 'pass': tb <= 10 and to <= 2 and tt <= 1}, indent=2))
