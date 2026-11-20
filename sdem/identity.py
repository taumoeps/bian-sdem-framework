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
