"""Design records and gap records — what did not fit an architecture entity, kept beside the estate (docs/sdem-load-design.md §4a).

`sdem load` writes <estate>/designs/design-records.json: a design record (DOC-…) per source page or file of an imported
design, and a gap record (GAP-…) per item that did not fit. `sdem build` turns them into designs.graph.json, beside the
architecture graphs. Information, not architecture: the rules engine and impact analysis never read them.

  sdem designs --estate DIR | --graph DIR [--entity ID] [--gaps] [--category C] [--status S] [--json]
  sdem designs resolve | accept | reopen GAP-… --estate DIR --person NAME --note TEXT     (a person's decision, on record)
"""
import argparse, collections, datetime, hashlib, json, re, sys
from pathlib import Path

from .paths import DATA_ROOT

RECORDS = Path('designs') / 'design-records.json'
GRAPH = 'designs.graph.json'
SCHEMA = DATA_ROOT / 'schema' / 'design-records.schema.json'
EMPTY = {'records_version': '1.0', 'documents': [], 'gaps': []}


def is_design_records(doc):
    return isinstance(doc, dict) and 'documents' in doc and 'gaps' in doc


def _hash(*parts):
    return hashlib.sha1('\x1f'.join(str(p) for p in parts).encode('utf-8')).hexdigest()[:10].upper()


def doc_id(page_id):
    p = str(page_id)
    return f'DOC-{p}' if re.fullmatch(r'[0-9]+', p) else f'DOC-{_hash(p)}'


def gap_id(document, category, where, text, about=()):
    return f"GAP-{_hash(document, category, where, text, ','.join(sorted(about)))}"


def from_transform(meta, index, ledger, records, loaded, excluded, person, load_id):
    """The design and gap records one load adds. `index` = design-index.json's designs, `ledger` = extraction.json's
    coverage items, `records` = its candidate records, `loaded` = ids now in the estate, `excluded` = ids the person rejected."""
    by_page = {p['page_id']: p for p in index}
    docs, gaps = {}, []

    def document(page_id, file=None, title=None):
        did = doc_id(page_id)
        if did not in docs:
            p = by_page.get(page_id)
            if p:
                kind = 'page' if not p.get('diagram_only') else ('picture file' if p['title'].endswith('(picture file)') else 'diagram file')
                docs[did] = {'id': did, 'kind': kind, 'page_id': str(page_id), 'title': p['title'], 'space': p.get('space') or '', 'url': p.get('url'),
                             'file': p['file'], 'modified': p.get('modified'), 'breadcrumb': p.get('breadcrumb', []), 'facts': p.get('facts', {}),
                             'coverage': p.get('coverage'), 'entities': sorted(set(p.get('records', [])) & loaded), 'loads': [load_id]}
            else:  # a file with no page of its own (e.g. a PDF)
                docs[did] = {'id': did, 'kind': 'file', 'page_id': str(page_id), 'title': title or Path(file or str(page_id)).name, 'file': file or str(page_id),
                             'entities': [], 'loads': [load_id]}
        return did

    for p in index: document(p['page_id'])
    for i in ledger:
        if i['status'] != 'not captured': continue
        if i.get('category') == 'column not mapped' and 'each entity' in i['reason']: continue   # entity columns: one gap per entity, below
        did = document(i['page_id'], i.get('file'), i.get('page_title'))
        about = sorted(set(i.get('records', [])) & loaded)
        gaps.append({'id': gap_id(did, i['category'], i['where'], i.get('text', ''), about), 'document': did, 'category': i['category'], 'kind': i['kind'],
                     'where': i['where'], 'text': i.get('text', ''), 'reason': i['reason'], 'about': about, 'status': 'open', 'first_load': load_id})
    for r in records:
        first = r['sources'][0]; did = document(first['page_id'], first.get('file'), first.get('page_title'))
        if r['id'] in loaded:
            tab = next((x for x in r['sources'] if str(x.get('rule', '')).startswith('HT-')), first)   # the entity table the unmapped columns came from
            tdid = document(tab['page_id'], tab.get('file'), tab.get('page_title'))
            for col, val in (r.get('unmapped') or {}).items():
                gaps.append({'id': gap_id(tdid, 'column not mapped', col, val, [r['id']]), 'document': tdid, 'category': 'column not mapped', 'kind': 'column',
                             'where': f"{tab['where']}, column '{col}'", 'text': f'{col}: {val}',
                             'reason': 'no rule maps this column — map it in the rules if the data model has an attribute for it',
                             'about': [r['id']], 'status': 'open', 'first_load': load_id})
        elif r['id'] in excluded:
            extra = '; unmapped: ' + ', '.join(f'{k}: {v}' for k, v in r['unmapped'].items()) if r.get('unmapped') else ''
            gaps.append({'id': gap_id(did, 'rejected at load', r['id'], r['name']), 'document': did, 'category': 'rejected at load', 'kind': 'candidate',
                         'where': first['where'], 'text': f"{r['id']} {r['name']} ({r['type']}, {r['confidence']}){extra}",
                         'reason': f'excluded by {person} at {load_id}', 'about': [], 'status': 'open', 'first_load': load_id})
    return list(docs.values()), gaps


def merge(existing, documents, gaps, load_id):
    """Add new records; a record already there keeps its status and notes (stable ids — a repeated load adds nothing twice)."""
    out = json.loads(json.dumps(existing or EMPTY))
    have_d = {d['id']: d for d in out['documents']}; have_g = {g['id'] for g in out['gaps']}
    added_d = added_g = 0
    for d in documents:
        if d['id'] in have_d:
            o = have_d[d['id']]
            o['entities'] = sorted(set(o['entities']) | set(d['entities']))
            if load_id not in o['loads']: o['loads'].append(load_id)
            for k in ('facts', 'coverage', 'url', 'modified'):
                if d.get(k): o[k] = d[k]
        else:
            out['documents'].append(d); have_d[d['id']] = d; added_d += 1
    for g in gaps:
        if g['id'] not in have_g: out['gaps'].append(g); have_g.add(g['id']); added_g += 1
    out['documents'].sort(key=lambda d: d['id']); out['gaps'].sort(key=lambda g: (g['document'], g['category'], g['id']))
    return out, {'documents_added': added_d, 'gaps_added': added_g}


def check(doc, entity_ids=None):
    """Schema, then references: gap → design record (error); design or gap → an entity no longer in the estate (warning)."""
    from .validate import check_schema
    errors = check_schema(doc, json.loads(SCHEMA.read_text(encoding='utf-8')))
    if errors: return errors, []
    warnings, ids = [], {d['id'] for d in doc['documents']}
    for kind, items in (('design record', doc['documents']), ('gap record', doc['gaps'])):
        seen = set()
        for x in items:
            if x['id'] in seen: errors.append(f"{kind} {x['id']}: duplicate id")
            seen.add(x['id'])
    for g in doc['gaps']:
        if g['document'] not in ids: errors.append(f"gap record {g['id']}: design record {g['document']} does not exist")
        last = (g.get('history') or [None])[-1]   # LD-R05: a status other than open is a person's decision, on record
        if g['status'] != 'open' and (not last or last['status'] != g['status'] or not _is_person(last['person'])):
            errors.append(f"gap record {g['id']}: status {g['status']!r} without a person's decision in its history — use sdem designs {'resolve' if g['status'] == 'resolved' else 'accept'}")
    if entity_ids is not None:
        for x in doc['documents'] + doc['gaps']:
            gone = [e for e in x.get('entities', []) + x.get('about', []) if e not in entity_ids]
            if gone: warnings.append(f"{x['id']}: refers to {', '.join(sorted(set(gone)))} — no longer in the estate")
    return errors, warnings


def graph(doc, node_key):
    """designs.graph.json (GS-D-01): design and gap nodes; DOCUMENTS, FOUND_IN, ABOUT edges. node_key(id) → an entity's node key or None."""
    nodes, edges = [], []
    for d in doc['documents']:
        nodes.append({'id': d['id'], 'label': d['title'], 'metadata': {'record': 'design', **{k: v for k, v in d.items() if k != 'id'}}})
        for e in d['entities']:
            k = node_key(e)
            if k: edges.append({'id': f"{d['id']}-DOCUMENTS-{e}", 'source': d['id'], 'target': k, 'relation': 'DOCUMENTS', 'metadata': {'scope': 'designs'}})
    for g in doc['gaps']:
        nodes.append({'id': g['id'], 'label': f"{g['category']}: {g.get('text', '')[:60]}", 'metadata': {'record': 'gap', **{k: v for k, v in g.items() if k != 'id'}}})
        edges.append({'id': f"{g['id']}-FOUND_IN", 'source': g['id'], 'target': g['document'], 'relation': 'FOUND_IN', 'metadata': {'scope': 'designs'}})
        for e in g['about']:
            k = node_key(e)
            if k: edges.append({'id': f"{g['id']}-ABOUT-{e}", 'source': g['id'], 'target': k, 'relation': 'ABOUT', 'metadata': {'scope': 'designs'}})
    return {'graph': {'id': 'sdem:designs', 'type': 'sdem.designs', 'label': 'Design records and gap records', 'directed': True,
                      'metadata': {'sdem_store_version': '1.0', 'records_version': doc['records_version'], 'documents': len(doc['documents']), 'gaps': len(doc['gaps'])},
                      'nodes': nodes, 'edges': edges}}


def _is_person(name):
    from .validate import is_person
    return is_person(name)


def set_status(doc, ids, status, person, note, now=None):
    """LD-R05: a person resolves, accepts or reopens gaps; the change is added to each gap's history."""
    if not _is_person(person): raise ValueError(f"--person {person!r}: dealing with a gap is a person's decision — give your own name, never an agent or tool")
    if status in ('resolved', 'accepted') and not (note or '').strip(): raise ValueError(f'--note is required: say why the gap is {status}')
    by = {g['id']: g for g in doc['gaps']}
    missing = [i for i in ids if i not in by]
    if missing: raise ValueError(f"no such gap record: {', '.join(missing)}")
    at = now or datetime.datetime.now().replace(microsecond=0).isoformat()
    changed = []
    for i in ids:
        g = by[i]
        if g['status'] == status: continue
        g['status'] = status; g.setdefault('history', []).append({'status': status, 'at': at, 'person': person, 'note': note or ''})
        changed.append(i)
    return changed


def from_graph(g):
    """design-records.json back from designs.graph.json."""
    out = {'records_version': g['graph']['metadata'].get('records_version', '1.0'), 'documents': [], 'gaps': []}
    for n in g['graph']['nodes']:
        m = dict(n['metadata']); kind = m.pop('record'); m = {'id': n['id'], **m}
        (out['documents'] if kind == 'design' else out['gaps']).append(m)
    return out


def for_entity(doc, eid):
    """The design records that document an entity, and the gaps about it or found in those pages."""
    docs = [d for d in doc['documents'] if eid in d['entities']]
    ids = {d['id'] for d in docs}
    return docs, [g for g in doc['gaps'] if eid in g['about'] or g['document'] in ids]


def load(estate=None, graph_dir=None):
    if graph_dir:
        p = Path(graph_dir) / GRAPH
        if not p.exists(): raise ValueError(f'{graph_dir}: no {GRAPH} — the estate has no design records, or the store was built before them')
        return from_graph(json.loads(p.read_text(encoding='utf-8')))
    p = Path(estate) / RECORDS
    if not p.exists(): raise ValueError(f'{estate}: no {RECORDS.as_posix()} — onboard designs with `sdem load` first')
    return json.loads(p.read_text(encoding='utf-8'))


def _set_main(argv):
    verb = argv[0]; status = {'resolve': 'resolved', 'accept': 'accepted', 'reopen': 'open'}[verb]
    ap = argparse.ArgumentParser(prog=f'sdem designs {verb}', description={'resolve': 'Mark gaps resolved — what they held is now in the data.',
                                 'accept': 'Mark gaps accepted — left as they are, on purpose.', 'reopen': 'Reopen gaps.'}[verb])
    ap.add_argument('gaps', nargs='+', metavar='GAP-ID'); ap.add_argument('--estate', required=True, metavar='DIR')
    ap.add_argument('--person', required=True, help='your name — a person, never an agent'); ap.add_argument('--note', default='', help='why (required to resolve or accept)')
    a = ap.parse_args(argv[1:])
    p = Path(a.estate) / RECORDS
    try:
        doc = json.loads(p.read_text(encoding='utf-8'))
        changed = set_status(doc, a.gaps, status, a.person, a.note)
        errs, _ = check(doc)
        if errs: raise ValueError('; '.join(errs[:5]))
    except (OSError, ValueError) as e:
        print(f'ERROR: {e}', file=sys.stderr); return 1
    from .files import write_json
    write_json(p, doc)
    left = sum(1 for g in doc['gaps'] if g['status'] == 'open')
    print(f"{status}: {', '.join(changed) or 'nothing changed'} (by {a.person}); {left} open gap(s) left in {a.estate}")
    print('Commit the change on a branch and open a pull request — it is a decision on record.')
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ('resolve', 'accept', 'reopen'): return _set_main(argv)
    ap = argparse.ArgumentParser(prog='sdem designs', description='List the design records (one per source page of an imported design) and gap records (what did not fit an architecture entity).')
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument('--estate', metavar='DIR'); src.add_argument('--graph', metavar='DIR')
    ap.add_argument('--entity', metavar='ID', help="an entity's pages and the gaps about it or found in them")
    ap.add_argument('--gaps', action='store_true', help='list gap records, not design records')
    ap.add_argument('--category', help='only gaps of this category, e.g. "no entity type"')
    ap.add_argument('--status', choices=['open', 'resolved', 'accepted'], help='only gaps with this status')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    try: doc = load(a.estate, a.graph)
    except (ValueError, OSError) as e:
        print(f'ERROR: {e}', file=sys.stderr); return 2
    docs, gaps = (for_entity(doc, a.entity) if a.entity else (doc['documents'], doc['gaps']))
    gaps = [g for g in gaps if (not a.category or g['category'] == a.category) and (not a.status or g['status'] == a.status)]
    if a.json: print(json.dumps({'documents': docs, 'gaps': gaps}, indent=2, ensure_ascii=False)); return 0
    if a.entity: print(f'{a.entity}: documented in {len(docs)} design record(s); {len(gaps)} gap(s) about it or in those pages')
    if not a.gaps or a.entity:
        for d in docs:
            c = d.get('coverage') or {}
            print(f"  {d['id']}  {d['title']}  ({d.get('modified') or 'no date'}" + (f", {c['percent']}% captured" if c else '') + f")  {len(d['entities'])} entities"
                  + (f"  · {', '.join(f'{k}: {v}' for k, v in list(d.get('facts', {}).items())[:3])}" if d.get('facts') else ''))
    if a.gaps or a.entity:
        n = collections.Counter(g['category'] for g in gaps)
        print(f"gaps: {len(gaps)}" + (' — ' + ', '.join(f'{k} {v}' for k, v in n.most_common()) if gaps else ''))
        for g in gaps:
            print(f"  {g['id']}  [{g['status']}] {g['category']}  {g['where']}" + (f"  — {g['text'][:100]}" if g.get('text') else '') + (f"  (about {', '.join(g['about'])})" if g['about'] else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
