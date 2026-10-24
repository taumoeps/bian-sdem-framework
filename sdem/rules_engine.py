"""The rule-based Architecture Relationship Inference Engine (relationship-rules-spec.md; procedure docs/mapping-execution.md).

Reads a graph through the graph access layer (sdem/store.py GraphReader), applies the Relationship Rules Model
(metamodel/relationship-rules.json) in fill-step order, and returns:
  proposals  — catalogue-typed records (the nine relationship types), status `proposed`, for sdem-validate and an architect
  candidates — reports for candidate, conditional, institution-only and derived-path rows, `relationship` = the plan ID
  log        — one record per attempt, including refusals (the evidence base; REQ-O-02)
It never approves, never invents an instance, and never re-proposes a link that is already approved.

Built step by step against the acceptance harness (sdem/acceptance.py). Implemented: steps 1–5 (data joins; BIAN REST decision procedure; structural matching; derivation; bounded text inference). Design mode (M2) is not built.
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

    # ------------------------------------------------------------ shared: links known so far (approved, or proposed in this run)
    def links(self, rel):
        """(source id, target id, label) for a catalogue relationship: approved arrows and this run's proposals, labelled which."""
        out = [(a, b, 'approved') for a, r, b in self.approved if r == rel]
        out += [(k[0], k[2], self.proposed[k]['mapping_id']) for k in self.proposed if k[1] == rel]
        return out

    def band_of(self, label):
        """Confidence band of an input arrow: approved counts as high; a proposal carries its own."""
        if label == 'approved': return 'high'
        rec = next(r for r in self.proposals if r['mapping_id'] == label)
        return {0.8: 'high', 0.6: 'medium', 0.4: 'low'}[rec['confidence']]

    def reports(self, plan_id):
        return [(k[0], k[2], v['mapping_id']) for k, v in self.reported.items() if k[1] == plan_id]

    def domain_of(self, op_id):
        return self.climb(op_id, 'A2.ServiceDomain', 'A2')

    def component_of(self, a3_id):
        return self.climb(a3_id, 'A3.ApplicationComponent', 'A3')

    def entity_aliases(self, de):
        """field_aliases a data entity carries: inherited from every interface of a component that accesses it; its own take precedence."""
        al = {}
        for e in self.wedges:
            if e['kind'] == 'access' and e['target'] == de['id']:
                comp = self.get(e['source'], 'A3.ApplicationComponent', 'A3')
                for x in (self.descendants(comp['id']) if comp else []):
                    ifc = self.get(x, 'A3.ApplicationInterface', 'A3')
                    if ifc: al.update(self.attr(ifc, 'field_aliases') or {})
        al.update(self.attr(de, 'field_aliases') or {})
        return al

    def one_to_one(self, plan_id, scored, file):
        """File the highest-scoring pair, drop pairs sharing either end, repeat; a tie at the top is no proposal (both named)."""
        pool = [x for x in scored]
        while pool:
            top = max(x[0] for x in pool)
            best = [x for x in pool if x[0] == top]
            tied = [x for x in best if any(y is not x and (y[1]['id'] == x[1]['id'] or y[2]['id'] == x[2]['id']) for y in best)]
            for x in tied:
                self.attempt(plan_id, x[1]['id'], x[2]['id'], 4, x[4], f'tie at score {top:.2f} with another pair sharing an end — no proposal')
            filed = [x for x in best if x not in tied]
            if not filed:
                pool = [x for x in pool if x not in best]; continue
            for x in filed: file(x)
            ends = {e for x in filed + tied for e in (('s', x[1]['id']), ('t', x[2]['id']))}
            pool = [x for x in pool if ('s', x[1]['id']) not in ends and ('t', x[2]['id']) not in ends]

    # ------------------------------------------------------------ step 4 — structural matching
    VERB = {'initiate': {'initiate', 'create', 'capture', 'apply', 'submit', 'open', 'request', 'register'}, 'create': {'create', 'initiate', 'capture', 'apply', 'submit', 'open'},
            'register': {'register', 'create', 'capture'}, 'evaluate': {'evaluate', 'validate', 'check', 'assess', 'screen', 'score', 'review', 'examine'},
            'execute': {'execute', 'issue', 'release', 'settle', 'pay', 'run'}, 'retrieve': {'retrieve', 'confirm', 'get', 'view', 'query', 'track'},
            'notify': {'notify', 'confirm', 'alert', 'inform'}, 'update': {'update', 'amend', 'change', 'modify'}, 'control': {'control', 'block', 'suspend', 'cancel', 'close'},
            'request': {'request', 'ask', 'order'}, 'provide': {'provide', 'supply', 'deliver'}, 'exchange': {'exchange', 'accept', 'reject'},
            'capture': {'capture', 'record', 'enter'}, 'grant': {'grant', 'approve', 'authorise', 'authorize'}}

    def verbs(self, term):
        t = str(term or '').lower(); return stems(self.VERB.get(t, {t}))

    def attr_match(self, want, have, aliases=None):
        w = {norm(a) for a in want}; h = set()
        for f in have:
            h.add(norm(f))
            if aliases and f in aliases: h.add(norm(aliases[f]))
        return w & h

    def step4(self):
        # S30 MAPPED_TO (BOM object -> data entity) and S20 (control record -> data entity): >= 50 % of the BIAN object's attributes, one-to-one
        des = self.of('A3.DataEntity')
        for plan, stype in (('S30', 'A2.BusinessObject'), ('S20', 'A2.ControlRecord')):
            scored = []
            for b in self.of(stype):
                want = _list(self.attr(b, 'attributes'))
                if not want: continue
                for de in des:
                    m = self.attr_match(want, _list(self.attr(de, 'attributes')), self.entity_aliases(de))
                    sc = len(m) / len(want)
                    if sc >= 0.5: scored.append((sc, b, de, sorted(m), [f"{b['id']}.attributes", f"{de['id']}.attributes"]))
            if plan == 'S30':
                self.one_to_one(plan, scored, lambda x: self.propose('S30', 'MAPPED_TO', x[1], x[2], 4, f"{len(x[3])}/{len(_list(self.attr(x[1], 'attributes')))} BOM attributes matched ({x[0]:.0%}): {x[3]}", x[4]))
            else:
                self.one_to_one(plan, scored, lambda x: self.report('S20', x[1], x[2], 4, f"{len(x[3])}/{len(_list(self.attr(x[1], 'attributes')))} control-record attributes matched ({x[0]:.0%})", x[4]))
        # S31: attributes of a mapped BOM object found in the data entity
        for b_id, de_id, lab in self.links('MAPPED_TO'):
            b = self.get(b_id, 'A2.BusinessObject'); de = self.get(de_id, 'A3.DataEntity')
            if not (b and de): continue
            have = self.attr_match([x['name'] for x in (self.get(c, 'A2.BusinessObjectAttribute') for c in self.children(b_id)) if x], _list(self.attr(de, 'attributes')), self.entity_aliases(de))
            for c in self.children(b_id):
                boa = self.get(c, 'A2.BusinessObjectAttribute')
                if boa and norm(boa['name']) in have:
                    self.report('S31', boa, de, 4, f"attribute {boa['name']} of {b_id} is in {de_id} (MAPPED_TO {lab})", [f"{de_id}.attributes"])
        # S12 ALIGNED_TO (bank glossary object -> BOM object): glossary attributes through the bank's aliases, one-to-one
        scored = []
        for a in self.of('A1.BusinessObject'):
            have = _list(self.attr(a, 'attributes')); al = self.attr(a, 'field_aliases') or {}
            for b in self.of('A2.BusinessObject'):
                want = _list(self.attr(b, 'attributes'))
                if not want or not have: continue
                m = self.attr_match(want, have, al); sc = len(m) / len(want)
                if sc >= 0.5: scored.append((sc, a, b, sorted(m), [f"{a['id']}.attributes/field_aliases", f"{b['id']}.attributes"]))
        self.one_to_one('S12', scored, lambda x: self.propose('S12', 'ALIGNED_TO', x[1], x[2], 4, f"{len(x[3])}/{len(_list(self.attr(x[2], 'attributes')))} BOM attributes covered by the glossary ({x[0]:.0%})", x[4]))
        # S02 ALIGNED_TO (value stream -> scenario): coverage of the scenario's operations, in order, by stage action verbs (>= 60 %)
        for vs in self.of('A1.ValueStream'):
            stages = [self.get(x, 'A1.ValueStreamStage') for x in _list(self.attr(vs, 'stages'))]
            stages = [x for x in stages if x]
            for sc_ in self.of('A2.BusinessScenario'):
                ops = [self.get(x, 'A2.ServiceOperation') for x in _list(self.attr(sc_, 'operation_sequence'))]
                ops = [o for o in ops if o]
                if not ops or not stages: continue
                i, hits = 0, []
                for o in ops:
                    v = self.verbs(self.attr(o, 'action_term'))
                    for j in range(i, len(stages)):
                        if v & stems(tokens(stages[j]['name'])):
                            hits.append((o['id'], stages[j]['id'])); i = j + 1; break
                cov = len(hits) / len(ops)
                data = [f"{vs['id']}.stages", f"{sc_['id']}.operation_sequence"]
                if cov >= 0.6:
                    self.propose('S02', 'ALIGNED_TO', vs, sc_, 4, f"{len(hits)}/{len(ops)} scenario operations covered in order by stage verbs ({cov:.0%}): {hits}", data)
                    for _, st in hits:
                        self.report('S03', self.get(st, 'A1.ValueStreamStage'), sc_, 4, f"stage {st} matches an operation of {sc_['id']} (S02 for {vs['id']})", data)
                else:
                    self.attempt('S02', vs['id'], sc_['id'], 4, data, f'coverage {cov:.0%} < 60 %')
        # S06 (activity -> operation) by verb + noun when the activity names no operation
        for act in self.of('A1.BusinessActivity'):
            if _list(self.attr(act, 'invokes')): continue
            at = stems(tokens(act['name']))
            for o in self.of('A2.ServiceOperation'):
                dom = self.domain_of(o['id']); asset = self.get(self.attr(dom, 'asset_type'), 'A2.AssetType') if dom and self.attr(dom, 'asset_type') else None
                noun = stems(tokens(asset['name'], *_list(self.attr(asset, 'aliases')))) if asset else set()
                if self.verbs(self.attr(o, 'action_term')) & at and noun & at:
                    self.report('S06', act, o, 4, f"verb and noun match: '{act['name']}' ~ '{o['name']}'", [f"{act['id']}.name", f"{o['id']}.action_term", 'asset type'])
        # S09 (business service -> operation): inputs/outputs vs operation attributes, >= 50 % and >= 2, unique best per service
        for bs in self.of('A1.BusinessService'):
            have = _list(self.attr(bs, 'inputs')) + _list(self.attr(bs, 'outputs'))
            if not have: continue
            sc = []
            for o in self.of('A2.ServiceOperation'):
                want = _list(self.attr(o, 'input_attributes')) + _list(self.attr(o, 'output_attributes'))
                m = self.attr_match(want, have)
                if want and len(m) >= 2 and len(m) / len(want) >= 0.5: sc.append((len(m), len(m) / len(want), o, sorted(m)))
            if sc:
                top = max(x[:2] for x in sc); best = [x for x in sc if x[:2] == top]
                if len(best) == 1:
                    self.report('S09', bs, best[0][2], 4, f"{best[0][0]} attributes matched ({best[0][1]:.0%}): {best[0][3]}", [f"{bs['id']}.inputs/outputs"])
                else:
                    self.attempt('S09', bs['id'], None, 4, [], f"tie between {[x[2]['id'] for x in best]} — no report")
        # S19 (asset type -> data entity) and S27 (qualifier -> data entity): a name or alias token in the entity name
        for plan, stype, src in (('S19', 'A2.AssetType', lambda x: tokens(*_list(self.attr(x, 'aliases')))), ('S27', 'A2.BehaviorQualifier', lambda x: tokens(*_list(self.attr(x, 'aliases'))))):
            for a in self.of(stype):
                toks = stems(src(a))
                for de in des:
                    hit = toks & stems(tokens(de['name']))
                    if hit: self.report(plan, a, de, 4, f"{sorted(hit)} of {a['id']} in entity name '{de['name']}'", [f"{a['id']}.aliases", f"{de['id']}.name"])

    # ------------------------------------------------------------ step 3 — derivation over approved arrows and this run's proposals
    def step3(self):
        impl = self.links('IMPLEMENTED_BY')
        # S17 REALIZED_BY: a component exposing APIs that implement a domain's operations realises the domain (cap: strongest input, DEC-E-02)
        real = {}
        for op_id, api_id, lab in impl:
            dom = self.domain_of(op_id); comp = self.component_of(api_id)
            if dom and comp: real.setdefault((dom['id'], comp['id']), []).append((op_id, api_id, lab))
        for (d, c), via in real.items():
            band = max((self.band_of(l) for _, _, l in via), key=lambda b: BAND[b])
            self.propose('S17', 'REALIZED_BY', self.get(d, 'A2.ServiceDomain'), self.get(c, 'A3.ApplicationComponent'), 3,
                         'implements ' + '; '.join(f'{o} via {a} ({l})' for o, a, l in via), [f'IMPLEMENTED_BY {l}' for _, _, l in via], band=band)
        done = {d for d, _ in real}
        # fallback A: the component accesses a data entity MAPPED_TO the business object of the domain's control record
        mapped = self.links('MAPPED_TO')
        for dom in self.of('A2.ServiceDomain'):
            if dom['id'] in done: continue
            crs = [x for x in self.children(dom['id'], 'aggregation') if self.get(x, 'A2.ControlRecord')]
            bos = {e['target'] for e in self.wedges if e['source'] in crs and self.get(e['target'], 'A2.BusinessObject')} | {e['source'] for e in self.wedges if e['target'] in crs and self.get(e['source'], 'A2.BusinessObject')}
            found = {}
            for b, de, lab in mapped:
                if b not in bos: continue
                for e in self.wedges:
                    if e['kind'] == 'access' and e['target'] == de:
                        comp = self.component_of(e['source'])
                        if comp: found.setdefault(comp['id'], []).append((b, de, lab))
            for c, via in found.items():
                band = max((self.band_of(l) for _, _, l in via), key=lambda b: BAND[b])
                self.propose('S17', 'REALIZED_BY', dom, self.get(c, 'A3.ApplicationComponent'), 3, 'fallback A (information perspective): ' + '; '.join(f'accesses {de}, MAPPED_TO {b} ({l})' for b, de, l in via),
                             [f'MAPPED_TO {l}' for _, _, l in via], band=band)
                done.add(dom['id'])
        # fallback B (step 4, one band lower): an asset-type token in the component's API paths or data entity names
        for dom in self.of('A2.ServiceDomain'):
            if dom['id'] in done: continue
            at = self.get(self.attr(dom, 'asset_type'), 'A2.AssetType') if self.attr(dom, 'asset_type') else None
            if not at: self.attempt('S17', dom['id'], None, 3, [], 'no implemented operation, no mapped object, no asset type — no proposal'); continue
            toks = stems(tokens(at['name'], *_list(self.attr(at, 'aliases'))))
            for comp in self.of('A3.ApplicationComponent'):
                # DEC-E-08: a token shared with the asset type of a domain this component (or one containing it) already realises explains nothing new
                lineage = {comp['id']} | set(self.parents(comp['id']))
                explained = set()
                for dd, cc, _ in self.links('REALIZED_BY'):
                    if cc in lineage and dd != dom['id']:
                        a2 = self.get(self.attr(self.get(dd, 'A2.ServiceDomain'), 'asset_type'), 'A2.AssetType')
                        if a2: explained |= stems(tokens(a2['name'], *_list(self.attr(a2, 'aliases'))))
                texts = []
                for x in self.descendants(comp['id']):
                    n = self.get(x, 'A3.APIOperation', 'A3')
                    if n: texts.append(self.attr(n, 'path'))
                for x in self.descendants(comp['id']):
                    for e in self.children(x, 'access'):
                        de = self.get(e, 'A3.DataEntity', 'A3')
                        if de: texts.append(de['name'])
                hit = (toks - explained) & stems(tokens(*texts))
                if hit: self.propose('S17', 'REALIZED_BY', dom, comp, 4, f'fallback B: asset-type tokens {sorted(hit)} in API paths / entity names', [f"{comp['id']} API paths, data entities"], fallback=True)
        # S04 USES_DOMAIN: a process (or one of its activities) invokes an operation of the domain, or an S06 report links its activity
        for prc in self.of('A1.BusinessProcess'):
            if self.mm.is_a(prc['type'], 'A1.BusinessActivity'): continue
            acts = [a for a in self.children(prc['id']) if self.get(a, 'A1.BusinessActivity')]
            ops = {o: f"{prc['id']}.invokes" for o in _list(self.attr(prc, 'invokes'))}
            for a in acts:
                for o in _list(self.attr(self.get(a, 'A1.BusinessActivity'), 'invokes')): ops.setdefault(o, f'{a}.invokes')
                for s_, o, lab in self.reports('S06'):
                    if s_ == a: ops.setdefault(o, f'S06 {lab}')
            doms = {}
            for o, why in ops.items():
                d = self.domain_of(o)
                if d: doms.setdefault(d['id'], []).append(f'{o} ({why})')
            for d, why in doms.items():
                self.propose('S04', 'USES_DOMAIN', prc, self.get(d, 'A2.ServiceDomain'), 3, 'invokes ' + '; '.join(why), why)
        # S01 SUPPORTED_BY: every process of the capability uses the domain (medium); only some (low)
        for cap in self.of('A1.BusinessCapability'):
            prcs = [e['source'] for e in self.wedges if e['kind'] == 'realization' and e['target'] == cap['id'] and self.get(e['source'], 'A1.BusinessProcess') and not self.get(e['source'], 'A1.BusinessActivity')]
            if not prcs: continue
            uses = {}
            for p_, d, lab in self.links('USES_DOMAIN'):
                if p_ in prcs: uses.setdefault(d, set()).add(p_)
            for d, ps in uses.items():
                if len(ps) == len(prcs):
                    self.propose('S01', 'SUPPORTED_BY', cap, self.get(d, 'A2.ServiceDomain'), 3, f"all {len(prcs)} processes of the capability use the domain", sorted(ps))
                else:  # DEC-E-09: partial coverage is not evidence enough for a registry arrow
                    self.attempt('S01', cap['id'], d, 3, sorted(ps), f'only {len(ps)} of {len(prcs)} processes use the domain — no proposal (DEC-E-09)')
        # candidate derivations (reported, never registry records)
        for a, o, lab in self.reports('S06'):
            d = self.domain_of(o)
            if d: self.report('S07', self.get(a, 'A1.BusinessActivity'), d, 3, f'S06 {lab}: {a} → {o}, in {d["id"]}', [lab])
        for req in self.of('A1.BusinessRequirement'):
            for t in _list(self.attr(req, 'applies_to')):
                tn = self.get(t, level='A1')
                if not tn: continue
                if self.mm.is_a(tn['type'], 'A1.BusinessActivity'):
                    ops = [o for s_, o, _ in self.reports('S06') if s_ == t] + _list(self.attr(tn, 'invokes'))
                    for o in dict.fromkeys(ops):
                        on = self.get(o, 'A2.ServiceOperation'); d = self.domain_of(o)
                        if on: self.report('S14', req, on, 3, f'applies to activity {t}, which invokes {o}', [f"{req['id']}.applies_to"])
                        if d: self.report('S13', req, d, 3, f'applies to activity {t}, whose operation {o} is in {d["id"]}', [f"{req['id']}.applies_to"])
                else:
                    for p_, d, lab in self.links('USES_DOMAIN'):
                        if p_ == t: self.report('S13', req, self.get(d, 'A2.ServiceDomain'), 3, f'applies to {t}, which USES_DOMAIN {d} ({lab})', [f"{req['id']}.applies_to"])
        for d, c, lab in self.links('REALIZED_BY'):
            comp = self.get(c, 'A3.ApplicationComponent')
            bd = [p_ for p_ in self.parents(d) if self.get(p_, 'A2.BusinessDomain')]
            for b in bd:
                self.report('S16', self.get(b, 'A2.BusinessDomain'), comp, 3, f'{b} composes {d}, REALIZED_BY {c} ({lab})', [lab])
                for a in self.parents(b):
                    if self.get(a, 'A2.BusinessArea'): self.report('S15', self.get(a, 'A2.BusinessArea'), comp, 3, f'{a} composes {b} composes {d}, REALIZED_BY {c} ({lab})', [lab])
        for op_id, api_id, lab in impl:
            op = self.get(op_id, 'A2.ServiceOperation'); ifc = self.climb(api_id, 'A3.ApplicationInterface', 'A3')
            svcs = [self.get(e['target'], 'A3.ApplicationService') for e in self.wedges if ifc and e['kind'] == 'assignment' and e['source'] == ifc['id']]
            for sv in [x for x in svcs if x]:
                self.report('S25', op, sv, 3, f'{op_id} IMPLEMENTED_BY {api_id} ({lab}); {ifc["id"]} composes it and is assigned to {sv["id"]}', [lab])
            for sg in [p_ for p_ in self.parents(op_id) if self.get(p_, 'A2.ServiceGroup')]:
                for sv in [x for x in svcs if x]: self.report('S22', self.get(sg, 'A2.ServiceGroup'), sv, 3, f'{sg} contains {op_id}, IMPLEMENTED_BY {api_id} exposed through {ifc["id"]} → {sv["id"]}', [lab])
                if ifc: self.report('S23', self.get(sg, 'A2.ServiceGroup'), ifc, 3, f'{sg} contains {op_id}, IMPLEMENTED_BY {api_id} in {ifc["id"]}', [lab])
            for fn in self.of('A3.ApplicationFunction'):
                if api_id in _list(self.attr(fn, 'exposed_through')):
                    d = self.domain_of(op_id)
                    fp = self.get(self.attr(d, 'functional_pattern'), 'A2.FunctionalPattern') if d and self.attr(d, 'functional_pattern') else None
                    if fp: self.report('S18', fp, fn, 3, f'{fn["id"]} exposed through {api_id}, which implements {op_id} of {d["id"]} (pattern {fp["id"]})', [lab])
                    for cr in self.children(op_id, 'access'):
                        crn = self.get(cr, 'A2.ControlRecord')
                        if crn: self.report('S21', crn, fn, 3, f'{fn["id"]} exposed through {api_id}; {op_id} accesses {cr}', [lab])
        for sc_ in self.of('A2.BusinessScenario'):
            for o in _list(self.attr(sc_, 'operation_sequence')):
                for s_, sv, lab in self.reports('S25'):
                    if s_ == o: self.report('S28', sc_, self.get(sv, 'A3.ApplicationService'), 3, f'{o} in the sequence → {sv} (S25 {lab})', [lab])
                d = self.domain_of(o)
                for dd, c, lab in self.links('REALIZED_BY'):
                    if d and dd == d['id']: self.report('S29', sc_, self.get(c, 'A3.ApplicationComponent'), 3, f'{o} in the sequence is in {dd}, REALIZED_BY {c} ({lab})', [lab])
        # technology derived paths (C3)
        dep_as = self.links('DEPLOYED_AS'); dep_on = self.links('DEPLOYED_ON')
        for c, d, lab in dep_as:
            dn = self.get(d, 'A4.Deployment'); env = self.get(self.attr(dn, 'environment_id'), 'A4.DeploymentEnvironment') if dn and self.attr(dn, 'environment_id') else None
            if env: self.report('S40', self.get(c, 'A3.ApplicationComponent'), env, 3, f'DEPLOYED_AS {d} ({lab}) in environment {env["id"]}', [lab])
            for x in self.descendants(c):
                api = self.get(x, 'A3.APIOperation', 'A3')
                if api: self.report('S47', api, dn, 3, f'{c} composes … {x}; {c} DEPLOYED_AS {d} ({lab})', [lab])
        for c, t, lab in dep_on:
            tn = self.get(t, 'A4.InfrastructureComponent', 'A4')
            if tn and self.mm.is_a(tn['type'], 'A4.SystemSoftware'):
                for f in self.children(c, 'assignment'):
                    fn = self.get(f, 'A3.ApplicationFunction')
                    if fn: self.report('S46', fn, tn, 3, f'{c} is assigned {f} and is DEPLOYED_ON {t} ({lab})', [lab])
        for ai, ti, lab in self.reports('S43'):
            tin = self.get(ti, 'A4.TechnologyInterface'); ts = self.get(self.attr(tin, 'of_service'), 'A4.TechnologyService') if tin and self.attr(tin, 'of_service') else None
            if ts: self.report('S44', self.get(ai, 'A3.ApplicationInterface'), ts, 3, f'S43 {lab}: {ai} → {ti}, interface of {ts["id"]}', [lab])
            for e in self.wedges:
                if e['kind'] == 'assignment' and e['source'] == ai and self.get(e['target'], 'A3.ApplicationService'):
                    self.report('S42', self.get(e['target'], 'A3.ApplicationService'), tin, 3, f'{e["target"]} is exposed through {ai}, which is exposed through {ti} (S43 {lab})', [lab])
            for x in self.children(ai):
                api = self.get(x, 'A3.APIOperation', 'A3')
                if api: self.report('S48', api, tin, 3, f'{ai} composes {x}; {ai} exposed through {ti} (S43 {lab})', [lab])
        for sbb in self.of('A3.SolutionBuildingBlock'):
            comps = _list(self.attr(sbb, 'components'))
            for c, t, lab in dep_on:
                if c in comps:
                    tn = self.get(t, 'A4.InfrastructureComponent', 'A4')
                    self.report('S52', sbb, tn, 3, f'component {c} of the block is DEPLOYED_ON {t} ({lab})', [lab])
                    if tn and self.mm.is_a(tn['type'], 'A4.Node'): self.report('S54', sbb, tn, 3, f'component {c} of the block is DEPLOYED_ON node {t} ({lab})', [lab])
            for c, d, lab in dep_as:
                if c in comps: self.report('S53', sbb, self.get(d, 'A4.Deployment'), 3, f'component {c} of the block is DEPLOYED_AS {d} ({lab})', [lab])

    # ------------------------------------------------------------ step 5 — bounded text inference (S01 when step 3 found nothing; S08 on opt-in)
    GENERIC = {'bank', 'customer', 'manage', 'management', 'account', 'service', 'process', 'record', 'data'}

    def concepts(self, *texts):
        return stems({w for w in tokens(*texts) if w not in self.GENERIC and len(w) > 2})

    def rank(self, plan, src, text, rel=None):
        doms = self.of('A2.ServiceDomain')
        if len(doms) < 2:
            self.attempt(plan, src['id'], None, 5, [], 'single-candidate — no proposal'); return
        def dtext(d):
            at = self.get(self.attr(d, 'asset_type'), 'A2.AssetType') if self.attr(d, 'asset_type') else None
            return self.concepts(d['name'], d.get('description'), at['name'] if at else None, *_list(self.attr(at, 'aliases') if at else None))
        mine = self.concepts(text)
        sc = sorted(((len(mine & dtext(d)), d) for d in doms), key=lambda x: -x[0])
        best, runner = sc[0], (sc[1][0] if len(sc) > 1 else 0)
        working = f"shares {sorted(mine & dtext(best[1]))} with {best[1]['id']}; runner-up shares {runner}"
        if best[0] >= 2 and best[0] - runner >= 1:
            if rel: self.propose(plan, rel, src, best[1], 5, working, ['descriptions'], band='low')
            else: self.report(plan, src, best[1], 5, working, ['descriptions'], band='low')
        else:
            self.attempt(plan, src['id'], best[1]['id'], 5, ['descriptions'], f'{working} — below threshold, no proposal')

    def step5(self, options):
        supported = {k[0] for k in self.proposed if k[1] == 'SUPPORTED_BY'} | {a for a, r, _ in self.approved if r == 'SUPPORTED_BY'}
        for cap in self.of('A1.BusinessCapability'):
            prcs = [e for e in self.wedges if e['kind'] == 'realization' and e['target'] == cap['id']]
            if cap['id'] in supported or prcs: continue  # step 5 only for a capability with no mapped processes
            kids = [c for c in self.children(cap['id']) if self.get(c, 'A1.BusinessCapability')]
            if kids:  # a parent's scope covered by a child's domain is a judgement, not a derivation (M0 run 2): report-only
                self.attempt('S01', cap['id'], None, 5, [f"{cap['id']} composes {kids}"], 'parent capability — report-only, never proposed (M0 run 2)'); continue
            self.rank('S01', cap, f"{cap['name']} {cap.get('description') or ''}", 'SUPPORTED_BY')
        if options.get('S08'):
            for bs in self.of('A1.BusinessService'):
                self.rank('S08', bs, f"{bs['name']} {bs.get('description') or ''}")

    def run(self, options=None):
        self.step1()
        self.step2()
        self.step4()
        self.step3()
        self.step5(options or {})
        return {'proposals': self.proposals, 'candidates': self.candidates, 'log': self.log}


ENGINE_NAME = 'sdem-rules/0.10'


class RulesEngine:
    name = ENGINE_NAME

    def infer(self, reader, case=None):
        return Run(reader, (case or {}).get('id', 'RUN')).run((case or {}).get('options'))
