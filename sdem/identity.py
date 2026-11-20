"""Stable identity for layers and types (docs/design/sdem-stable-identity-spec.md, ST-01…ST-05).

A layer and a type each have an id that never changes (`application`, `application.ApplicationComponent`); the A-number a person reads
(`A3`, `A3.ApplicationComponent`) is computed from the layers in order (ST-03). SDEM's code names layers and types by id through
`layer()` and `T()`, and every name is read through `metamodel/identity.json` (ST-04); 0.19's names keep working (ST-05).

Step 3 keeps 0.19's stack — Business, BIAN, Application, Technology — and its positions: BIAN's A2 is reserved whether or not it is on
(BX-04), so every computed A-number is 0.19's and every answer is the same (P1)."""
import json
from collections.abc import Mapping as _Mapping, Sequence as _Sequence, Set as _Set
from functools import lru_cache

from .paths import DATA_ROOT


class IdentityError(ValueError):
    """A layer or type name the identity table does not know — never guessed (ST-04)."""


@lru_cache(maxsize=1)
def table():
    return json.loads((DATA_ROOT / 'metamodel' / 'identity.json').read_text(encoding='utf-8'))


@lru_cache(maxsize=1)
def _index():
    t = table()
    code = {l['id']: l.get('code_0_19') for l in t['layers']}   # 0.19's code of each layer — how an unmigrated file names it
    layer_of_code = {v: k for k, v in code.items() if v}
    by_id = {x['id']: x for x in t['types']}
    by_old = {x['name_0_19']: x['id'] for x in t['types'] if x.get('name_0_19')}
    return code, layer_of_code, by_id, by_old


_VERSION = [0]   # bumped when the layers in use change (BIAN switched for the workspace at hand): every computed name is recomputed


def stack():
    """The layers in use, top to bottom (DL-06): SDEM's core layers, and an extension's layer where it is on (BIAN, BX-10…BX-13)."""
    return _stack(_VERSION[0])


@lru_cache(maxsize=8)
def _stack(_v):
    from . import parts
    on = {'ext:bian': parts.bian_on()}
    return tuple(l['id'] for l in sorted(table()['layers'], key=lambda l: l['order']) if l['provided_by'] == 'core' or on.get(l['provided_by'], False))


def changed():
    """The layers in use changed: forget every computed name (called by parts when BIAN is switched for a workspace)."""
    _VERSION[0] += 1
    _ids_folder.cache_clear()
    for f in (layer, T, F, display, display_layer, stored, stored_layer):
        f.cache_clear()


@lru_cache(maxsize=None)
def F(layer_id):
    """A layer's file in the workspace at hand (DL-10): named by its id in a migrated workspace (application.json), 0.19's name
    otherwise (a3-application.json)."""
    from . import parts
    l = next((x for x in table()['layers'] if x['id'] == layer_id), None)
    if l is None: raise IdentityError(f'{layer_id!r} is not a layer id')
    return f'{layer_id}.json' if parts.migrated() or not l.get('file') else l['file']


@lru_cache(maxsize=None)   # called in the engines' loops; cleared when the layers in use change
def layer(layer_id):
    """The A-code a person reads for a layer id, from the layers in use (DL-06): layer('application') → 'A3' (default) or 'A4' (with
    BIAN). A layer that is not in use gets a code no record ever has — '(bian)' — so nothing of it is ever matched or mixed up."""
    code = _index()[0]
    if layer_id not in code: raise IdentityError(f'{layer_id!r} is not a layer id — layer ids: {", ".join(code)}')
    st = stack()
    return f'A{st.index(layer_id) + 1}' if layer_id in st else f'({layer_id})'


def layer_id(code_or_id):
    """The layer id for an A-code as read now, or a layer id: 'A3' → 'application'. None for a layer the table does not hold (a profile's own)."""
    code = _index()[0]
    if code_or_id in code: return code_or_id
    return next((i for i in code if layer(i) == code_or_id), None)


@lru_cache(maxsize=None)   # called in the engines' loops; the stack is fixed in step 3 — step 4 clears it when it changes
def T(type_id):
    """The type name a person reads (and SDEM's records hold in 0.20) for a type id: T('application.ApplicationComponent') → 'A3.ApplicationComponent'."""
    by_id = _index()[2]
    if type_id not in by_id: raise IdentityError(f'{type_id!r} is not a type id — see sdem types --ids')
    lid, name = type_id.split('.', 1)
    return f'{layer(lid)}.{name}'


def type_id(name):
    """The type id for a name as read now, an id, or a 0.19 name: 'A3.ApplicationComponent' → 'application.ApplicationComponent'.
    None for a type the table does not hold (an extension's or a profile's own, e.g. SEC.S.SecurityControl)."""
    _, _, by_id, by_old = _index()
    if name in by_id: return name
    return _now().get(name) or by_old.get(name)


def ids():
    """Every type: [{'id', 'name'}] — the name as a person reads it now."""
    return [{'id': x['id'], 'name': T(x['id'])} for x in table()['types']]


# ---- step 4b of 0.20: files store ids, SDEM works in the names a person reads (docs/design/sdem-data-layer-spec.md, DL-10, DL-11)
# In memory, a type is the name a person reads (T(id)). A file holds ids (a migrated workspace: workspace.json "names": "ids") or
# 0.19's names (every other). Reading accepts all three — an id, a name as a person reads it now, a 0.19 name, in that order —
# and writing gives the file's own form, so no file is ever mixed (DL-12). Graph stores are derived: written as built, never translated.
LAYER_KEYS = frozenset({'level', 'owner_layer'})   # never 'layer': ArchiMate's own (business, application, technology — the same words as SDEM's layer ids)


@lru_cache(maxsize=None)
def display(name, legacy=False):
    """The name a person reads now. An id is always read as one. Otherwise a file's form decides: an unmigrated file (legacy) holds
    0.19's names; a migrated one ids — and what a person wrote there, the names as read now. Anything else unchanged."""
    if not isinstance(name, str) or '.' not in name: return name
    _, _, by_id, by_old = _index()
    if name in by_id: return T(name)
    if legacy and name in by_old: return T(by_old[name])
    if name in _now(): return name
    return T(by_old[name]) if name in by_old else name


@lru_cache(maxsize=None)
def display_layer(code, legacy=False):
    if not isinstance(code, str): return code
    code_of, of_code = _index()[:2]
    if code in code_of: return layer(code)
    if legacy and code in of_code: return layer(of_code[code])
    return code


def _now():
    """{name as read now: type id}."""
    return _now_v(_VERSION[0])


@lru_cache(maxsize=8)
def _now_v(_v): return {T(x['id']): x['id'] for x in table()['types']}


@lru_cache(maxsize=None)
def stored(name, ids):
    """The name a file holds for a name in memory: its id (ids=True) or its 0.19 name (an unmigrated workspace)."""
    if not isinstance(name, str) or '.' not in name: return name
    tid = _now().get(name) or (name if name in _index()[2] else None)
    if not tid: return name
    return tid if ids else (_index()[2][tid].get('name_0_19') or tid)


@lru_cache(maxsize=None)
def stored_layer(code, ids):
    if not isinstance(code, str): return code
    code_of = _index()[0]
    lid = code if code in code_of else layer_id(code)
    if not lid: return code
    return lid if ids else (code_of[lid] or lid)


def _walk(x, f, fl, key=None):
    if isinstance(x, (dict, _Mapping)): return {f(k) if isinstance(k, str) else k: _walk(v, f, fl, k) for k, v in x.items()}   # a live table too
    if isinstance(x, (list, tuple, _Sequence)) and not isinstance(x, str): return [_walk(v, f, fl, key) for v in x]
    if isinstance(x, str): return fl(x) if key in LAYER_KEYS else f(x)
    return x


def read_names(doc, legacy=False): return _walk(doc, lambda s: display(s, legacy), lambda s: display_layer(s, legacy))


def store_names(doc, ids): return _walk(doc, lambda s: stored(s, ids), lambda s: stored_layer(s, ids))


def _derived(path):
    p = str(path).replace('\\', '/')
    return p.endswith('.graph.json') or '/graph/' in p or p.endswith('/metamodel/identity.json')


@lru_cache(maxsize=256)
def _ids_folder(folder):
    """Does the workspace this folder is in store ids (migrated, DL-12)? Its workspace.json says "names": "ids"."""
    from pathlib import Path
    for d in (Path(folder), *Path(folder).parents):
        w = d / 'workspace.json'
        if w.is_file():
            try: return json.loads(w.read_text(encoding='utf-8')).get('names') == 'ids'
            except (OSError, ValueError): return False
    return False


def stores_ids(path):
    from pathlib import Path
    return _ids_folder(str(Path(path).resolve().parent))


def load(path):
    """A JSON file, its names as a person reads them now — the one way SDEM reads a design's files (DL-11)."""
    from pathlib import Path
    doc = json.loads(Path(path).read_text(encoding='utf-8'))
    return doc if _derived(path) else read_names(doc, legacy=not stores_ids(path))


def for_file(path, obj):
    """What to write to `path`: obj with the names the file's workspace stores (ids or 0.19's)."""
    return obj if _derived(path) else store_names(obj, stores_ids(path))


def loads(text, path=None):
    """JSON text of a design file (read by its caller, e.g. to take its checksum), its names as a person reads them now (DL-11)."""
    doc = json.loads(text)
    if path is None: return read_names(doc)
    return doc if _derived(path) else read_names(doc, legacy=not stores_ids(path))



# ---- tables computed from the layers in use (DL-06): a module's table of layers or types is live — recomputed when the stack changes


class _Live:
    __slots__ = ('_fn', '_v', '_val')
    def __init__(self, fn): self._fn, self._v, self._val = fn, None, None
    def _get(self):
        if self._v != _VERSION[0]: self._val, self._v = self._fn(), _VERSION[0]
        return self._val
    def __repr__(self): return repr(self._get())
    def __eq__(self, other): return self._get() == (other._get() if isinstance(other, _Live) else other)
    def __hash__(self): return id(self)


class LiveMap(_Live, _Mapping):
    __slots__ = ()
    def __getitem__(self, k): return self._get()[k]
    def __iter__(self): return iter(self._get())
    def __len__(self): return len(self._get())
    def __or__(self, other): return {**self._get(), **other}
    def copy(self): return dict(self._get())


class LiveSeq(_Live, _Sequence):
    __slots__ = ()
    def __getitem__(self, i): return self._get()[i]
    def __len__(self): return len(self._get())
    def __add__(self, other): return self._get() + type(self._get())(other)
    def __radd__(self, other): return type(self._get())(other) + self._get()


class LiveSet(_Live, _Set):
    __slots__ = ()
    def __contains__(self, x): return x in self._get()
    def __iter__(self): return iter(self._get())
    def __len__(self): return len(self._get())
    def __or__(self, other): return self._get() | set(other)
    def __and__(self, other): return self._get() & set(other)
    def __sub__(self, other): return self._get() - set(other)


def live(fn):
    """A module's table that names layers or types, recomputed when the layers in use change: live(lambda: {...})."""
    v = fn()
    return LiveMap(fn) if isinstance(v, _Mapping) else LiveSet(fn) if isinstance(v, _Set) else LiveSeq(fn)   # by kind: titled() gives a Mapping that is not a dict


def readable(name):
    """A name for a message: as read now; a type of a layer not in use by its id ('bian.ServiceDomain', never '(bian).ServiceDomain')."""
    if isinstance(name, str) and name.startswith('('):
        return type_id(name) or name
    return name
