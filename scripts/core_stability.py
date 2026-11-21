"""The core's stability, measured (the owner, 2026-11-21: "the objective is to have a stable core").

    python scripts/core_stability.py <workspace>          # one snapshot, as JSON

A snapshot is the metamodel SDEM loads for a workspace — every layer, entity type, attribute, link type between layers and rule inside
a layer — with every name read as its stable id (metamodel/identity.json), so a renumbering (BIAN on: Application A3 → A4) can neither
hide nor fake a change; and the design's own data (each core layer file's bytes, the links between core layers). Each item is marked
core or extension: core when every type it names is one of the core layers' (business, data, application, technology).

tests/test_core_stability.py takes a snapshot of one workspace as extensions are switched on and off — none; BIAN; BIAN and security;
security off; BIAN off — and holds the core identical throughout, the extensions' additions their own, and the end equal to the start.
Standard library only; made-up data only."""
import hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CORE = ('business', 'data', 'application', 'technology')


def snapshot(ws):
    from sdem import profile as P
    from sdem.metamodel import Metamodel
    from sdem.validate import load_registry
    from sdem import conformance, identity as I, parts
    ws = Path(ws)
    P.activate_from(ws)
    tid = lambda t: (I.type_id(t) or t) if isinstance(t, str) else t
    lid = lambda c: (I.layer_id(c) or c) if isinstance(c, str) else c
    mm = Metamodel.load()
    ents = {tid(t): {'level': lid(e.get('level')), 'extends': tid(e.get('extends')), 'abstract': bool(e.get('abstract')), 'artefact': bool(e.get('artefact')),
                     'definition': e.get('definition')} for t, e in mm.entities.items()}
    byent, common, _ = conformance.model()
    STRUCT = ('id', 'entity', 'name', 'type', 'required', 'status', 'kind', 'references', 'values', 'minimum', 'maximum', 'required_unless', 'enforcement')
    norm = lambda k, v: tid(v) if k == 'entity' else [tid(x) for x in v] if k == 'references' and isinstance(v, list) else v   # type names read as ids
    attrs = {f'{tid(t)}.{n}': {k: norm(k, a[k]) for k in STRUCT if k in a} for t, d in byent.items() for n, a in d.items()}
    text = {f'{tid(t)}.{n}': json.dumps({k: v for k, v in a.items() if k not in STRUCT}, sort_keys=True, ensure_ascii=False) for t, d in byent.items() for n, a in d.items()}   # the prose: descriptions, sources, approvals
    reg = load_registry()
    links = {r['mapping_type_id']: {'source': tid(r['source_type']), 'relationship': r['relationship'], 'target': tid(r['target_type']),
                                    'evidence': sorted(r.get('required_evidence') or []), 'perspective': r.get('perspective'), 'cardinality': r.get('cardinality'),
                                    'status': 'deprecated' if r in reg.get('deprecated_relationships', []) else 'active'}
             for r in reg['relationships'] + reg.get('deprecated_relationships', [])}
    rules = {c['id']: {'level': lid(c.get('level')), 'source': tid(c['source_type']), 'kind': c['kind'], 'target': tid(c['target_type']),
                       'cardinality': c.get('cardinality')} for c in mm.relationships['constraints']}
    files = {}
    for l in CORE:
        f = ws / I.F(l)
        if f.exists() and not (l == "data" and not parts.migrated()): files[l] = hashlib.sha256(f.read_bytes()).hexdigest()
    maps = json.loads((ws / 'mappings.json').read_text(encoding='utf-8')).get('mappings', []) if (ws / 'mappings.json').exists() else []
    core_maps = sorted(json.dumps({**m, 'source': {**m['source'], 'type': tid(m['source']['type'])}, 'target': {**m['target'], 'type': tid(m['target']['type'])}}, sort_keys=True)
                       for m in maps if all(str(tid(m[e]['type'])).split('.')[0] in CORE for e in ('source', 'target')))
    return {'layers': list(I.stack()), 'common_attributes': sorted(common), 'entities': ents, 'attributes': attrs, 'attribute_text': text, 'link_types': links,
            'rules': rules, 'data': {'files': files, 'links_between_core_layers': hashlib.sha256('\n'.join(core_maps).encode()).hexdigest(), 'links': len(core_maps)}}


def is_core(kind, key, item):
    """An item is core when every type it names, and its layer, are the core layers'."""
    names = {'entities': lambda: [key, item.get('extends') or key], 'attributes': lambda: [item.get('entity') or key.rsplit('.', 1)[0]],
             'link_types': lambda: [item['source'], item['target']], 'rules': lambda: [item['source'], item['target']]}[kind]()
    layers = [str(n).split('.')[0] for n in names] + ([item['level']] if kind in ('entities', 'rules') and item.get('level') else [])
    return all(x in CORE for x in layers)


def split(snap):
    """{kind: (core items, extension items)} for each part of the metamodel."""
    return {k: ({i: v for i, v in snap[k].items() if is_core(k, i, v)}, {i: v for i, v in snap[k].items() if not is_core(k, i, v)})
            for k in ('entities', 'attributes', 'link_types', 'rules')}


if __name__ == '__main__':
    print(json.dumps(snapshot(sys.argv[1]), indent=1, sort_keys=True, ensure_ascii=False))
