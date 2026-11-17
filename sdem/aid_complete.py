"""`sdem aid` completes the first draft (docs/design/sdem-completeness-design.md stage 4; aid-spec.md AID-D01…AID-D05).

A standard or pattern is asked first: it says what a record must be linked to, or what a kind of solution has. What it finds missing,
these written rules infer where the design gives evidence — never otherwise — and everything they add is marked inferred, with the rule
that asked for it, for a person to confirm or reject. Rules, deterministic and repeatable; no AI.

  AID-D01  a link a standard's rule asks for, to the one candidate that shares a distinctive word with the record (name_token, low)
  AID-D02  the last record with that gap and the last candidate with no such link — by elimination (low; review first)
  AID-D03  every gap left open is said, with why: no evidence, two candidates, or a person rejected it
  AID-D05  a BIAN service domain a pattern names and the design lacks, from the catalogue; and the one process whose name says it uses it
(AID-D04 — a person confirms or rejects an inferred link by naming it — is in sdem/aid_fill.py.)
"""
import copy, re

SMALL = {'the', 'and', 'for', 'with', 'from', 'that', 'this', 'into', 'are'}


def words(*texts):
    """The words of a name or an id: lower case, three letters or more, a plural's s dropped."""
    out = set()
    for t in texts:
        for w in re.split(r'[^a-z0-9]+', re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', t or '').lower()):
            if len(w) > 3 and w.endswith('s') and not w.endswith('ss'): w = w[:-1]
            if len(w) >= 3 and w not in SMALL: out.add(w)
    return out


def _unconfirmed(rec):
    m = (rec.get('attributes') or {}).get('inferred')
    return isinstance(m, dict) and m.get('status') != 'confirmed'


def _met(rule, x, layer, rels, recs, mm):
    """Whether one of the links the rule asks of record x is among the layer's links (those this run has written included)."""
    for lk in ([rule['link']] if rule.get('link') else [l for l in rule.get('any_link') or [] if l.get('kind')]):
        for s, k, t in rels[layer]:
            other = s if lk.get('direction') == 'in' else t
            if k == lk['kind'] and (t if lk.get('direction') == 'in' else s) == x and other in recs and (not lk.get('to') or mm.is_a(recs[other][1]['type'], lk['to'])): return True
    return False


def propose_links(docs, maps, mm, rules, mark, rejected=()):
    """AID-D01…D03. docs: {layer: dataset}; maps: approved links between layers [(source, relationship, target)]; rules: the active
    profile's rules. Returns ({layer: [link inside the layer, marked inferred]}, [gap left open: record, layer, rule, message, why])."""
    from .comply import evaluate
    findings = evaluate(docs, maps, mm, rules, ())
    by_rule = {r['id']: r for r in rules}
    recs = {i['id']: (l, i) for l, d in docs.items() for i in d.get('instances', [])}
    rels = {l: [(r['source'], r['kind'], r['target']) for r in d.get('relationships', [])] for l, d in docs.items()}
    out, left = {}, []
    def options(rule): return [rule['link']] if rule.get('link') else [lk for lk in rule.get('any_link') or [] if lk.get('kind')]
    def allowed(layer, x, c, lk):   # may the metamodel's link of this kind join the two — the candidate at the other end
        s, t = (c, x) if lk.get('direction') == 'in' else (x, c)
        return mm.relationship_issue(layer, recs[s][1]['type'], lk['kind'], recs[t][1]['type']) is None
    def triple(x, c, lk): return (c, lk['kind'], x) if lk.get('direction') == 'in' else (x, lk['kind'], c)
    gaps = [(f['layer'], f['record'], by_rule[f['rule']]) for f in findings
            if f['outcome'] in ('non_compliant', 'unresolved') and f['rule'] in by_rule and options(by_rule[f['rule']]) and not _unconfirmed(recs[f['record']][1])]
    pending = {}   # (rule id, option index) -> [(layer, record, candidates)] still open after AID-D01
    for layer, x, rule in sorted(gaps, key=lambda g: (g[2]['id'], g[1])):
        peers = [i for l, i in recs.values() if l == layer and mm.known(i['type']) and mm.is_a(i['type'], rule['entity'])]
        mine = words(recs[x][1].get('name'), x)
        mine = {w for w in mine if sum(w in words(p.get('name'), p['id']) for p in peers) == 1}   # a word other records of its kind share singles out nothing
        placed = why = None
        if _met(rule, x, layer, rels, recs, mm): continue   # a link this run already wrote for another record's gap closes this one too
        for n, lk in enumerate(options(rule)):
            cands = sorted(c for c, (l, i) in recs.items() if l == layer and c != x and mm.known(i['type']) and not _unconfirmed(i)
                           and (not lk.get('to') or mm.is_a(i['type'], lk['to'])) and allowed(layer, x, c, lk))
            hits = {}
            for c in cands:
                for w in mine & words(recs[c][1].get('name'), c): hits.setdefault(w, []).append(c)
            hits = {w: cs[0] for w, cs in hits.items() if len(cs) == 1}   # … and a word several candidates share singles out none
            targets = sorted(set(hits.values()))
            if len(targets) == 1:
                c = targets[0]; s, k, t = triple(x, c, lk); w = sorted(w for w, cc in hits.items() if cc == c)[0]
                if f'{s}|{k}|{t}' in rejected: why = f'{s} {k} {t} was inferred before and rejected by a person — it is not inferred again'; continue
                placed = {'source': s, 'kind': k, 'target': t,
                          'inferred': mark('AID-D01', f"{x} and {c} share the word '{w}', which no other {rule['entity'].split('.')[1]} and no other candidate has — {rule['id']} asks for the link ({rule.get('message', '')})",
                                           x, confidence='low', evidence_class='name_token', asked_by=rule['id'])}
                break
            if len(targets) > 1: why = f"{' or '.join(targets)} — each shares a word with it; a person says which"
            pending.setdefault((rule['id'], n), []).append((layer, x, cands, lk))
        if placed: out.setdefault(layer, []).append(placed); rels[layer].append((placed['source'], placed['kind'], placed['target']))
        else: left.append({'record': x, 'layer': layer, 'rule': rule['id'], 'message': rule.get('message', ''), 'why': why or 'no name evidence points to one candidate'})
    done = {(l, r['source'], r['kind'], r['target']) for l, rs in out.items() for r in rs}
    for (rid, n), items in sorted(pending.items()):   # AID-D02: one record still open, one candidate with no such link — by elimination
        rule = by_rule[rid]
        items = [it for it in items if any(o['record'] == it[1] and o['rule'] == rid for o in left)]
        if len(items) != 1: continue
        layer, x, cands, lk = items[0]
        if _met(rule, x, layer, rels, recs, mm): left = [o for o in left if not (o['record'] == x and o['rule'] == rid)]; continue
        kind_peers = {i['id'] for l, i in recs.values() if l == layer and mm.known(i['type']) and mm.is_a(i['type'], rule['entity'])}
        def linked(c): return any(k == lk['kind'] and ((s == c and t in kind_peers) if lk.get('direction') == 'in' else (t == c and s in kind_peers)) for s, k, t in rels[layer])
        free = [c for c in cands if not linked(c)]
        if len(free) != 1: continue
        s, k, t = triple(x, free[0], lk)
        if f'{s}|{k}|{t}' in rejected or (layer, s, k, t) in done or (s, k, t) in rels[layer]: continue
        out.setdefault(layer, []).append({'source': s, 'kind': k, 'target': t,
            'inferred': mark('AID-D02', f"by elimination: {x} is the only {rule['entity'].split('.')[1]} still without this link and {free[0]} the only candidate with none — nothing names either; review this first ({rule['id']}: {rule.get('message', '')})",
                             x, confidence='low', evidence_class='structural', asked_by=rule['id'])})
        rels[layer].append((s, k, t)); left = [o for o in left if not (o['record'] == x and o['rule'] == rid)]
    return out, left


def pattern_domains(docs, catalogue, maps, mm, structures, mark, rejected=()):
    """AID-D05. A BIAN service domain a pattern names (a part found anywhere, by its name) that the design lacks is taken from the catalogue
    with its parts, marked inferred (evidence: the pattern); and the one process whose name shares a word with the domain's is proposed as
    using it. Returns ([A2 record], [A2 link], [(process, 'USES_DOMAIN', domain, why)], [domain id added])."""
    from .profile import applies
    from .bian import reach
    a2 = docs.get('A2') or {'instances': [], 'relationships': []}
    recs = {i['id']: (l, i) for l, d in docs.items() for i in d.get('instances', [])}
    have = {i['name']: i['id'] for i in a2['instances'] if i['type'] == 'A2.ServiceDomain'}
    new, links, uses, added = [], [], [], []
    live = {(s, r, t) for s, r, t in maps}
    for st in structures:
        pat, S = st['pattern'], st['structure']; aw = pat.get('applies_when') or {}
        anchors = sorted(i for i, (l, r) in recs.items() if mm.known(r['type']) and mm.is_a(r['type'], aw.get('entity', '')) and applies({'when': aw.get('when') or {}}, r) and not _unconfirmed(r))
        if not anchors: continue
        for role in S['roles']:
            name = (role.get('when') or {}).get('name')
            if not (role.get('anywhere') and role['type'] == 'A2.ServiceDomain' and isinstance(name, str)): continue
            asked = f"{pat['id']}/{role['id']}"
            if name not in have and catalogue:
                keep = reach(catalogue, {name}); by = {i['id']: i for i in catalogue['instances']}
                sd = next((i for i in keep if by[i]['type'] == 'A2.ServiceDomain'), None)
                if not sd or sd in rejected: continue
                for i in sorted(keep):
                    if i in recs or any(n['id'] == i for n in new): continue
                    r = copy.deepcopy(by[i])
                    r.setdefault('attributes', {})['inferred'] = mark('AID-D05', f"the pattern {pat['title']} ({pat['id']}) says a design that has {anchors[0]} has BIAN's {name}: {role.get('reasoning', '')}".rstrip(': '),
                                                                      anchors[0] if i == sd else sd, confidence='low', evidence_class='pattern', asked_by=asked)
                    new.append(r)
                ids = set(recs) | {n['id'] for n in new}
                links += [r for r in catalogue.get('relationships', []) if r['source'] in keep and r['target'] in ids and not any((r['source'], r['kind'], r['target']) == (x['source'], x['kind'], x['target']) for x in a2.get('relationships', []) + links)]
                have[name] = sd; added.append(sd)
            sd = have.get(name)
            if not sd or any(r == 'USES_DOMAIN' and t == sd for _, r, t in live): continue
            procs = [(i, r) for i, (l, r) in recs.items() if mm.known(r['type']) and mm.is_a(r['type'], 'A1.BusinessProcess') and not _unconfirmed(r)]
            others = set().union(*[words(n) for n in have if n != name] or [set()])
            hits = {}
            for w in words(name) - others:
                got = [i for i, r in procs if w in words(r.get('name'))]
                if len(got) == 1: hits[w] = got[0]
            if len(set(hits.values())) == 1:
                p = next(iter(hits.values())); w = sorted(hits)[0]
                if (p, 'USES_DOMAIN', sd) not in live:
                    uses.append((p, 'USES_DOMAIN', sd, f"{p} is the one process whose name has the word '{w}' of BIAN's {name}, which the pattern {pat['id']} asks a process to use — name evidence only"))
    return new, links, uses, added


def _bound(docs, maps, mm, structures):
    """Each structured pattern and record it applies to, with its parts filled as `sdem comply` fills them (approved links only)."""
    from .patterns import bind
    from .profile import applies
    recs = {i['id']: (l, i) for l, d in docs.items() for i in d.get('instances', [])}
    inside, across = {}, {}
    for d in docs.values():
        for r in d.get('relationships', []):
            inside.setdefault((r['source'], r['kind'], 'out'), []).append(r['target']); inside.setdefault((r['target'], r['kind'], 'in'), []).append(r['source'])
    for s, rel, t in maps:
        across.setdefault((s, rel, 'out'), []).append(t); across.setdefault((t, rel, 'in'), []).append(s)
    for st in structures:
        pat, S = st['pattern'], st['structure']; aw = pat.get('applies_when') or {}
        for a, (l, r) in sorted(recs.items()):
            if mm.known(r['type']) and mm.is_a(r['type'], aw.get('entity', '')) and applies({'when': aw.get('when') or {}}, r) and not _unconfirmed(r):
                yield pat, S, a, recs, bind(a, S, pat['id'], recs, inside, across, mm)


def pattern_parts(docs, maps, mm, structures, mark, rejected=()):
    """AID-D06. A part a pattern requires, where the design has no record of that kind at all, is added as a planned record named for the
    part and marked inferred (evidence: the pattern), with the link the pattern draws to it — inside a layer written and marked, between
    layers proposed. Not a BIAN record (AID-D05 brings those from BIAN), not a part whose type is no one kind of record, not one a person
    rejected; and where records of the kind exist, nothing: which of them is the part is a link for a person to state.
    Returns ({layer: [record]}, {layer: [link]}, [(source, relationship, target, why, 'AID-D06')], [id added])."""
    from .profile import RECORD_FIELDS
    new, links, props, ids = {}, {}, [], []
    stands = [i['type'] for d in docs.values() for i in d.get('instances', [])]
    for pat, S, anchor, recs, (bound, via) in _bound(docs, maps, mm, structures):
        kinds = stands + [r['type'] for rs in new.values() for r in rs]   # the design as it stands, and what an earlier pattern added (CPL-14): within one pattern, what it adds is not evidence against adding its next part
        roles = {r['id']: r for r in S['roles']}; conn = {c['id']: c for c in S.get('connectors', [])}; pid = pat['id']
        changed = True
        while changed:
            changed = False
            for b, role in roles.items():
                if b == S['anchor'] or bound.get(b): continue
                c, a = (conn[via[b][0]], via[b][1]) if b in via else (None, None)
                if not (role.get('anywhere') or (a and bound.get(a))): continue
                t = role['type']; layer = t.split('.')[0]
                if layer not in ('A1', 'A3', 'A4') or not mm.known(t) or mm.is_abstract(t) or any(mm.known(k) and mm.is_a(k, t) for k in kinds): bound[b] = bound.get(b) or []; continue
                want = max(role.get('min', 1), 1); made = []
                for n in range(1, want + 1):
                    rid = f"AID-{pid}-{b.upper()}" + (f'-{n}' if want > 1 else '')
                    if rid in rejected or rid in recs or rid in ids: continue
                    why = f"the pattern {pat['title']} ({pid}) says a design that has {anchor} has this part, and the design has no {t.split('.')[1]} at all: {role.get('reasoning', '')}".rstrip(': ')
                    r = {'id': rid, 'type': t, 'version': '1', 'name': (role.get('label') or b) + (f' {n}' if want > 1 else '') + ' (inferred)', 'lifecycle_status': 'planned',
                         'attributes': {**{k: v for k, v in (role.get('when') or {}).items() if k not in RECORD_FIELDS},
                                        'conforms_to': [f'{pid}#{b}'],   # it is this part and no other (PR-23)
                                        'inferred': mark('AID-D06', why, anchor, confidence='low', evidence_class='pattern', asked_by=f'{pid}/{b}')}}
                    new.setdefault(layer, []).append(r); ids.append(rid); made.append(rid)
                    for other in (bound.get(a) or []) if c else []:
                        s, t2 = (other, rid) if c['from'] == a else (rid, other)
                        lw = f"the pattern {pid} draws this link ({c.get('label') or c['id']}) to the part it asks for"
                        if c.get('kind'): links.setdefault(layer, []).append({'source': s, 'kind': c['kind'], 'target': t2, 'inferred': mark('AID-D06', lw, anchor, confidence='low', evidence_class='pattern', asked_by=f"{pid}/{c['id']}")})
                        else: props.append((s, c['relationship'], t2, lw, 'AID-D06'))
                if made: bound[b] = made; changed = True
                else: bound[b] = bound.get(b) or []
                if not made: roles = {k: v for k, v in roles.items() if k != b}   # decided: not again in this run
    return new, links, props, ids


def name_parts(docs, maps, mm, structures):
    """AID-D07. Where several records could each be a part and the pattern allows fewer, the one whose name or id shares a word with the
    part's — and no other candidate does — is SUGGESTED. Nothing is written: a person names the part on the record (conforms_to) through a
    change set. Returns [{pattern, part, label, anchor, candidates, suggested (or None), conforms_to, why}]."""
    out = []
    for pat, S, anchor, recs, (bound, _) in _bound(docs, maps, mm, structures):
        for role in S['roles']:
            got, hi = bound.get(role['id']) or [], role.get('max', 1)
            if hi is None or len(got) <= hi: continue
            hits = {}
            for w in words(role.get('label') or role['id']):
                cs = [x for x in got if w in words(recs[x][1].get('name'), x)]
                if len(cs) == 1: hits[w] = cs[0]
            one = sorted(set(hits.values()))
            out.append({'pattern': pat['id'], 'part': role['id'], 'label': role.get('label') or role['id'], 'anchor': anchor, 'candidates': sorted(got),
                        'suggested': one[0] if len(one) == 1 else None, 'conforms_to': f"{pat['id']}#{role['id']}",
                        'why': (f"{one[0]} is the one candidate with the word '{sorted(w for w, x in hits.items() if x == one[0])[0]}' of the part's name — name evidence only" if len(one) == 1
                                else 'no one candidate is singled out by its name — a person says which')})
    return out
