"""Architecture Inference Design (AID) — docs/aid-design.md, docs/aid-spec.md.

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
Usage: sdem-aid project --have a1.json [...] --catalogue bian.json --out DIR · sdem-aid check DIR · sdem-aid gaps DIR --actual a*.json mappings.json
"""
import argparse, datetime, hashlib, json, re, sys
from pathlib import Path

from .graph import FederatedGraph, LevelGraph
from .metamodel import Metamodel
from .rules_engine import Run, RulesEngine, _list
from .store import GraphReader
from .validate import load_registry

MEDIUM, LOW = 0.6, 0.4
FILES = {'A1': 'projected-a1-business.json', 'A2': 'projected-a2-service-domain.json', 'A3': 'projected-a3-application.json', 'A4': 'projected-a4-technology.json'}
CATALOGUE_RULE = 'BIAN catalogue reference'
PROVENANCE = ('step', 'rule', 'inferred_from', 'reasoning', 'confidence')


def _registry(maps=()): return {'registry_version': load_registry()['$schema_version'], 'metamodel_version': '0.4.0', 'mappings': list(maps)}
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
        r = dict(rec); r['projection'] = {'step': step, 'rule': rule, 'inferred_from': inferred_from, 'reasoning': reasoning, 'confidence': min(conf, MEDIUM)}
        self.records[lvl][rec['id']] = r; return r

    def link(self, rel, src, tgt, step, rule, inferred_from, reasoning, conf):
        k = (src['id'], rel, tgt['id'])
        if k in self.links:
            l = self.links[k]; l['projection']['confidence'] = max(l['projection']['confidence'], min(conf, MEDIUM)); return l
        l = {'mapping_id': f'PRJ-L-{len(self.links) + 1:03d}', 'source': _ref(src), 'relationship': rel, 'target': _ref(tgt), 'status': 'projected', 'confidence': min(conf, MEDIUM),
             'rationale': f'PROJECTED DESIGN, not a mapping: {reasoning}', 'projection': {'step': step, 'rule': rule, 'inferred_from': inferred_from, 'reasoning': reasoning, 'confidence': min(conf, MEDIUM)}}
        self.links[k] = l; return l

    # -- BIAN references: a selected domain brings its catalogue structure, never anything invented
    def take_domain(self, dom_id, step, why, conf):
        cat = self.cat_by_id; rels = self.cat.get('relationships', [])
        keep = [dom_id]; todo = [dom_id]
        while todo:
            x = todo.pop()
            for r in rels:
                if r['source'] == x and r['kind'] in ('composition', 'aggregation', 'association') and r['target'] not in keep and cat.get(r['target']) and cat[r['target']]['type'] != 'A2.ServiceDomain':
                    keep.append(r['target']); todo.append(r['target'])
        for x in keep:
            self.record('A2', cat[x], step, CATALOGUE_RULE, [dom_id], why if x == dom_id else f'part of {dom_id} in the BIAN catalogue', conf)
        for r in rels:
            if r['source'] in keep and r['target'] in keep and r not in self.rels['A2']: self.rels['A2'].append(r)

    def package(self, pid, created_at):
        layers = {}
        for lvl, recs in self.records.items():
            if not recs: continue
            layers[lvl] = {'level': lvl, 'model_id': f'{pid}-{lvl.lower()}-PROJECTION', 'model_version': 'projection', 'metamodel_version': self.mm.version,
                           'source_system': 'AID-PROJECTION (sdem-aid; not a real architecture dataset)', 'instances': list(recs.values()), 'relationships': self.rels[lvl]}
        H = set(self.have)
        mode = 'forward' if min(H) == 'A1' and not ({'A1', 'A3'} <= H and 'A2' not in H) and max(H) <= 'A2' else 'middle' if {'A1', 'A3'} <= H and 'A2' not in H else 'reverse' if min(H) >= 'A3' else 'forward and reverse'
        meta = {'projection_id': pid, 'mode': mode, 'created_by': 'sdem-aid', 'created_at': created_at, 'metamodel_version': self.mm.version,
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
        best = max(x['confidence'] for x in why)
        prj.take_domain(d, 'F1', '; '.join(sorted({x['evidence'][0].replace('engine_rationale:', '') for x in why}))[:300], best)
    for m in props:
        if m['target']['id'] in prj.records['A2'] or m['target']['id'] in prj.cat_by_id and m['target']['id'] in doms:
            src = next(i for i in a1['instances'] if i['id'] == m['source']['id']); tgt = prj.cat_by_id[m['target']['id']]
            if m['target']['id'] not in prj.records['A2']: prj.take_domain(m['target']['id'], 'F1', m['rationale'], m['confidence'])
            prj.link(m['relationship'], src, tgt, 'F1', m['evidence'][0].split(' ')[0].replace('engine_rationale:', ''), [m['source']['id']], m['rationale'], m['confidence'])
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
        prj.take_domain(d, 'R2', '; '.join(sorted({x['evidence'][0].replace('engine_rationale:', '')[:160] for x in why})), max(x['confidence'] for x in why))
    a3_ids = {i['id']: i for i in a3['instances']}
    for m in props:
        s, t = m['source']['id'], m['target']['id']
        if m['relationship'] in ('IMPLEMENTED_BY', 'REALIZED_BY', 'MAPPED_TO') and s in prj.cat_by_id and t in a3_ids:
            if m['relationship'] == 'IMPLEMENTED_BY':
                dom = Run(_reader({'A2': prj.cat}, prj.mm), 'AID').domain_of(s)
                if dom and dom['id'] not in prj.records['A2']: prj.take_domain(dom['id'], 'R2', f'its operation {s} is implemented by {t}', m['confidence'])
            if m['relationship'] == 'MAPPED_TO' and s not in prj.records['A2']:
                prj.record('A2', prj.cat_by_id[s], 'R2', CATALOGUE_RULE, [t], f'business object mapped from data entity {t}', m['confidence'])
            prj.link(m['relationship'], prj.cat_by_id[s], a3_ids[t], 'R2', m['evidence'][0].split(' ')[0].replace('engine_rationale:', ''), [t], m['rationale'], m['confidence'])
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
            prj.take_domain(d['id'], 'R2', why, LOW)
            prj.link('REALIZED_BY', d, st, 'R2', 'name (id words)', [st['id']], why, LOW)


def reverse_a1(prj, domains):
    """R3 — one capability candidate per domain: the weakest step (BIAN publishes no capability-to-domain mapping)."""
    for d in domains:
        dom = prj.cat_by_id.get(d) or prj.records['A2'].get(d)
        if not dom: continue
        cap = prj.record('A1', {'id': f'PRJ-CAP-{d}', 'type': 'A1.BusinessCapability', 'version': '1.0', 'name': f"{_clean(dom['name'])} (capability candidate)", 'lifecycle_status': 'planned'},
                         'R3', 'domain name', [d], f"a business capability is likely to be supported by {_clean(dom['name'])}; BIAN publishes no capability mapping, so this is a candidate only", LOW)
        prj.link('SUPPORTED_BY', cap, dom, 'R3', 'domain name', [d], 'capability candidate', LOW)
    prj.steps.append({'step': 'R3', 'capability_candidates': len(domains)})


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
            prj.take_domain(d, 'M', 'supported from both sides: the business layer (F1) and the application layer (R2)', MEDIUM)
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
    issues = []; cat = {i['id'] for i in catalogue['instances']} if catalogue else None
    for lvl, d in pkg['layers'].items():
        for i in d['instances']:
            pr = i.get('projection') or {}
            missing = [k for k in PROVENANCE if k not in pr]
            if missing: issues.append(f"{i['id']}: projection provenance missing {missing}")
            if pr.get('confidence', 1) > MEDIUM: issues.append(f"{i['id']}: confidence {pr.get('confidence')} above medium")
            if lvl == 'A2' and (pr.get('rule') != CATALOGUE_RULE or (cat is not None and i['id'] not in cat)): issues.append(f"{i['id']}: an A2 element not taken from the BIAN catalogue")
            if lvl != 'A2' and not i['id'].startswith('PRJ-') and pr.get('step') != 'R1': issues.append(f"{i['id']}: a projected record must be marked PRJ-")
    for l in pkg['links']['links']:
        pr = l.get('projection') or {}
        if l.get('status') != 'projected': issues.append(f"{l['mapping_id']}: status must be 'projected'")
        if [k for k in PROVENANCE if k not in pr]: issues.append(f"{l['mapping_id']}: projection provenance missing")
        if l.get('confidence', 1) > MEDIUM: issues.append(f"{l['mapping_id']}: confidence above medium")
    return issues


# ------------------------------------------------------------------ gap analysis

def gaps(pkg, real, registry):
    """Compare a projection with the real layers and registry: per layer, matched / projected only / real only / differs."""
    mm = Metamodel.load(); rows = []; metrics = {}
    approved = [m for m in registry.get('mappings', []) if m.get('status') == 'approved']
    real_by_id = {i['id']: (lvl, i) for lvl, d in real.items() for i in d['instances']}
    used_domains = {m['target']['id'] for m in approved if m['relationship'] in ('USES_DOMAIN', 'SUPPORTED_BY')} | {m['source']['id'] for m in approved if m['relationship'] in ('REALIZED_BY', 'MAPPED_TO')} \
        | {e['id'] for m in approved if m['relationship'] == 'IMPLEMENTED_BY' for e in (m['source'],)}
    run = Run(_reader({'A2': real['A2']}, mm), 'AID') if 'A2' in real else None
    used_domains = {d if (real_by_id.get(d, (None, {}))[1].get('type') == 'A2.ServiceDomain') else ((run.domain_of(d) or {}).get('id') if run else None) for d in used_domains} - {None}
    def tally(name, P, R):
        m_ = P & R; metrics[name] = {'projected': len(P), 'real': len(R), 'matched': len(m_), 'precision': round(len(m_) / len(P), 2) if P else None, 'recall': round(len(m_) / len(R), 2) if R else None}
        for x in sorted(m_): rows.append({'layer': name, 'element': x, 'result': 'matched'})
        for x in sorted(P - R): rows.append({'layer': name, 'element': x, 'result': 'projected only'})
        for x in sorted(R - P): rows.append({'layer': name, 'element': x, 'result': 'real only'})
    layers = pkg['layers']
    if 'A2' in layers:
        tally('A2 service domains (those the real design links)', {i['id'] for i in layers['A2']['instances'] if i['type'] == 'A2.ServiceDomain'}, used_domains)
    if 'A3' in layers:
        real_real = {(m['source']['id'], m['target']['id']) for m in approved if m['relationship'] == 'REALIZED_BY'}
        P, R = set(), {c for _, c in real_real}
        for i in layers['A3']['instances']:
            if i['type'] != 'A3.ApplicationComponent': continue
            if i['id'].startswith('PRJ-APP-'):
                d = i['id'][len('PRJ-APP-'):]; hit = sorted(c for s, c in real_real if s == d)
                P.add(hit[0] if hit else i['id'])
            else: P.add(i['id'])
        if any(i['id'].startswith('PRJ-APP-') for i in layers['A3']['instances']):
            tally('A3 components (realising a domain)', P, R)
        else:
            Rn = {i['id'] for i in real.get('A3', {'instances': []})['instances'] if i['type'] == 'A3.ApplicationComponent' and any(i['id'] in _list((x.get('attributes') or {}).get(k)) for x in real.get('A4', {'instances': []})['instances'] for k in ('hosts', 'component_id', 'of_component'))}
            tally('A3 components (named by A4)', P, Rn)
        apis = [i for i in layers['A3']['instances'] if i['type'] == 'A3.APIOperation']
        if apis:
            impl = {m['source']['id']: m['target']['id'] for m in approved if m['relationship'] == 'IMPLEMENTED_BY'}
            match = differs = 0
            for a in apis:
                op = a['projection']['inferred_from'][0]; r = real_by_id.get(impl.get(op), (None, None))[1]
                pf = f"{a['attributes']['method']} {a['attributes']['path']}"
                if r:
                    rf = f"{r['attributes']['method']} {r['attributes']['path']}"; ok = rf == pf; match += ok; differs += not ok
                    rows.append({'layer': 'A3 APIs', 'element': f'{op}: projected {pf} · real {rf}', 'result': 'matched' if ok else 'differs'})
            metrics['A3 APIs (method and path)'] = {'compared': match + differs, 'matched': match, 'differs': differs}
    if 'A1' in layers:
        sup = {m['target']['id'] for m in approved if m['relationship'] == 'SUPPORTED_BY'}
        P = {i['projection']['inferred_from'][0] for i in layers['A1']['instances']}
        tally('A1 capability candidates (by the domain they point to)', P, sup)
    # links whose both ends are real elements
    real_keys = {(m['source']['id'], m['relationship'], m['target']['id']) for m in approved}
    proj_keys = {(l['source']['id'], l['relationship'], l['target']['id']) for l in pkg['links']['links'] if not l['source']['id'].startswith('PRJ-') and not l['target']['id'].startswith('PRJ-')}
    rels = {k[1] for k in proj_keys}
    if proj_keys:
        R = {k for k in real_keys if k[1] in rels}; m_ = proj_keys & R
        metrics['links between real elements'] = {'projected': len(proj_keys), 'real': len(R), 'matched': len(m_), 'precision': round(len(m_) / len(proj_keys), 2), 'recall': round(len(m_) / len(R), 2) if R else None}
    return {'rows': rows, 'metrics': metrics, 'projection_ends': pkg['projection']['projection_ends']}


def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem-aid', description='Architecture Inference Design: project the missing architecture layers for planning.')
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('project'); p.add_argument('--have', nargs='+', required=True); p.add_argument('--catalogue'); p.add_argument('--registry'); p.add_argument('--out', required=True)
    c = sub.add_parser('check'); c.add_argument('projection'); c.add_argument('--catalogue')
    g = sub.add_parser('gaps'); g.add_argument('projection'); g.add_argument('--actual', nargs='+', required=True); g.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    j = lambda f: json.loads(Path(f).read_text(encoding='utf-8'))
    if a.cmd == 'project':
        have = {j(f)['level']: j(f) for f in a.have}
        try: pkg = project(have, j(a.catalogue) if a.catalogue else None, j(a.registry) if a.registry else None)
        except ValueError as e: print(f'ERROR: {e}', file=sys.stderr); return 1
        issues = check(pkg, j(a.catalogue) if a.catalogue else None)
        if issues: print('ERROR: ' + '\nERROR: '.join(issues), file=sys.stderr); return 1
        write(pkg, a.out); m = pkg['projection']
        print(f"projection {m['projection_id']} written to {a.out}: " + ', '.join(f"{l} {s['records']} records" for l, s in m['summary'].items()) + f", {m['links']} links")
        for e in m['projection_ends']: print(f'NOTE: {e}')
        return 0
    if a.cmd == 'check':
        issues = check(read(a.projection), j(a.catalogue) if a.catalogue else None)
        for i in issues: print(f'ERROR: {i}')
        print('projection valid' if not issues else f'{len(issues)} issue(s)'); return 1 if issues else 0
    real, reg = {}, _registry()
    for f in a.actual:
        d = j(f)
        if 'mappings' in d: reg = d
        else: real[d['level']] = d
    res = gaps(read(a.projection), real, reg)
    if a.json: print(json.dumps(res, indent=2)); return 0
    for k, v in res['metrics'].items(): print(f'{k}: {v}')
    for r in res['rows']: print(f"  {r['result']:<15} {r['layer']}: {r['element']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
