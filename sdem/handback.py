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
    first_load = set()   # IN-13: the change events of a design's first load (sdem intake) — nothing existed before them, so nothing is planned from them
    try:
        import json as _jf
        from pathlib import Path as _Pf
        first_load = set(_jf.loads((_Pf(ws) / 'intake' / 'first-load.json').read_text(encoding='utf-8')).get('events', []))
    except (OSError, ValueError): pass
    events = [{'id': e['id'], 'layer': e.get('layer'), 'change_set': e.get('change_set'), 'validation': (status.get(e['id']) or {}).get('validation')}
              for e in d['changes']['events'] if not (status.get(e['id']) or {}).get('planned') and e['id'] not in first_load]
    review = [{'id': r['id'], 'link': f"{r['source']} {r['rel']} {r['target']}", 'confidence': r['confidence'], 'evidence_class': r.get('evidence_class'),
               'evidence_needed': r['evidence_needed']} for r in d['review']['rows']]
    rejected = []   # RJ-07: links a person rejected — decided, listed apart from those still to review
    try:
        import json as _json
        from pathlib import Path as _P
        ms = _json.loads((_P(ws) / 'mappings.json').read_text(encoding='utf-8')).get('mappings', [])
        k = lambda m: (m['source']['id'], m['relationship'], m['target']['id'])
        ok = {k(m) for m in ms if m.get('status') == 'approved'}
        rejected = [{'id': m['mapping_id'], 'link': ' '.join(k(m)), 'by': m.get('reviewer_id'), 'on': m.get('approved_at'), 'reason': (m.get('rationale') or '').split(' — as proposed:')[0]}
                    for m in ms if m.get('status') == 'rejected' and k(m) not in ok]
    except (OSError, ValueError, KeyError): pass
    comp = {'findings': [], 'expiring': []}
    try:
        from .comply import collect as comply
        from .exceptions import listing
        c = comply(ws)
        if c['profile_active']:
            comp['findings'] = [{k: f.get(k) for k in ('rule', 'standard', 'pattern', 'layer', 'record', 'outcome', 'severity', 'detail')}
                                for f in c['findings'] if f['outcome'] in ('non_compliant', 'unresolved')]
            comp['expiring'] = [e for e in listing(ws) if e['state'] == 'active' and e['days_left'] <= 30]
            done = [f for f in c['findings'] if (f.get('standard') or {}).get('id') == 'SDEM-COMPLETE']   # CPL-05: SDEM's standard for a complete design, as one figure
            if done:
                gaps = [f for f in done if f['outcome'] in ('non_compliant', 'unresolved')]; by = {}
                for f in gaps: by.setdefault(f['rule'], {'rule': f['rule'], 'message': f.get('message') or f['detail'], 'records': []})['records'].append(f['record'])
                checked = {f['record'] for f in done}; open_ = {f['record'] for f in gaps}
                only = 0   # AID-D01: records that meet the standard only through a link SDEM inferred and nobody has confirmed — connected in the draft, still to confirm
                try:
                    from .comply import workspace_data, evaluate as _ev
                    from . import profile as _pc
                    ds, maps_, mm_c, _ = workspace_data(ws)
                    unc = lambda r: isinstance(r.get('inferred'), dict) and r['inferred'].get('status') != 'confirmed'
                    if any(unc(r) for d in ds.values() for r in d.get('relationships', [])):
                        bare = {l: {**d, 'relationships': [r for r in d.get('relationships', []) if not unc(r)]} for l, d in ds.items()}
                        rules_ = [r for r in _pc.rules() if (r.get('standard') or {}).get('id') == 'SDEM-COMPLETE']
                        without = {f['record'] for f in _ev(bare, maps_, mm_c, rules_, _pc.exceptions()) if f['outcome'] in ('non_compliant', 'unresolved')}
                        only = len(without - open_)
                except (ValueError, OSError): pass
                defaults, covered = 0, set()   # CPL-15: what the draft rests on — links placed by default (AID-D08), and gaps a link proposed between layers would close once a person approves it
                try:
                    import json as _j2
                    from pathlib import Path as _P2
                    defaults = sum(1 for d in ds.values() for r in d.get('relationships', []) if unc(r) and r['inferred'].get('default'))
                    reg = _j2.loads((_P2(ws) / 'mappings.json').read_text(encoding='utf-8')).get('mappings', [])
                    decided = {(m['source']['id'], m['relationship'], m['target']['id']) for m in reg if m.get('status') in ('approved', 'rejected')}
                    props = set()
                    for pf in sorted((_P2(ws) / 'aid').glob('*-proposals.json')) + [_P2(ws) / 'links' / 'proposals.json']:
                        if pf.exists(): props |= {(m['source']['id'], m['relationship'], m['target']['id']) for m in _j2.loads(pf.read_text(encoding='utf-8')).get('mappings', [])}
                    props -= decided
                    rules_by = {r['id']: r for r in _pc.rules()}
                    for f in gaps:
                        a_ = (rules_by.get(f['rule']) or {}).get('across')
                        if a_ and any(r == a_['relationship'] and (t if a_.get('direction') == 'in' else s) == f['record'] for s, r, t in props): covered.add((f['rule'], f['record']))
                except (ValueError, OSError, NameError, KeyError): pass
                comp['completeness'] = {'standard': 'SDEM-COMPLETE', 'records_checked': len(checked), 'records_connected': len(checked - open_), 'gaps': len(gaps), 'inferred_to_confirm': only,
                                        'placed_by_default': defaults, 'proposed_to_approve': len({r for _, r in covered}),
                                        'draft_connected': len(checked - {f['record'] for f in gaps if (f['rule'], f['record']) not in covered}),
                                        'under_exception': sum(f['outcome'] == 'exception_approved' for f in done),
                                        'by_rule': [{**v, 'records': sorted(v['records'])} for v in sorted(by.values(), key=lambda v: (-len(v['records']), v['rule']))]}
            from . import profile as _p   # CPL-11: where the design stands against each pattern SDEM ships — one block a pattern and record, not a line a part
            ship = _p.shipped_included(); anchors = {st['pattern']['id']: st['structure']['anchor'] for st in _p.structures()}; groups = {}
            for f in c['findings']:
                pid = (f.get('pattern') or {}).get('id')
                if pid in ship and f.get('part'): groups.setdefault((pid, f['record']), []).append(f)
            comp['patterns'] = []; in_draft = {}
            try:   # CPL-15 for patterns: the same parts counting what is proposed between layers and not yet decided
                import json as _j3
                from pathlib import Path as _P3
                from .comply import workspace_data as _wd
                from .patterns import evaluate as _pe
                ds3, maps3, mm3, _ = _wd(ws)
                reg3 = _j3.loads((_P3(ws) / 'mappings.json').read_text(encoding='utf-8')).get('mappings', [])
                dec3 = {(m['source']['id'], m['relationship'], m['target']['id']) for m in reg3 if m.get('status') in ('approved', 'rejected')}
                pr3 = set()
                for pf in sorted((_P3(ws) / 'aid').glob('*-proposals.json')) + [_P3(ws) / 'links' / 'proposals.json']:
                    if pf.exists(): pr3 |= {(m['source']['id'], m['relationship'], m['target']['id']) for m in _j3.loads(pf.read_text(encoding='utf-8')).get('mappings', [])}
                for f in _pe(ds3, list(maps3) + sorted(pr3 - dec3), mm3, _p.structures(), _p.exceptions())[0]:
                    if f['part']['kind'] == 'role' and f['part']['id'] != anchors.get(f['pattern']['id']) and (f['outcome'] == 'compliant' or 'inferred, not yet confirmed' in (f.get('detail') or '')):
                        in_draft[(f['pattern']['id'], f['record'])] = in_draft.get((f['pattern']['id'], f['record']), 0) + 1
            except (ValueError, OSError, KeyError): pass
            for (pid, rid), fs in sorted(groups.items()):
                roles = [f for f in fs if f['part']['kind'] == 'role' and f['part']['id'] != anchors.get(pid)]
                comp['patterns'].append({'pattern': pid, 'title': fs[0]['pattern'].get('title'), 'anchor': rid, 'parts': len(roles), 'in_place': sum(f['outcome'] == 'compliant' for f in roles),
                                         'draft_in_place': max(in_draft.get((pid, rid), 0), sum(f['outcome'] == 'compliant' for f in roles)),
                                         'under_exception': sum(f['outcome'] == 'exception_approved' for f in fs),
                                         'open': [{'part': f['part']['id'], 'label': f['part']['label'], 'outcome': f['outcome'], 'detail': f['detail'], 'why': f['part'].get('reasoning')} for f in fs if f['outcome'] in ('non_compliant', 'unresolved')]})
        from .comply import workspace_data   # CPL-09: a pattern SDEM ships that fits this design and is not included
        ds, _, mm_, _ = workspace_data(ws)
        from . import profile as _p2
        comp['patterns_available'] = _p2.available(ds, mm_)
    except ValueError: pass   # a profile that does not pass its checks is in check_errors already
    w = str(ws)
    commands = []
    if errors: commands.append(f'sdem check --workspace {w}   # fix what fails first')
    if [m for m in missing if m['required'] and m['lifecycle_status'] != 'planned']:
        commands.append('leave each unknown value out and mark its record planned — or give the value — through a change set (sdem change propose)')
    if inferred: commands.append(f'sdem aid confirm <ids> --workspace {w} --person <you>   ·   sdem aid reject <ids> --workspace {w} --person <you>')
    if review: commands.append(f'sdem review <proposals.json> --workspace {w}   then   sdem approve <id> … --reviewer <you> --evidence <kind>:<ref>')
    if duplicates: commands.append('merge or rename each possible duplicate (one record, or two?) through a change set')
    if comp['findings']: commands.append(f'sdem comply --workspace {w}   # meet each standard, or ask for a time-limited exception: sdem exception grant … --person <you>')
    if comp['expiring']: commands.append(f'sdem exception list --workspace {w}   # exceptions ending within 30 days')
    if events: commands.append(f"sdem work plan --event {events[0]['id']} --workspace {w} --agent sdem-orchestrator --person <you>")
    return {'workspace': w, 'name': d['name'],
            'summary': {'check_errors': len(errors), 'missing_values': len(missing), 'missing_required': sum(m['required'] for m in missing),
                        'unconfirmed_inferred': len(inferred), 'weak_inferred': sum(x['weak'] for x in inferred), 'links_to_review': len(review), 'links_rejected': len(rejected),
                        'possible_duplicates': len(duplicates), 'records_without_source': len(unsourced), 'links_without_source': links['total'] - links['with_source'],
                        'events_to_plan': len(events), 'standards_not_met': sum(f['outcome'] == 'non_compliant' for f in comp['findings']),
                        'standards_unresolved': sum(f['outcome'] == 'unresolved' for f in comp['findings']), 'exceptions_expiring': len(comp['expiring'])},
            'check_errors': errors, 'missing_values': missing, 'unconfirmed_inferred': inferred, 'links_to_review': review, 'links_rejected': rejected,
            'possible_duplicates': duplicates, 'records_without_source': unsourced, 'links': links, 'events_to_plan': events, 'compliance': comp,
            'commands_for_the_person': commands,
            # read by sdem status (ST-01): the registry's own errors, the checks' advice, edits made outside SDEM, and the layers' size
            'registry_errors': d['registry']['errors'], 'advice': [{'layer': x['level'], 'text': e} for x in d['layers'] for e in x.get('advice', [])],
            'direct_edits': d['changes']['direct_edits'], 'layers': [{'level': x['level'], 'title': x['title'], 'records': x['records'], 'relationships': x['relationships']} for x in d['layers']],
            'missing_layers': d['missing_layers'], 'registry': {'links': d['registry']['links'], 'by_status': d['registry']['by_status']}}


def render(h):
    s = h['summary']; L = [f"Hand-back for {h['name']} — what is left for a person (sdem handback; read from the workspace)", '']
    def sec(title, rows, line):
        if rows: L.extend([f'{title} ({len(rows)})'] + [f'  {line(r)}' for r in rows[:40]] + (['  …'] if len(rows) > 40 else []) + [''])
    sec('Checks that fail', h['check_errors'], lambda r: f"{r['layer']}: {r['text']}")
    sec('Values nobody knows yet (LC-04)', h['missing_values'], lambda r: f"{r['layer']} {r['id']} {r['attribute']}: {r['why']}" + (f" ({r['value']!r})" if r['why'] != 'absent' else '')
        + ('' if r['required'] else ' — optional') + (' — planned' if r['lifecycle_status'] == 'planned' else ''))
    sec('Inferred by SDEM, not yet confirmed', h['unconfirmed_inferred'], lambda r: f"{r['layer']} {r['id']} {r['name']!r} — rule {r['rule']}, confidence {r['confidence']}, evidence {r['evidence_class'] or 'not recorded'}" + (' — WEAK: a name or description only' if r['weak'] else ''))
    sec('Links to review', h['links_to_review'], lambda r: f"{r['id']} {r['link']} — confidence {r['confidence']}, evidence {r['evidence_class'] or 'not recorded'}; needs {', '.join(r['evidence_needed']) or '—'}")
    sec('Links a person rejected (not proposed again — sdem approve overrides)', h.get('links_rejected') or [], lambda r: f"{r['id']} {r['link']} — {r['reason']} ({r['on']})")
    sec('Possible duplicates', h['possible_duplicates'], lambda r: f"{r['layer']} {r['type']}: {', '.join(r['ids'])} ({r['rule']})")
    sec("Standards and patterns not met or unresolved (sdem comply)", h['compliance']['findings'],
        lambda r: f"{r['outcome'].replace('_', '-')}: {r['rule']} on {r['layer']} {r['record']} — {r['detail']}")
    sec('Exceptions ending within 30 days', h['compliance']['expiring'], lambda r: f"{r['id']} {r['rule']} for {', '.join(r['records'])} — until {r['expires']}")
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
