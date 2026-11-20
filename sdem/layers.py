"""The layer registry (docs/design/sdem-layers-spec.md, LR-01…LR-10): the layers a workspace works across, in order.

SDEM's four core layers — A1 Business, A2 Service Domain (BIAN), A3 Application, A4 Technology — are always present. An organisation
profile (sdem/profile.py) may add layers **above A1** or **below A4**, each with its own record file, types and link types to its
neighbour, or **across** them all (LR-11: a cross-cutting architecture such as security, whose link types may reach any layer). Everything that works layer by layer — the workspace's files, the ledger, check, build, trace, impact, validation,
requirements, change sets, the dashboards — reads the layers from here, so a profile's layers take part without code changes.

The collections below are *live*: they reflect the active profile at the moment they are read (FILES, CODES, AGENTS).
"""
from .identity import T as _T, layer as _L, F as _F, live as _live  # ST-01…ST-05: layers and types by id (docs/design/sdem-stable-identity-spec.md)
from collections.abc import Mapping, Sequence

_CORE = (('business', 'Business', 'sdem-a1-business'), ('bian', 'BIAN', 'sdem-a2-bian'), ('data', 'Data', 'sdem-data'),
         ('application', 'Application', 'sdem-a3-application'), ('technology', 'Technology', 'sdem-a4-technology'))   # agent names never change (CTL-19)


def _core():
    from .identity import stack
    return tuple((_L(i), _F(i), f'{_L(i)} {n}', a) for i, n, a in _CORE if i != 'data' or 'data' in stack())   # DL-01: Data where it is in use


CORE = _live(_core)
CORE_CODES = _live(lambda: tuple(c[0] for c in CORE))
RESERVED_FILES = _live(lambda: {c[1] for c in CORE} | {'mappings.json', 'requirements.json', 'workspace.json', 'sdem-ledger.json', 'sdem-profile.json', 'governance.json'})


def agent_for(code):
    """The layer agent's name: SDEM's for a core layer; sdem-layer-<code> for a profile layer (CTL-19 scopes it to that layer)."""
    core = {c[0]: c[3] for c in CORE}
    return core.get(code) or f'sdem-layer-{code.lower()}'


def layers():
    """Every layer, top to bottom: [{code, file, name, agent, core, source}] — the profile's layers above A1, the core four, its layers below A4."""
    from . import profile as _p
    from . import parts
    core = [{'code': c, 'file': f, 'name': n, 'agent': a, 'core': True, 'source': 'SDEM' if c != parts.a2_code() else 'ext:bian'} for c, f, n, a in CORE
            if c != parts.a2_code() or parts.bian_on()]   # BX-04, BX-13: no A2 layer where BIAN is off
    own = (_p.ACTIVE or {}).get('layers', [])
    was = {v: k for k, v in ((_p.ACTIVE or {}).get('_numbering') or {}).items()}   # DL-25: an own layer renumbered for this workspace, by its profile code
    def row(l): return {'code': l['code'], 'file': l['file'], 'name': l.get('name') or l['code'], 'agent': f"sdem-layer-{was.get(l['code'], l['code']).lower()}", 'core': False,   # its agent keeps its name (CTL-19)
                        **({'code_0_19': was[l['code']]} if l['code'] in was else {}),
                        'source': l.get('source', 'organisation profile'), 'description': l.get('description', '')}
    above = [row(l) for l in own if l['position'] == 'above']   # listed nearest A1 first
    below = [row(l) for l in own if l['position'] == 'below']   # listed nearest A4 first
    across = [{**row(l), 'across': True} for l in own if l['position'] == 'across']   # LR-11: beside the stack, after it
    return list(reversed(above)) + core + below + across


def codes(): return [l['code'] for l in layers()]


def order(direction='down'):
    c = codes(); return c if direction == 'down' else list(reversed(c))


def file_of(code): return next((l['file'] for l in layers() if l['code'] == code), None)


def name_of(code): return next((l['name'] for l in layers() if l['code'] == code), code)


def is_core(code): return code in CORE_CODES


def adjacent(upper, lower):
    """Whether `lower` sits directly below `upper`."""
    c = codes(); return upper in c and lower in c and c.index(lower) - c.index(upper) == 1


def graph_file(code):
    """A layer's graph file in a store: by its layer id where the workspace is in the 0.20 form (DL-10), 0.19's name otherwise."""
    from . import parts
    from .identity import layer_id
    lid = layer_id(code)
    if lid and parts.migrated(): return f'{lid}.graph.json'
    core = {_L('business'): 'a1-business.graph.json', _L('bian'): 'a2-service-domain.graph.json', _L('data'): 'data.graph.json', _L('application'): 'a3-application.graph.json', _L('technology'): 'a4-technology.graph.json'}
    if code in core: return core[code]
    from . import profile as _p
    was = {v: k for k, v in ((_p.ACTIVE or {}).get('_numbering') or {}).items()}   # DL-25: a profile layer's graph file keeps its profile code
    return f'{was.get(code, code).lower()}.graph.json'


class _LiveMap(Mapping):
    def __init__(self, fn): self._fn = fn
    def __getitem__(self, k): return self._fn()[k]
    def __iter__(self): return iter(self._fn())
    def __len__(self): return len(self._fn())
    def __repr__(self): return repr(self._fn())


class _LiveSeq(Sequence):
    def __init__(self, fn): self._fn = fn
    def __getitem__(self, i): return self._fn()[i]
    def __len__(self): return len(self._fn())
    def __repr__(self): return repr(self._fn())
    def __add__(self, other): return list(self._fn()) + list(other)
    def __radd__(self, other): return list(other) + list(self._fn())


def titled(core_names):
    """A live map layer → title: a module's own titles for the core four, each profile layer's name, in layer order."""
    return _LiveMap(lambda: {l['code']: core_names.get(l['code'], l['name']) if l['core'] else l['name'] for l in layers()})


FILES = _LiveMap(lambda: {l['code']: l['file'] for l in layers()})               # layer code → workspace file
CODES = _LiveSeq(codes)                                                           # layer codes, top to bottom
AGENTS = _LiveMap(lambda: {l['agent']: l['code'] for l in layers()})              # layer agent → layer code
GRAPH_FILES = _LiveMap(lambda: {l['code']: graph_file(l['code']) for l in layers()})
DATASET_FILES = _LiveSeq(lambda: [l['file'] for l in layers()])
