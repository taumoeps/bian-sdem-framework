"""SDEM's standards where the Data layer is in use (docs/design/sdem-data-layer-spec.md, DL-04): an *access* from an application
element to a data entity was a link inside the Application layer in 0.19; with Data its own layer it is the link between the layers,
ACCESSED_BY, from the data entity down to the application element. The standards are written once, as 0.19 reads them; this is how
a workspace in the 0.20 form reads them — patterns' connectors and completeness rules alike. Nothing else changes."""


def _is_data(t):
    from .identity import type_id
    tid = type_id(t) if isinstance(t, str) else None
    return bool(tid and tid.startswith('data.'))


def _is_app(t):
    from .identity import type_id
    tid = type_id(t) if isinstance(t, str) else None
    return bool(tid and tid.startswith('application.'))


def adapt(doc):
    from .identity import stack
    if 'data' not in stack() or not isinstance(doc, dict): return doc
    doc = dict(doc)
    if isinstance(doc.get('rules'), list): doc['rules'] = [_rule(r) for r in doc['rules']]
    if isinstance(doc.get('structure'), dict): doc['structure'] = _structure(doc['structure'])
    if isinstance(doc.get('patterns'), list): doc['patterns'] = [adapt(p) for p in doc['patterns']]
    return doc


def _rule(r):
    """A completeness rule: a data entity used by something (access in) → it has an ACCESSED_BY link; an application element's access
    out → an ACCESSED_BY link in."""
    if not isinstance(r, dict): return r
    ent, r = r.get('entity'), dict(r)
    lk = r.get('link')
    if isinstance(lk, dict) and lk.get('kind') == 'access':
        if _is_data(ent) and lk.get('direction') == 'in':
            r.pop('link'); r['across'] = {'relationship': 'ACCESSED_BY', **({'min': lk['min']} if 'min' in lk else {})}
        elif _is_app(ent) and lk.get('direction') == 'out':
            r['link'] = {'relationship': 'ACCESSED_BY', 'direction': 'in', **({'min': lk['min']} if 'min' in lk else {})}
    if isinstance(r.get('any_link'), list):
        r['any_link'] = [({'relationship': 'ACCESSED_BY', 'direction': 'in' if x.get('direction') == 'out' else 'out'}
                          if isinstance(x, dict) and x.get('kind') == 'access' and (_is_app(ent) or _is_data(ent)) else x) for x in r['any_link']]
    return r


def _structure(s):
    """A pattern's connectors: application role → data role, kind access → data role → application role, relationship ACCESSED_BY."""
    roles = {r.get('id'): r.get('type') for r in s.get('roles', []) if isinstance(r, dict)}
    out = []
    for c in s.get('connectors', []):
        if isinstance(c, dict) and c.get('kind') == 'access' and _is_app(roles.get(c.get('from'))) and _is_data(roles.get(c.get('to'))):
            c = {k: v for k, v in c.items() if k != 'kind'}
            c['from'], c['to'], c['relationship'] = c['to'], c['from'], 'ACCESSED_BY'
        out.append(c)
    return {**s, 'connectors': out}
