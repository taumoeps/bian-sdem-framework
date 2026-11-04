"""Requirements and risk analysis (docs/design/sdem-requirements-risk-spec.md, RR-D01…RR-G05).

Three things kept apart, all deterministic, none of them AI:
  the structural impact   (sdem/graph.py)        which records and links a change reaches;
  requirements evaluation (here)                 whether confirmed requirements hold, now and in the proposed architecture;
  risk findings           (here, schema/risk-rules.json)  confirmed breaches, potential scenarios, missing evidence, assumptions.
Their review is the existing four-layer impact validation (sdem/validation.py): the findings are stored in the change event's
validation record, every layer's agent assesses them, a person accepts — and accepts any residual risk — before implementation.

The registry is `<workspace>/requirements.json` (schema/requirements.schema.json): requirements with a **subject** (the record a
requirement is about — evaluated only there) and **allocations** (records that contribute to it; their figures never establish it),
traceable to other requirements and to A1.BusinessRequirement records; and **measurements** — stated values, current or proposed,
each with evidence. A requirement no measurement speaks to is *not evaluable*, never *satisfied*; a workspace with no registry has
*no requirements recorded*, never *no requirements*.

  sdem requirements list|show|check|trace|evaluate|propose|confirm|retire|measure
"""
import argparse, datetime, hashlib, json, re, sys
from pathlib import Path

from .paths import DATA_ROOT

FILE = 'requirements.json'
FORMAT = 'sdem-requirements/1'
SCHEMA = DATA_ROOT / 'schema' / 'requirements.schema.json'
RULES = DATA_ROOT / 'schema' / 'risk-rules.json'
from .layers import CODES as LEVELS   # LR-08
DURATION = {'ms': 0.001, 's': 1, 'sec': 1, 'min': 60, 'h': 3600, 'hr': 3600, 'd': 86400}
FINDING_TYPES = ('confirmed_breach', 'potential_risk', 'missing_evidence', 'assumption', 'remediated_breach', 'accepted_residual_risk')
CONTRACT = 2   # analysis contract: 2 = disposition per requirement; overall describes the proposed state (v0.11.2, RR-E06)
DISPOSITIONS = ('compliant', 'current_breach_remediated', 'proposed_breach', 'unresolved_breach', 'missing_evidence', 'not_confirmed')


class RequirementsError(ValueError):
    pass


def _now(): return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def load(workspace):
    f = Path(workspace) / FILE
    return json.loads(f.read_text(encoding='utf-8')) if f.exists() else None


def empty():
    from .metamodel import Metamodel
    return {'format': FORMAT, 'metamodel_version': Metamodel.load().version, 'requirements': [], 'measurements': []}


def save(workspace, reg):
    from .files import write_json
    write_json(Path(workspace) / FILE, reg)


def inputs_sha(workspace):
    """RR-G02: one checksum over everything an analysis or an assessment rests on — the four layers, the approved links, the
    requirements and their measurements. A change to any of them makes earlier assessments stale."""
    from .files import TRACKED
    h = hashlib.sha256()
    for name in sorted(set(TRACKED) | {FILE}):
        p = Path(workspace) / name
        h.update(name.encode()); h.update(p.read_bytes() if p.exists() else b'-')
    return h.hexdigest()


# ------------------------------------------------------------------ the registry's own checks (RR-D05)

def check(reg, datasets):
    """Issues in a registry: schema, unique ids, references that resolve, versions and histories that agree, confirmed
    requirements with evidence."""
    from .validate import check_schema
    schema = json.loads(SCHEMA.read_text(encoding='utf-8'))
    from . import profile as _p
    schema['$defs']['requirement']['properties']['category']['enum'] += _p.requirement_categories()   # PR-12: the organisation's categories
    issues = check_schema(reg, schema)
    known = set(schema['$defs']['requirement']['properties'])
    for r in reg.get('requirements', []):   # found by the agent baseline (2026-11-02): an unknown layer or field passed silently
        if r.get('owner_layer') not in LEVELS: issues.append(f"{r.get('id')}: owner_layer {r.get('owner_layer')!r} is not a layer of this workspace ({', '.join(LEVELS)})")
        extra = sorted(set(r) - known)
        if extra: issues.append(f"{r.get('id')}: unknown field(s) {', '.join(extra)} — a requirement has {', '.join(sorted(known))} (sdem types requirement)")
    if issues: return issues
    ids = {i['id']: i for d in datasets.values() for i in d['instances']}
    reqs = {}
    for r in reg['requirements']:
        if r['id'] in reqs: issues.append(f"{r['id']}: defined twice")
        reqs[r['id']] = r
    for r in reg['requirements']:
        for x in [r['subject']] + r.get('allocated_to', []):
            if x not in ids: issues.append(f"{r['id']}: {x} is not a record of this workspace")
        for x in r.get('derived_from', []):
            if x not in reqs and (ids.get(x) or {}).get('type') != 'A1.BusinessRequirement':
                issues.append(f"{r['id']}: derived from {x} — neither a requirement here nor an A1.BusinessRequirement record")
        h = r['history'][-1]
        if (h['version'], h['status']) != (r['version'], r['status']): issues.append(f"{r['id']}: its history ends at version {h['version']} {h['status']}, not {r['version']} {r['status']}")
        if r['status'] == 'confirmed' and not r['evidence']: issues.append(f"{r['id']}: confirmed without evidence")
    seen = set()
    for m in reg.get('measurements', []):
        if m['id'] in seen: issues.append(f"{m['id']}: defined twice")
        seen.add(m['id'])
        if m['record'] not in ids and m['state'] != 'proposed': issues.append(f"{m['id']}: {m['record']} is not a record of this workspace")   # a proposed record may not exist yet
    return issues


# ------------------------------------------------------------------ comparing a measurement with a condition (RR-E02)

def _normal(value, unit):
    if isinstance(value, bool) or value is None: return value, None
    if isinstance(value, str):
        m = re.fullmatch(r'\s*([0-9]+(?:\.[0-9]+)?)\s*(ms|s|sec|min|h|hr|d)\s*', value)
        if m: return float(m.group(1)) * DURATION[m.group(2)], 'duration'
        return value, None
    if isinstance(value, (int, float)):
        if unit in DURATION: return float(value) * DURATION[unit], 'duration'
        return float(value), unit or 'number'
    return value, None


def compare(cond, m):
    """True (holds), False (breached) or None (cannot be compared: units or kinds differ) — never a guess."""
    op, want, got = cond['operator'], cond['value'], m['value']
    if op in ('in', 'not_in'):
        if not isinstance(want, list): return None
        return (got in want) if op == 'in' else (got not in want)
    w, wk = _normal(want, cond.get('unit')); g, gk = _normal(got, m.get('unit'))
    if op in ('==', '!='):
        if wk == 'duration' or gk == 'duration':
            if wk != gk: return None
        return (w == g) if op == '==' else (w != g)
    if not isinstance(w, float) or not isinstance(g, float) or (wk != gk and not {wk, gk} <= {'number', None}): return None
    return {'>=': g >= w, '<=': g <= w, '>': g > w, '<': g < w}[op]


# ------------------------------------------------------------------ what a change touches (RR-E01, RR-E03)

def substitution(before, after):
    """RR-E03: records the change set replaces — an attribute that pointed to S now points to T (a deployment's platform moved,
    a host's workload moved). From the change set's own before/after, so the proposed architecture is read, not assumed."""
    b = {i['id']: i for i in before.get('instances', [])}; a = {i['id']: i for i in after.get('instances', [])}
    ids = set(b) | set(a); subs = {}
    for rid, rec in a.items():
        old = b.get(rid)
        if not old: continue
        for k, v in (rec.get('attributes') or {}).items():
            ov = (old.get('attributes') or {}).get(k)
            if isinstance(v, str) and isinstance(ov, str) and v != ov and v in ids and ov in ids: subs.setdefault(ov, v)
            if isinstance(v, list) and isinstance(ov, list) and k in ('deployed_on', 'platform_id', 'host', 'hosted_on'):
                gone, new = [x for x in ov if x not in v and x in ids], [x for x in v if x not in ov and x in ids]
                if len(gone) == 1 and len(new) == 1: subs.setdefault(gone[0], new[0])
    return subs


def in_scope(reg, affected, changed):
    """The requirements a change touches, and why: its subject or an allocated record is affected; or a requirement derived
    from it is in scope (traceability upward)."""
    reqs = {r['id']: r for r in reg['requirements'] if r['status'] in ('confirmed', 'proposed')}
    scope = {}
    for r in reqs.values():
        if r['subject'] in affected: scope[r['id']] = 'its subject ' + r['subject'] + (' is changed' if r['subject'] in changed else ' is affected')
        elif set(r.get('allocated_to', [])) & affected:
            scope[r['id']] = 'allocated to ' + ', '.join(sorted(set(r['allocated_to']) & affected)) + ', which the change affects'
    todo = list(scope)
    while todo:
        rid = todo.pop()
        for p in reqs[rid].get('derived_from', []):
            if p in reqs and p not in scope: scope[p] = f'{rid} is derived from it and in scope'; todo.append(p)
    return [(reqs[k], why) for k, why in sorted(scope.items())]


def _latest(meas, record, metric, state):
    hits = [m for m in meas if m['record'] == record and m['metric'] == metric and m['state'] == state]
    return hits[-1] if hits else None


def evaluate_one(req, meas, subs, affected_cls):
    """One requirement, now and in the proposed architecture — on its subject only (RR-E04)."""
    c = req['condition']; subj = req['subject']
    def judge(m, what):
        if not m: return {'result': 'not_evaluable', 'why': f'no {what} measurement of {c["metric"]} for {subj if what == "current" else proposed_subject}'}
        ok = compare(c, m)
        if ok is None: return {'result': 'not_evaluable', 'measurement': m['id'], 'why': f"{m['id']} ({m['value']} {m.get('unit', '')}) cannot be compared with the condition"}
        return {'result': 'satisfied' if ok else 'breached', 'measurement': m['id'], 'value': m['value'], 'unit': m.get('unit')}
    cur = judge(_latest(meas, subj, c['metric'], 'current'), 'current')
    proposed_subject = subs.get(subj, subj)
    pm = _latest(meas, proposed_subject, c['metric'], 'proposed') or (proposed_subject != subj and _latest(meas, proposed_subject, c['metric'], 'current')) or None
    if pm is None and proposed_subject == subj and affected_cls.get(subj) in (None, 'no_impact') and subj not in subs:
        pm = _latest(meas, subj, c['metric'], 'current'); carried = True                # not affected by the change: today's evidence carries
    else: carried = False
    prop = judge(pm, 'proposed')
    if carried and pm: prop['note'] = 'the change does not affect the subject; its current measurement carries'
    notes = []
    if proposed_subject != subj: notes.append(f'in the proposed architecture {proposed_subject} replaces {subj}')
    if req['scope'] == 'end_to_end' and cur['result'] == 'not_evaluable':
        alloc = [m['id'] for m in meas if m['record'] in req.get('allocated_to', []) and m['metric'] == c['metric']]
        if alloc: notes.append(f"measurements of allocated records ({', '.join(alloc)}) do not establish this end-to-end requirement")
    # RR-E06: the change's disposition — what it does to the requirement — from the two states, kept apart
    if req['status'] != 'confirmed': disposition = 'not_confirmed'
    elif prop['result'] == 'breached': disposition = 'unresolved_breach' if cur['result'] == 'breached' else 'proposed_breach'
    elif prop['result'] == 'not_evaluable': disposition = 'missing_evidence'
    elif cur['result'] == 'breached': disposition = 'current_breach_remediated'   # proposed satisfied by a measurement: the remediation is evidenced
    else: disposition = 'compliant'
    # overall (contract 2): the PROPOSED state — breached, missing_evidence, satisfied or not_confirmed; today's state is in `current`
    overall = {'not_confirmed': 'not_confirmed', 'proposed_breach': 'breached', 'unresolved_breach': 'breached', 'missing_evidence': 'missing_evidence'}.get(disposition, 'satisfied')
    return {'requirement': req['id'], 'version': req['version'], 'status': req['status'], 'name': req['name'], 'category': req['category'],
            'owner_layer': req['owner_layer'], 'scope': req['scope'], 'subject': subj, 'proposed_subject': proposed_subject,
            'condition': c, 'current': cur, 'proposed': prop, 'overall': overall, 'disposition': disposition, 'notes': notes}


def analyse(workspace, fg, impact_records, changed, kind, subs, coverage):
    """RR-E05/RR-K01: the requirements evaluation and the risk findings for one change — what the impact validation reviews."""
    reg = load(workspace)
    cls = {}
    for r in impact_records:
        cls[r['id']] = r['classification']
    affected = set(changed) | set(cls) | set(subs.values())
    level = lambda rid: fg.mm.level((fg.instance(rid) or {}).get('type') or '')
    out = {'contract': CONTRACT, 'registry': 'present' if reg else 'missing', 'computed_at': _now(), 'inputs_sha256': inputs_sha(workspace),
           'change_kind': kind, 'changed': list(changed), 'substitution': subs, 'requirements': [], 'layers': {}, 'obligations': [], 'risks': []}
    if reg:
        meas = reg.get('measurements', [])
        for req, why in in_scope(reg, affected, set(changed)):
            e = evaluate_one(req, meas, subs, cls); e['in_scope_because'] = why; out['requirements'].append(e)
        a1req = {i['id'] for d in fg.levels.values() for i in d.instances.values() if i['type'] == 'A1.BusinessRequirement'}
        out['obligations'] = sorted({x for e in out['requirements'] for r in reg['requirements'] if r['id'] == e['requirement'] for x in r.get('derived_from', []) if x in a1req}
                                    | {e['requirement'] for e in out['requirements'] if e['owner_layer'] == 'A1'})
    for l in LEVELS:
        mine = [e for e in out['requirements'] if e['owner_layer'] == l]
        reached = (coverage.get(l) or {}).get('reached') or any(level(x) == l for x in affected)
        count = lambda o: sum(1 for e in mine if e['overall'] == o)
        status = ('requirements_registry_missing' if not reg else 'breached' if count('breached') else 'missing_evidence' if count('missing_evidence')
                  else 'satisfied' if mine and count('satisfied') == len([e for e in mine if e['overall'] != 'not_confirmed']) and count('satisfied')
                  else 'no_requirements_recorded')
        out['layers'][l] = {'status': status, 'requirements': [e['requirement'] for e in mine], 'breached': count('breached'), 'missing_evidence': count('missing_evidence'),
                            'remediated': sum(1 for e in mine if e['disposition'] == 'current_breach_remediated'),
                            'satisfied': count('satisfied'), 'not_confirmed': count('not_confirmed'), 'structurally_reached': bool(reached),
                            'note': {'requirements_registry_missing': 'the workspace has no requirements registry — not evidence that requirements are met',
                                     'no_requirements_recorded': 'no confirmed requirement of this layer is in scope — not evidence that none applies'}.get(status, '')}
    out['risks'] = risks(out, coverage, kind, fg)
    return out


# ------------------------------------------------------------------ risk findings (RR-K01…K05)

def risks(analysis, coverage, kind, fg):
    """Findings, each one of: confirmed_breach · potential_risk · missing_evidence · assumption (accepted_residual_risk is set
    only by a person on acceptance). Scenarios, decisions and mitigations come from schema/risk-rules.json; there are no
    likelihoods, losses, obligations or targets — only what the requirements and their evidence say."""
    rules = json.loads(RULES.read_text(encoding='utf-8'))['rules']
    name = lambda rid: (fg.instance(rid) or {}).get('name') or rid
    changed = ', '.join(name(x) for x in analysis['changed'][:3])
    def rule_for(cat):
        return next((r for r in rules if r['category'] == cat and kind in r['changes']), None) or next((r for r in rules if r['category'] == '*' and kind in r['changes']), None)
    out = []
    code = {'confirmed_breach': 'BREACH', 'potential_risk': 'RISK', 'missing_evidence': 'EVIDENCE', 'assumption': 'ASSUME', 'remediated_breach': 'REMEDIATED'}
    def add(t, text, **kw):   # a stable id, from what the finding is about — the same finding keeps its id when the analysis is re-run
        out.append({'id': f"RF-{code[t]}-{kw.get('requirement') or kw.get('layer')}", 'type': t, 'text': text, **kw})
    for e in analysis['requirements']:
        if e['overall'] == 'not_confirmed': continue
        r = rule_for(e['category']); req = f"{e['requirement']} ({e['name']})"
        base = {'requirement': e['requirement'], 'layer': e['owner_layer'], 'records': sorted({e['subject'], e['proposed_subject']}),
                'evidence': [x for x in (e['current'].get('measurement'), e['proposed'].get('measurement')) if x]}
        want = f"{e['condition']['operator']} {e['condition']['value']} {e['condition'].get('unit') or ''}".strip()
        val = lambda st: f"{e[st]['value']} {e[st].get('unit') or ''}".strip()
        if e['disposition'] == 'current_breach_remediated':   # visible for the audit trail; no decision needed — the proposed state is shown to meet it
            add('remediated_breach', f"{req} is breached today ({val('current')}, against {want}); the proposed architecture meets it ({val('proposed')})", **base)
        if e['overall'] == 'breached':
            got = val('proposed')
            how = 'introduced by the change' if e['disposition'] == 'proposed_breach' else f"carried forward — breached today too ({val('current')})"
            add('confirmed_breach', f"{req} is breached in the proposed architecture: {got}, against {want} — {how}", disposition=e['disposition'],
                rule=r['id'] if r else None, decision=(r or {}).get('breach_decision', 'meet the requirement, change it with its owner, or accept the residual risk'),
                mitigations=(r or {}).get('mitigations', []), **base)
        elif e['overall'] == 'missing_evidence':
            add('missing_evidence', f"{req}: {e['proposed']['why']}" + (f"; {'; '.join(e['notes'])}" if e['notes'] else ''), decision='provide the evidence, or accept that the requirement is not shown to hold', **base)
        if r and e['overall'] != 'breached' and (e['overall'] == 'missing_evidence' or e['category'] == 'availability'):   # availability: the transition itself
            add('potential_risk', r['scenario'].format(changed=changed, requirement=req), rule=r['id'], decision=r['decision'], mitigations=r['mitigations'], **base)
    for l in LEVELS:
        lay = analysis['layers'][l]; cov = coverage.get(l) or {}
        if lay['status'] in ('requirements_registry_missing', 'no_requirements_recorded') and lay['structurally_reached']:
            add('missing_evidence', f"{l}: the change reaches this layer, but {lay['note']}", layer=l, requirement=None, records=[], evidence=[],
                decision=f'record the {l} requirements the affected records must meet, or confirm that none applies')
        if cov.get('evidence') == 'incomplete' and (lay['requirements'] or lay['structurally_reached']):
            add('assumption', f"{l}: {cov.get('unmapped_count', 0)} record(s) without approved links and {len(cov.get('unapproved_links', []))} link(s) not approved — "
                              'the analysis assumes none of them carries a requirement or a dependency this change affects', layer=l, requirement=None,
                records=cov.get('unmapped_records', [])[:10], evidence=[], decision='confirm the assumption, or add and approve the missing links')
    return out


# ------------------------------------------------------------------ the CLI

def _estate(ws):
    from .agents import Estate
    return Estate(ws)


def _graph(ws):
    errors, fg = _estate(ws).check()
    return fg


def evaluate_event(ws, event_id):
    """The analysis of a change event: its stored impact, the change set's own substitution, the current registry."""
    from .graph import impact_coverage
    est = _estate(ws)
    ev = next((e for e in est.events() if e['id'] == event_id), None)
    if not ev: raise RequirementsError(f'{event_id}: no such change event')
    coord = Path(ws) / 'coordination' / 'snapshots'
    b, a = coord / f"{ev['change_set']}.before.json", coord / f"{ev['change_set']}.json"
    subs = substitution(json.loads(b.read_text(encoding='utf-8')), json.loads(a.read_text(encoding='utf-8'))) if b.exists() and a.exists() else {}
    kinds = sorted({(r.get('cause') or '').split(' of ')[0] for r in ev['impact']['records'] if ' of ' in (r.get('cause') or '')}) or ['modify']
    fg = _graph(ws)
    cov = ev['impact'].get('coverage') or impact_coverage(fg, ev['impact']['records'], ev['impact']['changed'])
    return analyse(ws, fg, ev['impact']['records'], ev['impact']['changed'], kinds[0], subs, cov)


def evaluate_change(ws, record, kind, proposed=None):
    """Before any change set: what changing `record` would touch — structural impact, requirements, risks (RR-K06)."""
    from .graph import impact_coverage
    fg = _graph(ws)
    if not fg.instance(record): raise RequirementsError(f'{record}: no such record in {ws}')
    # --proposed may name a record that does not exist yet (the platform you plan to move to): its proposed measurements speak for it
    imp = fg.impact(record, kind)
    cov = impact_coverage(fg, imp['instances'], [record])
    res = analyse(ws, fg, imp['instances'], [record], kind, {record: proposed} if proposed else {}, cov)
    return {'structural_impact': imp, 'coverage': cov, **res}


def main(argv=None):
    from .validate import is_person
    ap = argparse.ArgumentParser(prog='sdem requirements', formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description='Requirements and constraints a workspace must keep meeting, their measurements, and what a change does to them '
                                             '(requirements evaluation and risk findings; reviewed through the four-layer impact validation).',
                                 epilog='Examples:\n  sdem requirements list --workspace ws\n  sdem requirements evaluate --workspace ws --record INF-K8S-PAY-PROD --change rehost --proposed INF-K8S-PAY-PROD2\n'
                                        '  sdem requirements evaluate --workspace ws --event CE-001\n  sdem requirements trace REQ-AV-01 --workspace ws')
    sub = ap.add_subparsers(dest='cmd', required=True)
    def ws(p): p.add_argument('--workspace', dest='estate', required=True, metavar='DIR'); p.add_argument('--json', action='store_true')
    l = sub.add_parser('list', help='the requirements, with status and subject'); ws(l); l.add_argument('--layer', choices=LEVELS); l.add_argument('--status')
    s = sub.add_parser('show', help='one requirement: condition, evidence, history and its measurements'); s.add_argument('id'); ws(s)
    c = sub.add_parser('check', help='the registry against its schema and the workspace'); ws(c)
    t = sub.add_parser('trace', help='a requirement through the layers: its subject and allocations, what they depend on and serve, and the requirements it derives from'); t.add_argument('id'); ws(t)
    e = sub.add_parser('evaluate', help='what a change does to the requirements: in scope, satisfied, breached, not evaluable — and the risk findings'); ws(e)
    e.add_argument('--event', help='a change event (its stored impact and the change set it came from)')
    e.add_argument('--record', help='or: a record you plan to change'); e.add_argument('--change', choices=['modify', 'rehost', 'replace', 'retire'], help='with --record: the kind of change')
    e.add_argument('--proposed', help='with --record: the record that will replace it (e.g. the new platform)')
    p = sub.add_parser('propose', help='add requirements, or new versions, as proposed'); p.add_argument('file', help='a JSON requirement, a list of them, or a registry ({"requirements": [...]}) — version and history are set here'); ws(p)
    p.add_argument('--person', required=True); p.add_argument('--agent', default='')
    cf = sub.add_parser('confirm', help='a person confirms proposed requirements — only confirmed requirements are evaluated as obligations'); cf.add_argument('id', nargs='+'); ws(cf); cf.add_argument('--person', required=True); cf.add_argument('--note', default='')
    rt = sub.add_parser('retire', help='a person retires requirements'); rt.add_argument('id', nargs='+'); ws(rt); rt.add_argument('--person', required=True); rt.add_argument('--reason', required=True)
    m = sub.add_parser('measure', help='record measurements — stated values with their evidence, current or proposed'); ws(m)
    m.add_argument('--from', dest='source', metavar='FILE', help='measurements from a file (a list, or {"measurements": [...]}: record, metric, value, unit, state, evidence) — each recorded against you')
    m.add_argument('--record'); m.add_argument('--metric'); m.add_argument('--value'); m.add_argument('--unit', default='')
    m.add_argument('--state', choices=['current', 'proposed'], default='current'); m.add_argument('--evidence', action='extend', nargs='+', metavar='KIND:REF')
    m.add_argument('--person', required=True); m.add_argument('--agent', default='')
    a = ap.parse_args(argv)
    try:
        reg = load(a.estate)
        if a.cmd in ('list', 'show', 'check', 'trace') and reg is None:
            raise RequirementsError(f'{a.estate}: no requirements registry ({FILE}) — no requirements are recorded; that is not evidence that none apply. '
                                    f'Add one with: sdem requirements propose <file> --workspace {a.estate} --person <name>')
        if a.cmd == 'list':
            rows = [r for r in reg['requirements'] if (not a.layer or r['owner_layer'] == a.layer) and (not a.status or r['status'] == a.status)]
            if a.json: print(json.dumps({'requirements': rows}, indent=2, ensure_ascii=False)); return 0
            for r in rows: print(f"{r['id']:<12} v{r['version']} {r['status']:<10} {r['owner_layer']} {r['category']:<15} {r['subject']:<18} {r['name']}")
            return 0
        if a.cmd == 'show':
            r = next((x for x in reg['requirements'] if x['id'] == a.id), None)
            if not r: raise RequirementsError(f'{a.id}: no such requirement')
            ms = [x for x in reg.get('measurements', []) if x['record'] in [r['subject']] + r.get('allocated_to', []) and x['metric'] == r['condition']['metric']]
            print(json.dumps({**r, 'measurements': ms}, indent=2, ensure_ascii=False)); return 0
        if a.cmd == 'check':
            issues = check(reg, _estate(a.estate).datasets())
            if a.json: print(json.dumps({'ok': not issues, 'issues': issues}, indent=2)); return 1 if issues else 0
            for i in issues: print(f'ERROR: {i}')
            if not issues: print(f"OK: {len(reg['requirements'])} requirement(s), {len(reg.get('measurements', []))} measurement(s)")
            return 1 if issues else 0
        if a.cmd == 'trace':
            r = next((x for x in reg['requirements'] if x['id'] == a.id), None)
            if not r: raise RequirementsError(f'{a.id}: no such requirement')
            fg = _graph(a.estate)
            chains = {x: {'down': fg.trace(x, 'down'), 'up': fg.trace(x, 'up')} for x in [r['subject']] + r.get('allocated_to', []) if fg.instance(x)}
            def flat(n, depth=0):
                out = []
                for c in n.get('children', []):
                    node = c['node']; out.append({'id': node['id'], 'level': node.get('level'), 'name': node.get('name'), 'via': (c.get('via') or {}).get('mapping_id'), 'depth': depth + 1})
                    out += flat(node, depth + 1)
                return out
            res = {'requirement': r['id'], 'subject': r['subject'], 'allocated_to': r.get('allocated_to', []), 'derived_from': r.get('derived_from', []),
                   'derived_by': [x['id'] for x in reg['requirements'] if r['id'] in x.get('derived_from', [])],
                   'records': {x: {'depends_on': flat(v['down']), 'serves': flat(v['up'])} for x, v in chains.items()}}
            if a.json: print(json.dumps(res, indent=2, ensure_ascii=False)); return 0
            print(f"{r['id']} ({r['owner_layer']}, {r['scope']}) — subject {r['subject']}; allocated to {', '.join(res['allocated_to']) or '—'}")
            print(f"  derived from: {', '.join(res['derived_from']) or '—'}; requirements derived from it: {', '.join(res['derived_by']) or '—'}")
            for x, v in res['records'].items():
                serves = ', '.join(str(n['level']) + ' ' + n['id'] for n in v['serves']) or '—'
                deps = ', '.join(str(n['level']) + ' ' + n['id'] for n in v['depends_on']) or '—'
                print(f'  {x}: serves {serves}; depends on {deps}')
            return 0
        if a.cmd == 'evaluate':
            if a.event: res = evaluate_event(a.estate, a.event)
            elif a.record and a.change: res = evaluate_change(a.estate, a.record, a.change, a.proposed)
            else: raise RequirementsError('give --event <CE-id>, or --record <id> --change <kind> [--proposed <id>]')
            if a.json: print(json.dumps(res, indent=2, ensure_ascii=False)); return 0
            print_analysis(res); return 0
        # governed writes
        if not is_person(a.person): raise RequirementsError(f'--person {a.person!r}: a requirement change is recorded against a person (CTL-20) — never an agent or tool')
        reg = reg or empty()
        by = f'{a.agent} for {a.person}' if getattr(a, 'agent', '') else a.person
        if a.cmd == 'propose':   # always proposed — a person confirms each (RR-D03)
            doc = json.loads(Path(a.file).read_text(encoding='utf-8'))
            items = doc['requirements'] if isinstance(doc, dict) and 'requirements' in doc else doc if isinstance(doc, list) else [doc]
            for new in items:
                new = {k: v for k, v in new.items() if k not in ('version', 'status', 'history', 'provenance')}
                old = next((x for x in reg['requirements'] if x['id'] == new.get('id')), None)
                ver = (old['version'] + 1) if old else 1
                rec = {**new, 'version': ver, 'status': 'proposed', 'evidence': new.get('evidence', []), 'provenance': {'by': by, 'at': _now(), 'source': new.get('source', a.file)},
                       'history': (old['history'] if old else []) + [{'version': ver, 'status': 'proposed', 'by': by, 'at': _now(), 'note': 'proposed' if not old else f"new version of v{old['version']}"}]}
                rec.pop('source', None)
                reg['requirements'] = [x for x in reg['requirements'] if x['id'] != rec['id']] + [rec]
        elif a.cmd in ('confirm', 'retire'):
            if a.cmd == 'confirm' and (a.agent if hasattr(a, 'agent') else ''): raise RequirementsError('confirming a requirement is a person\'s decision (CTL-21)')
            for rid in (a.id if isinstance(a.id, list) else [a.id]):
                r = next((x for x in reg['requirements'] if x['id'] == rid), None)
                if not r: raise RequirementsError(f'{rid}: no such requirement')
                if a.cmd == 'confirm' and r['status'] != 'proposed': raise RequirementsError(f"{rid} is {r['status']} — only a proposed requirement is confirmed")
                if a.cmd == 'confirm' and not r['evidence']: raise RequirementsError(f'{rid} has no evidence — a confirmed requirement names where it comes from')
                r['status'] = 'confirmed' if a.cmd == 'confirm' else 'retired'
                r['history'].append({'version': r['version'], 'status': r['status'], 'by': a.person, 'at': _now(), 'note': a.note if a.cmd == 'confirm' else a.reason})
        else:   # measure — each recorded against the person (and agent) running it, whatever the file says (RR-D02)
            if a.source:
                doc = json.loads(Path(a.source).read_text(encoding='utf-8'))
                items = doc['measurements'] if isinstance(doc, dict) else doc
            else:
                if not (a.record and a.metric and a.value is not None and a.evidence): raise RequirementsError('give --record, --metric, --value and --evidence, or --from FILE')
                val = a.value
                try: val = json.loads(a.value)
                except ValueError: pass
                items = [{'record': a.record, 'metric': a.metric, 'value': val, 'unit': a.unit, 'state': a.state, 'evidence': a.evidence}]
            for x in items:
                if not x.get('evidence'): raise RequirementsError(f"a measurement of {x.get('record')} {x.get('metric')} has no evidence — none is recorded without it")
                n = 1 + max([int(re.sub(r'\D', '', y['id']) or 0) for y in reg.get('measurements', [])] or [0])
                reg.setdefault('measurements', []).append({'id': f'MEAS-{n:03d}', 'record': x['record'], 'metric': x['metric'], 'value': x['value'], **({'unit': x['unit']} if x.get('unit') else {}),
                                                          'state': x.get('state', 'current'), 'evidence': list(x['evidence']), 'provenance': {'by': by, 'at': _now(), **({'source': a.source} if a.source else {})}})
        issues = check(reg, _estate(a.estate).datasets())
        if issues: raise RequirementsError('the registry would not pass its checks — nothing written:\n  ' + '\n  '.join(issues[:10]))
        save(a.estate, reg)
        if a.cmd in ('confirm', 'retire'):   # GV-01: a person's decision, attributed
            from .governance import record
            for rid in a.id: record(a.estate, f'{a.cmd}_requirement', a.person, rid)   # --dry-run: sdem's sandbox catches the write (AF-04)
        print(json.dumps({'ok': True, 'requirements': len(reg['requirements']), 'measurements': len(reg.get('measurements', []))}) if a.json else f"{a.cmd}: done — {FILE} checked and written")
        return 0
    except RequirementsError as err:
        from .errors import note
        m = str(err); note('needs_person' if 'person' in m else 'not_found' if 'no such' in m or 'no requirements registry' in m else 'refused')
        print(f'ERROR: {err}', file=sys.stderr); return 2 if 'no such' in m or 'give --event' in m else 1


def print_analysis(res):
    if 'structural_impact' in res:
        print(f"STRUCTURAL IMPACT of {res['structural_impact']['change']} on {res['structural_impact']['changed']}:")
        for l, c in res['coverage'].items(): print(f"  {l}  {c['result']:<20} evidence {c['evidence']:<10} records {', '.join(r['id'] for r in c['records']) or '—'}")
    if res['substitution']: print('PROPOSED: ' + '; '.join(f'{b} replaces {a}' for a, b in res['substitution'].items()))
    print(f"\nREQUIREMENTS ({'registry ' + res['registry']}):")
    for e in res['requirements']:
        print(f"  {e['requirement']:<12} {e['owner_layer']} {e['category']:<15} {e.get('disposition', e['overall']):<26} now {e['current']['result']:<14} proposed {e['proposed']['result']:<14} {e['name']}")
        for n in e['notes']: print(f'      note: {n}')
    print('\nBY LAYER (structural impact and requirements are separate — no structural change is not no risk):')
    for l, x in res['layers'].items(): print(f"  {l}  {x['status']:<30} {x['note']}")
    if res['obligations']: print(f"\nA1 OBLIGATIONS EXPOSED: {', '.join(res['obligations'])}")
    print('\nRISK FINDINGS (no likelihoods or losses — only what the requirements and their evidence say):')
    for f in res['risks']:
        print(f"  {f['id']} {f['type']:<17} {f['text']}")
        if f.get('decision'): print(f"         decision: {f['decision']}")
