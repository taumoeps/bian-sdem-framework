"""SDEM's record of inferred BIAN asset types and functional patterns (owner's decision DA2-03; spec BI-C08…BI-C11).

BIAN does not publish an asset type and functional pattern for every service domain, and SDEM cannot derive them for 66 of
release 14.0.0's 258 (BI-W02). bian/inferences-<release>.json holds one entry per such domain: each value with its
confidence, source and reasoning, a status and a history. `sdem bian import --base` applies accepted entries only;
every change goes through `sdem bian inference …`, names a person and a reason, and is added to the entry's history.

  sdem bian inference list [--status proposed]
  sdem bian inference show BI-INF-063
  sdem bian inference accept BI-INF-063 --person jane.architect --reason "checked against the BIAN portal"
  sdem bian inference challenge BI-INF-063 --person jane.architect --reason "our BIAN owner reads it as Process"
  sdem bian inference change BI-INF-063 --pattern Process --confidence medium --source "BIAN portal" --person jane.architect --reason "…"
  sdem bian inference reject BI-INF-063 --person jane.architect --reason "…"

Usage of the generated page: python -m sdem.inferences [--check]
"""
import argparse, datetime, json, re, sys
from pathlib import Path

from .metamodel import ROOT

FORMAT = 'sdem-bian-inferences/1'
STATUSES = ('open', 'proposed', 'accepted', 'challenged', 'rejected')
CONFIDENCE = ('high', 'medium', 'low')
FIELDS = ('asset_type', 'functional_pattern')
OUT = ROOT / 'docs' / 'reference' / 'bian-inferences.md'
REPO_FILE = ROOT / 'bian' / 'inferences-14.0.0.json'


class InferenceError(ValueError):
    """The record or the request is wrong (exit 2)."""


def installed_file(release):
    """The inference record that ships with SDEM for a BIAN release, or None."""
    from .paths import DATA_ROOT
    f = DATA_ROOT / 'bian' / f'inferences-{release}.json'
    return f if f.exists() else None


def read(path):
    rec = json.loads(Path(path).read_text(encoding='utf-8'))
    if rec.get('format') != FORMAT: raise InferenceError(f'{path}: not an SDEM inference record ({FORMAT})')
    return rec


def snapshot(e):
    return {'asset_type': (e.get('asset_type') or {}).get('value'), 'functional_pattern': (e.get('functional_pattern') or {}).get('value'), 'status': e['status']}


def check(rec, domain_names=None):
    """Errors in a record (BI-C10): ids and domains unique, values well formed, accepted entries complete, and every change in the history."""
    from .bian import PATTERNS
    from .validate import is_person
    errs, ids, names = [], set(), set()
    for e in rec.get('entries', []):
        w = e.get('id', '?')
        if not re.fullmatch(r'BI-INF-\d{3}', w): errs.append(f'{w}: id must be BI-INF-nnn')
        if w in ids: errs.append(f'{w}: id used twice')
        ids.add(w)
        n = (e.get('service_domain') or '').lower()
        if n in names: errs.append(f"{w}: service domain {e.get('service_domain')!r} has two entries")
        names.add(n)
        if domain_names is not None and n not in domain_names: errs.append(f"{w}: {e.get('service_domain')!r} is not a service domain of BIAN {rec.get('bian_release')}")
        if e.get('status') not in STATUSES: errs.append(f"{w}: status {e.get('status')!r} is not one of {', '.join(STATUSES)}")
        for f in FIELDS:
            v = e.get(f)
            if v is None: continue
            for k in ('value', 'confidence', 'source', 'reasoning'):
                if not str(v.get(k) or '').strip(): errs.append(f'{w}: {f} has no {k} — every inferred value states its source, reasoning and confidence')
            if v.get('confidence') and v['confidence'] not in CONFIDENCE: errs.append(f"{w}: {f} confidence {v['confidence']!r} is not one of {', '.join(CONFIDENCE)}")
        p = (e.get('functional_pattern') or {}).get('value')
        if p and p.upper() not in PATTERNS: errs.append(f"{w}: {p!r} is not a BIAN functional pattern")
        if e.get('status') in ('proposed', 'accepted', 'challenged') and not (e.get('asset_type') and e.get('functional_pattern')):
            errs.append(f"{w}: a {e['status']} entry needs both an asset type and a functional pattern")
        h = e.get('history') or []
        if not h: errs.append(f'{w}: no history')
        elif h[-1].get('after') != snapshot(e): errs.append(f'{w}: changed without a history entry — change it with `sdem bian inference …`')
        for x in h[1:]:
            if not is_person(x.get('by')): errs.append(f"{w}: history entry of {x.get('date')} is not a person's ({x.get('by')!r})")
            if not str(x.get('reason') or '').strip(): errs.append(f"{w}: history entry of {x.get('date')} gives no reason")
    return errs


def accepted(rec):
    """{service domain (lower case): entry} for the entries the import applies (BI-C09)."""
    return {e['service_domain'].lower(): e for e in rec.get('entries', []) if e['status'] == 'accepted'}


def act(rec, entry_id, action, person, reason, now=None, **values):
    """Change one entry (BI-C11) and add the change to its history; returns the entry."""
    from .bian import PATTERNS
    from .validate import is_person
    if not is_person(person): raise InferenceError(f'--person {person!r} is not a person — a change to the record is a person\'s decision (CTL-21)')
    e = next((x for x in rec['entries'] if x['id'] == entry_id), None)
    if e is None: raise InferenceError(f'{entry_id}: no such entry — `sdem bian inference list` shows them')
    reason = (reason or '').strip()
    if action != 'accept' and not reason: raise InferenceError(f'--reason is required to {action} an entry')
    before = snapshot(e)
    if action == 'accept':
        if e['status'] == 'accepted': raise InferenceError(f'{entry_id} is already accepted')
        if not (e.get('asset_type') and e.get('functional_pattern')): raise InferenceError(f'{entry_id} has no values to accept — give them with `change` first')
        e['status'] = 'accepted'
    elif action == 'challenge':
        if e['status'] not in ('proposed', 'accepted'): raise InferenceError(f"{entry_id} is {e['status']} — only a proposed or accepted entry can be challenged")
        e['status'] = 'challenged'
    elif action == 'reject':
        if e['status'] == 'rejected': raise InferenceError(f'{entry_id} is already rejected')
        e['status'] = 'rejected'
    elif action == 'change':
        given = {k: v for k, v in values.items() if v not in (None, '')}
        if not given: raise InferenceError('change needs --asset-type and/or --pattern (with --confidence, --source, --reasoning)')
        for f, key in (('asset_type', 'asset_type'), ('functional_pattern', 'pattern')):
            if given.get(key) is None: continue
            v = given[key].strip()
            if f == 'functional_pattern':
                if v.upper() not in PATTERNS: raise InferenceError(f"{v!r} is not a BIAN functional pattern ({', '.join(p.title() for p in PATTERNS)})")
                v = v.upper().title()
            conf = given.get('confidence') or 'low'
            if conf not in CONFIDENCE: raise InferenceError(f"--confidence must be one of {', '.join(CONFIDENCE)}")
            if not given.get('source'): raise InferenceError('--source is required with a new value — where it comes from')
            e[f] = {'value': v, 'confidence': conf, 'source': given['source'].strip(), 'reasoning': (given.get('reasoning') or reason).strip()}
        e['status'] = 'proposed' if e.get('asset_type') and e.get('functional_pattern') else 'open'
    else:
        raise InferenceError(f'unknown action {action!r}')
    when = now or datetime.date.today().isoformat()
    e['history'].append({'date': when, 'by': person.strip(), 'by_kind': 'person', 'action': action, 'reason': reason or 'accepted',
                         'before': before, 'after': snapshot(e)})
    return e


def render(rec):
    from collections import Counter
    c = Counter(e['status'] for e in rec['entries'])
    L = ['# BIAN inferences — the asset types and functional patterns SDEM infers', '',
         f"> Generated by `python -m sdem.inferences` from [`bian/inferences-{rec['bian_release']}.json`](../../bian/inferences-{rec['bian_release']}.json). "
         "Do not edit by hand; change an entry with `sdem bian inference …` (CI fails if this page is out of date).", '',
         f"BIAN does not publish an asset type and functional pattern for every service domain, and SDEM cannot derive them for {len(rec['entries'])} of "
         f"BIAN {rec['bian_release']}'s service domains. This record holds SDEM's inference for each, with its source, reasoning and confidence. "
         "`sdem bian import --base` applies **accepted** entries only — the domain is marked `classification: inferred` with `inference_ref` naming the entry; "
         "every other domain here stays *not known yet*. To accept, challenge, change or reject an entry: "
         "`sdem bian inference accept|challenge|change|reject <id> --person <you> --reason \"…\"`, then a pull request — every change names a person and a reason, "
         "and is kept in the entry's history.", '',
         '| Status | Entries | Meaning |', '|---|---|---|']
    L += [f"| {s} | {c.get(s, 0)} | {rec['statuses'][s]} |" for s in STATUSES]
    L += ['', '## The entries', '', '| Id | Service domain | Asset type | Conf. | Functional pattern | Conf. | Status | Last change |', '|---|---|---|---|---|---|---|---|']
    for e in rec['entries']:
        a, p, h = e.get('asset_type') or {}, e.get('functional_pattern') or {}, e['history'][-1]
        L.append(f"| {e['id']} | {e['service_domain']} | {a.get('value', '—')} | {a.get('confidence', '—')} | {p.get('value', '—')} | {p.get('confidence', '—')} | "
                 f"{e['status']} | {h['date']} {h['action']} — {h['by']} |")
    L += ['', '## Sources and reasoning', '']
    for e in rec['entries']:
        L += [f"### {e['id']} · {e['service_domain']}", '', f"Control record: {e['control_record'] or '— (none published)'} · operations published: {e['operations']} · status: **{e['status']}**", '']
        for f, label in (('asset_type', 'Asset type'), ('functional_pattern', 'Functional pattern')):
            v = e.get(f)
            L.append(f"- **{label}:** " + (f"{v['value']} ({v['confidence']}) — {v['reasoning']} *Source:* {v['source']}" if v else 'not inferred'))
        L += ['', '| Date | By | Action | Reason |', '|---|---|---|---|'] + [f"| {h['date']} | {h['by']} | {h['action']} | {h['reason']} |" for h in e['history']] + ['']
    return '\n'.join(L)


def _editable(path):
    p = Path(path) if path else Path('bian') / REPO_FILE.name
    if not p.exists():
        raise InferenceError(f'{p}: not found — run this in a checkout of the SDEM repository (the record changes by pull request), or give --file')
    return p


def commands(argv=None):
    ap = argparse.ArgumentParser(prog='sdem bian inference', formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description="SDEM's record of inferred BIAN asset types and functional patterns: list, show, accept, challenge, change or reject an entry. "
                                             'Every change names a person and a reason and is kept in the entry\'s history; the import applies accepted entries only.',
                                 epilog=__doc__.split('\n\n')[2])
    sub = ap.add_subparsers(dest='cmd', required=True)
    ls = sub.add_parser('list', help='the entries, with values, confidence and status'); ls.add_argument('--status', choices=STATUSES)
    sh = sub.add_parser('show', help='one entry: values, sources, reasoning, history'); sh.add_argument('id')
    for name, hlp in (('accept', 'accept an entry — the import applies it'), ('challenge', 'question an entry — the import stops applying it'),
                      ('change', 'give new values — the entry becomes proposed'), ('reject', 'reject an entry — the import does not apply it')):
        p = sub.add_parser(name, help=hlp); p.add_argument('id'); p.add_argument('--person', required=True, help='your name — a person')
        p.add_argument('--reason', required=(name != 'accept'), help='why — kept in the history')
        if name == 'change':
            p.add_argument('--asset-type'); p.add_argument('--pattern'); p.add_argument('--confidence', choices=CONFIDENCE, default='low')
            p.add_argument('--source'); p.add_argument('--reasoning')
        p.add_argument('--dry-run', action='store_true')
    for p in sub.choices.values():
        p.add_argument('--file', metavar='FILE', help=f'the record (default: bian/{REPO_FILE.name} in this folder, or the installed one to read)')
        p.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    try:
        if a.cmd in ('list', 'show'):
            path = Path(a.file) if a.file else (Path('bian') / REPO_FILE.name if (Path('bian') / REPO_FILE.name).exists() else installed_file('14.0.0'))
            if not path: raise InferenceError('no inference record installed')
            rec = read(path)
            if a.cmd == 'list':
                rows = [e for e in rec['entries'] if not a.status or e['status'] == a.status]
                if a.json: print(json.dumps({'file': str(path), 'entries': [snapshot(e) | {'id': e['id'], 'service_domain': e['service_domain']} for e in rows]}, indent=2)); return 0
                for e in rows:
                    at, fp = e.get('asset_type') or {}, e.get('functional_pattern') or {}
                    print(f"{e['id']}  {e['service_domain']:<34} {at.get('value', '—'):<32} {fp.get('value', '—'):<12} {fp.get('confidence', '—'):<7} {e['status']}")
                print(f"{len(rows)} entr{'y' if len(rows) == 1 else 'ies'} — sdem bian inference show <id> for sources, reasoning and history")
            else:
                e = next((x for x in rec['entries'] if x['id'] == a.id), None)
                if not e: raise InferenceError(f'{a.id}: no such entry')
                if a.json: print(json.dumps(e, indent=2, ensure_ascii=False)); return 0
                print(f"{e['id']} {e['service_domain']} — {e['status']} (control record {e['control_record'] or 'none'}, {e['operations']} operations)")
                for f in FIELDS:
                    v = e.get(f)
                    print(f"  {f}: " + (f"{v['value']} ({v['confidence']})\n    reasoning: {v['reasoning']}\n    source: {v['source']}" if v else 'not inferred'))
                print('  history:'); [print(f"    {h['date']}  {h['action']:<9} {h['by']} — {h['reason']}") for h in e['history']]
            return 0
        path = _editable(a.file); rec = read(path)
        e = act(rec, a.id, a.cmd, a.person, a.reason, asset_type=getattr(a, 'asset_type', None), pattern=getattr(a, 'pattern', None),
                confidence=getattr(a, 'confidence', None), source=getattr(a, 'source', None), reasoning=getattr(a, 'reasoning', None))
        from .bian import read_pack, base_file
        errs = check(rec, {d['name'].lower() for d in read_pack(base_file())})
        if errs: raise InferenceError('the record would not pass its checks — nothing written:\n  ' + '\n  '.join(errs[:10]))
        snap = snapshot(e)
        if a.json:
            print(json.dumps({'id': e['id'], 'service_domain': e['service_domain'], 'action': a.cmd, 'dry_run': a.dry_run, **snap,
                              'next': None if a.dry_run else 'commit the record on a branch and open a pull request'}, indent=2))
            if a.dry_run: return 0
            from .files import write_json
            write_json(path, rec); return 0
        print(f"{'would change' if a.dry_run else 'changed'} {e['id']} {e['service_domain']}: {snap['asset_type'] or '—'} · {snap['functional_pattern'] or '—'} · {snap['status']}")
        if a.dry_run: return 0
        from .files import write_json
        write_json(path, rec)
        page = ' and regenerate the page (`python -m sdem.inferences`)' if Path(path).resolve() == REPO_FILE.resolve() else ''
        print(f'Next: commit the record{page} on a branch and open a pull request — the change is final when it is merged.')
        return 0
    except InferenceError as err:
        print(f'ERROR: {err}', file=sys.stderr); return 2


def main(argv=None):   # the generated page — run by `sdem model regenerate/check`
    ap = argparse.ArgumentParser(prog='sdem-inferences'); ap.add_argument('--check', action='store_true'); a = ap.parse_args(argv)
    from .docmap import relink
    t = relink(render(read(REPO_FILE)), OUT)
    if a.check:
        ok = OUT.exists() and OUT.read_text(encoding='utf-8') == t
        print(f"{OUT.name}: {'up to date' if ok else 'STALE: regenerate with python -m sdem.inferences'}"); return 0 if ok else 1
    OUT.write_text(t, encoding='utf-8'); print(f'wrote {OUT.relative_to(ROOT)}'); return 0


if __name__ == '__main__':
    raise SystemExit(main())
