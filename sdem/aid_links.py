"""AID proposes the direct A1→A3 links and field matches (the owner's approvals 2 and 2b, 2026-11-16 — found building Payment Initiation v2,
docs/evidence/payment-initiation-v2/report.md: every link of these types had to be stated by hand).

Each rule reads only approved links (or ones proposed in the same run) and the links inside a layer, proposes only when exactly one
candidate is found — never a guess between two — and says the path it followed. A person approves each, as always (CTL-21).

AID-L01  SERVED_BY: a process USES_DOMAIN a service domain that is REALIZED_BY a component (or a part of it) that realises an application
         service → the process is SERVED_BY that service; an actor or role assigned to the process → SERVED_BY it too (low).
AID-L02  AUTOMATED_BY: a process (or one of its activities) invokes a BIAN operation IMPLEMENTED_BY an API; the API's interface is assigned
         to an application service that one application function realises → the process is AUTOMATED_BY that function.
AID-L03  REALIZED_BY (business service): a process realises the business service and is SERVED_BY one application service → the business
         service is REALIZED_BY it.
AID-L04  REALIZED_BY (business event): a process raises the business event (or is triggered by it) and is SERVED_BY a service whose
         component raises exactly one application event → the business event is REALIZED_BY that event.
AID-L05  REALIZED_BY (channel): an API channel is associated with a business service REALIZED_BY an application service, and exactly one
         interface is assigned to that service → the channel is REALIZED_BY that interface.
AID-L06  SERVED_BY (platform): an application service consumes a technology service, and one component realises the application
         service → the component is SERVED_BY that technology service.
AID-I05  ALIGNED_TO: an A1 business object and the one BIAN business object of the same name.
AID-I06  STORED_IN: an inferred data entity, where every other table of the design is stored in one database.
AID-K02  MAPPED_TO (existing table): a BIAN business object and a data entity the person wrote, when at least two and at least half of the entity's columns
         say what the object's fields say and no other object comes close (15 points) — it feeds AID-K01 in the same run.
AID-K01  FIELD_MAPPED_TO: for a business object MAPPED_TO a data entity, each column with no field mapping is matched to the BIAN field
         whose name says the same thing (words, with a few banking synonyms), of a type the column can hold, preferring the object's own
         fields over those BIAN repeats from parent objects (its family, fix 3) — one clear best only.
"""
from .identity import T as _T, layer as _L  # ST-01…ST-05: layers and types by id (docs/design/sdem-stable-identity-spec.md)
import re

STOP = {'the', 'of', 'a', 'an', 'and', 'transaction', 'financial', 'money', 'transfer', 'payment', 'instruction', 'procedure', 'record'}


def words(name):
    s = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', str(name)).replace('_', ' ').replace('-', ' ').lower()
    return [w for w in s.split() if w]






def _idx(docs):
    every = {i['id']: i for d in docs.values() for i in d.get('instances', [])}
    rels = [(r['source'], r['kind'], r['target']) for d in docs.values() for r in d.get('relationships', [])]
    return every, rels


DIRECT_ORDER = ('AID-L01', 'AID-L02', 'AID-L03', 'AID-L04', 'AID-L05', 'AID-L06', 'AID-I05', 'AID-I06')   # the order propose_direct's rules run in
BIAN_DIRECT = {'AID-L01', 'AID-L02', 'AID-I05'}   # 0.22 step 3c: those that go through BIAN's service domains, operations and objects (sdem/aid_bian.py)


def propose_direct(docs, mappings, mm, only=None):
    """AID-L03…L06, I06 — the core's direct links: [(source, relationship, target, rule, why, confidence)]. BIAN's (AID-L01, L02, I05) are
    sdem/aid_bian.propose_direct_bian's, given here among `mappings` as proposed, as an earlier rule's results always were (0.22 step 3c)."""
    every, rels = _idx(docs)
    live = [m for m in mappings if m.get('status') in ('approved', 'proposed')]
    have = {(m['source']['id'], m['relationship'], m['target']['id']) for m in mappings if m.get('status') != 'rejected'}
    link = lambda rel: [(m['source']['id'], m['target']['id']) for m in live if m['relationship'] == rel]
    isa = lambda x, t: x in every and mm.is_a(every[x]['type'], t)
    out = []
    def add(s, rel, t, rule, why, conf):
        if (s, rel, t) not in have:
            have.add((s, rel, t))
            if only is None or rule in only: out.append((s, rel, t, rule, why, conf))
    parts = {}   # a component and its parts (composition, aggregation)
    for s, k, t in rels:
        if k in ('composition', 'aggregation'): parts.setdefault(s, set()).add(t)
    def with_parts(c, seen=None):
        seen = seen or set()
        if c in seen: return set()
        seen.add(c); return {c} | set().union(*[with_parts(p, seen) for p in parts.get(c, ())]) if parts.get(c) else {c}
    realises = {}   # component or function → application services it realises
    for s, k, t in rels:
        if k == 'realization' and isa(t, _T('application.ApplicationService')): realises.setdefault(s, set()).add(t)
    served = {}
    for p, svc in link('SERVED_BY'):
        if isa(p, _T('business.BusinessProcess')) and isa(svc, _T('application.ApplicationService')): served.setdefault(p, set()).add(svc)
    for s, rel, t, *_ in out:
        if rel == 'SERVED_BY' and isa(s, _T('business.BusinessProcess')): served.setdefault(s, set()).add(t)
    for p, k, bs in rels:   # AID-L03
        if k == 'realization' and isa(p, _T('business.BusinessProcess')) and isa(bs, _T('business.BusinessService')) and len(served.get(p, ())) == 1:
            svc = next(iter(served[p])); add(bs, 'REALIZED_BY', svc, 'AID-L03', f'{p} realises {bs} and is served by {svc}', 0.6)
    comps_of = {}   # AID-L04
    for c, svcs in realises.items():
        for s_ in svcs: comps_of.setdefault(s_, set()).add(c)
    raised = {}
    for s, k, t in rels:
        if k == 'triggering' and isa(t, _T('application.Event')): raised.setdefault(s, set()).add(t)
    for a, k, b in rels:
        if k != 'triggering': continue
        ev, p = (b, a) if isa(b, _T('business.BusinessEvent')) and isa(a, _T('business.BusinessProcess')) else (None, None)   # an event the process raises — its software raises the matching one
        if not ev: continue
        cands = set()
        for svc in served.get(p, ()):
            for c in comps_of.get(svc, ()):
                for whole in [x for x in every if c in with_parts(x)] or [c]: cands |= raised.get(whole, set()) | raised.get(c, set())
        if len(cands) == 1:
            e = next(iter(cands)); add(ev, 'REALIZED_BY', e, 'AID-L04', f'{p} raises {ev}, and the component serving {p} raises only {e}', 0.4)
    assigned = {}   # an interface and the application services assigned to it (AID-L05)
    for s, k, t in rels:
        if k == 'assignment' and isa(s, _T('application.ApplicationInterface')) and isa(t, _T('application.ApplicationService')): assigned.setdefault(s, set()).add(t)
    realized = {}   # AID-L05
    for bs, svc in link('REALIZED_BY'):
        if isa(bs, _T('business.BusinessService')): realized.setdefault(bs, set()).add(svc)
    for s, rel, t, *_ in out:
        if rel == 'REALIZED_BY' and isa(s, _T('business.BusinessService')): realized.setdefault(s, set()).add(t)
    for ch, k, bs in rels:
        if k != 'association' or not isa(ch, _T('business.BusinessInterface')) or not isa(bs, _T('business.BusinessService')): continue
        if (every[ch].get('attributes') or {}).get('channel_kind') != 'api': continue
        ifs = {i for svc in realized.get(bs, ()) for i, svcs in assigned.items() if svc in svcs}
        if len(ifs) == 1:
            i = next(iter(ifs)); add(ch, 'REALIZED_BY', i, 'AID-L05', f'{ch} is an API channel for {bs}, delivered through {i}', 0.6)
    for svc, rec in every.items():   # AID-L06: an application service's platform services (consumes) serve the one component that realises it
        if not isa(svc, _T('application.ApplicationService')): continue
        comps = {c for c, svcs in realises.items() if svc in svcs and isa(c, _T('application.ApplicationComponent'))}
        if len(comps) != 1: continue
        c = next(iter(comps))
        for ts in (rec.get('attributes') or {}).get('consumes') or []:
            if isa(ts, _T('technology.TechnologyService')): add(c, 'SERVED_BY', ts, 'AID-L06', f'{svc} uses {ts} (consumes), and only {c} realises {svc}', 0.6)
    # AID-I06: an inferred data entity is STORED_IN the one database the design's other entities are stored in
    stores = {t for s_, t in link('STORED_IN') if isa(s_, _T('data.DataEntity'))}
    if len(stores) == 1:
        db = next(iter(stores))
        for x, r in every.items():
            inf = (r.get('attributes') or {}).get('inferred')
            if isa(x, _T('data.DataEntity')) and isinstance(inf, dict) and inf.get('status') == 'confirmed' and not any(s_ == x for s_, _ in link('STORED_IN')):   # only a table the person kept
                add(x, 'STORED_IN', db, 'AID-I06', f'every other table of the design is stored in {db}', 0.4)
    return out






def family(*a, **k):   # 0.22 step 3c: AID-K01's helper is BIAN's (sdem/aid_bian.py) — here for those who call it from aid_links
    from .aid_bian import family as f
    return f(*a, **k)
