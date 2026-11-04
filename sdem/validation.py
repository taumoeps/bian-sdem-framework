"""Four-layer impact validation (docs/design/sdem-agent-platform-spec.md §11, AG-V01…AG-V10).

A change event carries the **calculated impact** — the deterministic engine's result, stored with the event and never changed. Before
any downstream work is planned, every layer's specialist assesses it (**specialist impact assessment**), and a person accepts the
final assessment and authorises implementation (**architect-accepted impact**). One validation record per change event, in
`<workspace>/coordination/validations/IV-<event>.json`, append-only:

  validation_pending → validation_in_progress → validation_complete | architect_review_required → architect_accepted
  → implementation_authorised

Validation is not approval of cross-layer links (that stays `sdem approve`), and assessments are not work items. Records written
before this existed (change events of v0.9.14 and earlier) stay as they were: validating one recomputes its coverage from the current
graph — marked as such — and nothing is accepted or authorised for it unless a person does so now.
"""
import hashlib, json
from pathlib import Path

from .layers import CODES as LEVELS   # LR-07
STATUSES = ('impact_confirmed', 'no_impact_confirmed', 'further_investigation_required', 'impact_disputed')
CLASSIFICATIONS = ('design_change_required', 'review_required', 'no_impact')
CONFIDENCE = ('high', 'medium', 'low')
PHASES = ('validation_pending', 'validation_in_progress', 'validation_complete', 'architect_review_required', 'architect_accepted', 'implementation_authorised')
NEXT = {None: {'validation_pending'}, 'validation_pending': {'validation_in_progress'},
        'validation_in_progress': {'validation_in_progress', 'validation_complete', 'architect_review_required'},
        'validation_complete': {'validation_complete', 'architect_review_required', 'architect_accepted'},
        'architect_review_required': {'architect_review_required', 'validation_complete', 'architect_accepted'},
        'architect_accepted': {'implementation_authorised'}, 'implementation_authorised': set()}


def vid(event_id): return 'IV-' + event_id[3:]          # CE-001 → IV-001; CE-main-002 → IV-main-002


def basis(path, fg, statuses=('approved',)):
    """What a calculation rested on (AG-V02): the impact rules' version, each dataset's and the registry's checksum, the approved
    links (count and a checksum of their ids)."""
    from .graph import _IMPACT
    from .files import TRACKED
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest() if Path(p).exists() else None
    ids = sorted(e['mapping_id'] for e in fg.edges(statuses))
    return {'rules_version': _IMPACT['$schema_version'], 'files': {f: sha(Path(path) / f) for f in TRACKED if (Path(path) / f).exists()},
            'approved_links': len(ids), 'approved_links_sha256': hashlib.sha256('\n'.join(ids).encode()).hexdigest()}


def phase(v): return v['history'][-1]['phase'] if v.get('history') else None


def latest(v, layer):
    a = v['layers'][layer]['assessments']
    return a[-1] if a else None


def derive(v):
    """The validation phase the assessments put it in (before acceptance)."""
    got = [latest(v, l) for l in LEVELS]
    if not any(got): return 'validation_pending'
    if not all(got): return 'validation_in_progress'
    if any(a['status'] in ('impact_disputed', 'further_investigation_required') for a in got): return 'architect_review_required'
    if any(v['layers'][l]['calculated']['evidence'] == 'incomplete' and a['status'] == 'no_impact_confirmed' and not a.get('uncertainty')
           for l, a in zip(LEVELS, got)): return 'architect_review_required'
    return 'validation_complete'


def summary(v, current_sha=None):
    """Calculated against assessed, layer by layer — with the requirements and risk picture, records the calculation did not
    name, missing links, stale assessments — and what still stops acceptance (AG-V07, RR-G01…G03)."""
    rows, open_ = {}, []
    an = v.get('analysis') or {}
    accepted = phase(v) in ('architect_accepted', 'implementation_authorised')
    for l in LEVELS:
        c = v['layers'][l]['calculated']; a = latest(v, l); req = (an.get('layers') or {}).get(l, {})
        stale = bool(a and current_sha and an and (a.get('inputs_sha256') != current_sha or a.get('analysis_contract') != an.get('contract'))) and not accepted   # other evidence, or an earlier analysis contract
        rows[l] = {'calculated': c['classification'], 'calculated_result': c['result'], 'evidence': c['evidence'],
                   'related_within_layer': c.get('related_within_layer', []),
                   'requirements': req.get('status', 'not analysed'), 'requirements_note': req.get('note', ''),
                   'assessment': a['status'] if a else None, 'recommended': a['recommended'] if a else None, 'by': a['agent'] if a else None,
                   'agrees': (a['recommended'] == c['classification']) if a else None,
                   'additional_records': (a or {}).get('additional_records', []), 'missing_relationships': (a or {}).get('missing_relationships', []),
                   'stale': stale, 'final': (v.get('acceptance') or {}).get('final', {}).get(l)}
        if not a: open_.append(f'{l}: no assessment yet')
        elif a['status'] in ('impact_disputed', 'further_investigation_required'): open_.append(f"{l}: {a['status']} — the architect resolves it on acceptance")
        if stale: open_.append(f'{l}: assessed against evidence that has since changed — re-assess')
    risks = an.get('risks', [])
    by_type = {}
    for f in risks: by_type.setdefault(f['type'], []).append(f['id'])
    accepted_ids = {x['finding'] for x in (v.get('acceptance') or {}).get('accepted_residual_risks', [])}
    if not accepted:
        if not an: open_.append('no requirements and risk analysis — sdem events analyse')
        elif current_sha and an.get('inputs_sha256') != current_sha: open_.append('the workspace changed since the analysis — sdem events analyse, then re-assess')
        open_ += [f"{f['id']}: confirmed breach — {f['requirement']} — decide it on acceptance (--accept-risk or change the design)" for f in risks if f['type'] == 'confirmed_breach']
    return {'event': v['event'], 'phase': phase(v), 'layers': rows, 'open': open_, 'legacy': v.get('legacy', False),
            'risks': {**by_type, 'accepted_residual_risk': sorted(accepted_ids)}, 'obligations': an.get('obligations', []),
            'requirements_registry': an.get('registry', 'not analysed')}


def check(v, root_schema, check_schema, is_person, agent_layer, human):
    """Issues in one validation record (detective; `sdem check`): schema, phase order, a person on every step (CTL-20), layer
    ownership of assessments (CTL-19), acceptance by a person (CTL-21)."""
    issues = [f'{v.get("id")}: {x}' for x in check_schema(v, root_schema['$defs']['validation'], root_schema)]
    prev = None
    for h in v.get('history', []):
        if h.get('phase') not in NEXT.get(prev, set()): issues.append(f"{v.get('id')}: step {prev} → {h.get('phase')} is not allowed")
        if not is_person(h.get('person')): issues.append(f"{v.get('id')}: step {h.get('phase')} has no person (CTL-20)")
        prev = h.get('phase')
    for l, layer in (v.get('layers') or {}).items():
        for a in layer.get('assessments', []):
            if a.get('agent') != human and agent_layer.get(a.get('agent')) != l: issues.append(f"{v.get('id')}: {l} assessed by {a.get('agent')} — not that layer's agent (CTL-19)")
            if not is_person(a.get('person')): issues.append(f"{v.get('id')}: a {l} assessment has no person (CTL-20)")
    acc = v.get('acceptance')
    if acc and not is_person(acc.get('by')): issues.append(f"{v.get('id')}: accepted by {acc.get('by')!r} — acceptance is a person's decision (CTL-21)")
    if phase(v) in ('architect_accepted', 'implementation_authorised') and not acc: issues.append(f"{v.get('id')}: {phase(v)} without an acceptance")
    return issues
