"""`sdem status` — where a design is and what to do next, for the architect (ST-01…ST-05, docs/design/sdem-workbench-ux-spec.md).

One read-only view over what SDEM already works out — the checks (`sdem check`), the organisation's standards and patterns
(`sdem comply`) and what is left for a person (`sdem handback`) — sorted into three groups:

  blocking     must be fixed: a check that fails, a standard that is not met (error severity), an edit made outside SDEM
  unresolved   needs a value or a person's decision: required values nobody knows, inferences nobody confirmed, links to review,
               standards that cannot be decided, change events to plan
  warnings     worth a look: optional values unknown, possible duplicates, warning-severity rules, exceptions ending soon, the checks' advice

and the next commands, in order, each saying who runs it — a person's decision is marked and never run for them. No score and no
rules of its own: every item comes from the engine that owns it. Writes nothing.
"""
import argparse, json, sys
from pathlib import Path

from .layers import FILES


def _item(kind, text, **k): return {'kind': kind, 'text': text, **{a: b for a, b in k.items() if b is not None}}


def collect(ws):
    from .handback import collect as handback
    ws = Path(ws); h = handback(ws); w = str(ws)
    blocking, unresolved, warnings, nxt = [], [], [], []

    def step(command, why, person=False):
        if not any(s['command'] == command for s in nxt):
            nxt.append({'command': command, 'why': why, 'who': 'a person — prepare it and ask; never run it for them' if person else 'you, or an agent', 'person_decides': person})

    for e in h['check_errors']: blocking.append(_item('check', f"{e['layer']}: {e['text']}", layer=e['layer']))
    for e in h['registry_errors']: blocking.append(_item('check', f'registry: {e}'))
    for e in h['direct_edits']: blocking.append(_item('unrecorded_edit', e))
    comp = h['compliance']['findings']
    for f in comp:
        text = f"{f['rule']} on {f['layer']} {f['record']} — {f['detail']}"
        if f['outcome'] == 'non_compliant' and f.get('severity') != 'warning': blocking.append(_item('standard_not_met', text, record=f['record'], rule=f['rule']))
        elif f['outcome'] == 'non_compliant': warnings.append(_item('standard_warning', text, record=f['record'], rule=f['rule']))
        else: unresolved.append(_item('standard_unresolved', text, record=f['record'], rule=f['rule']))
    for m in h['missing_values']:
        text = f"{m['layer']} {m['id']} {m['attribute']}: {m['why']}" + (' (planned)' if m['lifecycle_status'] == 'planned' else '')
        (unresolved if m['required'] and m['lifecycle_status'] != 'planned' else warnings).append(
            _item('value_unknown' if m['required'] else 'optional_value_unknown', text, record=m['id']))
    for i in h['unconfirmed_inferred']:
        unresolved.append(_item('inferred_unconfirmed', f"{i['layer']} {i['id']} {i['name']!r} — inferred by SDEM (rule {i['rule']}, confidence {i['confidence']}"
                                + (', WEAK: a name or description only' if i['weak'] else '') + ')', record=i['id']))
    for r in h['links_to_review']: unresolved.append(_item('link_to_review', f"{r['id']} {r['link']} — proposed, confidence {r['confidence']}", link=r['id']))
    for e in h['events_to_plan']: unresolved.append(_item('event_to_plan', f"change event {e['id']} ({e['layer']}) — impact validated, not yet planned", event=e['id']))
    for d in h['possible_duplicates']:
        if not d['same_key']: warnings.append(_item('possible_duplicate', f"{d['layer']} {d['type']}: {', '.join(d['ids'])} — one record, or two? ({d['rule']})"))
    for x in h['compliance']['expiring']: warnings.append(_item('exception_expiring', f"exception {x['id']} ({x['rule']}) ends {x['expires']}"))
    for a in h['advice']: warnings.append(_item('advice', f"{a['layer']}: {a['text']}", layer=a['layer']))

    if any(b['kind'] == 'check' for b in blocking): step(f'sdem check --workspace {w}', 'see what fails, and fix it through a change set (sdem change propose)')
    if any(b['kind'] == 'unrecorded_edit' for b in blocking): step(f'sdem change adopt --workspace {w} --person <you>', 'an edit made outside SDEM: a person adopts it (or reverts it) before anything else is accepted', True)
    if any(b['kind'] == 'standard_not_met' for b in blocking) or any(u['kind'] == 'standard_unresolved' for u in unresolved):
        step(f'sdem comply --workspace {w}', "meet each of the organisation's rules — or a person grants a time-limited exception (sdem exception grant)")
    if any(u['kind'] == 'value_unknown' for u in unresolved): step(f'sdem handback --workspace {w}', 'give each unknown value, or mark its record planned, through a change set')
    if h['unconfirmed_inferred']:
        step(f'sdem aid confirm <ids> --workspace {w} --person <you>', 'confirm what SDEM inferred — or reject it: sdem aid reject <ids> …', True)
    if h['links_to_review']:
        step(f'sdem link --workspace {w} --out work/links', 'see the proposed links, weakest first')
        step(f'sdem approve <id> --proposals work/links/proposals.json --workspace {w} --reviewer <you> --evidence <kind>:<ref>', 'approve each link with its evidence', True)
    if h['events_to_plan']: step(f"sdem work plan --event {h['events_to_plan'][0]['id']} --workspace {w} --agent sdem-orchestrator --person <you>", 'plan the validated change', True)
    have = {x['level'] for x in h['layers']}; gone = [m['level'] for m in h['missing_layers']]
    if 'A1' in have and gone and not h['unconfirmed_inferred']:
        step(f'sdem aid --workspace {w} --person <you> --dry-run', f"infer what is missing ({', '.join(gone)}) from the business design — every record marked inferred until a person confirms it; then without --dry-run when the person agrees")
    if not blocking and not unresolved: step(f'sdem document --workspace {w} --layer all', 'nothing blocks the design or waits on a person: write it up, or look at it all: sdem workbench --workspace ' + w)

    state = 'blocked' if blocking else 'open' if unresolved else 'clear'
    return {'workspace': w, 'name': h['name'], 'state': state,
            'layers': h['layers'], 'missing_layers': [m['level'] for m in h['missing_layers']], 'connections': h['registry'],
            'counts': {'blocking': len(blocking), 'unresolved': len(unresolved), 'warnings': len(warnings)},
            'blocking': blocking, 'unresolved': unresolved, 'warnings': warnings, 'next': nxt,
            'sources': {'records_without_source': h['summary']['records_without_source'], 'links_without_source': h['summary']['links_without_source']}}


def render(s, limit=8):
    L = [f"{s['name']} — {'BLOCKED' if s['state'] == 'blocked' else 'OPEN: waiting on values or decisions' if s['state'] == 'open' else 'CLEAR: nothing blocks it or waits on a person'}", '']
    L.append('Layers: ' + ' · '.join(f"{x['level']} {x['records']} record(s)" for x in s['layers'])
             + (f" · missing: {', '.join(s['missing_layers'])}" if s['missing_layers'] else ''))
    by = s['connections']['by_status']
    L.append('Connections between layers: ' + (', '.join(f'{n} {k}' for k, n in sorted(by.items())) or 'none yet'))
    for title, key in (('Blocking — must be fixed', 'blocking'), ('Unresolved — needs a value or a decision', 'unresolved'), ('Warnings', 'warnings')):
        rows = s[key]
        if not rows: continue
        L += ['', f'{title} ({len(rows)})'] + [f"  {r['text']}" for r in rows[:limit]] + ([f'  … {len(rows) - limit} more (--json for all)'] if len(rows) > limit else [])
    if s['next']:
        L += ['', 'Next']
        for n, x in enumerate(s['next'], 1):
            L.append(f"  {n}. {'👤 ' if x['person_decides'] else ''}{x['command']}")
            L.append(f"     {x['why']}" + (' — a person decides' if x['person_decides'] else ''))
    return '\n'.join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem status', formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description="Where a design is and what to do next: what blocks it, what waits on a value or a person's decision, "
                                             'and what is worth a look — from sdem check, sdem comply and sdem handback, with the next commands and who runs each. Read-only.',
                                 epilog='Examples:\n  sdem status                                   # inside a workspace folder\n'
                                        '  sdem status --workspace workspaces/payments --json\n\nExit codes: 0 nothing blocks the design, 1 something blocks it, 2 not a workspace.')
    ap.add_argument('--workspace', required=True, metavar='DIR', help='the workspace folder — found from the current folder when you are inside one')
    ap.add_argument('--json', action='store_true', help='the result as JSON')
    a = ap.parse_args(argv)
    ws = Path(a.workspace)
    if not (ws / 'mappings.json').exists() or not any((ws / f).exists() for f in FILES.values()):
        print(f'ERROR: {ws}: not a workspace folder (it needs mappings.json and at least one layer dataset)', file=sys.stderr); return 2
    s = collect(ws)
    print(json.dumps(s, indent=2, ensure_ascii=False) if a.json else render(s))
    return 1 if s['state'] == 'blocked' else 0


if __name__ == '__main__':
    sys.exit(main())
