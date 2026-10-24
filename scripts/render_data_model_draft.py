"""Render a data-model draft for review: docs/drafts/data-model-<level>-draft.md from metamodel/drafts/<level>-descriptive-attributes.json.

Each entity gets '<entity> — Data Model': the complete field list (core, common, inherited, specific) with type, required,
allowed values and what each field holds; then a Sources table (question, source, reasoning, confidence) for its fields.
Usage: python scripts/render_data_model_draft.py a1
"""
import json, sys
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
CT = {'string': 'text', 'list<string>': 'list of text', 'map<string,string>': 'name map', 'object': 'object'}
FILES = {'a1': 'a1-business.json', 'a2': 'a2-service-domain.json', 'a3': 'a3-application.json', 'a4': 'a4-technology.json'}
NAMES = {'a1': 'A1 Business Architecture', 'a2': 'A2 Service Domain Architecture', 'a3': 'A3 Application Architecture', 'a4': 'A4 Technology Architecture'}


def allowed(a):
    if a.get('values'): return ', '.join(a['values'])
    if a.get('references'): return 'refers to ' + ', '.join(f"`{t}`" for t in a['references'])
    return '—'


def ctype(c): return 'enum' if c['type'].startswith('enum') else CT.get(c['type'], c['type'])


def src(a): return f"[{a['source'].split(' (')[0]}]({a['uri']}) `{a['term']}`"


def render(level):
    d = json.loads((ROOT / 'metamodel' / 'drafts' / f'{level}-descriptive-attributes.json').read_text())
    ents = json.loads((ROOT / 'metamodel' / FILES[level]).read_text())['entities']
    rec = json.loads((ROOT / 'metamodel' / 'entity-attributes.json').read_text())
    lv = level.upper()
    cur = [a for a in rec['attributes'] if a['entity'].startswith(lv)]; core = [c for c in rec['core_fields'] if c['name'] != 'attributes']
    A = d['attributes']; common = [a for a in A if a['entity'] == 'all']; common_names = {a['name'] for a in common}
    out = [f"# {NAMES[level]} — Data Model (DRAFT for review)", '',
           f"> **Status: draft, {d['date']}.** Proposed fields are marked **proposed**; nothing here is in the model until you approve it. Record: `metamodel/drafts/{level}-descriptive-attributes.json`. Rendered by `python scripts/render_data_model_draft.py {level}`.", '',
           '**How to read each entity.** The **Data Model** table is the complete record for the entity: every field, its type, whether it is required, its allowed values and what it holds. Fields come in groups — **Core** (identity, on every entity), **Common** (descriptive, on every entity), **Inherited** (from a parent entity) and **Specific** (this entity only). The **Sources** table under it gives, for each specific field, the question it answers, where it comes from, why, and how confident that basis is; the common fields\' sources are in section 1. In an export file the common and specific fields sit inside the instance\'s `attributes` object.', '',
           '**How the draft was built.** One field per design question, each from the highest available source — BIAN → open public standards readable without login (Dublin Core, W3C ORG, W3C SKOS, public privacy law) → ArchiMate concepts (meaning only) → SDEM-defined. Not used: TOGAF and the ArchiMate text (login), paid standards, vendor schemas, your employer\'s model. Confidence: **high** = a public standard defines it and it was checked; **medium** = built on a standard concept as SDEM chose; **low** = SDEM-defined.', '',
           '## 1. Fields every entity has', '', '### Core fields (existing)', '', '| Field | Type | Required | Holds |', '|---|---|---|---|']
    out += [f"| `{c['name']}` | {ctype(c)} | {'yes' if c['required'] else 'no'} | {c['description']} |" for c in core]
    if common:
        out += ['', '### Common fields (proposed for all four architectures)', '', '| ID | Field | Type | Allowed values | Holds | Answers | Source | Reasoning | Confidence |', '|---|---|---|---|---|---|---|---|---|']
        out += [f"| {a['id']} | `{a['name']}` | {a['type']} | {allowed(a)} | {a['meaning']} | {a['question']} | {src(a)} | {a['reasoning']} | **{a['confidence']}** |" for a in common]
    out.append('')
    n = 1
    for e in ents:
        if e.get('abstract') or e.get('artefact'): continue
        n += 1
        ex = [a for a in cur if a['entity'] == e['type']]; pr = [a for a in A if a['entity'] == e['type']]
        dup = [a for a in ex if a['name'] in common_names]; ex = [a for a in ex if a['name'] not in common_names]
        par = e.get('extends')
        pex = [a for a in cur if par and a['entity'] == par]; ppr = [a for a in A if par and a['entity'] == par]
        out += [f"## {n}. {e['type']} — Data Model", '', f"**{e['definition'].rstrip('.')}.**" + (f" A kind of `{par}`: it has all of its parent's fields as well." if par else ''), '',
                '| # | Field | Group | Type | Required | Allowed values / refers to | Holds | Status |', '|---|---|---|---|---|---|---|---|']
        i = 0
        for c in core:
            i += 1; out.append(f"| {i} | `{c['name']}` | Core | {ctype(c)} | {'yes' if c['required'] else 'no'} | {', '.join(c.get('values', [])) or '—'} | {('always `' + e['type'] + '`') if c['name'] == 'type' else c['description']} | existing |")
        for a in common:
            i += 1; out.append(f"| {i} | `{a['name']}` | Common | {a['type']} | no | {allowed(a)} | {a['meaning']} | proposed |")
        for a in pex:
            i += 1; out.append(f"| {i} | `{a['name']}` | Inherited from `{par.split('.')[1]}` | {CT.get(a['type'], a['type'])} | {'yes' if a['required'] else 'no'} | {allowed(a)} | {a['description']} | existing |")
        for a in ppr:
            i += 1; out.append(f"| {i} | `{a['name']}` | Inherited from `{par.split('.')[1]}` | {a['type']} | no | {allowed(a)} | {a['meaning']} | proposed |")
        for a in ex:
            i += 1; out.append(f"| {i} | `{a['name']}` | Specific | {CT.get(a['type'], a['type'])} | {'yes' if a['required'] else 'no'} | {allowed(a)} | {a['description']} | existing |")
        for a in pr:
            i += 1; out.append(f"| {i} | **`{a['name']}`** | Specific | {a['type']} | no | {allowed(a)} | {a['meaning']} | **proposed** |")
        if ex or pr or dup:
            out += ['', '**Sources of the specific fields**', '', '| Field | Status | Answers | Source | Reasoning | Confidence |', '|---|---|---|---|---|---|']
            out += [f"| `{a['name']}` | existing | — | {a['source']} ({a['reference']['standard']}) | {a['reasoning']} | {a['confidence']} |" for a in ex]
            out += [f"| `{a['name']}` | proposed {a['id']} | {a['question']} | {src(a)} | {a['reasoning']} | **{a['confidence']}** |" for a in pr]
            out += [f"| ~~`{a['name']}`~~ (existing text field) | **replaced** by the common `{a['name']}` | — | {a['source']} | {a['reasoning']} The common field supersedes it: it refers to an actor or role instead of holding free text. | {a['confidence']} |" for a in dup]
        out.append('')
    c = Counter(a['confidence'] for a in A)
    out += ['## Summary of proposed fields', '', '| Group | Fields | High | Medium | Low |', '|---|---|---|---|---|']
    for scope, label in (('all', 'Common (every entity)'),) + tuple((e['type'], f"`{e['type']}`") for e in ents):
        r = [a for a in A if a['entity'] == scope]
        if r: cc = Counter(a['confidence'] for a in r); out.append(f"| {label} | {len(r)} | {cc['high']} | {cc['medium']} | {cc['low']} |")
    out += [f"| **Total** | **{len(A)}** | **{c['high']}** | **{c['medium']}** | **{c['low']}** |", '']
    out += ['## Decisions for you', ''] + [f"{k}. {q}" for k, q in enumerate(d.get('decisions', []), 1)] + ['']
    path = ROOT / 'docs' / 'drafts' / f'data-model-{level}-draft.md'
    path.write_text('\n'.join(out) + '\n'); return path


if __name__ == '__main__':
    print('wrote', render(sys.argv[1] if len(sys.argv) > 1 else 'a1'))
