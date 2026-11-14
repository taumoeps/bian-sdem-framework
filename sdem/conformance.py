"""Data-model conformance: enforce the logical constraints on architecture datasets.

Errors (the architecture dataset does not conform):
  LC-04 required attribute missing — absent, empty, or a placeholder such as TBD (a warning on a `planned` instance) · LC-05 wrong type · LC-06 value not allowed · LC-07 same-level reference
  does not resolve · LC-09 duplicate natural key · LC-10 cardinality maximum exceeded (BIAN / ArchiMate rows).
Warnings (the architecture dataset is usable but incomplete or dated):
  LC-08 cross-level reference does not resolve in the loaded workspace (a join key the inference engine cannot use)
  · LC-10m cardinality minimum not met (architecture datasets may be partial selections) · LC-13 deprecated attribute in use
  · attribute not defined in the model · LC-04p a placeholder or empty value in an optional attribute · LC-09n two names that differ
  only in case, spacing or punctuation (a possible duplicate) · LC-14 an attribute source that names no attribute of the record, or is not kind:ref
  · LC-15 a platform that hosts something is on no communication network (RA4-37) · LC-16 a shape in no network zone, or in more than one
  · LC-18 an internet-facing shape outside a DMZ, or a DMZ shape that is not internet facing · LC-17 a level-0 zone with no internal zone yet.
  · LC-19 an inferred zone placement not yet confirmed or rejected · LC-20 a shape placed against strong hosting evidence
  · LC-21 an A4 shape connected to nothing inside A4 (another layer does not count) · LC-22 an internet-facing A3 interface exposed through nothing
  (both checked over the whole workspace: sdem/graph.py FederatedGraph.unconnected, unexposed).
  Error: LC-17 the zone structure contradicts itself (a kind wrong for its level, a zone in the wrong parent, two internal zones, two cloud zones).
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
def placeholders():
    """The words that stand for a value nobody knows yet (metamodel: entity-attributes.json › placeholders; LC-04, owner's decision D1)."""
    return frozenset(w.casefold() for w in (_j(MM_DIR / 'entity-attributes.json').get('placeholders') or {}).get('values', []))


def unknown_value(v, allowed=()):
    """Why a value says nothing: 'empty', 'placeholder' — or None when it is a value. An allowed enumeration value is always a value."""
    if isinstance(v, str):
        t = v.strip()
        if not t: return 'empty'
        if t in allowed: return None
        w = placeholders()
        if t.casefold() in w: return 'placeholder'
        if t.startswith('/') and any(seg.strip().casefold() in w for seg in t.split('/') if seg.strip()): return 'placeholder'   # a path such as /TBD or /payments/TBD
        return None
    if isinstance(v, list):
        if not v: return None   # an empty list says 'none' (a BIAN operation with no inputs) — a value
        kinds = [unknown_value(x, allowed) for x in v]
        return 'placeholder' if 'placeholder' in kinds else ('empty' if all(kinds) else None)
    if isinstance(v, dict) and not v: return 'empty'
    return None


def natural(v):
    """A natural-key value compared as a person reads it: case, spacing and punctuation ignored (LC-09n)."""
    return ' '.join(re.sub(r'[^0-9a-z]+', ' ', v.casefold()).split()) if isinstance(v, str) else v


OWNERS = {'owning interface': 'A3.ApplicationInterface', 'owning service domain': 'A2.ServiceDomain'}   # identifier keys held as a whole-part link, not an attribute


def owner_of(iid, want, mm, local, parents, depth=4):
    """The nearest whole of type `want` above iid, through composition and aggregation (e.g. operation ← group ← service domain)."""
    seen, frontier = {iid}, [iid]
    for _ in range(depth):
        nxt = []
        for x in frontier:
            for p in parents.get(x, ()):
                if p in seen: continue
                if local.get(p) and mm.is_a(local[p], want): return p
                seen.add(p); nxt.append(p)
        frontier = nxt
    return None


@lru_cache(maxsize=2)
def model(base=False):
    """Attribute definitions by entity type, the common attributes, and the cardinality rows that are enforced — with the active
    organisation profile's attributes added (base=True: SDEM's alone)."""
    rec = _j(MM_DIR / 'entity-attributes.json'); byent = {}
    for a in rec['attributes']: byent.setdefault(a['entity'], {})[a['name']] = a
    if not base:
        from . import profile as _p
        for ent, defs in _p.profile_attributes().items(): byent.setdefault(ent, {}).update(defs)
    rows = [c for c in _j(MM_DIR / 'level-relationships.json')['constraints'] if (c.get('cardinality') or {}).get('basis') not in (None, 'SDEM default')]
    return byent, {c['name']: c for c in rec.get('common_attributes', [])}, rows


def definitions(mm, etype):
    """Every attribute an instance of etype may carry: common, then inherited (root first), then its own."""
    byent, common, _ = model(); defs = dict(common)
    for t in list(reversed(list(mm.ancestors(etype)))) + [etype]: defs.update(byent.get(t, {}))
    return defs


def type_ok(a, v, name):
    if a.get('number'): return isinstance(v, (int, float)) and not isinstance(v, bool)   # a profile 'number' attribute
    want = TYPES.get(a['type'])
    if want is None: return True
    if v is None and name == 'behavior_qualifier': return True
    if want is int and isinstance(v, bool): return False
    if not isinstance(v, want): return False
    if a['type'] == 'date' and not DATE.match(v): return False
    return not (want is int and (v < a.get('minimum', v) or v > a.get('maximum', v)))


def check_level(doc, mm, estate_index=None):
    """Check one architecture dataset. estate_index maps instance id -> type across every loaded level (for LC-08).
    Returns (errors, warnings, counts)."""
    _, _, rows = model()
    errors, warnings, n = [], [], Counter()
    local = {i['id']: i['type'] for i in doc.get('instances', [])}
    byid = {i['id']: i for i in doc.get('instances', [])}
    from . import profile as _p
    own_rules = _p.rules()
    keys = Counter(); loose = {}
    parents = {}
    for r in doc.get('relationships', []):
        if r.get('kind') in ('composition', 'aggregation'): parents.setdefault(r['target'], []).append(r['source'])
    to_confirm = 0
    for i in doc.get('instances', []):
        if not mm.known(i['type']): continue  # reported by the graph loader (LC-02)
        defs = definitions(mm, i['type']); at = i.get('attributes') or {}; who = f"instance {i['id']}"
        mark = at.get('inferred')
        if str(i['id']).startswith('AID-') and not isinstance(mark, dict):   # CTL-16: an inferred record keeps its mark
            errors.append(f"{who}: inferred by sdem aid but its 'inferred' mark is missing — confirm it with `sdem aid confirm`, never by removing the mark (CTL-16)"); continue
        unconfirmed = isinstance(mark, dict) and mark.get('status') != 'confirmed'
        to_confirm += unconfirmed
        for k, a in defs.items():
            if a['required'] and a['status'] == 'active':
                n['LC-04 checked'] += 1
                why = 'absent' if k not in at else unknown_value(at[k], a.get('values') or ())
                if why:
                    said = '' if why == 'absent' else f" — {at[k]!r} is {'a placeholder' if why == 'placeholder' else 'empty'}, not a value"
                    unless = a.get('required_unless') or {}
                    if unless and all(at.get(x) == v for x, v in unless.items()):   # e.g. a BIAN domain whose pattern is not known yet: advise, do not reject
                        n['LC-04 to confirm'] += 1
                        warnings.append(f"{who}: {k!r} not known yet ({', '.join(f'{x} {v}' for x, v in unless.items())}) — give it when known (LC-04)"); continue
                    if i.get('lifecycle_status') == 'planned':  # a planned (target-design) record may not know every fact yet: warn, do not reject
                        n['LC-04 planned'] += 1
                        if not unconfirmed: warnings.append(f"{who}: planned instance — required attribute {k!r} not yet known{said} (LC-04)")   # inferred: in the summary
                    else:
                        n['LC-04 failed'] += 1
                        errors.append(f"{who}: required attribute {k!r} missing (LC-04)" if why == 'absent' else
                                      f"{who}: required attribute {k!r} has no value{said} — leave it out and mark the record planned until it is known (LC-04)")
            elif k in at and a['status'] != 'deprecated' and k not in ('inferred', 'sources'):
                why = unknown_value(at[k], a.get('values') or ())
                if why: n['LC-04p'] += 1; warnings.append(f"{who}: optional attribute {k!r} is {'a placeholder' if why == 'placeholder' else 'empty'} ({at[k]!r}) — leave it out until it is known (LC-04)")
        srcs = at.get('sources')
        if isinstance(srcs, dict):   # LC-14: where single values came from (CA-13) — only the record's own attributes, as kind:ref
            for k, ref in srcs.items():
                n['LC-14 checked'] += 1
                if k not in at and k not in ('name', 'description'):
                    n['LC-14 failed'] += 1; warnings.append(f"{who}: sources names {k!r}, which the record does not have (LC-14)")
                elif not (isinstance(ref, str) and all(re.match(r'^[a-z][a-z0-9_-]*:\S', x.strip()) for x in ref.split(','))):
                    n['LC-14 failed'] += 1; warnings.append(f"{who}: the source of {k!r} is {ref!r} — write it as kind:ref, e.g. document:DESIGN.md#4.2 (LC-14)")
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
                            n['LC-07 failed'] += 1; errors.append(f"{who}: attribute {k!r} refers to {x!r}, which is not a {' or '.join(targets)} in this architecture dataset (LC-07)")
                    elif estate_index is not None:
                        lvls = {mm.level(t) for t in targets}
                        if not any(l in estate_index['levels'] for l in lvls): continue  # target level not loaded: nothing to check against
                        n['LC-08 checked'] += 1; t = estate_index['types'].get(x)
                        if not (t and any(mm.is_a(t, r) for r in targets)):
                            n['LC-08 failed'] += 1; warnings.append(f"{who}: attribute {k!r} refers to {x!r}, which is not a {' or '.join(targets)} in the loaded workspace (LC-08)")
        if i.get('lifecycle_status'):
            n['LC-06 checked'] += 1
            if i['lifecycle_status'] not in LIFECYCLE: n['LC-06 failed'] += 1; errors.append(f"{who}: lifecycle_status {i['lifecycle_status']!r} is not one of {list(LIFECYCLE)} (LC-06)")
        key = ((mm.entities.get(i['type']) or {}).get('identifier') or {}).get('key') or []
        vals = {}
        for k in key:   # LC-09: a key part is a field, an attribute, or the whole the record is part of (OWNERS)
            if k in OWNERS: vals[k] = owner_of(i['id'], OWNERS[k], mm, local, parents)
            elif k in i: vals[k] = i[k]
            elif k in at: vals[k] = at[k]
        if key and all(k in vals and (k not in OWNERS or vals[k]) for k in key) and not any(unknown_value(vals[k]) for k in key if k not in OWNERS):
            keys[(i['type'],) + tuple(json.dumps(vals[k], sort_keys=True) for k in key)] += 1
            loose.setdefault((i['type'],) + tuple(json.dumps(natural(vals[k]), sort_keys=True) for k in key), set()).add(tuple(json.dumps(vals[k], sort_keys=True) for k in key))
    if own_rules:   # PR-04, PR-10, PR-11, PR-15 (sdem/comply.py evaluates; check enforces): the organisation's own rules inside this layer
        from .comply import evaluate
        inside = [r for r in own_rules if not r.get('across')]
        for f in evaluate({doc.get('level'): doc}, [], mm, inside, _p.exceptions()):
            if f['outcome'] == 'not_applicable': continue
            n['profile rule checked'] += 1
            if f['outcome'] != 'non_compliant': continue
            if (byid.get(f['record']) or {}).get('lifecycle_status') == 'planned': continue
            rule = next(r for r in inside if r['id'] == f['rule'])
            say = f"instance {f['record']}: {rule['id']} — {rule.get('message') or 'required by the organisation profile'}"
            n['profile rule failed'] += 1
            for part in f.get('parts') or [f['detail']]:
                (warnings if f['severity'] == 'warning' else errors).append(f"{say}: {part}")
    n['LC-09 checked'] += len(keys)
    for k, c in keys.items():
        if c > 1: n['LC-09 failed'] += c - 1; errors.append(f"{c} instances of {k[0]} share the natural key {', '.join(k[1:])} (LC-09)")
    for k, exact in loose.items():
        if len(exact) > 1:
            n['LC-09n'] += 1; warnings.append(f"possible duplicate: {k[0]} keys {' and '.join(sorted(', '.join(e) for e in exact))} differ only in case, spacing or punctuation — one record, or two? (LC-09n)")
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
    on_network(doc, mm, local, byid, warnings, n)   # LC-15
    zone_checks(doc, mm, local, byid, errors, warnings, n)   # LC-16…LC-18
    if to_confirm: warnings.append(f"{to_confirm} inferred record(s) to confirm — review them (marked 'inferred', with source, reasoning and confidence), then `sdem aid confirm` or `sdem aid reject` (CTL-16)")
    return errors, warnings, n


PLATFORM, NETWORK, ZONE = 'A4.InfrastructureComponent', 'A4.CommunicationNetwork', 'A4.NetworkZone'
ZONE_KINDS = {0: ('on_premises', 'cloud'), 1: ('internal', 'dmz'), 2: ('private',)}
UNPLACED = ('A4.CommunicationNetwork', 'A4.NetworkZone', 'A4.DeploymentEnvironment', 'A4.Path')   # networks, zones, environments (they group deployments: Z2) and paths are not placed


def zones_of(doc, mm, local=None):
    """Network zones (metamodel 0.10.0; docs/design/sdem-network-zones-design.md): {shape: [innermost zones it is in]} — directly (RA4-38: the
    zone holds it) or through what hosts it (a deployment or artifact assigned to a platform, software on a node, a service a platform
    realises, a part of a whole) — and {zone: parent zone} (RA4-39: the parent is composed of it)."""
    local = local or {i['id']: i['type'] for i in doc.get('instances', [])}
    direct, parent, hosts = {}, {}, {}
    for r in doc.get('relationships', []):
        a, b, k = r['source'], r['target'], r['kind']
        if a not in local or b not in local: continue
        if mm.is_a(local[a], ZONE):
            if k == 'aggregation' and not mm.is_a(local[b], NETWORK): direct.setdefault(b, []).append(a)
            elif k == 'composition' and mm.is_a(local[b], ZONE): parent[b] = a
            continue
        if mm.is_a(local[a], NETWORK) or mm.is_a(local[b], NETWORK) or mm.is_a(local[b], ZONE) or mm.is_a(local[a], 'A4.DeploymentEnvironment'): continue
        if k in ('assignment', 'composition', 'aggregation', 'realization'): hosts.setdefault(b, []).append(a)   # b runs on, or is part of, a
    def find(x, seen):
        if direct.get(x): return direct[x]
        for h in hosts.get(x, ()):
            if h not in seen:
                got = find(h, seen | {h})
                if got: return got
        return []
    shapes = {x: find(x, {x}) for x, t in local.items() if not any(mm.is_a(t, u) for u in UNPLACED)}
    return shapes, parent, direct


def zone_checks(doc, mm, local, byid, errors, warnings, n):
    """LC-16 every shape in one zone (warning) · LC-17 the zone structure holds (error) · LC-18 internet-facing shapes in a DMZ (warning)."""
    if doc.get('level') != 'A4': return
    zones = {x: (byid[x].get('attributes') or {}) for x, t in local.items() if mm.is_a(t, ZONE)}
    shapes, parent, direct = zones_of(doc, mm, local)
    if not zones:
        if shapes: n['LC-16 checked'] += 1; n['LC-16 failed'] += 1; warnings.append(f"no network zones recorded — place each of the {len(shapes)} shape(s) in a zone: on premises or cloud, internal or DMZ (RA4-38, LC-16)")
        return
    lvl = lambda z: zones[z].get('zone_level')
    for z, at in sorted(zones.items()):   # LC-17
        n['LC-17 checked'] += 1; bad = []
        if at.get('zone_level') in ZONE_KINDS and at.get('zone_kind') not in ZONE_KINDS[at['zone_level']]:
            bad.append(f"a level-{at['zone_level']} zone is {' or '.join(ZONE_KINDS[at['zone_level']])}, not {at.get('zone_kind')!r}")
        p = parent.get(z)
        if at.get('zone_level') == 0 and p: bad.append(f'a level-0 zone is inside no other zone, but {p} is composed of it')
        if at.get('zone_level') in (1, 2) and (not p or p not in zones or lvl(p) != at['zone_level'] - 1):
            bad.append(f"a level-{at['zone_level']} zone is part of a level-{at['zone_level'] - 1} zone (composition, RA4-39){f' — {p} is level {lvl(p)}' if p in zones else ''}")
        for b in bad: n['LC-17 failed'] += 1; errors.append(f"instance {z}: {b} (LC-17)")
    tops = [z for z in zones if lvl(z) == 0]
    for kind in ('on_premises', 'cloud'):
        same = sorted(z for z in tops if zones[z].get('zone_kind') == kind)
        if len(same) > 1: n['LC-17 failed'] += 1; errors.append(f"{len(same)} {kind} level-0 zones ({', '.join(same)}) — one per workspace (LC-17)")
    for t in tops:
        kids = [z for z in zones if parent.get(z) == t]
        inner = [z for z in kids if zones[z].get('zone_kind') == 'internal']; dmz = [z for z in kids if zones[z].get('zone_kind') == 'dmz']
        if len(inner) > 1: n['LC-17 failed'] += 1; errors.append(f"instance {t}: a level-0 zone has exactly one internal zone, not {len(inner)} (LC-17)")
        if not inner: n['LC-17 failed'] += 1; warnings.append(f"instance {t}: a level-0 zone has no internal zone yet — every shape belongs at least to an internal or DMZ zone (LC-17)")
        if len(dmz) > 1: n['LC-17 failed'] += 1; errors.append(f"instance {t}: a level-0 zone has at most one DMZ, not {len(dmz)} (LC-17)")
    for x, zs in sorted(shapes.items()):   # LC-16
        if (byid.get(x) or {}).get('lifecycle_status') == 'retired': continue
        n['LC-16 checked'] += 1
        inner = sorted(set(zs))
        if not inner:
            n['LC-16 failed'] += 1; warnings.append(f"instance {x}: is in no network zone — place it, or what it runs on, in an internal, DMZ or private zone (RA4-38, LC-16)")
        elif len(inner) > 1:
            n['LC-16 failed'] += 1; warnings.append(f"instance {x}: is in {len(inner)} zones ({', '.join(inner)}) — one innermost zone (LC-16)")
        elif lvl(inner[0]) == 0:
            n['LC-16 failed'] += 1; warnings.append(f"instance {x}: is in level-0 zone {inner[0]} — place it in its internal or DMZ zone, or a private zone inside one (LC-16)")
    def in_dmz(z):
        while z in zones:
            if zones[z].get('zone_kind') == 'dmz': return True
            z = parent.get(z)
        return False
    waiting = [r for r in doc.get('relationships', []) if isinstance(r.get('inferred'), dict) and r['inferred'].get('status') != 'confirmed']   # LC-19
    if waiting:
        n['LC-19 checked'] += 1; n['LC-19 failed'] += len(waiting)
        warnings.append(f"{len(waiting)} inferred link(s) to decide — zone placements and A4 connections: {', '.join(r['source'] + ' ' + r['kind'] + ' ' + r['target'] for r in waiting[:4])}"
                        f"{' …' if len(waiting) > 4 else ''}: sdem aid confirm|reject <shape> (LC-19)")
    from .hosting import evidence, policy   # LC-20: a shape placed against strong evidence
    sig = policy()['signals']; kind_of = {}
    for z in zones:
        t = z
        while t in zones and zones[t].get('zone_level') != 0: t = parent.get(t)
        kind_of[z] = zones.get(t, {}).get('zone_kind') if t else None
    for x, zs in sorted(shapes.items()):
        if x not in direct or not zs: continue
        placed = kind_of.get(zs[0])
        against = [e for e in evidence(byid[x], doc, mm, sig) if e['confidence'] == 'high' and e['points_to'] in ('cloud', 'on_premises') and e['points_to'] != placed]
        n['LC-20 checked'] += 1
        if placed and against:
            n['LC-20 failed'] += 1; warnings.append(f"instance {x}: is in a {placed} zone, but {against[0]['id']} ({against[0]['read']}) says {against[0]['points_to']} (LC-20)")
    for x, zs in sorted(shapes.items()):   # LC-18
        facing = ((byid.get(x) or {}).get('attributes') or {}).get('internet_facing') is True
        if not zs: continue
        n['LC-18 checked'] += 1
        if facing and not in_dmz(zs[0]): n['LC-18 failed'] += 1; warnings.append(f"instance {x}: is internet facing but in {zs[0]}, not a DMZ (LC-18)")
        if x in direct and not facing and in_dmz(zs[0]): n['LC-18 failed'] += 1; warnings.append(f"instance {x}: is in DMZ {zs[0]} but not internet facing — a DMZ holds only internet-facing shapes (LC-18)")


def networks_of(doc, mm, local=None):
    """Each platform's communication networks (RA4-37: platform association network, either way round) — its own, or else the
    networks of the node or device it runs on (assigned to it, or a part of it), the nearest first."""
    local = local or {i['id']: i['type'] for i in doc.get('instances', [])}
    own, hosts = {}, {}
    for r in doc.get('relationships', []):
        a, b, k = r['source'], r['target'], r['kind']
        if a not in local or b not in local: continue
        if k == 'association':
            for p, x in ((a, b), (b, a)):
                if mm.is_a(local[p], PLATFORM) and mm.is_a(local[x], NETWORK) and not mm.is_a(local[p], NETWORK): own.setdefault(p, []).append(x)
        elif k == 'aggregation' and mm.is_a(local[a], ZONE):   # RA4-38: the zone holds it — it is on that zone (0.10.0)
            if not mm.is_a(local[b], NETWORK): own.setdefault(b, []).append(a)
        elif mm.is_a(local[a], NETWORK) or mm.is_a(local[b], NETWORK) or mm.is_a(local[a], ZONE) or mm.is_a(local[b], ZONE): continue   # network nesting (RA4-27), zone nesting (RA4-39): not hosting
        elif k in ('assignment', 'composition', 'aggregation') and mm.is_a(local[a], PLATFORM) and mm.is_a(local[b], PLATFORM):
            hosts.setdefault(b, []).append(a)   # b runs on (or is part of) a
    def find(p, seen):
        if own.get(p): return own[p]
        for h in hosts.get(p, ()):
            if h not in seen:
                got = find(h, seen | {h})
                if got: return got
        return []
    return {p: find(p, {p}) for p in local if mm.is_a(local[p], PLATFORM)}


def on_network(doc, mm, local, byid, warnings, n):
    """LC-15 (metamodel 0.9.0): a platform that hosts something — a deployment, an artifact or system software assigned to it — or
    that a deployment environment groups is on at least one communication network, its own or that of the node it runs on.
    A warning: a design may not have recorded its networks yet."""
    if doc.get('level') != 'A4': return
    nets = networks_of(doc, mm, local)
    why = {}
    for r in doc.get('relationships', []):
        a, b, k = r['source'], r['target'], r['kind']
        if a not in local or b not in local: continue
        if k == 'assignment' and a in nets and any(mm.is_a(local[b], t) for t in ('A4.Deployment', 'A4.Artifact', 'A4.SystemSoftware')):
            why.setdefault(a, f'hosts {b}')
        if k == 'aggregation' and b in nets and mm.is_a(local[a], 'A4.DeploymentEnvironment'):
            why.setdefault(b, f'is in environment {a}')
    for p, reason in sorted(why.items()):
        if (byid.get(p) or {}).get('lifecycle_status') == 'retired': continue
        if not any(mm.is_a(local[p], t) for t in ('A4.Node', 'A4.Device', 'A4.SystemSoftware')): continue   # a deployment is on its platform's network
        n['LC-15 checked'] += 1
        if not nets[p]:
            n['LC-15 failed'] += 1
            warnings.append(f"instance {p}: {reason} but is on no communication network — connect it, or the node it runs on (RA4-37, LC-15)")


def natural_keys(doc, mm):
    """Each record's natural key (LC-09) as an exact and a loose (LC-09n) value: {id: (exact, loose)}; records whose key is incomplete are left out."""
    local = {i['id']: i['type'] for i in doc.get('instances', [])}
    parents = {}
    for r in doc.get('relationships', []):
        if r.get('kind') in ('composition', 'aggregation'): parents.setdefault(r['target'], []).append(r['source'])
    out = {}
    for i in doc.get('instances', []):
        key = ((mm.entities.get(i['type']) or {}).get('identifier') or {}).get('key') or []
        at = i.get('attributes') or {}; vals = {}
        for k in key:
            if k in OWNERS: vals[k] = owner_of(i['id'], OWNERS[k], mm, local, parents)
            elif k in i: vals[k] = i[k]
            elif k in at: vals[k] = at[k]
        if key and all(k in vals and (k not in OWNERS or vals[k]) for k in key) and not any(unknown_value(vals[k]) for k in key if k not in OWNERS):
            out[i['id']] = ((i['type'],) + tuple(json.dumps(vals[k], sort_keys=True) for k in key),
                            (i['type'],) + tuple(json.dumps(natural(vals[k]), sort_keys=True) for k in key))
    return out


def estate_index(docs):
    return {'levels': {d['level'] for d in docs}, 'types': {i['id']: i['type'] for d in docs for i in d.get('instances', [])}}
