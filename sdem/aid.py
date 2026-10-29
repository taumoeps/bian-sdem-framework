"""Architecture Inference Design (AID) — docs/design/aid-design.md, docs/design/aid-spec.md.

Projects the architecture layers an architect does not have from the ones they do, for planning. The output is a
**projected design** in a projection package, kept apart from real data (CTL-16) and fully marked (CTL-17):

  forward  F1 A1 → A2  the engine's rules on A1 + the BIAN catalogue choose the service domains
           F2 A2 → A3  BIAN container pattern: one component per domain, one API per operation (REST mapping)
           F3 A3 → A4  one deployment per component; no platform, environment or network
  reverse  R1 A4 → A3  the applications A4 records name
           R2 A3 → A2  the engine's rules on A3 (+ A4) + the catalogue choose the service domains
           R3 A2 → A1  one capability candidate per domain (weakest step)
  middle   A1 + A3 → A2: the domains both sides support
  gaps     projected vs real: matched, projected only, real only, differs

BIAN elements are always references to the catalogue, never invented. No element is above medium confidence.
Usage: sdem aid project --have a1.json [...] --catalogue bian.json --out DIR · sdem aid check DIR · sdem aid gaps DIR --actual a*.json mappings.json
"""
import argparse, datetime, hashlib, json, re, sys
from pathlib import Path

from .graph import FederatedGraph, LevelGraph
from .metamodel import Metamodel
from .rules_engine import Run, RulesEngine, _list, _rules, stem, tokens
from .store import GraphReader
from .validate import load_registry

MEDIUM, LOW = 0.6, 0.4
from .paths import DATA_ROOT as _DATA_ROOT
SCHEMA = _DATA_ROOT / 'schema' / 'projection.schema.json'
FILES = {'A1': 'projected-a1-business.json', 'A2': 'projected-a2-service-domain.json', 'A3': 'projected-a3-application.json', 'A4': 'projected-a4-technology.json'}
CATALOGUE_RULE = 'BIAN catalogue reference'
PROVENANCE = ('step', 'rule', 'source_reference', 'inferred_from', 'reasoning', 'confidence')
# AID's own rule names → the metamodel rule whose published basis they rest on (relationship-rules.json `source_reference`)
RULE_BASIS = {'BIAN container pattern': 'S17', 'BIAN REST mapping': 'S24', 'named by A4': 'S32', 'domain name': 'S01'}


def basis(rule, step=None, catalogue=None):
    """The source reference for a projection rule: the metamodel rule and its published basis."""
    if rule == CATALOGUE_RULE: return f"BIAN reference catalogue `{(catalogue or {}).get('model_id', '?')}` — the element is copied, not invented"
    if rule == 'name (id words)': return 'none published — SDEM fallback (AID-R02): words of an application id matched to domain names'
    if rule == 'service group': return 'none published — SDEM pattern (AID-R03): one process candidate per BIAN service group; the grouping itself is BIAN\'s ([SL14])'
    rid = 'S32' if (rule == 'BIAN container pattern' and step == 'F3') else RULE_BASIS.get(rule) or (re.match(r'(S\d\d|B\d\d)', rule or '') or [None])[0]
    r = _rules().get(rid)
    return f"{rid}: {r['source_reference']}" if r else f'{rule}: no metamodel entry'


NAME_ONLY = re.compile(r'fallback|step5|verb and noun match|contains \[.*\], which begin words')


def weak(text):
    """AID-B6: evidence that rests on names alone — an engine fallback (e.g. S17 fallback B: one asset-type word in API
    paths), a description match (step 5), a verb-and-noun name match, or the id-word fallback. Never above low."""
    return bool(NAME_ONLY.search(text or ''))


def conf_of(item):
    """An engine proposal's confidence, capped at low when its evidence is name-only (AID-B6)."""
    return min(item['confidence'], LOW) if all(weak(e) for e in item['evidence']) else item['confidence']


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


def _registry(maps=()): return {'registry_version': load_registry()['$schema_version'], 'metamodel_version': Metamodel.load().version, 'mappings': list(maps)}
def _sha(doc): return hashlib.sha256(json.dumps(doc, sort_keys=True).encode('utf-8')).hexdigest()
def _ref(i): return {'id': i['id'], 'type': i['type'], 'version': i['version']}
def _clean(name): return re.sub(r'\s*\(.*?\)\s*', ' ', name).strip()


class Projection:
    def __init__(self, have, catalogue, mm):
        self.have, self.cat, self.mm = have, catalogue, mm
        self.records = {lvl: {} for lvl in FILES}; self.rels = {lvl: [] for lvl in FILES}; self.links = {}; self.ends = []; self.steps = []
        self.cat_by_id = {i['id']: i for i in catalogue['instances']} if catalogue else {}

    def record(self, lvl, rec, step, rule, inferred_from, reasoning, conf):
        if rec['id'] in self.records[lvl]: return self.records[lvl][rec['id']]
        r = dict(rec); r['projection'] = {'step': step, 'rule': rule, 'source_reference': basis(rule, step, self.cat), 'inferred_from': inferred_from, 'reasoning': plain(reasoning), 'confidence': min(conf, MEDIUM)}
        self.records[lvl][rec['id']] = r; return r

    def link(self, rel, src, tgt, step, rule, inferred_from, reasoning, conf):
        k = (src['id'], rel, tgt['id'])
        if k in self.links:
            l = self.links[k]; l['projection']['confidence'] = max(l['projection']['confidence'], min(conf, MEDIUM)); return l
        l = {'mapping_id': f'PRJ-L-{len(self.links) + 1:03d}', 'source': _ref(src), 'relationship': rel, 'target': _ref(tgt), 'status': 'projected', 'confidence': min(conf, MEDIUM),
             'rationale': f'PROJECTED DESIGN, not a mapping: {plain(reasoning)}', 'projection': {'step': step, 'rule': rule, 'source_reference': basis(rule, step, self.cat), 'inferred_from': inferred_from, 'reasoning': plain(reasoning), 'confidence': min(conf, MEDIUM)}}
        self.links[k] = l; return l

    # -- BIAN references: a selected domain brings its catalogue structure, never anything invented
    def take_domain(self, dom_id, step, why, conf, evidence=None):
        cat = self.cat_by_id; rels = self.cat.get('relationships', [])
        keep = [dom_id]; todo = [dom_id]
        while todo:
            x = todo.pop()
            for r in rels:
                if r['source'] == x and r['kind'] in ('composition', 'aggregation', 'association') and r['target'] not in keep and cat.get(r['target']) and cat[r['target']]['type'] != 'A2.ServiceDomain':
                    keep.append(r['target']); todo.append(r['target'])
        for x in keep:
            self.record('A2', cat[x], step, CATALOGUE_RULE, (evidence or [dom_id]) if x == dom_id else [dom_id], why if x == dom_id else f'part of {dom_id} in the BIAN catalogue', conf)
        for r in rels:
            if r['source'] in keep and r['target'] in keep and r not in self.rels['A2']: self.rels['A2'].append(r)

    def package(self, pid, created_at):
        layers = {}
        for lvl, recs in self.records.items():
            if not recs: continue
            layers[lvl] = {'level': lvl, 'model_id': f'{pid}-{lvl.lower()}-PROJECTION', 'model_version': 'projection', 'metamodel_version': self.mm.version,
                           'source_system': 'AID-PROJECTION (sdem aid; not a real architecture dataset)', 'instances': list(recs.values()), 'relationships': self.rels[lvl]}
        H = set(self.have)
        mode = 'forward' if min(H) == 'A1' and not ({'A1', 'A3'} <= H and 'A2' not in H) and max(H) <= 'A2' else 'middle' if {'A1', 'A3'} <= H and 'A2' not in H else 'reverse' if min(H) >= 'A3' else 'forward and reverse'
        meta = {'projection_id': pid, 'mode': mode, 'created_by': 'sdem aid', 'created_at': created_at, 'metamodel_version': self.mm.version,
                'have': sorted(self.have), 'catalogue': {'model_id': (self.cat or {}).get('model_id'), 'sha256': _sha(self.cat) if self.cat else None},
                'inputs': {lvl: {'model_id': d.get('model_id'), 'sha256': _sha(d)} for lvl, d in sorted(self.have.items())},
                'steps': self.steps, 'projection_ends': self.ends,
                'summary': {lvl: {'records': len(d['instances']), 'by_confidence': {str(c): sum(1 for i in d['instances'] if i['projection']['confidence'] == c) for c in (MEDIUM, LOW)}} for lvl, d in layers.items()},
                'links': len(self.links)}
        return {'projection': meta, 'layers': layers, 'links': {'links': list(self.links.values())}}


def _reader(levels, mm, registry=None):
    return GraphReader(FederatedGraph([LevelGraph(d, mm) for d in levels.values()], [registry or _registry()], mm), 'aid')


def _engine(levels, mm, registry=None):
    reader = _reader(levels, mm, registry); res = RulesEngine().infer(reader, {'id': 'AID'})
    return res['proposals'], res['candidates'], reader


# ------------------------------------------------------------------ steps

def forward_a2(prj, a1, registry):
    """F1 — choose the service domains A1 needs: the engine's rules on A1 + the BIAN catalogue."""
    props, cands, reader = _engine({'A1': a1, 'A2': prj.cat}, prj.mm, registry)
    doms = {}
    for m in props:
        if m['relationship'] in ('USES_DOMAIN', 'SUPPORTED_BY') and m['target']['id'] in prj.cat_by_id:
            doms.setdefault(m['target']['id'], []).append(m)
    for c in cands:
        if c['relationship'] == 'S07' and c['target']['id'] in prj.cat_by_id: doms.setdefault(c['target']['id'], []).append(c)
    for d, why in doms.items():
        best = max(conf_of(x) for x in why)
        prj.take_domain(d, 'F1', 'the business layer points to it — ' + why_text(why), best, sorted({x['source']['id'] for x in why}))
    for m in props:
        if m['target']['id'] in prj.records['A2'] or m['target']['id'] in prj.cat_by_id and m['target']['id'] in doms:
            src = next(i for i in a1['instances'] if i['id'] == m['source']['id']); tgt = prj.cat_by_id[m['target']['id']]
            if m['target']['id'] not in prj.records['A2']: prj.take_domain(m['target']['id'], 'F1', m['rationale'], m['confidence'])
            prj.link(m['relationship'], src, tgt, 'F1', m['evidence'][0].split(' ')[0].replace('engine_rationale:', ''), [m['source']['id']], m['rationale'] + (' — name-only evidence, capped low (AID-B6)' if conf_of(m) < m['confidence'] else ''), conf_of(m))
    prj.steps.append({'step': 'F1', 'domains': sorted(doms)})
    if not doms: prj.ends.append('projection ends at A1: no business record names a BIAN operation or matches a catalogue domain closely enough')
    return sorted(doms)


def forward_a3_a4(prj, domains, a2, project_a4=True):
    """F2 + F3 — BIAN container pattern below the given or projected domains."""
    run = Run(_reader({'A2': a2}, prj.mm), 'AID'); comps = []
    for dom_id in domains:
        dom = next((i for i in a2['instances'] if i['id'] == dom_id), None)
        if not dom: continue
        ops = [o for o in run.of('A2.ServiceOperation') if (run.domain_of(o['id']) or {}).get('id') == dom_id]
        if not ops: prj.ends.append(f'{dom_id}: no service operations in the A2 data — no component projected'); continue
        at = run.get(run.attr(dom, 'asset_type'), 'A2.AssetType') if run.attr(dom, 'asset_type') else None
        base = at['name'] if at else _clean(dom['name']); coll = run._collection(base)
        comp = prj.record('A3', {'id': f'PRJ-APP-{dom_id}', 'type': 'A3.ApplicationComponent', 'version': '1.0', 'name': f'{base} service (projected)', 'lifecycle_status': 'planned',
                                 'description': f"Projected: one deployable component for {_clean(dom['name'])} (BIAN container pattern)."}, 'F2', 'BIAN container pattern', [dom_id], 'one component per service domain', LOW)
        comps.append(comp); prj.link('REALIZED_BY', dom, comp, 'F2', 'BIAN container pattern', [dom_id], 'one component per service domain', LOW)
        for op in ops:
            method, path, why = run._rest_form(op, coll)
            if not method: prj.ends.append(f"{op['id']}: {why} — no API projected"); continue
            api = prj.record('A3', {'id': f"PRJ-API-{op['id']}", 'type': 'A3.APIOperation', 'version': '1.0', 'name': f'{method} {path}', 'lifecycle_status': 'planned',
                                    'attributes': {'method': method, 'path': path, 'payload_fields': sorted(set(_list(run.attr(op, 'input_attributes')) + _list(run.attr(op, 'output_attributes'))))}},
                             'F2', 'BIAN REST mapping', [op['id']], why, LOW)
            prj.rels['A3'].append({'source': comp['id'], 'kind': 'composition', 'target': api['id']})
            prj.link('IMPLEMENTED_BY', op, api, 'F2', 'BIAN REST mapping', [op['id']], why, LOW)
    if project_a4: forward_a4(prj, comps)
    prj.steps.append({'step': 'F2', 'components': [c['id'] for c in comps]})
    return comps


def forward_a4(prj, comps):
    for comp in comps:
        dep = prj.record('A4', {'id': f"PRJ-DEP-{comp['id'].replace('PRJ-APP-', '')}", 'type': 'A4.Deployment', 'version': '1.0', 'name': f"{comp['name']} — deployment (projected)", 'lifecycle_status': 'planned',
                                'attributes': {'component_id': comp['id']}}, 'F3', 'BIAN container pattern', [comp['id']], 'one deployment per component; no platform, environment or network is projected', LOW)
        prj.link('DEPLOYED_AS', comp, dep, 'F3', 'BIAN container pattern', [comp['id']], 'one deployment per component', LOW)
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
        st = prj.record('A3', {'id': cid, 'type': 'A3.ApplicationComponent', 'version': '1.0', 'name': cid},
                        'R1', 'named by A4', [f"{i['id']}.{k}" for i, k in via], 'an A4 record names this application; nothing else about it is known from A4', MEDIUM)
        stubs.append(st)
        for i, key in via:
            if key == 'hosts': prj.link('DEPLOYED_ON', st, i, 'R1', 'S33 (A4 hosts)', [f"{i['id']}.hosts"], f"{i['id']} hosts {cid}", MEDIUM)
            if key == 'component_id' and mm_is(prj, i['type'], 'A4.Deployment'): prj.link('DEPLOYED_AS', st, i, 'R1', 'S32 (deployment component_id)', [f"{i['id']}.component_id"], f"{i['id']} deploys {cid}", MEDIUM)
    prj.steps.append({'step': 'R1', 'applications': [s['id'] for s in stubs]})
    if not stubs: prj.ends.append('projection ends at A4: no technology record names an application')
    return stubs


def mm_is(prj, t, a): return prj.mm.is_a(t, a)


def reverse_a2(prj, a3, a4=None, registry=None):
    """R2 — choose the service domains A3 realises: the engine's rules on A3 (+ A4) + the BIAN catalogue."""
    levels = {'A2': prj.cat, 'A3': a3}
    if a4: levels['A4'] = a4
    props, _, _ = _engine(levels, prj.mm, registry)
    doms = {}
    for m in props:
        if m['relationship'] == 'REALIZED_BY' and m['source']['id'] in prj.cat_by_id: doms.setdefault(m['source']['id'], []).append(m)
    for d, why in doms.items():
        c = max(conf_of(x) for x in why)
        prj.take_domain(d, 'R2', 'the application layer points to it — ' + why_text(why) + (' — name-only evidence, capped low (AID-B6)' if c < max(x['confidence'] for x in why) else ''), c, sorted({x['target']['id'] for x in why}))
    a3_ids = {i['id']: i for i in a3['instances']}
    for m in props:
        s, t = m['source']['id'], m['target']['id']
        if m['relationship'] in ('IMPLEMENTED_BY', 'REALIZED_BY', 'MAPPED_TO') and s in prj.cat_by_id and t in a3_ids:
            if m['relationship'] == 'IMPLEMENTED_BY':
                dom = Run(_reader({'A2': prj.cat}, prj.mm), 'AID').domain_of(s)
                if dom and dom['id'] not in prj.records['A2']: prj.take_domain(dom['id'], 'R2', f'its operation {s} is implemented by {t}', m['confidence'])
            if m['relationship'] == 'MAPPED_TO' and s not in prj.records['A2']:
                prj.record('A2', prj.cat_by_id[s], 'R2', CATALOGUE_RULE, [t], f'business object mapped from data entity {t}', m['confidence'])
            prj.link(m['relationship'], prj.cat_by_id[s], a3_ids[t], 'R2', m['evidence'][0].split(' ')[0].replace('engine_rationale:', ''), [t], m['rationale'] + (' — name-only evidence, capped low (AID-B6)' if conf_of(m) < m['confidence'] else ''), conf_of(m))
    stubs = [i for i in a3['instances'] if (prj.records['A3'].get(i['id']) or {}).get('projection', {}).get('step') == 'R1']
    if stubs and not doms: name_fallback(prj, stubs)
    chosen = sorted({i for i, r in prj.records['A2'].items() if r['type'] == 'A2.ServiceDomain'})
    prj.steps.append({'step': 'R2', 'domains': chosen})
    if not chosen: prj.ends.append('projection ends at A3: the application data (names, APIs, data entities) does not match any domain in the BIAN catalogue')
    return chosen


STUB_WORDS = {'APP', 'CMP', 'SVC', 'SYS', 'HUB', 'API', 'CORE', 'GW'}


def name_fallback(prj, stubs):
    """R2 for applications known only by the id an A4 record gives them: an id word (3+ letters) that begins a word of a
    catalogue domain's name or asset type suggests that domain — low confidence, the weakest evidence R2 accepts."""
    for st in stubs:
        words = [w.lower() for w in re.split(r'[-_]', st['id']) if len(w) >= 3 and w.upper() not in STUB_WORDS]
        for d in (i for i in prj.cat['instances'] if i['type'] == 'A2.ServiceDomain'):
            at = prj.cat_by_id.get((d.get('attributes') or {}).get('asset_type')) or {}
            names = re.findall(r'[a-z]+', (_clean(d['name']) + ' ' + at.get('name', '')).lower())
            hit = sorted({w for w in words for n in names if n.startswith(w)})
            if not hit: continue
            why = f"application id {st['id']} contains {hit}, which begin words of {_clean(d['name'])}; nothing else is known from A4"
            prj.take_domain(d['id'], 'R2', why, LOW, [st['id']])
            prj.link('REALIZED_BY', d, st, 'R2', 'name (id words)', [st['id']], why, LOW)


def reverse_a1(prj, domains):
    """R3 — per domain, one capability candidate (from its name) and one process candidate per BIAN service group
    (the group's operations): the weakest step, as BIAN publishes no capability- or process-to-domain mapping."""
    for d in domains:
        dom = prj.cat_by_id.get(d) or prj.records['A2'].get(d)
        if not dom: continue
        cap = prj.record('A1', {'id': f'PRJ-CAP-{d}', 'type': 'A1.BusinessCapability', 'version': '1.0', 'name': f"{_clean(dom['name'])} (capability candidate)", 'lifecycle_status': 'planned'},
                         'R3', 'domain name', [d], f"a business capability is likely to be supported by {_clean(dom['name'])}; BIAN publishes no capability mapping, so this is a candidate only", LOW)
        prj.link('SUPPORTED_BY', cap, dom, 'R3', 'domain name', [d], 'capability candidate', LOW)
        rels = (prj.cat or {}).get('relationships', [])
        groups = [prj.cat_by_id[r['target']] for r in rels if r['source'] == d and r['kind'] == 'composition' and (prj.cat_by_id.get(r['target']) or {}).get('type') == 'A2.ServiceGroup']
        if not groups: prj.ends.append(f'{d}: no BIAN service groups in the catalogue — no process candidates'); continue
        at = prj.cat_by_id.get((dom.get('attributes') or {}).get('asset_type')) or {}
        for g in groups:
            ops = [prj.cat_by_id[r['target']] for r in rels if r['source'] == g['id'] and r['kind'] == 'composition' and (prj.cat_by_id.get(r['target']) or {}).get('type') == 'A2.ServiceOperation']
            if not ops: continue
            why = f"BIAN groups the operations {', '.join(o['name'] for o in ops)} as “{g['name']}”; a business process typically covers one such group — a candidate only"
            prc = prj.record('A1', {'id': f"PRJ-PRC-{g['id']}", 'type': 'A1.BusinessProcess', 'version': '1.0', 'name': f"{g['name']} — {at.get('name') or _clean(dom['name'])} (process candidate)",
                                    'lifecycle_status': 'planned', 'attributes': {'invokes': [o['id'] for o in ops]}}, 'R3', 'service group', [g['id']] + [o['id'] for o in ops], why, LOW)
            prj.link('USES_DOMAIN', prc, dom, 'R3', 'service group', [g['id']], 'process candidate', LOW)
    prj.steps.append({'step': 'R3', 'capability_candidates': len(domains), 'process_candidates': sum(1 for x in prj.records['A1'] if x.startswith('PRJ-PRC-'))})


# ------------------------------------------------------------------ orchestration

def project(have, catalogue=None, registry=None, pid=None, created_at=None):
    """have: {'A1': dataset, …} — one or more layers. Returns a projection package dict."""
    mm = Metamodel.load(); prj = Projection(have, catalogue, mm); H = set(have)
    if not H: raise ValueError('AID needs at least one architecture dataset (AID-I01)')
    for name, d in list(have.items()) + ([('catalogue', catalogue)] if catalogue else []):
        issues = LevelGraph(d, mm).validate()  # AID-I01: every input passes the dataset check (CTL-01…03, CTL-16)
        if issues: raise ValueError(f"{name} ({d.get('model_id')}) fails the dataset check: {issues[0]}")
    pid = pid or 'PRJ-' + '-'.join(sorted(H)); created_at = created_at or datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    if 'A2' in H:
        doms = [i['id'] for i in have['A2']['instances'] if i['type'] == 'A2.ServiceDomain']
        if 'A3' not in H: forward_a3_a4(prj, doms, have['A2'], project_a4='A4' not in H)
        if 'A1' not in H: reverse_a1(prj, doms)
    elif not catalogue:
        prj.ends.append('no A2 layer and no BIAN catalogue: nothing can be projected through the BIAN layer')
    elif 'A1' in H and 'A3' in H:  # middle gap — the domains both sides support
        fwd = Projection(have, catalogue, mm); f = set(forward_a2(fwd, have['A1'], registry))
        rev = Projection(have, catalogue, mm); r = set(reverse_a2(rev, have['A3'], have.get('A4'), registry))
        both = sorted(f & r)
        for d in both:
            fr, rr = fwd.records['A2'][d]['projection'], rev.records['A2'][d]['projection']
            prj.take_domain(d, 'M', f"supported from both sides. Business side (F1): {fr['reasoning']}. Application side (R2): {rr['reasoning']}", MEDIUM, fr['inferred_from'] + rr['inferred_from'])
        for side in (fwd, rev):
            for k, l in side.links.items():
                ends = {l['source']['id'], l['target']['id']}
                if ends & set(both) or any(Run(_reader({'A2': catalogue}, mm), 'AID').domain_of(e) and Run(_reader({'A2': catalogue}, mm), 'AID').domain_of(e)['id'] in both for e in ends if e in prj.cat_by_id):
                    src = {'id': l['source']['id'], 'type': l['source']['type'], 'version': l['source']['version']}; tgt = {'id': l['target']['id'], 'type': l['target']['type'], 'version': l['target']['version']}
                    prj.link(l['relationship'], src, tgt, 'M', l['projection']['rule'], l['projection']['inferred_from'], l['projection']['reasoning'], min(l['confidence'] + 0.2, MEDIUM))
        for x, rec in list(fwd.records['A2'].items()) + list(rev.records['A2'].items()):
            if rec['type'] == 'A2.BusinessObject' and x not in prj.records['A2']: prj.record('A2', prj.cat_by_id[x], 'M', CATALOGUE_RULE, rec['projection']['inferred_from'], rec['projection']['reasoning'], rec['projection']['confidence'])
        prj.steps.append({'step': 'M', 'forward_domains': sorted(f), 'reverse_domains': sorted(r), 'kept': both})
        if not both: prj.ends.append('middle gap: the business and application layers point to no common BIAN domain')
        if 'A4' not in H: forward_a4(prj, [])
    elif 'A1' in H:  # forward
        doms = forward_a2(prj, have['A1'], registry)
        if doms and 'A3' not in H:
            a2p = {'level': 'A2', 'model_id': 'aid-selected', 'model_version': 'x', 'metamodel_version': mm.version, 'instances': list(prj.records['A2'].values()), 'relationships': prj.rels['A2']}
            a2p['instances'] = [{k: v for k, v in i.items() if k != 'projection'} for i in a2p['instances']]
            forward_a3_a4(prj, doms, a2p, project_a4='A4' not in H)
    else:  # reverse from A3 and/or A4
        a3 = have.get('A3')
        if a3 is None and 'A4' in H:
            stubs = reverse_a3(prj, have['A4'])
            a3 = {'level': 'A3', 'model_id': 'aid-stubs', 'model_version': 'x', 'metamodel_version': mm.version, 'instances': [{k: v for k, v in s.items() if k != 'projection'} for s in stubs], 'relationships': []}
        doms = reverse_a2(prj, a3, have.get('A4'), registry) if a3 and a3['instances'] else []
        if doms and 'A1' not in H: reverse_a1(prj, doms)
    return prj.package(pid, created_at)


# ------------------------------------------------------------------ package: write, read, check (CTL-17)

def write(pkg, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    for f in out.glob('projected-*.json'): f.unlink()
    (out / 'projection.json').write_text(json.dumps(pkg['projection'], indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    for lvl, d in pkg['layers'].items(): (out / FILES[lvl]).write_text(json.dumps(d, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    (out / 'projected-links.json').write_text(json.dumps(pkg['links'], indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return out


def read(path):
    p = Path(path); layers = {lvl: json.loads((p / f).read_text(encoding='utf-8')) for lvl, f in FILES.items() if (p / f).exists()}
    return {'projection': json.loads((p / 'projection.json').read_text(encoding='utf-8')), 'layers': layers, 'links': json.loads((p / 'projected-links.json').read_text(encoding='utf-8'))}


def check(pkg, catalogue=None):
    """CTL-17: every projected element carries its provenance, is at most medium confidence, and invents no BIAN element."""
    from .validate import check_schema
    issues = [f'schema: {x}' for x in check_schema(pkg, json.loads(SCHEMA.read_text(encoding='utf-8')))]  # AID-O05
    cat = {i['id'] for i in catalogue['instances']} if catalogue else None
    for lvl, d in pkg['layers'].items():
        for i in d['instances']:
            pr = i.get('projection') or {}
            missing = [k for k in PROVENANCE if k not in pr]
            if missing: issues.append(f"{i['id']}: projection provenance missing {missing}")
            if pr.get('confidence', 1) > MEDIUM: issues.append(f"{i['id']}: confidence {pr.get('confidence')} above medium")
            if pr.get('confidence', 0) > LOW and weak(pr.get('reasoning')) and not re.search(r'\b(implements|invokes|BOM attributes)\b', pr.get('reasoning', '')):
                issues.append(f"{i['id']}: name-only evidence above low confidence (AID-B6)")
            if lvl == 'A2' and (pr.get('rule') != CATALOGUE_RULE or (cat is not None and i['id'] not in cat)): issues.append(f"{i['id']}: an A2 element not taken from the BIAN catalogue")
            if lvl != 'A2' and not i['id'].startswith('PRJ-') and pr.get('step') != 'R1': issues.append(f"{i['id']}: a projected record must be marked PRJ-")
    for l in pkg['links']['links']:
        pr = l.get('projection') or {}
        if l.get('status') != 'projected': issues.append(f"{l['mapping_id']}: status must be 'projected'")
        if [k for k in PROVENANCE if k not in pr]: issues.append(f"{l['mapping_id']}: projection provenance missing")
        if l.get('confidence', 1) > MEDIUM: issues.append(f"{l['mapping_id']}: confidence above medium")
        if l.get('confidence', 0) > LOW and weak(pr.get('reasoning')): issues.append(f"{l['mapping_id']}: name-only evidence above low confidence (AID-B6)")
    return issues


# ------------------------------------------------------------------ gap analysis

def gaps(pkg, real, registry):
    """Compare a projection with the real layers and registry (AID-G01…G03). Every projected element gets a result —
    matched / projected only / real only / differs — with its real counterpart and the reason; then the real elements
    AID did not project; then every projected link between real elements; then precision and recall per layer."""
    mm = Metamodel.load(); rows, link_rows, metrics = [], [], {}
    approved = [m for m in registry.get('mappings', []) if m.get('status') == 'approved']
    rel = lambda r: [(m['source']['id'], m['target']['id']) for m in approved if m['relationship'] == r]
    inst = {i['id']: i for d in real.values() for i in d['instances']}
    pnames = {i['id']: i.get('name', i['id']) for d in pkg['layers'].values() for i in d['instances']}
    nm = lambda i: (inst.get(i) or {}).get('name') or pnames.get(i, i)
    run = Run(_reader({'A2': real['A2']}, mm), 'AID') if 'A2' in real else None
    dom = lambda x: x if (inst.get(x) or {}).get('type') == 'A2.ServiceDomain' else ((run.domain_of(x) or {}).get('id') if run and x in inst else None)
    used = {dom(t) for s, t in rel('USES_DOMAIN') + rel('SUPPORTED_BY')} | {dom(s) for r in ('REALIZED_BY', 'IMPLEMENTED_BY', 'MAPPED_TO') for s, _ in rel(r)}
    used.discard(None)
    realised = {}
    for s, c in rel('REALIZED_BY'): realised.setdefault(s, []).append(c)
    impl = dict(rel('IMPLEMENTED_BY'))
    parts = lambda c: [r['target'] for r in real.get('A3', {}).get('relationships', []) if r['kind'] == 'composition' and r['source'] == c and (inst.get(r['target']) or {}).get('type') == 'A3.ApplicationComponent']
    def row(lvl, i, result, real_, reason, by='—'):
        rows.append({'layer': lvl, 'element': i['id'], 'name': i.get('name', i['id']), 'type': i['type'].split('.')[1], 'result': result, 'real': real_, 'reason': reason,
                     'matched_by': by if result != 'projected only' else '—', 'confidence': (i.get('projection') or {}).get('confidence')})
    canon = {}
    for x in real.get('A2', {}).get('instances', []):
        if x.get('canonical_id'): canon[x['canonical_id']] = x['id']
    words = lambda t: {stem(w) for w in tokens(re.sub(r'\(.*?\)', ' ', t or ''))}
    def by_name(name, cands):
        """Real records whose name shares at least two words (stems) and at least half of the projected name's words — a hint, not a match."""
        w = words(name); return [c for c in cands if w and len(w & words(c.get('name'))) >= 2 and len(w & words(c.get('name'))) * 2 >= len(w)]
    a3run = Run(_reader({'A3': real['A3']}, mm), 'AID') if 'A3' in real else None
    L = pkg['layers']; projected_ops = set()
    for i in L.get('A2', {}).get('instances', []):
        if i['type'] == 'A2.ServiceDomain':
            rid = canon.get(i.get('canonical_id')) or (i['id'] if i['id'] in inst else None)
            how = f"BIAN canonical_id {i['canonical_id']}" if i.get('canonical_id') in canon else 'catalogue id'
            if rid in used: row('A2', i, 'matched', f"{rid} {nm(rid)}", 'the real design links business or application records to this domain', how)
            elif rid: row('A2', i, 'projected only', '—', 'the domain is in the real BIAN layer, but the real design links nothing to it')
            else: row('A2', i, 'projected only', '—', 'not in the real design at all')
        else:
            same = inst.get(canon.get(i.get('canonical_id'))) if i.get('canonical_id') in canon else inst.get(i['id'])
            ok = same and same['type'] == i['type'] and (same.get('name') == i.get('name') or i.get('canonical_id') in canon)
            row('A2', i, 'matched' if ok else 'projected only', f"{same['id']} {same.get('name')}" if ok else '—',
                'the same BIAN element is in the real BIAN layer' if ok else 'brought in from the catalogue with its domain; the real BIAN layer does not have it',
                'BIAN canonical_id' if i.get('canonical_id') in canon else 'same type and name')
    for d in sorted(used - {i['id'] for i in L.get('A2', {}).get('instances', [])}) if 'A2' in L else []:
        rows.append({'layer': 'A2', 'element': d, 'name': nm(d), 'type': 'ServiceDomain', 'result': 'real only', 'real': f'{d} {nm(d)}', 'reason': 'the real design uses this domain; AID did not project it', 'confidence': None})
    for i in L.get('A3', {}).get('instances', []):
        if i['type'] == 'A3.ApplicationComponent' and i['id'].startswith('PRJ-APP-'):
            d = i['id'][len('PRJ-APP-'):]; how = 'the BIAN operations its APIs implement'
            ops = [a['projection']['inferred_from'][0] for a in L['A3']['instances'] if a['type'] == 'A3.APIOperation' and any(r['source'] == i['id'] and r['target'] == a['id'] for r in L['A3']['relationships'])]
            hit = sorted({(a3run.component_of(impl[o]) or {}).get('id') for o in ops if o in impl and a3run} - {None})
            if not hit: hit, how = realised.get(d, []), f'the domain it realises ({d})'
            if not hit:
                hit, how = [c['id'] for c in by_name(i['name'], [x for x in real.get('A3', {}).get('instances', []) if x['type'] == 'A3.ApplicationComponent'])], 'name'
            if hit and how == 'name': row('A3', i, 'similar name', ', '.join(f'{c} {nm(c)}' for c in hit), 'no real component realises this domain or implements these operations; a real one has a similar name — a hint, not a match', how)
            elif hit:
                sub = [p for c in hit for p in parts(c)]
                row('A3', i, 'matched' if not sub else 'matched — structure differs', ', '.join(f'{c} {nm(c)}' for c in hit),
                    f'the real component found by {how}' + (f'; the real one is split into {len(sub)} sub-components ({", ".join(nm(p) for p in sub)}), AID projects one' if sub else ''), how)
            else: row('A3', i, 'projected only', '—', f'the real design realises {d} with no component')
        elif i['type'] == 'A3.ApplicationComponent':
            r_ = inst.get(i['id'])
            row('A3', i, 'matched' if r_ else 'projected only', f"{i['id']} {nm(i['id'])}" if r_ else '—',
                'the application exists in the real design' + (f" — its real name is “{r_['name']}”, which A4 does not give" if r_ else '') if r_ else 'A4 names an application the real A3 does not have', 'same id')
        elif i['type'] == 'A3.APIOperation':
            op = i['projection']['inferred_from'][0]; projected_ops.add(op); r_ = inst.get(impl.get(op))
            pf = f"{i['attributes']['method']} {i['attributes']['path']}"
            if not r_: row('A3', i, 'projected only', '—', f'the real design has no API for {op} {nm(op)}' + (' — this operation is not in the real BIAN layer' if op not in inst else '')); continue
            rf = f"{r_['attributes']['method']} {r_['attributes']['path']}"
            why = 'same method and path' if rf == pf else (f"the method differs — AID {i['attributes']['method']}, real {r_['attributes']['method']}" if r_['attributes']['path'] == i['attributes']['path'] else 'the path differs' if r_['attributes']['method'] == i['attributes']['method'] else 'method and path differ')
            row('A3', i, 'matched' if rf == pf else 'differs', f"{r_['id']} {rf}", why, f'the BIAN operation it implements ({op}), then method and path')
    stubs = {i['id'] for i in L.get('A3', {}).get('instances', []) if i['type'] == 'A3.ApplicationComponent' and not i['id'].startswith('PRJ-')}
    if stubs:
        named = {x for i in real.get('A4', {}).get('instances', []) for k in ('hosts', 'component_id', 'of_component') for x in _list((i.get('attributes') or {}).get(k))}
        for c in sorted(named - stubs):
            rows.append({'layer': 'A3', 'element': c, 'name': nm(c), 'type': 'ApplicationComponent', 'result': 'real only', 'real': c, 'reason': 'an A4 record names it; AID did not project it', 'confidence': None})
    if any(i['type'] == 'A3.APIOperation' for i in L.get('A3', {}).get('instances', [])):
        for a in (x for x in real.get('A3', {}).get('instances', []) if x['type'] == 'A3.APIOperation'):
            op = next((o for o, t in impl.items() if t == a['id']), None)
            if op in projected_ops: continue
            rows.append({'layer': 'A3', 'element': a['id'], 'name': f"{a['attributes']['method']} {a['attributes']['path']}", 'type': 'APIOperation', 'result': 'real only', 'real': a['id'],
                         'reason': f'the real API implements {op} {nm(op)}, which AID gave no API' if op else 'the real API implements no BIAN operation, so no rule could project it', 'confidence': None})
    for i in L.get('A4', {}).get('instances', []):
        comp = i['attributes']['component_id']; d = comp[len('PRJ-APP-'):]; hit = realised.get(d, [])
        deps = [x for x in real.get('A4', {}).get('instances', []) if x['type'] == 'A4.Deployment' and (x.get('attributes') or {}).get('component_id') in hit]
        envs = [((x.get('attributes') or {}).get('environment_id') or '?') for x in deps]
        row('A4', i, 'matched' if len(deps) == 1 else 'differs' if deps else 'projected only', ', '.join(x['id'] for x in deps) or '—',
            (f'the real component is deployed {len(deps)} times ({", ".join(envs)}); AID projects one deployment and, by rule, no platform or environment' if len(deps) > 1 else 'one real deployment' if deps else 'no real deployment of the realising component'), 'the component it deploys')
    sup = {}
    for c, d in rel('SUPPORTED_BY'): sup.setdefault(d, []).append(c)
    uses = {}
    for pr_, d in rel('USES_DOMAIN'): uses.setdefault(d, []).append(pr_)
    real_a1 = real.get('A1', {}).get('instances', [])
    for i in L.get('A1', {}).get('instances', []):
        src = i['projection']['inferred_from']
        if i['type'] == 'A1.BusinessCapability':
            d = src[0]; hit, how = sup.get(d, []), f'the domain it points to ({d})'
            if not hit: hit, how = [c['id'] for c in by_name(i['name'], [c for c in real_a1 if c['type'] == 'A1.BusinessCapability'])], 'name'
            row('A1', i, ('similar name' if how == 'name' else 'matched') if hit else 'projected only', ', '.join(f'{c} {nm(c)}' for c in hit) or '—',
                (f'no real capability is supported by {d}; a real one has a similar name — a hint, not a match' if how == 'name' else f'real capability found by {how}: “{nm(hit[0])}” — AID can only suggest one from the domain name') if hit else f'no real capability is supported by {d}, and none has a similar name', how)
        else:
            ops = set((i.get('attributes') or {}).get('invokes', []))
            hit = [p_['id'] for p_ in real_a1 if p_['type'] == 'A1.BusinessProcess' and ops & set((p_.get('attributes') or {}).get('invokes', []))]
            how = 'the BIAN operations it covers'
            if not hit:
                dd = [l['target']['id'] for l in pkg['links']['links'] if l['source']['id'] == i['id']]
                hit, how = [x for d in dd for x in uses.get(d, [])], 'the domain it uses'
            if not hit: hit, how = [c['id'] for c in by_name(i['name'], [c for c in real_a1 if c['type'] == 'A1.BusinessProcess'])], 'name'
            shared = lambda pid: sorted(ops & set((inst[pid].get('attributes') or {}).get('invokes', [])))
            row('A1', i, ('similar name' if how == 'name' else 'matched') if hit else 'projected only', ', '.join(f'{c} {nm(c)}' for c in hit) or '—',
                ('no real process covers these operations or uses the domain; a real one has a similar name — a hint, not a match' if how == 'name' else f'real process(es) found by {how}' + (': ' + '; '.join(f"“{nm(c)}” invokes {', '.join(shared(c))}" for c in hit) if how.startswith('the BIAN') else '')) if hit else 'no real process covers these operations or uses the domain', how)
    real_keys = {(m['source']['id'], m['relationship'], m['target']['id']) for m in approved}
    for l in pkg['links']['links']:
        s_, t_ = l['source']['id'], l['target']['id']
        if s_.startswith('PRJ-') or t_.startswith('PRJ-'): continue
        k = (s_, l['relationship'], t_); ok = k in real_keys
        link_rows.append({'source': s_, 'relationship': l['relationship'], 'target': t_, 'result': 'matched' if ok else 'projected only',
                          'reason': 'the same link is approved in the real registry' if ok else 'no such approved link in the real registry', 'confidence': l['confidence']})
    def tally(name, sel):
        P = [r for r in rows if sel(r) and r['result'] != 'real only']; Rr = [r for r in rows if sel(r) and r['result'] != 'projected only']
        m_ = [r for r in rows if sel(r) and r['result'].startswith('matched')]
        if P or Rr: metrics[name] = {'projected': len(P), 'real': len(Rr), 'matched': len(m_), 'precision': round(len(m_) / len(P), 2) if P else None, 'recall': round(len(m_) / len(Rr), 2) if Rr else None}
    tally('A2 service domains', lambda r: r['layer'] == 'A2' and r['type'] == 'ServiceDomain')
    tally('A3 components', lambda r: r['layer'] == 'A3' and r['type'] == 'ApplicationComponent')
    apis = [r for r in rows if r['type'] == 'APIOperation' and r['result'] != 'real only']
    if apis: metrics['A3 APIs (method and path)'] = {'projected': len(apis), 'compared': sum(r['result'] in ('matched', 'differs') for r in apis), 'matched': sum(r['result'] == 'matched' for r in apis),
                                                    'differs': sum(r['result'] == 'differs' for r in apis), 'projected only': sum(r['result'] == 'projected only' for r in apis),
                                                    'real only': sum(r['type'] == 'APIOperation' and r['result'] == 'real only' for r in rows)}
    tally('A4 deployments', lambda r: r['layer'] == 'A4')
    tally('A1 capability candidates', lambda r: r['layer'] == 'A1' and r['type'] == 'BusinessCapability')
    tally('A1 process candidates', lambda r: r['layer'] == 'A1' and r['type'] == 'BusinessProcess')
    if link_rows:
        Rl = {k for k in real_keys if k[1] in {x['relationship'] for x in link_rows}}; m_ = sum(x['result'] == 'matched' for x in link_rows)
        metrics['links between real elements'] = {'projected': len(link_rows), 'real': len(Rl), 'matched': m_, 'precision': round(m_ / len(link_rows), 2), 'recall': round(m_ / len(Rl), 2) if Rl else None}
    by_rel = {}
    for t in sorted({x['relationship'] for x in link_rows}):
        P = [x for x in link_rows if x['relationship'] == t]; Rl = {k for k in real_keys if k[1] == t}; m_ = sum(x['result'] == 'matched' for x in P)
        by_rel[t] = {'projected': len(P), 'real': len(Rl), 'matched': m_, 'precision': round(m_ / len(P), 2), 'recall': round(m_ / len(Rl), 2) if Rl else None}
    return {'rows': rows, 'links': link_rows, 'metrics': metrics, 'by_relationship': by_rel, 'projection_ends': pkg['projection']['projection_ends']}


def trace(reader, pkg, start, direction='down'):
    """AID-O06: trace across real approved links and projected links; every projected hop and record is labelled.
    Down = towards A4 (link source → target), up = towards A1. Returns text lines."""
    names, level = {}, {}
    for n in reader.nodes(): names[n['id']] = n.get('name', n['id']); level[n['id']] = n['level']
    proj = set()
    for lvl, d in pkg['layers'].items():
        for i in d['instances']:
            if i['id'] not in level: proj.add(i['id'])
            names.setdefault(i['id'], i.get('name', i['id'])); level.setdefault(i['id'], lvl)
    edges = [(e['source']['id'], e['relationship'], e['target']['id'], f"approved {e['mapping_id']}") for e in reader.edges('cross-level')]
    edges += [(l['source']['id'], l['relationship'], l['target']['id'], f"PROJECTED {l['confidence']} · {l['projection']['step']} · {l['projection']['rule']}") for l in pkg['links']['links']]
    tag = lambda x: f"[{level.get(x, '?')}{' PROJECTED' if x in proj else ''}] {x} {names.get(x, '') if names.get(x, x) != x else ''}".rstrip()
    out, seen = [tag(start)], {start}
    def rec(x, prefix):
        nxt = [(r, t, how) for s_, r, t, how in ((e[0], e[1], e[2], e[3]) if direction == 'down' else (e[2], e[1], e[0], e[3]) for e in edges) if s_ == x]
        for k, (r, t, how) in enumerate(nxt):
            last = k == len(nxt) - 1
            out.append(f"{prefix}{'└─ ' if last else '├─ '}{r}{' (reverse)' if direction == 'up' else ''} → {tag(t)}   ({how})")
            if t not in seen: seen.add(t); rec(t, prefix + ('   ' if last else '│  '))
    rec(start, '')
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv and argv[0] not in ('project', 'check', 'gaps', '-h', '--help'):   # DA2-05: `sdem aid` fills the workspace; confirm, reject
        from .aid_fill import main as fill_main
        return fill_main(argv)
    ap = argparse.ArgumentParser(prog='sdem aid', description='Architecture Inference Design: project the missing architecture layers for planning.')
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('project'); p.add_argument('--workspace', dest='estate', metavar='DIR', help="plan from a workspace: its business layer (and any applications and technology), its BIAN layer and its approved connections"); p.add_argument('--have', nargs='+'); p.add_argument('--catalogue'); p.add_argument('--registry'); p.add_argument('-o', '--out', help='where the planned design goes (default with --workspace: <workspace>/plans/PLAN-nnn)'); p.add_argument('--json', action='store_true')
    c = sub.add_parser('check'); c.add_argument('projection'); c.add_argument('--catalogue'); c.add_argument('--json', action='store_true')
    g = sub.add_parser('gaps'); g.add_argument('projection'); g.add_argument('--workspace', dest='estate', metavar='DIR', help="compare with a workspace's real layers and approved connections"); g.add_argument('--actual', nargs='+'); g.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    j = lambda f: json.loads(Path(f).read_text(encoding='utf-8'))
    if a.cmd == 'project' and a.estate:   # WS-05: plan from a workspace; the plan is kept apart in <workspace>/plans/
        ws = Path(a.estate)
        if not (ws / 'mappings.json').exists(): print(f'ERROR: {ws}: no workspace here — start one with sdem new', file=sys.stderr); return 2
        have = {d['level']: d for f in ('a1-business.json', 'a3-application.json', 'a4-technology.json') if (ws / f).exists() for d in [j(ws / f)] if d.get('instances')}
        if 'A1' not in have: print(f'ERROR: {ws}: no business layer (A1) yet — AID plans from what the business does; add it first', file=sys.stderr); return 2
        a.catalogue = a.catalogue or (str(ws / 'a2-service-domain.json') if (ws / 'a2-service-domain.json').exists() else None)
        a.registry = a.registry or str(ws / 'mappings.json')
        if not a.out:
            plans = ws / 'plans'; n = 1 + max([int(x.name.split('-')[1]) for x in plans.glob('PLAN-*') if x.name.split('-')[1].isdigit()] or [0]) if plans.exists() else 1
            a.out = str(plans / f'PLAN-{n:03d}')
    elif a.cmd == 'project':
        if not a.have or not a.out: ap.error('project needs --workspace, or --have and --out')
        have = {j(f)['level']: j(f) for f in a.have}
    if a.cmd == 'project':
        try: pkg = project(have, j(a.catalogue) if a.catalogue else None, j(a.registry) if a.registry else None)
        except ValueError as e: print(f'ERROR: {e}', file=sys.stderr); return 1
        issues = check(pkg, j(a.catalogue) if a.catalogue else None)
        if issues: print('ERROR: ' + '\nERROR: '.join(issues), file=sys.stderr); return 1
        write(pkg, a.out); m = pkg['projection']
        if a.json:
            print(json.dumps({'projection_id': m['projection_id'], 'mode': m['mode'], 'out': str(a.out), 'summary': m['summary'], 'links': m['links'], 'projection_ends': m['projection_ends']}, indent=2, ensure_ascii=False)); return 0
        print(f"projection {m['projection_id']} written to {a.out}: " + ', '.join(f"{l} {s['records']} records" for l, s in m['summary'].items()) + f", {m['links']} links")
        for e in m['projection_ends']: print(f'NOTE: {e}')
        return 0
    if a.cmd == 'check':
        issues = check(read(a.projection), j(a.catalogue) if a.catalogue else None)
        if a.json: print(json.dumps({'valid': not issues, 'issues': issues}, indent=2)); return 1 if issues else 0
        for i in issues: print(f'ERROR: {i}')
        print('projection valid' if not issues else f'{len(issues)} issue(s)'); return 1 if issues else 0
    real, reg = {}, _registry()
    if a.estate:
        ws = Path(a.estate)
        a.actual = [str(ws / f) for f in ('a2-service-domain.json', 'a3-application.json', 'a4-technology.json', 'mappings.json') if (ws / f).exists()]
    if not a.actual: ap.error('gaps needs --workspace or --actual')
    for f in a.actual:
        d = j(f)
        if 'mappings' in d: reg = d
        else: real[d['level']] = d
    res = gaps(read(a.projection), real, reg)
    if a.json: print(json.dumps(res, indent=2)); return 0
    for k, v in res['metrics'].items(): print(f'{k}: {v}')
    for r in res['rows']: print(f"  {r['result']:<15} {r['layer']} {r['element']} {r['name']} — {r['reason']}")
    for r in res['links']: print(f"  {r['result']:<15} link {r['source']} {r['relationship']} {r['target']} — {r['reason']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
