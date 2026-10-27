"""Agent platform coordination — change sets, change events, impact results, work items (docs/sdem-agent-platform-spec.md).

The layer agents (A1–A4) and the orchestrator coordinate only through these records, never by messaging each other
(AG-D02). They are stored with the estate, in `<estate>/coordination/`, append-only (AG-R05):

  change-sets/CS-….json     one layer's proposed record changes, with agent and person (AG-R01)
  events/CE-….json          change events, each with its stored impact result (AG-R02, AG-R03)
  work-items/WI-….json      one task for one layer, with its history of states (AG-R04)

One file per record, and ids scoped to the Git branch they were made on (CS-<branch>-001; plain CS-001 on main or
outside Git), so agents working on different branches never create the same id or edit the same file.

Controls: CTL-19 layer ownership (a change set changes one declared layer; an agent only its own layer; never the
registry), CTL-20 change provenance (agent and person on every change set and work-item step). A change set lands only
if the estate's checks show no new error (the rulebook, CTL-01…17).
"""
import copy, datetime, json, re, subprocess
from pathlib import Path

from .graph import FederatedGraph
from .metamodel import Metamodel, PROJECTED_PREFIXES
from .validate import check_schema

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / 'schema' / 'coordination.schema.json'
FILES = {'A1': 'a1-business.json', 'A2': 'a2-service-domain.json', 'A3': 'a3-application.json', 'A4': 'a4-technology.json'}
REGISTRY = 'mappings.json'
AGENT_LAYER = {'sdem-a1-business': 'A1', 'sdem-a2-bian': 'A2', 'sdem-a3-application': 'A3', 'sdem-a4-technology': 'A4'}
ORCHESTRATOR = 'sdem-orchestrator'
HUMAN = 'architect'                       # a person working without an agent may change any one layer
KIND_OF = {'update': 'modify', 'retire': 'retire', 'add': None}
STRENGTH = {'design_change_required': 3, 'review_required': 2, 'no_impact': 1}
MAX_ROUNDS = 3                            # AG-S07 / AG-Q02


class CoordinationError(Exception):
    """A request the controls reject; the message names the control."""


def _now(): return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
def _j(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def _w(p, obj): Path(p).parent.mkdir(parents=True, exist_ok=True); Path(p).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


class Estate:
    """An estate folder: the four architecture datasets, the registry, and the coordination records."""

    def __init__(self, path, now=None):
        self.path = Path(path); self.coord = self.path / 'coordination'; self.now = now or _now
        missing = [f for f in list(FILES.values()) + [REGISTRY] if not (self.path / f).exists()]
        if missing: raise CoordinationError(f'{self.path}: not an estate folder (missing {", ".join(missing)})')

    # -- records
    def datasets(self): return {lvl: _j(self.path / f) for lvl, f in FILES.items()}
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
        """The estate's errors under the rulebook (the same checks as `sdem check`)."""
        mm = Metamodel.load(); from .graph import LevelGraph
        ds = datasets or self.datasets(); reg = registry or self.registry()
        fg = FederatedGraph([LevelGraph(d, mm) for d in ds.values()], [reg], mm)
        return sorted(f'{k}: {i}' for k, v in fg.check().items() for i in v), fg

    # -- change sets (AG-K01)
    def propose(self, change_set, agent, person, work_ids=(), catalogue=None):
        issues = check_schema(change_set, json.loads(SCHEMA.read_text(encoding='utf-8'))['$defs']['change_set_input'], json.loads(SCHEMA.read_text(encoding='utf-8')))
        if issues: raise CoordinationError('change set format: ' + '; '.join(issues[:5]))
        if not (agent or '').strip() or not (person or '').strip():
            raise CoordinationError('CTL-20: a change set needs both the agent and the person behind it')
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
        before, _ = self.check(ds)
        new = copy.deepcopy(ds); target = new[layer]; by_id = {i['id']: i for i in target['instances']}
        ids_anywhere = {i['id'] for d in ds.values() for i in d['instances']}
        cat = {i['id']: i for i in _j(catalogue)['instances']} if catalogue else None
        changed = []
        for n, c in enumerate(change_set['changes'], 1):
            op, rec = c['op'], c['record']; rid = rec['id']
            if op == 'remove': raise CoordinationError(f'change {n}: remove is not a change-set operation — retire the record instead')
            if str(rid).startswith(PROJECTED_PREFIXES): raise CoordinationError(f'CTL-16: change {n}: {rid} is a projected or design record, never real data')
            if not str(rec.get('type', layer + '.')).startswith(layer + '.'):
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
                if rid not in by_id: raise CoordinationError(f'change {n}: {rid} is not a {layer} record in this estate')
                old = by_id[rid]
                if op == 'update':
                    if rec.get('type', old['type']) != old['type']: raise CoordinationError(f'change {n}: {rid} cannot change type — retire it and add a new record')
                    replacement = {**rec, 'type': old['type']}
                    old.clear(); old.update(replacement)
                else:
                    old['lifecycle_status'] = 'retired'
                changed.append((rid, c.get('kind') or KIND_OF[op]))
        rels = change_set.get('relationships', {})
        lay_ids = {i['id'] for i in target['instances']}
        for r in rels.get('add', []):
            if r['source'] not in lay_ids or r['target'] not in lay_ids: raise CoordinationError(f"CTL-19: relationship {r['source']} → {r['target']} leaves layer {layer}")
            if r not in target['relationships']: target['relationships'].append(r)
        for r in rels.get('remove', []):
            if r in target['relationships']: target['relationships'].remove(r)
        after, fg = self.check(new)
        added_errors = [e for e in after if e not in before]
        if added_errors: raise CoordinationError('the change set breaks the rulebook — nothing was changed:\n  ' + '\n  '.join(added_errors[:10]))
        # land it
        cs_id = self._next('CS'); ce_id = self._next('CE')
        round_ = max(w['round'] for w in wis) + 1 if wis else 1
        before = _file_sha(self.path / FILES[layer])
        _w(self.coord / 'snapshots' / f'{cs_id}.before.json', ds[layer])   # the layer as it was — what `sdem change revert` restores (T5)
        _w(self.path / FILES[layer], new[layer])
        cs = {'id': cs_id, **change_set, 'agent': agent, 'person': person, 'created_at': self.now(), 'work_items': [w['id'] for w in wis], 'event': ce_id, 'branch': _branch(self.path),
              'dataset': {'file': FILES[layer], 'before_sha256': before, 'after_sha256': _file_sha(self.path / FILES[layer])}}
        _w(self.coord / 'change-sets' / f'{cs_id}.json', cs)
        _w(self.coord / 'snapshots' / f'{cs_id}.json', new[layer])   # the layer as this change set left it (AG-S08, and undo later)
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
        if added: raise CoordinationError('the result would break the rulebook — nothing was changed:\n  ' + '\n  '.join(added[:10]))
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
        again. The edit must keep the rulebook (no new errors); its impact is recorded like any change set's."""
        if layer not in FILES: raise CoordinationError(f'unknown layer {layer}')
        if not (person or '').strip() or person in AGENT_LAYER or person in (ORCHESTRATOR, HUMAN): raise CoordinationError('CTL-20: adopt needs the name of the person who made the edit')
        if not (reason or '').strip(): raise CoordinationError('adopt needs a reason')
        last = self._last_change_set(layer)
        if not last: raise CoordinationError(f'{layer} has no change sets yet — its current content is the starting point; nothing to adopt')
        if _file_sha(self.path / FILES[layer]) == last['dataset']['after_sha256']: raise CoordinationError(f"{FILES[layer]} has not changed since {last['id']} — nothing to adopt")
        prev = _j(self.coord / 'snapshots' / f"{last['id']}.json")
        return self._record(layer, prev, self.datasets()[layer], HUMAN, person, reason, {'adopted': True, '_before_sha': last['dataset']['after_sha256']})

    def revert(self, cs_id, agent, person, reason=''):
        """T5 / AG-K06: undo a change set — restore its layer as it was before — recorded as a new change set and change event.
        Only the latest change set of a layer, only when the layer is exactly as it left it; CTL-19/20 apply; open work
        from the reverted change event is cancelled, with a note."""
        f = self.coord / 'change-sets' / f'{cs_id}.json'
        if not f.exists(): raise CoordinationError(f'{cs_id}: no such change set')
        target = _j(f); layer = target['layer']
        if not (agent or '').strip() or not (person or '').strip(): raise CoordinationError('CTL-20: a revert needs both the agent and the person behind it')
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
            if not kind:
                rows.setdefault(rid, {'id': rid, 'level': layer, 'classification': 'design_change_required', 'via': [], 'cause': f'{rid} added'}); continue
            r = fg.impact(rid, kind)
            supersede |= set(r['mappings_to_supersede'])
            for x in r['instances']:
                cur = rows.get(x['id'])
                row = {'id': x['id'], 'name': x['name'], 'level': x['level'], 'classification': x['classification'], 'via': x['via'], 'cause': f'{kind} of {rid}'}
                if not cur or STRENGTH[x['classification']] > STRENGTH[cur['classification']]: rows[x['id']] = row
        return {'records': sorted(rows.values(), key=lambda x: (x['level'] or '', x['id'])), 'mappings_to_supersede': sorted(supersede),
                'changed': [rid for rid, _ in changed]}

    # -- work items (AG-K04)
    def plan(self, event_id, agent, person, max_rounds=MAX_ROUNDS):
        """The orchestrator turns an event's impact into work items: one per record outside the changed layer that needs a
        design change. Review notices are reported, not turned into work (impact rules: 'nothing further')."""
        if agent != ORCHESTRATOR and agent != HUMAN: raise CoordinationError(f'only the orchestrator (or an architect) plans work, not {agent}')
        if not (person or '').strip(): raise CoordinationError('CTL-20: planning needs the person behind it')
        ev = next((e for e in self.events() if e['id'] == event_id), None)
        if not ev: raise CoordinationError(f'{event_id}: no such change event')
        work = self.work()
        if any(w['event'] == event_id for w in work): raise CoordinationError(f'{event_id}: already planned')
        todo = [r for r in ev['impact']['records'] if r['classification'] == 'design_change_required' and r['level'] != ev['layer'] and r['id'] not in ev['impact']['changed']]
        review = [r for r in ev['impact']['records'] if r['classification'] == 'review_required']
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
        if not (agent or '').strip() or not (person or '').strip(): raise CoordinationError('CTL-20: every work-item step needs the agent and the person')
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
            out.append({**e, 'work_items': [w['id'] for w in items], 'open_work_items': open_items, 'planned': bool(items) or not any(
                r['classification'] == 'design_change_required' and r['level'] != e['layer'] and r['id'] not in e['impact']['changed'] for r in e['impact']['records'])})
        return out


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
    ap.add_argument('--estate', required=True, metavar='DIR', help='the estate folder (a1…a4 datasets, mappings.json)')
    if who:
        ap.add_argument('--agent', required=True, help=f"the agent: {', '.join(list(AGENT_LAYER) + [ORCHESTRATOR])}, or '{HUMAN}' for a person working without an agent")
        ap.add_argument('--person', required=True, help='the person behind the agent (CTL-20)')
    ap.add_argument('--json', action='store_true')


def _fail(e):
    import sys
    print(f'ERROR: {e}', file=sys.stderr); return 1


def change_main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog='sdem change', description='Change sets: one layer\'s record changes, checked against the rulebook and controls before they land (AG-K01/K02).',
                                 epilog='Examples (agent platform):\n  sdem change propose cs-rehost.json --estate work/est --agent sdem-a4-technology --person jane.architect\n'
                                        '  sdem change propose cs-a3.json --estate work/est --agent sdem-a3-application --person jane.architect --work WI-001 WI-002\n'
                                        '  sdem change show CS-001 --estate work/est\n'
                                        '  sdem change revert CS-002 --estate work/est --agent sdem-a3-application --person jane.architect --reason "wrong cluster"', formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('propose', help='check and apply a change set to its layer; records the change event and its impact')
    p.add_argument('change_set', help='change set file (JSON): layer, reason, changes[, relationships]')
    _common(p); p.add_argument('--work', nargs='*', default=[], metavar='WI', help='work item(s) this change set answers (claimed by the same agent)')
    p.add_argument('--catalogue', metavar='FILE', help='BIAN catalogue (A2 dataset) — required when an A2 change set adds records')
    s = sub.add_parser('show', help='a change set with its event and impact'); s.add_argument('id'); _common(s, who=False)
    r = sub.add_parser('revert', help='undo the latest change set of a layer — recorded as a new change set (T5)'); r.add_argument('id'); _common(r); r.add_argument('--reason', default='')
    d = sub.add_parser('adopt', help="record a person's direct edit of a layer as a change set (AG-S08)"); _common(d, who=False)
    d.add_argument('--layer', required=True, choices=list(FILES)); d.add_argument('--person', required=True, help='who made the edit'); d.add_argument('--reason', required=True)
    a = ap.parse_args(argv)
    try:
        est = Estate(a.estate)
        if a.cmd == 'propose':
            cs, ev = est.propose(_j(a.change_set), a.agent, a.person, a.work, a.catalogue)
            if a.json: print(json.dumps({'change_set': cs, 'event': ev}, indent=2, ensure_ascii=False)); return 0
            imp = ev['impact']; design = [r for r in imp['records'] if r['classification'] == 'design_change_required' and r['level'] != ev['layer'] and r['id'] not in imp['changed']]
            print(f"{cs['id']} applied to {cs['layer']} ({len(cs['changes'])} change(s)) by {a.agent} for {a.person}" + (f"; answers {', '.join(cs['work_items'])}" if cs['work_items'] else ''))
            print(f"change event {ev['id']} recorded (round {ev['round']}): {len(design)} record(s) in other layers need a design change"
                  + (f"; links to supersede: {', '.join(imp['mappings_to_supersede'])}" if imp['mappings_to_supersede'] else ''))
            for r in design: print(f"  {r['level']}  {r['id']}  {r.get('name') or ''}  — {r['cause']}, via {', '.join(r['via']) or '-'}")
            if cs.get('branch') in ('main', 'master'): print('NOTE: you are on the main branch — agent changes belong on a branch, reviewed in a pull request (AG-W01)')
            print('NOTE: graph stores built from this estate are now out of date — rebuild them before trace, impact or view: sdem build --estate … --out <graph>')
            print(f"next: the orchestrator runs  sdem work plan --event {ev['id']} --estate {a.estate} --agent {ORCHESTRATOR} --person <name>"
                  + f"\n      and the rules engine proposes the new links:  sdem link {a.estate}/a*.json {a.estate}/mappings.json --out <dir>")
            return 0
        if a.cmd == 'revert':
            cs, ev, cancelled = est.revert(a.id, a.agent, a.person, a.reason)
            if a.json: print(json.dumps({'change_set': cs, 'event': ev, 'cancelled_work_items': cancelled}, indent=2, ensure_ascii=False)); return 0
            print(f"{cs['id']} reverts {a.id}: {cs['layer']} restored as it was before ({len(cs['changes'])} record change(s)); change event {ev['id']} with its impact"
                  + (f"; cancelled open work items {', '.join(cancelled)}" if cancelled else ''))
            print(f"next: the orchestrator runs  sdem work plan --event {ev['id']} --estate {a.estate} --agent {ORCHESTRATOR} --person <name>; rebuild graph stores")
            return 0
        if a.cmd == 'adopt':
            cs, ev = est.adopt(a.layer, a.person, a.reason)
            if a.json: print(json.dumps({'change_set': cs, 'event': ev}, indent=2, ensure_ascii=False)); return 0
            ops = {}
            for c in cs['changes']: ops[c['op']] = ops.get(c['op'], 0) + 1
            print(f"{cs['id']} records {a.person}'s direct edit of {a.layer}: " + ', '.join(f'{n} {k}' for k, n in ops.items()) + f"; change event {ev['id']} with its impact")
            print(f"next: the orchestrator runs  sdem work plan --event {ev['id']} --estate {a.estate} --agent {ORCHESTRATOR} --person <name>")
            return 0
        f = est.coord / 'change-sets' / f'{a.id}.json'
        if not f.exists(): return _fail(f'{a.id}: no such change set')
        cs = _j(f); ev = next((e for e in est.events() if e['id'] == cs['event']), None)
        print(json.dumps({'change_set': cs, 'event': ev}, indent=2, ensure_ascii=False)); return 0
    except CoordinationError as e:
        return _fail(e)


def events_main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog='sdem events', description='Change events with their impact and work status (AG-K03).',
                                 epilog='Example:\n  sdem events --estate work/est --open', formatter_class=argparse.RawDescriptionHelpFormatter)
    _common(ap, who=False); ap.add_argument('--open', action='store_true', help='only events not yet planned or with open work')
    a = ap.parse_args(argv)
    try: rows = Estate(a.estate).status()
    except CoordinationError as e: return _fail(e)
    if a.open: rows = [r for r in rows if not r['planned'] or r['open_work_items']]
    if a.json: print(json.dumps(rows, indent=2, ensure_ascii=False)); return 0
    if not rows: print('no change events' + (' open' if a.open else '')); return 0
    for r in rows:
        state = 'needs planning' if not r['planned'] else (f"open work: {', '.join(r['open_work_items'])}" if r['open_work_items'] else 'done')
        print(f"{r['id']}  round {r['round']}  {r['layer']} {r['change_set']} by {r['agent']} ({r['person']})  — {state}"
              + (f"; supersede {', '.join(r['impact']['mappings_to_supersede'])}" if r['impact']['mappings_to_supersede'] else ''))
    return 0


def work_main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog='sdem work', description='Work items — the orchestrator plans them from a change event; layer agents claim and answer them (AG-K04).',
                                 epilog='Examples:\n  sdem work plan --event CE-001 --estate work/est --agent sdem-orchestrator --person jane.architect\n'
                                        '  sdem work list --estate work/est --layer A3 --status open\n'
                                        '  sdem work claim WI-001 --estate work/est --agent sdem-a3-application --person jane.architect',
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('plan', help='orchestrator: turn a change event\'s impact into work items'); p.add_argument('--event', required=True); _common(p)
    p.add_argument('--max-rounds', type=int, default=MAX_ROUNDS, help=f'stop and ask the architect after this many rounds (default {MAX_ROUNDS})')
    l = sub.add_parser('list', help='work items'); _common(l, who=False); l.add_argument('--layer', choices=list(FILES)); l.add_argument('--status', choices=['open', 'in_progress', 'done', 'blocked', 'cancelled'])
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
    """Issues in <estate>/coordination/: schema, file name = id, references resolve, work-item histories follow the allowed
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
                          f"sdem change adopt --estate {estate_dir} --layer {layer} --person <name> --reason <why>")
    return issues, len(sets) + len(events) + len(work)
