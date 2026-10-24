"""Generate the physical data model: one JSON Schema per concrete entity type, schema/entities/<level>/<Entity>.schema.json,
and its index docs/physical-data-model.md, from the Architecture Metamodel and the attribute record.

Each schema is standard JSON Schema 2020-12 using only keywords the built-in validator also checks (type, enum,
pattern, required, items, minimum, maximum), so adapters can validate an instance with any JSON Schema tool. Source
reference, reasoning and confidence travel with every property as `x-sdem-*` annotations. What a single-instance
schema cannot see (references, natural keys, cardinality) stays with `sdem-graph check` (sdem/conformance.py).
Usage: python -m sdem.physical [--check]
"""
import argparse, json
from collections import Counter
from pathlib import Path

from .conformance import definitions, model
from .metamodel import Metamodel, MM_DIR, ROOT

OUT = ROOT / 'schema' / 'entities'
DOC = ROOT / 'docs' / 'physical-data-model.md'
REPO = 'https://github.com/taumoeps/bian-sdem-framework'
DATE_PATTERN = r'^\d{4}-\d{2}-\d{2}$'


def _j(p): return json.loads(Path(p).read_text(encoding='utf-8'))


def _prop(a, group):
    t = a['type']
    if a['name'] == 'behavior_qualifier': p = {}  # string or null (an operation may have no qualifier); the validator has no type unions
    elif t == 'list<string>': p = {'type': 'array', 'items': {'type': 'string', **({'enum': a['values']} if a.get('values') else {})}}
    elif t == 'map<string,string>': p = {'type': 'object'}
    elif t == 'date': p = {'type': 'string', 'format': 'date', 'pattern': DATE_PATTERN}
    elif t in ('integer', 'boolean'): p = {'type': t}
    else: p = {'type': 'string', **({'enum': a['values']} if a.get('values') else {})}
    for k in ('minimum', 'maximum'):
        if k in a: p[k] = a[k]
    p['description'] = a['description']
    if a['status'] == 'deprecated': p['deprecated'] = True
    p['x-sdem-id'] = a['id']; p['x-sdem-group'] = group; p['x-sdem-kind'] = a.get('kind', 'value')
    if a.get('references'): p['x-sdem-references'] = a['references']
    p['x-sdem-source'] = a['reference']; p['x-sdem-reasoning'] = a['reasoning']; p['x-sdem-confidence'] = a['confidence']
    return p


def schema_for(mm, etype, core):
    e = mm.entities[etype]; _, common, _ = model(); byent = model()[0]
    defs = definitions(mm, etype); own = set(byent.get(etype, {}))
    group = lambda k: 'common' if k in common and k not in own and not any(k in byent.get(t, {}) for t in mm.ancestors(etype)) else ('specific' if k in own else 'inherited')
    props = {}
    for c in core:
        if c['name'] == 'attributes': continue
        p = dict(core_schema()[c['name']])
        if c['name'] == 'type': p = {'type': 'string', 'enum': [etype]}
        p['description'] = c['description']; p['x-sdem-source'] = c['reference']; p['x-sdem-reasoning'] = c['reasoning']; p['x-sdem-confidence'] = c['confidence']
        props[c['name']] = p
    attrs = {k: _prop(a, group(k)) for k, a in defs.items()}
    req = [k for k, a in defs.items() if a['required'] and a['status'] == 'active']
    props['attributes'] = {'type': 'object', 'description': 'common, inherited and entity-specific attributes', **({'required': req} if req else {}),
                           'properties': attrs, 'additionalProperties': True, 'x-sdem-note': 'undefined attributes are allowed here but reported as warnings by sdem-graph check'}
    r = e['reference']
    return {'$schema': 'https://json-schema.org/draft/2020-12/schema', '$id': f"{REPO}/schema/entities/{e['level']}/{etype.split('.')[1]}.schema.json",
            'title': etype, 'description': e['definition'], 'type': 'object', 'additionalProperties': False,
            'required': ['id', 'type', 'version', 'name'] + (['attributes'] if req else []), 'properties': props,
            'x-sdem-entity': {'level': e['level'], 'extends': e.get('extends'), 'identifier': (e.get('identifier') or {}).get('key'),
                              'source': {k: r.get(k) for k in ('standard', 'release', 'concept', 'locator', 'uri') if r.get(k)}, 'reasoning': e['reasoning'], 'confidence': e['confidence']},
            'x-sdem-generated-from': 'metamodel/a1…a4-*.json, metamodel/entity-attributes.json (python -m sdem.physical)'}


def core_schema():
    return _j(ROOT / 'schema' / 'level-model.schema.json')['$defs']['instance']['properties']


def render():
    mm = Metamodel.load(); rec = _j(MM_DIR / 'entity-attributes.json'); core = rec['core_fields']
    ents = [t for t, e in mm.entities.items() if not e.get('abstract') and not e.get('artefact')]
    files = {f"{mm.entities[t]['level']}/{t.split('.')[1]}.schema.json": schema_for(mm, t, core) for t in ents}
    rows, tot = [], Counter()
    for path, s in files.items():
        a = s['properties']['attributes']['properties']; g = Counter(p['x-sdem-group'] for p in a.values()); c = Counter(p['x-sdem-confidence'] for p in a.values())
        tot.update(c); rows.append(f"| `{s['title']}` | [`{path}`](../schema/entities/{path}) | {len(s['properties']) - 1} | {g['common']} | {g['inherited']} | {g['specific']} | {len(s['properties']['attributes'].get('required', []))} | {c['high']} / {c['medium']} / {c['low']} |")
    out = ['# SDEM — Physical Data Model', '',
           '> Generated by `python -m sdem.physical` from the Architecture Metamodel (`metamodel/a1…a4-*.json`) and the attribute record (`metamodel/entity-attributes.json`). Do not edit by hand; CI fails if it is stale.', '',
           '## What it is', '',
           'The **physical data model** is the logical data model written as files a tool can use: **one JSON Schema per entity type** that an export instance must satisfy. A tool adapter validates each record it exports against the schema for its type; `sdem-graph check` then checks what a single record cannot show on its own.', '',
           '| Layer | Document | Holds |', '|---|---|---|',
           '| Conceptual | [architecture-entity-design.md](architecture-entity-design.md) | the entity types and how they relate |',
           '| Logical | [logical-data-model.md](logical-data-model.md), [architecture-attribute-design.md](architecture-attribute-design.md) | identifiers, attributes, types, allowed values, references, cardinality, rules |',
           '| **Physical (this document)** | `schema/entities/<level>/<Entity>.schema.json` | the export format of each entity, validatable by any JSON Schema 2020-12 tool |', '',
           '## How the logical model maps to JSON Schema', '',
           '| Logical | JSON Schema |', '|---|---|',
           '| entity type | one schema file; `type` fixed to the entity name |',
           '| core field (`id`, `version`, `name`…) | top-level property; `id`, `type`, `version`, `name` required; no other top-level properties allowed |',
           '| attribute (common, inherited, specific) | property of `attributes`; required attributes listed in `attributes.required` |',
           '| text / list / map / boolean / integer | `string` / `array` of `string` / `object` / `boolean` / `integer` (with `minimum`/`maximum` where defined) |',
           '| date | `string`, `format: date`, pattern `YYYY-MM-DD` |',
           '| enumeration | `enum` |',
           '| reference | `string` (or array) plus `x-sdem-references` naming the target types; resolution is checked by `sdem-graph check` |',
           '| deprecated attribute | `deprecated: true` |',
           '| source reference, reasoning, confidence | `x-sdem-source`, `x-sdem-reasoning`, `x-sdem-confidence` on every property and in `x-sdem-entity` |', '',
           '## What the schemas do not check', '',
           'A schema sees one record. These rules need the whole export or estate and are enforced by `sdem-graph check` ([logical rules](logical-data-model.md)): references resolve (LC-07 error, LC-08 warning), natural keys are unique (LC-09), cardinality (LC-10, LC-10m), within-level and cross-level relationships (LC-03, LC-11). Attributes not in the model are accepted by the schema and reported as warnings.', '',
           f"## Schemas ({len(files)} entity types)", '',
           'Artefact types (BOM model, wireframe, Semantic API) and abstract types are not export instance types and have no schema.', '',
           '| Entity | Schema | Core fields | Common | Inherited | Specific | Required attributes | Attribute confidence (H / M / L) |', '|---|---|---|---|---|---|---|---|'] + rows + [
           '', f"Attribute definitions across all schemas: **{tot['high']} high, {tot['medium']} medium, {tot['low']} low** (the 11 common attributes are counted in every schema).", '',
           '## Using a schema', '', '```bash',
           '# any JSON Schema 2020-12 validator, e.g. check-jsonschema',
           'check-jsonschema --schemafile schema/entities/A1/BusinessProcess.schema.json my-process.json', '',
           '# then the whole export and estate',
           'python -m sdem.graph check exports/a*.json exports/mappings.json', '```', '']
    return files, '\n'.join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem-physical', description='Generate the per-entity JSON Schemas and docs/physical-data-model.md.')
    ap.add_argument('--check', action='store_true'); args = ap.parse_args(argv)
    files, doc = render(); want = {OUT / k: json.dumps(v, indent=2, ensure_ascii=False) + '\n' for k, v in files.items()}; want[DOC] = doc
    if args.check:
        stale = [p for p, t in want.items() if not p.exists() or p.read_text(encoding='utf-8') != t]
        stale += [p for p in OUT.glob('*/*.schema.json') if p not in want]
        for p in stale: print(f'STALE: {p.relative_to(ROOT)} — regenerate with python -m sdem.physical')
        if not stale: print(f'physical data model: up to date ({len(files)} schemas)')
        return 1 if stale else 0
    for p in OUT.glob('*/*.schema.json'):
        if p not in want: p.unlink()
    for p, t in want.items():
        p.parent.mkdir(parents=True, exist_ok=True); p.write_text(t, encoding='utf-8')
    print(f'wrote {len(files)} schemas and {DOC.relative_to(ROOT)}'); return 0


if __name__ == '__main__':
    raise SystemExit(main())
