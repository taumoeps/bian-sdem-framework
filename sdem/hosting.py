"""Hosting and zone connectivity (metamodel 0.11.0; docs/design/sdem-hosting-inference-design.md, the owner's decisions H1–H8, 2026-11-14).

  · the organisation's hosting default and zone templates (PR-32) — SDEM's default is cloud first;
  · the evidence for a shape's hosting: the signals in metamodel/hosting-signals.json (HS-01…HS-13) and the profile's own;
  · the zone connections SDEM works out from the zone structure (ZC-01…ZC-04) — never records;
  · zone placements proposed for a person to decide (AID-Z01…AID-Z04), each marked inferred with the signals it read.
"""
import json, re
from functools import lru_cache
from pathlib import Path

from .metamodel import ROOT

SIGNALS_FILE = ROOT / 'metamodel' / 'hosting-signals.json'
RANK = {'low': 1, 'medium': 2, 'high': 3}
PLATFORMS = ('A4.Node', 'A4.Device', 'A4.SystemSoftware')
ZONE = 'A4.NetworkZone'
DEFAULT_TEMPLATES = {'cloud': ['cloud', ['dmz', 'internal']], 'on_premises': ['on_premises', ['dmz', 'internal']], 'hybrid': ['cloud', 'on_premises']}


@lru_cache(maxsize=1)
def _sdem_signals():
    return json.loads(SIGNALS_FILE.read_text(encoding='utf-8'))['signals']


def policy():
    """The active profile's hosting policy (PR-32), or SDEM's: cloud first, the standard templates."""
    from . import profile as _p
    h = _p.hosting() or {}
    over = {o['id']: o for o in h.get('signal_overrides') or [] if isinstance(o, dict) and o.get('id')}   # PR-33
    ours, off = [], []
    for s in _sdem_signals():
        o = over.get(s['id'])
        if o and o.get('off') is True: off.append({**s, 'reason': o.get('reason', '')}); continue
        ours.append({**s, 'confidence': o['confidence'], 'overridden': o.get('reason', '')} if o and o.get('confidence') else s)
    return {'default': h.get('default', 'cloud'), 'templates': {**DEFAULT_TEMPLATES, **(h.get('templates') or {})},
            'signals': ours + list(h.get('signals') or []), 'off': off}


def _words(rec):
    return ' '.join(str(rec.get(k) or '') for k in ('name', 'description')).casefold()


def evidence(rec, doc, mm, signals=None):
    """The signals a shape carries: [{id, points_to, confidence, read}] — what was read, so the proposal can cite it (HS-01…HS-13)."""
    signals = signals if signals is not None else policy()['signals']
    at = rec.get('attributes') or {}
    envs = [i for i in doc.get('instances', []) if i['type'] == 'A4.DeploymentEnvironment'
            and any(r['source'] == i['id'] and r['target'] == rec['id'] and r['kind'] == 'aggregation' for r in doc.get('relationships', []))]
    out = []
    for s in signals:
        read = s.get('read') or {}; got = None
        if read.get('type') and mm.is_a(rec['type'], read['type']): got = f"type {rec['type']}"
        for k in read.get('attribute', []):
            if not got and at.get(k) not in (None, '', []): got = f'{k} = {at[k]!r}'
        for k, vals in (read.get('attribute_in') or {}).items():
            if not got and at.get(k) in vals: got = f'{k} = {at[k]!r}'
        for k, vals in (read.get('environment_attribute_in') or {}).items():
            for e in envs:
                if not got and (e.get('attributes') or {}).get(k) in vals: got = f"environment {e['id']} {k} = {e['attributes'][k]!r}"
        for w in read.get('environment_words') or []:   # HS-12: the environment's own description
            for e in envs:
                if not got and re.search(r'(?<![a-z0-9])' + re.escape(w.casefold()) + r'(?![a-z0-9])', _words(e)): got = f"environment {e['id']} says {w!r}"
        words = read.get('name_words') or []
        if not got and words:
            hit = next((w for w in words if re.search(r'(?<![a-z0-9])' + re.escape(w.casefold()) + r'(?![a-z0-9])', _words(rec))), None)
            if hit: got = f'name or description says {hit!r}'
        if got and (not read.get('for_types') or any(mm.is_a(rec['type'], t) for t in read['for_types'])):
            out.append({'id': s['id'], 'points_to': s['points_to'], 'confidence': s['confidence'], 'read': got,
                        **({'overridden': s['overridden']} if s.get('overridden') else {})})
    return out


def judge(ev, default):
    """The hosting a shape's evidence points to: (kind, confidence, signals used) — or (None, 'unresolved', both sides) when
    signals at medium or above point both ways (AID-Z01: never guessed). No signal: the default, at low confidence (HS-10)."""
    strong = [e for e in ev if RANK[e['confidence']] >= 2]
    sides = {e['points_to'] for e in strong}
    if len(sides) > 1: return None, 'unresolved', strong
    use = strong or [e for e in ev if e['points_to'] in ('cloud', 'on_premises')]
    if not use: return default, 'low', [{'id': 'HS-10', 'points_to': default, 'confidence': 'low', 'read': f"no signal — the organisation's default ({default})"}]
    kinds = {e['points_to'] for e in use}
    if len(kinds) > 1: return None, 'unresolved', use
    best = max(RANK[e['confidence']] for e in use)
    return kinds.pop(), {1: 'low', 2: 'medium', 3: 'high'}[best], use


def zone_connections(doc, mm):
    """ZC-01…ZC-04: the connections SDEM works out from the zone structure — never records.
    ZC-01 level-0 zones with each other (on premises ↔ cloud) · ZC-02 the level-1 zones of one level 0 with each other ·
    ZC-03 a zone with the zone it is part of. Returns [(zone, zone, rule)]."""
    from .conformance import zones_of
    zones = {i['id']: (i.get('attributes') or {}) for i in doc.get('instances', []) if mm.is_a(i['type'], ZONE)}
    _, parent, _ = zones_of(doc, mm)
    tops = sorted(z for z in zones if zones[z].get('zone_level') == 0)
    out = [(a, b, 'ZC-01') for i, a in enumerate(tops) for b in tops[i + 1:]]
    for t in tops:
        kids = sorted(z for z in zones if parent.get(z) == t and zones[z].get('zone_level') == 1)
        out += [(a, b, 'ZC-02') for i, a in enumerate(kids) for b in kids[i + 1:]]
    out += [(p, z, 'ZC-03') for z, p in sorted(parent.items()) if z in zones and p in zones]
    return out


def path(doc, mm, a, b):
    """ZC-04: how shape a reaches shape b through their zones — [a, zone, …, zone, b] — or None. Shapes are connected through their zones."""
    from .conformance import zones_of
    shapes, _, _ = zones_of(doc, mm)
    za, zb = (shapes.get(a) or [None])[0], (shapes.get(b) or [None])[0]
    if not za or not zb: return None
    adj = {}
    for x, y, _ in zone_connections(doc, mm): adj.setdefault(x, set()).add(y); adj.setdefault(y, set()).add(x)
    prev, frontier = {za: None}, [za]
    while frontier:
        nxt = []
        for z in frontier:
            for y in sorted(adj.get(z, ())):
                if y not in prev: prev[y] = z; nxt.append(y)
        frontier = nxt
    if zb not in prev: return None
    route, z = [], zb
    while z: route.append(z); z = prev[z]
    return [a] + route[::-1] + [b]


LABEL = {'cloud': 'Cloud', 'on_premises': 'On premises', 'dmz': 'Security zone (DMZ)', 'internal': 'Internal network', 'private': 'Private network'}
LEVEL_OF = {'cloud': 0, 'on_premises': 0, 'dmz': 1, 'internal': 1, 'private': 2}


def template_zones(name, stem):
    """WS-12: the zones of a hosting template (PR-32) — records and their nesting links — for `sdem new --hosting NAME`.
    A template is [level-0 kind, [level-1 kinds, a list after one = its level-2 kinds]] or a list of level-0 kinds (hybrid)."""
    pol = policy(); t = pol['templates'].get(name)
    if t is None: raise ValueError(f"no hosting template {name!r} — {', '.join(sorted(pol['templates']))} (the organisation profile can add its own, PR-32)")
    tops = [t] if (len(t) > 1 and isinstance(t[1], list)) or len(t) == 1 else [pol['templates'].get(k, [k, ['dmz', 'internal']]) for k in t]
    recs, links = [], []
    def zone(zid, kind, where, within=None):
        name = f"{LABEL[kind]} — {LABEL[within].lower() if within == 'cloud' else 'on premises' if within else where}{f' ({where})' if within else ''}"
        recs.append({'id': zid, 'type': ZONE, 'version': '1.0', 'name': name, 'lifecycle_status': 'active',
                     'description': f"{LABEL[kind]} zone (level {LEVEL_OF[kind]}), from the hosting template '{name}' (sdem new --hosting).",
                     'attributes': {'zone_level': LEVEL_OF[kind], 'zone_kind': kind}})
    where = stem.lower()
    for top in tops:
        kind, spec = top[0], (top[1] if len(top) > 1 else [])
        tid = f"ZONE-{stem}-{kind.upper().replace('_', '-')}"; zone(tid, kind, where)
        last = None
        for item in spec:
            if isinstance(item, list):
                for k2 in item:
                    zid = f'{last}-{k2.upper()}'; zone(zid, k2, where, kind); links.append({'source': last, 'kind': 'composition', 'target': zid})
            else:
                last = f'{tid}-{item.upper()}'; zone(last, item, where, kind); links.append({'source': tid, 'kind': 'composition', 'target': last})
    return recs, links


def placement_mark(link):
    return link.get('inferred') if isinstance(link.get('inferred'), dict) else None


def propose(doc, mm, run, person, now, rejected=(), stem=None):
    """AID-Z01…Z04: for each A4 shape in no zone and not hosted by another, propose its zone — level 0 from the evidence, level 1 from
    internet_facing; never a private (level-2) zone. Creates the policy's template zones (as inferred records) where the workspace has no
    level-0 zone of that kind. Returns (new zone records, new placement links, unresolved [{id, signals}])."""
    from .conformance import zones_of, UNPLACED
    pol = policy()
    shapes, parent, _ = zones_of(doc, mm)
    local = {i['id']: i for i in doc.get('instances', [])}
    hosted = {r['target'] for r in doc.get('relationships', []) if r['kind'] in ('assignment', 'composition', 'aggregation', 'realization')
              and r['source'] in local and r['target'] in local and not mm.is_a(local[r['source']]['type'], 'A4.CommunicationNetwork')
              and local[r['source']]['type'] != 'A4.DeploymentEnvironment'}   # AID-Z04: in its host's zone
    zones = {i['id']: (i.get('attributes') or {}) for i in local.values() if mm.is_a(i['type'], ZONE)}
    stem = re.sub(r'[^A-Z0-9]+', '-', (stem or doc.get('model_id') or 'WS').upper()).strip('-')[:24] or 'WS'
    new_zones, links, unresolved, made = [], [], [], {}
    def zone_for(kind, level1):
        top = next((z for z in sorted(zones) if zones[z].get('zone_level') == 0 and zones[z].get('zone_kind') == kind), None) \
              or made.get((kind, None))
        if not top:
            top = f'ZONE-{stem}-{kind.upper().replace("_", "-")}'
            made[(kind, None)] = top
            new_zones.append(_zone(top, f"{'Cloud' if kind == 'cloud' else 'On premises'} (inferred)", 0, kind, run, person, now))
        inner = next((z for z in sorted(zones) if parent.get(z) == top and zones[z].get('zone_kind') == level1), None) or made.get((kind, level1))
        if not inner:
            inner = f'{top}-{level1.upper()}'
            made[(kind, level1)] = inner
            new_zones.append(_zone(inner, f"{'Security zone (DMZ)' if level1 == 'dmz' else 'Internal network'} — {'cloud' if kind == 'cloud' else 'on premises'} (inferred)", 1, level1, run, person, now))
            links.append({'source': top, 'kind': 'composition', 'target': inner})
        return inner
    for x, zs in sorted(shapes.items()):
        rec = local[x]
        if zs or x in hosted or rec.get('lifecycle_status') == 'retired' or any(mm.is_a(rec['type'], t) for t in UNPLACED): continue
        ev = evidence(rec, doc, mm, pol['signals'])
        kind, conf, used = judge(ev, pol['default'])
        if kind is None: unresolved.append({'id': x, 'signals': used}); continue
        level1 = 'dmz' if (rec.get('attributes') or {}).get('internet_facing') is True else 'internal'
        z = zone_for(kind, level1)
        if f'{x}@{z}' in rejected: continue
        links.append({'source': z, 'kind': 'aggregation', 'target': x, 'inferred': {
            'by': 'sdem aid', 'run': run, 'at': now, 'requested_by': person, 'rule': 'AID-Z01, AID-Z02', 'status': 'proposed',
            'source': '; '.join(f"{e['id']} {e['read']}" + (f" (confidence {e['confidence']} by the profile: {e['overridden']})" if e.get('overridden') else '') for e in used)
                      + ''.join(f"; {e['id']} off by the profile ({e['reason']}) — it would have read {e['read']}" for e in evidence(rec, doc, mm, pol.get('off') or [])
                                for e in [{**e, 'reason': next((s['reason'] for s in pol['off'] if s['id'] == e['id']), '')}]), 'confidence': conf,
            'reasoning': f"{'on premises' if kind == 'on_premises' else 'cloud'} from {', '.join(e['id'] for e in used)}; {'internet facing' if level1 == 'dmz' else 'not internet facing'} → {level1}"}})
    return new_zones, links, unresolved


def _zone(zid, name, level, kind, run, person, now):
    return {'id': zid, 'type': ZONE, 'version': '1.0', 'name': name, 'lifecycle_status': 'active',
            'description': f'Inferred by sdem aid from the organisation\'s hosting policy (PR-32) — a person confirms or rejects it.',
            'attributes': {'zone_level': level, 'zone_kind': kind, 'inferred': {
                'by': 'sdem aid', 'run': run, 'at': now, 'requested_by': person, 'rule': 'AID-Z01', 'source': 'hosting policy (PR-32)',
                'reasoning': 'a zone the proposed placements need', 'confidence': 'low', 'evidence_class': '', 'from': '', 'step': 'zones'}}}
