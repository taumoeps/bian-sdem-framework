"""The layer registry (docs/design/sdem-layers-spec.md, LR-01…LR-10): the layers a workspace works across, in order.

SDEM's four core layers — A1 Business, A2 Service Domain (BIAN), A3 Application, A4 Technology — are always present. An organisation
profile (sdem/profile.py) may add layers **above A1** or **below A4**, each with its own record file, types and link types to its
neighbour. Everything that works layer by layer — the workspace's files, the ledger, check, build, trace, impact, validation,
requirements, change sets, the dashboards — reads the layers from here, so a profile's layers take part without code changes.

The collections below are *live*: they reflect the active profile at the moment they are read (FILES, CODES, AGENTS).
"""
from collections.abc import Mapping, Sequence

CORE = (('A1', 'a1-business.json', 'A1 Business', 'sdem-a1-business'),
        ('A2', 'a2-service-domain.json', 'A2 BIAN', 'sdem-a2-bian'),
        ('A3', 'a3-application.json', 'A3 Application', 'sdem-a3-application'),
        ('A4', 'a4-technology.json', 'A4 Technology', 'sdem-a4-technology'))
CORE_CODES = tuple(c[0] for c in CORE)
RESERVED_FILES = {c[1] for c in CORE} | {'mappings.json', 'requirements.json', 'workspace.json', 'sdem-ledger.json', 'sdem-profile.json', 'governance.json'}


def agent_for(code):
    """The layer agent's name: SDEM's for a core layer; sdem-layer-<code> for a profile layer (CTL-19 scopes it to that layer)."""
    core = {c[0]: c[3] for c in CORE}
    return core.get(code) or f'sdem-layer-{code.lower()}'


def layers():
    """Every layer, top to bottom: [{code, file, name, agent, core, source}] — the profile's layers above A1, the core four, its layers below A4."""
    from . import profile as _p
    core = [{'code': c, 'file': f, 'name': n, 'agent': a, 'core': True, 'source': 'SDEM'} for c, f, n, a in CORE]
    own = (_p.ACTIVE or {}).get('layers', [])
    def row(l): return {'code': l['code'], 'file': l['file'], 'name': l.get('name') or l['code'], 'agent': agent_for(l['code']), 'core': False,
                        'source': l.get('source', 'organisation profile'), 'description': l.get('description', '')}
    above = [row(l) for l in own if l['position'] == 'above']   # listed nearest A1 first
    below = [row(l) for l in own if l['position'] == 'below']   # listed nearest A4 first
    return list(reversed(above)) + core + below


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
    core = {'A1': 'a1-business.graph.json', 'A2': 'a2-service-domain.graph.json', 'A3': 'a3-application.graph.json', 'A4': 'a4-technology.graph.json'}
    return core.get(code) or f'{code.lower()}.graph.json'


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
