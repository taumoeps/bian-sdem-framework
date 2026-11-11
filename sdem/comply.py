"""Standards and pattern compliance — `sdem comply` (docs/design/sdem-profile-spec.md PR-13…PR-20; the owner's decisions B1–B6, 2026-11-10).

An organisation's standards (security, network, technology …) and reference-architecture patterns are rules in its profile: in the
profile itself, or in standards and pattern files it includes. One evaluator reads them all, deterministically, over the workspace:

  require   the record carries these attributes — a placeholder (TBD, unknown, /TBD) or an empty value is not carrying one (PR-20)
  check     an attribute compares with a value: == != < <= > >= in not_in, and before/after a date (`today`, `today+90d`, `2027-01-01`)
  link      at least `min` links of a kind inside the layer (optionally from or to a type)
  compare   linked records (by a kind inside the layer) differ in — or share — an attribute
  across    the record's APPROVED cross-layer links of a relationship (DEPLOYED_ON …): at least `min`, and `check` holds on each linked record

Each rule × record has one outcome: compliant · non_compliant · not_applicable (its `when` does not hold) · unresolved (a value is unknown,
or the record is inferred and unconfirmed, or a planned design not yet complete — never counted compliant) · exception_approved (a person
granted a time-limited exception, `sdem exception grant`). A rule not yet effective (`effective_from` after today) is reported as a warning.
`sdem check` keeps enforcing the rules (errors; warnings for severity warning); `sdem comply` reports every outcome. Read-only.
"""
import argparse, datetime, json, os, re, sys
from pathlib import Path

OUTCOMES = ('compliant', 'non_compliant', 'unresolved', 'exception_approved', 'not_applicable')
OPS = ('==', '!=', '<', '<=', '>', '>=', 'in', 'not_in', 'before', 'after')
DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def today():
    """The date rules are evaluated on: SDEM_AS_OF (a fixed date, for CI and tests) or the computer's date."""
    v = os.environ.get('SDEM_AS_OF')
    return datetime.date.fromisoformat(v) if v else datetime.date.today()


def date_of(v, as_of=None):
    """`today`, `today+90d`, `today-365d` or an ISO date → a date; anything else → None."""
    as_of = as_of or today()
    if isinstance(v, str):
        m = re.fullmatch(r'today(?:([+-])(\d+)d)?', v.strip())
        if m: return as_of + datetime.timedelta(days=(int(m.group(2)) if m.group(1) == '+' else -int(m.group(2))) if m.group(1) else 0)
        if DATE.match(v): return datetime.date.fromisoformat(v)
    return None


def test(chk, value, as_of=None):
    """True (holds), False (does not) or None (cannot tell: no value, a placeholder, or values that do not compare)."""
    from .conformance import unknown_value
    if value is None or unknown_value(value): return None
    op, want = chk['op'], chk.get('value')
    if op in ('in', 'not_in'):
        vals = want if isinstance(want, list) else [want]
        have = value if isinstance(value, list) else [value]
        return all(x in vals for x in have) if op == 'in' else not any(x in vals for x in have)
    if op in ('before', 'after'):
        a, b = date_of(value, as_of), date_of(want, as_of)
        if a is None or b is None: return None
        return a < b if op == 'before' else a > b
    if op in ('==', '!='): return (value == want) == (op == '==')
    try: a, b = float(value), float(want)
    except (TypeError, ValueError): return None
    return {'<': a < b, '<=': a <= b, '>': a > b, '>=': a >= b}[op]


def describe_check(c):
    return f"{c['attribute']} {c['op'].replace('_', ' ')} {c.get('value')}"


def _unknown(at, k):
    from .conformance import unknown_value
    return k not in at or at[k] in (None, '', []) or bool(unknown_value(at[k]))


def evaluate(datasets, maps, mm, rules, exceptions=(), as_of=None):
    """Every rule × record outcome. datasets: {layer: dataset}; maps: approved cross-layer links [(source, relationship, target)];
    rules: the active profile's rules (with their standard and pattern); exceptions: granted exceptions. Returns findings."""
    from . import profile as _p
    as_of = as_of or today()
    recs = {i['id']: (l, i) for l, d in datasets.items() for i in d.get('instances', [])}
    links_out, links_in = {}, {}
    for l, d in datasets.items():
        for r in d.get('relationships', []):
            links_out.setdefault((r['source'], r['kind']), []).append(r['target']); links_in.setdefault((r['target'], r['kind']), []).append(r['source'])
    across_out, across_in = {}, {}
    for s, rel, t in maps:
        across_out.setdefault((s, rel), []).append(t); across_in.setdefault((t, rel), []).append(s)
    exc = {}
    for e in exceptions or []:
        for rid in e.get('records', []): exc.setdefault((e['rule'], rid), []).append(e)
    out = []
    for rule in rules:
        sev = rule.get('severity', 'error')
        eff = date_of((rule.get('standard') or {}).get('effective_from') or (rule.get('pattern') or {}).get('effective_from') or rule.get('effective_from'), as_of)
        not_yet = eff is not None and as_of < eff
        for rid, (layer, i) in sorted(recs.items()):
            if not mm.known(i['type']) or not mm.is_a(i['type'], rule['entity']): continue
            base = {'rule': rule['id'], 'standard': _ref(rule.get('standard')), 'pattern': _ref(rule.get('pattern')), 'layer': layer, 'record': rid,
                    'name': i.get('name'), 'severity': 'warning' if not_yet else sev, 'message': rule.get('message', '')}
            if not _p.applies(rule, i): out.append({**base, 'outcome': 'not_applicable'}); continue
            at = i.get('attributes') or {}
            fails, unknown = [], []
            missing = [x for x in rule.get('require', []) if _unknown(at, x)]
            if missing: fails.append(f"missing {', '.join(missing)}")
            if rule.get('check') and not rule.get('across'):
                c = rule['check']; ok = test(c, i.get(c['attribute'], at.get(c['attribute'])), as_of)
                if ok is None: unknown.append(f"{c['attribute']} not known")
                elif not ok: fails.append(f"{c['attribute']} is {at.get(c['attribute'])!r} — must be {describe_check(c)[len(c['attribute']) + 1:]}")
            if rule.get('link'):
                lk = rule['link']; ends = (links_in if lk.get('direction') == 'in' else links_out).get((rid, lk['kind']), [])
                ends = [e for e in ends if not lk.get('to') or (e in recs and mm.is_a(recs[e][1]['type'], lk['to']))]
                if len(ends) < lk.get('min', 1): fails.append(f"{len(ends)} {lk['kind']} link(s){' to ' + lk['to'] if lk.get('to') else ''}, needs at least {lk.get('min', 1)}")
            if rule.get('compare'):
                c = rule['compare']; k = c['attribute']
                for other in links_out.get((rid, c['kind']), []):   # PR-11a: a value that is missing or a placeholder cannot be compared — unresolved, never compliant
                    if other not in recs: unknown.append(f'{other} ({c["kind"]}) is not in the workspace'); continue
                    oat = recs[other][1].get('attributes') or {}
                    gone = [x for x, a in ((rid, at), (other, oat)) if _unknown(a, k)]
                    if gone: unknown.append(f"{k} of {' and '.join(gone)} not known — cannot compare ({c['kind']})"); continue
                    mine, theirs = at[k], oat[k]
                    if (c['must'] == 'differ') == (mine == theirs):
                        fails.append(f"{c['attribute']} is {mine!r} here and {theirs!r} on {other} ({c['kind']}) — must {c['must']}")
            if rule.get('across'):
                a = rule['across']; ends = (across_in if a.get('direction') == 'in' else across_out).get((rid, a['relationship']), [])
                if len(ends) < a.get('min', 1): fails.append(f"{len(ends)} approved {a['relationship']} link(s), needs at least {a.get('min', 1)}")
                c = rule.get('check')
                for e in ends if c else []:
                    other = recs.get(e)
                    if not other: unknown.append(f'{e} is not in the workspace'); continue
                    oat = other[1].get('attributes') or {}
                    ok = test(c, other[1].get(c['attribute'], oat.get(c['attribute'])), as_of)
                    if ok is None: unknown.append(f"{c['attribute']} of {e} not known")
                    elif not ok: fails.append(f"{e} ({a['relationship']}): {c['attribute']} is {oat.get(c['attribute'])!r} — must be {describe_check(c)[len(c['attribute']) + 1:]}")
            mark = at.get('inferred') if isinstance(at.get('inferred'), dict) else None
            inferred = bool(mark) and mark.get('status') != 'confirmed'
            planned = i.get('lifecycle_status') == 'planned'
            if inferred: outcome, why = 'unresolved', 'inferred by SDEM and not yet confirmed by a person' + (f" ({'; '.join(fails + unknown)})" if fails or unknown else '')
            elif fails and planned: outcome, why = 'unresolved', 'planned — ' + '; '.join(fails)
            elif fails: outcome, why = 'non_compliant', '; '.join(fails)
            elif unknown: outcome, why = 'unresolved', '; '.join(unknown)
            else: outcome, why = 'compliant', ''
            f = {**base, 'outcome': outcome, 'detail': why, 'parts': fails}
            if outcome in ('non_compliant', 'unresolved'):
                for e in exc.get((rule['id'], rid), []):
                    exp = date_of(e.get('expires'), as_of)
                    if exp is not None and as_of <= exp:
                        f.update(outcome='exception_approved', exception={'id': e['id'], 'expires': e['expires'], 'approved_by': e.get('approved_by')}); break
                    f['detail'] += f"; exception {e['id']} expired on {e.get('expires')}"
            if not_yet and outcome == 'non_compliant': f['detail'] += f' — not yet effective (from {eff.isoformat()})'
            out.append(f)
    return out


def _ref(x): return {k: x[k] for k in ('id', 'version', 'title') if k in x} if x else None


def summary(findings):
    s = {o: 0 for o in OUTCOMES}
    for f in findings: s[f['outcome']] += 1
    groups = {}
    for f in findings:
        for kind in ('pattern', 'standard'):
            if f.get(kind):
                g = groups.setdefault((kind, f[kind]['id']), {'kind': kind, **f[kind], **{o: 0 for o in OUTCOMES}}); g[f['outcome']] += 1; break
        else:
            g = groups.setdefault(('profile', ''), {'kind': 'profile', 'id': 'profile rules', **{o: 0 for o in OUTCOMES}}); g[f['outcome']] += 1
    return s, sorted(groups.values(), key=lambda g: (g['kind'], g['id']))


def collect(ws, as_of=None):
    """PR-19: the active profile's standards and patterns over a workspace."""
    from . import profile as _p
    from .layers import FILES
    from .metamodel import Metamodel
    from .patterns import evaluate as structures
    ws = Path(ws)
    datasets, maps, mm, merged = workspace_data(ws)
    as_of = as_of or today()
    findings = evaluate(datasets, maps, mm, _p.rules(), _p.exceptions(), as_of)
    found, bindings = structures(datasets, maps, mm, _p.structures(), _p.exceptions(), as_of)   # PR-21…PR-24: patterns as structures
    findings += found
    s, groups = summary(findings)
    blocking = [f for f in findings if f['outcome'] == 'non_compliant' and f['severity'] == 'error']
    return {'workspace': str(ws), 'as_of': as_of.isoformat(), 'profile': _p.record(), 'summary': s, 'groups': groups,
            'findings': [f for f in findings if f['outcome'] != 'not_applicable'], 'bindings': bindings, 'blocking': len(blocking), 'profile_active': merged is not None}


def workspace_data(ws):
    """The workspace's layer datasets, its APPROVED cross-layer links, the metamodel with its profile, and the merged profile."""
    from . import profile as _p
    from .layers import FILES
    from .metamodel import Metamodel
    ws = Path(ws)
    merged = _p.activate_from(ws)
    mm = Metamodel.load()
    datasets = {l: json.loads((ws / f).read_text(encoding='utf-8')) for l, f in FILES.items() if (ws / f).exists()}
    reg = json.loads((ws / 'mappings.json').read_text(encoding='utf-8')) if (ws / 'mappings.json').exists() else {}
    maps = [(m['source']['id'], m['relationship'], m['target']['id']) for m in reg.get('mappings', []) if m.get('status') == 'approved']
    return datasets, maps, mm, merged


def render(r):
    s = r['summary']
    if not r['profile_active']: return f"{r['workspace']}: no organisation profile — no standards or patterns to evaluate (sdem profile example shows the form)"
    L = [f"Standards and patterns — {r['workspace']} (profile {r['profile']['name']} v{r['profile']['version']}, as of {r['as_of']})",
         f"  {s['compliant']} compliant · {s['non_compliant']} non-compliant · {s['unresolved']} unresolved · {s['exception_approved']} under an exception · {s['not_applicable']} not applicable", '']
    for g in r['groups']:
        L.append(f"  {g['kind']:<8} {g['id']:<22} {g.get('version', ''):<6} {g['compliant']:>3} ok  {g['non_compliant']:>3} not  {g['unresolved']:>3} unresolved  {g['exception_approved']:>3} exception   {g.get('title', '')}")
    rows = [f for f in r['findings'] if f['outcome'] != 'compliant']
    if rows: L += ['']
    for f in rows:
        tag = {'non_compliant': 'NOT MET', 'unresolved': 'UNRESOLVED', 'exception_approved': 'EXCEPTION'}[f['outcome']]
        L.append(f"  {tag:<10} {f['rule']:<16} {f['layer']} {f['record']}: {f['detail'] or f['message']}" + (f" (until {f['exception']['expires']}, {f['exception']['id']})" if f.get('exception') else '')
                 + (' [warning]' if f['severity'] == 'warning' and f['outcome'] == 'non_compliant' else ''))
    L += ['', 'Compliance is separate from `sdem check` (structure): a workspace can pass its checks and still not meet a standard.' if r['blocking'] or s['unresolved'] else 'Every applicable rule is met (or under an approved exception).']
    return '\n'.join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem comply', formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description="The organisation's standards and reference-architecture patterns (its profile's rules, and the standards and pattern files it includes) "
                                             'over a workspace: per rule and record compliant, non-compliant, unresolved, under an exception or not applicable — separate from sdem check. Read-only (PR-19).',
                                 epilog='Examples:\n  sdem comply --workspace workspaces/payments\n  sdem comply --workspace workspaces/payments --json --as-of 2027-01-01')
    ap.add_argument('--workspace', required=True, metavar='DIR')
    ap.add_argument('--as-of', metavar='DATE', help='evaluate dates (effective dates, expiries, `today`) as of this date')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    ws = Path(a.workspace)
    from .layers import FILES
    if not (ws / 'mappings.json').exists() or not any((ws / f).exists() for f in FILES.values()):
        print(f'ERROR: {ws}: not a workspace folder (it needs mappings.json and at least one layer dataset)', file=sys.stderr); return 2
    from .profile import ProfileError
    try: r = collect(ws, datetime.date.fromisoformat(a.as_of) if a.as_of else None)
    except ProfileError as e: print(f'ERROR: {e}', file=sys.stderr); return 2
    print(json.dumps(r, indent=2, ensure_ascii=False) if a.json else render(r))
    return 1 if r['blocking'] else 0


if __name__ == '__main__':
    sys.exit(main())
