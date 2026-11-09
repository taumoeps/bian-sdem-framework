"""`sdem exception` — a person's time-limited exception to one of the organisation's rules, for named records (docs/design/sdem-profile-spec.md
PR-18; the owner's decision B4, 2026-11-10).

An exception is a governed decision (`grant_exception`, attributed like every decision — verified only by a signed commit, GV-01): who,
why, which rule, which records, until when. While it holds, the rule's finding for those records is `exception_approved` in `sdem comply`
and not an error in `sdem check`; on the day after it expires the finding comes back. An agent never grants one (CTL-21). Stored in the
workspace's `exceptions.json`; `sdem exception list` shows them, active or expired.
"""
import argparse, datetime, json, sys
from pathlib import Path

FORMAT = 'sdem-exceptions/1'


def _j(p): return json.loads(Path(p).read_text(encoding='utf-8'))


def load(ws):
    f = Path(ws) / 'exceptions.json'
    return _j(f) if f.exists() else {'format': FORMAT, 'note': 'Exceptions to the organisation profile\'s rules, each a person\'s time-limited decision (sdem exception grant).', 'exceptions': []}


def grant(ws, rule, records, reason, expires, person, dry_run=False, as_of=None):
    """PR-18: record a person's exception — checked first: a person, a rule of the active profile, records of the workspace, a reason,
    and an expiry date after today."""
    from . import profile as _p
    from .comply import today
    from .layers import FILES
    from .validate import is_person
    ws = Path(ws)
    if not is_person(person): raise ValueError(f"--person {person!r}: an exception is a person's decision — never an agent's (CTL-21)")
    if not (reason or '').strip(): raise ValueError('an exception needs a reason')
    if _p.activate_from(ws) is None: raise ValueError(f'{ws}: no organisation profile — there are no rules to grant an exception from')
    known = {r['id']: r for r in _p.rules()}
    if rule not in known: raise ValueError(f"{rule}: not a rule of the profile ({', '.join(sorted(known)) or 'none'})")
    ids = {i['id'] for f in FILES.values() if (ws / f).exists() for i in _j(ws / f).get('instances', [])}
    unknown = [r for r in records if r not in ids]
    if unknown: raise ValueError(f"not records of the workspace: {', '.join(unknown)}")
    try: exp = datetime.date.fromisoformat(expires)
    except (TypeError, ValueError): raise ValueError(f'--expires {expires!r}: a date, e.g. 2026-12-31')
    now = as_of or today()
    if exp <= now: raise ValueError(f'--expires {expires}: an exception ends after today ({now.isoformat()})')
    doc = load(ws)
    n = 1 + max([int(e['id'].split('-')[1]) for e in doc['exceptions'] if e.get('id', '').startswith('EXC-')] or [0])
    r = known[rule]
    e = {'id': f'EXC-{n:03d}', 'rule': rule, 'standard': (r.get('standard') or {}).get('id'), 'pattern': (r.get('pattern') or {}).get('id'),
         'records': list(records), 'reason': reason.strip(), 'approved_by': person.strip(), 'approved_at': now.isoformat(), 'expires': expires}
    e = {k: v for k, v in e.items() if v is not None}
    if dry_run: return e, None
    from .files import Batch, record as ledger
    from .governance import record as gd
    g = gd(ws, 'grant_exception', person.strip(), rule, {'exception': e['id'], 'records': list(records), 'expires': expires, 'reason': e['reason']})
    e['decision'] = g['id']; doc['exceptions'].append(e)
    b = Batch(); b.json(ws / 'exceptions.json', doc); b.commit()
    ledger([ws / 'exceptions.json'], by=f"{person.strip()} (sdem exception grant, {g['id']})", note=e['reason'])
    return e, g


def listing(ws, as_of=None):
    from .comply import today
    now = as_of or today()
    out = []
    for e in load(ws)['exceptions']:
        exp = datetime.date.fromisoformat(e['expires'])
        out.append({**e, 'state': 'active' if now <= exp else 'expired', 'days_left': (exp - now).days})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem exception', formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description="A person's time-limited exception to one of the organisation's rules (a standard or a pattern), for named records — "
                                             'recorded as a governed decision; while it holds, sdem comply reports the finding as under an exception and sdem check does not fail on it (PR-18).',
                                 epilog='Examples:\n  sdem exception grant --workspace workspaces/payments --rule NET-07 --records APP-PAY-HUB --expires 2026-12-31 '
                                        '--reason "migration to the restricted zone in Q4" --person jane.architect --dry-run\n  sdem exception list --workspace workspaces/payments')
    sub = ap.add_subparsers(dest='cmd', required=True)
    g = sub.add_parser('grant', help="record a person's exception — never an agent's")
    g.add_argument('--workspace', required=True, metavar='DIR'); g.add_argument('--rule', required=True); g.add_argument('--records', nargs='+', required=True)
    g.add_argument('--expires', required=True, metavar='DATE'); g.add_argument('--reason', required=True); g.add_argument('--person', required=True)
    g.add_argument('--dry-run', action='store_true'); g.add_argument('--json', action='store_true')
    l = sub.add_parser('list', help='the workspace\'s exceptions, active or expired')
    l.add_argument('--workspace', required=True, metavar='DIR'); l.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    try:
        if a.cmd == 'grant':
            e, gd = grant(a.workspace, a.rule, a.records, a.reason, a.expires, a.person, a.dry_run)
            if a.json: print(json.dumps({'exception': e, 'dry_run': a.dry_run}, indent=2)); return 0
            print(f"{'would grant' if a.dry_run else 'granted'} {e['id']}: {e['rule']} for {', '.join(e['records'])} until {e['expires']}, by {e['approved_by']}"
                  + (f" — decision {gd['id']} (attributed; verified by a signed commit)" if gd else ' (dry run — nothing written)'))
            return 0
        rows = listing(a.workspace)
        if a.json: print(json.dumps({'exceptions': rows}, indent=2)); return 0
        if not rows: print('no exceptions'); return 0
        for e in rows: print(f"{e['id']}  {e['state']:<7} {e['rule']:<16} {', '.join(e['records'])}  until {e['expires']}  by {e['approved_by']} — {e['reason']}")
        return 0
    except ValueError as err:
        print(f'ERROR: {err}', file=sys.stderr); return 2


if __name__ == '__main__':
    sys.exit(main())
