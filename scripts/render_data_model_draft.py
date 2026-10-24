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


def src(a):
    if a['term'] in ('—', '', None):
        return f"SDEM-defined — no open standard; decision {a['id']} in this draft"
    return f"[{a['source'].split(' (')[0]}]({a['uri']}) `{a['term']}`"


def csrc(c):
    r = c.get('reference') or {}
    return f"[{r.get('standard', c.get('source', ''))}]({r.get('uri', '')}): {r.get('locator', '')}" if r else c.get('source', '')


def esrc(a):
    r = a['reference']; loc = r.get('locator') or ''
    return f"[{r['standard']}]({r['uri']})" + (f": {loc}" if loc and loc != '—' else '')


def render(level):
    d = json.loads((ROOT / 'metamodel' / 'drafts' / f'{level}-descriptive-attributes.json').read_text())
    ents = json.loads((ROOT / 'metamodel' / FILES[level]).read_text())['entities']
    rec = json.loads((ROOT / 'metamodel' / 'entity-attributes.json').read_text())
    lv = level.upper()
    cur = [a for a in rec['attributes'] if a['entity'].startswith(lv)]; core = [c for c in rec['core_fields'] if c['name'] != 'attributes']
    A = d['attributes']; drafted = {a['id'] for a in A}
    cur = [a for a in cur if (a.get('approved') or {}).get('draft_id') not in drafted]  # a re-rendered draft shows its own fields as proposed, not twice
    common = [a for a in A if a['entity'] == 'all']; common_status = 'proposed'
    if not common:  # common attributes already approved: show them from the attribute record
        common_status = 'approved'
        common = [{'id': c['id'], 'name': c['name'], 'type': c['type'], 'values': c.get('values'), 'references': c.get('references'), 'meaning': c['description'], 'question': c['question'],
                   'reasoning': c['reasoning'].replace(f"Answers: {c['question']} ", ''), 'source': c['reference']['standard'], 'uri': c['reference']['uri'], 'term': c['reference']['locator'], 'confidence': c['confidence']} for c in rec.get('common_attributes', [])]
    common_names = {a['name'] for a in common}
    out = [f"# {NAMES[level]} — Data Model (DRAFT for review)", '',
           f"> **Status: draft, {d['date']}.** Proposed fields are marked **proposed**; nothing here is in the model until you approve it. Record: `metamodel/drafts/{level}-descriptive-attributes.json`. Rendered by `python scripts/render_data_model_draft.py {level}`.", '',
           '**How to read each entity.** The **Data Model** table is the complete record for the entity: every field, its type, whether it is required, its allowed values, what it holds and its **source reference**. Fields come in groups — **Core** (identity, on every entity), **Common** (descriptive, on every entity), **Inherited** (from a parent entity) and **Specific** (this entity only). Each entity and each field carries its **source reference**, **reasoning** (for proposed fields, starting with the design question it answers) and **confidence**. In an export file the common and specific fields sit inside the instance\'s `attributes` object.', '',
           '**How the draft was built.** One field per design question, each from the highest available source — BIAN → open public standards readable without login (Dublin Core, W3C ORG, W3C SKOS, public privacy law) → ArchiMate concepts (meaning only) → SDEM-defined. Not used: TOGAF and the ArchiMate text (login), paid standards, vendor schemas, your employer\'s model. Confidence: **high** = a public standard defines it and it was checked; **medium** = built on a standard concept as SDEM chose; **low** = SDEM-defined.', '',
           '## 1. Fields every entity has', '', '### Core fields (existing)', '', '| Field | Type | Required | Holds | Source reference | Reasoning | Confidence |', '|---|---|---|---|---|---|---|']
    out += [f"| `{c['name']}` | {ctype(c)} | {'yes' if c['required'] else 'no'} | {c['description']} | {csrc(c)} | {c['reasoning']} | **{c['confidence']}** |" for c in core]
    if common:
        out += ['', f"### Common attributes ({common_status} for all four architectures)", '', '| ID | Field | Type | Allowed values | Holds | Answers | Source | Reasoning | Confidence |', '|---|---|---|---|---|---|---|---|---|']
        out += [f"| {a['id']} | `{a['name']}` | {a['type']} | {allowed(a)} | {a['meaning']} | {a['question']} | {src(a)} | {a['reasoning']} | **{a['confidence']}** |" for a in common]
    out.append('')
    n = 1
    for e in ents:
        if e.get('abstract'): continue
        n += 1
        ex = [a for a in cur if a['entity'] == e['type']]; pr = [a for a in A if a['entity'] == e['type'] and a.get('status') != 'dropped']
        dup = [a for a in ex if a['name'] in common_names]; ex = [a for a in ex if a['name'] not in common_names]
        par = e.get('extends')
        pex = [a for a in cur if par and a['entity'] == par]; ppr = [a for a in A if par and a['entity'] == par]
        r = e['reference']
        out += [f"## {n}. {e['type']} — Data Model", '', ('*An artefact: a published document or model file, not an architecture element.* ' if e.get('artefact') else '') + f"**{e['definition'].rstrip('.')}.**" + (f" A kind of `{par}`: it has all of its parent's fields as well." if par else ''), '',
                '| Entity | Source reference | Reasoning | Confidence |', '|---|---|---|---|',
                f"| `{e['type']}` | [{r['standard']}{(' ' + r['release']) if r['release'] not in r['standard'] else ''}: {r['concept']}]({r['uri']}){(', ' + r['locator']) if r.get('locator') else ''} | {e['reasoning']} | **{e['confidence']}** |", '',
                '| # | Field | Group | Type | Required | Allowed values / refers to | Holds | Source reference | Reasoning | Confidence | Status |', '|---|---|---|---|---|---|---|---|---|---|---|']
        i = 0
        def row(name, group, typ, req, allow, holds, source, why, conf, status):
            nonlocal i
            i += 1
            out.append(f"| {i} | {name} | {group} | {typ} | {req} | {allow} | {holds} | {source} | {why} | **{conf}** | {status} |")
        for c in core:
            row(f"`{c['name']}`", 'Core', ctype(c), 'yes' if c['required'] else 'no', ', '.join(c.get('values', [])) or '—',
                ('always `' + e['type'] + '`') if c['name'] == 'type' else c['description'], csrc(c), c['reasoning'], c['confidence'], 'existing')
        for x in common:
            row(f"`{x['name']}`", 'Common', x['type'], 'no', allowed(x), x['meaning'], src(x), f"Answers: {x['question']} {x['reasoning']}", x['confidence'], f"{common_status} {x['id']}")
        for x in pex:
            row(f"`{x['name']}`", f"Inherited from `{par.split('.')[1]}`", CT.get(x['type'], x['type']), 'yes' if x['required'] else 'no', allowed(x), x['description'], esrc(x), x['reasoning'], x['confidence'], 'existing')
        for x in ppr:
            row(f"`{x['name']}`", f"Inherited from `{par.split('.')[1]}`", x['type'], 'no', allowed(x), x['meaning'], src(x), f"Answers: {x['question']} {x['reasoning']}", x['confidence'], f"proposed {x['id']}")
        for x in ex:
            row(f"`{x['name']}`", 'Specific', CT.get(x['type'], x['type']), 'yes' if x['required'] else 'no', allowed(x), x['description'], esrc(x), x['reasoning'], x['confidence'], 'existing')
        for x in pr:
            row(f"**`{x['name']}`**", 'Specific', x['type'], 'no', allowed(x), x['meaning'], src(x), f"Answers: {x['question']} {x['reasoning']}", x['confidence'], f"**{'approved' if x.get('status') == 'approved' else 'proposed'} {x['id']}**")
        for x in dup:
            row(f"~~`{x['name']}`~~", 'Specific (existing text field)', CT.get(x['type'], x['type']), 'no', '—', x['description'], esrc(x), x['reasoning'] + f" Replaced by the common `{x['name']}`, which refers to an actor or role instead of holding free text.", x['confidence'], '**to be replaced**')
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
