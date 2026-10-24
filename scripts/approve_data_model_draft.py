"""Write an approved data-model draft into metamodel/entity-attributes.json.

Each approved draft attribute becomes an attribute record (AT-<level>-nn) carrying its source reference,
verification, reasoning and confidence; the draft is marked approved and becomes the decision record.
Usage: python scripts/approve_data_model_draft.py a2 --drop DA2-02 --decision "..." [--decision "..."]
"""
import argparse, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATE = '2026-10-24'
# draft source text (prefix) -> attribute-record source; order matters (longest first)
SOURCES = [('BIAN Semantic API Practitioner Guide', 'BIAN'), ('BIAN concept', 'BIAN concept'), ('ISO 20022', 'ISO 20022'), ('Dublin Core', 'Dublin Core'),
           ('W3C Organization Ontology', 'W3C ORG'), ('W3C SKOS', 'W3C SKOS'), ('W3C', 'W3C'), ('EU GDPR', 'public legislation'), ('ArchiMate 3.2 concept', 'ArchiMate concept'),
           ('OpenAPI', 'OpenAPI'), ('AsyncAPI', 'AsyncAPI'), ('SPDX', 'SPDX'), ('CycloneDX', 'CycloneDX'), ('Semantic Versioning', 'SemVer'), ('NIST', 'NIST'),
           ('IANA', 'IANA'), ('CloudEvents', 'CloudEvents'), ('IETF', 'IETF'), ('package-url', 'purl'), ('ISO 3166', 'ISO 3166'), ('Kubernetes', 'Kubernetes'), ('Open Container Initiative', 'OCI'), ('SDEM-defined', 'SDEM')]
CHECKED = {'BIAN': 'public BIAN Semantic API Practitioner Guide v8.1, page checked ' + DATE, 'BIAN concept': 'BIAN concept named in the public Service Landscape; the field itself not checked against a public page',
           'ArchiMate concept': 'concept confirmed by the Archi oracle; field as SDEM chose to model it', 'SDEM': f'SDEM design; approved in the data-model review {DATE}'}


def source_of(text):
    for prefix, src in SOURCES:
        if text.startswith(prefix): return src
    raise SystemExit(f'unknown source: {text}')


def rtype(x):
    t = x['type']
    if x.get('values') or t in ('text', 'uri', 'enum') or t.startswith('reference'): return 'string'
    for k in ('integer', 'boolean', 'date'):
        if t.startswith(k): return k
    return 'list<string>' if t.startswith('list') else 'string'


def build(x, ident, level):
    src = source_of(x['source'])
    a = {'id': ident, 'entity': x['entity'], 'name': x['name'], 'type': rtype(x), 'required': bool(x.get('required')), 'description': x['meaning'], 'status': 'active', 'source': src,
         'reference': {'standard': x['source'], 'locator': x['term'] if x['term'] not in ('—', '') else f"SDEM decision {x['id']} ({level.upper()} data-model review, {DATE})", 'uri': x['uri']},
         'verification': x.get('verification') or CHECKED.get(src, f'public standard ({src}), checked {DATE}'), 'reasoning': f"Answers: {x['question']} {x['reasoning']}", 'confidence': x['confidence'],
         'read_by': x.get('read_by', 'design and impact queries (descriptive attribute)'), 'question': x['question'],
         'approved': {'review': f'{level.upper()} data-model review', 'date': DATE, 'draft_id': x['id']}}
    if x.get('references'):
        a['kind'] = 'reference'; a['references'] = x['references']; a['reference_scope'] = x.get('reference_scope', 'same level — resolved by the local knowledge graph')
    elif x.get('values'):
        a['kind'] = 'enumeration'; a['values'] = x['values']; a['values_source'] = x.get('values_source', 'SDEM' if src == 'SDEM' else x['source'])
    else:
        a['kind'] = 'value'
    return a


def approve(level, drop=(), decisions=()):
    dp = ROOT / 'metamodel' / 'drafts' / f'{level}-descriptive-attributes.json'; d = json.loads(dp.read_text())
    rp = ROOT / 'metamodel' / 'entity-attributes.json'; rec = json.loads(rp.read_text())
    lv = level.upper(); done = {(a.get('approved') or {}).get('draft_id') for a in rec['attributes']}
    n = max([int(a['id'].split('-')[-1]) for a in rec['attributes'] if a['id'].startswith(f'AT-{lv}-')] or [0])
    added = []
    for x in d['attributes']:
        if x['id'] in drop: x['status'] = 'dropped'; continue
        x['status'] = 'approved'
        if x['id'] in done: continue
        n += 1; a = build(x, f'AT-{lv}-{n:02d}', level); rec['attributes'].append(a); added.append(a['id'])
    rp.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + '\n')
    d['status'] = f"APPROVED {DATE}" + (f" — dropped {', '.join(drop)}" if drop else '') + f". Written into metamodel/entity-attributes.json ({', '.join(added[:1] + added[-1:]) if added else 'nothing new'})."
    if decisions: d['decisions_taken'] = list(decisions)
    dp.write_text(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
    return added


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('level'); ap.add_argument('--drop', nargs='*', default=[]); ap.add_argument('--decision', action='append', default=[])
    o = ap.parse_args(); print('added', approve(o.level, o.drop, o.decision))
