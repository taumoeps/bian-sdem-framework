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
from .identity import for_file as _for_file  # DL-11: what a design's file stores (docs/design/sdem-data-layer-spec.md)
from .identity import load as _jload  # DL-11: a design's files read through one boundary (docs/design/sdem-data-layer-spec.md)
from .identity import T as _T, layer as _L, F as _F, live as _live  # ST-01…ST-05: layers and types by id (docs/design/sdem-stable-identity-spec.md)
import argparse, datetime, hashlib, json, re, sys
from pathlib import Path

from .graph import FederatedGraph, LevelGraph
from .metamodel import Metamodel
from .rules_engine import Run, RulesEngine, WEAK_CLASSES, _list, _rules, stem, stems, strongest, tokens, weakest
from .store import GraphReader
from .validate import load_registry

MEDIUM, LOW = 0.6, 0.4
from .paths import DATA_ROOT as _DATA_ROOT
SCHEMA = _DATA_ROOT / 'schema' / 'projection.schema.json'
FILES = _live(lambda: {_L('business'): 'projected-a1-business.json', _L('bian'): 'projected-a2-service-domain.json', _L('data'): 'projected-a3-data.json', _L('application'): 'projected-a3-application.json', _L('technology'): 'projected-a4-technology.json'})
CATALOGUE_RULE = 'BIAN catalogue reference'
PROVENANCE = ('step', 'rule', 'source_reference', 'inferred_from', 'reasoning', 'confidence')




NAME_ONLY = re.compile(r'fallback|step5|verb and noun match|contains \[.*\], which begin words')


def weak(text):
    """AID-B6: evidence that rests on names alone — an engine fallback (e.g. S17 fallback B: one asset-type word in API
    paths), a description match (step 5), a verb-and-noun name match, or the id-word fallback. Never above low.
    Used only where no evidence class is recorded (a package from before AID-E01)."""
    return bool(NAME_ONLY.search(text or ''))


def is_weak(item):
    """AID-B6 by evidence class (AID-E01): a name or a description, nothing more. Older items without a class: by their text."""
    c = item.get('evidence_class') or (item.get('projection') or {}).get('evidence_class')
    return c in WEAK_CLASSES if c else all(weak(e) for e in item.get('evidence') or [(item.get('projection') or {}).get('reasoning', '')])


def conf_of(item):
    """An engine proposal's confidence, capped at low when its evidence is name-only (AID-B6)."""
    return min(item['confidence'], LOW) if is_weak(item) else item['confidence']








def _registry(maps=()): return {'registry_version': load_registry()['$schema_version'], 'metamodel_version': Metamodel.load().version, 'mappings': list(maps)}




def _reader(levels, mm, registry=None):
    return GraphReader(FederatedGraph([LevelGraph(d, mm) for d in levels.values()], [registry or _registry()], mm), 'aid')




# ------------------------------------------------------------------ steps





















# ------------------------------------------------------------------ orchestration



# ------------------------------------------------------------------ package: write, read, check (CTL-17)

def write(pkg, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    for f in out.glob('projected-*.json'): f.unlink()
    (out / 'projection.json').write_text(json.dumps(_for_file(out / 'projection.json', pkg['projection']), indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    for lvl, d in pkg['layers'].items(): (out / FILES[lvl]).write_text(json.dumps(_for_file(out / FILES[lvl], d), indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    (out / 'projected-links.json').write_text(json.dumps(_for_file(out / 'projected-links.json', pkg['links']), indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return out


def read(path):
    p = Path(path); layers = {lvl: _jload(p / f) for lvl, f in FILES.items() if (p / f).exists()}
    return {'projection': _jload(p / 'projection.json'), 'layers': layers, 'links': _jload(p / 'projected-links.json')}


def check(pkg, catalogue=None):
    """CTL-17: every projected element carries its provenance, is at most medium confidence, and invents no BIAN element."""
    from .validate import check_schema
    issues = [f'schema: {x}' for x in check_schema(pkg, _jload(SCHEMA))]  # AID-O05
    cat = {i['id'] for i in catalogue['instances']} if catalogue else None
    for lvl, d in pkg['layers'].items():
        for i in d['instances']:
            pr = i.get('projection') or {}
            missing = [k for k in PROVENANCE if k not in pr]
            if missing: issues.append(f"{i['id']}: projection provenance missing {missing}")
            if pr.get('confidence', 1) > MEDIUM: issues.append(f"{i['id']}: confidence {pr.get('confidence')} above medium")
            name_only = pr['evidence_class'] in WEAK_CLASSES if pr.get('evidence_class') else (weak(pr.get('reasoning')) and not re.search(r'\b(implements|invokes|BOM attributes)\b', pr.get('reasoning', '')))
            if pr.get('confidence', 0) > LOW and name_only:
                issues.append(f"{i['id']}: name-only evidence above low confidence (AID-B6)")
            if lvl == _L('bian') and (pr.get('rule') != CATALOGUE_RULE or (cat is not None and i['id'] not in cat)): issues.append(f"{i['id']}: an {_L('bian')} element not taken from the BIAN catalogue")
            if lvl != _L('bian') and not i['id'].startswith('PRJ-') and pr.get('step') != 'R1': issues.append(f"{i['id']}: a projected record must be marked PRJ-")
    for l in pkg['links']['links']:
        pr = l.get('projection') or {}
        if l.get('status') != 'projected': issues.append(f"{l['mapping_id']}: status must be 'projected'")
        if [k for k in PROVENANCE if k not in pr]: issues.append(f"{l['mapping_id']}: projection provenance missing")
        if l.get('confidence', 1) > MEDIUM: issues.append(f"{l['mapping_id']}: confidence above medium")
        if l.get('confidence', 0) > LOW and (pr['evidence_class'] in WEAK_CLASSES if pr.get('evidence_class') else weak(pr.get('reasoning'))): issues.append(f"{l['mapping_id']}: name-only evidence above low confidence (AID-B6)")
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
    run = Run(_reader({_L('bian'): real[_L('bian')]}, mm), 'AID') if _L('bian') in real else None
    dom = lambda x: x if (inst.get(x) or {}).get('type') == _T('bian.ServiceDomain') else ((run.climb(x, _T('bian.ServiceDomain'), _L('bian')) or {}).get('id') if run and x in inst else None)   # the core's climb (BIAN's domain_of)
    used = {dom(t) for s, t in rel('USES_DOMAIN') + rel('SUPPORTED_BY')} | {dom(s) for r in ('REALIZED_BY', 'IMPLEMENTED_BY', 'MAPPED_TO') for s, _ in rel(r)}
    used.discard(None)
    realised = {}
    for s, c in rel('REALIZED_BY'): realised.setdefault(s, []).append(c)
    impl = dict(rel('IMPLEMENTED_BY'))
    parts = lambda c: [r['target'] for r in real.get(_L('application'), {}).get('relationships', []) if r['kind'] == 'composition' and r['source'] == c and (inst.get(r['target']) or {}).get('type') == _T('application.ApplicationComponent')]
    def row(lvl, i, result, real_, reason, by='—'):
        rows.append({'layer': lvl, 'element': i['id'], 'name': i.get('name', i['id']), 'type': i['type'].split('.')[1], 'result': result, 'real': real_, 'reason': reason,
                     'matched_by': by if result != 'projected only' else '—', 'confidence': (i.get('projection') or {}).get('confidence')})
    canon = {}
    for x in real.get(_L('bian'), {}).get('instances', []):
        if x.get('canonical_id'): canon[x['canonical_id']] = x['id']
    words = lambda t: {stem(w) for w in tokens(re.sub(r'\(.*?\)', ' ', t or ''))}
    def by_name(name, cands):
        """Real records whose name shares at least two words (stems) and at least half of the projected name's words — a hint, not a match."""
        w = words(name); return [c for c in cands if w and len(w & words(c.get('name'))) >= 2 and len(w & words(c.get('name'))) * 2 >= len(w)]
    a3run = Run(_reader({_L('application'): real[_L('application')]}, mm), 'AID') if _L('application') in real else None
    L = pkg['layers']; projected_ops = set()
    for i in L.get(_L('bian'), {}).get('instances', []):
        if i['type'] == _T('bian.ServiceDomain'):
            rid = canon.get(i.get('canonical_id')) or (i['id'] if i['id'] in inst else None)
            how = f"BIAN canonical_id {i['canonical_id']}" if i.get('canonical_id') in canon else 'catalogue id'
            if rid in used: row(_L('bian'), i, 'matched', f"{rid} {nm(rid)}", 'the real design links business or application records to this domain', how)
            elif rid: row(_L('bian'), i, 'projected only', '—', 'the domain is in the real BIAN layer, but the real design links nothing to it')
            else: row(_L('bian'), i, 'projected only', '—', 'not in the real design at all')
        else:
            same = inst.get(canon.get(i.get('canonical_id'))) if i.get('canonical_id') in canon else inst.get(i['id'])
            ok = same and same['type'] == i['type'] and (same.get('name') == i.get('name') or i.get('canonical_id') in canon)
            row(_L('bian'), i, 'matched' if ok else 'projected only', f"{same['id']} {same.get('name')}" if ok else '—',
                'the same BIAN element is in the real BIAN layer' if ok else 'brought in from the catalogue with its domain; the real BIAN layer does not have it',
                'BIAN canonical_id' if i.get('canonical_id') in canon else 'same type and name')
    for d in sorted(used - {i['id'] for i in L.get(_L('bian'), {}).get('instances', [])}) if _L('bian') in L else []:
        rows.append({'layer': _L('bian'), 'element': d, 'name': nm(d), 'type': 'ServiceDomain', 'result': 'real only', 'real': f'{d} {nm(d)}', 'reason': 'the real design uses this domain; AID did not project it', 'confidence': None})
    for i in L.get(_L('application'), {}).get('instances', []):
        if i['type'] == _T('application.ApplicationComponent') and i['id'].startswith('PRJ-APP-'):
            d = i['id'][len('PRJ-APP-'):]; how = 'the BIAN operations its APIs implement'
            ops = [a['projection']['inferred_from'][0] for a in L[_L('application')]['instances'] if a['type'] == _T('application.APIOperation') and any(r['source'] == i['id'] and r['target'] == a['id'] for r in L[_L('application')]['relationships'])]
            hit = sorted({(a3run.component_of(impl[o]) or {}).get('id') for o in ops if o in impl and a3run} - {None})
            if not hit: hit, how = realised.get(d, []), f'the domain it realises ({d})'
            if not hit:
                hit, how = [c['id'] for c in by_name(i['name'], [x for x in real.get(_L('application'), {}).get('instances', []) if x['type'] == _T('application.ApplicationComponent')])], 'name'
            if hit and how == 'name': row(_L('application'), i, 'similar name', ', '.join(f'{c} {nm(c)}' for c in hit), 'no real component realises this domain or implements these operations; a real one has a similar name — a hint, not a match', how)
            elif hit:
                sub = [p for c in hit for p in parts(c)]
                row(_L('application'), i, 'matched' if not sub else 'matched — structure differs', ', '.join(f'{c} {nm(c)}' for c in hit),
                    f'the real component found by {how}' + (f'; the real one is split into {len(sub)} sub-components ({", ".join(nm(p) for p in sub)}), AID projects one' if sub else ''), how)
            else: row(_L('application'), i, 'projected only', '—', f'the real design realises {d} with no component')
        elif i['type'] == _T('application.ApplicationComponent'):
            r_ = inst.get(i['id'])
            row(_L('application'), i, 'matched' if r_ else 'projected only', f"{i['id']} {nm(i['id'])}" if r_ else '—',
                'the application exists in the real design' + (f" — its real name is “{r_['name']}”, which {_L('technology')} does not give" if r_ else '') if r_ else f'{_L("technology")} names an application the real {_L("application")} does not have', 'same id')
        elif i['type'] == _T('application.APIOperation'):
            op = i['projection']['inferred_from'][0]; projected_ops.add(op); r_ = inst.get(impl.get(op))
            pf = f"{i['attributes']['method']} {i['attributes']['path']}"
            if not r_: row(_L('application'), i, 'projected only', '—', f'the real design has no API for {op} {nm(op)}' + (' — this operation is not in the real BIAN layer' if op not in inst else '')); continue
            rf = f"{r_['attributes']['method']} {r_['attributes']['path']}"
            why = 'same method and path' if rf == pf else (f"the method differs — AID {i['attributes']['method']}, real {r_['attributes']['method']}" if r_['attributes']['path'] == i['attributes']['path'] else 'the path differs' if r_['attributes']['method'] == i['attributes']['method'] else 'method and path differ')
            row(_L('application'), i, 'matched' if rf == pf else 'differs', f"{r_['id']} {rf}", why, f'the BIAN operation it implements ({op}), then method and path')
    stubs = {i['id'] for i in L.get(_L('application'), {}).get('instances', []) if i['type'] == _T('application.ApplicationComponent') and not i['id'].startswith('PRJ-')}
    if stubs:
        named = {x for i in real.get(_L('technology'), {}).get('instances', []) for k in ('hosts', 'component_id', 'of_component') for x in _list((i.get('attributes') or {}).get(k))}
        for c in sorted(named - stubs):
            rows.append({'layer': _L('application'), 'element': c, 'name': nm(c), 'type': 'ApplicationComponent', 'result': 'real only', 'real': c, 'reason': f'an {_L("technology")} record names it; AID did not project it', 'confidence': None})
    if any(i['type'] == _T('application.APIOperation') for i in L.get(_L('application'), {}).get('instances', [])):
        for a in (x for x in real.get(_L('application'), {}).get('instances', []) if x['type'] == _T('application.APIOperation')):
            op = next((o for o, t in impl.items() if t == a['id']), None)
            if op in projected_ops: continue
            rows.append({'layer': _L('application'), 'element': a['id'], 'name': f"{a['attributes']['method']} {a['attributes']['path']}", 'type': 'APIOperation', 'result': 'real only', 'real': a['id'],
                         'reason': f'the real API implements {op} {nm(op)}, which AID gave no API' if op else 'the real API implements no BIAN operation, so no rule could project it', 'confidence': None})
    for i in L.get(_L('technology'), {}).get('instances', []):
        comp = i['attributes']['component_id']; d = comp[len('PRJ-APP-'):]; hit = realised.get(d, [])
        deps = [x for x in real.get(_L('technology'), {}).get('instances', []) if x['type'] == _T('technology.Deployment') and (x.get('attributes') or {}).get('component_id') in hit]
        envs = [((x.get('attributes') or {}).get('environment_id') or '?') for x in deps]
        row(_L('technology'), i, 'matched' if len(deps) == 1 else 'differs' if deps else 'projected only', ', '.join(x['id'] for x in deps) or '—',
            (f'the real component is deployed {len(deps)} times ({", ".join(envs)}); AID projects one deployment and, by rule, no platform or environment' if len(deps) > 1 else 'one real deployment' if deps else 'no real deployment of the realising component'), 'the component it deploys')
    sup = {}
    for c, d in rel('SUPPORTED_BY'): sup.setdefault(d, []).append(c)
    uses = {}
    for pr_, d in rel('USES_DOMAIN'): uses.setdefault(d, []).append(pr_)
    real_a1 = real.get(_L('business'), {}).get('instances', [])
    for i in L.get(_L('business'), {}).get('instances', []):
        src = i['projection']['inferred_from']
        if i['type'] == _T('business.BusinessCapability'):
            d = src[0]; hit, how = sup.get(d, []), f'the domain it points to ({d})'
            if not hit: hit, how = [c['id'] for c in by_name(i['name'], [c for c in real_a1 if c['type'] == _T('business.BusinessCapability')])], 'name'
            row(_L('business'), i, ('similar name' if how == 'name' else 'matched') if hit else 'projected only', ', '.join(f'{c} {nm(c)}' for c in hit) or '—',
                (f'no real capability is supported by {d}; a real one has a similar name — a hint, not a match' if how == 'name' else f'real capability found by {how}: “{nm(hit[0])}” — AID can only suggest one from the domain name') if hit else f'no real capability is supported by {d}, and none has a similar name', how)
        else:
            ops = set((i.get('attributes') or {}).get('invokes', []))
            hit = [p_['id'] for p_ in real_a1 if p_['type'] == _T('business.BusinessProcess') and ops & set((p_.get('attributes') or {}).get('invokes', []))]
            how = 'the BIAN operations it covers'
            if not hit:
                dd = [l['target']['id'] for l in pkg['links']['links'] if l['source']['id'] == i['id']]
                hit, how = [x for d in dd for x in uses.get(d, [])], 'the domain it uses'
            if not hit: hit, how = [c['id'] for c in by_name(i['name'], [c for c in real_a1 if c['type'] == _T('business.BusinessProcess')])], 'name'
            shared = lambda pid: sorted(ops & set((inst[pid].get('attributes') or {}).get('invokes', [])))
            row(_L('business'), i, ('similar name' if how == 'name' else 'matched') if hit else 'projected only', ', '.join(f'{c} {nm(c)}' for c in hit) or '—',
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
    tally(f'{_L("bian")} service domains', lambda r: r['layer'] == _L('bian') and r['type'] == 'ServiceDomain')
    tally(f'{_L("application")} components', lambda r: r['layer'] == _L('application') and r['type'] == 'ApplicationComponent')
    apis = [r for r in rows if r['type'] == 'APIOperation' and r['result'] != 'real only']
    if apis: metrics[f'{_L("application")} APIs (method and path)'] = {'projected': len(apis), 'compared': sum(r['result'] in ('matched', 'differs') for r in apis), 'matched': sum(r['result'] == 'matched' for r in apis),
                                                    'differs': sum(r['result'] == 'differs' for r in apis), 'projected only': sum(r['result'] == 'projected only' for r in apis),
                                                    'real only': sum(r['type'] == 'APIOperation' and r['result'] == 'real only' for r in rows)}
    tally(f'{_L("technology")} deployments', lambda r: r['layer'] == _L('technology'))
    tally(f'{_L("business")} capability candidates', lambda r: r['layer'] == _L('business') and r['type'] == 'BusinessCapability')
    tally(f'{_L("business")} process candidates', lambda r: r['layer'] == _L('business') and r['type'] == 'BusinessProcess')
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


def _project(workspace, have, catalogue, registry):
    """AID's projection package (AID-F1…F3, R1…R3, M) — BIAN's part of AID, from the installed sdem-bian (MX-54, BX-15): its projection
    phase with this catalogue, keeping only what both sides support (either=False), as `sdem aid project` always did."""
    import tempfile
    from .aid_fill import _bian
    with tempfile.TemporaryDirectory() as t:
        ws = Path(workspace) if workspace else Path(t)   # outside a workspace: an empty folder (BIAN on where sdem-bian is installed, BX-12)
        from . import profile as _p, parts
        if workspace: _p.activate_from(ws)
        else: _p.deactivate(); (ws / parts.LAYER_FILES[0]).write_text('{}', encoding='utf-8')   # no workspace: BX-12 — the folder holds a BIAN layer so its part is asked for
        if not parts.bian_on(): raise ValueError(f"{workspace or 'here'}: a core design — AID's projection plans from BIAN's service domains; add BIAN first (sdem profile include ext:bian, with sdem-bian installed)")
        return _bian(ws).call('projection', {'have': have, 'registry': registry or _registry(), 'catalogue': catalogue, 'either': False})['package']


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv and argv[0] not in ('project', 'check', 'gaps', '-h', '--help'):   # DA2-05: `sdem aid` fills the workspace; confirm, reject
        from .aid_fill import main as fill_main
        return fill_main(argv)
    ap = argparse.ArgumentParser(prog='sdem aid', description='Architecture Inference Design. Fill a workspace: sdem aid --workspace DIR --person NAME [--dry-run] '
                                 '— adds the missing layers, each record marked inferred; then sdem aid confirm|reject <ids> (the person). '
                                 'Or plan without changing it: the subcommands below.')
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('project'); p.add_argument('--workspace', dest='estate', metavar='DIR', help="plan from a workspace: its business layer (and any applications and technology), its BIAN layer and its approved connections"); p.add_argument('--have', nargs='+', help='the architecture datasets you already have (a1-business.json …)'); p.add_argument('--catalogue'); p.add_argument('--registry'); p.add_argument('-o', '--out', help='where the planned design goes (default with --workspace: <workspace>/plans/PLAN-nnn)'); p.add_argument('--json', action='store_true')
    c = sub.add_parser('check'); c.add_argument('projection'); c.add_argument('--catalogue'); c.add_argument('--json', action='store_true')
    g = sub.add_parser('gaps'); g.add_argument('projection', help='a projection file written by sdem aid project'); g.add_argument('--workspace', dest='estate', metavar='DIR', help="compare with a workspace's real layers and approved connections"); g.add_argument('--actual', nargs='+', help='the real architecture datasets to compare the plan with'); g.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    j = lambda f: _jload(Path(f))
    if a.cmd == 'project' and a.estate:   # WS-05: plan from a workspace; the plan is kept apart in <workspace>/plans/
        ws = Path(a.estate)
        if not (ws / 'mappings.json').exists(): print(f'ERROR: {ws}: no workspace here — start one with sdem new', file=sys.stderr); return 2
        have = {d['level']: d for f in (_F('business'), _F('application'), _F('technology')) if (ws / f).exists() for d in [j(ws / f)] if d.get('instances')}
        if _L('business') not in have: print(f'ERROR: {ws}: no business layer ({_L("business")}) yet — AID plans from what the business does; add it first', file=sys.stderr); return 2
        a.catalogue = a.catalogue or (str(ws / _F('bian')) if (ws / _F('bian')).exists() else None)
        a.registry = a.registry or str(ws / 'mappings.json')
        if not a.out:
            plans = ws / 'plans'; n = 1 + max([int(x.name.split('-')[1]) for x in plans.glob('PLAN-*') if x.name.split('-')[1].isdigit()] or [0]) if plans.exists() else 1
            a.out = str(plans / f'PLAN-{n:03d}')
    elif a.cmd == 'project':
        if not a.have or not a.out: ap.error('project needs --workspace, or --have and --out')
        have = {j(f)['level']: j(f) for f in a.have}
    if a.cmd == 'project':
        try: pkg = _project(a.estate, have, j(a.catalogue) if a.catalogue else None, j(a.registry) if a.registry else None)   # BX-15: BIAN's projection, by sdem-bian
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
        a.actual = [str(ws / f) for f in (_F('bian'), _F('application'), _F('technology'), 'mappings.json') if (ws / f).exists()]
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

