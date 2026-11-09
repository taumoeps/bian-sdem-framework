"""`sdem handback` — what a workspace leaves open for a person, as data (owner's decision D7, improvement roadmap #5; AG-H01…H03 in
docs/design/sdem-agent-platform-spec.md).

An agent ends every task by handing back what it could not decide. Read from the workspace rather than written by the agent, so it is
the same whichever agent did the work: values nobody knows yet (LC-04), records SDEM inferred and nobody confirmed (with what kind of
evidence they rest on), links to review, possible duplicates (LC-09), records with no recorded source, checks that fail, and change
events waiting for a person — each with the command the person runs. Read-only.
"""
import argparse, json, sys
from pathlib import Path

from .conformance import definitions, natural_keys, unknown_value
from .layers import FILES
from .metamodel import Metamodel
from .rules_engine import WEAK_CLASSES


def _j(p): return json.loads(Path(p).read_text(encoding='utf-8'))


def collect(ws):
    """AG-H01: everything a person must look at before the work is done — read from the workspace, never from an agent's own account."""
    from .dashboard import collect as dash
    ws = Path(ws); mm = Metamodel.load(); d = dash(ws)
    datasets = {l: _j(ws / f) for l, f in FILES.items() if (ws / f).exists()}
    missing, inferred, unsourced, duplicates = [], [], [], []
    links = {'total': 0, 'with_source': 0}
    for l, doc in datasets.items():
        for i in doc.get('instances', []):
            if not mm.known(i['type']): continue
            at = i.get('attributes') or {}; mark = at.get('inferred') if isinstance(at.get('inferred'), dict) else None
            for k, a in definitions(mm, i['type']).items():
                if a.get('status') != 'active' or k in ('inferred', 'sources'): continue
                why = ('absent' if a['required'] else None) if k not in at else unknown_value(at[k], a.get('values') or ())
                if why: missing.append({'layer': l, 'id': i['id'], 'name': i.get('name'), 'attribute': k, 'required': bool(a['required']), 'why': why,
                                        'value': at.get(k), 'lifecycle_status': i.get('lifecycle_status')})
            if mark and mark.get('status') != 'confirmed':
                ev = mark.get('evidence_class') or ''
                inferred.append({'layer': l, 'id': i['id'], 'name': i.get('name'), 'rule': mark.get('rule'), 'confidence': mark.get('confidence'),
                                 'evidence_class': ev or None, 'weak': ev in WEAK_CLASSES, 'reasoning': mark.get('reasoning')})
            elif not at.get('source_id'):
                unsourced.append({'layer': l, 'id': i['id'], 'name': i.get('name')})
        for r in doc.get('relationships', []):
            links['total'] += 1; links['with_source'] += bool(r.get('source_id'))
        groups = {}
        for rid, (exact, loose) in natural_keys(doc, mm).items(): groups.setdefault(loose, {}).setdefault(exact, []).append(rid)
        for loose, by_exact in groups.items():
            ids = sorted(x for v in by_exact.values() for x in v)
            if len(ids) > 1: duplicates.append({'layer': l, 'type': loose[0], 'ids': ids, 'same_key': any(len(v) > 1 for v in by_exact.values()),
                                                'rule': 'LC-09' if any(len(v) > 1 for v in by_exact.values()) else 'LC-09n'})
    errors = [{'layer': x['level'], 'text': e} for x in d['layers'] for e in x.get('errors', [])]
    from .agents import Estate, CoordinationError
    try: status = {r['id']: r for r in Estate(ws).status()}
    except (CoordinationError, OSError, ValueError): status = {}
    events = [{'id': e['id'], 'layer': e.get('layer'), 'change_set': e.get('change_set'), 'validation': (status.get(e['id']) or {}).get('validation')}
              for e in d['changes']['events'] if not (status.get(e['id']) or {}).get('planned')]
    review = [{'id': r['id'], 'link': f"{r['source']} {r['rel']} {r['target']}", 'confidence': r['confidence'], 'evidence_class': r.get('evidence_class'),
               'evidence_needed': r['evidence_needed']} for r in d['review']['rows']]
    w = str(ws)
    commands = []
    if errors: commands.append(f'sdem check --workspace {w}   # fix what fails first')
    if [m for m in missing if m['required'] and m['lifecycle_status'] != 'planned']:
        commands.append('leave each unknown value out and mark its record planned — or give the value — through a change set (sdem change propose)')
    if inferred: commands.append(f'sdem aid confirm <ids> --workspace {w} --person <you>   ·   sdem aid reject <ids> --workspace {w} --person <you>')
    if review: commands.append(f'sdem review <proposals.json> --workspace {w}   then   sdem approve <id> … --reviewer <you> --evidence <kind>:<ref>')
    if duplicates: commands.append('merge or rename each possible duplicate (one record, or two?) through a change set')
    if events: commands.append(f"sdem work plan --event {events[0]['id']} --workspace {w} --agent sdem-orchestrator --person <you>")
    return {'workspace': w, 'name': d['name'],
            'summary': {'check_errors': len(errors), 'missing_values': len(missing), 'missing_required': sum(m['required'] for m in missing),
                        'unconfirmed_inferred': len(inferred), 'weak_inferred': sum(x['weak'] for x in inferred), 'links_to_review': len(review),
                        'possible_duplicates': len(duplicates), 'records_without_source': len(unsourced), 'links_without_source': links['total'] - links['with_source'],
                        'events_to_plan': len(events)},
            'check_errors': errors, 'missing_values': missing, 'unconfirmed_inferred': inferred, 'links_to_review': review,
            'possible_duplicates': duplicates, 'records_without_source': unsourced, 'links': links, 'events_to_plan': events,
            'commands_for_the_person': commands}


def render(h):
    s = h['summary']; L = [f"Hand-back for {h['name']} — what is left for a person (sdem handback; read from the workspace)", '']
    def sec(title, rows, line):
        if rows: L.extend([f'{title} ({len(rows)})'] + [f'  {line(r)}' for r in rows[:40]] + (['  …'] if len(rows) > 40 else []) + [''])
    sec('Checks that fail', h['check_errors'], lambda r: f"{r['layer']}: {r['text']}")
    sec('Values nobody knows yet (LC-04)', h['missing_values'], lambda r: f"{r['layer']} {r['id']} {r['attribute']}: {r['why']}" + (f" ({r['value']!r})" if r['why'] != 'absent' else '')
        + ('' if r['required'] else ' — optional') + (' — planned' if r['lifecycle_status'] == 'planned' else ''))
    sec('Inferred by SDEM, not yet confirmed', h['unconfirmed_inferred'], lambda r: f"{r['layer']} {r['id']} {r['name']!r} — rule {r['rule']}, confidence {r['confidence']}, evidence {r['evidence_class'] or 'not recorded'}" + (' — WEAK: a name or description only' if r['weak'] else ''))
    sec('Links to review', h['links_to_review'], lambda r: f"{r['id']} {r['link']} — confidence {r['confidence']}, evidence {r['evidence_class'] or 'not recorded'}; needs {', '.join(r['evidence_needed']) or '—'}")
    sec('Possible duplicates', h['possible_duplicates'], lambda r: f"{r['layer']} {r['type']}: {', '.join(r['ids'])} ({r['rule']})")
    sec('Change events to plan', h['events_to_plan'], lambda r: f"{r['id']} ({r['layer']}, {r['change_set']})")
    L.append(f"Sources: {s['records_without_source']} record(s) with no source_id; {s['links_without_source']} of {h['links']['total']} link(s) inside the layers with no source_id")
    if h['commands_for_the_person']: L += ['', 'For the person (the agent does not run these):'] + [f'  {c}' for c in h['commands_for_the_person']]
    else: L += ['', 'Nothing is waiting on a person.']
    return '\n'.join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem handback', description='What a workspace leaves open for a person — values nobody knows, unconfirmed inferences and how strong their evidence is, links to review, possible duplicates, unsourced records, failing checks, events to plan — with the commands the person runs. Read-only; agents end every task with it (AG-H01).',
                                 epilog='Example:\n  sdem handback --workspace workspaces/payments --json', formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--workspace', required=True, metavar='DIR')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    ws = Path(a.workspace)
    if not (ws / 'mappings.json').exists() or not any((ws / f).exists() for f in FILES.values()):
        print(f'ERROR: {ws}: not a workspace folder (it needs mappings.json and at least one layer dataset)', file=sys.stderr); return 2
    h = collect(ws)
    print(json.dumps(h, indent=2, ensure_ascii=False) if a.json else render(h))
    return 0


if __name__ == '__main__':
    sys.exit(main())
