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
from .identity import T as _T, layer as _L  # ST-01…ST-05: layers and types by id (docs/design/sdem-stable-identity-spec.md)
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
    complete = h['compliance'].get('completeness')   # CPL-05: said once, as a figure — not a line per gap
    pats = h['compliance'].get('patterns') or []; avail = h['compliance'].get('patterns_available') or []   # CPL-11, CPL-09
    for f in comp:
        if complete and (f.get('standard') or {}).get('id') == 'SDEM-COMPLETE': continue
        if (f.get('pattern') or {}).get('id') in {p['pattern'] for p in pats}: continue
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
    said = ([f": {r['rule']} —" for r in complete['by_rule']] if complete else []) + [f": {p['pattern']}/" for p in pats]   # CPL-05, CPL-11: sdem check's own line for a gap already in a summary above
    for a in h['advice']:
        if any(k in a['text'] for k in said): continue
        warnings.append(_item('advice', f"{a['layer']}: {a['text']}", layer=a['layer']))

    if any(b['kind'] == 'check' for b in blocking): step(f'sdem check --workspace {w}', 'see what fails, and fix it through a change set (sdem change propose)')
    if any(b['kind'] == 'unrecorded_edit' for b in blocking): step(f'sdem change adopt --workspace {w} --person <you>', 'an edit made outside SDEM: a person adopts it (or reverts it) before anything else is accepted', True)
    # CPL-17: the steps of a complete first draft, in the one order (the skill sdem-complete-draft): standards and patterns first, then infer, then every
    # proposed link in one list, then look, then a person decides — whoever follows this list does them in that order
    for x in avail:
        step(f"sdem profile include {x['include']} --workspace {w} --person <you>", f"a pattern for this kind of solution ships with SDEM ({x['title']}, because of {x['because']}) — including it checks the design has what such a solution needs", True)
    draft_open = bool(complete and complete.get('draft_connected', complete['records_connected']) < complete['records_checked']) or any(p.get('draft_in_place', p['in_place']) < p['parts'] for p in pats)
    if draft_open and not blocking:
        step(f'sdem aid --workspace {w} --person <you> --complete-draft --dry-run', 'complete the first draft: SDEM asks the standards and every pattern that fits, then infers what is missing — each item marked inferred, a gap with no evidence placed by default and marked so; then without --dry-run when the person agrees')
    if h['links_to_review'] or (draft_open and not blocking):
        step(f'sdem link --workspace {w} --out work/links', 'every proposed link between layers in one list, weakest first')
    if complete and complete['gaps']:
        step(f'sdem comply --workspace {w}', f"see each of the {complete['gaps']} gap(s) in the design's connections — link the record through a change set, or a person grants an exception (sdem exception grant)")
    for p in pats:
        if p['open']: step(f"sdem pattern draw --id {p['pattern']} --workspace {w} --anchor {p['anchor']} -o pattern.html", f"see the {p['title']} pattern drawn over the design — which parts are there, which are missing; add a part through a change set, or a person grants an exception")
    if any(b['kind'] == 'standard_not_met' for b in blocking) or any(u['kind'] == 'standard_unresolved' for u in unresolved):
        step(f'sdem comply --workspace {w}', "meet each of the organisation's rules — or a person grants a time-limited exception (sdem exception grant)")
    if any(u['kind'] == 'value_unknown' for u in unresolved): step(f'sdem handback --workspace {w}', 'give each unknown value, or mark its record planned, through a change set')
    if complete and complete.get('inferred_to_confirm'):
        step(f"sdem aid confirm '<source|kind|target>' --workspace {w} --person <you>", f"{complete['inferred_to_confirm']} record(s) are connected only by a link SDEM inferred from names — confirm each, or reject it: sdem aid reject … --reason … (sdem handback lists them)", True)
    if h['unconfirmed_inferred']:
        step(f'sdem aid confirm <ids> --workspace {w} --person <you>', 'confirm what SDEM inferred — or reject it: sdem aid reject <ids> …', True)
    if h['links_to_review']:
        step(f'sdem approve <id> --proposals work/links/proposals.json --workspace {w} --reviewer <you> --evidence <kind>:<ref>', 'approve each link with its evidence', True)
    if h['events_to_plan']: step(f"sdem work plan --event {h['events_to_plan'][0]['id']} --workspace {w} --agent sdem-orchestrator --person <you>", 'plan the validated change', True)
    have = {x['level'] for x in h['layers']}; gone = [m['level'] for m in h['missing_layers']]
    if _L('business') in have and gone and not h['unconfirmed_inferred']:
        step(f'sdem aid --workspace {w} --person <you> --dry-run', f"infer what is missing ({', '.join(gone)}) from the business design — every record marked inferred until a person confirms it; then without --dry-run when the person agrees")
    if not blocking and not unresolved and not (complete and (complete['gaps'] or complete.get('inferred_to_confirm'))) and not any(p['open'] for p in pats): step(f'sdem document --workspace {w} --layer all', 'nothing blocks the design or waits on a person: write it up, or look at it all: sdem workbench --workspace ' + w)

    try: gap = _objects_gap(ws)   # BO-06
    except Exception: gap = None
    if gap:
        warnings.append(_item('bian_objects_missing', f"BIAN: {gap['service_domains']} service domain(s) but no BIAN business object — the design's BIAN → Data connections are empty (BO-06)"))
        step(f'sdem bian objects suggest --workspace {w}', 'which BIAN business object each data entity may be — a person brings one in (--object) and states the link (sdem connect … MAPPED_TO …)')

    try:
        from .dataarch import gaps as data_gaps   # DAR-07: the Data Architecture's own finding — only once the design uses it
        dg = data_gaps(ws)
    except Exception: dg = None
    if dg:
        if dg['no_domain']: warnings.append(_item('data_entity_without_domain', f"Data: {len(dg['no_domain'])} data entit(ies) in no data domain — {', '.join(dg['no_domain'][:5])} (DAR-07)"))
        if dg['no_owner']: warnings.append(_item('personal_data_without_owner', f"Data: {len(dg['no_owner'])} data entit(ies) holding personal data with no data_owner — {', '.join(dg['no_owner'][:5])} (DAR-07)"))
        if dg['no_mode']:
            warnings.append(_item('personal_data_access_mode_not_stated', f"Data: {len(dg['no_mode'])} access link(s) to personal data with no read or write stated — {', '.join(dg['no_mode'][:5])} (DAR-07)"))
            step(f'sdem data mode {dg["no_mode"][0]} read|write|read_write --workspace {w} --person <you> --rationale "…"', 'a person states whether each access to personal data reads, writes or both')

    state = 'blocked' if blocking else 'open' if unresolved or (complete and (complete['gaps'] or complete.get('inferred_to_confirm'))) or any(p['open'] for p in pats) else 'clear'
    return {'workspace': w, 'name': h['name'], 'state': state,
            'layers': h['layers'], 'missing_layers': [m['level'] for m in h['missing_layers']], 'connections': h['registry'],
            'counts': {'blocking': len(blocking), 'unresolved': len(unresolved), 'warnings': len(warnings)},
            'blocking': blocking, 'unresolved': unresolved, 'warnings': warnings, 'next': nxt, 'completeness': complete, 'patterns': pats, 'patterns_available': avail,
            'sources': {'records_without_source': h['summary']['records_without_source'], 'links_without_source': h['summary']['links_without_source']}}


def render(s, limit=8):
    L = [f"{s['name']} — {'BLOCKED' if s['state'] == 'blocked' else 'OPEN: waiting on values or decisions' if s['state'] == 'open' else 'CLEAR: nothing blocks it or waits on a person'}", '']
    L.append('Layers: ' + ' · '.join(f"{x['level']} {x['records']} record(s)" for x in s['layers'])
             + (f" · missing: {', '.join(s['missing_layers'])}" if s['missing_layers'] else ''))
    by = s['connections']['by_status']
    L.append('Connections between layers: ' + (', '.join(f'{n} {k}' for k, n in sorted(by.items())) or 'none yet'))
    c = s.get('completeness')
    if c and c['records_checked']:   # CPL-05
        pct = round(100 * c['records_connected'] / c['records_checked'])
        L.append(f"Completeness: {c['records_connected']} of {c['records_checked']} records connected ({pct}%)" + (f" — {c['gaps']} gap{'s' if c['gaps'] != 1 else ''}" if c['gaps'] else ' — no gaps')
                 + (f", {c['inferred_to_confirm']} record{'s' if c['inferred_to_confirm'] != 1 else ''} connected only by an inferred link, to confirm" if c.get('inferred_to_confirm') else '')
                 + (f", {c['under_exception']} under an exception" if c.get('under_exception') else ''))
        if c.get('inferred_to_confirm') or c.get('proposed_to_approve'):   # CPL-15: the draft, and what it rests on
            rests = ([f"{c['inferred_to_confirm']} inferred, to confirm" + (f" ({c['placed_by_default']} placed by default with no evidence — review first)" if c.get('placed_by_default') else '')] if c.get('inferred_to_confirm') else []) \
                    + ([f"{c['proposed_to_approve']} by a proposed link between layers, to approve"] if c.get('proposed_to_approve') else [])
            L.append(f"Draft: {c['draft_connected']} of {c['records_checked']} records connected counting what is inferred or proposed — " + '; '.join(rests))
        L += [f"  {len(r['records'])} × {r['message']}: {', '.join(r['records'][:4])}{' …' if len(r['records']) > 4 else ''}" for r in c['by_rule'][:6]]
    for p in s.get('patterns') or []:   # CPL-11
        n = len(p['open'])
        L.append(f"Pattern {p['title']} ({p['anchor']}): {p['in_place']} of {p['parts']} parts in place" + (f' — {n} to decide' if n else ' — nothing missing')
                 + (f"; in the draft: {p['draft_in_place']} of {p['parts']} counting what is inferred or proposed" if p.get('draft_in_place', 0) > p['in_place'] else '')
                 + (f", {p['under_exception']} under an exception" if p.get('under_exception') else ''))
        L += [f"  {o['detail']}" + (f" — why: {o['why']}" if o.get('why') else '') for o in p['open'][:6]] + ([f"  … and {n - 6} more (sdem comply)"] if n > 6 else [])
    for x in s.get('patterns_available') or []:   # CPL-09
        L.append(f"A pattern for this kind of solution ships with SDEM: {x['title']} — a person includes it: sdem profile include {x['include']} --workspace {s['workspace']} --person <you>")
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


def _objects_gap(workspace):
    """BO-06: a design that holds BIAN service domains but no BIAN business object — its BIAN → Data connections are empty. None otherwise."""
    from . import parts
    from .identity import F as _F, T as _T, load as _jload
    if not parts.bian_on(): return None
    p = Path(workspace) / _F('bian')
    if not p.is_file(): return None
    recs = [i for i in (_jload(p).get('instances') or []) if isinstance(i, dict)]
    sds = sum(1 for i in recs if i.get('type') == _T('bian.ServiceDomain'))
    if not sds or any(i.get('type') == _T('bian.BusinessObject') for i in recs): return None
    return {'service_domains': sds}
