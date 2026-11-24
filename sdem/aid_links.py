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

SYN = {'identification': 'ref', 'identifier': 'ref', 'reference': 'ref', 'id': 'ref', 'ref': 'ref', 'from': 'debtor', 'source': 'debtor',
       'debtor': 'debtor', 'payer': 'debtor', 'target': 'creditor', 'to': 'creditor', 'creditor': 'creditor', 'payee': 'creditor',
       'amount': 'amount', 'value': 'amount', 'currency': 'currency', 'date': 'date', 'datetime': 'date', 'time': 'date', 'status': 'status',
       'description': 'text', 'remittance': 'text', 'information': 'text', 'name': 'name', 'account': 'account', 'iban': 'account'}
STOP = {'the', 'of', 'a', 'an', 'and', 'transaction', 'financial', 'money', 'transfer', 'payment', 'instruction', 'procedure', 'record'}
COMPAT = {'integer': ('int', 'integer', 'smallint', 'bigint', 'number', 'numeric'), 'decimal': ('numeric', 'decimal', 'number', 'float', 'double', 'real', 'money'),
          'amount': ('numeric', 'decimal', 'number', 'money'), 'date': ('date', 'timestamp', 'datetime'), 'datetime': ('timestamp', 'datetime', 'date'),
          'boolean': ('bool', 'boolean', 'bit')}


def words(name):
    s = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', str(name)).replace('_', ' ').replace('-', ' ').lower()
    return [w for w in s.split() if w]


def concepts(name, drop=()):
    return {SYN.get(w, w) for w in words(name) if w not in STOP and w not in drop}


def family(field_name, object_name):
    """Fix 3: a BIAN field's family — its object's own (the name starts with the object's name) or one BIAN repeats from a parent object."""
    own = ''.join(w.capitalize() for w in words(object_name))
    return 'own' if str(field_name).startswith(own) else 'inherited'


def _idx(docs):
    every = {i['id']: i for d in docs.values() for i in d.get('instances', [])}
    rels = [(r['source'], r['kind'], r['target']) for d in docs.values() for r in d.get('relationships', [])]
    return every, rels


DIRECT_ORDER = ('AID-L01', 'AID-L02', 'AID-L03', 'AID-L04', 'AID-L05', 'AID-L06', 'AID-I05', 'AID-I06')   # the order propose_direct's rules run in
BIAN_DIRECT = {'AID-L01', 'AID-L02', 'AID-L03', 'AID-L04', 'AID-L05', 'AID-I05'}   # 0.22 step 3c: those that go through BIAN's service domains and objects


def propose_direct(docs, mappings, mm, only=None):
    """AID-L01…L05: [(source, relationship, target, rule, why, confidence)]. `only`: keep only these rules' results — every rule still runs and
    still counts what it found as present, so a filtered run leaves out exactly what the whole run does (0.22 step 3c)."""
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
    served = {}     # AID-L01
    for p, sd in link('USES_DOMAIN'):
        if not isa(p, _T('business.BusinessProcess')): continue
        svcs = set()
        for d, comp in link('REALIZED_BY'):
            if d == sd and isa(comp, _T('application.ApplicationComponent')):
                for c in with_parts(comp): svcs |= realises.get(c, set())
        if len(svcs) == 1:
            svc = next(iter(svcs)); served.setdefault(p, set()).add(svc)
            add(p, 'SERVED_BY', svc, 'AID-L01', f'{p} uses {sd}, realised by {next(c for d, c in link("REALIZED_BY") if d == sd)}, which provides {svc}', 0.6)
            for a, k, t in rels:
                if k == 'assignment' and t == p and (isa(a, _T('business.BusinessActor')) or isa(a, _T('business.BusinessRole'))):
                    add(a, 'SERVED_BY', svc, 'AID-L01', f'{a} performs {p}, which {svc} serves', 0.4)
    for p, svc in link('SERVED_BY'):
        if isa(p, _T('business.BusinessProcess')) and isa(svc, _T('application.ApplicationService')): served.setdefault(p, set()).add(svc)
    for s, rel, t, *_ in out:
        if rel == 'SERVED_BY' and isa(s, _T('business.BusinessProcess')): served.setdefault(s, set()).add(t)
    impl = dict(link('IMPLEMENTED_BY'))   # AID-L02
    iface_of = {t: s for s, k, t in rels if k == 'composition' and isa(s, _T('application.ApplicationInterface')) and isa(t, _T('application.APIOperation'))}
    assigned = {}
    for s, k, t in rels:
        if k == 'assignment' and isa(s, _T('application.ApplicationInterface')) and isa(t, _T('application.ApplicationService')): assigned.setdefault(s, set()).add(t)
    funcs_of = {}
    for s, k, t in rels:
        if k == 'realization' and isa(s, _T('application.ApplicationFunction')) and isa(t, _T('application.ApplicationService')): funcs_of.setdefault(t, set()).add(s)
    acts = {}
    for s, k, t in rels:
        if k == 'composition' and isa(s, _T('business.BusinessProcess')) and isa(t, _T('business.BusinessActivity')): acts.setdefault(s, set()).add(t)
    for p, rec in every.items():
        if not isa(p, _T('business.BusinessProcess')) or isa(p, _T('business.BusinessActivity')): continue
        ops = set((rec.get('attributes') or {}).get('invokes') or [])
        for a in acts.get(p, ()): ops |= set((every[a].get('attributes') or {}).get('invokes') or [])
        fs = set()
        for op in ops:
            api = impl.get(op); i = iface_of.get(api)
            for svc in assigned.get(i, ()): fs |= funcs_of.get(svc, set())
        names = set(words(rec.get('name', ''))) | {w for a in acts.get(p, ()) for w in words(every[a].get('name', ''))}
        fs = {f for f in fs if (set(words(every[f].get('name', ''))) - STOP) & (names - STOP)}   # the function does what the process says it does
        if len(fs) == 1:
            f = next(iter(fs)); add(p, 'AUTOMATED_BY', f, 'AID-L02', f'{p} invokes BIAN operations implemented by APIs of a service that {f} realises', 0.4)
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
    # AID-I05: an A1 business object ALIGNED_TO the BIAN business object of the same name, when exactly one has it
    norm = lambda n: ''.join(words(n))
    bians = {}
    for x, r in every.items():
        if isa(x, _T('bian.BusinessObject')): bians.setdefault(norm(r.get('name', '')), []).append(x)
    for x, r in every.items():
        if isa(x, _T('business.BusinessObject')):
            same = bians.get(norm(r.get('name', '')), [])
            if len(same) == 1: add(x, 'ALIGNED_TO', same[0], 'AID-I05', f"{r.get('name')} is BIAN's {every[same[0]].get('name')} (the same name)", 0.6)
    # AID-I06: an inferred data entity is STORED_IN the one database the design's other entities are stored in
    stores = {t for s_, t in link('STORED_IN') if isa(s_, _T('data.DataEntity'))}
    if len(stores) == 1:
        db = next(iter(stores))
        for x, r in every.items():
            inf = (r.get('attributes') or {}).get('inferred')
            if isa(x, _T('data.DataEntity')) and isinstance(inf, dict) and inf.get('status') == 'confirmed' and not any(s_ == x for s_, _ in link('STORED_IN')):   # only a table the person kept
                add(x, 'STORED_IN', db, 'AID-I06', f'every other table of the design is stored in {db}', 0.4)
    return out


def propose_fields(docs, mappings, mm):
    """AID-K01: [(BIAN field, 'FIELD_MAPPED_TO', column, 'AID-K01', why, confidence)]."""
    every, rels = _idx(docs)
    fields = {}
    for s, k, t in rels:
        if k == 'composition' and t in every and (mm.is_a(every[t]['type'], _T('bian.BusinessObjectAttribute')) or mm.is_a(every[t]['type'], _T('data.DataAttribute'))):
            fields.setdefault(s, []).append(every[t])
    done = {m['target']['id'] for m in mappings if m['relationship'] == 'FIELD_MAPPED_TO' and m.get('status') != 'rejected'}
    out = []
    for m in mappings:
        if m['relationship'] != 'MAPPED_TO' or m.get('status') not in ('approved', 'proposed'): continue
        bo, ent = m['source']['id'], m['target']['id']
        if bo not in every or not mm.is_a(every[bo]['type'], _T('bian.BusinessObject')): continue
        bofs, cols = fields.get(bo, []), fields.get(ent, [])
        drop = set(words(every[bo]['name'])); used = set()
        for col in cols:
            if col['id'] in done: continue
            want = concepts(col['name'])
            if not want: continue
            pt = str((col.get('attributes') or {}).get('physical_type') or '').lower()
            scored = []
            for f in bofs:
                have = concepts(f['name'], drop)
                if not have: continue
                score = len(want & have) / len(want | have)
                lt = str((f.get('attributes') or {}).get('data_type') or '').lower()
                if lt in COMPAT and pt and not pt.startswith(COMPAT[lt]): score -= 0.5
                if family(f['name'], every[bo]['name']) == 'own': score += 0.1
                scored.append((score, f))
            scored.sort(key=lambda x: -x[0])
            scored = [x for x in scored if x[1]['id'] not in used]   # one BIAN field maps to one column
            if scored and scored[0][0] >= 0.6 and (len(scored) == 1 or scored[0][0] - scored[1][0] >= 0.1 - 1e-9):   # the column's main words, not one of two
                f = scored[0][1]; used.add(f['id'])
                out.append((f['id'], 'FIELD_MAPPED_TO', col['id'], 'AID-K01', f"{col['name']} says what {f['name']} says ({', '.join(sorted(want & concepts(f['name'], drop)))})", 0.6 if scored[0][0] >= 0.8 else 0.4))
                done.add(col['id'])
    return out


def match_existing(docs, mappings, mm):
    """AID-K02: [(BIAN object, 'MAPPED_TO', existing data entity, 'AID-K02', why, confidence)] — run before AID-I01, so an object an existing
    table already stores gets that table proposed, not a new inferred one."""
    every, rels = _idx(docs)
    fields = {}
    for s_, k, t in rels:
        if k == 'composition' and t in every and (mm.is_a(every[t]['type'], _T('bian.BusinessObjectAttribute')) or mm.is_a(every[t]['type'], _T('data.DataAttribute'))):
            fields.setdefault(s_, []).append(every[t])
    mapped = {(m['source']['id'], m['target']['id']) for m in mappings if m['relationship'] == 'MAPPED_TO' and m.get('status') != 'rejected'}
    has_map = {a for a, _ in mapped}
    ents = [e for e in every.values() if mm.is_a(e['type'], _T('data.DataEntity')) and not (e.get('attributes') or {}).get('inferred') and fields.get(e['id'])]
    objs = [o for o in every.values() if mm.is_a(o['type'], _T('bian.BusinessObject')) and fields.get(o['id']) and o['id'] not in has_map]
    best = {}   # each object to its one best table; each table to its one best object
    for e in ents:
        cols = [concepts(c['name']) for c in fields[e['id']]]
        score = []
        for o in objs:
            have = set().union(*[concepts(f['name']) for f in fields[o['id']]]) | concepts(o['name'])   # the object's name counts: an account's fields are about an account
            hits = sum(1 for c in cols if c and len(c & have) / len(c) >= 0.5)
            if hits < 2: continue   # one shared word (a reference) is not evidence that the table stores the object
            sc = hits / len(cols)
            if (set(words(o['name'])) & set(words(e['name']))) - {'the', 'of', 'a', 'and'}: sc += 0.2   # the table is named for the object (its plain words)
            score.append((sc, o))
        score.sort(key=lambda x: -x[0])
        if score and score[0][0] >= 0.5 and (len(score) == 1 or score[0][0] - score[1][0] >= 0.15 - 1e-9):
            o = score[0][1]
            if score[0][0] > best.get(o['id'], (0, None))[0]: best[o['id']] = (score[0][0], e)
    out = []
    for oid, (sc, e) in sorted(best.items()):
        if (oid, e['id']) not in mapped:
            out.append((oid, 'MAPPED_TO', e['id'], 'AID-K02', f"{min(sc, 1):.0%} of {e['name']}'s columns say what {every[oid]['name']}'s fields say", 0.4))
    return out
