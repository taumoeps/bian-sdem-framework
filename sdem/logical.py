"""Render docs/logical-data-model.md — the SDEM Logical Data Model (the platform-independent model).

Assembled from the Architecture Metamodel records: entity types and their identifiers (metamodel/a1…a4-*.json),
attributes with kinds, allowed values and references (metamodel/entity-attributes.json), within-level relationships
with cardinality (metamodel/level-relationships.json) and the relationship type catalogue (schema/relationship-types.json).
It also measures the example estates against the model. Regenerate with `python -m sdem.logical`; the tests check it.
"""
from pathlib import Path
from collections import Counter
import argparse, glob, json
from sdem.metamodel import Metamodel, MM_DIR, LEVEL_FILES
from sdem.terms import apply as _terms

ROOT = MM_DIR.parent
DOC = ROOT / 'docs' / 'logical-data-model.md'
NAMES = {'A1': 'A1 Business Architecture', 'A2': 'A2 Service Domain Architecture', 'A3': 'A3 Application Architecture', 'A4': 'A4 Technology Architecture'}
LEFT = {'1..1': '||', '0..1': '|o', '0..*': '}o', '1..*': '}|'}
RIGHT = {'1..1': '||', '0..1': 'o|', '0..*': 'o{', '1..*': '|{'}
TY = {'string': str, 'list<string>': list, 'map<string,string>': dict}

CONSTRAINTS = [
 ('LC-01', 'Instance identity', '`id` + `version` is unique within a level export', 'enforced', '`sdem-graph check`'),
 ('LC-02', 'Entity typing', 'every instance\'s `type` is a concrete, non-artefact entity type of the export\'s level', 'enforced', '`sdem-graph check`'),
 ('LC-03', 'Within-level relationships', 'every relationship matches a within-level row of its level (through inheritance), or is `association`', 'enforced', '`sdem-graph check`'),
 ('LC-04', 'Required attributes', 'every attribute marked required is present', 'not enforced', 'designed; next build'),
 ('LC-05', 'Attribute types', 'every attribute value has its declared type', 'not enforced', 'designed; next build'),
 ('LC-06', 'Enumerations', 'enumerated attributes (`action_term`, `method`, `lifecycle_status`) take an allowed value', 'not enforced', 'designed; next build'),
 ('LC-07', 'Same-level references', 'a reference attribute whose target is in the same level names an instance of the declared type in the same export', 'not enforced', 'designed; next build'),
 ('LC-08', 'Cross-level references', 'a reference attribute whose target is in another level names an instance of the declared type in the estate', 'not enforced', 'resolved by the inference engine (join keys); never a federated edge'),
 ('LC-09', 'Natural keys', 'no two instances of a type share their identifier key within an export', 'not enforced', 'designed; needed by the export diff'),
 ('LC-10', 'Cardinality — maximum', 'no instance exceeds the stated maximum of a BIAN or ArchiMate-composition row (e.g. a service group in two Service Domains)', 'not enforced', 'designed as an error; next build'),
 ('LC-10m', 'Cardinality — minimum (completeness)', 'an instance meets the stated minimum (e.g. a Service Domain has a control record); exports may legitimately be partial selections of BIAN, so a shortfall is a completeness warning, not an error', 'not enforced', 'designed as a warning; next build'),
 ('LC-11', 'Cross-level relationship ends', 'both ends of every registry record resolve to instances of the right type, level and version', 'enforced', '`sdem-graph check`'),
 ('LC-12', 'Registry immutability', 'approved, rejected and superseded registry records are never edited', 'enforced', '`sdem-diff`'),
 ('LC-13', 'Deprecated attributes', 'deprecated attributes raise a warning', 'not enforced', 'designed; next build'),
]


def _j(p): return json.loads(Path(p).read_text(encoding='utf-8'))


def conformance(mm, attrs):
    """Measure the example estates against LC-04 … LC-09 (the constraints not yet enforced)."""
    byent = {}
    for a in attrs: byent.setdefault(a['entity'], {})[a['name']] = a
    res = Counter(); estates = 0; instances = 0
    for est in sorted(glob.glob(str(ROOT / 'examples' / '*') + '/')):
        if 'reference-structure' in est: continue
        estates += 1; idx = {}
        files = glob.glob(est + 'a[1-4]-*.json')
        for f in files:
            for i in _j(f)['instances']: idx[i['id']] = i['type']
        for f in files:
            keys = Counter()
            for i in _j(f)['instances']:
                instances += 1
                defs = {}
                for t in list(reversed(list(mm.ancestors(i['type'])))) + [i['type']]: defs.update(byent.get(t, {}))
                at = i.get('attributes') or {}
                for k, a in defs.items():
                    if a['required']:
                        res['LC-04 checked'] += 1; res['LC-04 failed'] += k not in at
                for k, v in at.items():
                    a = defs.get(k)
                    if not a: res['undefined'] += 1; continue
                    if a['status'] == 'deprecated': res['LC-13 failed'] += 1
                    want = TY.get(a['type'])
                    if want: res['LC-05 checked'] += 1; res['LC-05 failed'] += not (isinstance(v, want) or (v is None and k == 'behavior_qualifier'))
                    if a.get('values'): res['LC-06 checked'] += 1; res['LC-06 failed'] += v not in a['values']
                    if a.get('kind') == 'reference':
                        same = all(t.startswith(i['type'][:2]) for t in a['references'])
                        for x in (v if isinstance(v, list) else [v]):
                            t = idx.get(x); hit = bool(t) and any(mm.is_a(t, r) for r in a['references'])
                            lc = 'LC-07' if same else 'LC-08'
                            res[f'{lc} checked'] += 1; res[f'{lc} failed'] += not hit
                if i.get('lifecycle_status'):
                    res['LC-06 checked'] += 1; res['LC-06 failed'] += i['lifecycle_status'] not in ('planned', 'active', 'deprecated', 'retired')
                e = mm.entities[i['type']]; key = (e.get('identifier') or {}).get('key') or []
                if key and all(k in i or k in at for k in key):
                    keys[(i['type'],) + tuple(json.dumps(i.get(k, at.get(k)), sort_keys=True) for k in key)] += 1
            dup = sum(n - 1 for n in keys.values() if n > 1)
            res['LC-09 checked'] += len(keys); res['LC-09 failed'] += dup
            doc = _j(f); itype = {i['id']: i['type'] for i in doc['instances']}
            for c in _j(MM_DIR / 'level-relationships.json')['constraints']:
                cd = c.get('cardinality') or {}
                if c['level'] != doc['level'] or cd.get('basis') == 'SDEM default': continue
                links = [(r['source'], r['target']) for r in doc['relationships'] if r['kind'] == c['kind'] and r['source'] in itype and r['target'] in itype
                         and mm.is_a(itype[r['source']], c['source_type']) and mm.is_a(itype[r['target']], c['target_type'])]
                for side, card, ends in (('src', cd['source_per_target'], [t for t in itype if mm.is_a(itype[t], c['target_type'])]),
                                         ('tgt', cd['target_per_source'], [x for x in itype if mm.is_a(itype[x], c['source_type'])])):
                    lo, hi = card.split('..')
                    for inst_id in ends:
                        cnt = sum(1 for a, b in links if (b if side == 'src' else a) == inst_id)
                        res['LC-10 checked'] += 1; res['LC-10m checked'] += 1
                        res['LC-10 failed'] += hi != '*' and cnt > int(hi)
                        res['LC-10m failed'] += cnt < int(lo)
    return estates, instances, res


def render():
    mm = Metamodel.load()
    ents = [e for f in LEVEL_FILES for e in _j(MM_DIR / f)['entities']]
    rec = _j(MM_DIR / 'entity-attributes.json'); attrs = rec['attributes']; core = rec['core_fields']
    lr = _j(MM_DIR / 'level-relationships.json'); reg = _j(ROOT / 'schema' / 'relationship-types.json')['relationships']
    byent = {}
    for a in attrs: byent.setdefault(a['entity'], []).append(a)
    alias = lambda t: t.replace('.', '_')
    out = ['# SDEM Logical Data Model', '',
           'Generated by `python -m sdem.logical` from the Architecture Metamodel records; the test suite checks it is current. This is the **platform-independent model** of the four architectures: entity types, their **identifiers**, **attributes** with types, allowed values and **references**, **relationships with cardinality**, and the **constraints** that bind them. It is assembled from [`architecture-entity-design.md`](architecture-entity-design.md), [`architecture-attribute-design.md`](architecture-attribute-design.md) and [`relationships-planning.md`](relationships-planning.md); the physical models (export JSON Schemas, a graph store schema) are to be generated from it.', '',
           '## 1. Model-driven layers', '', '| Layer | Content | Status |', '|---|---|---|',
           '| Conceptual | entity types and the relationships between them | complete |',
           f"| **Logical (this document)** | identifiers, typed attributes, allowed values, references, cardinality, constraints | **designed**; {sum(1 for c in CONSTRAINTS if c[3] == 'enforced')} of {len(CONSTRAINTS)} constraints enforced |",
           '| Physical | per-entity export JSON Schemas; graph store schema (DEC-01) | not generated yet — next build |', '',
           '## 2. Building blocks', '', '| Element | Defined in | Count |', '|---|---|---|',
           f"| Entity types | entity records | {len(ents)} ({sum(1 for e in ents if e.get('abstract'))} abstract, {sum(1 for e in ents if e.get('artefact'))} artefacts) |",
           f"| Core fields on every instance | `entity-attributes.json` › core_fields | {len(core)} |",
           f"| Attributes | `entity-attributes.json` › attributes | {len(attrs)}: " + ', '.join(f"{v} {k}" for k, v in Counter(a.get('kind', 'value') for a in attrs).most_common()) + ' |',
           f"| Within-level relationships | `level-relationships.json` | {len(lr['constraints'])}, each with cardinality |",
           f"| Cross-level relationship types | `relationship-types.json` | {len(reg)} |",
           f"| Constraints | this model | {len(CONSTRAINTS)} |", '',
           '## 3. Identifiers', '',
           'Every instance is identified by `id` (unique within its level, permanent, never reused) and `version`; a relationship end pins both. The **natural key** makes an instance unique *as a thing* — what the export diff uses to spot duplicates and re-keys.', '',
           '| Entity type | Natural key | Basis | Reasoning |', '|---|---|---|---|']
    for e in ents:
        idf = e.get('identifier') or {}
        if idf.get('key') and idf['key'] != ['name']:
            out.append(f"| `{e['type']}` | {', '.join(f'`{k}`' for k in idf['key'])} | {idf['basis']} | {idf['reasoning']} |")
    out += [f"| all other concrete types ({sum(1 for e in ents if (e.get('identifier') or {}).get('key') == ['name'])}) | `name` | SDEM | no standard key; a unique name within the export is recommended |", '',
            '## 4. Core fields', '', '| Field | Type | Required | Allowed values |', '|---|---|---|---|']
    out += [f"| `{c['name']}` | {c['type']} | {'yes' if c['required'] else 'no'} | {', '.join(c.get('values', [])) or '—'} |" for c in core]
    vals = [a for a in attrs if a.get('values')]
    out += ['', '## 5. Enumerations', '', '| Attribute | Allowed values | Source |', '|---|---|---|']
    out += [f"| `{a['entity']}.{a['name']}` | {', '.join(a['values'])} | {a['values_source']} |" for a in vals]
    out += ['| core `lifecycle_status` | planned, active, deprecated, retired | SDEM |', '| relationship `kind` | ' + ', '.join(k['kind'] for k in lr['kinds']) + ' | ArchiMate 3.2 |', '']
    xref = [a for a in attrs if a.get('kind') == 'reference' and a['reference_scope'].startswith('cross')]
    out += ['## 6. Cross-level references (join keys)', '',
            f'{len(xref)} reference attributes point *across* architectures. They are not relationships: they are the data the inference engine joins on to propose registry records (for example `deployed_on` → a `DEPLOYED_ON` record). Approved records, not these attributes, become federated edges.', '',
            '| Attribute | References | Read by |', '|---|---|---|']
    out += [f"| `{a['entity']}.{a['name']}` | {', '.join(f'`{t}`' for t in a['references'])} | {a['read_by']} |" for a in xref]
    out.append('')
    n = 6
    for lvl in ('A1', 'A2', 'A3', 'A4'):
        n += 1
        le = [e for e in ents if e['level'] == lvl]
        rows = [c for c in lr['constraints'] if c['level'] == lvl]
        out += [f'## {n}. {NAMES[lvl]}', '', f'### {n}.1 Entity–relationship diagram', '',
                'Cardinality markers follow crow\'s-foot notation; labels carry the within-level row ID and kind. Inheritance is listed in the table below (an ER diagram has no notation for it).', '', '```mermaid', 'erDiagram']
        for e in le:
            fields = [f"        string id PK", "        string version PK"] + [f"        {'list' if a['type'].startswith('list') else 'map' if a['type'].startswith('map') else 'string'} {a['name']}{' FK' if a.get('kind') == 'reference' else ''}" for a in byent.get(e['type'], [])]
            out += [f"    {alias(e['type'])} {{"] + fields + ['    }']
        for c in rows:
            cd = c['cardinality']
            out.append(f"    {alias(c['source_type'])} {LEFT[cd['source_per_target']]}--{RIGHT[cd['target_per_source']]} {alias(c['target_type'])} : \"{c['id']} {c['kind']}\"")
        out += ['```', '', f'### {n}.2 Entities and attributes', '',
                '| Entity type | Kind | Identifier | Attributes (`*` required, `→` reference) |', '|---|---|---|---|']
        for e in le:
            kind = 'abstract' if e.get('abstract') else 'artefact' if e.get('artefact') else 'concrete'
            if e.get('extends'): kind += f", is-a `{e['extends']}`"
            idf = ', '.join((e.get('identifier') or {}).get('key') or []) or '—'
            at = '; '.join(f"`{a['name']}`{'*' if a['required'] else ''} {a['type']}" + (f" → {', '.join(t.split('.')[1] for t in a['references'])}" if a.get('kind') == 'reference' else '') + (' *(deprecated)*' if a['status'] == 'deprecated' else '') for a in byent.get(e['type'], [])) or '— (core fields only)'
            out.append(f"| `{e['type']}` | {kind} | {idf} | {at} |")
        out += ['', f'### {n}.3 Relationships and cardinality', '', '| ID | Source | Kind | Target | Source per target | Target per source | Basis |', '|---|---|---|---|---|---|---|']
        for c in rows:
            cd = c['cardinality']
            out.append(f"| {c['id']} | `{c['source_type']}` | {c['kind']} | `{c['target_type']}` | {cd['source_per_target']} | {cd['target_per_source']} | {cd['basis']} |")
        out.append('')
    out += [f'## {n + 1}. Cross-level relationship types', '', 'Registry records connect adjacent architectures only; level-skipping answers are paths.', '',
            '| Type | Source → target | Relationship | Cardinality | Required evidence |', '|---|---|---|---|---|']
    out += [f"| {x['mapping_type_id']} | `{x['source_type']}` → `{x['target_type']}` | `{x['relationship']}` | {x['cardinality'].replace('_', ' ')} | {', '.join(x['required_evidence'])} |" for x in reg]
    est, inst, res = conformance(mm, attrs)
    out += ['', f'## {n + 2}. Constraints', '', '| ID | Constraint | Rule | Status | By |', '|---|---|---|---|---|']
    out += [f"| {c[0]} | {c[1]} | {c[2]} | **{c[3]}** | {c[4]} |" for c in CONSTRAINTS]
    out += ['', f'## {n + 3}. Conformance of the example estates', '',
            f"The {est} example estates ({inst} instances) measured against the constraints not yet enforced. " + ('No errors' if all(res[f'{lc} failed'] == 0 for lc in ('LC-04', 'LC-05', 'LC-06', 'LC-07', 'LC-08', 'LC-09', 'LC-10')) else 'Errors are listed below') + f"; {res['LC-10m failed']} completeness warning(s), where an example exports part of BIAN's structure (a business domain without its area, a business object without attribute instances, a stub Service Domain without its groups or control record)" + (f"; {res['LC-13 failed']} instance(s) still use a deprecated attribute" if res['LC-13 failed'] else '') + '.', '',
            '| Constraint | Values checked | Failures |', '|---|---|---|']
    for lc in ('LC-04', 'LC-05', 'LC-06', 'LC-07', 'LC-08', 'LC-09', 'LC-10', 'LC-10m'):
        out.append(f"| {lc}{' (warning)' if lc == 'LC-10m' else ''} | {res[lc + ' checked']} | {res[lc + ' failed']} |")
    out += [f"| LC-13 (deprecated in use) | — | {res['LC-13 failed']} |", f"| attributes not in the model | — | {res['undefined']} |", '',
            f'## {n + 4}. Basis of the logical decisions', '',
            '| Decision | Count | Basis |', '|---|---|---|']
    cb = Counter(c['cardinality']['basis'] for c in lr['constraints'])
    CB = {'BIAN': 'stated by BIAN', 'SDEM default': 'no standard multiplicity; left open', 'SDEM reading': "SDEM's reading of a BIAN page"}
    out += [f"| Cardinality — {k} | {v} | {CB.get(k, 'a part belongs to at most one whole (ArchiMate)')} |" for k, v in cb.most_common()]
    ib = Counter((e.get('identifier') or {}).get('basis') for e in ents if (e.get('identifier') or {}).get('key'))
    out += [f"| Natural keys — {k} | {v} | {'BIAN concept ids and operation naming' if k == 'BIAN' else 'path and method unique per API' if k == 'OpenAPI' else 'SDEM recommendation'} |" for k, v in ib.most_common()]
    out += ['', '## Next', '', '1. **Generate the physical export model**: one JSON Schema per entity type from this model, and make `sdem-graph check` enforce LC-04 … LC-10 and LC-13.',
            '2. **Approve the model as a baseline** (`SDEM-METAMODEL-0.8`) after an independent review.',
            '3. **Graph store schema** when a persistent store is chosen (knowledge-graph spec DEC-01).', '']
    return _terms('\n'.join(out) + '\n')


def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem-logical', description='Render docs/logical-data-model.md from the Architecture Metamodel records.')
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args(argv)
    text = render()
    if args.check:
        ok = DOC.exists() and DOC.read_text(encoding='utf-8') == text
        print('up to date' if ok else 'STALE: regenerate with python -m sdem.logical'); return 0 if ok else 1
    DOC.write_text(text, encoding='utf-8'); print(f'wrote {DOC}'); return 0


if __name__ == '__main__':
    raise SystemExit(main())
