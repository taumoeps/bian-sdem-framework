"""The rule-based Architecture Relationship Inference Engine (relationship-rules-spec.md; procedure docs/mapping-execution.md).

Reads a graph through the graph access layer (sdem/store.py GraphReader), applies the Relationship Rules Model
(metamodel/relationship-rules.json) in fill-step order, and returns:
  proposals  — catalogue-typed records (the nine relationship types), status `proposed`, for sdem-validate and an architect
  candidates — reports for candidate, conditional, institution-only and derived-path rows, `relationship` = the plan ID
  log        — one record per attempt, including refusals (the evidence base; REQ-O-02)
It never approves, never invents an instance, and never re-proposes a link that is already approved.

Built step by step against the acceptance harness (sdem/acceptance.py). Implemented: step 1 (data joins).
"""
import json
from pathlib import Path

from .paths import DATA_ROOT

BAND = {'high': 0.8, 'medium': 0.6, 'low': 0.4}
LOWER = {'high': 'medium', 'medium': 'low', 'low': 'low'}


def _rules():
    return {m['id']: m for m in json.loads((DATA_ROOT / 'metamodel' / 'relationship-rules.json').read_text(encoding='utf-8'))['mappings']}


def _list(v):
    return [] if v is None else (v if isinstance(v, list) else [v])


class Run:
    """One inference run over one graph: the state every step reads and writes."""

    def __init__(self, reader, uc):
        self.r, self.mm, self.uc = reader, reader.mm, uc
        self.rules = _rules()
        self.proposals, self.candidates, self.log = [], [], []
        self.approved = {(e['source']['id'], e['relationship'], e['target']['id']) for e in reader.fg.edges()}
        self.proposed = {}   # (src, rel, tgt) -> proposal record (this run)
        self.reported = {}   # (src, plan id, tgt) -> candidate record (this run)
        self.ids = {}        # (level, id) -> node, latest version
        for n in reader.nodes(): self.ids[(n['level'], n['id'])] = n

    # -- lookups
    def of(self, etype):
        return self.r.nodes(type=etype)

    def get(self, iid, etype=None, level=None):
        """The instance with this id (of this type or a subtype), or None — never invented."""
        for (lvl, i), n in self.ids.items():
            if i == iid and (level is None or lvl == level) and (etype is None or self.mm.is_a(n['type'], etype)):
                return n
        return None

    @staticmethod
    def attr(n, k):
        return (n.get('attributes') or {}).get(k)

    @staticmethod
    def ref(n):
        r = {'id': n['id'], 'type': n['type'], 'version': n['version']}
        if n.get('canonical_id'): r['canonical_id'] = n['canonical_id']
        return r

    def band(self, plan_id, fallback=False):
        b = self.rules[plan_id]['confidence']
        return LOWER[b] if fallback else b

    # -- outputs
    def attempt(self, plan_id, src, tgt, step, data_read, reasoning, proposal_id=None, fallback=False, predicted=None, given=None, outcome=None):
        self.log.append({'plan_id': plan_id, 'connection': f"{src} → {tgt}" if tgt else src, 'step_assigned': self.rules[plan_id]['fill_step'], 'step_used': step,
                         'fallback': fallback, 'data_read': data_read, 'reasoning': reasoning, 'confidence_predicted': predicted or self.rules[plan_id]['confidence'],
                         'confidence_given': given, 'proposal_id': proposal_id, 'outcome': outcome or ('proposed' if proposal_id else 'no_proposal')})

    def propose(self, plan_id, rel, src, tgt, step, working, data_read, fallback=False, band=None):
        """A catalogue-typed proposal. Skips (and logs) a link already approved or already proposed in this run."""
        k = (src['id'], rel, tgt['id'])
        if k in self.approved:
            self.attempt(plan_id, src['id'], tgt['id'], step, data_read, 'already approved — not re-proposed', outcome='already_approved'); return None
        if k in self.proposed:
            self.proposed[k]['evidence'].append(f'engine_rationale:{plan_id} step{step} also: {working}'); return self.proposed[k]
        b = band or self.band(plan_id, fallback); pid = f'P-{self.uc}-{len(self.proposals) + 1:03d}'
        rec = {'mapping_id': pid, 'source': self.ref(src), 'relationship': rel, 'target': self.ref(tgt), 'status': 'proposed', 'confidence': BAND[b],
               'evidence': [f'engine_rationale:{plan_id} step{step} {working}'], 'rationale': working, 'baseline_id': f'ENGINE-RUN-{self.uc}', 'created_by': ENGINE_NAME}
        self.proposals.append(rec); self.proposed[k] = rec
        self.attempt(plan_id, src['id'], tgt['id'], step, data_read, working, pid, fallback, given=BAND[b])
        return rec

    def report(self, plan_id, src, tgt, step, working, data_read, fallback=False, band=None):
        """A candidate report (relationship = plan ID); not a registry record."""
        k = (src['id'], plan_id, tgt['id'])
        if k in self.reported:
            return self.reported[k]
        b = band or self.band(plan_id, fallback); cid = f'C-{self.uc}-{len(self.candidates) + 1:03d}'
        rec = {'mapping_id': cid, 'source': self.ref(src), 'relationship': plan_id, 'target': self.ref(tgt), 'status': 'proposed', 'confidence': BAND[b],
               'evidence': [f'engine_rationale:{plan_id} step{step} {working}'], 'rationale': working, 'created_by': f'candidate_rule:{plan_id}'}
        self.candidates.append(rec); self.reported[k] = rec
        self.attempt(plan_id, src['id'], tgt['id'], step, data_read, working, cid, fallback, given=BAND[b])
        return rec

    # ------------------------------------------------------------ step 1 — data joins (mapping-execution.md §3, step 1)
    def step1(self):
        comps = self.of('A3.ApplicationComponent')
        deps = self.of('A4.Deployment')
        # S32 DEPLOYED_AS: the deployment names the component, or the component lists the deployment
        for c in comps:
            for d in deps:
                via = []
                if self.attr(d, 'component_id') == c['id']: via.append(f"a4 {d['id']}.component_id = {c['id']}")
                if d['id'] in _list(self.attr(c, 'deployed_as')): via.append(f"a3 {c['id']}.deployed_as lists {d['id']}")
                if via:
                    self.propose('S32', 'DEPLOYED_AS', c, d, 1, 'data join; ' + '; '.join(via), [v.split(' ', 2)[1] for v in via])
        # S33 / S34 / S35 DEPLOYED_ON: logged under the plan row of the target's entity type
        for c in comps:
            hosts = {}
            for x in _list(self.attr(c, 'deployed_on')): hosts.setdefault(x, []).append(f"a3 {c['id']}.deployed_on lists {x}")
            for p in self.r.nodes(level='A4'):
                if c['id'] in _list(self.attr(p, 'hosts')): hosts.setdefault(p['id'], []).append(f"a4 {p['id']}.hosts lists {c['id']}")
            for d in deps:
                if self.attr(d, 'component_id') == c['id'] and self.attr(d, 'platform_id'):
                    hosts.setdefault(self.attr(d, 'platform_id'), []).append(f"a4 deployment {d['id']} (component {c['id']}) names platform {self.attr(d, 'platform_id')}")
            for x, via in hosts.items():
                t = self.get(x, 'A4.InfrastructureComponent', 'A4')
                if t is None:
                    self.attempt('S33', c['id'], x, 1, via, f'{x} is not an A4 instance in the export — no instance to map to'); continue
                if self.mm.is_a(t['type'], 'A4.Deployment'): continue  # a deployment is DEPLOYED_AS, not a platform
                plan = 'S34' if self.mm.is_a(t['type'], 'A4.Node') else 'S35' if self.mm.is_a(t['type'], 'A4.Device') else 'S33'
                note = {'S34': ', logged under S34 because the target is A4.Node', 'S35': ', logged under S35 because the target is A4.Device',
                        'S33': ' (S36 subsumed in S33)' if self.mm.is_a(t['type'], 'A4.SystemSoftware') else ''}[plan]
                self.propose(plan, 'DEPLOYED_ON', c, t, 1, f'data join{note}; ' + '; '.join(via), via, band=self.rules['S33']['confidence'])
        # candidate joins: (plan, source type, attribute on source, target type, reverse attribute on target)
        joins = [('S39', 'A3.ApplicationComponent', 'built_as', 'A4.Artifact', 'of_component'),
                 ('S41', 'A3.ApplicationService', 'consumes', 'A4.TechnologyService', None),
                 ('S43', 'A3.ApplicationInterface', 'exposed_through', 'A4.TechnologyInterface', 'exposes'),
                 ('S45', 'A3.ApplicationFunction', 'consumes', 'A4.TechnologyService', None),
                 ('S49', 'A3.DataEntity', 'stored_in', 'A4.Artifact', None),
                 ('S50', 'A3.DataEntity', 'stored_in', 'A4.SystemSoftware', None),
                 ('S51', 'A3.Event', 'published_to', 'A4.TechnologyService', None),
                 ('S06', 'A1.BusinessActivity', 'invokes', 'A2.ServiceOperation', None)]
        for plan, st, key, tt, back in joins:
            for s in self.of(st):
                found = {}
                for x in _list(self.attr(s, key)):
                    t = self.get(x, tt)
                    if t: found.setdefault(t['id'], (t, []))[1].append(f"{s['level'].lower()} {s['id']}.{key} lists {x}")
                if back:
                    for t in self.of(tt):
                        if s['id'] in _list(self.attr(t, back)): found.setdefault(t['id'], (t, []))[1].append(f"{t['level'].lower()} {t['id']}.{back} names {s['id']}")
                for t, via in found.values():
                    self.report(plan, s, t, 1, 'data join; ' + '; '.join(via), via)
        # S37 network zone: the component's network_zone wins over a network's `connects` (C3 finding 3)
        for c in comps:
            z = self.attr(c, 'network_zone')
            if z and self.get(z, 'A4.CommunicationNetwork'):
                self.report('S37', c, self.get(z, 'A4.CommunicationNetwork'), 1, f"data join; a3 {c['id']}.network_zone = {z}", [f"{c['id']}.network_zone"])
        # S38 path carries the component
        for p in self.of('A4.Path'):
            for x in _list(self.attr(p, 'carries')):
                c = self.get(x, 'A3.ApplicationComponent')
                if c: self.report('S38', c, p, 1, f"data join; a4 {p['id']}.carries lists {x}", [f"{p['id']}.carries"])

    def run(self):
        self.step1()
        return {'proposals': self.proposals, 'candidates': self.candidates, 'log': self.log}


ENGINE_NAME = 'sdem-rules/0.10'


class RulesEngine:
    name = ENGINE_NAME

    def infer(self, reader, case=None):
        return Run(reader, (case or {}).get('id', 'RUN')).run()
