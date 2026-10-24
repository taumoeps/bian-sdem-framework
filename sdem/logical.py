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
TY = {'string': str, 'list<string>': list, 'map<string,string>': dict, 'integer': int, 'boolean': bool, 'date': str}

CONSTRAINTS = [
 ('LC-01', 'Instance identity', '`id` + `version` is unique within a level export', 'enforced', '`sdem-graph check`'),
 ('LC-02', 'Entity typing', 'every instance\'s `type` is a concrete, non-artefact entity type of the export\'s level', 'enforced', '`sdem-graph check`'),
 ('LC-03', 'Within-level relationships', 'every relationship matches a within-level row of its level (through inheritance), or is `association`', 'enforced', '`sdem-graph check`'),
 ('LC-04', 'Required attributes', 'every attribute marked required is present', 'enforced', '`sdem-graph check` (error)'),
 ('LC-05', 'Attribute types', 'every attribute value has its declared type', 'enforced', '`sdem-graph check` (error)'),
 ('LC-06', 'Enumerations', 'enumerated attributes (`action_term`, `method`, `lifecycle_status`) take an allowed value', 'enforced', '`sdem-graph check` (error)'),
 ('LC-07', 'Same-level references', 'a reference attribute whose target is in the same level names an instance of the declared type in the same export', 'enforced', '`sdem-graph check` (error)'),
 ('LC-08', 'Cross-level references', 'a reference attribute whose target is in another level names an instance of the declared type in the estate', 'enforced as a warning', '`sdem-graph check` (warning when the target level is loaded); resolved by the inference engine; never a federated edge'),
 ('LC-09', 'Natural keys', 'no two instances of a type share their identifier key within an export', 'enforced', '`sdem-graph check` (error)'),
 ('LC-10', 'Cardinality — maximum', 'no instance exceeds the stated maximum of a BIAN or ArchiMate-composition row (e.g. a service group in two Service Domains)', 'enforced', '`sdem-graph check` (error)'),
 ('LC-10m', 'Cardinality — minimum (completeness)', 'an instance meets the stated minimum (e.g. a Service Domain has a control record); exports may legitimately be partial selections of BIAN, so a shortfall is a completeness warning, not an error', 'enforced', '`sdem-graph check` (warning)'),
 ('LC-11', 'Cross-level relationship ends', 'both ends of every registry record resolve to instances of the right type, level and version', 'enforced', '`sdem-graph check`'),
 ('LC-12', 'Registry immutability', 'approved, rejected and superseded registry records are never edited', 'enforced', '`sdem-diff`'),
 ('LC-13', 'Deprecated attributes', 'deprecated attributes raise a warning', 'enforced', '`sdem-graph check` (warning)'),
]


def _j(p): return json.loads(Path(p).read_text(encoding='utf-8'))


def conformance(mm, attrs=None, common=None):
    """Measure the example estates with the enforced conformance checks (sdem/conformance.py)."""
    from .conformance import check_level, estate_index
    res = Counter(); estates = 0; instances = 0
    for est in sorted(glob.glob(str(ROOT / 'examples' / '*') + '/')):
        if 'reference-structure' in est: continue
        estates += 1; docs = [_j(f) for f in sorted(glob.glob(est + 'a[1-4]-*.json'))]; index = estate_index(docs)
        for d in docs:
            instances += len(d['instances']); res.update(check_level(d, mm, index)[2])
    return estates, instances, res


def render():
    mm = Metamodel.load()
    ents = [e for f in LEVEL_FILES for e in _j(MM_DIR / f)['entities']]
    rec = _j(MM_DIR / 'entity-attributes.json'); attrs = rec['attributes']; core = rec['core_fields']; common = rec.get('common_attributes', [])
    lr = _j(MM_DIR / 'level-relationships.json'); reg = _j(ROOT / 'schema' / 'relationship-types.json')['relationships']
    byent = {}
    for x in attrs: byent.setdefault(x['entity'], []).append(x)
    alias = lambda t: t.replace('.', '_')
    short = lambda t: t.split('.')[1]
    CARD = {'1..1': 'exactly one', '0..1': 'at most one', '0..*': 'any number', '1..*': 'one or more'}
    TYPE = {'string': 'text', 'list<string>': 'list', 'map<string,string>': 'name map'}

    out = ['# SDEM Logical Data Model', '',
           'Generated by `python -m sdem.logical` from the Architecture Metamodel records; the test suite checks it is current.', '',
           '## What this is', '',
           'A **data model** says, for each kind of thing an architecture holds: **what it is**, **how one is identified**, **what fields it has**, and **what it links to**. This document is that model for the four architectures, one section per architecture and **one card per entity**. Everything else — the rules, the allowed values, where each decision comes from, and how the example data measures up — is at the end.', '',
           '### Every entity also has these fields', '',
           'Every instance of every entity carries the same core fields, so the cards below do not repeat them:', '',
           '| Field | Type | Required | Meaning |', '|---|---|---|---|']
    out += [f"| `{c['name']}` | {c['type']} | {'yes' if c['required'] else 'no'} | {c['description']} |" for c in core]
    if common:
        out += ['', 'and these common attributes (approved 2026-10-24; optional):', '', '| Attribute | Type | Allowed values / refers to | Meaning |', '|---|---|---|---|']
        out += [f"| `{c['name']}` | {c['type']} | {(', '.join(c['values']) if c.get('values') else ('refers to ' + ', '.join(c['references'])) if c.get('references') else '—')} | {c['description']} |" for c in common]
    out += ['', '### How to read a card', '',
            '- **Identified by** — besides `id`, the fields that make it unique as a real-world thing.',
            '- **Fields** — the entity\'s own fields. *Required* fields must be present. A field that **refers to** another entity holds that entity\'s `id`; when it points into another architecture it is a *join key* the inference engine uses, not a link in the graph.',
            '- **Links** — the relationships allowed with other entities in the same architecture, with how many are allowed on each side.', '']
    n = 0
    for lvl in ('A1', 'A2', 'A3', 'A4'):
        n += 1
        le = [e for e in ents if e['level'] == lvl]
        rows = [c for c in lr['constraints'] if c['level'] == lvl]
        out += [f'## {n}. {NAMES[lvl]}', '', f'{len(le)} entities. The diagram shows the entities, their key fields and references, and the links between them.', '', '```mermaid', 'erDiagram']
        for e in le:
            fields = ["        string id PK"] + [f"        {'list' if x['type'].startswith('list') else 'map' if x['type'].startswith('map') else x['type'] if x['type'] in ('integer', 'boolean', 'date') else 'string'} {x['name']}{' FK' if x.get('kind') == 'reference' else ''}" for x in byent.get(e['type'], [])]
            out += [f"    {alias(e['type'])} {{"] + fields + ['    }']
        for c in rows:
            cd = c['cardinality']
            out.append(f"    {alias(c['source_type'])} {LEFT[cd['source_per_target']]}--{RIGHT[cd['target_per_source']]} {alias(c['target_type'])} : \"{c['kind']}\"")
        out += ['```', '']
        for e in le:
            kind = 'abstract — never instantiated' if e.get('abstract') else 'artefact — a document, never instantiated' if e.get('artefact') else 'entity'
            out += [f"### `{e['type']}`", '', f"*{kind}*" + (f" · a kind of `{e['extends']}` and inherits its fields" if e.get('extends') else ''), '', e['definition'], '']
            idf = e.get('identifier') or {}
            if idf.get('key'):
                out += [f"**Identified by:** {', '.join(f'`{k}`' for k in idf['key'])} — {idf['reasoning']}", '']
            fl = byent.get(e['type'], [])
            if fl:
                out += ['**Fields**', '', '| Field | Type | Required | Meaning | Refers to |', '|---|---|---|---|---|']
                for x in fl:
                    ref = ', '.join(f'`{t}`' for t in x.get('references', [])) + (' *(join key)*' if x.get('kind') == 'reference' and x['reference_scope'].startswith('cross') else '') if x.get('kind') == 'reference' else ('one of: ' + ', '.join(x['values']) if x.get('values') else '—')
                    out.append(f"| `{x['name']}`{' *(deprecated)*' if x['status'] == 'deprecated' else ''} | {TYPE.get(x['type'], x['type'])} | {'yes' if x['required'] else 'no'} | {x['description']} | {ref} |")
                out.append('')
            else:
                out += ['**Fields:** core fields only.', '']
            links = [c for c in rows if c['source_type'] == e['type'] or c['target_type'] == e['type']]
            if links:
                out += ['**Links**', '', '| Link | With | How many |', '|---|---|---|']
                for c in links:
                    cd = c['cardinality']
                    if c['source_type'] == e['type'] and c['target_type'] == e['type']:
                        out.append(f"| {c['kind']} (with itself) | `{short(e['type'])}` | {CARD[cd['target_per_source']]} |")
                    elif c['source_type'] == e['type']:
                        out.append(f"| {c['kind']} → | `{short(c['target_type'])}` | {CARD[cd['target_per_source']]} |")
                    else:
                        out.append(f"| ← {c['kind']} | `{short(c['source_type'])}` | {CARD[cd['source_per_target']]} |")
                out.append('')
    n += 1
    out += [f'## {n}. Links between architectures', '',
            'The model above covers each architecture on its own. Links **between** architectures are the nine relationship types below; actual links are records in the Architecture Relationship Registry, proposed by the inference engine and approved by architects.', '',
            '| Relationship | From → to | How many |', '|---|---|---|']
    out += [f"| `{x['relationship']}` | `{x['source_type']}` → `{x['target_type']}` | {x['cardinality'].replace('_', ' to ')} |" for x in reg]
    est, inst, res = conformance(mm, attrs, common)
    out += ['', '---', '', '## Appendix A. Rules', '',
            'The rules the data must satisfy, and which the checker enforces today.', '',
            '| ID | Rule | Detail | Status |', '|---|---|---|---|']
    out += [f"| {c[0]} | {c[1]} | {c[2]} | **{c[3]}** |" for c in CONSTRAINTS]
    out += ['', '## Appendix B. How the example data measures up', '',
            f"The {est} example estates ({inst} instances) checked by `sdem-graph check` against the enforced rules. " + ('No errors' if all(res[f'{lc} failed'] == 0 for lc in ('LC-04', 'LC-05', 'LC-06', 'LC-07', 'LC-09', 'LC-10')) else 'Errors are listed below') + f"; {res['LC-10m failed']} completeness warning(s), where an example exports part of BIAN's structure (a business domain without its area, a business object without attribute instances, a stub Service Domain without its groups or control record)" + (f"; {res['LC-13 failed']} instance(s) still use a deprecated field" if res['LC-13 failed'] else '') + '.', '',
            '| Rule | Values checked | Failures |', '|---|---|---|']
    for lc in ('LC-04', 'LC-05', 'LC-06', 'LC-07', 'LC-08', 'LC-09', 'LC-10', 'LC-10m'):
        out.append(f"| {lc}{' (warning)' if lc in ('LC-08', 'LC-10m') else ''} | {res[lc + ' checked']} | {res[lc + ' failed']} |")
    out += [f"| LC-13 deprecated field in use | — | {res['LC-13 failed']} |", f"| fields not in the model | — | {res['undefined']} |", '',
            '## Appendix C. Where the model\'s decisions come from', '',
            'Each entity\'s, field\'s and link\'s source, reasoning and confidence are in [`architecture-entity-design.md`](architecture-entity-design.md), [`architecture-attribute-design.md`](architecture-attribute-design.md) and [`relationships-planning.md`](relationships-planning.md). In summary:', '',
            '| Decision | Count | Basis |', '|---|---|---|']
    cb = Counter(c['cardinality']['basis'] for c in lr['constraints'])
    CB = {'BIAN': 'stated by BIAN', 'SDEM default': 'no standard sets a number; left open', 'SDEM reading': "SDEM's reading of a BIAN page"}
    out += [f"| Link counts — {k} | {v} | {CB.get(k, 'a part belongs to at most one whole (ArchiMate)')} |" for k, v in cb.most_common()]
    ib = Counter((e.get('identifier') or {}).get('basis') for e in ents if (e.get('identifier') or {}).get('key'))
    out += [f"| Identifiers — {k} | {v} | {'BIAN concept ids and operation naming' if k == 'BIAN' else 'path and method unique per API' if k == 'OpenAPI' else 'SDEM recommendation: a unique name'} |" for k, v in ib.most_common()]
    out += ['', '## Appendix D. Where this sits', '', '| Layer | Content | Status |', '|---|---|---|',
            '| Conceptual | which entities exist and which links are allowed | complete |',
            f"| **Logical (this document)** | identifiers, typed fields, allowed values, references, link counts, rules | designed; {sum(1 for c in CONSTRAINTS if c[3].startswith('enforced'))} of {len(CONSTRAINTS)} rules enforced |",
            '| Physical | one export JSON Schema per entity; a graph store schema | not generated yet — next build |', '']
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
