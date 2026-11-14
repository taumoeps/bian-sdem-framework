"""What sdem aid proposes at A4, the physical deployment (metamodel 0.12.0; docs/design/sdem-edge-exposure-design.md, the owner's decisions X1–X6):

  · AID-X01 — EXPOSED_THROUGH: an internet-facing A3 interface, exposed through the one internet-facing edge platform (a connection
    between layers, proposed for a person to approve with network_design evidence; two or more candidates: unresolved, never guessed);
  · AID-C01…C06 — a connection for every A4 shape linked to nothing (LC-21): each a link marked inferred, with the rule, what it read and
    how sure, for a person to confirm or reject by the shape's id. A shape no rule reaches is unresolved, never guessed.
"""
import re

PLATFORMS = ('A4.Node', 'A4.Device', 'A4.SystemSoftware')
NOT_SHAPES = ('A4.CommunicationNetwork', 'A4.DeploymentEnvironment', 'A4.Path')
DATABASE = re.compile(r'postgres|mysql|oracle|sql server|database|\bdb2?\b|redis|mongo|cassandra', re.I)


def _approved(maps, rel):
    return [(m['source']['id'], m['target']['id']) for m in maps if m.get('relationship') == rel and m.get('status') == 'approved']


def lone(a4, mm):
    """LC-21's shapes: A4 is the physical deployment, so a shape is connected only by a link inside A4 — its zone placement aside.
    A connection to another layer (DEPLOYED_ON, EXPOSED_THROUGH) does not count (the owner, 2026-11-14). Retired shapes are not deployed."""
    typ = {i['id']: i['type'] for i in a4.get('instances', [])}
    retired = {i['id'] for i in a4.get('instances', []) if i.get('lifecycle_status') == 'retired'}
    zone = lambda x: mm.is_a(typ.get(x, ''), 'A4.NetworkZone')
    linked = {x for r in a4.get('relationships', []) if not (zone(r['source']) or zone(r['target'])) for x in (r['source'], r['target'])}
    return [x for x, t in typ.items() if x not in linked and x not in retired and not any(mm.is_a(t, s) for s in NOT_SHAPES)]


def propose_exposure(a3, a4, maps, mm):
    """AID-X01: [(interface, platform, why)] and unresolved [{id, candidates}]."""
    have = {s for s, _ in [(m['source']['id'], None) for m in maps if m.get('relationship') == 'EXPOSED_THROUGH']}
    edge = [i['id'] for i in a4.get('instances', []) if any(mm.is_a(i['type'], t) for t in PLATFORMS) and (i.get('attributes') or {}).get('internet_facing') is True]
    out, unresolved = [], []
    for i in a3.get('instances', []):
        if not mm.is_a(i['type'], 'A3.ApplicationInterface') or (i.get('attributes') or {}).get('internet_facing') is not True or i['id'] in have: continue
        if len(edge) == 1: out.append((i['id'], edge[0], f"{i['id']} is internet facing and {edge[0]} is the one internet-facing edge platform"))
        else: unresolved.append({'id': i['id'], 'candidates': edge})
    return out, unresolved


def propose_connections(a3, a4, maps, mm, run, person, now, rejected=()):
    """AID-C01…C06 for each A4 shape linked to nothing: ([links marked inferred], [unresolved ids with why])."""
    from .conformance import zones_of
    recs = {i['id']: i for i in a4.get('instances', [])}
    typ = {k: v['type'] for k, v in recs.items()}
    rels = a4.get('relationships', [])
    shapes, parent, _ = zones_of(a4, mm)
    zone_of = lambda x: (shapes.get(x) or [None])[0]
    def top(z):
        while z and parent.get(z): z = parent[z]
        return z
    hosts = {}   # platform -> deployments it runs (assignment)
    for r in rels:
        if r['kind'] == 'assignment' and r['source'] in typ and r['target'] in typ and any(mm.is_a(typ[r['source']], t) for t in PLATFORMS) and typ[r['target']] == 'A4.Deployment':
            hosts.setdefault(r['source'], []).append(r['target'])
    env_of = {}
    for r in rels:
        if r['kind'] == 'aggregation' and typ.get(r['source']) == 'A4.DeploymentEnvironment': env_of.setdefault(r['target'], set()).add(r['source'])
    deployed_as = _approved(maps, 'DEPLOYED_AS'); deployed_on = _approved(maps, 'DEPLOYED_ON'); exposed = _approved(maps, 'EXPOSED_THROUGH')
    env_name = {i['id']: (i.get('name') or '').lower() for i in a4.get('instances', []) if i['type'] == 'A4.DeploymentEnvironment'}
    offers = {r['target']: r['source'] for r in (a3 or {}).get('relationships', []) if r['kind'] == 'composition'}   # interface -> the application composing it
    links, unresolved = [], []
    def mark(rule, src, conf, why):
        return {'by': 'sdem aid', 'run': run, 'at': now, 'requested_by': person, 'rule': rule, 'status': 'proposed', 'source': src, 'confidence': conf, 'reasoning': why}
    def add(s, k, t, rule, src, conf, why):
        if f'{s}|{k}|{t}' in rejected or any(r['source'] == s and r['kind'] == k and r['target'] == t for r in rels + links): return
        links.append({'source': s, 'kind': k, 'target': t, 'inferred': mark(rule, src, conf, why)})
    running = lambda: sorted({p for p, ds in hosts.items() if ds} | {p for _, p in deployed_on if p in typ})   # runs a deployment, or an application component (DEPLOYED_ON)
    run_by = {d for ds in hosts.values() for d in ds}
    todo = set(lone(a4, mm)) | {x for x, t in typ.items() if t == 'A4.Deployment' and x not in run_by}   # AID-C01: a deployment no platform runs
    for x in sorted(todo, key=lambda x: (typ[x] != 'A4.Deployment', x)):   # deployments first: they make platforms hosts for the rules after
        t, name = typ[x], recs[x].get('name', '')
        if t != 'A4.Deployment' and any(x in (l['source'], l['target']) for l in links): continue   # a rule already connected it (e.g. as a deployment's platform)
        if t == 'A4.Deployment':   # AID-C01
            named = (recs[x].get('attributes') or {}).get('platform_id')
            if named in typ and any(mm.is_a(typ[named], p) for p in PLATFORMS):   # the deployment record names its platform
                add(named, 'assignment', x, 'AID-C01', f'{x} names its platform: platform_id {named}', 'high', 'the deployment runs on the platform its record names')
                hosts.setdefault(named, []).append(x); continue
            comps = [c for c, d in deployed_as if d == x]
            cand = sorted({p for c, p in deployed_on if c in comps and p in typ})
            if env_of.get(x): cand = [p for p in cand if not env_of.get(p) or env_of[p] & env_of[x]] or cand
            if len(cand) == 1:
                add(cand[0], 'assignment', x, 'AID-C01', f"{', '.join(comps)} DEPLOYED_ON {cand[0]} and DEPLOYED_AS {x} (approved)", 'high', 'the deployment runs on the platform its component is deployed on')
                hosts.setdefault(cand[0], []).append(x); continue
            unresolved.append({'id': x, 'why': 'no single platform its component is deployed on' if not cand else f"its component is deployed on {', '.join(cand)} — which one?"}); continue
        if any(mm.is_a(t, p) for p in PLATFORMS) and (recs[x].get('attributes') or {}).get('internet_facing') is True:   # AID-C06
            ifcs = [i for i, p in exposed if p == x]; apps = {offers[i] for i in ifcs if i in offers}
            deps = sorted({d for c, d in deployed_as if c in apps and d in typ})
            prod = [d for d in deps if any('prod' in env_name.get(e, '') for e in env_of.get(d, ()))]
            if prod or deps:
                for d in (prod or deps): add(x, 'association', d, 'AID-C06', f"{', '.join(ifcs)} EXPOSED_THROUGH {x}; {', '.join(sorted(apps))} composes it and is DEPLOYED_AS {d} (approved)", 'high', 'an edge platform fronts the deployment of the application whose interface it exposes')
                continue
        if any(mm.is_a(t, p) for p in PLATFORMS) and DATABASE.search(name):   # AID-C02
            users = {c for e in [i for i in a3.get('instances', []) if (i.get('attributes') or {}).get('stored_in') == x]
                     for c in [r['source'] for r in a3.get('relationships', []) if r['target'] == e['id'] and r['kind'] == 'access']}
            plats = sorted({p for c, p in deployed_on if c in users and p in typ and p != x})
            if plats:
                for p in plats: add(p, 'association', x, 'AID-C02', f"components {', '.join(sorted(users))} use data stored in {x} and run on {p}", 'medium', 'the platform running the data\'s users reaches its database')
                continue
            near = [p for p in running() if p != x and zone_of(p) and zone_of(p) == zone_of(x)]
            if near:
                for p in near: add(p, 'association', x, 'AID-C02', f'{p} runs deployments or applications in {zone_of(x)}, the zone {x} is in', 'low', 'a database in the same zone as the platforms that run the deployments')
                continue
        if t == 'A4.TechnologyService':   # AID-C03
            z = zone_of(x)
            near = [p for p in running() if z and zone_of(p) == z] or [p for p in running() if z and top(zone_of(p)) == top(z)]
            if near:
                for p in near: add(x, 'serving', p, 'AID-C03', f'{p} runs deployments or applications in the zone {x} is in ({z})', 'low', 'a technology service serves the platforms in its zone')
                continue
        if t == 'A4.Artifact':   # AID-C04
            words = {w for w in re.findall(r'[a-z0-9]+', name.lower()) if len(w) >= 4}
            cand = sorted({p for p, ds in hosts.items() for d in ds if words & {w for w in re.findall(r'[a-z0-9]+', recs.get(d, {}).get('name', '').lower()) if len(w) >= 4}})
            if len(cand) == 1:
                add(cand[0], 'assignment', x, 'AID-C04', f"{x}'s name shares {', '.join(sorted(words))} with a deployment {cand[0]} runs", 'low', 'an artifact is assigned to the platform that runs its deployment'); continue
        if any(mm.is_a(t, p) for p in PLATFORMS):   # AID-C05
            near = [p for p in running() if p != x and zone_of(p) and zone_of(p) == zone_of(x)]
            if near:
                for p in near: add(x, 'association', p, 'AID-C05', f'{p} runs deployments or applications in {zone_of(x)}, the zone {x} is in', 'low', 'platforms in one zone work together')
                continue
        unresolved.append({'id': x, 'why': 'no rule reaches it — a person links it (LC-21)'})
    return links, unresolved
