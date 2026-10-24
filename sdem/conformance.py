"""Data-model conformance: enforce the logical constraints on level exports.

Errors (the export does not conform):
  LC-04 required attribute missing · LC-05 wrong type · LC-06 value not allowed · LC-07 same-level reference
  does not resolve · LC-09 duplicate natural key · LC-10 cardinality maximum exceeded (BIAN / ArchiMate rows).
Warnings (the export is usable but incomplete or dated):
  LC-08 cross-level reference does not resolve in the loaded estate (a join key the inference engine cannot use)
  · LC-10m cardinality minimum not met (exports may be partial selections) · LC-13 deprecated attribute in use
  · attribute not defined in the model.
LC-01…LC-03 and LC-11 are checked by the graph loader and the registry validator; LC-12 by sdem-diff.
"""
import json, re
from collections import Counter
from functools import lru_cache
from pathlib import Path

from .metamodel import ROOT

MM_DIR = ROOT / 'metamodel'
LIFECYCLE = ('planned', 'active', 'deprecated', 'retired')
TYPES = {'string': str, 'list<string>': list, 'map<string,string>': dict, 'integer': int, 'boolean': bool, 'date': str}
DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def _j(p): return json.loads(Path(p).read_text(encoding='utf-8'))


@lru_cache(maxsize=1)
def model():
    """Attribute definitions by entity type, the common attributes, and the cardinality rows that are enforced."""
    rec = _j(MM_DIR / 'entity-attributes.json'); byent = {}
    for a in rec['attributes']: byent.setdefault(a['entity'], {})[a['name']] = a
    rows = [c for c in _j(MM_DIR / 'level-relationships.json')['constraints'] if (c.get('cardinality') or {}).get('basis') not in (None, 'SDEM default')]
    return byent, {c['name']: c for c in rec.get('common_attributes', [])}, rows


def definitions(mm, etype):
    """Every attribute an instance of etype may carry: common, then inherited (root first), then its own."""
    byent, common, _ = model(); defs = dict(common)
    for t in list(reversed(list(mm.ancestors(etype)))) + [etype]: defs.update(byent.get(t, {}))
    return defs


def type_ok(a, v, name):
    want = TYPES.get(a['type'])
    if want is None: return True
    if v is None and name == 'behavior_qualifier': return True
    if want is int and isinstance(v, bool): return False
    if not isinstance(v, want): return False
    if a['type'] == 'date' and not DATE.match(v): return False
    return not (want is int and (v < a.get('minimum', v) or v > a.get('maximum', v)))


def check_level(doc, mm, estate_index=None):
    """Check one level export. estate_index maps instance id -> type across every loaded level (for LC-08).
    Returns (errors, warnings, counts)."""
    _, _, rows = model()
    errors, warnings, n = [], [], Counter()
    local = {i['id']: i['type'] for i in doc.get('instances', [])}
    keys = Counter()
    for i in doc.get('instances', []):
        if not mm.known(i['type']): continue  # reported by the graph loader (LC-02)
        defs = definitions(mm, i['type']); at = i.get('attributes') or {}; who = f"instance {i['id']}"
        for k, a in defs.items():
            if a['required'] and a['status'] == 'active':
                n['LC-04 checked'] += 1
                if k not in at: n['LC-04 failed'] += 1; errors.append(f"{who}: required attribute {k!r} missing (LC-04)")
        for k, v in at.items():
            a = defs.get(k)
            if not a:
                n['undefined'] += 1; warnings.append(f"{who}: attribute {k!r} is not defined for {i['type']}"); continue
            if a['status'] == 'deprecated':
                n['LC-13 failed'] += 1; warnings.append(f"{who}: attribute {k!r} is deprecated (LC-13)")
            if a['type'] in TYPES:
                n['LC-05 checked'] += 1
                if not type_ok(a, v, k): n['LC-05 failed'] += 1; errors.append(f"{who}: attribute {k!r} should be {a['type']}, got {v!r} (LC-05)"); continue
            if a.get('values'):
                for x in (v if isinstance(v, list) else [v]):
                    n['LC-06 checked'] += 1
                    if x not in a['values']: n['LC-06 failed'] += 1; errors.append(f"{who}: attribute {k!r} value {x!r} is not one of {a['values']} (LC-06)")
            if a.get('kind') == 'reference':
                targets = [i['type'] if t == 'same entity type' else t for t in a['references']]
                same = all(mm.level(t) == doc['level'] for t in targets)
                for x in (v if isinstance(v, list) else [v]):
                    if same:
                        n['LC-07 checked'] += 1; t = local.get(x)
                        if not (t and any(mm.is_a(t, r) for r in targets)):
                            n['LC-07 failed'] += 1; errors.append(f"{who}: attribute {k!r} refers to {x!r}, which is not a {' or '.join(targets)} in this export (LC-07)")
                    elif estate_index is not None:
                        lvls = {mm.level(t) for t in targets}
                        if not any(l in estate_index['levels'] for l in lvls): continue  # target level not loaded: nothing to check against
                        n['LC-08 checked'] += 1; t = estate_index['types'].get(x)
                        if not (t and any(mm.is_a(t, r) for r in targets)):
                            n['LC-08 failed'] += 1; warnings.append(f"{who}: attribute {k!r} refers to {x!r}, which is not a {' or '.join(targets)} in the loaded estate (LC-08)")
        if i.get('lifecycle_status'):
            n['LC-06 checked'] += 1
            if i['lifecycle_status'] not in LIFECYCLE: n['LC-06 failed'] += 1; errors.append(f"{who}: lifecycle_status {i['lifecycle_status']!r} is not one of {list(LIFECYCLE)} (LC-06)")
        key = ((mm.entities.get(i['type']) or {}).get('identifier') or {}).get('key') or []
        if key and all(k in i or k in at for k in key):
            keys[(i['type'],) + tuple(json.dumps(i.get(k, at.get(k)), sort_keys=True) for k in key)] += 1
    n['LC-09 checked'] += len(keys)
    for k, c in keys.items():
        if c > 1: n['LC-09 failed'] += c - 1; errors.append(f"{c} instances of {k[0]} share the natural key {', '.join(k[1:])} (LC-09)")
    for c in rows:
        if c['level'] != doc['level']: continue
        cd = c['cardinality']
        links = [(r['source'], r['target']) for r in doc.get('relationships', []) if r['kind'] == c['kind'] and r['source'] in local and r['target'] in local
                 and mm.is_a(local[r['source']], c['source_type']) and mm.is_a(local[r['target']], c['target_type'])]
        for side, card, ends in (('src', cd['source_per_target'], [t for t in local if mm.is_a(local[t], c['target_type'])]),
                                 ('tgt', cd['target_per_source'], [x for x in local if mm.is_a(local[x], c['source_type'])])):
            lo, hi = card.split('..')
            for iid in ends:
                cnt = sum(1 for a, b in links if (b if side == 'src' else a) == iid)
                n['LC-10 checked'] += 1; n['LC-10m checked'] += 1
                other = c['source_type'] if side == 'src' else c['target_type']
                if hi != '*' and cnt > int(hi):
                    n['LC-10 failed'] += 1; errors.append(f"instance {iid}: {cnt} {c['kind']} links with {other}, at most {hi} allowed by {c['id']} (LC-10)")
                if cnt < int(lo):
                    n['LC-10m failed'] += 1; warnings.append(f"instance {iid}: {cnt} {c['kind']} links with {other}, {c['id']} expects at least {lo} (LC-10m)")
    return errors, warnings, n


def estate_index(docs):
    return {'levels': {d['level'] for d in docs}, 'types': {i['id']: i['type'] for d in docs for i in d.get('instances', [])}}
