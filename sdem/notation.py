"""The ArchiMate notation of SDEM's types and links (docs/design/sdem-architecture-viewpoint-spec.md §10, ARV-12…ARV-17): how each
kind of record is DRAWN — not where its definition comes from (its `reference`). A file beside the frozen core: changing it changes no
record. Profiles and extensions name their own types' element (`archimate`); a type with none inherits its nearest ancestor's."""
import json
from functools import lru_cache
from .paths import DATA_ROOT

FILE = DATA_ROOT / 'metamodel' / 'archimate-notation.json'
ELEMENTS = {   # ArchiMate 3.2 elements, by layer — what a notation may name
    'strategy': {'Capability', 'Value Stream', 'Resource', 'Course of Action'},
    'business': {'Business Actor', 'Business Role', 'Business Collaboration', 'Business Interface', 'Business Process', 'Business Function',
                 'Business Interaction', 'Business Event', 'Business Service', 'Business Object', 'Contract', 'Representation', 'Product'},
    'application': {'Application Component', 'Application Collaboration', 'Application Interface', 'Application Function', 'Application Interaction',
                    'Application Process', 'Application Event', 'Application Service', 'Data Object'},
    'technology': {'Node', 'Device', 'System Software', 'Technology Collaboration', 'Technology Interface', 'Path', 'Communication Network',
                   'Technology Function', 'Technology Process', 'Technology Interaction', 'Technology Event', 'Technology Service', 'Artifact'},
    'physical': {'Equipment', 'Facility', 'Distribution Network', 'Material'},
    'motivation': {'Stakeholder', 'Driver', 'Assessment', 'Goal', 'Outcome', 'Principle', 'Requirement', 'Constraint', 'Meaning', 'Value'},
    'implementation': {'Work Package', 'Deliverable', 'Implementation Event', 'Plateau', 'Gap'},
    'other': {'Grouping', 'Location', 'Junction'}}
LAYER_OF = {e: l for l, es in ELEMENTS.items() for e in es}
RELATIONSHIPS = {'composition', 'aggregation', 'assignment', 'realization', 'serving', 'access', 'influence', 'triggering', 'flow', 'specialization', 'association'}


@lru_cache(maxsize=1)
def load():
    return json.loads(FILE.read_text(encoding='utf-8'))


def for_type(mm, t):
    """ARV-15, ARV-16: the notation a type is drawn with — its own (SDEM's file, or a profile's or extension's `archimate`), else its
    nearest ancestor's. {element, layer, from} — `from` says where it came from; None if nothing on its line has one."""
    own = load()['entities']
    for i, x in enumerate([t] + mm.ancestors(t)):
        e = mm.entities.get(x) or {}
        if x in own:
            n = own[x]; return {'element': n['element'], 'layer': n['layer'], 'from': 'SDEM' if i == 0 else f'inherited from {x}', **({'why': n['why']} if i == 0 and n.get('why') else {})}
        if e.get('archimate'):   # a profile's or an extension's type names its element (the security pack's do)
            el = e['archimate']; return {'element': el, 'layer': LAYER_OF.get(el, 'other'), 'from': ('profile or extension' if i == 0 else f'inherited from {x}')}
    return None


def for_relationship(name):
    """ARV-14: a within-layer link kind or a cross-layer relationship → its ArchiMate relationship (None if not mapped)."""
    d = load(); return d['within_layer'].get(name) or d['cross_layer'].get(name)


def check(mm, registry=None):
    """Every SDEM type has a notation (its own or inherited), every element is ArchiMate's and in its layer, every link kind and every
    cross-layer relationship is mapped onto an ArchiMate relationship. Returns problems (empty: fine)."""
    d, out = load(), []
    for t, n in d['entities'].items():
        if t not in mm.entities: out.append(f'{t}: not a type SDEM knows')
        if LAYER_OF.get(n['element']) != n['layer']: out.append(f"{t}: {n['element']!r} is not an ArchiMate {n['layer']} element")
    for t in mm.entities:
        if t.count('.') == 1 and for_type(mm, t) is None: out.append(f'{t}: no notation, own or inherited')
    for k, v in list(d['within_layer'].items()) + list(d['cross_layer'].items()):
        if v not in RELATIONSHIPS: out.append(f'{k}: {v!r} is not an ArchiMate relationship')
    kinds = {k['kind'] for k in mm.relationships.get('kinds', [])}
    out += [f'link kind {k}: no notation' for k in sorted(kinds - set(d['within_layer']))]
    if registry is not None:
        out += [f'relationship {r}: no notation' for r in sorted({x['relationship'] for x in registry['relationships']} - set(d['cross_layer']))]
    return out
