from .identity import T as _T, layer as _L, live as _live  # ST-01…ST-05: layers and types by id (docs/design/sdem-stable-identity-spec.md)
"""Attributes as evidence (metamodel 0.16.0; docs/design/sdem-full-design-metamodel-design.md AT-01, FD-P3).

The approved link is the fact; an attribute that says the same thing is evidence `sdem aid` proposes the link from:
AID-A01  a data entity's stored_in → STORED_IN that artifact or system software;
AID-A02  an application function's consumes → SERVED_BY that technology service;
AID-A03  a path's from and to → the path associated with each end (a link inside A4, marked inferred).
Links between layers are proposals for a person to approve; nothing already approved or proposed is proposed again.
LC-28 (warning): where a record's attribute and its approved links of the same meaning name different records.
"""
PAIRS = _live(lambda: [   # (entity, attribute, relationship, target types) — the attribute and the link that say the same thing
    (_T('application.DataEntity'), 'stored_in', 'STORED_IN', (_T('technology.Artifact'), _T('technology.SystemSoftware'))),
    (_T('application.ApplicationFunction'), 'consumes', 'SERVED_BY', (_T('technology.TechnologyService'),)),
    (_T('application.ApplicationComponent'), 'deployed_on', 'DEPLOYED_ON', (_T('technology.Node'), _T('technology.Device'), _T('technology.SystemSoftware'))),
    (_T('application.ApplicationComponent'), 'deployed_as', 'DEPLOYED_AS', (_T('technology.Deployment'),)),
    (_T('application.ApplicationComponent'), 'built_as', 'BUILT_AS', (_T('technology.Artifact'),)),
])


def _list(v): return v if isinstance(v, list) else ([v] if v else [])


def propose_links(docs, mappings, mm):
    """AID-A01, A02: [(source, relationship, target, why)] for links between layers the attributes imply."""
    every = {i['id']: i for d in docs.values() for i in d.get('instances', [])}
    have = {(m['source']['id'], m['relationship'], m['target']['id']) for m in mappings if m.get('status') != 'rejected'}
    out = []
    for ent, attr, rel, targets in PAIRS[:2]:
        for i in (docs.get(_L('application')) or {}).get('instances', []):
            if not mm.is_a(i['type'], ent): continue
            for t in _list((i.get('attributes') or {}).get(attr)):
                o = every.get(t)
                if o and any(mm.is_a(o['type'], x) for x in targets) and (i['id'], rel, t) not in have:
                    out.append((i['id'], rel, t, f"{i['id']}.{attr} names {t} ({'AID-A01' if rel == 'STORED_IN' else 'AID-A02'})"))
                    have.add((i['id'], rel, t))
    return out


def path_ends(a4, mm, mark):
    """AID-A03: a path associated with each of its ends (from, to) — inside A4, marked inferred."""
    inst = {i['id']: i for i in (a4 or {}).get('instances', [])}
    have = {(r['source'], r['kind'], r['target']) for r in (a4 or {}).get('relationships', [])}
    out = []
    for p in inst.values():
        if not mm.is_a(p['type'], _T('technology.Path')): continue
        for end in ('from', 'to'):
            t = (p.get('attributes') or {}).get(end)
            if t in inst and (mm.is_a(inst[t]['type'], _T('technology.Node')) or mm.is_a(inst[t]['type'], _T('technology.Device'))) and (p['id'], 'association', t) not in have:
                out.append({'source': p['id'], 'kind': 'association', 'target': t, 'inferred': mark('AID-A03', f'{p["id"]}.{end} names {t}', p['id'])})
                have.add((p['id'], 'association', t))
    return out


def disagreements(levels, mappings, mm):
    """LC-28 (warning): an attribute and the approved links of the same meaning name different records."""
    approved = {}
    for m in mappings:
        if m.get('status') == 'approved':
            approved.setdefault((m['source']['id'], m['relationship']), set()).add(m['target']['id'])
    out = []
    for ent, attr, rel, _ in PAIRS:
        for i in (levels.get(_L('application')) or {}).get('instances', []):
            if not mm.is_a(i['type'], ent): continue
            said = set(_list((i.get('attributes') or {}).get(attr)))
            links = approved.get((i['id'], rel))
            if said and links and said != links:
                out.append(f"instance {i['id']}: {attr} names {', '.join(sorted(said))} but its approved {rel} links are to {', '.join(sorted(links))} — the approved link is the fact; correct the attribute or the link (LC-28)")
    return out
