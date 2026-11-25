"""The rule-based Architecture Relationship Inference Engine (relationship-rules-spec.md; procedure docs/design/mapping-execution.md).

Reads a graph through the graph access layer (sdem/store.py GraphReader), applies the Relationship Rules Model
(metamodel/relationship-rules.json) in fill-step order, and returns:
  proposals  — catalogue-typed records (the registry's relationship types), status `proposed`, for sdem validate and an architect
  candidates — reports for candidate, conditional, institution-only and derived-path rows, `relationship` = the plan ID
  log        — one record per attempt, including refusals (the evidence base; REQ-O-02)
It never approves, never invents an instance, and never re-proposes a link that is already approved.

Built step by step against the acceptance harness (sdem/acceptance.py). Implemented: steps 1–5 (data joins; BIAN REST decision procedure; structural matching; derivation; bounded text inference). Design mode: a target design from BIAN's container pattern when no A3 architecture dataset exists (M2).
"""
from .identity import load as _jload  # DL-11: a design's files read through one boundary (docs/design/sdem-data-layer-spec.md)
from .identity import T as _T, layer as _L  # ST-01…ST-05: layers and types by id (docs/design/sdem-stable-identity-spec.md)
import collections, functools, json, re
from pathlib import Path

from .paths import DATA_ROOT

BAND = {'high': 0.8, 'medium': 0.6, 'low': 0.4}
DOCUMENT_SOURCES = ('confluence:',)  # entities transformed from a document by sdem transform: links touching them are capped at low (DEC-E-11)
LOWER = {'high': 'medium', 'medium': 'low', 'low': 'low'}
EVIDENCE_CLASSES = ('attribute_join', 'structural', 'pattern', 'name_token', 'text')   # strongest first (D3, AID-E01)
WEAK_CLASSES = ('name_token', 'text')                                                    # a name or a description, nothing more
NAME_RULES = ('S02', 'S06', 'S07', 'S19', 'S27')                                         # rules that match words in names


def strongest(*classes):
    """The strongest of several evidence classes (a link proposed for more than one reason)."""
    have = [c for c in classes if c in EVIDENCE_CLASSES]
    return min(have, key=EVIDENCE_CLASSES.index) if have else None


def weakest(*classes):
    """The weakest of several evidence classes (a link derived from several others is no stronger than the weakest of them)."""
    have = [c for c in classes if c in EVIDENCE_CLASSES]
    return max(have, key=EVIDENCE_CLASSES.index) if have else None


def _rules():
    from . import parts   # BX-02: inference rules that name an A2 type belong to ext:bian
    ms = _jload(DATA_ROOT / 'metamodel' / 'relationship-rules.json')['mappings']
    ms = parts.splice(ms, parts.bian_rule, lambda m: m['id'], 'rules')   # BP-02: the installed sdem-bian's, if any
    if not parts.bian_on(): ms = [m for m in ms if (_L('bian') + '.') not in json.dumps(m)]
    return {m['id']: m for m in ms}


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


@functools.lru_cache(maxsize=None)   # pure functions of their text: remembered (the engine reads the same names many times)
def _sing(w):
    if len(w) > 4 and w.endswith('ies'): return w[:-3] + 'y'
    if len(w) > 3 and w.endswith('s') and not w.endswith('ss'): return w[:-1]
    return w


def tokens(*texts, structural=True):
    """Lower-case words: camel- and snake-case split, singularised; stop words (and structural nouns) dropped."""
    return set(_tokens(tuple(str(t) if t else '' for t in texts), structural))


_WORDS = re.compile(r'[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|[0-9]+')


@functools.lru_cache(maxsize=None)
def _tokens(texts, structural):
    out = set()
    for t in texts:
        if not t: continue
        for part in _WORDS.findall(t):
            w = _sing(part.lower())
            if w in STOP or (structural and w in STRUCTURAL) or w.isdigit(): continue
            out.add(w)
    return frozenset(out)


@functools.lru_cache(maxsize=None)
def stem(w):
    """Light stem for check 3's 'clear synonym': a qualifier noun and its verb share a stem (closure/close, posting/post,
    reversal/reverse, validation/validate). Engine convention EC-01 (relationship-rules-spec.md DEC-E-07)."""
    for suf in ('ation', 'ition', 'ment', 'ing', 'ure', 'ion', 'al', 'e'):
        if w.endswith(suf) and len(w) - len(suf) >= 4: return w[:-len(suf)]
    return w


def stems(ws):
    return {stem(w) for w in ws}


@functools.lru_cache(maxsize=None)
def _norm(name):
    return _sing(re.sub(r'[^a-z0-9]', '', name.lower()))


def norm(name):
    return _norm(str(name))


class CoreRun:   # 0.22 step 3b: the engine and the core's rules; BIAN's steps are rules_bian.BianSteps
    """One inference run over one graph: the state every step reads and writes."""

    def __init__(self, reader, uc):
        self.r, self.mm, self.uc = reader, reader.mm, uc
        self.rules = _rules()
        self.rules['DESIGN'] = {'fill_step': 'design', 'confidence': 'low'}
        self.proposals, self.candidates, self.log = [], [], []
        self.approved_order = list(dict.fromkeys((e['source']['id'], e['relationship'], e['target']['id']) for e in reader.fg.edges()))   # registry order: output is the same on every run
        self.approved = set(self.approved_order)   # membership only — never iterated (set order varies between runs)
        self.rejected = {(e['source']['id'], e['relationship'], e['target']['id']) for e in reader.fg.edges(statuses=('rejected',))} - self.approved   # RJ-03: a person said no (RJ-05: unless approved since)
        self.left_out_rejected = set()
        self.proposed = {}   # (src, rel, tgt) -> proposal record (this run)
        self.reported = {}   # (src, plan id, tgt) -> candidate record (this run)
        self.ids = {}        # (level, id) -> node, latest version
        for n in reader.nodes(): self.ids[(n['level'], n['id'])] = n
        self.wedges = reader.edges('within-level')
        # indexes — the same answers as scanning, in the same order, without scanning (scaling: thousands of records)
        self.by_id = {}
        for (lvl, i), n in self.ids.items(): self.by_id.setdefault(i, []).append((lvl, n))
        self._out, self._in = {}, {}
        for e in self.wedges:
            self._out.setdefault((e['source'], e['kind']), []).append(e['target'])
            self._in.setdefault((e['target'], e['kind']), []).append(e['source'])
        self._climb, self._desc, self._bound = {}, {}, {}
        self._of, self._aliases = {}, {}
        self._approved_by_rel, self._proposed_by_rel, self._reported_by_plan, self._by_mapping_id = {}, {}, {}, {}
        for a, r, b in self.approved_order: self._approved_by_rel.setdefault(r, []).append((a, b, 'approved'))
        # links by end, numbered in links() order (approved in registry order, then proposals as made) — kept live as proposals are made
        self._lix, self._rix, self._seq = {}, {}, 0
        for a, r, b in self.approved_order: self._index_link(r, a, b, 'approved')

    # -- lookups
    def of(self, etype):
        if etype not in self._of: self._of[etype] = self.r.nodes(type=etype)
        return list(self._of[etype])

    def get(self, iid, etype=None, level=None):
        """The instance with this id (of this type or a subtype), or None — never invented."""
        for lvl, n in self.by_id.get(iid, ()):
            if (level is None or lvl == level) and (etype is None or self.mm.is_a(n['type'], etype)):
                return n
        return None

    def parents(self, iid, kind='composition'):
        return list(self._in.get((iid, kind), ()))

    def children(self, iid, kind='composition'):
        return list(self._out.get((iid, kind), ()))

    def climb(self, iid, etype, level):
        """Nearest composition ancestor (or self) of the given type. Remembered: the data does not change during a run."""
        k = (iid, etype, level)
        if k not in self._climb: self._climb[k] = self._climb_(iid, etype, level)
        return self._climb[k]

    def _climb_(self, iid, etype, level):
        seen, todo = set(), [iid]
        while todo:
            x = todo.pop(0)
            if x in seen: continue
            seen.add(x); n = self.get(x, level=level)
            if n and self.mm.is_a(n['type'], etype): return n
            todo += self.parents(x)
        return None

    def _boundary_tokens(self, comp):
        """The words of a component's boundary — its API operations and the data entities they access. Depends only on the
        component, so it is worked out once per component, not once per operation × API pair."""
        key = comp['id'] if comp else None
        if key not in self._bound:
            texts = []
            for x in (self.descendants(comp['id']) if comp else []):
                n = self.get(x, level=_L('application'))
                if not n: continue
                if self.mm.is_a(n['type'], _T('application.APIOperation')): texts += [n['name'], self.attr(n, 'path'), n.get('description'), self.attr(n, 'operation_id')]
            for c in (self.descendants(comp['id']) if comp else []):
                for e in self.children(c, 'access'):
                    de = self.get(e, _T('data.DataEntity'), _L('application'))
                    if de: texts.append(de['name'])
            self._bound[key] = tokens(*texts)
        return self._bound[key]

    def descendants(self, iid, kinds=('composition',)):
        k = (iid, tuple(kinds))
        if k not in self._desc: self._desc[k] = self._descendants(iid, kinds)
        return list(self._desc[k])

    def _descendants(self, iid, kinds):
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

    @staticmethod
    def evidence_class(plan_id, step, working):
        """What kind of evidence a proposal rests on (owner's decision D3; docs/design/aid-spec.md AID-E01): set by the rule and step, never
        read back from text a person wrote. Strongest first: attribute_join, structural, pattern, name_token, text."""
        w = str(working)
        if step == 'design': return 'pattern'
        if step == 5: return 'text'
        if step == 1: return 'attribute_join'                                # a field names the other record (deployed_on, hosts …)
        if plan_id in NAME_RULES or w.startswith(('fallback B', 'S06 ')) or 'verb and noun match' in w: return 'name_token'
        return 'structural'

    def band(self, plan_id, fallback=False):
        b = self.rules[plan_id]['confidence']
        return LOWER[b] if fallback else b

    # -- outputs
    def attempt(self, plan_id, src, tgt, step, data_read, reasoning, proposal_id=None, fallback=False, predicted=None, given=None, outcome=None):
        if plan_id not in self.rules: return None   # BX-02, BX-13: a rule of an extension that is off (e.g. ext:bian) does not run
        self.log.append({'plan_id': plan_id, 'connection': f"{src} → {tgt}" if tgt else src, 'step_assigned': self.rules[plan_id]['fill_step'], 'step_used': step,
                         'fallback': fallback, 'data_read': data_read, 'reasoning': reasoning, 'confidence_predicted': predicted or self.rules[plan_id]['confidence'],
                         'confidence_given': given, 'proposal_id': proposal_id, 'outcome': outcome or ('proposed' if proposal_id else 'no_proposal')})

    @staticmethod
    def _document_cap(b, working, *recs):
        """DEC-E-11: a link touching an entity transformed from a document is low, never more."""
        doc = [r['id'] for r in recs if r and str((r.get('attributes') or {}).get('source_id', '')).startswith(DOCUMENT_SOURCES)]
        if doc and b != 'low': return 'low', f'{working} — capped at low: {", ".join(doc)} transformed from a document (DEC-E-11)'
        return b, working

    def propose(self, plan_id, rel, src, tgt, step, working, data_read, fallback=False, band=None, ev=None):
        """A catalogue-typed proposal. Skips (and logs) a link already approved or already proposed in this run."""
        if plan_id not in self.rules: return None   # BX-02, BX-13: a rule of an extension that is off (e.g. ext:bian) does not run
        k = (src['id'], rel, tgt['id'])
        if k in self.approved:
            self.attempt(plan_id, src['id'], tgt['id'], step, data_read, 'already approved — not re-proposed', outcome='already_approved'); return None
        if k in self.rejected:
            self.left_out_rejected.add(k)
            self.attempt(plan_id, src['id'], tgt['id'], step, data_read, 'rejected by a person — not proposed again (RJ-03)', outcome='rejected'); return None
        if k in self.proposed:
            rec = self.proposed[k]; rec['evidence'].append(f'engine_rationale:{plan_id} step{step} also: {working}')
            rec['evidence_class'] = strongest(rec.get('evidence_class'), ev or self.evidence_class(plan_id, step, working)); return rec
        b = band or self.band(plan_id, fallback); pid = f'P-{self.uc}-{len(self.proposals) + 1:03d}'
        b, working = self._document_cap(b, working, src, tgt)
        rec = {'mapping_id': pid, 'source': self.ref(src), 'relationship': rel, 'target': self.ref(tgt), 'status': 'proposed', 'confidence': BAND[b],
               'evidence_class': ev or self.evidence_class(plan_id, step, working),
               'evidence': [f'engine_rationale:{plan_id} step{step} {working}'], 'rationale': working, 'baseline_id': f'ENGINE-RUN-{self.uc}', 'created_by': ENGINE_NAME}
        self.proposals.append(rec); self.proposed[k] = rec
        self._proposed_by_rel.setdefault(rel, []).append(k); self._by_mapping_id[pid] = rec; self._index_link(rel, k[0], k[2], pid)
        self.attempt(plan_id, src['id'], tgt['id'], step, data_read, working, pid, fallback, given=BAND[b])
        return rec

    def report(self, plan_id, src, tgt, step, working, data_read, fallback=False, band=None):
        """A candidate report (relationship = plan ID); not a registry record."""
        if src is None or tgt is None:   # an approved link to a record this workspace does not hold (e.g. a layer not loaded): nothing to report
            self.attempt(plan_id, (src or {}).get('id', '?'), (tgt or {}).get('id', '?'), step, data_read, f'{working} — an end is not in the loaded data; not reported', outcome='no_proposal')
            return None
        k = (src['id'], plan_id, tgt['id'])
        if k in self.reported:
            return self.reported[k]
        b = band or self.band(plan_id, fallback); cid = f'C-{self.uc}-{len(self.candidates) + 1:03d}'
        b, working = self._document_cap(b, working, src, tgt)
        rec = {'mapping_id': cid, 'source': self.ref(src), 'relationship': plan_id, 'target': self.ref(tgt), 'status': 'proposed', 'confidence': BAND[b],
               'evidence_class': self.evidence_class(plan_id, step, working),
               'evidence': [f'engine_rationale:{plan_id} step{step} {working}'], 'rationale': working, 'created_by': f'candidate_rule:{plan_id}'}
        self.candidates.append(rec); self.reported[k] = rec
        self._reported_by_plan.setdefault(plan_id, []).append(k); self._rix.setdefault((plan_id, k[0]), []).append((k[0], k[2], cid))
        self.attempt(plan_id, src['id'], tgt['id'], step, data_read, working, cid, fallback, given=BAND[b])
        return rec

    # ------------------------------------------------------------ step 1 — data joins (mapping-execution.md §3, step 1)
    def step1(self):
        comps = self.of(_T('application.ApplicationComponent'))
        deps = self.of(_T('technology.Deployment'))
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
            for p in self.r.nodes(level=_L('technology')):
                if c['id'] in _list(self.attr(p, 'hosts')): hosts.setdefault(p['id'], []).append(f"a4 {p['id']}.hosts lists {c['id']}")
            for d in deps:
                if self.attr(d, 'component_id') == c['id'] and self.attr(d, 'platform_id'):
                    hosts.setdefault(self.attr(d, 'platform_id'), []).append(f"a4 deployment {d['id']} (component {c['id']}) names platform {self.attr(d, 'platform_id')}")
            for x, via in hosts.items():
                t = self.get(x, _T('technology.InfrastructureComponent'), _L('technology'))
                if t is None:
                    self.attempt('S33', c['id'], x, 1, via, f'{x} is not an {_L("technology")} instance in the architecture dataset — no instance to map to'); continue
                if self.mm.is_a(t['type'], _T('technology.Deployment')): continue  # a deployment is DEPLOYED_AS, not a platform
                if not any(self.mm.is_a(t['type'], h) for h in (_T('technology.Node'), _T('technology.Device'), _T('technology.SystemSoftware'))):   # B1 (metamodel 0.8.0): only what hosts software
                    self.attempt('S33', c['id'], x, 1, via, f"{x} is a {t['type']} — an application is deployed on a Node, Device or System Software (ArchiMate 3.2), not on this"); continue
                plan = 'S34' if self.mm.is_a(t['type'], _T('technology.Node')) else 'S35' if self.mm.is_a(t['type'], _T('technology.Device')) else 'S33'
                note = {'S34': f', logged under S34 because the target is {_T("technology.Node")}', 'S35': f', logged under S35 because the target is {_T("technology.Device")}',
                        'S33': ' (S36 subsumed in S33)' if self.mm.is_a(t['type'], _T('technology.SystemSoftware')) else ''}[plan]
                self.propose(plan, 'DEPLOYED_ON', c, t, 1, f'data join{note}; ' + '; '.join(via), via, band=self.rules['S33']['confidence'])
        # candidate joins: (plan, source type, attribute on source, target type, reverse attribute on target)
        joins = [('S39', _T('application.ApplicationComponent'), 'built_as', _T('technology.Artifact'), 'of_component'),
                 ('S41', _T('application.ApplicationService'), 'consumes', _T('technology.TechnologyService'), None),
                 ('S43', _T('application.ApplicationInterface'), 'exposed_through', _T('technology.TechnologyInterface'), 'exposes'),
                 ('S45', _T('application.ApplicationFunction'), 'consumes', _T('technology.TechnologyService'), None),
                 ('S49', _T('data.DataEntity'), 'stored_in', _T('technology.Artifact'), None),
                 ('S50', _T('data.DataEntity'), 'stored_in', _T('technology.SystemSoftware'), None),
                 ('S51', _T('application.Event'), 'published_to', _T('technology.TechnologyService'), None)] + self.extra_joins()
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
        # S37 the component's network: the network its platform is on (RA4-37) first; the deprecated network_zone (AT-A3-07) only when
        # no platform route gives one (the owner's decisions G4, G5, 2026-11-14 — docs/design/sdem-hosting-evidence-s37-design.md)
        for c in comps:
            nets = {}
            for _, p, lab in self.links_by('DEPLOYED_ON', src=c['id']):
                for e in self.wedges:
                    if e['kind'] != 'association' or p not in (e['source'], e['target']): continue
                    n = e['target'] if e['source'] == p else e['source']
                    net = self.get(n, _T('technology.CommunicationNetwork'))
                    if net and not self.mm.is_a(net['type'], _T('technology.NetworkZone')):
                        nets.setdefault(n, (net, []))[1].append(f'{c["id"]} DEPLOYED_ON {p} ({lab}); a4 {p} association {n} (RA4-37)')
            z = self.attr(c, 'network_zone')
            for n, (net, via) in nets.items():
                self.report('S37', c, net, 1, 'data join; ' + '; '.join(via), via)
            if z and self.get(z, _T('technology.CommunicationNetwork')):
                if not nets:
                    self.report('S37', c, self.get(z, _T('technology.CommunicationNetwork')), 1, f"data join; a3 {c['id']}.network_zone = {z} (deprecated, AT-A3-07 — no platform route gives a network)", [f"{c['id']}.network_zone"])
                elif z not in nets:
                    self.attempt('S37', c['id'], z, 1, [f"a3 {c['id']}.network_zone = {z}"], f"the deprecated network_zone names {z}, but its platform is on {', '.join(sorted(nets))} — the platform route wins; a person corrects one of them")
        # S38 path carries the component
        for p in self.of(_T('technology.Path')):
            for x in _list(self.attr(p, 'carries')):
                c = self.get(x, _T('application.ApplicationComponent'))
                if c: self.report('S38', c, p, 1, f"data join; a4 {p['id']}.carries lists {x}", [f"{p['id']}.carries"])







    # ------------------------------------------------------------ shared: links known so far (approved, or proposed in this run)
    def links(self, rel):
        """(source id, target id, label) for a catalogue relationship: approved arrows and this run's proposals, labelled which."""
        out = list(self._approved_by_rel.get(rel, ()))
        out += [(k[0], k[2], self.proposed[k]['mapping_id']) for k in self._proposed_by_rel.get(rel, ())]
        return out

    def _index_link(self, rel, a, b, label):
        self._seq += 1; e = (self._seq, a, b, label)
        self._lix.setdefault((rel, 's', a), []).append(e); self._lix.setdefault((rel, 't', b), []).append(e)

    def links_by(self, rel, src=None, tgt=None, srcs=None, tgts=None):
        """links(rel) restricted to these sources or targets — the same entries in the same order, without scanning."""
        keys = [('s', x) for x in ([src] if src is not None else srcs or ())] + [('t', x) for x in ([tgt] if tgt is not None else tgts or ())]
        seen, out = set(), []
        for side, x in keys:
            for e in self._lix.get((rel, side, x), ()):
                if e[0] not in seen: seen.add(e[0]); out.append(e)
        return [(a, b, lab) for _, a, b, lab in sorted(out)]

    def reports_from(self, plan_id, src):
        """reports(plan_id) whose source is src — in the same order."""
        return list(self._rix.get((plan_id, src), ()))

    def band_of(self, label):
        """Confidence band of an input arrow: approved counts as high; a proposal carries its own."""
        if label == 'approved': return 'high'
        rec = self._by_mapping_id[label]
        return {0.8: 'high', 0.6: 'medium', 0.4: 'low'}[rec['confidence']]

    def reports(self, plan_id):
        return [(k[0], k[2], self.reported[k]['mapping_id']) for k in self._reported_by_plan.get(plan_id, ())]


    def component_of(self, a3_id):
        return self.climb(a3_id, _T('application.ApplicationComponent'), _L('application'))


    def one_to_one(self, plan_id, scored, file):
        """File the highest-scoring pair, drop pairs sharing either end, repeat; a tie at the top is no proposal (both named)."""
        pool = [x for x in scored]
        while pool:
            top = max(x[0] for x in pool)
            best = [x for x in pool if x[0] == top]
            ns, nt = collections.Counter(x[1]['id'] for x in best), collections.Counter(x[2]['id'] for x in best)   # another top pair sharing an end
            tied = [x for x in best if ns[x[1]['id']] > 1 or nt[x[2]['id']] > 1]
            tied_ids, best_ids = {id(x) for x in tied}, {id(x) for x in best}
            for x in tied:
                self.attempt(plan_id, x[1]['id'], x[2]['id'], 4, x[4], f'tie at score {top:.2f} with another pair sharing an end — no proposal')
            filed = [x for x in best if id(x) not in tied_ids]
            if not filed:
                pool = [x for x in pool if id(x) not in best_ids]; continue
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




    # ------------------------------------------------------------ step 3 — derivation over approved arrows and this run's proposals
    def step3(self):   # 0.22 step 3b: BIAN's rules first (S17…S29), then the core's (S40…S54) — the order as before
        self.step3_bian(); self.step3_core()

    # what an extension's steps provide (rules_bian.BianSteps; sdem-bian in 0.22): nothing here
    def extra_joins(self): return []
    def step2(self): pass
    def step4(self): pass
    def step3_bian(self): pass
    def step5(self, options): pass
    def design(self): return []

    def step3_core(self):
        # technology derived paths (C3)
        dep_as = self.links('DEPLOYED_AS'); dep_on = self.links('DEPLOYED_ON')
        for c, d, lab in dep_as:
            dn = self.get(d, _T('technology.Deployment')); env = self.get(self.attr(dn, 'environment_id'), _T('technology.DeploymentEnvironment')) if dn and self.attr(dn, 'environment_id') else None
            if env: self.report('S40', self.get(c, _T('application.ApplicationComponent')), env, 3, f'DEPLOYED_AS {d} ({lab}) in environment {env["id"]}', [lab])
            for x in self.descendants(c):
                api = self.get(x, _T('application.APIOperation'), _L('application'))
                if api: self.report('S47', api, dn, 3, f'{c} composes … {x}; {c} DEPLOYED_AS {d} ({lab})', [lab])
        for c, t, lab in dep_on:
            tn = self.get(t, _T('technology.InfrastructureComponent'), _L('technology'))
            if tn and self.mm.is_a(tn['type'], _T('technology.SystemSoftware')):
                for f in self.children(c, 'assignment'):
                    fn = self.get(f, _T('application.ApplicationFunction'))
                    if fn: self.report('S46', fn, tn, 3, f'{c} is assigned {f} and is DEPLOYED_ON {t} ({lab})', [lab])
        for ai, ti, lab in self.reports('S43'):
            tin = self.get(ti, _T('technology.TechnologyInterface')); ts = self.get(self.attr(tin, 'of_service'), _T('technology.TechnologyService')) if tin and self.attr(tin, 'of_service') else None
            if ts: self.report('S44', self.get(ai, _T('application.ApplicationInterface')), ts, 3, f'S43 {lab}: {ai} → {ti}, interface of {ts["id"]}', [lab])
            for e in self.wedges:
                if e['kind'] == 'assignment' and e['source'] == ai and self.get(e['target'], _T('application.ApplicationService')):
                    self.report('S42', self.get(e['target'], _T('application.ApplicationService')), tin, 3, f'{e["target"]} is exposed through {ai}, which is exposed through {ti} (S43 {lab})', [lab])
            for x in self.children(ai):
                api = self.get(x, _T('application.APIOperation'), _L('application'))
                if api: self.report('S48', api, tin, 3, f'{ai} composes {x}; {ai} exposed through {ti} (S43 {lab})', [lab])
        for sbb in self.of(_T('application.SolutionBuildingBlock')):
            comps = _list(self.attr(sbb, 'components'))
            for c, t, lab in dep_on:
                if c in comps:
                    tn = self.get(t, _T('technology.InfrastructureComponent'), _L('technology'))
                    self.report('S52', sbb, tn, 3, f'component {c} of the block is DEPLOYED_ON {t} ({lab})', [lab])
                    if tn and self.mm.is_a(tn['type'], _T('technology.Node')): self.report('S54', sbb, tn, 3, f'component {c} of the block is DEPLOYED_ON node {t} ({lab})', [lab])
            for c, d, lab in dep_as:
                if c in comps: self.report('S53', sbb, self.get(d, _T('technology.Deployment')), 3, f'component {c} of the block is DEPLOYED_AS {d} ({lab})', [lab])

    # ------------------------------------------------------------ step 5 — bounded text inference (S01 when step 3 found nothing; S08 on opt-in)
    GENERIC = {'bank', 'customer', 'manage', 'management', 'account', 'service', 'process', 'record', 'data'}




    # ------------------------------------------------------------ design targets — the one place instances are created (mapping-execution.md, M2)
    CREATE_TERMS = {'Initiate', 'Create', 'Register', 'Evaluate', 'Provide', 'Request'}




    def run(self, options=None):
        self.step1()
        self.step2()
        self.step4()
        self.step3()
        self.step5(options or {})
        design = self.design()
        out = {'proposals': self.proposals, 'candidates': self.candidates, 'log': self.log, 'left_out_rejected': sorted(self.left_out_rejected)}
        if design: out['design'] = design
        return out


class Run(CoreRun):   # 0.22 step 4a-2 (BX-15): BIAN's steps run in the installed sdem-bian (MX-53) — SDEM's engine is the core's
    pass
    pass


ENGINE_NAME = 'sdem-rules/0.10'


class RulesEngine:
    name = ENGINE_NAME

    def __init__(self, core_only=False):
        self.core_only = core_only   # 0.22 step 3b: BIAN's steps run in sdem-bian (MX-51) — this run is the core's rules only

    def infer(self, reader, case=None):
        return Run(reader, (case or {}).get('id', 'RUN')).run((case or {}).get('options'))
