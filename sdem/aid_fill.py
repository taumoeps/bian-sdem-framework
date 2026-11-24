"""`sdem aid` — Architecture Inference Design fills a workspace's gaps (owner's decision DA2-05; spec docs/design/aid-spec.md AID-W*).

An architect writes whatever they have — any of A1…A4 — and `sdem aid` adds the records the workspace is missing to its real layer
files, each marked `inferred` with its source, reasoning and confidence, and writes the connections it infers as **proposals**
(approved by a person with `sdem approve`, as always). The architect reviews the files, then confirms or rejects each inferred record.
Nothing a person wrote is changed; a rejected record is never added again.

  sdem aid --workspace workspaces/payments --person jane.architect
  sdem aid confirm AID-APP-SD-PAYMENT-RAIL --workspace workspaces/payments --person jane.architect
  sdem aid reject AID-DEP-SD-PAYMENT-RAIL --workspace workspaces/payments --person jane.architect --reason "runs on the shared platform"

Zone placements (metamodel 0.11.0; AID-Z01…Z04): each A4 shape in no zone is placed in a proposed zone — on premises or cloud from the hosting
signals (metamodel/hosting-signals.json) or the organisation's default, the DMZ when internet facing — as a link marked inferred. Confirm or
reject it by the shape's id: `sdem aid confirm INF-K8S-PROD --workspace … --person …`.
"""
from .identity import load as _jload  # DL-11: a design's files read through one boundary (docs/design/sdem-data-layer-spec.md)
from .identity import T as _T, layer as _L, F as _F, live as _live  # ST-01…ST-05: layers and types by id (docs/design/sdem-stable-identity-spec.md)
import argparse, copy, datetime, json, re, sys
from pathlib import Path

DATASETS = _live(lambda: {_L('business'): _F('business'), _L('bian'): _F('bian'), _L('data'): _F('data'), _L('application'): _F('application'), _L('technology'): _F('technology')})
FOLDER = 'aid'


class AidError(ValueError):
    """The request cannot be done (exit 2)."""


def _j(p): return _jload(Path(p))


def _rid(i): return 'AID-' + i[4:] if isinstance(i, str) and i.startswith('PRJ-') else i


def _ids(x):
    """A record's values with planned ids (PRJ-) renamed to inferred ids (AID-)."""
    if isinstance(x, dict): return {k: _ids(v) for k, v in x.items()}
    if isinstance(x, list): return [_ids(v) for v in x]
    return _rid(x)


def is_inferred(rec, confirmed=None):
    m = (rec.get('attributes') or {}).get('inferred')
    if not isinstance(m, dict): return False
    return confirmed is None or (m.get('status') == 'confirmed') == confirmed


def _ext_layers():
    """MX-48: the layers the active profile's extensions add (code: file) — written by aid as SDEM's own are, never by name."""
    from . import profile as _prof
    return {l['code']: l['file'] for l in ((_prof.ACTIVE or {}).get('layers') or []) if l.get('code') and l.get('file') and l['code'] not in DATASETS}


def _index_ids():
    from . import identity
    return identity._index()[0]


def _file(lvl): return DATASETS.get(lvl) or _ext_layers().get(lvl)


def _ext_docs(ws, now=None):
    """The extension layers' documents — an empty one for a layer with no file yet, so an extension can infer its first records into it."""
    from .metamodel import Metamodel
    out = {}
    for c, f in _ext_layers().items():
        p = Path(ws) / f
        out[c] = _j(p) if p.exists() else {'level': c, 'model_id': f"{re.sub(r'[^A-Z0-9]+', '-', Path(ws).name.upper()).strip('-') or 'WORKSPACE'}-{c}",
                                           'model_version': (now or datetime.date.today().isoformat())[:10], 'metamodel_version': Metamodel.load().version,
                                           'source_system': 'SDEM-AID', 'instances': [], 'relationships': []}
    return out


def _bian():
    """0.22 step 3c: BIAN's part of AID — SDEM's own copy (sdem/aid_bian.py) until it moves to the sdem-bian extension."""
    from . import aid_bian
    return aid_bian


def _workspace(ws):
    ws = Path(ws)
    if not (ws / 'mappings.json').exists(): raise AidError(f'{ws}: no workspace here — start one with sdem new --workspace {ws} --person <you>')
    docs = {lvl: _j(ws / f) for lvl, f in DATASETS.items() if (ws / f).exists()}
    registry = _j(ws / 'mappings.json')
    from . import parts
    if parts.migrated():   # DL-12: inside view_019 — data.json in the Application layer, approved ACCESSED_BY as access inside it
        app = _L('application'); d = ws / 'data.json'
        if d.exists():
            dd = _j(d)   # no Application file yet: the layer as data.json describes it — a dataset needs its model_id (DS schema)
            a = docs.setdefault(app, {**{k: dd[k] for k in ('model_id', 'model_version', 'metamodel_version', 'source_system') if dd.get(k)}, 'level': app, 'instances': [], 'relationships': []})
            a['instances'] = list(a.get('instances', [])) + dd.get('instances', []); a['relationships'] = list(a.get('relationships', [])) + dd.get('relationships', [])
        keep = []
        for m in registry.get('mappings', []):
            if m.get('relationship') == 'ACCESSED_BY' and m.get('status') == 'approved' and app in docs:
                docs[app]['relationships'].append({'source': m['target']['id'], 'kind': 'access', 'target': m['source']['id']})
                _APPROVED.setdefault(str(ws.resolve()), set()).add((m['target']['id'], m['source']['id']))
            else: keep.append(m)
        registry = {**registry, 'mappings': keep}
    return ws, docs, registry


_APPROVED = {}   # {workspace: {(application element, data entity)}} — the approved ACCESSED_BY links seen as access in the 0.19 view


def _split(ws, lvl, doc, run, proposals, by='sdem aid'):
    """DL-12 on the way out: {path: document} for one layer AID writes. In a migrated workspace the Application document of the 0.19 view
    goes back to application.json and data.json; an access link it holds that was an approved ACCESSED_BY stays one (not written
    twice); a new one becomes a proposed ACCESSED_BY — a link between layers is a person's to approve."""
    from . import parts
    from .identity import type_id
    if not parts.migrated() or lvl != _L('application'): return {ws / _file(lvl): doc}
    is_data = lambda t: (type_id(t) or '').startswith('data.')
    kinds = {i['id']: i for i in doc.get('instances', [])}
    data_ids = {k for k, i in kinds.items() if is_data(i.get('type'))}
    app = {**doc, 'instances': [i for i in doc.get('instances', []) if i['id'] not in data_ids], 'relationships': []}
    old = _j(ws / 'data.json') if (ws / 'data.json').exists() else {'level': 'data', 'model_id': f"{doc.get('model_id', 'workspace')}-data",
                                                                    'model_version': doc.get('model_version'), 'metamodel_version': doc.get('metamodel_version'),
                                                                    'source_system': doc.get('source_system')}   # every field a layer file needs, as migrate writes it
    data = {**old, 'level': 'data', 'instances': [i for i in doc.get('instances', []) if i['id'] in data_ids], 'relationships': []}   # its own layer id: in the view Data reads as Application's code
    for rel in doc.get('relationships', []):
        s, t = rel.get('source') in data_ids, rel.get('target') in data_ids
        if s and t: data['relationships'].append(rel)
        elif t and rel.get('kind') == 'access':
            if (rel['source'], rel['target']) in _APPROVED.get(str(Path(ws).resolve()), ()): continue   # an approved ACCESSED_BY already
            src, tgt = kinds[rel['target']], kinds[rel['source']]
            proposals.append({'mapping_id': f'{run}-P{len(proposals) + 1:03d}', 'source': {'id': src['id'], 'type': src['type'], 'version': src.get('version', '1')},
                              'relationship': 'ACCESSED_BY', 'target': {'id': tgt['id'], 'type': tgt['type'], 'version': tgt.get('version', '1')}, 'status': 'proposed',
                              'evidence': [f"engine_rationale:{run} access {'inferred' if by == 'sdem aid' else 'stated'} inside the Application layer of the 0.19 view"],
                              'rationale': (f'Inferred by {by}' if by == 'sdem aid' else f'Loaded by {by} from a past design') + ': the application element reads or writes the data entity — a link between the Data and Application layers (DL-04)',
                              'baseline_id': run, 'created_by': by})
        else: app['relationships'].append(rel)
    return {ws / DATASETS[lvl]: app, ws / 'data.json': data}


def _person(p):
    from .validate import is_person
    if not is_person(p): raise AidError(f"--person {p!r}: a decision about the workspace is a person's — give your own name (CTL-21)")


def _rejected(ws):
    f = ws / FOLDER / 'rejected.json'
    return _j(f) if f.exists() else {'rejected': []}


def _in_view(fn):
    """DL-12: AID — proven on 0.19's stack — runs in a migrated workspace's 0.19 view; what it returns comes back through ids, in the
    workspace's own numbering."""
    import functools
    @functools.wraps(fn)
    def run(*a, **k):
        from . import parts, identity
        if not parts.migrated() or identity._VIEW_019[0]: return fn(*a, **k)
        with identity.view_019(): out = identity.store_names(fn(*a, **k), True)
        return identity.read_names(out)
    return run


@_in_view
def fill(workspace, person, dry_run=False, now=None, complete_draft=False):
    """Infer what the workspace is missing into its layer files (AID-W01…W04). Returns the run record; nothing written when refused."""
    from .connect import estate_errors
    _person(person)
    ws, docs, registry = _workspace(workspace)
    now = now or datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()   # UTC with its offset, like change sets
    def evidence(d):   # AID-W08: AID infers only from what a person wrote or confirmed — never from its own unconfirmed records
        keep = [i for i in d['instances'] if not is_inferred(i, confirmed=False)]; ids = {i['id'] for i in keep}
        return {**d, 'instances': keep, 'relationships': [r for r in d.get('relationships', []) if r['source'] in ids and r['target'] in ids
                                                          and not (isinstance(r.get('inferred'), dict) and r['inferred'].get('rule', '').startswith('AID-D') and r['inferred'].get('status') != 'confirmed')]}   # … nor from a link it inferred to complete the draft
    have = {lvl: e for lvl, d in docs.items() if lvl != _L('bian') for e in [evidence(d)] if e.get('instances')}
    if not have: raise AidError(f'{ws}: nothing to infer from yet — write what you have first: any of {", ".join(f for l, f in DATASETS.items() if l != _L("bian"))}')
    B = _bian()   # 0.22 step 3c: BIAN's part of AID, at its four points (projection, patterns, information, direct)
    pkg, catalogue = B.projection(ws, have, registry)
    runs = ws / FOLDER
    n = 1 + max([int(m.group(1)) for p in (runs.glob('AID-*.json') if runs.exists() else []) for m in [re.match(r'AID-(\d+)\.json$', p.name)] if m] or [0])
    run = f'AID-{n:03d}'
    rejected = {r['id'] for r in _rejected(ws)['rejected']}
    after = {lvl: copy.deepcopy(d) for lvl, d in docs.items()}
    present = {i['id'] for d in after.values() for i in d['instances']}
    added = {}
    stem = re.sub(r'[^A-Z0-9]+', '-', ws.name.upper()).strip('-') or 'WORKSPACE'
    for lvl, layer in sorted(pkg['layers'].items()):   # A2: only the service domains the design needs, with their parts, from the catalogue
        doc = after.setdefault(lvl, {'level': lvl, 'model_id': f'{stem}-{lvl}', 'model_version': now[:10], 'metamodel_version': layer['metamodel_version'],
                                     'source_system': 'SDEM-AID', 'instances': [], 'relationships': []})
        for inst in layer['instances']:
            nid = _rid(inst['id'])
            if nid in present or nid in rejected: continue
            rec = _ids(copy.deepcopy(inst)); pj = rec.pop('projection', {}) or {}
            rec['id'] = nid
            if lvl != _L('bian'):   # BIAN records keep BIAN's names; what SDEM built is named as inferred
                rec['name'] = re.sub(r'\s*\(projected\)', '', rec['name']).rstrip() + ' (inferred)'   # e.g. 'Payment Rail service — deployment (inferred)'
                if rec.get('description'): rec['description'] = re.sub(r'^Projected:', 'Inferred:', rec['description'])
            rec.setdefault('attributes', {})['inferred'] = {
                'by': 'sdem aid', 'run': run, 'at': now, 'requested_by': person.strip(), 'step': str(pj.get('step', '')), 'rule': str(pj.get('rule', '')),
                'source': str(pj.get('source_reference') or pj.get('rule') or ''), 'reasoning': str(pj.get('reasoning', '')),
                'confidence': str(pj.get('confidence', '')), 'evidence_class': str(pj.get('evidence_class', '')), 'from': ', '.join(_ids(pj.get('inferred_from', [])))}   # AID-E01
            doc['instances'].append(rec); present.add(nid); added.setdefault(lvl, []).append(nid)
        have_rels = {(r['source'], r['kind'], r['target']) for r in doc.get('relationships', [])}
        for r in layer.get('relationships', []):
            r = _ids(dict(r)); key = (r['source'], r['kind'], r['target'])
            if key not in have_rels and r['source'] in present and r['target'] in present:
                doc.setdefault('relationships', []).append(r); have_rels.add(key)
    zone_unresolved, placements, connections, conn_unresolved, exposure_unresolved = [], 0, 0, [], []
    if after.get(_L('technology'), {}).get('instances'):   # AID-Z01…Z04: each A4 shape in no zone gets a proposed zone, marked inferred, for a person to decide (H2, H5)
        from .hosting import propose
        from .metamodel import Metamodel
        zrej = {r['id'] for r in _rejected(ws)['rejected'] if '@' in r['id']}
        new_zones, links, zone_unresolved = propose(after[_L('technology')], Metamodel.load(), run, person.strip(), now, zrej, stem)
        for z in new_zones:
            if z['id'] not in present and z['id'] not in rejected:
                after[_L('technology')]['instances'].append(z); present.add(z['id']); added.setdefault(_L('technology'), []).append(z['id'])
        have = {(r['source'], r['kind'], r['target']) for r in after[_L('technology')].get('relationships', [])}
        for r in links:
            if (r['source'], r['kind'], r['target']) not in have and r['source'] in present:
                after[_L('technology')].setdefault('relationships', []).append(r); placements += 1 if r.get('inferred') else 0
        from .a4_connect import propose_connections   # AID-C01…C06 (X6): at A4 every shape is connected — proposed, marked inferred
        crej = {r['id'] for r in _rejected(ws)['rejected'] if '|' in r['id']}
        clinks, conn_unresolved = propose_connections(after.get(_L('application')) or {}, after[_L('technology')], registry.get('mappings', []), Metamodel.load(), run, person.strip(), now, crej)
        after[_L('technology')].setdefault('relationships', []).extend(clinks); placements += len(clinks); connections = len(clinks)
        if placements and _L('technology') not in added: added[_L('technology')] = []
    from . import profile as _prof   # the workspace's profile is active (catalogue() above): its standards and patterns are asked first
    dmark = lambda rule, why, frm, **k: {'by': 'sdem aid', 'run': run, 'at': now, 'requested_by': person.strip(), 'step': 'draft', 'rule': rule,
                                         'source': 'docs/design/sdem-completeness-design.md stage 4', 'reasoning': why, 'from': frm, **k}
    live_maps = [(m['source']['id'], m['relationship'], m['target']['id']) for m in registry.get('mappings', []) if m.get('status') == 'approved']
    domain_uses, domains_added, parts_added = [], [], []
    from .metamodel import Metamodel as _MMd
    structs = list(_prof.structures()) + _prof.fitting(after, _MMd.load())   # CPL-16: every pattern SDEM ships that fits is asked, in the profile or not
    consulted = []
    for st in structs:
        aw = st['pattern'].get('applies_when') or {}
        hit = sorted(i['id'] for d in after.values() for i in d['instances'] if _MMd.load().known(i['type']) and _MMd.load().is_a(i['type'], aw.get('entity', ''))
                     and _prof.applies({'when': aw.get('when') or {}}, i) and not is_inferred(i, confirmed=False))
        if hit: consulted.append({'id': st['pattern']['id'], 'title': st['pattern']['title'], 'included': st.get('included', True), 'applies_to': hit[0],
                                  **({'include': st['file']} if st.get('included') is False else {})})
    if structs:   # AID-D05: a BIAN domain a pattern names and the design lacks — from the catalogue, marked inferred
        earlier_maps = [(m['source']['id'], m['relationship'], m['target']['id']) for f in (runs.glob('AID-*-proposals.json') if runs.exists() else []) for m in _j(f).get('mappings', [])]
        drecs, dlinks, domain_uses, domains_added = B.pattern_domains(after, catalogue, live_maps + earlier_maps, _MMd.load(), structs, dmark, rejected)
        if drecs:
            a2doc = after.setdefault(_L('bian'), {'level': _L('bian'), 'model_id': f'{stem}-A2', 'model_version': now[:10], 'metamodel_version': _MMd.load().version,
                                            'source_system': 'SDEM-AID', 'instances': [], 'relationships': []})
            for r in drecs:
                if r['id'] not in present: a2doc['instances'].append(r); present.add(r['id']); added.setdefault(_L('bian'), []).append(r['id'])
            a2doc.setdefault('relationships', []).extend(dlinks)
        domain_uses = [(*u, 'AID-D05') for u in domain_uses]
        from .aid_complete import pattern_parts   # AID-D06: a part a pattern requires and the design has nothing of — a planned record, marked inferred
        precs, plinks, pprops, parts_added = pattern_parts(after, live_maps, _MMd.load(), structs, dmark, rejected)
        for lvl, rs in sorted(precs.items()):
            doc = after.setdefault(lvl, {'level': lvl, 'model_id': f'{stem}-{lvl}', 'model_version': now[:10], 'metamodel_version': _MMd.load().version,
                                         'source_system': 'SDEM-AID', 'instances': [], 'relationships': []})
            for r in rs: doc['instances'].append(r); present.add(r['id']); added.setdefault(lvl, []).append(r['id'])
        for lvl, ls in plinks.items(): after[lvl].setdefault('relationships', []).extend(l for l in ls if l['source'] in present and l['target'] in present)
        domain_uses += pprops
    approved = {(m['source']['id'], m['relationship'], m['target']['id']) for m in registry.get('mappings', []) if m.get('status') in ('approved', 'rejected')}   # decided by a person, either way (RJ-03)
    earlier = []   # proposed by an earlier run, still to review: not again — and nothing inferred beside them meanwhile (RJ-04)
    for f in (runs.glob('AID-*-proposals.json') if runs.exists() else []):
        ms = _j(f).get('mappings', []); earlier += [m for m in ms if (m['source']['id'], m['relationship'], m['target']['id']) not in approved]
        approved |= {(m['source']['id'], m['relationship'], m['target']['id']) for m in ms}
    proposals = []
    by_id = {i['id']: i for d in after.values() for i in d['instances']}
    def end(ref):   # as `sdem link` writes them: id, type, version — and the canonical id a BIAN record carries
        r = by_id.get(ref['id'], {})
        return {**ref, **({'canonical_id': r['canonical_id']} if r.get('canonical_id') else {})}
    for link in pkg['links']['links']:
        s, t = end(_ids(link['source'])), end(_ids(link['target']))
        if s['id'] not in present or t['id'] not in present or (s['id'], link['relationship'], t['id']) in approved: continue
        pj = link.get('projection', {}) or {}
        proposals.append({'mapping_id': f'{run}-P{len(proposals) + 1:03d}', 'source': s, 'relationship': link['relationship'], 'target': t, 'status': 'proposed',
                          'confidence': link.get('confidence'), 'evidence': [f"engine_rationale:{run} {pj.get('rule', '')}".strip()],
                          'rationale': re.sub(r'^PROJECTED DESIGN, not a mapping:\s*', 'Inferred by sdem aid: ', link.get('rationale', '')),
                          'baseline_id': run, 'created_by': 'sdem aid'})
    not_stored = []
    if after.get(_L('bian')):   # AID-I01…I04 (metamodel 0.15.0, IM-10): a data entity with its fields for each typed business object — inferred, proposed
        mark = lambda rule, why, frm: {'by': 'sdem aid', 'run': run, 'at': now, 'requested_by': person.strip(), 'step': 'information', 'rule': rule,
                                       'source': 'docs/design/sdem-full-design-metamodel-design.md IM-10', 'reasoning': why, 'confidence': 'low',
                                       'evidence_class': 'attribute_join', 'from': frm}
        a3doc = after.setdefault(_L('application'), {'level': _L('application'), 'model_id': f'{stem}-A3', 'model_version': now[:10], 'metamodel_version': after[_L('bian')].get('metamodel_version'),
                                         'source_system': 'SDEM-AID', 'instances': [], 'relationships': []})
        from .metamodel import Metamodel as _MMk   # AID-K02 first: an object an existing table stores is not given a new one
        for src, rel, tgt, rule, why, conf in B.match_existing(after, registry.get('mappings', []) + earlier + proposals, _MMk.load()):
            if src in by_id and tgt in by_id and (src, rel, tgt) not in approved:
                proposals.append({'mapping_id': f'{run}-P{len(proposals) + 1:03d}', 'source': end({'id': src, 'type': by_id[src]['type'], 'version': by_id[src]['version']}), 'relationship': rel,
                                  'target': {'id': tgt, 'type': by_id[tgt]['type'], 'version': by_id[tgt]['version']}, 'status': 'proposed', 'confidence': conf,
                                  'evidence': [f'engine_rationale:{run} {rule}'], 'rationale': f'Inferred by sdem aid ({rule}): {why}', 'baseline_id': run, 'created_by': 'sdem aid'})
        iinst, irels, ilinks, not_stored = B.propose_information(after[_L('bian')], a3doc, registry.get('mappings', []) + earlier + proposals, mark, rejected, lambda r: is_inferred(r, confirmed=False))
        for rec in iinst:
            if rec['id'] in present: continue
            a3doc['instances'].append(rec); present.add(rec['id']); by_id[rec['id']] = rec; added.setdefault(_L('application'), []).append(rec['id'])
        a3doc.setdefault('relationships', []).extend(r for r in irels if r['source'] in present and r['target'] in present)
        from .metamodel import Metamodel as _MMi   # AID-I07: a table nobody accesses, accessed by the component realising its object's domain (inferred)
        acc = B.propose_access(after, registry.get('mappings', []) + proposals, _MMi.load(), mark)
        if acc:
            a3doc['relationships'].extend(acc); added.setdefault(_L('application'), [])
        for src, rel, tgt, why in ilinks:
            if src not in by_id or tgt not in by_id or (src, rel, tgt) in approved: continue
            proposals.append({'mapping_id': f'{run}-P{len(proposals) + 1:03d}', 'source': end({'id': src, 'type': by_id[src]['type'], 'version': by_id[src]['version']}),
                              'relationship': rel, 'target': {'id': tgt, 'type': by_id[tgt]['type'], 'version': by_id[tgt]['version']}, 'status': 'proposed',
                              'confidence': 'low', 'evidence': [f'engine_rationale:{run} AID-I03'], 'rationale': f'Inferred by sdem aid: {why} — approve with data_model evidence',
                              'baseline_id': run, 'created_by': 'sdem aid'})
    if after.get(_L('application')) or after.get(_L('technology')):   # AID-A01…A03 (metamodel 0.16.0, AT-01): the links attributes imply — proposed; a path's ends, inferred
        from .aid_attr import propose_links, path_ends
        from .metamodel import Metamodel as _MMa
        _mm = _MMa.load()
        amark = lambda rule, why, frm: {'by': 'sdem aid', 'run': run, 'at': now, 'requested_by': person.strip(), 'step': 'attributes', 'rule': rule,
                                        'source': 'docs/design/sdem-full-design-metamodel-design.md AT-01', 'reasoning': why, 'confidence': 'high',
                                        'evidence_class': 'attribute_join', 'from': frm}
        for src, rel, tgt, why in propose_links(after, registry.get('mappings', []) + proposals, _mm):
            if src not in by_id or tgt not in by_id or (src, rel, tgt) in approved: continue
            s_, t_ = by_id[src], by_id[tgt]
            proposals.append({'mapping_id': f'{run}-P{len(proposals) + 1:03d}', 'source': {'id': src, 'type': s_['type'], 'version': s_['version']}, 'relationship': rel,
                              'target': {'id': tgt, 'type': t_['type'], 'version': t_['version']}, 'status': 'proposed', 'confidence': 'high',
                              'evidence': [f'engine_rationale:{run} {why.split("(")[-1].rstrip(")")}'], 'rationale': f'Inferred by sdem aid from an attribute: {why} — approve with deployment_design evidence',
                              'baseline_id': run, 'created_by': 'sdem aid'})
        if after.get(_L('technology')):
            ends = path_ends(after[_L('technology')], _mm, amark)
            if ends:
                after[_L('technology')].setdefault('relationships', []).extend(ends); placements += len(ends); connections += len(ends)
                if _L('technology') not in added: added[_L('technology')] = []
    if after.get(_L('business')) or after.get(_L('bian')):   # AID-L01…L05, AID-K01 (the owner's approvals 2, 2b, 2026-11-16): direct A1->A3 links and field matches, proposed
        from .aid_links import propose_direct, DIRECT_ORDER
        from .metamodel import Metamodel as _MMl
        _mml = _MMl.load()
        maps_ = registry.get('mappings', []) + proposals
        bdirect, bfields = B.direct(after, maps_, _mml)   # BIAN's: AID-L01, L02, I05, and K01
        seen_b = [{'source': {'id': s_}, 'relationship': r_, 'target': {'id': t_}, 'status': 'proposed'} for s_, r_, t_, *_ in bdirect]
        core = propose_direct(after, maps_ + seen_b, _mml)   # the core's AID-L03…L06, I06 — BIAN's found first, as an earlier rule's always were
        merged = sorted(bdirect + core, key=lambda x: DIRECT_ORDER.index(x[3]))   # stable: each rule's own order, the rules in the order they always ran
        for found in (merged, bfields):
            for src, rel, tgt, rule, why, conf in found:
                if src not in by_id or tgt not in by_id or (src, rel, tgt) in approved: continue
                s_, t_ = by_id[src], by_id[tgt]
                proposals.append({'mapping_id': f'{run}-P{len(proposals) + 1:03d}', 'source': end({'id': src, 'type': s_['type'], 'version': s_['version']}), 'relationship': rel,
                                  'target': {'id': tgt, 'type': t_['type'], 'version': t_['version']}, 'status': 'proposed', 'confidence': conf,
                                  'evidence': [f'engine_rationale:{run} {rule}'], 'rationale': f'Inferred by sdem aid ({rule}): {why}',
                                  'baseline_id': run, 'created_by': 'sdem aid'})
    if after.get(_L('application')) and after.get(_L('technology')):   # AID-X01: an internet-facing interface EXPOSED_THROUGH the one edge platform — for a person to approve
        from .a4_connect import propose_exposure
        from .metamodel import Metamodel as _MM
        pairs, exposure_unresolved = propose_exposure(after[_L('application')], after[_L('technology')], registry.get('mappings', []) + proposals, _MM.load())
        from .a4_connect import propose_builds   # AID-X02: an application BUILT_AS its artifact — for a person to approve
        for comp, art, why in propose_builds(after[_L('application')], after[_L('technology')], registry.get('mappings', []) + proposals, _MM.load()):
            s_, t_ = by_id[comp], by_id[art]
            proposals.append({'mapping_id': f'{run}-P{len(proposals) + 1:03d}', 'source': {'id': comp, 'type': s_['type'], 'version': s_['version']}, 'relationship': 'BUILT_AS',
                              'target': {'id': art, 'type': t_['type'], 'version': t_['version']}, 'status': 'proposed', 'confidence': 'medium',
                              'evidence': [f'engine_rationale:{run} AID-X02'], 'rationale': f'Inferred by sdem aid (AID-X02): {why} — approve with build_pipeline evidence',
                              'baseline_id': run, 'created_by': 'sdem aid'})
        for iface, plat in [(a, b) for a, b, _ in pairs]:
            s_, t_ = by_id[iface], by_id[plat]
            proposals.append({'mapping_id': f'{run}-P{len(proposals) + 1:03d}', 'source': {'id': iface, 'type': s_['type'], 'version': s_['version']}, 'relationship': 'EXPOSED_THROUGH',
                              'target': {'id': plat, 'type': t_['type'], 'version': t_['version']}, 'status': 'proposed', 'confidence': 'medium',
                              'evidence': [f'engine_rationale:{run} AID-X01'], 'rationale': f'Inferred by sdem aid (AID-X01): {iface} is internet facing and {plat} is the one internet-facing edge platform — approve with network_design evidence',
                              'baseline_id': run, 'created_by': 'sdem aid'})
    for src, rel, tgt, why, drule in domain_uses:   # AID-D05, AID-D06: a link between layers a pattern asks for — proposed, for a person to approve
        if src not in by_id or tgt not in by_id or (src, rel, tgt) in approved or any((p['source']['id'], p['relationship'], p['target']['id']) == (src, rel, tgt) for p in proposals): continue
        s_, t_ = by_id[src], by_id[tgt]
        proposals.append({'mapping_id': f'{run}-P{len(proposals) + 1:03d}', 'source': {'id': src, 'type': s_['type'], 'version': s_['version']}, 'relationship': rel,
                          'target': end({'id': tgt, 'type': t_['type'], 'version': t_['version']}), 'status': 'proposed', 'confidence': 'low', 'evidence_class': 'name_token' if drule == 'AID-D05' else 'pattern',
                          'evidence': [f'engine_rationale:{run} {drule}'], 'rationale': f'Inferred by sdem aid ({drule}): {why}' + (' — approve with process_model evidence' if drule == 'AID-D05' else ''),
                          'baseline_id': run, 'created_by': 'sdem aid'})
    draft = {'links_inferred': 0, 'defaults': 0, 'links': [], 'left_open': [], 'domains_added': domains_added, 'parts_added': parts_added, 'parts_to_name': [], 'patterns_consulted': consulted}
    if structs:   # AID-D07: which record is the part — suggested from its name, never written
        from .aid_complete import name_parts
        from .metamodel import Metamodel as _MMn
        draft['parts_to_name'] = name_parts(after, live_maps, _MMn.load(), structs)
    if _prof.ACTIVE is not None and _prof.rules():   # AID-D01…D03: the links a standard asks for and the design lacks — inferred where a name gives evidence, said where none does
        from .aid_complete import propose_links
        from .metamodel import Metamodel as _MMc
        lrej = {r['id'] for r in _rejected(ws)['rejected'] if '|' in r['id']}
        dlinks_, draft['left_open'] = propose_links(after, live_maps, _MMc.load(), _prof.rules(), dmark, lrej, complete=complete_draft)
        for lvl, ls in sorted(dlinks_.items()):
            after[lvl].setdefault('relationships', []).extend(ls); added.setdefault(lvl, [])
            draft['links'] += [{'layer': lvl, 'link': f"{r['source']}|{r['kind']}|{r['target']}", 'rule': r['inferred']['rule'], 'asked_by': r['inferred']['asked_by'], 'reasoning': r['inferred']['reasoning']} for r in ls]
        draft['defaults'] = sum(l['rule'] == 'AID-D08' for l in draft['links'])
        draft['links_inferred'] = len(draft['links']); placements += len(draft['links']); connections += len(draft['links'])
        joined = {e for l in draft['links'] for e in l['link'].split('|')[::2]}
        conn_unresolved = [u for u in conn_unresolved if u['id'] not in joined]   # no longer linked to nothing
    if complete_draft and _prof.ACTIVE is not None and _prof.rules():   # AID-D09: a gap between layers nothing proposes a link for — a default proposal, where the others of its kind go
        from .aid_complete import default_across
        from .metamodel import Metamodel as _MMx
        prop_now = [(p['source']['id'], p['relationship'], p['target']['id']) for p in proposals + earlier]
        for src, rel, tgt, why, drule in default_across(after, live_maps, prop_now, _MMx.load(), _prof.rules(), approved):
            if src not in by_id or tgt not in by_id: continue
            s_, t_ = by_id[src], by_id[tgt]
            proposals.append({'mapping_id': f'{run}-P{len(proposals) + 1:03d}', 'source': {'id': src, 'type': s_['type'], 'version': s_['version']}, 'relationship': rel,
                              'target': {'id': tgt, 'type': t_['type'], 'version': t_['version']}, 'status': 'proposed', 'confidence': 'low', 'evidence_class': 'structural',
                              'evidence': [f'engine_rationale:{run} {drule}'], 'rationale': f'Inferred by sdem aid ({drule}): {why}', 'baseline_id': run, 'created_by': 'sdem aid'})
            draft['defaults'] += 1; draft.setdefault('default_proposals', []).append(f'{src} {rel} {tgt}')
    # MX-45…MX-50: what the workspace's extensions infer — asked by running them, checked and marked as SDEM's own, written only with everything else
    from .ext_infer import contribute
    for code, d in _ext_docs(ws, now).items(): after.setdefault(code, d)
    known = {i['id']: i for d in after.values() for i in d.get('instances', [])}
    eadded, eprops, ext_report = contribute('aid', ws, after, known, run=run, person=person.strip(), now=now,
                                            rejected=rejected | {r['id'] for r in _rejected(ws)['rejected']}, approved=approved)
    for pr in eprops: proposals.append({'mapping_id': f'{run}-P{len(proposals) + 1:03d}', **pr})
    for lvl, ids_ in eadded.items(): added.setdefault(lvl, []).extend(ids_)
    BAND = {'low': 0.4, 'medium': 0.6, 'high': 0.8}   # the registry holds confidence as a number, as the engine writes it (found building Payment Initiation v2)
    for pr in proposals:
        if isinstance(pr.get('confidence'), str): pr['confidence'] = BAND.get(pr['confidence'], 0.4)
    errors = estate_errors({_file(l): d for l, d in after.items()}, registry)
    if errors: raise AidError('the workspace would not pass its checks with the inferred records — nothing written:\n  ' + '\n  '.join(errors[:10]))
    from . import parts as _parts
    if _parts.migrated():   # DL-12: reported by layer id, Data's records apart from Application's — numbered as the workspace reads them, outside the view
        from .identity import layer_id as _lid, type_id as _tid
        typ = {i['id']: i.get('type') for d in after.values() for i in d.get('instances', [])}
        by_id = {}
        for lvl, ids_ in added.items():
            for x in ids_: by_id.setdefault('data' if (_tid(typ.get(x)) or '').startswith('data.') else (_lid(lvl) or lvl), []).append(x)   # an extension's layer: by its code (MX-48)
        added_report = {(f'@layer:{k}' if k in _index_ids() else k): v for k, v in by_id.items()}
    else: added_report = added
    record = {'id': run, 'at': now, 'requested_by': person.strip(), 'added': added_report, 'proposals': f'{FOLDER}/{run}-proposals.json',
              'proposed_connections': len(proposals), 'projection_ends': pkg['projection'].get('projection_ends', []),
              'zone_placements': placements - connections, 'zones_unresolved': zone_unresolved, 'a4_connections': connections, 'a4_unresolved': conn_unresolved,
              'exposure_unresolved': exposure_unresolved, 'tables_not_inferred': not_stored, 'draft': draft, **({'extensions': ext_report} if ext_report else {}),
              'skipped_rejected': sorted(rejected & {_rid(i['id']) for l in pkg['layers'].values() for i in l['instances']})}
    if dry_run:   # AF: a dry run says what it would write (AGENTS.md) — nothing is written
        record['would_write'] = sorted([(ws / _file(lvl)).as_posix() for lvl in added] + ([(runs / f'{run}-proposals.json').as_posix(), (runs / f'{run}.json').as_posix()] if (added or proposals) else []))
    if not dry_run and (added or proposals or placements):
        from .files import Batch
        b = Batch()
        for lvl in added:
            for path, doc in _split(ws, lvl, after[lvl], run, proposals).items(): b.json(path, doc)   # DL-12
        b.json(runs / f'{run}-proposals.json', {'mappings': proposals}); b.json(runs / f'{run}.json', record); b.commit()
        _adopt(ws, added, person, f'sdem aid {run}: inferred records and links, each marked inferred (AID-W02) - confirm or reject them with sdem aid confirm|reject')   # AID-W10
    return record


@_in_view
def decide(workspace, ids, person, action, reason='', all_=False, now=None):
    """Confirm or reject inferred records (AID-W05, W06). Returns the ids changed."""
    _person(person)
    if action == 'reject' and not (reason or '').strip(): raise AidError('--reason is required to reject — it is kept, so the record is not inferred again')
    ws, docs, view_registry = _workspace(workspace)
    docs.update(_ext_docs(ws))   # MX-49: what an extension inferred into its own layer is confirmed or rejected the same way
    now = now or datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()   # UTC with its offset, like change sets
    inferred = {i['id']: (lvl, i) for lvl, d in docs.items() for i in d['instances'] if is_inferred(i, confirmed=False if all_ else None)}
    marked = lambda r: isinstance(r.get('inferred'), dict) and (not all_ or r['inferred'].get('status') != 'confirmed')
    placed = {}   # a record's inferred links (H5): its zone placement (AID-Z01), its connections at A4 (AID-C01…C06), a link a standard asked for (AID-D01) — by either end's id, or the link itself as source|kind|target (AID-D04)
    home = {}
    for lvl, d in docs.items():
        for r in d.get('relationships', []):
            if marked(r):
                home[id(r)] = lvl
                for end in ((r['source'], r['target']) if lvl == _L('technology') else ()) + (f"{r['source']}|{r['kind']}|{r['target']}",): placed.setdefault(end, []).append(r)
    chosen = sorted(set(inferred) | {k for k in placed if '|' not in k}) if all_ else list(ids)
    if not chosen: raise AidError('nothing to do — give the ids (see `sdem check` or the dashboard), or --all')
    missing = [i for i in chosen if i not in inferred and i not in placed]
    if missing: raise AidError(f"not inferred records or placements in {ws}: {', '.join(missing)} — `sdem aid confirm|reject` acts only on what SDEM inferred")
    changed = set()
    plc = [i for i in chosen if i in placed and i not in inferred]; chosen = [i for i in chosen if i not in plc]
    rej = _rejected(ws)
    for i in plc:   # its inferred links: confirmed with the person's name, or removed and remembered so they are not proposed again
        for r in placed[i]:
            if action == 'confirm':
                if r['inferred'].get('status') != 'confirmed': r['inferred'].update(status='confirmed', confirmed_by=person.strip(), confirmed_at=now); changed.add(home[id(r)])
            elif any(x is r for x in docs[home[id(r)]]['relationships']):
                lv = home[id(r)]; docs[lv]['relationships'] = [x for x in docs[lv]['relationships'] if x is not r]; changed.add(lv)
                key = f"{r['target']}@{r['source']}" if r['inferred'].get('rule', '').startswith('AID-Z') else f"{r['source']}|{r['kind']}|{r['target']}"
                rej['rejected'].append({'id': key, 'by': person.strip(), 'at': now, 'reason': reason.strip()})
    every = {i['id']: (lvl, i) for lvl, d in docs.items() for i in d['instances'] if is_inferred(i)}
    def froms(rec): return {x.strip() for x in str(rec['attributes']['inferred'].get('from', '')).split(',') if x.strip()}
    if action == 'confirm' and chosen:
        chosen = list(chosen) + [i for i, (lvl, r) in every.items()   # a BIAN service domain is confirmed with its parts (operations, control record …)
                                 if lvl == _L('bian') and i not in chosen and froms(r) and froms(r) <= {c for c in chosen if every.get(c, ('', {}))[0] == _L('bian')}]
        for i in chosen:
            lvl, rec = every[i]
            if is_inferred(rec, confirmed=True): continue
            rec['attributes']['inferred'].update(status='confirmed', confirmed_by=person.strip(), confirmed_at=now); changed.add(lvl)
    elif chosen:
        gone = set(chosen)
        while True:   # what SDEM inferred only from rejected records goes too: a domain's parts, the application built on it, its APIs and deployment
            more = {i for i, (lvl, r) in every.items() if i not in gone and is_inferred(r, confirmed=False) and froms(r) and froms(r) <= gone}
            if not more: break
            gone |= more
        def refs(x):   # every id a record or link names
            if isinstance(x, dict): return set().union(*(refs(v) for v in x.values())) if x else set()
            if isinstance(x, list): return set().union(*(refs(v) for v in x)) if x else set()
            return {x} if isinstance(x, str) else set()
        while True:    # a record another kept record still uses stays (e.g. a functional pattern two domains share)
            used = set().union(*([refs(i.get('attributes', {})) for d in docs.values() for i in d['instances'] if i['id'] not in gone] or [set()]))
            used |= {r['target'] for d in docs.values() for r in d.get('relationships', []) if r['source'] not in gone and not isinstance(r.get('inferred'), dict)}   # an inferred zone placement keeps nothing
            keep = (gone & used) - set(chosen)
            if not keep: break
            gone -= keep
        chosen = sorted(gone)
        for lvl, d in docs.items():
            before = len(d['instances'])
            d['instances'] = [x for x in d['instances'] if x['id'] not in gone]
            d['relationships'] = [r for r in d.get('relationships', []) if r['source'] not in gone and r['target'] not in gone]
            if len(d['instances']) != before: changed.add(lvl)
        rej['rejected'] += [{'id': i, 'by': person.strip(), 'at': now, 'reason': reason.strip()} for i in chosen]
    from .connect import estate_errors
    errors = estate_errors({_file(l): d for l, d in docs.items()}, view_registry)   # 0.22: the registry as AID's 0.19 view reads it — approved ACCESSED_BY are access links inside it (DL-12), as fill checks
    if errors: raise AidError(f'the workspace would not pass its checks after this {action} — nothing written:\n  ' + '\n  '.join(errors[:8])
                              + ('\n  (an approved connection may still point to it: supersede it first)' if action == 'reject' else ''))
    from .files import Batch
    b = Batch()
    for lvl in changed:
        for path, doc in _split(ws, lvl, docs[lvl], 'AID-DECIDE', []).items(): b.json(path, doc)   # DL-12
    if action == 'reject': b.json(ws / FOLDER / 'rejected.json', rej)
    b.commit()
    _adopt(ws, changed, person, f'sdem aid {action}: {len(chosen) + len(plc)} inferred record(s) or link(s)' + (f' - {reason}' if reason else ''))   # AID-W10
    return chosen + plc


def _adopt(ws, layers, person, reason):
    """AID-W10: in a workspace that keeps change sets, what sdem aid (fill, confirm, reject) wrote is recorded as a change set adopted by
    the person, so the chain of change sets stays whole (CTL-20)."""
    from .agents import Estate, CoordinationError
    from . import identity, parts
    ids = {identity.layer_id(l) or l for l in layers}   # DL-12: AID names layers in its 0.19 view; its change sets are the workspace's
    if parts.migrated() and 'application' in ids: ids.add('data')   # the view's Application file is written as application.json and data.json
    with identity.outside_view():
        est = Estate(ws)
        if not any(est._last_change_set(l) for l in DATASETS): return
        for lvl in sorted(identity.layer(i) if i in identity._index()[0] else i for i in ids):
            try: est.adopt(lvl, person.strip(), reason)
            except CoordinationError: pass   # nothing new in that layer's file


def main(argv):
    if argv[:1] in (['confirm'], ['reject']):
        action, argv = argv[0], argv[1:]
        ap = argparse.ArgumentParser(prog=f'sdem aid {action}', description=('Confirm inferred records: you agree with them; the mark stays, with your name.' if action == 'confirm'
                                     else 'Reject inferred records: removed with their links inside the layer, and remembered so they are not inferred again.'))
        ap.add_argument('ids', nargs='*', metavar='ID', help='the inferred record ids (sdem status or sdem handback lists them)'); ap.add_argument('--workspace', dest='estate', required=True, metavar='DIR')
        ap.add_argument('--person', required=True, help='your name — a person'); ap.add_argument('--all', action='store_true', help='every inferred record not yet confirmed')
        ap.add_argument('--reason', required=(action == 'reject'), help='why — kept')
        ap.add_argument('--json', action='store_true')
        a = ap.parse_args(argv)
        try: done = decide(a.estate, a.ids, a.person, action, a.reason or '', a.all)
        except AidError as e: print(f'ERROR: {e}', file=sys.stderr); return 2
        if a.json:
            print(json.dumps({'action': action, 'workspace': a.estate, 'by': a.person, 'records': done, 'count': len(done),
                              'next': 'commit on a branch and open a pull request'}, indent=2)); return 0
        print(f"{'confirmed' if action == 'confirm' else 'rejected'} {len(done)} inferred record(s) in {a.estate}: {', '.join(done[:8])}{' …' if len(done) > 8 else ''}")
        print('Next: commit on a branch and open a pull request.'); return 0
    ap = argparse.ArgumentParser(prog='sdem aid', formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description=f'Architecture Inference Design: from what the workspace has (any of {_L("business")}…{_L("technology")}), add the records it is missing to its layer '
                                             'files — each marked inferred, with source, reasoning and confidence — and propose the connections. You review, then '
                                             '`sdem aid confirm` or `sdem aid reject` each record and `sdem approve` the connections.',
                                 epilog=__doc__.split('\n\n')[2])
    ap.add_argument('--workspace', dest='estate', required=True, metavar='DIR'); ap.add_argument('--person', required=True, help='your name — a person')
    ap.add_argument('--dry-run', action='store_true'); ap.add_argument('--json', action='store_true')
    ap.add_argument('--complete-draft', action='store_true', help="also place, by default, each gap a standard finds that nothing in the design gives evidence for — so the first draft is whole; each is marked 'placed by default', to review first (AID-D08)")
    a = ap.parse_args(argv)
    try: rec = fill(a.estate, a.person, a.dry_run, complete_draft=a.complete_draft)
    except AidError as e:
        from .errors import note
        if 'would not pass its checks' in str(e):
            note('refused', 'the inferred records conflict with the workspace — fix what the message names (often an approved connection to a record the workspace no longer holds), then run again')
        print(f'ERROR: {e}', file=sys.stderr); return 2
    if a.json: print(json.dumps(rec, indent=2)); return 0
    total = sum(len(v) for v in rec['added'].values())
    if not total and not rec['proposed_connections']:
        print(f"nothing to add to {a.estate} — every record AID can infer is already there" + (f" (or rejected: {len(rec['skipped_rejected'])})" if rec['skipped_rejected'] else ''))
    else:
        what = ', '.join(f'{l} {len(v)} inferred record(s)' for l, v in sorted(rec['added'].items())) or 'no new records'
        print(f"{'would add' if a.dry_run else 'added (' + rec['id'] + ')'} to {a.estate}: {what}; "
              + f"{rec['proposed_connections']} connection(s) proposed in {a.estate}/{rec['proposals']} — checked")
    for e in rec['projection_ends']: print(f'NOTE: {e}')
    for e in rec.get('tables_not_inferred') or []:
        print(f"NOTE: no table inferred for the BIAN object {e['name']} ({e['id']}) — " + (e['why'] + '; say where it is stored with sdem connect … MAPPED_TO …' if e.get('why') else
              f"no application here realises {', '.join(e['domains'])} (AID-I08); if one stores it, link the domain to it (sdem connect … REALIZED_BY …) and run sdem aid again"))
    if rec.get('zone_placements'):
        print(f"zones: {rec['zone_placements']} shape(s) {'would be placed' if a.dry_run else 'placed'} in a proposed zone (AID-Z01) — from the hosting signals and the organisation's default; "
              f"decide each: sdem aid confirm|reject <shape> --workspace {a.estate} --person <you>")
    if rec.get('a4_connections'):
        print(f"{_L('technology')}: {rec['a4_connections']} connection(s) {'would be proposed' if a.dry_run else 'proposed'} for shapes linked to nothing (AID-C01…C06) — confirm or reject by the shape's id")
    for u in rec.get('a4_unresolved', []): print(f"{_L('technology')}: {u['id']} not connected — {u['why']}")
    dr = rec.get('draft') or {}
    if dr.get('patterns_consulted'):   # CPL-16: said every time — which patterns were asked before anything was inferred
        print('patterns consulted: ' + '; '.join(f"{p['title']} (" + ('in the profile' if p['included'] else f"fits the design; not in the profile — a person includes it to keep it checked: sdem profile include {p['include']} --workspace {a.estate} --person <you>") + ')' for p in dr['patterns_consulted']))
    else: print('patterns consulted: none — no pattern SDEM ships or the profile includes fits this design')
    if dr.get('domains_added'): print(f"draft: {', '.join(dr['domains_added'])} {'would be' if a.dry_run else ''} brought in from BIAN because a pattern names them (AID-D05) — marked inferred: confirm or reject each")
    if dr.get('parts_added'): print(f"draft: {len(dr['parts_added'])} part(s) a pattern asks for and the design has nothing of {'would be' if a.dry_run else ''} added as planned records (AID-D06) — marked inferred: {', '.join(dr['parts_added'][:8])}{' …' if len(dr['parts_added']) > 8 else ''}")
    for x in dr.get('parts_to_name') or []:
        print(f"draft: which record is the {x['label']}? {' or '.join(x['candidates'])} — " + (f"suggested: {x['suggested']} ({x['why']})" if x['suggested'] else x['why'])
              + f"; a person names it: conforms_to \"{x['conforms_to']}\" on the record, through a change set (AID-D07)")
    if dr.get('links_inferred'):
        print(f"draft: {dr['links_inferred']} link(s) a standard asks for {'would be inferred' if a.dry_run else 'inferred'} from names (AID-D01, AID-D02) — each marked inferred, low confidence; "
              f"confirm or reject each by naming it: sdem aid confirm|reject '<source|kind|target>' --workspace {a.estate} --person <you>")
        for l in dr['links'][:12]: print(f"  {l['link'].replace('|', ' ')}  ({l['rule']}, asked by {l['asked_by']})" + ('  — PLACED BY DEFAULT, no evidence: review first' if l['rule'] == 'AID-D08' else ''))
    for x in dr.get('default_proposals') or []: print(f"draft: {x} — PROPOSED BY DEFAULT, no evidence (AID-D09): review first, then approve or reject it like any proposal")
    if dr.get('left_open'):
        print(f"draft: {len(dr['left_open'])} gap(s) left open — nothing in the design says what the link is (AID-D03); a person states it through a change set"
              + ('' if a.complete_draft else ' — or run again with --complete-draft to place each by default, marked so') + ':')
        for o in dr['left_open'][:12]: print(f"  {o['record']} ({o['rule']}: {o['message']}) — {o['why']}")
    for u in rec.get('exposure_unresolved', []):
        print(f"exposure: {u['id']} is internet facing — {'no internet-facing edge platform to expose it through' if not u['candidates'] else 'several candidates: ' + ', '.join(u['candidates'])} (AID-X01): a person decides")
    for u in rec.get('zones_unresolved', []):
        print(f"zones: {u['id']} not placed — " + (u['why'] if u.get('why') else f"its evidence points both ways ({'; '.join(e['id'] + ' ' + e['read'] for e in u['signals'])}): a person places it (AID-Z01)"))
    if total and not a.dry_run:
        print(f'Next: review the inferred records in the layer files (marked "inferred", with source, reasoning and confidence), then '
              f'sdem aid confirm|reject <ids> --workspace {a.estate} --person <you>; then propose every connection in one list to review and approve from '
              f'(it includes these): sdem link --workspace {a.estate} --out {a.estate}/links')
    return 0
