"""`sdem aid` — Architecture Inference Design fills a workspace's gaps (owner's decision DA2-05; spec docs/design/aid-spec.md AID-W*).

An architect writes whatever they have — any of A1…A4 — and `sdem aid` adds the records the workspace is missing to its real layer
files, each marked `inferred` with its source, reasoning and confidence, and writes the connections it infers as **proposals**
(approved by a person with `sdem approve`, as always). The architect reviews the files, then confirms or rejects each inferred record.
Nothing a person wrote is changed; a rejected record is never added again.

  sdem aid --workspace workspaces/payments --person jane.architect
  sdem aid confirm AID-APP-SD-PAYMENT-RAIL --workspace workspaces/payments --person jane.architect
  sdem aid reject AID-DEP-SD-PAYMENT-RAIL --workspace workspaces/payments --person jane.architect --reason "runs on the shared platform"
"""
import argparse, copy, datetime, json, re, sys
from pathlib import Path

DATASETS = {'A1': 'a1-business.json', 'A2': 'a2-service-domain.json', 'A3': 'a3-application.json', 'A4': 'a4-technology.json'}
FOLDER = 'aid'


class AidError(ValueError):
    """The request cannot be done (exit 2)."""


def _j(p): return json.loads(Path(p).read_text(encoding='utf-8'))


def _rid(i): return 'AID-' + i[4:] if isinstance(i, str) and i.startswith('PRJ-') else i


def _ids(x):
    """A record's values with planned ids (PRJ-) renamed to inferred ids (AID-)."""
    if isinstance(x, dict): return {k: _ids(v) for k, v in x.items()}
    if isinstance(x, list): return [_ids(v) for v in x]
    return _rid(x)


def is_inferred(rec, confirmed=None):
    m = (rec.get('attributes') or {}).get('inferred')
    if not isinstance(m, dict): return False
    return confirmed is None or (m.get('status') == 'confirmed') == confirmed


def _workspace(ws):
    ws = Path(ws)
    if not (ws / 'mappings.json').exists(): raise AidError(f'{ws}: no workspace here — start one with sdem new --workspace {ws} --person <you>')
    docs = {lvl: _j(ws / f) for lvl, f in DATASETS.items() if (ws / f).exists()}
    return ws, docs, _j(ws / 'mappings.json')


def _person(p):
    from .validate import is_person
    if not is_person(p): raise AidError(f"--person {p!r}: a decision about the workspace is a person's — give your own name (CTL-21)")


def _rejected(ws):
    f = ws / FOLDER / 'rejected.json'
    return _j(f) if f.exists() else {'rejected': []}


def fill(workspace, person, dry_run=False, now=None):
    """Infer what the workspace is missing into its layer files (AID-W01…W04). Returns the run record; nothing written when refused."""
    from .aid import project
    from .connect import estate_errors
    _person(person)
    ws, docs, registry = _workspace(workspace)
    now = now or datetime.datetime.now().replace(microsecond=0).isoformat()
    def evidence(d):   # AID-W08: AID infers only from what a person wrote or confirmed — never from its own unconfirmed records
        keep = [i for i in d['instances'] if not is_inferred(i, confirmed=False)]; ids = {i['id'] for i in keep}
        return {**d, 'instances': keep, 'relationships': [r for r in d.get('relationships', []) if r['source'] in ids and r['target'] in ids]}
    have = {lvl: e for lvl, d in docs.items() if lvl != 'A2' for e in [evidence(d)] if e.get('instances')}
    if not have: raise AidError(f'{ws}: nothing to infer from yet — write what you have first: any of {", ".join(f for l, f in DATASETS.items() if l != "A2")}')
    from .new import catalogue as workspace_catalogue
    catalogue = workspace_catalogue(ws)   # WS-01: the workspace's own A2 plus the BIAN catalogue it uses — read, not copied
    pkg = project(have, catalogue, registry, either=True)   # AID-M02: for a person to review, keep what either side supports
    runs = ws / FOLDER
    n = 1 + max([int(m.group(1)) for p in (runs.glob('AID-*.json') if runs.exists() else []) for m in [re.match(r'AID-(\d+)\.json$', p.name)] if m] or [0])
    run = f'AID-{n:03d}'
    rejected = {r['id'] for r in _rejected(ws)['rejected']}
    after = {lvl: copy.deepcopy(d) for lvl, d in docs.items()}
    present = {i['id'] for d in after.values() for i in d['instances']}
    added = {}
    stem = re.sub(r'[^A-Z0-9]+', '-', ws.name.upper()).strip('-') or 'WORKSPACE'
    for lvl, layer in sorted(pkg['layers'].items()):   # A2: only the service domains the design needs, with their parts, from the catalogue
        doc = after.setdefault(lvl, {'level': lvl, 'model_id': f'{stem}-{lvl}', 'model_version': now[:10], 'metamodel_version': layer['metamodel_version'],
                                     'source_system': 'SDEM-AID', 'instances': [], 'relationships': []})
        for inst in layer['instances']:
            nid = _rid(inst['id'])
            if nid in present or nid in rejected: continue
            rec = _ids(copy.deepcopy(inst)); pj = rec.pop('projection', {}) or {}
            rec['id'] = nid
            if lvl != 'A2':   # BIAN records keep BIAN's names; what SDEM built is named as inferred
                rec['name'] = re.sub(r'\s*\(projected\)', '', rec['name']).rstrip() + ' (inferred)'   # e.g. 'Payment Rail service — deployment (inferred)'
                if rec.get('description'): rec['description'] = re.sub(r'^Projected:', 'Inferred:', rec['description'])
            rec.setdefault('attributes', {})['inferred'] = {
                'by': 'sdem aid', 'run': run, 'at': now, 'requested_by': person.strip(), 'step': str(pj.get('step', '')), 'rule': str(pj.get('rule', '')),
                'source': str(pj.get('source_reference') or pj.get('rule') or ''), 'reasoning': str(pj.get('reasoning', '')),
                'confidence': str(pj.get('confidence', '')), 'from': ', '.join(_ids(pj.get('inferred_from', [])))}
            doc['instances'].append(rec); present.add(nid); added.setdefault(lvl, []).append(nid)
        have_rels = {(r['source'], r['kind'], r['target']) for r in doc.get('relationships', [])}
        for r in layer.get('relationships', []):
            r = _ids(dict(r)); key = (r['source'], r['kind'], r['target'])
            if key not in have_rels and r['source'] in present and r['target'] in present:
                doc.setdefault('relationships', []).append(r); have_rels.add(key)
    approved = {(m['source']['id'], m['relationship'], m['target']['id']) for m in registry.get('mappings', []) if m.get('status') == 'approved'}
    for f in (runs.glob('AID-*-proposals.json') if runs.exists() else []):   # already proposed by an earlier run, still to review: not again
        approved |= {(m['source']['id'], m['relationship'], m['target']['id']) for m in _j(f).get('mappings', [])}
    proposals = []
    by_id = {i['id']: i for d in after.values() for i in d['instances']}
    def end(ref):   # as `sdem link` writes them: id, type, version — and the canonical id a BIAN record carries
        r = by_id.get(ref['id'], {})
        return {**ref, **({'canonical_id': r['canonical_id']} if r.get('canonical_id') else {})}
    for link in pkg['links']['links']:
        s, t = end(_ids(link['source'])), end(_ids(link['target']))
        if s['id'] not in present or t['id'] not in present or (s['id'], link['relationship'], t['id']) in approved: continue
        pj = link.get('projection', {}) or {}
        proposals.append({'mapping_id': f'{run}-P{len(proposals) + 1:03d}', 'source': s, 'relationship': link['relationship'], 'target': t, 'status': 'proposed',
                          'confidence': link.get('confidence'), 'evidence': [f"engine_rationale:{run} {pj.get('rule', '')}".strip()],
                          'rationale': re.sub(r'^PROJECTED DESIGN, not a mapping:\s*', 'Inferred by sdem aid: ', link.get('rationale', '')),
                          'baseline_id': run, 'created_by': 'sdem aid'})
    errors = estate_errors({DATASETS[l]: d for l, d in after.items()}, registry)
    if errors: raise AidError('the workspace would not pass its checks with the inferred records — nothing written:\n  ' + '\n  '.join(errors[:10]))
    record = {'id': run, 'at': now, 'requested_by': person.strip(), 'added': added, 'proposals': f'{FOLDER}/{run}-proposals.json',
              'proposed_connections': len(proposals), 'projection_ends': pkg['projection'].get('projection_ends', []),
              'skipped_rejected': sorted(rejected & {_rid(i['id']) for l in pkg['layers'].values() for i in l['instances']})}
    if not dry_run and (added or proposals):
        from .files import Batch
        b = Batch()
        for lvl in added: b.json(ws / DATASETS[lvl], after[lvl])
        b.json(runs / f'{run}-proposals.json', {'mappings': proposals}); b.json(runs / f'{run}.json', record); b.commit()
    return record


def decide(workspace, ids, person, action, reason='', all_=False, now=None):
    """Confirm or reject inferred records (AID-W05, W06). Returns the ids changed."""
    _person(person)
    if action == 'reject' and not (reason or '').strip(): raise AidError('--reason is required to reject — it is kept, so the record is not inferred again')
    ws, docs, _ = _workspace(workspace)
    now = now or datetime.datetime.now().replace(microsecond=0).isoformat()
    inferred = {i['id']: (lvl, i) for lvl, d in docs.items() for i in d['instances'] if is_inferred(i, confirmed=False if all_ else None)}
    chosen = sorted(inferred) if all_ else list(ids)
    if not chosen: raise AidError('nothing to do — give the ids (see `sdem check` or the dashboard), or --all')
    missing = [i for i in chosen if i not in inferred]
    if missing: raise AidError(f"not inferred records in {ws}: {', '.join(missing)} — `sdem aid confirm|reject` acts only on records SDEM inferred")
    changed = set()
    every = {i['id']: (lvl, i) for lvl, d in docs.items() for i in d['instances'] if is_inferred(i)}
    def froms(rec): return {x.strip() for x in str(rec['attributes']['inferred'].get('from', '')).split(',') if x.strip()}
    if action == 'confirm':
        chosen = list(chosen) + [i for i, (lvl, r) in every.items()   # a BIAN service domain is confirmed with its parts (operations, control record …)
                                 if lvl == 'A2' and i not in chosen and froms(r) and froms(r) <= {c for c in chosen if every.get(c, ('', {}))[0] == 'A2'}]
        for i in chosen:
            lvl, rec = every[i]
            if is_inferred(rec, confirmed=True): continue
            rec['attributes']['inferred'].update(status='confirmed', confirmed_by=person.strip(), confirmed_at=now); changed.add(lvl)
    else:
        gone = set(chosen)
        while True:   # what SDEM inferred only from rejected records goes too: a domain's parts, the application built on it, its APIs and deployment
            more = {i for i, (lvl, r) in every.items() if i not in gone and is_inferred(r, confirmed=False) and froms(r) and froms(r) <= gone}
            if not more: break
            gone |= more
        def refs(x):   # every id a record or link names
            if isinstance(x, dict): return set().union(*(refs(v) for v in x.values())) if x else set()
            if isinstance(x, list): return set().union(*(refs(v) for v in x)) if x else set()
            return {x} if isinstance(x, str) else set()
        while True:    # a record another kept record still uses stays (e.g. a functional pattern two domains share)
            used = set().union(*([refs(i.get('attributes', {})) for d in docs.values() for i in d['instances'] if i['id'] not in gone] or [set()]))
            used |= {r['target'] for d in docs.values() for r in d.get('relationships', []) if r['source'] not in gone}
            keep = (gone & used) - set(chosen)
            if not keep: break
            gone -= keep
        chosen = sorted(gone)
        for lvl, d in docs.items():
            before = len(d['instances'])
            d['instances'] = [x for x in d['instances'] if x['id'] not in gone]
            d['relationships'] = [r for r in d.get('relationships', []) if r['source'] not in gone and r['target'] not in gone]
            if len(d['instances']) != before: changed.add(lvl)
        rej = _rejected(ws); rej['rejected'] += [{'id': i, 'by': person.strip(), 'at': now, 'reason': reason.strip()} for i in chosen]
    from .connect import estate_errors
    errors = estate_errors({DATASETS[l]: d for l, d in docs.items()}, _j(ws / 'mappings.json'))
    if errors: raise AidError(f'the workspace would not pass its checks after this {action} — nothing written:\n  ' + '\n  '.join(errors[:8])
                              + ('\n  (an approved connection may still point to it: supersede it first)' if action == 'reject' else ''))
    from .files import Batch
    b = Batch()
    for lvl in changed: b.json(ws / DATASETS[lvl], docs[lvl])
    if action == 'reject': b.json(ws / FOLDER / 'rejected.json', rej)
    b.commit()
    return chosen


def main(argv):
    if argv[:1] in (['confirm'], ['reject']):
        action, argv = argv[0], argv[1:]
        ap = argparse.ArgumentParser(prog=f'sdem aid {action}', description=('Confirm inferred records: you agree with them; the mark stays, with your name.' if action == 'confirm'
                                     else 'Reject inferred records: removed with their links inside the layer, and remembered so they are not inferred again.'))
        ap.add_argument('ids', nargs='*', metavar='ID'); ap.add_argument('--workspace', dest='estate', required=True, metavar='DIR')
        ap.add_argument('--person', required=True, help='your name — a person'); ap.add_argument('--all', action='store_true', help='every inferred record not yet confirmed')
        ap.add_argument('--reason', required=(action == 'reject'), help='why — kept')
        a = ap.parse_args(argv)
        try: done = decide(a.estate, a.ids, a.person, action, a.reason or '', a.all)
        except AidError as e: print(f'ERROR: {e}', file=sys.stderr); return 2
        print(f"{'confirmed' if action == 'confirm' else 'rejected'} {len(done)} inferred record(s) in {a.estate}: {', '.join(done[:8])}{' …' if len(done) > 8 else ''}")
        print('Next: commit on a branch and open a pull request.'); return 0
    ap = argparse.ArgumentParser(prog='sdem aid', formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description='Architecture Inference Design: from what the workspace has (any of A1…A4), add the records it is missing to its layer '
                                             'files — each marked inferred, with source, reasoning and confidence — and propose the connections. You review, then '
                                             '`sdem aid confirm` or `sdem aid reject` each record and `sdem approve` the connections.',
                                 epilog=__doc__.split('\n\n')[2])
    ap.add_argument('--workspace', dest='estate', required=True, metavar='DIR'); ap.add_argument('--person', required=True, help='your name — a person')
    ap.add_argument('--dry-run', action='store_true'); ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    try: rec = fill(a.estate, a.person, a.dry_run)
    except AidError as e: print(f'ERROR: {e}', file=sys.stderr); return 2
    if a.json: print(json.dumps(rec, indent=2)); return 0
    total = sum(len(v) for v in rec['added'].values())
    if not total and not rec['proposed_connections']:
        print(f"nothing to add to {a.estate} — every record AID can infer is already there" + (f" (or rejected: {len(rec['skipped_rejected'])})" if rec['skipped_rejected'] else ''))
    else:
        what = ', '.join(f'{l} {len(v)} inferred record(s)' for l, v in sorted(rec['added'].items())) or 'no new records'
        print(f"{'would add' if a.dry_run else 'added (' + rec['id'] + ')'} to {a.estate}: {what}; "
              + f"{rec['proposed_connections']} connection(s) proposed in {a.estate}/{rec['proposals']} — checked")
    for e in rec['projection_ends']: print(f'NOTE: {e}')
    if total and not a.dry_run:
        print(f'Next: review the inferred records in the layer files (marked "inferred", with source, reasoning and confidence), then '
              f'sdem aid confirm|reject <ids> --workspace {a.estate} --person <you>; review the connections: sdem review {a.estate}/{rec["proposals"]}')
    return 0
