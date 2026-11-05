"""Agent platform coordination — change sets, change events, impact results, work items (docs/design/sdem-agent-platform-spec.md).

The layer agents (A1–A4) and the orchestrator coordinate only through these records, never by messaging each other
(AG-D02). They are stored with the workspace, in `<workspace>/coordination/`, append-only (AG-R05):

  change-sets/CS-….json     one layer's proposed record changes, with agent and person (AG-R01)
  events/CE-….json          change events, each with its stored impact result (AG-R02, AG-R03)
  work-items/WI-….json      one task for one layer, with its history of states (AG-R04)

One file per record, and ids scoped to the Git branch they were made on (CS-<branch>-001; plain CS-001 on main or
outside Git), so agents working on different branches never create the same id or edit the same file.

Controls: CTL-19 layer ownership (a change set changes one declared layer; an agent only its own layer; never the
registry), CTL-20 change provenance (agent and person on every change set and work-item step). A change set lands only
if the workspace's checks show no new error (the metamodel, CTL-01…17).
"""
import copy, datetime, json, re, subprocess
from pathlib import Path

from .graph import FederatedGraph
from .metamodel import Metamodel, PROJECTED_PREFIXES
from .validate import is_person
from .validate import check_schema

from .paths import DATA_ROOT
SCHEMA = DATA_ROOT / 'schema' / 'coordination.schema.json'
from .layers import FILES, AGENTS as AGENT_LAYER, CODES   # LR-02: layer → file, layer agent → layer — the profile's layers included
REGISTRY = 'mappings.json'
ORCHESTRATOR = 'sdem-orchestrator'
HUMAN = 'architect'                       # a person working without an agent may change any one layer
KIND_OF = {'update': 'modify', 'retire': 'retire', 'add': None}
TEXT_FIELDS = {'name', 'description'}   # AG-V11: an update that changes only these is documentation — no structural impact
STRENGTH = {'design_change_required': 3, 'review_required': 2, 'no_impact': 1}
MAX_ROUNDS = 3                            # AG-S07 / AG-Q02


class CoordinationError(Exception):
    """A request the controls reject; the message names the control."""


class EstateNotFound(ValueError):
    """The folder is not a workspace — an input error (exit 2), not a refusal."""


def _now(): return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
def _j(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def _w(p, obj):
    from .files import write_json
    write_json(p, obj)   # in one step — never a half-written record


class Estate:
    """A workspace folder: the four architecture datasets, the registry, and the coordination records."""

    def __init__(self, path, now=None):
        self.path = Path(path); self.coord = self.path / 'coordination'; self.now = now or _now
        if not (self.path / REGISTRY).exists() or not any((self.path / f).exists() for f in FILES.values()):   # one to four layers, as everywhere
            raise EstateNotFound(f'{self.path}: not a workspace folder (it needs {REGISTRY} and at least one of {", ".join(FILES.values())})')
        from . import profile as _p
        _p.activate_from(self.path)   # PR-07

    # -- records
    def datasets(self): return {lvl: _j(self.path / f) for lvl, f in FILES.items() if (self.path / f).exists()}
    def registry(self): return _j(self.path / REGISTRY)
    def _records(self, folder):
        d = self.coord / folder
        if not d.exists(): return []
        first_at = lambda r: r.get('at') or (r.get('history') or [{}])[0].get('at', '')
        return sorted((_j(f) for f in d.glob('*.json')), key=lambda r: (first_at(r), _seq(r['id'])))
    def events(self): return self._records('events')
    def work(self): return self._records('work-items')
    def change_sets(self): return sorted((self.coord / 'change-sets').glob('CS-*.json')) if (self.coord / 'change-sets').exists() else []
    def _save_event(self, e): _w(self.coord / 'events' / f"{e['id']}.json", e)
    def _save_work(self, items):
        for w in items: _w(self.coord / 'work-items' / f"{w['id']}.json", w)

    def _next(self, prefix):
        """The next id for a record kind, scoped to the Git branch (D1): CS-<branch>-001, or CS-001 on main / outside Git."""
        folder = {'CS': 'change-sets', 'CE': 'events', 'WI': 'work-items'}[prefix]
        scope = _scope(_branch(self.path)); head = f'{prefix}-{scope}-' if scope else f'{prefix}-'
        used = [f.stem[len(head):] for f in (self.coord / folder).glob(f'{head}*.json')] if (self.coord / folder).exists() else []
        n = max((int(u) for u in used if u.isdigit()), default=0) + 1
        return f'{head}{n:03d}'

    def check(self, datasets=None, registry=None):
        """The workspace's errors under the metamodel (the same checks as `sdem check`)."""
        mm = Metamodel.load(); from .graph import LevelGraph
        ds = datasets or self.datasets(); reg = registry or self.registry()
        fg = FederatedGraph([LevelGraph(d, mm) for d in ds.values()], [reg], mm)
        return sorted(f'{k}: {i}' for k, v in fg.check().items() for i in v), fg

    # -- change sets (AG-K01)
    def propose(self, change_set, agent, person, work_ids=(), catalogue=None):
        issues = check_schema(change_set, json.loads(SCHEMA.read_text(encoding='utf-8'))['$defs']['change_set_input'], json.loads(SCHEMA.read_text(encoding='utf-8')))
        if issues: raise CoordinationError('change set format: ' + '; '.join(issues[:5]))
        if not (agent or '').strip() or not is_person(person):
            raise CoordinationError('CTL-20: a change set needs both the agent and the person behind it — the person is a person, never an agent or tool (CTL-21)')
        layer = change_set['layer']
        if agent == ORCHESTRATOR: raise CoordinationError('CTL-19: the orchestrator never changes layer data')
        if agent != HUMAN and AGENT_LAYER.get(agent) != layer:
            raise CoordinationError(f"CTL-19: agent {agent} may change only {AGENT_LAYER.get(agent, 'no layer')}, not {layer}")
        ds = self.datasets(); work = self.work(); wis = []
        for work_id in work_ids or ():
            wi = next((w for w in work if w['id'] == work_id), None)
            if not wi: raise CoordinationError(f'{work_id}: no such work item')
            st = wi['history'][-1]
            if wi['layer'] != layer: raise CoordinationError(f"CTL-19: {work_id} is for {wi['layer']}, not {layer}")
            if st['status'] != 'in_progress' or st['agent'] != agent: raise CoordinationError(f'CTL-20: {work_id} is not claimed by {agent} — run sdem work claim first')
            wis.append(wi)
        if layer not in ds: raise CoordinationError(f'the workspace has no {layer} dataset ({FILES[layer]}) — a change set changes an existing layer')
        if not wis and agent != HUMAN:   # RR-G04: a downstream change comes only from an authorised work item
            from .validation import phase as _ph
            touched = {c['record']['id'] for c in change_set['changes']}
            for e in self.events():
                vv = self.validation(e['id'])
                if vv and _ph(vv) == 'implementation_authorised': continue
                if any(w['event'] == e['id'] for w in work): continue          # planned before validation existed
                hit = sorted(touched & {r['id'] for r in e['impact']['records'] if r['id'] not in e['impact']['changed']})
                if hit: raise CoordinationError(f"AG-V08: {', '.join(hit)} {'is' if len(hit) == 1 else 'are'} affected by {e['id']}, whose impact is not yet accepted and authorised — "
                                                f"a downstream change waits for its work item (sdem events show {e['id']})")
        before, _ = self.check(ds)
        new = copy.deepcopy(ds); target = new[layer]; by_id = {i['id']: i for i in target['instances']}
        ids_anywhere = {i['id'] for d in ds.values() for i in d['instances']}
        cat = {i['id']: i for i in _j(catalogue)['instances']} if catalogue else None
        changed = []
        for n, c in enumerate(change_set['changes'], 1):
            op, rec = c['op'], c['record']; rid = rec['id']
            if op == 'remove': raise CoordinationError(f'change {n}: remove is not a change-set operation — retire the record instead')
            if str(rid).startswith(PROJECTED_PREFIXES): raise CoordinationError(f'CTL-16: change {n}: {rid} is a projected or design record, never real data')
            if 'type' in rec and Metamodel.load().level(rec['type']) not in (layer, None) or 'type' in rec and Metamodel.load().level(rec['type']) is None and not str(rec['type']).startswith(layer + '.'):   # a profile type's layer is the metamodel's, not its name's first part
                raise CoordinationError(f"CTL-19: change {n}: {rid} has type {rec.get('type')} — not a {layer} record")
            if op == 'add':
                if rid in ids_anywhere: raise CoordinationError(f'change {n}: {rid} already exists — use update')
                if layer == 'A2':
                    if cat is None: raise CoordinationError('CTL-19: an A2 change set that adds records needs --catalogue (BIAN elements come only from the catalogue)')
                    src = cat.get(rid)
                    if not src or (rec.get('canonical_id') and src.get('canonical_id') != rec['canonical_id']):
                        raise CoordinationError(f'CTL-19: change {n}: {rid} is not in the BIAN catalogue')
                target['instances'].append(rec); changed.append((rid, None))
            else:
                if rid not in by_id: raise CoordinationError(f'change {n}: {rid} is not a {layer} record in this workspace')
                old = by_id[rid]
                kind = c.get('kind') or KIND_OF[op]
                if op == 'update':
                    if rec.get('type', old['type']) != old['type']: raise CoordinationError(f'change {n}: {rid} cannot change type — retire it and add a new record')
                    replacement = {**rec, 'type': old['type']}
                    differs = {k for k in set(old) | set(replacement) if old.get(k) != replacement.get(k)}
                    if not c.get('kind') and differs and differs <= TEXT_FIELDS: kind = 'document'   # AG-V11
                    old.clear(); old.update(replacement)
                else:
                    old['lifecycle_status'] = 'retired'
                changed.append((rid, kind))
        rels = change_set.get('relationships', {})
        lay_ids = {i['id'] for i in target['instances']}
        for r in rels.get('add', []):
            if r['source'] not in lay_ids or r['target'] not in lay_ids: raise CoordinationError(f"CTL-19: relationship {r['source']} → {r['target']} leaves layer {layer}")
            if r not in target['relationships']: target['relationships'].append(r)
        for r in rels.get('remove', []):
            if r in target['relationships']: target['relationships'].remove(r)
        after, fg = self.check(new)
        added_errors = [e for e in after if e not in before]
        if added_errors: raise CoordinationError('the change set breaks the metamodel — nothing was changed:\n  ' + '\n  '.join(added_errors[:10]))
        # land it
        cs_id = self._next('CS'); ce_id = self._next('CE')
        round_ = max(w['round'] for w in wis) + 1 if wis else 1
        before = _file_sha(self.path / FILES[layer])
        _w(self.coord / 'snapshots' / f'{cs_id}.before.json', ds[layer])   # the layer as it was — what `sdem change revert` restores (T5)
        _w(self.path / FILES[layer], new[layer])
        cs = {'id': cs_id, **change_set, 'agent': agent, 'person': person, 'created_at': self.now(), 'work_items': [w['id'] for w in wis], 'event': ce_id, 'branch': _branch(self.path),
              'trigger': 'downstream' if wis else 'initial',   # RR-G04: an authorised downstream change answers work items; an initial change starts a new event
              'dataset': {'file': FILES[layer], 'before_sha256': before, 'after_sha256': _content_sha(new[layer])}}   # what was written (also in a dry run)
        _w(self.coord / 'change-sets' / f'{cs_id}.json', cs)
        _w(self.coord / 'snapshots' / f'{cs_id}.json', new[layer])   # the layer as this change set left it (AG-S08, and undo later)
        if rels.get('add') or rels.get('remove'): changed = [(r, 'modify' if k == 'document' else k) for r, k in changed]   # links changed: not text only
        impact = self._impact(fg, changed, layer)
        event = {'id': ce_id, 'change_set': cs_id, 'layer': layer, 'round': round_, 'at': self.now(), 'agent': agent, 'person': person, 'impact': impact}
        self._save_event(event)
        for wi in wis:
            wi['history'].append({'status': 'done', 'at': self.now(), 'agent': agent, 'person': person, 'note': f'answered by {cs_id}'})
        if wis: self._save_work(wis)
        return cs, event

    def _record(self, layer, prev, cur, agent, person, reason, extra, write=None):
        """Record a change of `layer` from `prev` to `cur` as a change set (the diff, with its impact) and a change event.
        Shared by adopt (a person's hand edit, already in the file) and revert (`write` = the content to restore)."""
        cur_all = self.datasets()
        if write is not None: cur_all = {**cur_all, layer: write}
        old_all = {**cur_all, layer: prev}
        before_errors, old_fg = self.check(old_all); after_errors, fg = self.check(cur_all)
        added = [e for e in after_errors if e not in before_errors]
        if added: raise CoordinationError('the result would break the metamodel — nothing was changed:\n  ' + '\n  '.join(added[:10]))
        po = {i['id']: i for i in prev['instances']}; co = {i['id']: i for i in cur['instances']}
        changes, changed = [], []
        for rid, r in co.items():
            if rid not in po: changes.append({'op': 'add', 'record': r}); changed.append((rid, None))
            elif r != po[rid]: changes.append({'op': 'update', 'record': r}); changed.append((rid, 'modify'))
        removed = [rid for rid in po if rid not in co]
        for rid in removed: changes.append({'op': 'remove', 'record': po[rid]})
        rel_add = [r for r in cur.get('relationships', []) if r not in prev.get('relationships', [])]
        rel_rem = [r for r in prev.get('relationships', []) if r not in cur.get('relationships', [])]
        before_sha = _file_sha(self.path / FILES[layer]) if write is not None else extra.pop('_before_sha')
        cs_id = self._next('CS'); ce_id = self._next('CE')
        if write is not None:
            _w(self.coord / 'snapshots' / f'{cs_id}.before.json', prev); _w(self.path / FILES[layer], write)
        impact = self._impact(fg, changed, layer)
        if removed:   # the impact of a removal is read from the graph as it was
            gone = self._impact(old_fg, [(rid, 'retire') for rid in removed], layer)
            impact['records'] = sorted({r['id']: r for r in gone['records'] + impact['records']}.values(), key=lambda x: (x['level'] or '', x['id']))
            impact['mappings_to_supersede'] = sorted(set(impact['mappings_to_supersede']) | set(gone['mappings_to_supersede'])); impact['changed'] += removed
        cs = {'id': cs_id, 'layer': layer, 'reason': reason, 'changes': changes, 'relationships': {'add': rel_add, 'remove': rel_rem}, **extra,
              'agent': agent, 'person': person, 'created_at': self.now(), 'work_items': [], 'event': ce_id, 'branch': _branch(self.path),
              'dataset': {'file': FILES[layer], 'before_sha256': before_sha, 'after_sha256': _file_sha(self.path / FILES[layer])}}
        _w(self.coord / 'change-sets' / f'{cs_id}.json', cs); _w(self.coord / 'snapshots' / f'{cs_id}.json', cur)
        event = {'id': ce_id, 'change_set': cs_id, 'layer': layer, 'round': 1, 'at': self.now(), 'agent': agent, 'person': person, 'impact': impact}
        self._save_event(event)
        return cs, event

    def adopt(self, layer, person, reason):
        """AG-S08: record a person's direct edit of a layer's dataset as a change set, so the chain of change sets is whole
        again. The edit must keep the metamodel (no new errors); its impact is recorded like any change set's."""
        OTHER = {'registry': REGISTRY, 'requirements': 'requirements.json'}
        if layer not in FILES and layer not in OTHER: raise CoordinationError(f'unknown layer {layer}')
        if not is_person(person) or person in AGENT_LAYER or person in (ORCHESTRATOR, HUMAN): raise CoordinationError('CTL-20: adopt needs the name of the person who made the edit')
        if not (reason or '').strip(): raise CoordinationError('adopt needs a reason')
        from .governance import record as _gd
        if layer in OTHER:   # GV-06: an explicit, recorded reconciliation of the ledger for a file that has no change sets
            from .files import record, unrecorded
            if not any(u['file'] == OTHER[layer] for u in (unrecorded(self.path) or [])): raise CoordinationError(f'{OTHER[layer]} has not changed since SDEM last wrote it — nothing to adopt')
            errors, _ = self.check()
            if errors: raise CoordinationError('the workspace does not pass its checks — fix it first (sdem check --workspace …)')
            if layer == 'requirements':
                from .requirements import load, check as rcheck
                bad = rcheck(load(self.path), self.datasets())
                if bad: raise CoordinationError('requirements.json does not pass its checks: ' + '; '.join(bad[:3]))
            gd = _gd(self.path, 'adopt_edit', person, OTHER[layer], {'reason': reason})
            record([self.path / OTHER[layer]], by=f'{person} (sdem change adopt, {gd["id"]})', note=reason)
            return None, None
        from .files import record, unrecorded
        last = self._last_change_set(layer)
        if not last:   # AF-07: no change sets yet — the edit is accepted in the workspace's ledger, with who and why
            if not any(u['file'] == FILES[layer] for u in (unrecorded(self.path) or [])):
                raise CoordinationError(f'{FILES[layer]} has not changed since SDEM last wrote it — nothing to adopt')
            from .graph import FederatedGraph as _FG
            errors = _FG.load([str(self.path / f) for f in (*FILES.values(), REGISTRY) if (self.path / f).exists()]).check()
            if any(errors.values()): raise CoordinationError('the edit does not pass the workspace checks — fix it first (sdem check --workspace …)')
            gd = _gd(self.path, 'adopt_edit', person, FILES[layer], {'reason': reason})
            record([self.path / FILES[layer]], by=f'{person} (sdem change adopt, {gd["id"]})', note=reason)
            return None, None
        if _file_sha(self.path / FILES[layer]) == last['dataset']['after_sha256']: raise CoordinationError(f"{FILES[layer]} has not changed since {last['id']} — nothing to adopt")
        prev = _j(self.coord / 'snapshots' / f"{last['id']}.json")
        out = self._record(layer, prev, self.datasets()[layer], HUMAN, person, reason, {'adopted': True, '_before_sha': last['dataset']['after_sha256']})
        record([self.path / FILES[layer]], by=f'{person} (sdem change adopt)', note=reason)
        return out

    def revert(self, cs_id, agent, person, reason=''):
        """T5 / AG-K06: undo a change set — restore its layer as it was before — recorded as a new change set and change event.
        Only the latest change set of a layer, only when the layer is exactly as it left it; CTL-19/20 apply; open work
        from the reverted change event is cancelled, with a note."""
        f = self.coord / 'change-sets' / f'{cs_id}.json'
        if not f.exists(): raise CoordinationError(f'{cs_id}: no such change set')
        target = _j(f); layer = target['layer']
        if not (agent or '').strip() or not is_person(person): raise CoordinationError('CTL-20: a revert needs both the agent and the person behind it')
        if agent == ORCHESTRATOR: raise CoordinationError('CTL-19: the orchestrator never changes layer data')
        if agent != HUMAN and AGENT_LAYER.get(agent) != layer: raise CoordinationError(f"CTL-19: agent {agent} may change only {AGENT_LAYER.get(agent, 'no layer')}, not {layer}")
        last = self._last_change_set(layer)
        if not last or last['id'] != cs_id: raise CoordinationError(f"{cs_id} is not the latest change set of {layer} ({last['id'] if last else 'none'} is) — revert the later ones first")
        if target.get('dataset', {}).get('after_sha256') != _file_sha(self.path / FILES[layer]):
            raise CoordinationError(f"CTL-20 (AG-S08): {FILES[layer]} was changed after {cs_id} outside a change set — adopt or undo that edit first")
        before = self.coord / 'snapshots' / f'{cs_id}.before.json'
        if not before.exists(): raise CoordinationError(f'{cs_id} was made before undo was available (no before-snapshot) — undo it with Git')
        cs, ev = self._record(layer, self.datasets()[layer], _j(before), agent, person, reason or f'revert {cs_id}', {'reverts': cs_id}, write=_j(before))
        cancelled = []
        for w in self.work():
            if w['event'] == target['event'] and w['history'][-1]['status'] in ('open', 'in_progress', 'blocked'):
                w['history'].append({'status': 'cancelled', 'at': self.now(), 'agent': agent, 'person': person, 'note': f'{cs_id} reverted by {cs["id"]}'}); self._save_work([w]); cancelled.append(w['id'])
        return cs, ev, cancelled

    def _last_change_set(self, layer):
        sets = [_j(f) for f in self.change_sets()]
        sets = [c for c in sets if c.get('layer') == layer and c.get('dataset')]
        return sorted(sets, key=lambda c: (c.get('created_at', ''), _seq(c['id'])))[-1] if sets else None

    def _impact(self, fg, changed, layer):
        """Stored impact result (AG-R03): every affected record with its strongest classification and paths."""
        rows, supersede = {}, set()
        for rid, kind in changed:
            if kind == 'document': continue   # AG-V11: name or description only — nothing depends on the words
            if not kind:
                rows.setdefault(rid, {'id': rid, 'level': layer, 'classification': 'design_change_required', 'via': [], 'cause': f'{rid} added', 'rule': 'add → design_change_required'}); continue
            r = fg.impact(rid, kind)
            supersede |= set(r['mappings_to_supersede'])
            for x in r['instances']:
                cur = rows.get(x['id'])
                row = {'id': x['id'], 'name': x['name'], 'level': x['level'], 'classification': x['classification'], 'via': x['via'], 'cause': f'{kind} of {rid}', 'rule': x.get('rule')}
                if not cur or STRENGTH[x['classification']] > STRENGTH[cur['classification']]: rows[x['id']] = row
        from .graph import impact_coverage
        from .validation import basis
        recs = sorted(rows.values(), key=lambda x: (x['level'] or '', x['id']))
        doc_only = bool(changed) and all(k == 'document' for _, k in changed)
        return {'records': recs, 'mappings_to_supersede': sorted(supersede), 'changed': [rid for rid, _ in changed],
                **({'documentation_only': True} if doc_only else {}),
                'coverage': impact_coverage(fg, recs, [rid for rid, _ in changed]), 'basis': basis(self.path, fg)}   # AG-V01, AG-V02

    # -- four-layer impact validation (AG-V01…V10; sdem/validation.py)
    def validations(self): return self._records('validations')

    def validation(self, event_id):
        from .validation import vid
        f = self.coord / 'validations' / f'{vid(event_id)}.json'
        return _j(f) if f.exists() else None

    def _save_validation(self, v): _w(self.coord / 'validations' / f"{v['id']}.json", v)

    def request_validation(self, event_id, agent, person):
        """AG-V03: open the validation of a change event — all four layers, including those with no detected impact. Idempotent."""
        from . import validation as V
        if agent not in (ORCHESTRATOR, HUMAN): raise CoordinationError(f'only the orchestrator (or an architect) requests impact validation, not {agent}')
        if not is_person(person): raise CoordinationError('CTL-20: requesting validation needs the person behind it (a person, never an agent or tool)')
        ev = next((e for e in self.events() if e['id'] == event_id), None)
        if not ev: raise CoordinationError(f'{event_id}: no such change event')
        old = self.validation(event_id)
        if old: return old, False
        cov, note = ev['impact'].get('coverage'), 'stored with the change event'
        if cov is None:   # AG-V09: an event from before validation existed — recomputed now, and said so; nothing accepted for it
            from .graph import impact_coverage
            _, fg = self.check()
            cov = impact_coverage(fg, ev['impact']['records'], ev['impact']['changed'])
            note = f'recomputed from the workspace as it is now ({self.now()}) — {event_id} was recorded before impact validation existed'
        legacy = 'coverage' not in ev['impact']
        planned = any(w['event'] == event_id for w in self.work())
        v = {'id': V.vid(event_id), 'event': event_id, 'change_set': ev['change_set'], 'changed_layer': ev['layer'], 'round': ev['round'],
             'calculated': {'impact': f'events/{event_id}.json#impact', 'coverage_source': note, 'basis': ev['impact'].get('basis')},
             'layers': {l: {'calculated': cov[l], 'assessments': []} for l in V.LEVELS},
             'history': [{'phase': 'validation_pending', 'at': self.now(), 'agent': agent, 'person': person}]}
        if legacy: v['legacy'] = True
        if planned: v['note'] = f'{event_id} had work planned before impact validation existed; that work stands as it was — this validation does not authorise it retroactively'
        v['analysis'] = self._analysis(event_id)   # RR-G01: requirements evaluation and risk findings, reviewed in this same validation
        self._save_validation(v)
        return v, True

    def _analysis(self, event_id):
        from . import requirements as R
        return R.evaluate_event(self.path, event_id)

    def analyse(self, event_id, agent, person):
        """RR-G02: recompute the requirements evaluation and risk findings (after new evidence, links or requirements). Earlier
        analyses are kept; assessments made against other evidence become stale."""
        from . import validation as V
        if agent not in (ORCHESTRATOR, HUMAN) and agent not in AGENT_LAYER: raise CoordinationError(f'unknown agent {agent}')
        if not is_person(person): raise CoordinationError('CTL-20: an analysis is recorded against the person behind it')
        v = self.validation(event_id)
        if not v: raise CoordinationError(f'{event_id}: impact validation not requested — sdem events validate {event_id} first')
        if V.phase(v) in ('architect_accepted', 'implementation_authorised'): raise CoordinationError(f'{event_id}: already accepted — a change since then is a new change event')
        if v.get('analysis'): v.setdefault('analysis_history', []).append({k: v['analysis'][k] for k in ('computed_at', 'inputs_sha256')})
        v['analysis'] = self._analysis(event_id); v['analysis']['by'] = {'agent': agent, 'person': person}
        self._save_validation(v)
        return v

    def assess(self, event_id, layer, status, agent, person, reasoning, recommended=None, evidence=(), mappings=(), records=(), missing=(), uncertainty='', confidence='medium'):
        """AG-V04/V05: one layer's specialist assessment of the calculated impact."""
        from . import validation as V
        v = self.validation(event_id)
        if not v: raise CoordinationError(f'{event_id}: impact validation not requested — the orchestrator runs: sdem events validate {event_id} --workspace {self.path} --agent {ORCHESTRATOR} --person <name>')
        if V.phase(v) in ('architect_accepted', 'implementation_authorised'): raise CoordinationError(f"{event_id}: the impact assessment was already accepted by {v['acceptance']['by']} — it is closed")
        if layer not in V.LEVELS: raise CoordinationError(f'unknown layer {layer}')
        if agent == ORCHESTRATOR: raise CoordinationError('CTL-19: the orchestrator coordinates validation; each layer is assessed by its own agent')
        if agent != HUMAN and AGENT_LAYER.get(agent) != layer: raise CoordinationError(f"CTL-19: agent {agent} may assess only {AGENT_LAYER.get(agent, 'no layer')}, not {layer}")
        if not is_person(person): raise CoordinationError('CTL-20: an assessment needs the person behind the agent (a person, never an agent or tool)')
        if status not in V.STATUSES: raise CoordinationError(f'status must be one of {", ".join(V.STATUSES)}')
        if confidence not in V.CONFIDENCE: raise CoordinationError(f'confidence must be one of {", ".join(V.CONFIDENCE)}')
        if not (reasoning or '').strip(): raise CoordinationError('an assessment needs its reasoning (--reasoning)')
        calc = v['layers'][layer]['calculated']
        rec = recommended or {'impact_confirmed': calc['classification'], 'no_impact_confirmed': 'no_impact', 'further_investigation_required': calc['classification']}.get(status)   # further investigation: the calculation stands until decided
        if rec not in V.CLASSIFICATIONS: raise CoordinationError(f'{status} needs --recommend ({", ".join(V.CLASSIFICATIONS)})')
        if status == 'impact_confirmed' and (calc['classification'] == 'no_impact' or rec != calc['classification']):
            raise CoordinationError(f"impact_confirmed agrees with the calculation ({calc['classification']}) — to disagree, use impact_disputed with --recommend and evidence")
        if status == 'no_impact_confirmed':
            if rec != 'no_impact': raise CoordinationError('no_impact_confirmed recommends no_impact')
            if calc['classification'] != 'no_impact': raise CoordinationError(f"the calculation found {calc['classification']} in {layer} — to say there is none, use impact_disputed with evidence")
            if not evidence: raise CoordinationError('no_impact_confirmed needs evidence (--evidence kind:ref …): a missing path is not proof of no impact (AG-V05)')
            if calc['evidence'] == 'incomplete' and not (uncertainty or '').strip():
                raise CoordinationError(f"{layer}'s links are incomplete ({calc['unmapped_count']} record(s) with no approved link, {len(calc['unapproved_links'])} link(s) not approved) — "
                                        'say why they do not change your conclusion (--uncertainty), or use further_investigation_required')
        if status == 'impact_disputed':
            if rec == calc['classification']: raise CoordinationError(f"impact_disputed recommends something other than the calculation ({calc['classification']})")
            if not evidence: raise CoordinationError('impact_disputed needs evidence (--evidence kind:ref …)')
            if rec == 'design_change_required' and not records: raise CoordinationError('a disputed design change names the records it affects (--record ID …)')
        if status == 'further_investigation_required' and not (missing or (uncertainty or '').strip()):
            raise CoordinationError('further_investigation_required says what is missing (--missing …) or uncertain (--uncertainty …)')
        known = {i['id'] for d in self.datasets().values() for i in d['instances']}
        bad = [r for r in records if r not in known]
        if bad: raise CoordinationError(f"not records of this workspace: {', '.join(bad)}")
        from .requirements import inputs_sha
        calc_ids = {r['id'] for r in calc.get('records', [])}
        extra = [r for r in records if r not in calc_ids]
        a = {'event': event_id, 'layer': layer, 'calculated': calc['classification'], 'status': status, 'recommended': rec, 'evidence': list(evidence),
             'additional_records': extra, 'inputs_sha256': inputs_sha(self.path),   # RR-G03: records the calculation did not name; RR-G02: what it was assessed against
             'analysis_contract': (v.get('analysis') or {}).get('contract'),        # RR-E06: which reading of the analysis it was made against
             'mappings': list(mappings), 'records': list(records), 'missing_relationships': list(missing), 'uncertainty': uncertainty or '',
             'confidence': confidence, 'reasoning': reasoning, 'agent': agent, 'person': person, 'at': self.now()}
        v['layers'][layer]['assessments'].append(a)
        v['history'].append({'phase': V.derive(v), 'at': self.now(), 'agent': agent, 'person': person, 'note': f'{layer}: {status}'})
        self._save_validation(v)
        return v, a

    def accept_validation(self, event_id, person, reason, final=None, resolutions=None, authorise=False, accept_risks=None):
        """AG-V06: a person accepts the final impact assessment — and, when they say so, authorises implementation."""
        from . import validation as V
        final, resolutions = dict(final or {}), dict(resolutions or {})
        if not is_person(person) or person in AGENT_LAYER or person in (ORCHESTRATOR, HUMAN):
            raise CoordinationError(f'CTL-21: accepting an impact assessment is a person\'s decision — give your own name, not {person!r}')
        if not (reason or '').strip(): raise CoordinationError('acceptance needs a reason (--reason)')
        v = self.validation(event_id)
        if not v: raise CoordinationError(f'{event_id}: impact validation not requested')
        if V.phase(v) in ('architect_accepted', 'implementation_authorised'): raise CoordinationError(f"{event_id}: already accepted by {v['acceptance']['by']}")
        missing = [l for l in V.LEVELS if not V.latest(v, l)]
        if missing: raise CoordinationError(f"{event_id}: no assessment yet for {', '.join(missing)} — every layer is assessed before acceptance (AG-V03)")
        from .requirements import inputs_sha
        now_sha = inputs_sha(self.path)
        if not v.get('analysis'): raise CoordinationError(f'RR-G01: {event_id} has no requirements and risk analysis — run: sdem events analyse {event_id} --workspace {self.path} --agent {ORCHESTRATOR} --person <name>')
        from .requirements import CONTRACT
        if v['analysis'].get('contract') != CONTRACT:   # RR-E06: an analysis made before v0.11.2 read `overall` differently — never reinterpreted
            raise CoordinationError(f'RR-E06: the analysis of {event_id} was made by an earlier SDEM (before current and proposed compliance were kept apart) — '
                                    f'run sdem events analyse {event_id} --workspace {self.path} --agent {ORCHESTRATOR} --person <name>, then have the layers re-assess')
        if v['analysis']['inputs_sha256'] != now_sha:
            raise CoordinationError(f'RR-G02: the workspace changed since the analysis ({v["analysis"]["computed_at"]}) — run sdem events analyse {event_id}, then have the layers re-assess')
        stale = [l for l in V.LEVELS if V.latest(v, l).get('inputs_sha256') != now_sha   # none recorded (made before v0.11.0) is stale too
                 or V.latest(v, l).get('analysis_contract') != CONTRACT]                 # made against an earlier analysis contract (before v0.11.2)
        if stale: raise CoordinationError(f"RR-G02: the assessments of {', '.join(stale)} were made against other evidence, or before the requirements and risk analysis existed — "
                                          "those layers re-assess (sdem events assess …)")
        accept_risks = dict(accept_risks or {})
        breaches = [f for f in v['analysis']['risks'] if f['type'] == 'confirmed_breach']
        open_b = [f['id'] for f in breaches if not accept_risks.get(f['id'])]
        if open_b: raise CoordinationError(f"RR-K04: confirmed requirement breaches need your decision — change the design and re-analyse, or accept each as a residual risk: "
                                           + ' '.join(f'--accept-risk {x}="<why>"' for x in open_b))
        unknown = [x for x in accept_risks if x not in {f['id'] for f in v['analysis']['risks']}]
        if unknown: raise CoordinationError(f"no such risk finding in {event_id}: {', '.join(unknown)}")
        out = {}
        for l in V.LEVELS:
            a = V.latest(v, l); f = final.get(l)
            if f and f not in V.CLASSIFICATIONS: raise CoordinationError(f'{l}: {f} is not a classification')
            open_ = a['status'] in ('impact_disputed', 'further_investigation_required')
            if open_ and not (f and resolutions.get(l)): raise CoordinationError(f"{l} is {a['status']} — decide it: --final {l}=<classification> --resolve {l}=\"<why>\"")
            if f and f != a['recommended'] and not resolutions.get(l): raise CoordinationError(f"{l}: your final {f} differs from the specialist's {a['recommended']} — say why (--resolve {l}=\"…\")")
            out[l] = f or a['recommended']
        types = {}
        for f in v['analysis']['risks']: types.setdefault(f['type'], []).append(f['id'])
        v['acceptance'] = {'by': person, 'at': self.now(), 'reason': reason, 'final': out, 'resolutions': resolutions,
                           'assessments': {l: len(v['layers'][l]['assessments']) for l in V.LEVELS}, 'inputs_sha256': now_sha,
                           'accepted_residual_risks': [{'finding': k, 'reason': x, 'by': person, 'at': self.now()} for k, x in accept_risks.items()],
                           'findings_acknowledged': types, 'identity': _identity(person)}
        v['history'].append({'phase': 'architect_accepted', 'at': self.now(), 'agent': HUMAN, 'person': person})
        from .governance import record   # GV-01: each decision, attributed (verified only by the person's signed commit)
        gds = [record(self.path, 'accept_impact', person, event_id)['id']]
        gds += [record(self.path, 'accept_residual_risk', person, k, {'event': event_id, 'reason': x})['id'] for k, x in accept_risks.items()]
        if authorise:
            v['history'].append({'phase': 'implementation_authorised', 'at': self.now(), 'agent': HUMAN, 'person': person})
            gds.append(record(self.path, 'authorise_implementation', person, event_id)['id'])
        v['acceptance']['decisions'] = gds; v['acceptance']['attestation'] = 'attributed'
        self._save_validation(v)
        return v

    def authorise(self, event_id, person):
        from . import validation as V
        if not is_person(person) or person in AGENT_LAYER or person in (ORCHESTRATOR, HUMAN):
            raise CoordinationError(f'CTL-21: authorising implementation is a person\'s decision — give your own name, not {person!r}')
        v = self.validation(event_id)
        if not v or V.phase(v) != 'architect_accepted': raise CoordinationError(f'{event_id}: the impact assessment is not accepted — accept it first (sdem events accept)')
        from .governance import record
        gd = record(self.path, 'authorise_implementation', person, event_id)
        v['history'].append({'phase': 'implementation_authorised', 'at': self.now(), 'agent': HUMAN, 'person': person, 'note': gd['id']}); self._save_validation(v)
        return v

    # -- work items (AG-K04)
    def plan(self, event_id, agent, person, max_rounds=MAX_ROUNDS):
        """The orchestrator turns an event's impact into work items: one per record outside the changed layer that needs a
        design change. Review notices are reported, not turned into work (impact rules: 'nothing further')."""
        if agent != ORCHESTRATOR and agent != HUMAN: raise CoordinationError(f'only the orchestrator (or an architect) plans work, not {agent}')
        if not is_person(person): raise CoordinationError('CTL-20: planning needs the person behind it (a person, never an agent or tool)')
        if max_rounds > MAX_ROUNDS and agent != HUMAN:  # AG-S07: a cap, not a default — an agent may lower it, never raise it
            raise CoordinationError(f'AG-S07: the round limit is {MAX_ROUNDS}; an agent may lower it, never raise it — the architect decides (--agent architect)')
        ev = next((e for e in self.events() if e['id'] == event_id), None)
        if not ev: raise CoordinationError(f'{event_id}: no such change event')
        work = self.work()
        if any(w['event'] == event_id for w in work): raise CoordinationError(f'{event_id}: already planned')
        from . import validation as V
        v = self.validation(event_id)   # AG-V08: no implementation before a person accepts the four-layer assessment and authorises it
        if not v: raise CoordinationError(f'AG-V08: {event_id} has no impact validation — implementation waits until every layer has assessed the impact and a person has accepted it. '
                                          f'Next: sdem events validate {event_id} --workspace {self.path} --agent {ORCHESTRATOR} --person <name>')
        if V.phase(v) != 'implementation_authorised':
            raise CoordinationError(f"AG-V08: {event_id} is at {V.phase(v)} — implementation needs a person's acceptance and authorisation "
                                    + (f"({'; '.join(V.summary(v)['open'])})" if V.summary(v)['open'] else f'(sdem events accept {event_id} … --authorise)'))
        from .governance import require_verified   # GV-04: fail closed where the workspace requires verified decisions
        for kind in ('accept_impact', 'authorise_implementation'):
            why = require_verified(self.path, kind, event_id)
            if why: raise CoordinationError(f'GV-04: {why}')
        from .requirements import inputs_sha
        if v['acceptance'].get('inputs_sha256') and v['acceptance']['inputs_sha256'] != inputs_sha(self.path):
            raise CoordinationError(f"RR-G02: the workspace changed after {v['acceptance']['by']} accepted {event_id} — the acceptance no longer covers it; validate the change again")
        final = v['acceptance']['final']
        todo = [r for r in ev['impact']['records'] if r['classification'] == 'design_change_required' and r['level'] != ev['layer'] and r['id'] not in ev['impact']['changed']
                and final.get(r['level']) == 'design_change_required']
        for l in V.LEVELS:   # a design change the architect accepted that the engine did not calculate: the records the specialist named
            a = V.latest(v, l)
            if final.get(l) == 'design_change_required':   # RR-G03: the changed layer's own additional records too (e.g. an artifact on the moved platform)
                for rid in (a or {}).get('records', []):
                    if rid in ev['impact']['changed']: continue
                    if not any(r['id'] == rid for r in todo):
                        todo.append({'id': rid, 'name': rid, 'level': l, 'classification': 'design_change_required', 'via': a.get('mappings', []),
                                     'cause': f"accepted impact assessment ({v['acceptance']['by']}): {a['reasoning'][:120]}"})
        review = [r for r in ev['impact']['records'] if r['classification'] == 'review_required' or (final.get(r['level']) == 'review_required' and r['level'] != ev['layer'])]
        if todo and ev['round'] >= max_rounds:
            return {'event': event_id, 'stopped': f"round limit {max_rounds} reached — {len(todo)} more design change(s) need the architect's decision", 'work_items': [], 'review': review}
        made = []
        for r in todo:
            wid = self._next('WI')
            supersede = [m for m in ev['impact']['mappings_to_supersede'] if m in r['via']]
            action = f"{r['cause']}: change {r['id']} ({r['name']}) in {r['level']} accordingly" + (f"; the links {', '.join(supersede)} will be superseded" if supersede else '')
            w = {'id': wid, 'event': event_id, 'layer': r['level'], 'records': [r['id']], 'action': action, 'reason': {'event': event_id, 'path': r['via']},
                 'round': ev['round'], 'history': [{'status': 'open', 'at': self.now(), 'agent': agent, 'person': person}]}
            work.append(w); made.append(w); self._save_work([w])
        return {'event': event_id, 'work_items': made, 'review': review}

    def transition(self, work_id, status, agent, person, note=''):
        if not (agent or '').strip() or not is_person(person): raise CoordinationError('CTL-20: every work-item step needs the agent and the person')
        work = self.work(); w = next((x for x in work if x['id'] == work_id), None)
        if not w: raise CoordinationError(f'{work_id}: no such work item')
        cur = w['history'][-1]['status']
        allowed = {'open': {'in_progress', 'cancelled'}, 'in_progress': {'done', 'blocked', 'cancelled', 'open'}, 'blocked': {'in_progress', 'cancelled'}}
        if status not in allowed.get(cur, set()): raise CoordinationError(f'{work_id}: cannot go from {cur} to {status}')
        if status == 'in_progress' and agent not in (HUMAN,) and AGENT_LAYER.get(agent) != w['layer']:
            raise CoordinationError(f"CTL-19: {work_id} is for {w['layer']}; {agent} may take only {AGENT_LAYER.get(agent, 'no layer')} work")
        w['history'].append({'status': status, 'at': self.now(), 'agent': agent, 'person': person, **({'note': note} if note else {})}); self._save_work([w])
        return w

    def status(self):
        """Open events: an event is open while any of its work items is not done or cancelled."""
        work = self.work(); out = []
        for e in self.events():
            items = [w for w in work if w['event'] == e['id']]
            open_items = [w['id'] for w in items if w['history'][-1]['status'] not in ('done', 'cancelled')]
            from .validation import phase as _phase
            v = self.validation(e['id'])
            out.append({**e, 'work_items': [w['id'] for w in items], 'open_work_items': open_items,
                        'validation': _phase(v) if v else ('not needed — documentation only (AG-V11)' if e['impact'].get('documentation_only') else
                                                           'not needed — planned before impact validation existed' if items and 'coverage' not in e['impact'] else 'not requested'),
                        'planned': bool(items) or bool(e['impact'].get('documentation_only')) or bool(v and _phase(v) == 'implementation_authorised' and not any(
                            r['classification'] == 'design_change_required' and r['level'] != e['layer'] and r['id'] not in e['impact']['changed']
                            and v['acceptance']['final'].get(r['level']) == 'design_change_required' for r in e['impact']['records']))})
        return out


def _identity(person):
    """RR-G05: who the machine says ran the command — beside the name given. A claim for the audit, not authentication: the
    reviewed pull request (code owners on coordination/) is the control."""
    import getpass, subprocess
    git = {}
    for k in ('user.name', 'user.email'):
        try: git[k] = subprocess.run(['git', 'config', k], capture_output=True, text=True, timeout=5).stdout.strip() or None
        except (OSError, subprocess.SubprocessError): git[k] = None
    try: os_user = getpass.getuser()
    except Exception: os_user = None
    return {'named_person': person, 'os_user': os_user, 'git_user': git.get('user.name'), 'git_email': git.get('user.email'),
            'note': 'the name given is a claim, not authenticated by SDEM; the reviewed pull request is the control'}


def _content_sha(obj):
    """The fingerprint of a dataset as _w writes it — the same as _file_sha of the written file."""
    import hashlib
    from .files import dumps
    return hashlib.sha256(dumps(obj).encode('utf-8')).hexdigest()


def _file_sha(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _seq(rid):
    m = re.search(r'(\d+)$', rid); return int(m.group(1)) if m else 0


def _scope(branch):
    """A short, id-safe form of the branch name; empty on main / master / outside Git."""
    if not branch or branch in ('main', 'master', 'HEAD'): return ''
    return re.sub(r'[^a-z0-9]+', '-', branch.lower()).strip('-')[:24].strip('-')


def _branch(path):
    try: return subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=path, capture_output=True, text=True, timeout=5).stdout.strip() or None
    except (OSError, subprocess.SubprocessError): return None


# ------------------------------------------------------------------ commands (AG-K01…K04): sdem change · events · work

def _common(ap, who=True):
    import argparse  # noqa: F401
    ap.add_argument('--workspace', dest='estate', required=True, metavar='DIR', help='the workspace folder (a1…a4 datasets, mappings.json)')
    if who:
        ap.add_argument('--agent', required=True, help=f"the agent: {', '.join(list(AGENT_LAYER) + [ORCHESTRATOR])}, or '{HUMAN}' for a person working without an agent")
        ap.add_argument('--person', required=True, help='the person behind the agent (CTL-20)')
    ap.add_argument('--json', action='store_true')


def _fail(e):
    """A refused coordination step: one ERROR line, its code taken from the rule that refused it (AF-05)."""
    import re, sys
    from .errors import note
    m = str(e)
    code = ('needs_person' if re.match(r'CTL-2[01]\b', m) else 'refused' if re.match(r'(CTL-19|AG-[A-Z]\d+|CTL-16)\b', m)
            else 'not_found' if 'no such' in m else 'refused')
    hint = (re.search(r'(?:Next|next): (sdem [^;]+)', m) or re.search(r'\((sdem events [^)]+)\)', m))
    note(code, hint.group(1).strip() if hint else None)
    print(f'ERROR: {e}', file=sys.stderr); return 1


def change_main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog='sdem change', description='Change sets: one layer\'s record changes, checked against the metamodel and controls before they land (AG-K01/K02).',
                                 epilog='Examples (agent platform):\n  sdem change propose cs-rehost.json --workspace work/est --agent sdem-a4-technology --person jane.architect\n'
                                        '  sdem change propose cs-a3.json --workspace work/est --agent sdem-a3-application --person jane.architect --work WI-001 WI-002\n'
                                        '  sdem change show CS-001 --workspace work/est\n'
                                        '  sdem change revert CS-002 --workspace work/est --agent sdem-a3-application --person jane.architect --reason "wrong cluster"', formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('propose', help='check and apply a change set to its layer; records the change event and its impact')
    p.add_argument('change_set', help='change set file (JSON): layer, reason, changes[, relationships]')
    _common(p); p.add_argument('--work', nargs='*', default=[], metavar='WI', help='work item(s) this change set answers (claimed by the same agent)')
    p.add_argument('--catalogue', metavar='FILE', help='BIAN catalogue (A2 dataset) — required when an A2 change set adds records')
    s = sub.add_parser('show', help='a change set with its event and impact'); s.add_argument('id'); _common(s, who=False)
    r = sub.add_parser('revert', help='undo the latest change set of a layer — recorded as a new change set (T5)'); r.add_argument('id'); _common(r); r.add_argument('--reason', default='')
    d = sub.add_parser('adopt', help="record a person's direct edit of a layer as a change set (AG-S08)"); _common(d, who=False)
    d.add_argument('--layer', required=True, choices=CODES + ['registry', 'requirements']); d.add_argument('--person', required=True, help='who made the edit'); d.add_argument('--reason', required=True)
    a = ap.parse_args(argv)
    try:
        est = Estate(a.estate)
        if a.cmd == 'propose':
            cs, ev = est.propose(_j(a.change_set), a.agent, a.person, a.work, a.catalogue)
            if a.json: print(json.dumps({'change_set': cs, 'event': ev}, indent=2, ensure_ascii=False)); return 0
            imp = ev['impact']; design = [r for r in imp['records'] if r['classification'] == 'design_change_required' and r['level'] != ev['layer'] and r['id'] not in imp['changed']]
            print(f"{cs['id']} applied to {cs['layer']} ({len(cs['changes'])} change(s)) by {a.agent} for {a.person}" + (f"; answers {', '.join(cs['work_items'])}" if cs['work_items'] else ''))
            if imp.get('documentation_only'):   # AG-V11
                print(f"change event {ev['id']} recorded: documentation only (name or description) — no structural impact, no impact validation needed (AG-V11)")
                print('NOTE: graph stores show the old words until rebuilt: sdem build --workspace … --out <graph>')
                return 0
            print(f"change event {ev['id']} recorded (round {ev['round']}): {len(design)} record(s) in other layers need a design change"
                  + (f"; links to supersede: {', '.join(imp['mappings_to_supersede'])}" if imp['mappings_to_supersede'] else ''))
            for r in design: print(f"  {r['level']}  {r['id']}  {r.get('name') or ''}  — {r['cause']}, via {', '.join(r['via']) or '-'}")
            if cs.get('branch') in ('main', 'master'): print('NOTE: you are on the main branch — agent changes belong on a branch, reviewed in a pull request (AG-W01)')
            print('NOTE: graph stores built from this workspace are now out of date — rebuild them before trace, impact or view: sdem build --workspace … --out <graph>')
            print(f"next: the orchestrator runs  sdem work plan --event {ev['id']} --workspace {a.estate} --agent {ORCHESTRATOR} --person <name>"
                  + f"\n      and the rules engine proposes the new links:  sdem link --workspace {a.estate} --out <dir>")
            return 0
        if a.cmd == 'revert':
            cs, ev, cancelled = est.revert(a.id, a.agent, a.person, a.reason)
            if a.json: print(json.dumps({'change_set': cs, 'event': ev, 'cancelled_work_items': cancelled}, indent=2, ensure_ascii=False)); return 0
            print(f"{cs['id']} reverts {a.id}: {cs['layer']} restored as it was before ({len(cs['changes'])} record change(s)); change event {ev['id']} with its impact"
                  + (f"; cancelled open work items {', '.join(cancelled)}" if cancelled else ''))
            print(f"next: the orchestrator runs  sdem work plan --event {ev['id']} --workspace {a.estate} --agent {ORCHESTRATOR} --person <name>; rebuild graph stores")
            return 0
        if a.cmd == 'adopt':
            cs, ev = est.adopt(a.layer, a.person, a.reason)
            if cs is None:   # AF-07: no change sets yet — accepted in the ledger
                fname = {**FILES, 'registry': REGISTRY, 'requirements': 'requirements.json'}[a.layer]
                if a.json: print(json.dumps({'accepted': fname, 'by': a.person, 'reason': a.reason, 'change_set': None, 'attestation': 'attributed'}, indent=2)); return 0
                print(f"{a.person}'s edit of {fname} accepted (recorded in sdem-ledger.json and decisions/ with the reason; attributed, not verified)"); return 0
            if a.json: print(json.dumps({'change_set': cs, 'event': ev}, indent=2, ensure_ascii=False)); return 0
            ops = {}
            for c in cs['changes']: ops[c['op']] = ops.get(c['op'], 0) + 1
            print(f"{cs['id']} records {a.person}'s direct edit of {a.layer}: " + ', '.join(f'{n} {k}' for k, n in ops.items()) + f"; change event {ev['id']} with its impact")
            print(f"next: the orchestrator runs  sdem work plan --event {ev['id']} --workspace {a.estate} --agent {ORCHESTRATOR} --person <name>")
            return 0
        f = est.coord / 'change-sets' / f'{a.id}.json'
        if not f.exists(): return _fail(f'{a.id}: no such change set')
        cs = _j(f); ev = next((e for e in est.events() if e['id'] == cs['event']), None)
        print(json.dumps({'change_set': cs, 'event': ev}, indent=2, ensure_ascii=False)); return 0
    except CoordinationError as e:
        return _fail(e)


EVENT_COMMANDS = ('validate', 'analyse', 'pending', 'assess', 'show', 'accept', 'authorise')


def _pairs(items, what):
    out = {}
    for x in items or []:
        if '=' not in x: raise CoordinationError(f'{what} takes LAYER=VALUE, got {x!r}')
        k, val = x.split('=', 1); k = k.strip().upper()
        if k not in FILES: raise CoordinationError(f'{what}: unknown layer {k}')
        out[k] = val.strip()
    return out


def events_main(argv=None):
    import argparse
    argv = list(argv or [])
    if argv[:1] == ['list']: argv = argv[1:]   # `sdem events list` is the list too
    if not argv or argv[0] not in EVENT_COMMANDS:   # the list, as before
        ap = argparse.ArgumentParser(prog='sdem events', description='Change events with their impact, their impact validation and work status (AG-K03, AG-V07). '
                                     f"Subcommands for four-layer impact validation: {', '.join(EVENT_COMMANDS)} (sdem events <subcommand> --help).",
                                     epilog='Examples:\n  sdem events --workspace work/est --open\n  sdem events show CE-001 --workspace work/est', formatter_class=argparse.RawDescriptionHelpFormatter)
        _common(ap, who=False); ap.add_argument('--open', action='store_true', help='only events not yet validated, planned or done')
        a = ap.parse_args(argv)
        try: rows = Estate(a.estate).status()
        except CoordinationError as e: return _fail(e)
        if a.open: rows = [r for r in rows if not r['planned'] or r['open_work_items']]
        if a.json: print(json.dumps(rows, indent=2, ensure_ascii=False)); return 0
        if not rows: print('no change events' + (' open' if a.open else '')); return 0
        for r in rows:
            state = (f"open work: {', '.join(r['open_work_items'])}" if r['open_work_items'] else 'done') if r['planned'] else f"impact validation: {r['validation']}"
            print(f"{r['id']}  round {r['round']}  {r['layer']} {r['change_set']} by {r['agent']} ({r['person']})  — {state}"
                  + (f"; supersede {', '.join(r['impact']['mappings_to_supersede'])}" if r['impact']['mappings_to_supersede'] else ''))
        return 0
    ap = argparse.ArgumentParser(prog='sdem events', formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description='Four-layer impact validation (AG-V01…V10): every layer\'s specialist assesses a change event\'s calculated impact; a person accepts '
                                             'the final assessment and authorises implementation. Only then does `sdem work plan` plan the work.',
                                 epilog='The flow:\n  sdem events validate CE-001 --workspace W --agent sdem-orchestrator --person jane.architect\n'
                                        '  sdem events pending --workspace W --layer A2\n'
                                        '  sdem events assess CE-001 --layer A2 --status no_impact_confirmed --evidence process_model:PM-1 --reasoning "…" --workspace W --agent sdem-a2-bian --person jane.architect\n'
                                        '  sdem events show CE-001 --workspace W\n'
                                        '  sdem events accept CE-001 --reason "…" --authorise --workspace W --person jane.architect')
    sub = ap.add_subparsers(dest='cmd', required=True)
    v = sub.add_parser('validate', help='orchestrator or architect: open the impact validation of a change event — all four layers'); v.add_argument('event'); _common(v)
    an = sub.add_parser('analyse', help='recompute the requirements evaluation and risk findings after new evidence, links or requirements (assessments made against other evidence become stale)')
    an.add_argument('event'); _common(an)
    pe = sub.add_parser('pending', help='layers still to assess — for a layer agent: its own'); _common(pe, who=False); pe.add_argument('--layer', choices=list(FILES)); pe.add_argument('--event')
    x = sub.add_parser('assess', help="a layer agent records its layer's assessment of the calculated impact"); x.add_argument('event'); _common(x)
    x.add_argument('--layer', required=True, choices=CODES)
    x.add_argument('--status', required=True, choices=['impact_confirmed', 'no_impact_confirmed', 'further_investigation_required', 'impact_disputed'])
    x.add_argument('--recommend', choices=['design_change_required', 'review_required', 'no_impact'], help='your classification for the layer (implied for the two *_confirmed statuses)')
    x.add_argument('--evidence', action='extend', nargs='+', default=[], metavar='KIND:REF', help='what you checked — a record, a document, a design (required to confirm no impact or to dispute)')
    x.add_argument('--mapping', action='extend', nargs='+', default=[], metavar='ID', help='the approved links (mapping ids) you relied on')
    x.add_argument('--record', action='extend', nargs='+', default=[], metavar='ID', help='records of your layer that are affected (required for a disputed design change)')
    x.add_argument('--missing', action='extend', nargs='+', default=[], metavar='TEXT', help='links or records that should exist but do not')
    x.add_argument('--uncertainty', default='', help='what you could not establish, and why it does or does not change your conclusion')
    x.add_argument('--confidence', default='medium', choices=['high', 'medium', 'low'])
    x.add_argument('--reasoning', required=True, help='why — in a sentence or two')
    sh = sub.add_parser('show', help='the calculated impact, every assessment, and what still stops acceptance'); sh.add_argument('event'); _common(sh, who=False)
    ac = sub.add_parser('accept', help='a person accepts the final impact assessment (and, with --authorise, authorises implementation)'); ac.add_argument('event')
    ac.add_argument('--workspace', dest='estate', required=True, metavar='DIR'); ac.add_argument('--person', required=True, help='your name — a person; never an agent')
    ac.add_argument('--reason', required=True); ac.add_argument('--final', action='extend', nargs='+', default=[], metavar='LAYER=CLASS', help='your final classification for a layer (required where a specialist disputed or asked for more investigation)')
    ac.add_argument('--resolve', action='extend', nargs='+', default=[], metavar='LAYER=WHY', help='how you resolved a layer you decided'); ac.add_argument('--authorise', action='store_true', help='also authorise implementation now')
    ac.add_argument('--accept-risk', action='extend', nargs='+', default=[], metavar='RF-ID=WHY', help='accept a confirmed requirement breach as a residual risk, with your reason (required for every confirmed breach)')
    ac.add_argument('--json', action='store_true')
    au = sub.add_parser('authorise', help='a person authorises implementation of an accepted assessment'); au.add_argument('event')
    au.add_argument('--workspace', dest='estate', required=True, metavar='DIR'); au.add_argument('--person', required=True); au.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    from . import validation as V
    try:
        est = Estate(a.estate)
        if a.cmd == 'validate':
            v, new = est.request_validation(a.event, a.agent, a.person)
            if a.json: print(json.dumps({**v, 'created': new}, indent=2, ensure_ascii=False)); return 0
            print(f"{v['id']}: impact validation of {a.event} {'opened' if new else 'already open'} — {V.phase(v)}" + (' (legacy event: coverage recomputed now)' if v.get('legacy') else ''))
            for l in V.LEVELS:
                c = v['layers'][l]['calculated']; print(f"  {l}  calculated {c['classification']:<23} {c['result']:<20} evidence {c['evidence']}")
            print(f"next: each layer agent assesses its layer — sdem events assess {a.event} --layer <{'|'.join(CODES)}> --status … --workspace {a.estate} --agent <layer agent> --person <name>")
            return 0
        if a.cmd == 'analyse':
            v = est.analyse(a.event, a.agent, a.person)
            if a.json: print(json.dumps({'event': a.event, 'analysis': v['analysis'], 'summary': V.summary(v, v['analysis']['inputs_sha256'])}, indent=2, ensure_ascii=False)); return 0
            from .requirements import print_analysis
            print_analysis(v['analysis']); return 0
        if a.cmd == 'pending':
            rows = []
            for v in est.validations():
                if V.phase(v) in ('architect_accepted', 'implementation_authorised') or (a.event and v['event'] != a.event): continue
                for l in V.LEVELS:
                    if (not a.layer or l == a.layer) and not V.latest(v, l):
                        c = v['layers'][l]['calculated']
                        rows.append({'event': v['event'], 'layer': l, 'calculated': c['classification'], 'result': c['result'], 'evidence': c['evidence'], 'reason': c['reason']})
            if a.json: print(json.dumps({'pending': rows}, indent=2, ensure_ascii=False)); return 0
            if not rows: print('no layer assessments pending'); return 0
            for r in rows: print(f"{r['event']}  {r['layer']}  calculated {r['calculated']} ({r['result']}, evidence {r['evidence']}) — {r['reason']}")
            return 0
        if a.cmd == 'assess':
            v, x_ = est.assess(a.event, a.layer, a.status, a.agent, a.person, a.reasoning, a.recommend, a.evidence, a.mapping, a.record, a.missing, a.uncertainty, a.confidence)
            if a.json: print(json.dumps({'assessment': x_, 'phase': V.phase(v), 'summary': V.summary(v)}, indent=2, ensure_ascii=False)); return 0
            print(f"{a.event} {a.layer}: {a.status} (recommends {x_['recommended']}; calculated {x_['calculated']}) — validation now {V.phase(v)}"); return 0
        if a.cmd == 'show':
            ev = next((e for e in est.events() if e['id'] == a.event), None)
            if not ev: raise CoordinationError(f'{a.event}: no such change event')
            v = est.validation(a.event)
            from .requirements import inputs_sha
            out = {'event': a.event, 'calculated_impact': ev['impact'], 'validation': v, 'summary': V.summary(v, inputs_sha(est.path)) if v else None}
            if a.json: print(json.dumps(out, indent=2, ensure_ascii=False)); return 0
            print(f"{a.event} ({ev['layer']}, {ev['change_set']}, round {ev['round']}) — impact validation: {V.phase(v) if v else 'not requested'}")
            if not v: print(f"next: sdem events validate {a.event} --workspace {a.estate} --agent {ORCHESTRATOR} --person <name>"); return 0
            sm = out['summary']
            print(f"{'layer':<6}{'structural':<24}{'evidence':<12}{'requirements':<31}{'assessment':<32}{'by':<22}{'recommends':<24}{'final'}")
            for l, r in sm['layers'].items():
                print(f"{l:<6}{r['calculated']:<24}{r['evidence']:<12}{r['requirements']:<31}{(r['assessment'] or '—') + (' (stale)' if r['stale'] else ''):<32}{r['by'] or '—':<22}{r['recommended'] or '—':<24}{r['final'] or '—'}")
                if r['additional_records']: print(f"      additional records named by the {l} agent: {', '.join(r['additional_records'])}")
                if r['missing_relationships']: print(f"      missing links reported: {'; '.join(r['missing_relationships'])}")
                if r['related_within_layer']: print(f"      linked inside {l}, not followed by the impact rules: {', '.join(r['related_within_layer'])}")
            print('  risk findings: ' + ', '.join(f'{k} {len(x)}' for k, x in sm['risks'].items() if x) + (f"; A1 obligations exposed: {', '.join(sm['obligations'])}" if sm['obligations'] else ''))
            print('  (no structural change is not no risk — the requirements column and the findings are separate from it)')
            for o in sm['open']: print(f'  open: {o}')
            return 0
        if a.cmd == 'accept':
            risks = {}
            for x in a.accept_risk:
                if '=' not in x: raise CoordinationError(f'--accept-risk takes RF-ID=WHY, got {x!r}')
                k, why = x.split('=', 1); risks[k.strip()] = why.strip()
            v = est.accept_validation(a.event, a.person, a.reason, _pairs(a.final, '--final'), _pairs(a.resolve, '--resolve'), a.authorise, risks)
            if a.json: print(json.dumps({'acceptance': v['acceptance'], 'phase': V.phase(v)}, indent=2, ensure_ascii=False)); return 0
            print(f"{a.event}: impact assessment accepted by {a.person} — " + ', '.join(f'{l} {c}' for l, c in v['acceptance']['final'].items()) + f"; now {V.phase(v)}")
            if V.phase(v) == 'implementation_authorised': print(f"next: the orchestrator plans the work — sdem work plan --event {a.event} --workspace {a.estate} --agent {ORCHESTRATOR} --person {a.person}")
            return 0
        v = est.authorise(a.event, a.person)
        print(json.dumps({'event': a.event, 'phase': V.phase(v)}) if a.json else f'{a.event}: implementation authorised by {a.person}'); return 0
    except CoordinationError as e:
        return _fail(e)


def work_main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog='sdem work', description='Work items — the orchestrator plans them from a change event; layer agents claim and answer them (AG-K04).',
                                 epilog='Examples:\n  sdem work plan --event CE-001 --workspace work/est --agent sdem-orchestrator --person jane.architect\n'
                                        '  sdem work list --workspace work/est --layer A3 --status open\n'
                                        '  sdem work claim WI-001 --workspace work/est --agent sdem-a3-application --person jane.architect',
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('plan', help='orchestrator: turn a change event\'s impact into work items'); p.add_argument('--event', required=True); _common(p)
    p.add_argument('--max-rounds', type=int, default=MAX_ROUNDS, help=f'stop and ask the architect after this many rounds (default and most {MAX_ROUNDS}; only the architect may raise it)')
    l = sub.add_parser('list', help='work items'); _common(l, who=False); l.add_argument('--layer', choices=CODES); l.add_argument('--status', choices=['open', 'in_progress', 'done', 'blocked', 'cancelled'])
    for name, hlp in (('claim', 'a layer agent takes a work item'), ('block', 'a work item cannot proceed — say why'), ('cancel', 'drop a work item — say why'), ('reopen', 'return a work item to open')):
        x = sub.add_parser(name, help=hlp); x.add_argument('id'); _common(x); x.add_argument('--note', default='')
    a = ap.parse_args(argv)
    try:
        est = Estate(a.estate)
        if a.cmd == 'plan':
            r = est.plan(a.event, a.agent, a.person, a.max_rounds)
            if a.json: print(json.dumps(r, indent=2, ensure_ascii=False)); return 0
            if r.get('stopped'): print(f"STOP: {r['stopped']}"); return 1
            print(f"{a.event}: {len(r['work_items'])} work item(s)")
            for w in r['work_items']: print(f"  {w['id']}  {w['layer']}  {', '.join(w['records'])}  — {w['action']}")
            if r['review']: print('for the architect to review (no work item): ' + ', '.join(f"{x['level']} {x['id']}" for x in r['review']))
            return 0
        if a.cmd == 'list':
            rows = [w for w in est.work() if (not a.layer or w['layer'] == a.layer) and (not a.status or w['history'][-1]['status'] == a.status)]
            if a.json: print(json.dumps(rows, indent=2, ensure_ascii=False)); return 0
            if not rows: print('no work items'); return 0
            for w in rows:
                h = w['history'][-1]
                print(f"{w['id']}  {w['layer']}  {h['status']:<11} {', '.join(w['records'])}  (event {w['event']}, round {w['round']})  — {w['action']}" + (f"  [held by {h['agent']}]" if h['status'] == 'in_progress' else ''))
            return 0
        status = {'claim': 'in_progress', 'block': 'blocked', 'cancel': 'cancelled', 'reopen': 'open'}[a.cmd]
        w = est.transition(a.id, status, a.agent, a.person, a.note)
        print(json.dumps(w, indent=2, ensure_ascii=False) if a.json else f"{w['id']} is now {status} ({a.agent}, {a.person})"); return 0
    except CoordinationError as e:
        return _fail(e)


# ------------------------------------------------------------------ D2: `sdem check` checks the coordination records too

TRANSITIONS = {'open': {'in_progress', 'cancelled'}, 'in_progress': {'done', 'blocked', 'cancelled', 'open'}, 'blocked': {'in_progress', 'cancelled'}}


def check_coordination(estate_dir):
    """Issues in <workspace>/coordination/: schema, file name = id, references resolve, work-item histories follow the allowed
    steps, every step has agent and person (CTL-20). Empty when there is no coordination folder."""
    coord = Path(estate_dir) / 'coordination'
    if not coord.exists(): return [], 0
    root = json.loads(SCHEMA.read_text(encoding='utf-8')); issues = []
    def load(folder):
        out = {}
        for f in sorted((coord / folder).glob('*.json')) if (coord / folder).exists() else []:
            try: r = _j(f)
            except ValueError as e: issues.append(f'{folder}/{f.name}: not valid JSON ({e})'); continue
            if r.get('id') != f.stem: issues.append(f"{folder}/{f.name}: file name does not match its id {r.get('id')!r}")
            out[r.get('id')] = r
        return out
    sets, events, work = load('change-sets'), load('events'), load('work-items')
    from . import validation as V
    vals = load('validations')
    for v in vals.values():   # AG-V10: the validation records are checked like the others
        issues += [f'validations/{x}' for x in V.check(v, root, check_schema, is_person, AGENT_LAYER, HUMAN)]
        if v.get('event') not in events: issues.append(f"validations/{v.get('id')}: event {v.get('event')} not found")
    for e in events.values():
        issues += [f"events/{e.get('id')}: {x}" for x in check_schema(e, root['$defs']['event'], root)]
        if e.get('change_set') not in sets: issues.append(f"events/{e.get('id')}: change set {e.get('change_set')} not found")
    for c in sets.values():
        for k in ('layer', 'reason', 'changes', 'agent', 'person', 'event'):
            if not c.get(k): issues.append(f"change-sets/{c.get('id')}: missing {k}" + (' (CTL-20)' if k in ('agent', 'person') else ''))
        if c.get('event') and c['event'] not in events: issues.append(f"change-sets/{c.get('id')}: event {c['event']} not found")
        for w in c.get('work_items', []):
            if w not in work: issues.append(f"change-sets/{c.get('id')}: work item {w} not found")
    for w in work.values():
        issues += [f"work-items/{w.get('id')}: {x}" for x in check_schema(w, root['$defs']['work_item'], root)]
        if w.get('event') not in events: issues.append(f"work-items/{w.get('id')}: event {w.get('event')} not found")
        h = w.get('history') or []
        if h and h[0].get('status') != 'open': issues.append(f"work-items/{w.get('id')}: history must start 'open'")
        for a, b in zip(h, h[1:]):
            if b.get('status') not in TRANSITIONS.get(a.get('status'), set()): issues.append(f"work-items/{w.get('id')}: step {a.get('status')} → {b.get('status')} is not allowed")
    # AG-S08 / CTL-20: every change to a layer's dataset since its first change set came through a change set
    for layer, fname in FILES.items():
        chain = sorted((c for c in sets.values() if c.get('layer') == layer and c.get('dataset')), key=lambda c: (c.get('created_at', ''), _seq(c['id'])))
        for a, b in zip(chain, chain[1:]):
            if b['dataset']['before_sha256'] != a['dataset']['after_sha256']:
                issues.append(f"CTL-20 (AG-S08): {fname} was changed outside a change set between {a['id']} and {b['id']} (or two branches changed it in parallel)")
        f = Path(estate_dir) / fname
        if chain and f.exists() and _file_sha(f) != chain[-1]['dataset']['after_sha256']:
            issues.append(f"CTL-20 (AG-S08): {fname} was changed outside a change set since {chain[-1]['id']} — propose the change as a change set, or record a person's edit: "
                          f"sdem change adopt --workspace {estate_dir} --layer {layer} --person <name> --reason <why>")
    return issues, len(sets) + len(events) + len(work) + len(vals)
