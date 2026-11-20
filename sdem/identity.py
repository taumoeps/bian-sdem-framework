"""Stable identity for layers and types (docs/design/sdem-stable-identity-spec.md, ST-01…ST-05).

A layer and a type each have an id that never changes (`application`, `application.ApplicationComponent`); the A-number a person reads
(`A3`, `A3.ApplicationComponent`) is computed from the layers in order (ST-03). SDEM's code names layers and types by id through
`layer()` and `T()`, and every name is read through `metamodel/identity.json` (ST-04); 0.19's names keep working (ST-05).

Step 3 keeps 0.19's stack — Business, BIAN, Application, Technology — and its positions: BIAN's A2 is reserved whether or not it is on
(BX-04), so every computed A-number is 0.19's and every answer is the same (P1)."""
import json
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
    code = {l['id']: l['code_0_19'] for l in t['layers']}   # ST-03, step 3: the position in the full stack, BIAN's kept (BX-04)
    layer_of_code = {v: k for k, v in code.items()}
    by_id = {x['id']: x for x in t['types']}
    by_old = {x['name_0_19']: x['id'] for x in t['types']}
    return code, layer_of_code, by_id, by_old


@lru_cache(maxsize=None)   # called in the engines' loops; the stack is fixed in step 3 — step 4 clears it when it changes
def layer(layer_id):
    """The A-code a person reads for a layer id: layer('application') → 'A3'."""
    code = _index()[0]
    if layer_id not in code: raise IdentityError(f'{layer_id!r} is not a layer id — layer ids: {", ".join(code)}')
    return code[layer_id]


def layer_id(code_or_id):
    """The layer id for an A-code or a layer id: 'A3' → 'application'. None for a layer the table does not hold (a profile's own)."""
    code, of_code = _index()[:2]
    return code_or_id if code_or_id in code else of_code.get(code_or_id)


@lru_cache(maxsize=None)   # called in the engines' loops; the stack is fixed in step 3 — step 4 clears it when it changes
def T(type_id):
    """The type name a person reads (and SDEM's records hold in 0.20) for a type id: T('application.ApplicationComponent') → 'A3.ApplicationComponent'."""
    by_id = _index()[2]
    if type_id not in by_id: raise IdentityError(f'{type_id!r} is not a type id — see sdem types --ids')
    lid, name = type_id.split('.', 1)
    return f'{layer(lid)}.{name}'


def type_id(name):
    """The type id for a type name of 0.19 or 0.20 or an id: 'A3.ApplicationComponent' → 'application.ApplicationComponent'.
    None for a type the table does not hold (an extension's or a profile's own, e.g. SEC.S.SecurityControl)."""
    _, _, by_id, by_old = _index()
    if name in by_id: return name
    if name in by_old: return by_old[name]
    code, _, rest = str(name).partition('.')
    lid = layer_id(code)
    return f'{lid}.{rest}' if lid and f'{lid}.{rest}' in by_id else None


def ids():
    """Every type: [{'id', 'name'}] — the name as a person reads it now."""
    return [{'id': x['id'], 'name': T(x['id'])} for x in table()['types']]


# ---- step 4b of 0.20: files store ids, SDEM works in the names a person reads (docs/design/sdem-data-layer-spec.md, DL-10, DL-11)
# In memory, a type is the name a person reads (T(id)). A file holds ids (a migrated workspace: workspace.json "names": "ids") or
# 0.19's names (every other). Reading accepts all three — an id, a name as a person reads it now, a 0.19 name, in that order —
# and writing gives the file's own form, so no file is ever mixed (DL-12). Graph stores are derived: written as built, never translated.
LAYER_KEYS = frozenset({'level', 'owner_layer'})   # never 'layer': ArchiMate's own (business, application, technology — the same words as SDEM's layer ids)


@lru_cache(maxsize=None)
def display(name):
    """The name a person reads now, for a type id, a name as read now or a 0.19 name; anything else unchanged."""
    if not isinstance(name, str) or '.' not in name: return name
    _, _, by_id, by_old = _index()
    if name in by_id: return T(name)
    tid = _now().get(name) or by_old.get(name)
    return T(tid) if tid else name


@lru_cache(maxsize=None)
def display_layer(code):
    if not isinstance(code, str): return code
    code_of, of_code = _index()[:2]
    if code in code_of: return layer(code)
    return code if code in _now_layers() else (layer(of_code[code]) if code in of_code else code)


def _now():
    """{name as read now: type id}."""
    return {T(x['id']): x['id'] for x in table()['types']}


def _now_layers(): return {layer(l['id']) for l in table()['layers']}


@lru_cache(maxsize=None)
def stored(name, ids):
    """The name a file holds for a name in memory: its id (ids=True) or its 0.19 name."""
    if not isinstance(name, str) or '.' not in name: return name
    tid = _now().get(name) or (name if name in _index()[2] else None)
    if not tid: return name
    return tid if ids else _index()[2][tid]['name_0_19']


@lru_cache(maxsize=None)
def stored_layer(code, ids):
    if not isinstance(code, str): return code
    code_of, of_code = _index()[:2]
    lid = next((i for i in code_of if layer(i) == code), None) or (code if code in code_of else None)
    if not lid: return code
    return lid if ids else code_of[lid]


def _walk(x, f, fl, key=None):
    if isinstance(x, dict): return {f(k) if isinstance(k, str) else k: _walk(v, f, fl, k) for k, v in x.items()}
    if isinstance(x, list): return [_walk(v, f, fl, key) for v in x]
    if isinstance(x, str): return fl(x) if key in LAYER_KEYS else f(x)
    return x


def read_names(doc): return _walk(doc, display, display_layer)


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
    return doc if _derived(path) else read_names(doc)


def for_file(path, obj):
    """What to write to `path`: obj with the names the file's workspace stores (ids or 0.19's)."""
    return obj if _derived(path) else store_names(obj, stores_ids(path))


def loads(text, path=None):
    """JSON text of a design file (read by its caller, e.g. to take its checksum), its names as a person reads them now (DL-11)."""
    doc = json.loads(text)
    return doc if path is not None and _derived(path) else read_names(doc)
