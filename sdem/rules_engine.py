"""The rule-based Architecture Relationship Inference Engine (relationship-rules-spec.md; procedure docs/mapping-execution.md).

Reads a graph through the graph access layer (sdem/store.py GraphReader), applies the Relationship Rules Model
(metamodel/relationship-rules.json) in fill-step order, and returns:
  proposals  — catalogue-typed records (the nine relationship types), status `proposed`, for sdem-validate and an architect
  candidates — reports for candidate, conditional, institution-only and derived-path rows, `relationship` = the plan ID
  log        — one record per attempt, including refusals (the evidence base; REQ-O-02)
It never approves, never invents an instance, and never re-proposes a link that is already approved.

Built step by step against the acceptance harness (sdem/acceptance.py). Implemented: step 1 (data joins), step 2 (BIAN REST decision procedure).
"""
import json, re
from pathlib import Path

from .paths import DATA_ROOT

BAND = {'high': 0.8, 'medium': 0.6, 'low': 0.4}
LOWER = {'high': 'medium', 'medium': 'low', 'low': 'low'}


def _rules():
    return {m['id']: m for m in json.loads((DATA_ROOT / 'metamodel' / 'relationship-rules.json').read_text(encoding='utf-8'))['mappings']}


def _list(v):
    return [] if v is None else (v if isinstance(v, list) else [v])


STOP = {'the', 'and', 'of', 'for', 'a', 'an', 'to', 'in', 'on', 'by', 'with', 'from', 'api', 'svc', 'v1', 'v2', 'v3', 'id'}
STRUCTURAL = {'set', 'record', 'item', 'list', 'group', 'type', 'data', 'master', 'detail', 'entry'}  # never gate evidence (C2 finding 3)
HTTP = {'GET', 'POST', 'PUT', 'PATCH', 'DELETE'}
# check 2: action term -> methods that pass. Retrieve -> GET is verified (SAPG §3.5); the rest is the executor convention,
# binding under DEC-E-06. Execute passes on POST only on a sub-resource named for the qualifier (checked in _check2).
METHODS = {'Retrieve': {'GET'}, 'Create': {'POST'}, 'Initiate': {'POST'}, 'Register': {'POST'}, 'Evaluate': {'POST'}, 'Provide': {'POST'}, 'Request': {'POST'},
           'Update': {'PUT', 'PATCH'}, 'Control': {'PUT', 'PATCH', 'DELETE'}, 'Exchange': {'PUT', 'PATCH'}, 'Capture': {'PUT', 'PATCH'}, 'Grant': {'PUT', 'PATCH'},
           'Execute': {'PUT', 'PATCH', 'POST'}, 'Activate': {'PUT', 'POST'}, 'Configure': {'PUT', 'POST'}, 'Feedback': {'PUT', 'POST'}}


def _sing(w):
    if len(w) > 4 and w.endswith('ies'): return w[:-3] + 'y'
    if len(w) > 3 and w.endswith('s') and not w.endswith('ss'): return w[:-1]
    return w


def tokens(*texts, structural=True):
    """Lower-case words: camel- and snake-case split, singularised; stop words (and structural nouns) dropped."""
    out = set()
    for t in texts:
        if not t: continue
        for part in re.findall(r'[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|[0-9]+', str(t)):
            w = _sing(part.lower())
            if w in STOP or (structural and w in STRUCTURAL) or w.isdigit(): continue
            out.add(w)
    return out


def stem(w):
    """Light stem for check 3's 'clear synonym': a qualifier noun and its verb share a stem (closure/close, posting/post,
    reversal/reverse, validation/validate). Engine convention EC-01 (relationship-rules-spec.md DEC-E-07)."""
    for suf in ('ation', 'ition', 'ment', 'ing', 'ure', 'ion', 'al', 'e'):
        if w.endswith(suf) and len(w) - len(suf) >= 4: return w[:-len(suf)]
    return w


def stems(ws):
    return {stem(w) for w in ws}


def norm(name):
    return _sing(re.sub(r'[^a-z0-9]', '', str(name).lower()))


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
        self.wedges = reader.edges('within-level')

    # -- lookups
    def of(self, etype):
        return self.r.nodes(type=etype)

    def get(self, iid, etype=None, level=None):
        """The instance with this id (of this type or a subtype), or None — never invented."""
        for (lvl, i), n in self.ids.items():
            if i == iid and (level is None or lvl == level) and (etype is None or self.mm.is_a(n['type'], etype)):
                return n
        return None

    def parents(self, iid, kind='composition'):
        return [e['source'] for e in self.wedges if e['target'] == iid and e['kind'] == kind]

    def children(self, iid, kind='composition'):
        return [e['target'] for e in self.wedges if e['source'] == iid and e['kind'] == kind]

    def climb(self, iid, etype, level):
        """Nearest composition ancestor (or self) of the given type."""
        seen, todo = set(), [iid]
        while todo:
            x = todo.pop(0)
            if x in seen: continue
            seen.add(x); n = self.get(x, level=level)
            if n and self.mm.is_a(n['type'], etype): return n
            todo += self.parents(x)
        return None

    def descendants(self, iid, kinds=('composition',)):
        seen, todo = [], [iid]
        while todo:
            x = todo.pop(0)
            if x in seen: continue
            seen.append(x); todo += [c for k in kinds for c in self.children(x, k)]
        return seen

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

    # ------------------------------------------------------------ step 2 — BIAN REST decision procedure (S24, S26)
    def _qual(self, name):
        """A behaviour qualifier's tokens: its name and the institution's aliases (A2.BehaviorQualifier.attributes.aliases)."""
        if not name: return set(), None
        bq = next((b for b in self.of('A2.BehaviorQualifier') if b['name'].lower() == str(name).lower()), None)
        return stems(tokens(name, *_list(self.attr(bq, 'aliases') if bq else None))), bq

    @staticmethod
    def _path_segments(path):
        segs = [x for x in str(path or '').split('/') if x and not x.startswith('{')]
        return [stems(tokens(x)) for x in segs]

    def _check2(self, term, method, qual_in_path):
        if term not in METHODS: return 'fail', f'action term {term!r} has no REST form'
        if term == 'Execute' and method == 'POST':
            return ('pass', 'Execute on POST to a sub-resource named for the qualifier') if qual_in_path else ('fail', 'Execute on POST without a qualifier sub-resource')
        return ('pass', f'{term} ↔ {method}') if method in METHODS[term] else ('fail', f'{term} on {method}')

    def _check3(self, op_qual, other_quals, path):
        segs = self._path_segments(path); after = set().union(*segs[1:]) if len(segs) > 1 else set()
        if op_qual:
            return ('pass', 'qualifier in path') if op_qual & after else ('fail', 'qualifier not in path')
        for q in other_quals:
            if q & after: return 'fail', f'path carries another operation\'s qualifier ({sorted(q & after)[0]})'
        return 'neutral', 'no qualifier, none in path'

    def _overlap(self, op, api, aliases):
        want = {norm(a) for a in _list(self.attr(op, 'input_attributes')) + _list(self.attr(op, 'output_attributes'))}
        have = set()
        for f in _list(self.attr(api, 'payload_fields')):
            have.add(norm(f))
            if f in aliases: have.add(norm(aliases[f]))
        m = want & have
        return len(m), (len(m) / len(want) if want else 0.0), sorted(m)

    def step2(self):
        ops = self.of('A2.ServiceOperation'); apis = self.of('A3.APIOperation')
        pairs = []
        for op in ops:
            dom = self.climb(op['id'], 'A2.ServiceDomain', 'A2')
            term = self.attr(op, 'action_term'); qual, _ = self._qual(self.attr(op, 'behavior_qualifier'))
            siblings = [o for o in ops if o['id'] != op['id'] and dom and self.climb(o['id'], 'A2.ServiceDomain', 'A2') == dom]
            other_quals = [q for q in (self._qual(self.attr(o, 'behavior_qualifier'))[0] for o in siblings) if q]
            if dom is None:
                self.attempt('S24', op['id'], None, 2, [f"{op['id']} composition ancestors"], 'operation belongs to no exported Service Domain — no boundary'); continue
            at = self.get(self.attr(dom, 'asset_type'), 'A2.AssetType') if self.attr(dom, 'asset_type') else None
            gate = tokens(at['name'], *_list(self.attr(at, 'aliases'))) if at else set()
            for api in apis:
                comp = self.climb(api['id'], 'A3.ApplicationComponent', 'A3')
                ifc = self.climb(api['id'], 'A3.ApplicationInterface', 'A3')
                method = str(self.attr(api, 'method') or '').upper()
                conn = f"{op['id']} → {api['id']}"
                # precondition — boundary
                comps = {comp['id']} | ({c for c in self.descendants(comp['id'])} if comp else set()) if comp else set()
                anc = [x['id'] for x in [comp] if x]
                realized = comp and any((dom['id'], 'REALIZED_BY', c) in self.approved for c in anc + [p for p in self.parents(comp['id'])])
                if not realized:
                    if not gate:
                        self.log.append({'plan_id': 'S24', 'connection': conn, 'step_assigned': 2, 'step_used': 2, 'fallback': False, 'data_read': [dom['id']],
                                         'reasoning': 'boundary untestable: no approved REALIZED_BY and no asset type/aliases in the export', 'outcome': 'no_proposal', 'proposal_id': None,
                                         'confidence_predicted': 'high', 'confidence_given': None}); continue
                    texts = []
                    for x in (self.descendants(comp['id']) if comp else []):
                        n = self.get(x, level='A3')
                        if not n: continue
                        if self.mm.is_a(n['type'], 'A3.APIOperation'): texts += [n['name'], self.attr(n, 'path'), n.get('description'), self.attr(n, 'operation_id')]
                    for c in (self.descendants(comp['id']) if comp else []):
                        for e in self.children(c, 'access'):
                            de = self.get(e, 'A3.DataEntity', 'A3')
                            if de: texts.append(de['name'])
                    hit = gate & tokens(*texts)
                    if not hit: continue  # outside the boundary: not a candidate pair (not logged per pair; the gate is per component)
                if method not in HTTP:
                    self.attempt('S24', op['id'], api['id'], 2, [f"{api['id']}.method"], f'method {method or "?"} is not HTTP — the BIAN REST mapping does not apply'); continue
                c3, why3 = self._check3(qual, other_quals, self.attr(api, 'path'))
                c2, why2 = self._check2(term, method, c3 == 'pass')
                aliases = (self.attr(ifc, 'field_aliases') or {}) if ifc else {}
                cnt, ratio, matched = self._overlap(op, api, aliases)
                pairs.append({'op': op, 'api': api, 'c2': c2, 'c3': c3, 'cnt': cnt, 'ratio': ratio, 'matched': matched, 'why': f'{why2}; {why3}; payload {cnt} matched ({ratio:.0%}): {matched}',
                              'qual_hit': bool(qual & stems(tokens(self.attr(api, 'path')) | tokens(api['name'])))})
        filed, removed = [], set()
        def live(): return [p for p in pairs if id(p) not in removed]
        def c4(p, pool):
            if p['cnt'] < 2 or p['ratio'] < 0.5: return False
            mine = [q for q in pool if q['op'] is p['op'] and q['cnt'] >= 2 and q['ratio'] >= 0.5]
            best = max((q['cnt'], q['ratio']) for q in mine)
            tops = [q for q in mine if (q['cnt'], q['ratio']) == best]
            if len(tops) > 1:
                tops = [q for q in tops if q['qual_hit']] or tops
            return len(tops) == 1 and tops[0] is p
        def award(cands):
            """Contention for one API between operations: count, then ratio, then the qualifier the path carries; a tie is no proposal."""
            out = []
            by_api = {}
            for p in cands: by_api.setdefault(p['api']['id'], []).append(p)
            for group in by_api.values():
                if len(group) == 1: out.append(group[0]); continue
                group.sort(key=lambda q: (q['cnt'], q['ratio'], q['qual_hit']), reverse=True)
                a, b = group[0], group[1]
                if (a['cnt'], a['ratio'], a['qual_hit']) == (b['cnt'], b['ratio'], b['qual_hit']):
                    for q in group:
                        self.attempt('S24', q['op']['id'], q['api']['id'], 2, [], f"contention tie for {q['api']['id']} between {[g['op']['id'] for g in group]} — no proposal")
                    continue
                out.append(a)
            return out
        def file(p, decision):
            filed.append((p, decision))
            for q in live():
                if q is not p and (q['op'] is p['op'] or q['api'] is p['api']): removed.add(id(q))
            removed.add(id(p))
        while True:
            pool = live()
            d1 = award([p for p in pool if p['c2'] == 'pass' and p['c3'] != 'fail' and c4(p, pool)])
            for p in d1: file(p, 1)
            pool = live()
            d2 = award([p for p in pool if p['c2'] == 'fail' and p['c3'] != 'fail' and c4(p, pool)]) if not d1 else []
            for p in d2: file(p, 2)
            if not d1 and not d2: break
        for p in live():
            self.attempt('S24', p['op']['id'], p['api']['id'], 2, [f"{p['op']['id']}.action_term/qualifier/attributes", f"{p['api']['id']}.method/path/payload_fields"], f"no decision: {p['why']}")
        for p, decision in filed:
            working = f"decision {decision}: {p['why']}" + ('' if decision == 1 else ' — method mismatch, proposed one band lower')
            rec = self.propose('S24', 'IMPLEMENTED_BY', p['op'], p['api'], 2, working, [f"{p['op']['id']}.action_term/behavior_qualifier/input_attributes/output_attributes", f"{p['api']['id']}.method/path/payload_fields"], fallback=decision == 2)
            if rec and p['c3'] == 'pass':
                _, bq = self._qual(self.attr(p['op'], 'behavior_qualifier'))
                if bq: self.report('S26', bq, p['api'], 2, f"qualifier {bq['name']} in path of {p['api']['id']}, which implements {p['op']['id']} ({rec['mapping_id']})", [f"{p['api']['id']}.path"])

    def run(self):
        self.step1()
        self.step2()
        return {'proposals': self.proposals, 'candidates': self.candidates, 'log': self.log}


ENGINE_NAME = 'sdem-rules/0.10'


class RulesEngine:
    name = ENGINE_NAME

    def infer(self, reader, case=None):
        return Run(reader, (case or {}).get('id', 'RUN')).run()
