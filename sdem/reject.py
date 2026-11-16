"""`sdem reject` — a person rejects proposed links between layers (docs/design/sdem-public-twin-follow-up-design.md RJ-01…RJ-07; control CTL-21).

The mirror of `sdem approve`. The link is written to the registry with status `rejected`, the reviewer (a person) and the date; the
reason is kept in its rationale and in a governance decision. A rejected link is remembered: `sdem link` and `sdem aid` do not propose
it again (RJ-03), nor put something in its place (RJ-04). Approving the same link later supersedes the rejection (RJ-05). Agents never
run this command.
"""
import argparse, copy, datetime, json, sys
from pathlib import Path

from .approve import _next_id
from .metamodel import Metamodel
from .validate import is_person, load_registry, load_schema, validate


class RejectError(Exception):
    pass


def reject(registry, proposals, ids, reviewer, reason, date=None):
    """Returns the new registry (a copy) and the rejected records; raises RejectError with the reason when it cannot."""
    who = (reviewer or '').strip()
    if not is_person(who): raise RejectError(f'CTL-21: the reviewer must be a person, not {reviewer!r} — give your own name')
    why = (reason or '').strip()
    if not why: raise RejectError('--reason is required: why the link is wrong — it is kept, so the link is not proposed again (RJ-01)')
    reg = copy.deepcopy(registry); by_id = {m['mapping_id']: m for m in proposals.get('mappings', [])}
    key = lambda m: (m['source']['id'], m['relationship'], m['target']['id'])
    decided = {key(m): m.get('status') for m in reg['mappings'] if m.get('status') in ('approved', 'rejected')}
    out = []
    for pid in ids:
        p = by_id.get(pid)
        if not p: raise RejectError(f'{pid}: not in the proposals file')
        if decided.get(key(p)) == 'approved': raise RejectError(f'{pid}: this link is approved in the registry — supersede or retire it there; a proposal is what `sdem reject` decides')
        if decided.get(key(p)) == 'rejected': raise RejectError(f'{pid}: this link is already rejected in the registry')
        r = copy.deepcopy(p)
        r.update(mapping_id=_next_id(reg['mappings']), status='rejected', reviewer_id=who, approved_at=date or datetime.date.today().isoformat(),
                 rationale=f"Rejected by {who}: {why} — as proposed: {p.get('rationale', '')}".rstrip(' —:'))
        reg['mappings'].append(r); decided[key(r)] = 'rejected'; out.append((r, why))
    issues = validate(reg, load_registry(), load_schema(), metamodel=Metamodel.load())
    if issues: raise RejectError('the registry would not pass its checks — nothing was written:\n  ' + '\n  '.join(issues[:10]))
    return reg, out


def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem reject', formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description='A person rejects proposed links: each is kept in the registry as rejected, with the reviewer, the date and the reason, so it is '
                                             'not proposed again and nothing is inferred in its place. Approving the same link later supersedes the rejection. Agents never run this.',
                                 epilog='Example (J3):\n  sdem reject P-RUN-018 --proposals work/links/proposals.json --workspace work/est --reviewer jane.architect \\\n'
                                        '      --reason "the ingress only terminates the channel; it does not realise the domain"')
    ap.add_argument('ids', nargs='+', metavar='PROPOSAL', help='proposal id(s) from `sdem review`')
    ap.add_argument('--proposals', required=True, metavar='FILE'); ap.add_argument('--workspace', dest='estate', metavar='DIR', help='workspace folder (its mappings.json)')
    ap.add_argument('--registry', metavar='FILE', help='the registry, if not <workspace>/mappings.json')
    ap.add_argument('--reviewer', '--person', dest='reviewer', required=True, help='your name — a person (CTL-21)')
    ap.add_argument('--reason', help='why the link is wrong — required, and kept')
    ap.add_argument('--date', help='the date (default today)'); ap.add_argument('--dry-run', action='store_true', help='show the record; write nothing')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    reg_path = Path(a.registry) if a.registry else Path(a.estate or '.') / 'mappings.json'
    if not a.registry and not a.estate: ap.error('give --workspace DIR or --registry FILE')
    try:
        reg = json.loads(reg_path.read_text(encoding='utf-8')); props = json.loads(Path(a.proposals).read_text(encoding='utf-8'))
        new, recs = reject(reg, props, a.ids, a.reviewer, a.reason, a.date)
    except (OSError, ValueError) as e:
        print(f'ERROR: {e}', file=sys.stderr); return 2
    except RejectError as e:
        print(f'ERROR: {e}', file=sys.stderr); return 1
    if a.json: print(json.dumps([r for r, _ in recs], indent=2, ensure_ascii=False))
    else:
        for r, why in recs:
            print(f"{'would reject' if a.dry_run else 'rejected'} {r['mapping_id']}: {r['source']['id']} -{r['relationship']}-> {r['target']['id']}  (reviewer {r['reviewer_id']}, {r['approved_at']}: {why})")
    if a.dry_run: return 0
    from .files import write_json
    write_json(reg_path, new)
    from .governance import record   # GV-01: the decision, attributed
    for r, why in recs: record(reg_path.parent, 'reject_link', r['reviewer_id'], r['mapping_id'], {'link': f"{r['source']['id']} {r['relationship']} {r['target']['id']}", 'reason': why})
    if not a.json:
        print(f'{reg_path} updated and checked — the link will not be proposed again, and nothing is inferred in its place; approving it later supersedes this (sdem approve). '
              'Next: commit on a branch and open a pull request.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
