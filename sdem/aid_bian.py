"""BIAN's part of AID (`sdem aid`) — the 0.22 plan, step 3c: the four points where AID's inference goes through BIAN, called by
sdem/aid_fill.py at the same points, in the same order, so they can move to the sdem-bian extension (R-D5) behind a phased contract.

    projection     AID-F1…F3, R1…R3, M: the domains, BIAN's container pattern, the reverse steps (aid.project, with BIAN's catalogue)
    patterns       AID-D05: a BIAN domain a pattern names and the design lacks
    information    AID-K02, I01…I04, I07: BIAN objects and the tables that store them
    direct         AID-L01…L05, I05, K01: links that go through BIAN's service domains, objects and fields
"""
from .identity import layer as _L  # ST-01…ST-05: layers by id

import datetime, hashlib, json, re  # noqa: F401
from .identity import T as _T, live as _live  # noqa: F401 — ST-01…ST-05: types by id
from .graph import FederatedGraph, LevelGraph  # noqa: F401
from .metamodel import Metamodel
from .rules_engine import CoreRun, RulesEngine, WEAK_CLASSES, _list, _rules, stem, stems, strongest, tokens, weakest  # noqa: F401 — the engine's helpers
from .rules_bian import BianSteps
from .store import GraphReader  # noqa: F401
import copy  # noqa: F401
from .identity import layer as _L2  # noqa: F401
from .aid_complete import SMALL, _unconfirmed, words  # noqa: F401 — shared with AID's core (D06 …)
from .aid_links import STOP, _idx, words as _lwords  # noqa: F401 — shared with AID's core (L06, I06 …)
from .aid import CATALOGUE_RULE, FILES, LOW, MEDIUM, NAME_ONLY, _reader, _registry, conf_of, is_weak, weak  # noqa: F401 — AID's package helpers, SDEM's


class Run(BianSteps, CoreRun):   # the engine with BIAN's steps: what the projection asks it (domain_of …)
    pass


CORE_DIRECT = {'AID-L06', 'AID-I06'}


def projection(ws, have, registry):
    """(the projection package, the catalogue it used) — WS-01: the workspace's own BIAN layer plus the BIAN catalogue it uses."""
    from .new import catalogue as workspace_catalogue
    catalogue = workspace_catalogue(ws)
    return project(have, catalogue, registry, either=True), catalogue   # AID-M02: for a person to review, keep what either side supports


def direct(after, maps, mm):
    """BIAN's direct links: AID-L01, L02, I05, then K01 (propose_fields)."""
    return propose_direct_bian(after, maps, mm), propose_fields(after, maps, mm)


# ---- AID's projection (moved from sdem/aid.py, 0.22 step 3c) ----

# AID's own rule names → the metamodel rule whose published basis they rest on (relationship-rules.json `source_reference`)
RULE_BASIS = _live(lambda: {'BIAN container pattern': 'S17', 'BIAN REST mapping': 'S24', f'named by {_L("technology")}': 'S32', 'domain name': 'S01'})

# AID's own rules → the kind of evidence they rest on (AID-E01); an engine rule brings its proposal's own class
RULE_CLASS = _live(lambda: {'BIAN container pattern': 'pattern', 'BIAN REST mapping': 'pattern', 'domain name': 'pattern', 'service group': 'pattern',
              f'named by {_L("technology")}': 'attribute_join', f'S33 ({_L("technology")} hosts)': 'attribute_join', 'S32 (deployment component_id)': 'attribute_join', 'name': 'name_token'})

def basis(rule, step=None, catalogue=None):
    """The source reference for a projection rule: the metamodel rule and its published basis."""
    if rule == CATALOGUE_RULE: return f"BIAN reference catalogue `{(catalogue or {}).get('model_id', '?')}` — the element is copied, not invented"
    if rule == 'name (id words)': return 'none published — SDEM fallback (AID-R02): words of an application id matched to domain names'
    if rule == 'service group': return 'none published — SDEM pattern (AID-R03): one process candidate per BIAN service group; the grouping itself is BIAN\'s ([SL14])'
    rid = 'S32' if (rule == 'BIAN container pattern' and step == 'F3') else RULE_BASIS.get(rule) or (re.match(r'(S\d\d|B\d\d)', rule or '') or [None])[0]
    r = _rules().get(rid)
    return f"{rid}: {r['source_reference']}" if r else f'{rule}: no metamodel entry'

def class_of(items):
    """The evidence class of a choice made for several reasons: the strongest (AID-E01)."""
    return strongest(*[x.get('evidence_class') for x in items])

def why_text(items):
    """Readable reasons from engine proposals and candidates: one line per rule, without step numbers or proposal ids."""
    out = []
    for x in items:
        t = re.sub(r'^(S\d\d|B\d\d) step\d\s*', r'\1 — ', plain(x['evidence'][0].replace('engine_rationale:', '')))
        t = re.sub(r'\s*(S\d\d) step\d\s*', r' · \1 — ', t)
        if t not in out: out.append(t)
    return '; '.join(out)

def plain(text):
    """Engine reasoning without run-local proposal ids."""
    return re.sub(r'\s*\((?:P|C)-AID-\d+\)|(?:P|C)-AID-\d+:\s*', '', text or '').strip()

def _sha(doc): return hashlib.sha256(json.dumps(doc, sort_keys=True).encode('utf-8')).hexdigest()

def _ref(i): return {'id': i['id'], 'type': i['type'], 'version': i['version']}

def _clean(name): return re.sub(r'\s*\(.*?\)\s*', ' ', name).strip()

class Projection:
    def __init__(self, have, catalogue, mm):
        self.have, self.cat, self.mm = have, catalogue, mm
        self.records = {lvl: {} for lvl in FILES}; self.rels = {lvl: [] for lvl in FILES}; self.links = {}; self.ends = []; self.steps = []
        self.cat_by_id = {i['id']: i for i in catalogue['instances']} if catalogue else {}

    @staticmethod
    def _prov(prov, ev):
        ev = ev or RULE_CLASS.get(prov['rule'])
        if ev: prov['evidence_class'] = ev
        return prov

    def record(self, lvl, rec, step, rule, inferred_from, reasoning, conf, ev=None):
        if rec['id'] in self.records[lvl]:
            r = self.records[lvl][rec['id']]
            if ev and 'evidence_class' in r['projection']: r['projection']['evidence_class'] = strongest(r['projection']['evidence_class'], ev)
            return r
        r = dict(rec); r['projection'] = self._prov({'step': step, 'rule': rule, 'source_reference': basis(rule, step, self.cat), 'inferred_from': inferred_from, 'reasoning': plain(reasoning), 'confidence': min(conf, MEDIUM)}, ev)
        self.records[lvl][rec['id']] = r; return r

    def link(self, rel, src, tgt, step, rule, inferred_from, reasoning, conf, ev=None):
        k = (src['id'], rel, tgt['id'])
        if k in self.links:
            l = self.links[k]; l['projection']['confidence'] = max(l['projection']['confidence'], min(conf, MEDIUM))
            if ev: l['projection']['evidence_class'] = strongest(l['projection'].get('evidence_class'), ev)
            return l
        l = {'mapping_id': f'PRJ-L-{len(self.links) + 1:03d}', 'source': _ref(src), 'relationship': rel, 'target': _ref(tgt), 'status': 'projected', 'confidence': min(conf, MEDIUM),
             'rationale': f'PROJECTED DESIGN, not a mapping: {plain(reasoning)}', 'projection': self._prov({'step': step, 'rule': rule, 'source_reference': basis(rule, step, self.cat), 'inferred_from': inferred_from, 'reasoning': plain(reasoning), 'confidence': min(conf, MEDIUM)}, ev)}
        self.links[k] = l; return l

    # -- BIAN references: a selected domain brings its catalogue structure, never anything invented
    def take_domain(self, dom_id, step, why, conf, evidence=None, ev=None):
        cat = self.cat_by_id; rels = self.cat.get('relationships', [])
        keep = [dom_id]; todo = [dom_id]
        while todo:
            x = todo.pop()
            for r in rels:
                if r['source'] == x and r['kind'] in ('composition', 'aggregation', 'association') and r['target'] not in keep and cat.get(r['target']) and cat[r['target']]['type'] != _T('bian.ServiceDomain'):
                    keep.append(r['target']); todo.append(r['target'])
        for x in keep:
            self.record(_L('bian'), cat[x], step, CATALOGUE_RULE, (evidence or [dom_id]) if x == dom_id else [dom_id], why if x == dom_id else f'part of {dom_id} in the BIAN catalogue', conf, ev)   # a part rests on what its domain rests on
        for r in rels:
            if r['source'] in keep and r['target'] in keep and r not in self.rels[_L('bian')]: self.rels[_L('bian')].append(r)

    def package(self, pid, created_at):
        layers = {}
        for lvl, recs in self.records.items():
            if not recs: continue
            layers[lvl] = {'level': lvl, 'model_id': f'{pid}-{lvl.lower()}-PROJECTION', 'model_version': 'projection', 'metamodel_version': self.mm.version,
                           'source_system': 'AID-PROJECTION (sdem aid; not a real architecture dataset)', 'instances': list(recs.values()), 'relationships': self.rels[lvl]}
        H = set(self.have)
        mode = 'forward' if min(H) == _L('business') and not ({_L('business'), _L('application')} <= H and _L('bian') not in H) and max(H) <= _L('bian') else 'middle' if {_L('business'), _L('application')} <= H and _L('bian') not in H else 'reverse' if min(H) >= _L('application') else 'forward and reverse'
        meta = {'projection_id': pid, 'mode': mode, 'created_by': 'sdem aid', 'created_at': created_at, 'metamodel_version': self.mm.version,
                'have': sorted(self.have), 'catalogue': {'model_id': (self.cat or {}).get('model_id'), 'sha256': _sha(self.cat) if self.cat else None},
                'inputs': {lvl: {'model_id': d.get('model_id'), 'sha256': _sha(d)} for lvl, d in sorted(self.have.items())},
                'steps': self.steps, 'projection_ends': self.ends,
                'summary': {lvl: {'records': len(d['instances']), 'by_confidence': {str(c): sum(1 for i in d['instances'] if i['projection']['confidence'] == c) for c in (MEDIUM, LOW)}} for lvl, d in layers.items()},
                'links': len(self.links)}
        return {'projection': meta, 'layers': layers, 'links': {'links': list(self.links.values())}}

def _engine(levels, mm, registry=None):
    reader = _reader(levels, mm, registry); res = RulesEngine().infer(reader, {'id': 'AID'})
    return res['proposals'], res['candidates'], reader

def forward_a2(prj, a1, registry):
    """F1 — choose the service domains A1 needs: the engine's rules on A1 + the BIAN catalogue."""
    props, cands, reader = _engine({_L('business'): a1, _L('bian'): prj.cat}, prj.mm, registry)
    doms = {}
    for m in props:
        if m['relationship'] in ('USES_DOMAIN', 'SUPPORTED_BY') and m['target']['id'] in prj.cat_by_id:
            doms.setdefault(m['target']['id'], []).append(m)
    for c in cands:
        if c['relationship'] == 'S07' and c['target']['id'] in prj.cat_by_id: doms.setdefault(c['target']['id'], []).append(c)
    for d, why in doms.items():
        best = max(conf_of(x) for x in why)
        prj.take_domain(d, 'F1', 'the business layer points to it — ' + why_text(why), best, sorted({x['source']['id'] for x in why}), class_of(why))
    for m in props:
        if m['target']['id'] in prj.records[_L('bian')] or m['target']['id'] in prj.cat_by_id and m['target']['id'] in doms:
            src = next(i for i in a1['instances'] if i['id'] == m['source']['id']); tgt = prj.cat_by_id[m['target']['id']]
            if m['target']['id'] not in prj.records[_L('bian')]: prj.take_domain(m['target']['id'], 'F1', m['rationale'], m['confidence'], ev=m.get('evidence_class'))
            prj.link(m['relationship'], src, tgt, 'F1', m['evidence'][0].split(' ')[0].replace('engine_rationale:', ''), [m['source']['id']], m['rationale'] + (' — name-only evidence, capped low (AID-B6)' if conf_of(m) < m['confidence'] else ''), conf_of(m), m.get('evidence_class'))
    prj.steps.append({'step': 'F1', 'domains': sorted(doms)})
    if not doms: prj.ends.append(f'projection ends at {_L("business")}: no business record names a BIAN operation or matches a catalogue domain closely enough')
    return sorted(doms)

def forward_a3_a4(prj, domains, a2, project_a4=True):
    """F2 + F3 — BIAN container pattern below the given or projected domains."""
    run = Run(_reader({_L('bian'): a2}, prj.mm), 'AID'); comps = []
    for dom_id in domains:
        dom = next((i for i in a2['instances'] if i['id'] == dom_id), None)
        if not dom: continue
        ops = [o for o in run.of(_T('bian.ServiceOperation')) if (run.domain_of(o['id']) or {}).get('id') == dom_id]
        if not ops: prj.ends.append(f'{dom_id}: no service operations in the {_L("bian")} data — no component projected'); continue
        ev = weakest('pattern', (prj.records[_L('bian')].get(dom_id) or {}).get('projection', {}).get('evidence_class')) or 'pattern'   # no stronger than its domain (AID-E01)
        at = run.get(run.attr(dom, 'asset_type'), _T('bian.AssetType')) if run.attr(dom, 'asset_type') else None
        base = at['name'] if at else _clean(dom['name']); coll = run._collection(base)
        comp = prj.record(_L('application'), {'id': f'PRJ-APP-{dom_id}', 'type': _T('application.ApplicationComponent'), 'version': '1.0', 'name': f'{base} service (projected)', 'lifecycle_status': 'planned',
                                 'description': f"Projected: one deployable component for {_clean(dom['name'])} (BIAN container pattern)."}, 'F2', 'BIAN container pattern', [dom_id], 'one component per service domain', LOW, ev)
        comps.append(comp); prj.link('REALIZED_BY', dom, comp, 'F2', 'BIAN container pattern', [dom_id], 'one component per service domain', LOW, ev)
        for op in ops:
            method, path, why = run._rest_form(op, coll)
            if not method: prj.ends.append(f"{op['id']}: {why} — no API projected"); continue
            api = prj.record(_L('application'), {'id': f"PRJ-API-{op['id']}", 'type': _T('application.APIOperation'), 'version': '1.0', 'name': f'{method} {path}', 'lifecycle_status': 'planned',
                                    'attributes': {'method': method, 'path': path, 'payload_fields': sorted(set(_list(run.attr(op, 'input_attributes')) + _list(run.attr(op, 'output_attributes'))))}},
                             'F2', 'BIAN REST mapping', [op['id']], why, LOW, ev)
            prj.rels[_L('application')].append({'source': comp['id'], 'kind': 'composition', 'target': api['id']})
            prj.link('IMPLEMENTED_BY', op, api, 'F2', 'BIAN REST mapping', [op['id']], why, LOW, ev)
    if project_a4: forward_a4(prj, comps)
    prj.steps.append({'step': 'F2', 'components': [c['id'] for c in comps]})
    return comps

def forward_a4(prj, comps):
    for comp in comps:
        dep = prj.record(_L('technology'), {'id': f"PRJ-DEP-{comp['id'].replace('PRJ-APP-', '')}", 'type': _T('technology.Deployment'), 'version': '1.0', 'name': f"{comp['name']} — deployment (projected)", 'lifecycle_status': 'planned',
                                'attributes': {'component_id': comp['id']}}, 'F3', 'BIAN container pattern', [comp['id']], 'one deployment per component; no platform, environment or network is projected', LOW, comp['projection'].get('evidence_class'))
        prj.link('DEPLOYED_AS', comp, dep, 'F3', 'BIAN container pattern', [comp['id']], 'one deployment per component', LOW, comp['projection'].get('evidence_class'))
    prj.steps.append({'step': 'F3', 'deployments': len(comps)})

def reverse_a3(prj, a4):
    """R1 — the applications that A4 records name (hosts, deployments, artifacts)."""
    named = {}
    for i in a4['instances']:
        at = i.get('attributes') or {}
        for key in ('hosts', 'component_id', 'of_component'):
            for x in _list(at.get(key)): named.setdefault(x, []).append((i, key))
    stubs = []
    for cid, via in sorted(named.items()):
        # AID-R05: a deployment or artifact of one application is usually named after it ("Payments Hub — production")
        names = [re.split(r'\s+[—–-]\s+|\s*\(|:', i['name'])[0].strip() for i, k in via if k in ('component_id', 'of_component') and i.get('name')]
        name = max(set(names), key=names.count) if names else cid
        st = prj.record(_L('application'), {'id': cid, 'type': _T('application.ApplicationComponent'), 'version': '1.0', 'name': name},
                        'R1', f'named by {_L("technology")}', [f"{i['id']}.{k}" for i, k in via],
                        f'an {_L("technology")} record names this application' + (f'; its name comes from {", ".join(sorted({i["id"] for i, k in via if k in ("component_id", "of_component")}))}' if names else f'; nothing else about it is known from {_L("technology")}'), MEDIUM)
        stubs.append(st)
        for i, key in via:
            if key == 'hosts': prj.link('DEPLOYED_ON', st, i, 'R1', f'S33 ({_L("technology")} hosts)', [f"{i['id']}.hosts"], f"{i['id']} hosts {cid}", MEDIUM)
            if key == 'component_id' and mm_is(prj, i['type'], _T('technology.Deployment')): prj.link('DEPLOYED_AS', st, i, 'R1', 'S32 (deployment component_id)', [f"{i['id']}.component_id"], f"{i['id']} deploys {cid}", MEDIUM)
    prj.steps.append({'step': 'R1', 'applications': [s['id'] for s in stubs]})
    if not stubs: prj.ends.append(f'projection ends at {_L("technology")}: no technology record names an application')
    return stubs

def mm_is(prj, t, a): return prj.mm.is_a(t, a)

def reverse_a2(prj, a3, a4=None, registry=None):
    """R2 — choose the service domains A3 realises: the engine's rules on A3 (+ A4) + the BIAN catalogue."""
    levels = {_L('bian'): prj.cat, _L('application'): a3}
    if a4: levels[_L('technology')] = a4
    props, _, _ = _engine(levels, prj.mm, registry)
    doms = {}
    for m in props:
        if m['relationship'] == 'REALIZED_BY' and m['source']['id'] in prj.cat_by_id: doms.setdefault(m['source']['id'], []).append(m)
    for d, why in doms.items():
        c = max(conf_of(x) for x in why)
        prj.take_domain(d, 'R2', 'the application layer points to it — ' + why_text(why) + (' — name-only evidence, capped low (AID-B6)' if c < max(x['confidence'] for x in why) else ''), c, sorted({x['target']['id'] for x in why}), class_of(why))
    a3_ids = {i['id']: i for i in a3['instances']}
    for m in props:
        s, t = m['source']['id'], m['target']['id']
        if m['relationship'] in ('IMPLEMENTED_BY', 'REALIZED_BY', 'MAPPED_TO') and s in prj.cat_by_id and t in a3_ids:
            if m['relationship'] == 'IMPLEMENTED_BY':
                dom = Run(_reader({_L('bian'): prj.cat}, prj.mm), 'AID').domain_of(s)
                if dom and dom['id'] not in prj.records[_L('bian')]: prj.take_domain(dom['id'], 'R2', f'its operation {s} is implemented by {t}', m['confidence'], ev=m.get('evidence_class'))
            if m['relationship'] == 'MAPPED_TO' and s not in prj.records[_L('bian')]:
                prj.record(_L('bian'), prj.cat_by_id[s], 'R2', CATALOGUE_RULE, [t], f'business object mapped from data entity {t}', m['confidence'], m.get('evidence_class'))
            prj.link(m['relationship'], prj.cat_by_id[s], a3_ids[t], 'R2', m['evidence'][0].split(' ')[0].replace('engine_rationale:', ''), [t], m['rationale'] + (' — name-only evidence, capped low (AID-B6)' if conf_of(m) < m['confidence'] else ''), conf_of(m), m.get('evidence_class'))
    stubs = [i for i in a3['instances'] if (prj.records[_L('application')].get(i['id']) or {}).get('projection', {}).get('step') == 'R1']
    if stubs and not doms: name_fallback(prj, stubs)
    chosen = sorted({i for i, r in prj.records[_L('bian')].items() if r['type'] == _T('bian.ServiceDomain')})
    prj.steps.append({'step': 'R2', 'domains': chosen})
    if not chosen: prj.ends.append(f'projection ends at {_L("application")}: the application data (names, APIs, data entities) does not match any domain in the BIAN catalogue')
    return chosen

GENERIC = {'app', 'application', 'service', 'services', 'system', 'platform', 'hub', 'gateway', 'engine', 'core', 'api', 'portal', 'cmp', 'svc', 'sys', 'gw', 'module', 'manager', 'management'}

def subject_words(prj, d):
    """The words of what a BIAN service domain is about: its asset type, or — when BIAN publishes none — its own name."""
    at = prj.cat_by_id.get((d.get('attributes') or {}).get('asset_type')) or {}
    return stems(tokens(at.get('name') or _clean(d['name']))) - stems(set(GENERIC))

def name_fallback(prj, stubs):
    """R2 for applications known only by a name (or id) from A4 (AID-R06): a domain is suggested only when the name covers what
    the domain is about — its whole subject, or at least two of its words and two thirds of it — and only the best-covered
    domains; one shared common word ('payment', 'order') is not enough. Otherwise AID stops here and says what it needs."""
    doms = [i for i in prj.cat['instances'] if i['type'] == _T('bian.ServiceDomain')]
    subj = {d['id']: subject_words(prj, d) for d in doms}
    for st in stubs:
        words = stems(tokens(st['name'] if st['name'] != st['id'] else ' '.join(re.split(r'[-_]', st['id'])))) - stems(set(GENERIC))
        found = []
        for d in doms:
            sw = subj[d['id']]
            if not sw: continue
            shared = sw & words; cover = len(shared) / len(sw)
            if cover == 1 or (len(shared) >= 2 and cover >= 2 / 3): found.append((cover, len(shared), d, sorted(shared)))
        if not found:
            prj.ends.append(f"{st['id']} {st['name']!r}: its name does not say which BIAN service domain it realises — describe its APIs or data "
                            f"({_L('application')}), or connect it yourself (sdem connect <service domain> REALIZED_BY {st['id']} …)"); continue
        best = max((c, n) for c, n, _, _ in found)
        for c, n, d, shared in found:
            if (c, n) != best: continue
            why = f"its name {st['name']!r} covers {_clean(d['name'])}'s subject ({', '.join(shared)}) — name only"
            prj.take_domain(d['id'], 'R2', why, LOW, [st['id']], 'name_token')
            prj.link('REALIZED_BY', d, st, 'R2', 'name', [st['id']], why, LOW)

def reverse_a1(prj, domains):
    """R3 — per domain, one capability candidate (from its name) and one process candidate per BIAN service group
    (the group's operations): the weakest step, as BIAN publishes no capability- or process-to-domain mapping."""
    for d in domains:
        dom = prj.cat_by_id.get(d) or prj.records[_L('bian')].get(d)
        if not dom: continue
        cap = prj.record(_L('business'), {'id': f'PRJ-CAP-{d}', 'type': _T('business.BusinessCapability'), 'version': '1.0', 'name': f"{_clean(dom['name'])} (capability candidate)", 'lifecycle_status': 'planned'},
                         'R3', 'domain name', [d], f"a business capability is likely to be supported by {_clean(dom['name'])}; BIAN publishes no capability mapping, so this is a candidate only", LOW)
        prj.link('SUPPORTED_BY', cap, dom, 'R3', 'domain name', [d], 'capability candidate', LOW)
        rels = (prj.cat or {}).get('relationships', [])
        groups = [prj.cat_by_id[r['target']] for r in rels if r['source'] == d and r['kind'] == 'composition' and (prj.cat_by_id.get(r['target']) or {}).get('type') == _T('bian.ServiceGroup')]
        if not groups: prj.ends.append(f'{d}: no BIAN service groups in the catalogue — no process candidates'); continue
        at = prj.cat_by_id.get((dom.get('attributes') or {}).get('asset_type')) or {}
        used = {l['source']['id'] for l in prj.links.values() if l['relationship'] == 'IMPLEMENTED_BY'}   # operations the design's APIs implement
        for g in groups:
            ops = [prj.cat_by_id[r['target']] for r in rels if r['source'] == g['id'] and r['kind'] == 'composition' and (prj.cat_by_id.get(r['target']) or {}).get('type') == _T('bian.ServiceOperation')]
            if not ops or not any(o['id'] in used for o in ops): continue   # AID-R07: only for service groups the design uses
            why = f"BIAN groups the operations {', '.join(o['name'] for o in ops)} as “{g['name']}”; a business process typically covers one such group — a candidate only"
            prc = prj.record(_L('business'), {'id': f"PRJ-PRC-{g['id']}", 'type': _T('business.BusinessProcess'), 'version': '1.0', 'name': f"{g['name']} — {at.get('name') or _clean(dom['name'])} (process candidate)",
                                    'lifecycle_status': 'planned', 'attributes': {'invokes': [o['id'] for o in ops]}}, 'R3', 'service group', [g['id']] + [o['id'] for o in ops], why, LOW)
            prj.link('USES_DOMAIN', prc, dom, 'R3', 'service group', [g['id']], 'process candidate', LOW)
    prj.steps.append({'step': 'R3', 'capability_candidates': len(domains), 'process_candidates': sum(1 for x in prj.records[_L('business')] if x.startswith('PRJ-PRC-'))})

def project(have, catalogue=None, registry=None, pid=None, created_at=None, either=False):
    """have: {'A1': dataset, …} — one or more layers. Returns a projection package dict."""
    mm = Metamodel.load(); prj = Projection(have, catalogue, mm); H = set(have)
    if not H: raise ValueError('AID needs at least one architecture dataset (AID-I01)')
    for name, d in list(have.items()) + ([('catalogue', catalogue)] if catalogue else []):
        issues = LevelGraph(d, mm).validate()  # AID-I01: every input passes the dataset check (CTL-01…03, CTL-16)
        if issues: raise ValueError(f"{name} ({d.get('model_id')}) fails the dataset check: {issues[0]}")
    pid = pid or 'PRJ-' + '-'.join(sorted(H)); created_at = created_at or datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    if _L('bian') in H:
        doms = [i['id'] for i in have[_L('bian')]['instances'] if i['type'] == _T('bian.ServiceDomain')]
        if _L('application') not in H: forward_a3_a4(prj, doms, have[_L('bian')], project_a4=_L('technology') not in H)
        if _L('business') not in H: reverse_a1(prj, doms)
    elif not catalogue:
        prj.ends.append(f'no {_L("bian")} layer and no BIAN catalogue: nothing can be projected through the BIAN layer')
    elif _L('business') in H and _L('application') in H:  # middle gap — the domains both sides support
        fwd = Projection(have, catalogue, mm); f = set(forward_a2(fwd, have[_L('business')], registry))
        rev = Projection(have, catalogue, mm); r = set(reverse_a2(rev, have[_L('application')], have.get(_L('technology')), registry))
        both = sorted(f & r)
        for d in both:
            fr, rr = fwd.records[_L('bian')][d]['projection'], rev.records[_L('bian')][d]['projection']
            prj.take_domain(d, 'M', f"supported from both sides. Business side (F1): {fr['reasoning']}. Application side (R2): {rr['reasoning']}", MEDIUM, fr['inferred_from'] + rr['inferred_from'],
                            strongest(fr.get('evidence_class'), rr.get('evidence_class')))
        approved_links = [m for m in ((registry or {}).get('mappings', []) if isinstance(registry, dict) else (registry or [])) if m.get('status') == 'approved']
        decided_f = {m['target']['id'] for m in approved_links if m.get('relationship') in ('USES_DOMAIN', 'SUPPORTED_BY')}   # domains the business side already uses, approved
        decided_r = {m['source']['id'] for m in approved_links if m.get('relationship') == 'REALIZED_BY' and str(m['source'].get('type', '')).startswith((_L('bian') + '.'))}   # domains an application already realises, approved
        if either:   # AID-M02: filling a workspace for a person to review — a domain one side supports is kept too, at that side's confidence
            kept_r = set()
            for side, d in [(fwd, d) for d in sorted(f - r)] + [(rev, d) for d in sorted(r - f)]:
                x = side.records[_L('bian')][d]['projection']
                other = (f | decided_f) if side is rev else (r | decided_r)   # AID-M03: "the other side already names its domains" — by a proposal now, or by a link a person approved earlier (F15)
                weak_only = x['evidence_class'] in WEAK_CLASSES if x.get('evidence_class') else (side is rev and x['confidence'] <= LOW)
                if other and weak_only:
                    # AID-M03, by evidence class (AID-E02): the other side already names its domains; a domain only names or descriptions on
                    # one side point to is a note, not a record
                    by = 'application' if side is rev else 'business'
                    prj.ends.append(f"not added — {d} ({_clean(prj.cat_by_id[d]['name'])}): only {by} names or descriptions point to it ({x['reasoning']}; evidence: {x.get('evidence_class', 'name only')}). "
                                    f"If it belongs to this design, name its operations in a process's invokes, or add it: sdem bian add --workspace <ws> \"{_clean(prj.cat_by_id[d]['name'])}\" --person <you>")
                    continue
                if side is rev: kept_r.add(d)
                prj.take_domain(d, 'M', f"supported from the {'business' if side is fwd else 'application'} side only: {x['reasoning']}", x['confidence'], x['inferred_from'], x.get('evidence_class'))
            both = sorted(f | (r & f) | kept_r)
        for side in (fwd, rev):
            for k, l in side.links.items():
                ends = {l['source']['id'], l['target']['id']}
                if ends & set(both) or any(Run(_reader({_L('bian'): catalogue}, mm), 'AID').domain_of(e) and Run(_reader({_L('bian'): catalogue}, mm), 'AID').domain_of(e)['id'] in both for e in ends if e in prj.cat_by_id):
                    src = {'id': l['source']['id'], 'type': l['source']['type'], 'version': l['source']['version']}; tgt = {'id': l['target']['id'], 'type': l['target']['type'], 'version': l['target']['version']}
                    boost = 0 if is_weak(l) else 0.2   # agreement lifts a link — never one that rests on a name alone (AID-B6)
                    prj.link(l['relationship'], src, tgt, 'M', l['projection']['rule'], l['projection']['inferred_from'], l['projection']['reasoning'], min(l['confidence'] + boost, MEDIUM), l['projection'].get('evidence_class'))
        for x, rec in list(fwd.records[_L('bian')].items()) + list(rev.records[_L('bian')].items()):
            if rec['type'] == _T('bian.BusinessObject') and x not in prj.records[_L('bian')]: prj.record(_L('bian'), prj.cat_by_id[x], 'M', CATALOGUE_RULE, rec['projection']['inferred_from'], rec['projection']['reasoning'], rec['projection']['confidence'], rec['projection'].get('evidence_class'))
        prj.steps.append({'step': 'M', 'forward_domains': sorted(f), 'reverse_domains': sorted(r), 'kept': both})
        if not both: prj.ends.append('middle gap: the business and application layers point to no common BIAN domain')
        if _L('technology') not in H: forward_a4(prj, [])
    elif _L('business') in H:  # forward
        doms = forward_a2(prj, have[_L('business')], registry)
        if doms and _L('application') not in H:
            a2p = {'level': _L('bian'), 'model_id': 'aid-selected', 'model_version': 'x', 'metamodel_version': mm.version, 'instances': list(prj.records[_L('bian')].values()), 'relationships': prj.rels[_L('bian')]}
            a2p['instances'] = [{k: v for k, v in i.items() if k != 'projection'} for i in a2p['instances']]
            forward_a3_a4(prj, doms, a2p, project_a4=_L('technology') not in H)
    else:  # reverse from A3 and/or A4
        a3 = have.get(_L('application'))
        if a3 is None and _L('technology') in H:
            stubs = reverse_a3(prj, have[_L('technology')])
            a3 = {'level': _L('application'), 'model_id': 'aid-stubs', 'model_version': 'x', 'metamodel_version': mm.version, 'instances': [{k: v for k, v in s.items() if k != 'projection'} for s in stubs], 'relationships': []}
        doms = reverse_a2(prj, a3, have.get(_L('technology')), registry) if a3 and a3['instances'] else []
        if doms and _L('business') not in H: reverse_a1(prj, doms)
    return prj.package(pid, created_at)


# ---- AID-D05 (moved from sdem/aid_complete.py) ----

def pattern_domains(docs, catalogue, maps, mm, structures, mark, rejected=()):
    """AID-D05. A BIAN service domain a pattern names (a part found anywhere, by its name) that the design lacks is taken from the catalogue
    with its parts, marked inferred (evidence: the pattern); and the one process whose name shares a word with the domain's is proposed as
    using it. Returns ([A2 record], [A2 link], [(process, 'USES_DOMAIN', domain, why)], [domain id added])."""
    from .profile import applies
    from .bian import reach
    a2 = docs.get(_L('bian')) or {'instances': [], 'relationships': []}
    recs = {i['id']: (l, i) for l, d in docs.items() for i in d.get('instances', [])}
    have = {i['name']: i['id'] for i in a2['instances'] if i['type'] == _T('bian.ServiceDomain')}
    new, links, uses, added = [], [], [], []
    live = {(s, r, t) for s, r, t in maps}
    for st in structures:
        pat, S = st['pattern'], st['structure']; aw = pat.get('applies_when') or {}
        anchors = sorted(i for i, (l, r) in recs.items() if mm.known(r['type']) and mm.is_a(r['type'], aw.get('entity', '')) and applies({'when': aw.get('when') or {}}, r) and not _unconfirmed(r))
        if not anchors: continue
        for role in S['roles']:
            name = (role.get('when') or {}).get('name')
            if not (role.get('anywhere') and role['type'] == _T('bian.ServiceDomain') and isinstance(name, str)): continue
            asked = f"{pat['id']}/{role['id']}"
            if name not in have and catalogue:
                keep = reach(catalogue, {name}); by = {i['id']: i for i in catalogue['instances']}
                sd = next((i for i in keep if by[i]['type'] == _T('bian.ServiceDomain')), None)
                if not sd or sd in rejected: continue
                for i in sorted(keep):
                    if i in recs or any(n['id'] == i for n in new): continue
                    r = copy.deepcopy(by[i])
                    r.setdefault('attributes', {})['inferred'] = mark('AID-D05', f"the pattern {pat['title']} ({pat['id']}) says a design that has {anchors[0]} has BIAN's {name}: {role.get('reasoning', '')}".rstrip(': '),
                                                                      anchors[0] if i == sd else sd, confidence='low', evidence_class='pattern', asked_by=asked)
                    new.append(r)
                ids = set(recs) | {n['id'] for n in new}
                links += [r for r in catalogue.get('relationships', []) if r['source'] in keep and r['target'] in ids and not any((r['source'], r['kind'], r['target']) == (x['source'], x['kind'], x['target']) for x in a2.get('relationships', []) + links)]
                have[name] = sd; added.append(sd)
            sd = have.get(name)
            if not sd or any(r == 'USES_DOMAIN' and t == sd for _, r, t in live): continue
            procs = [(i, r) for i, (l, r) in recs.items() if mm.known(r['type']) and mm.is_a(r['type'], _T('business.BusinessProcess')) and not _unconfirmed(r)]
            others = set().union(*[words(n) for n in have if n != name] or [set()])
            hits = {}
            for w in words(name) - others:
                got = [i for i, r in procs if w in words(r.get('name'))]
                if len(got) == 1: hits[w] = got[0]
            if len(set(hits.values())) == 1:
                p = next(iter(hits.values())); w = sorted(hits)[0]
                if (p, 'USES_DOMAIN', sd) not in live:
                    uses.append((p, 'USES_DOMAIN', sd, f"{p} is the one process whose name has the word '{w}' of BIAN's {name}, which the pattern {pat['id']} asks a process to use — name evidence only"))
    return new, links, uses, added


# ---- AID-K01, K02 (moved from sdem/aid_links.py) ----

SYN = {'identification': 'ref', 'identifier': 'ref', 'reference': 'ref', 'id': 'ref', 'ref': 'ref', 'from': 'debtor', 'source': 'debtor',
       'debtor': 'debtor', 'payer': 'debtor', 'target': 'creditor', 'to': 'creditor', 'creditor': 'creditor', 'payee': 'creditor',
       'amount': 'amount', 'value': 'amount', 'currency': 'currency', 'date': 'date', 'datetime': 'date', 'time': 'date', 'status': 'status',
       'description': 'text', 'remittance': 'text', 'information': 'text', 'name': 'name', 'account': 'account', 'iban': 'account'}

COMPAT = {'integer': ('int', 'integer', 'smallint', 'bigint', 'number', 'numeric'), 'decimal': ('numeric', 'decimal', 'number', 'float', 'double', 'real', 'money'),
          'amount': ('numeric', 'decimal', 'number', 'money'), 'date': ('date', 'timestamp', 'datetime'), 'datetime': ('timestamp', 'datetime', 'date'),
          'boolean': ('bool', 'boolean', 'bit')}

def concepts(name, drop=()):
    return {SYN.get(w, w) for w in _lwords(name) if w not in STOP and w not in drop}

def family(field_name, object_name):
    """Fix 3: a BIAN field's family — its object's own (the name starts with the object's name) or one BIAN repeats from a parent object."""
    own = ''.join(w.capitalize() for w in _lwords(object_name))
    return 'own' if str(field_name).startswith(own) else 'inherited'

def propose_fields(docs, mappings, mm):
    """AID-K01: [(BIAN field, 'FIELD_MAPPED_TO', column, 'AID-K01', why, confidence)]."""
    every, rels = _idx(docs)
    fields = {}
    for s, k, t in rels:
        if k == 'composition' and t in every and (mm.is_a(every[t]['type'], _T('bian.BusinessObjectAttribute')) or mm.is_a(every[t]['type'], _T('data.DataAttribute'))):
            fields.setdefault(s, []).append(every[t])
    done = {m['target']['id'] for m in mappings if m['relationship'] == 'FIELD_MAPPED_TO' and m.get('status') != 'rejected'}
    out = []
    for m in mappings:
        if m['relationship'] != 'MAPPED_TO' or m.get('status') not in ('approved', 'proposed'): continue
        bo, ent = m['source']['id'], m['target']['id']
        if bo not in every or not mm.is_a(every[bo]['type'], _T('bian.BusinessObject')): continue
        bofs, cols = fields.get(bo, []), fields.get(ent, [])
        drop = set(_lwords(every[bo]['name'])); used = set()
        for col in cols:
            if col['id'] in done: continue
            want = concepts(col['name'])
            if not want: continue
            pt = str((col.get('attributes') or {}).get('physical_type') or '').lower()
            scored = []
            for f in bofs:
                have = concepts(f['name'], drop)
                if not have: continue
                score = len(want & have) / len(want | have)
                lt = str((f.get('attributes') or {}).get('data_type') or '').lower()
                if lt in COMPAT and pt and not pt.startswith(COMPAT[lt]): score -= 0.5
                if family(f['name'], every[bo]['name']) == 'own': score += 0.1
                scored.append((score, f))
            scored.sort(key=lambda x: -x[0])
            scored = [x for x in scored if x[1]['id'] not in used]   # one BIAN field maps to one column
            if scored and scored[0][0] >= 0.6 and (len(scored) == 1 or scored[0][0] - scored[1][0] >= 0.1 - 1e-9):   # the column's main words, not one of two
                f = scored[0][1]; used.add(f['id'])
                out.append((f['id'], 'FIELD_MAPPED_TO', col['id'], 'AID-K01', f"{col['name']} says what {f['name']} says ({', '.join(sorted(want & concepts(f['name'], drop)))})", 0.6 if scored[0][0] >= 0.8 else 0.4))
                done.add(col['id'])
    return out

def match_existing(docs, mappings, mm):
    """AID-K02: [(BIAN object, 'MAPPED_TO', existing data entity, 'AID-K02', why, confidence)] — run before AID-I01, so an object an existing
    table already stores gets that table proposed, not a new inferred one."""
    every, rels = _idx(docs)
    fields = {}
    for s_, k, t in rels:
        if k == 'composition' and t in every and (mm.is_a(every[t]['type'], _T('bian.BusinessObjectAttribute')) or mm.is_a(every[t]['type'], _T('data.DataAttribute'))):
            fields.setdefault(s_, []).append(every[t])
    mapped = {(m['source']['id'], m['target']['id']) for m in mappings if m['relationship'] == 'MAPPED_TO' and m.get('status') != 'rejected'}
    has_map = {a for a, _ in mapped}
    ents = [e for e in every.values() if mm.is_a(e['type'], _T('data.DataEntity')) and not (e.get('attributes') or {}).get('inferred') and fields.get(e['id'])]
    objs = [o for o in every.values() if mm.is_a(o['type'], _T('bian.BusinessObject')) and fields.get(o['id']) and o['id'] not in has_map]
    best = {}   # each object to its one best table; each table to its one best object
    for e in ents:
        cols = [concepts(c['name']) for c in fields[e['id']]]
        score = []
        for o in objs:
            have = set().union(*[concepts(f['name']) for f in fields[o['id']]]) | concepts(o['name'])   # the object's name counts: an account's fields are about an account
            hits = sum(1 for c in cols if c and len(c & have) / len(c) >= 0.5)
            if hits < 2: continue   # one shared word (a reference) is not evidence that the table stores the object
            sc = hits / len(cols)
            if (set(_lwords(o['name'])) & set(_lwords(e['name']))) - {'the', 'of', 'a', 'and'}: sc += 0.2   # the table is named for the object (its plain words)
            score.append((sc, o))
        score.sort(key=lambda x: -x[0])
        if score and score[0][0] >= 0.5 and (len(score) == 1 or score[0][0] - score[1][0] >= 0.15 - 1e-9):
            o = score[0][1]
            if score[0][0] > best.get(o['id'], (0, None))[0]: best[o['id']] = (score[0][0], e)
    out = []
    for oid, (sc, e) in sorted(best.items()):
        if (oid, e['id']) not in mapped:
            out.append((oid, 'MAPPED_TO', e['id'], 'AID-K02', f"{min(sc, 1):.0%} of {e['name']}'s columns say what {every[oid]['name']}'s fields say", 0.4))
    return out


# ---- AID-I01…I04, I07 (moved from sdem/aid_info.py) ----

TYPES = {'string': 'varchar(140)', 'text': 'text', 'integer': 'integer', 'decimal': 'numeric(18,6)', 'amount': 'numeric(18,2)',
         'currency_code': 'char(3)', 'date': 'date', 'datetime': 'timestamp', 'boolean': 'boolean', 'identifier': 'varchar(35)',
         'enum': 'varchar(35)', 'reference': 'varchar(35)'}   # SDEM's default physical type for each logical type — the architect changes it

def _snake(name):
    s = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', '_', str(name)).replace(' ', '_').replace('-', '_')
    return re.sub(r'_+', '_', s).strip('_').lower()

def _key(name):
    return re.sub(r'[^A-Z0-9]+', '-', str(name).upper()).strip('-')

def propose_information(a2, a3, mappings, mark, rejected=frozenset(), is_inferred=lambda r: False):
    """Returns (instances, relationships, links, skipped): new A3 records, A3 links, (source, relationship, target, why) to propose, and the
    objects left without a table by AID-I08 ([{id, name, domains}]). `mark(rule, reasoning, frm)` gives the `inferred` block every new record carries."""
    a2i = {i['id']: i for i in (a2 or {}).get('instances', []) if not is_inferred(i)}
    a3i = {i['id']: i for i in (a3 or {}).get('instances', [])}
    fields = {}
    for r in (a2 or {}).get('relationships', []):
        if r.get('kind') == 'composition' and r['source'] in a2i and a2i.get(r['target'], {}).get('type') == _T('bian.BusinessObjectAttribute'):
            fields.setdefault(r['source'], []).append(a2i[r['target']])
    refers = {r['source']: r['target'] for r in (a2 or {}).get('relationships', [])
              if r.get('kind') == 'association' and a2i.get(r['source'], {}).get('type') == _T('bian.BusinessObjectAttribute')}
    mapped = {}
    for m in mappings:
        if m.get('relationship') == 'MAPPED_TO' and m.get('status') != 'rejected':
            mapped.setdefault(m['source']['id'], m['target']['id'])
    entity_of = dict(mapped)
    # AID-I08: which service domains work on each object (domain aggregates control record; control record is associated with the object), and which are realised here
    typ2 = {i: r.get('type') for i, r in a2i.items()}
    sd_of = {r['target']: r['source'] for r in (a2 or {}).get('relationships', []) if r.get('kind') == 'aggregation' and typ2.get(r['source']) == _T('bian.ServiceDomain')}
    domains = {}
    for r in (a2 or {}).get('relationships', []):
        if r.get('kind') == 'association' and typ2.get(r['source']) == _T('bian.ControlRecord') and r['source'] in sd_of: domains.setdefault(r['target'], set()).add(sd_of[r['source']])
    realised = {m['source']['id'] for m in mappings if m.get('relationship') == 'REALIZED_BY' and m.get('status') != 'rejected'}
    has_apps = any(i.get('type') == _T('application.ApplicationComponent') and not is_inferred(i) for i in a3i.values())
    skipped = []
    declined = {}   # RJ-04: a person rejected the object's mapping — where it is stored is theirs to say; nothing is inferred in its place
    for m in mappings:
        if m.get('relationship') == 'MAPPED_TO' and m.get('status') == 'rejected': declined.setdefault(m['source']['id'], m['target']['id'])
    for bo, fs in fields.items():   # AID-I01: the entities first, so a foreign key can point at one inferred in the same run
        if bo in mapped or a2i[bo].get('type') != _T('bian.BusinessObject'): continue
        if bo in declined:
            skipped.append({'id': bo, 'name': a2i[bo].get('name', bo), 'domains': sorted(domains.get(bo, ())), 'why': f'a person rejected its mapping to {declined[bo]} (RJ-04)'}); continue
        if has_apps and domains.get(bo) and not (domains[bo] & realised):
            skipped.append({'id': bo, 'name': a2i[bo].get('name', bo), 'domains': sorted(domains[bo])}); continue
        eid = f"AID-ENT-{_key(a2i[bo]['name'])}"
        if eid not in rejected: entity_of[bo] = eid
    inst, rels, links = [], [], []
    for bo, fs in sorted(fields.items()):
        if bo in mapped or bo not in entity_of: continue
        o, eid = a2i[bo], entity_of[bo]
        if eid not in a3i:
            names = [_snake(f['name']) for f in fs]
            inst.append({'id': eid, 'type': _T('data.DataEntity'), 'version': '1', 'name': f"{_snake(o['name'])} (inferred)", 'lifecycle_status': 'planned',
                         'description': f"Inferred: the data entity that stores the business object {o['name']} ({bo}).",
                         'attributes': {'attributes': names, 'inferred': mark('AID-I01', f"one data entity per business object with typed fields — {o['name']} has {len(fs)}", bo)}})
            rels_from = []
            for f in fs:
                a = f.get('attributes') or {}
                fid = f"AID-ENTF-{_key(o['name'])}-{_key(f['name'])}"
                if fid in rejected or fid in a3i: continue
                lt = a.get('data_type') or 'string'
                fa = {'physical_type': TYPES.get(lt, 'varchar(140)'), 'required': bool(a.get('required'))}
                if a.get('identifier'): fa['primary_key'] = True
                if a.get('allowed_values'): fa['allowed_values'] = list(a['allowed_values'])
                if a.get('personal_information') is not None: fa['personal_information'] = a['personal_information']
                fa['inferred'] = mark('AID-I01', f"the field {f['name']} ({lt}) as {fa['physical_type']}" + (', the primary key' if fa.get('primary_key') else ''), f['id'])
                inst.append({'id': fid, 'type': _T('data.DataAttribute'), 'version': '1', 'name': _snake(f['name']), 'lifecycle_status': 'planned', 'attributes': fa})
                rels.append({'source': eid, 'kind': 'composition', 'target': fid})
                target = entity_of.get(refers.get(f['id']))
                if target and target != eid:   # AID-I02: a reference becomes a foreign key
                    rels.append({'source': fid, 'kind': 'association', 'target': target})
                links.append((f['id'], 'FIELD_MAPPED_TO', fid, f"the data attribute {_snake(f['name'])} stores the BIAN attribute {f['name']} (AID-I03)"))
                rels_from.append(fid)
            links.insert(len(links) - len(rels_from), (bo, 'MAPPED_TO', eid, f"the data entity stores the business object {o['name']} (AID-I03)"))
    return inst, rels, links, sorted(skipped, key=lambda s: s['id'])

def propose_access(docs, mappings, mm, mark):
    """AID-I07 (found in v2: inferred tables nobody used): a data entity no component accesses is accessed by the one component that realises
    the BIAN service domain whose control record is associated with the business object the entity stores. A link inside A3, marked inferred."""
    a2, a3 = docs.get(_L('bian')) or {}, docs.get(_L('application')) or {}
    i3 = {i['id']: i for i in a3.get('instances', [])}
    accessed = {r['target'] for r in a3.get('relationships', []) if r.get('kind') == 'access'}
    live = [m for m in mappings if m.get('status') in ('approved', 'proposed')]
    stores = {}
    for m in live:
        if m['relationship'] == 'MAPPED_TO': stores.setdefault(m['target']['id'], set()).add(m['source']['id'])
    realised = {}
    for m in live:
        if m['relationship'] == 'REALIZED_BY' and mm.is_a(m['source'].get('type') or '', _T('bian.ServiceDomain')):
            realised.setdefault(m['source']['id'], set()).add(m['target']['id'])
    cr_of = {}
    for r in a2.get('relationships', []):
        if r.get('kind') == 'association': cr_of.setdefault(r['target'], set()).add(r['source'])
    sd_of = {r['target']: r['source'] for r in a2.get('relationships', []) if r.get('kind') == 'aggregation'}
    out = []
    for e, rec in i3.items():
        if not mm.is_a(rec['type'], _T('data.DataEntity')) or e in accessed: continue
        comps = {c for bo in stores.get(e, ()) for cr in cr_of.get(bo, ()) for c in realised.get(sd_of.get(cr), ())}
        if len(comps) == 1:
            c = next(iter(comps))
            out.append({'source': c, 'kind': 'access', 'target': e,
                        'inferred': mark('AID-I07', f'{e} stores a business object the control record of a domain {c} realises works on, and nothing accesses {e}', e)})
    return out


# ---- AID-L01, L02, I05 (moved from sdem/aid_links.propose_direct) ----

def propose_direct_bian(docs, mappings, mm, only=None):
    """AID-L01, L02, I05 — BIAN's direct links (moved from sdem/aid_links.propose_direct, 0.22 step 3c): through the domains a process uses,
    the BIAN operations it invokes, and BIAN's business objects. [(source, relationship, target, rule, why, confidence)]."""
    every, rels = _idx(docs)
    live = [m for m in mappings if m.get('status') in ('approved', 'proposed')]
    have = {(m['source']['id'], m['relationship'], m['target']['id']) for m in mappings if m.get('status') != 'rejected'}
    link = lambda rel: [(m['source']['id'], m['target']['id']) for m in live if m['relationship'] == rel]
    isa = lambda x, t: x in every and mm.is_a(every[x]['type'], t)
    out = []
    def add(s, rel, t, rule, why, conf):
        if (s, rel, t) not in have:
            have.add((s, rel, t))
            if only is None or rule in only: out.append((s, rel, t, rule, why, conf))
    parts = {}   # a component and its parts (composition, aggregation)
    for s, k, t in rels:
        if k in ('composition', 'aggregation'): parts.setdefault(s, set()).add(t)
    def with_parts(c, seen=None):
        seen = seen or set()
        if c in seen: return set()
        seen.add(c); return {c} | set().union(*[with_parts(p, seen) for p in parts.get(c, ())]) if parts.get(c) else {c}
    realises = {}   # component or function → application services it realises
    for s, k, t in rels:
        if k == 'realization' and isa(t, _T('application.ApplicationService')): realises.setdefault(s, set()).add(t)
    served = {}     # AID-L01
    for p, sd in link('USES_DOMAIN'):
        if not isa(p, _T('business.BusinessProcess')): continue
        svcs = set()
        for d, comp in link('REALIZED_BY'):
            if d == sd and isa(comp, _T('application.ApplicationComponent')):
                for c in with_parts(comp): svcs |= realises.get(c, set())
        if len(svcs) == 1:
            svc = next(iter(svcs)); served.setdefault(p, set()).add(svc)
            add(p, 'SERVED_BY', svc, 'AID-L01', f'{p} uses {sd}, realised by {next(c for d, c in link("REALIZED_BY") if d == sd)}, which provides {svc}', 0.6)
            for a, k, t in rels:
                if k == 'assignment' and t == p and (isa(a, _T('business.BusinessActor')) or isa(a, _T('business.BusinessRole'))):
                    add(a, 'SERVED_BY', svc, 'AID-L01', f'{a} performs {p}, which {svc} serves', 0.4)
    for p, svc in link('SERVED_BY'):
        if isa(p, _T('business.BusinessProcess')) and isa(svc, _T('application.ApplicationService')): served.setdefault(p, set()).add(svc)
    for s, rel, t, *_ in out:
        if rel == 'SERVED_BY' and isa(s, _T('business.BusinessProcess')): served.setdefault(s, set()).add(t)
    impl = dict(link('IMPLEMENTED_BY'))   # AID-L02
    iface_of = {t: s for s, k, t in rels if k == 'composition' and isa(s, _T('application.ApplicationInterface')) and isa(t, _T('application.APIOperation'))}
    assigned = {}
    for s, k, t in rels:
        if k == 'assignment' and isa(s, _T('application.ApplicationInterface')) and isa(t, _T('application.ApplicationService')): assigned.setdefault(s, set()).add(t)
    funcs_of = {}
    for s, k, t in rels:
        if k == 'realization' and isa(s, _T('application.ApplicationFunction')) and isa(t, _T('application.ApplicationService')): funcs_of.setdefault(t, set()).add(s)
    acts = {}
    for s, k, t in rels:
        if k == 'composition' and isa(s, _T('business.BusinessProcess')) and isa(t, _T('business.BusinessActivity')): acts.setdefault(s, set()).add(t)
    for p, rec in every.items():
        if not isa(p, _T('business.BusinessProcess')) or isa(p, _T('business.BusinessActivity')): continue
        ops = set((rec.get('attributes') or {}).get('invokes') or [])
        for a in acts.get(p, ()): ops |= set((every[a].get('attributes') or {}).get('invokes') or [])
        fs = set()
        for op in ops:
            api = impl.get(op); i = iface_of.get(api)
            for svc in assigned.get(i, ()): fs |= funcs_of.get(svc, set())
        names = set(words(rec.get('name', ''))) | {w for a in acts.get(p, ()) for w in words(every[a].get('name', ''))}
        fs = {f for f in fs if (set(words(every[f].get('name', ''))) - STOP) & (names - STOP)}   # the function does what the process says it does
        if len(fs) == 1:
            f = next(iter(fs)); add(p, 'AUTOMATED_BY', f, 'AID-L02', f'{p} invokes BIAN operations implemented by APIs of a service that {f} realises', 0.4)
    # AID-I05: an A1 business object ALIGNED_TO the BIAN business object of the same name, when exactly one has it
    norm = lambda n: ''.join(words(n))
    bians = {}
    for x, r in every.items():
        if isa(x, _T('bian.BusinessObject')): bians.setdefault(norm(r.get('name', '')), []).append(x)
    for x, r in every.items():
        if isa(x, _T('business.BusinessObject')):
            same = bians.get(norm(r.get('name', '')), [])
            if len(same) == 1: add(x, 'ALIGNED_TO', same[0], 'AID-I05', f"{r.get('name')} is BIAN's {every[same[0]].get('name')} (the same name)", 0.6)
    return out
