"""`sdem approve` — a person approves proposed links into the registry (docs/design/sdem-workbench-spec.md WB-A04; control CTL-21).

Writes a correct registry record from a proposal: a new unique id, status `approved`, the reviewer (a person — CTL-21) and
date, the evidence the link type requires, and — when it replaces an old link — `previous_mapping_id` with the old link
set to `superseded`. The whole registry is validated before anything is written. Approval still becomes final only when the
change is merged in a reviewed pull request. Agents never run this command.
"""
import argparse, collections, copy, datetime, json, re, sys
from pathlib import Path

from .metamodel import Metamodel
from .validate import is_person, load_registry, load_schema, validate


class ApproveError(Exception):
    pass


def _next_id(mappings):
    """The registry's own id style: the most common prefix (e.g. PAY-) and the next number after the highest."""
    ids = [m['mapping_id'] for m in mappings]
    pref = collections.Counter(re.match(r'^(.*?)(\d+)$', i).group(1) for i in ids if re.match(r'^(.*?)(\d+)$', i)).most_common(1)
    p = pref[0][0] if pref else 'MAP-'
    nums = [int(re.match(r'^(.*?)(\d+)$', i).group(2)) for i in ids if i.startswith(p) and re.match(r'^(.*?)(\d+)$', i)]
    width = max((len(re.match(r'^(.*?)(\d+)$', i).group(2)) for i in ids if i.startswith(p)), default=3)
    return f'{p}{max(nums, default=0) + 1:0{width}d}'


def approve(registry, proposals, ids, reviewer, evidence, supersedes=None, new_id=None, date=None, bian_release=None):
    """Returns the new registry (a copy) and the approved records; raises ApproveError with the reason when it cannot."""
    who = (reviewer or '').strip()
    if not is_person(who):
        raise ApproveError(f'CTL-21: the reviewer must be a person, not {reviewer!r} — give your own name')
    if not evidence: raise ApproveError('--evidence is required: the document that proves the link, as kind:reference (see `sdem approve --help`)')
    if any(':' not in e for e in evidence): raise ApproveError('evidence must be written kind:reference, e.g. deployment_design:PAY-REHOST#cutover')
    if supersedes and len(ids) != 1: raise ApproveError('--supersedes works with one proposal at a time')
    if new_id and len(ids) != 1: raise ApproveError('--id works with one proposal at a time')
    reg = copy.deepcopy(registry); by_id = {m['mapping_id']: m for m in proposals.get('mappings', [])}
    approved_keys = {(m['source']['id'], m['relationship'], m['target']['id']) for m in reg['mappings'] if m.get('status') == 'approved'}
    out = []
    for pid in ids:
        p = by_id.get(pid)
        if not p: raise ApproveError(f'{pid}: not in the proposals file')
        if (p['source']['id'], p['relationship'], p['target']['id']) in approved_keys: raise ApproveError(f'{pid}: this link is already approved in the registry')
        r = copy.deepcopy(p)
        r.update(mapping_id=new_id or _next_id(reg['mappings']), status='approved', reviewer_id=who, approved_at=date or datetime.date.today().isoformat(),
                 evidence=list(evidence) + [e for e in p.get('evidence', []) if e not in evidence])
        if bian_release: r['bian_release'] = bian_release   # the BIAN release a BIAN-anchored link relies on (the person states it)
        if supersedes:
            old = next((m for m in reg['mappings'] if m['mapping_id'] == supersedes), None)
            if not old: raise ApproveError(f'{supersedes}: not in the registry')
            if old.get('status') != 'approved': raise ApproveError(f"{supersedes} is {old.get('status')}, not approved — only an approved link can be superseded")
            old['status'] = 'superseded'; r['previous_mapping_id'] = supersedes
        reg['mappings'].append(r); out.append(r)
    issues = validate(reg, load_registry(), load_schema(), metamodel=Metamodel.load())
    if issues:
        hint = '\n  → a link to a BIAN element needs the BIAN release it relies on: add --bian-release <release>' if any('requires bian_release' in i for i in issues) else ''
        raise ApproveError('the registry would not pass its checks — nothing was written:\n  ' + '\n  '.join(issues[:10]) + hint)
    return reg, out


def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem approve', formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description='A person approves proposed links into the registry: a correct record with the reviewer, the date and the required evidence, '
                                             'validated before it is written. The approval becomes final when the change is merged in a reviewed pull request. Agents never run this.',
                                 epilog='Examples (J3):\n  sdem approve P-RUN-001 --proposals work/links/proposals.json --estate work/est --reviewer jane.architect \\\n'
                                        '      --evidence application_architecture_document:AA-PAYHUB-HLD#s3\n'
                                        '  sdem approve P-RUN-001 --proposals … --estate … --reviewer … --evidence deployment_design:PAY-REHOST#cutover --supersedes PAY-108\n\n'
                                        'Evidence kinds per link type: .github/skills/sdem-approve-links/evidence-by-link-type.md')
    ap.add_argument('ids', nargs='+', metavar='PROPOSAL', help='proposal id(s) from `sdem review`')
    ap.add_argument('--proposals', required=True, metavar='FILE'); ap.add_argument('--estate', metavar='DIR', help='estate folder (its mappings.json)')
    ap.add_argument('--registry', metavar='FILE', help='the registry, if not <estate>/mappings.json')
    ap.add_argument('--reviewer', '--person', dest='reviewer', required=True, help='your name — a person (CTL-21); --person works too, as in the other commands')
    ap.add_argument('--evidence', action='append', default=[], metavar='KIND:REF', help='the document that proves the link (repeatable)')
    ap.add_argument('--supersedes', metavar='MAPPING_ID', help='the approved link this one replaces (it becomes superseded)')
    ap.add_argument('--id', dest='new_id', metavar='MAPPING_ID', help='the new link id (default: the next in the registry\'s style)')
    ap.add_argument('--bian-release', metavar='RELEASE', help='for a link to a BIAN element: the BIAN release it relies on (required by the registry rules)')
    ap.add_argument('--date', help='approval date (default today)'); ap.add_argument('--dry-run', action='store_true', help='show the record; write nothing')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    reg_path = Path(a.registry) if a.registry else Path(a.estate or '.') / 'mappings.json'
    if not a.registry and not a.estate: ap.error('give --estate DIR or --registry FILE')
    try:
        reg = json.loads(reg_path.read_text(encoding='utf-8')); props = json.loads(Path(a.proposals).read_text(encoding='utf-8'))
        new, recs = approve(reg, props, a.ids, a.reviewer, a.evidence, a.supersedes, a.new_id, a.date, a.bian_release)
    except (OSError, ValueError) as e:
        print(f'ERROR: {e}', file=sys.stderr); return 2
    except ApproveError as e:
        print(f'ERROR: {e}', file=sys.stderr); return 1
    if a.json: print(json.dumps(recs, indent=2, ensure_ascii=False))
    else:
        for r in recs:
            print(f"{'would approve' if a.dry_run else 'approved'} {r['mapping_id']}: {r['source']['id']} -{r['relationship']}-> {r['target']['id']}  "
                  f"(reviewer {r['reviewer_id']}, {r['approved_at']}, evidence {'; '.join(e for e in r['evidence'] if not e.startswith('engine_rationale:'))})" + (f"; supersedes {r['previous_mapping_id']}" if r.get('previous_mapping_id') else ''))
    if a.dry_run: return 0
    from .files import write_json
    write_json(reg_path, new)   # in one step: never a half-written registry
    if not a.json:
        print(f'{reg_path} updated and checked. Next: commit on a branch and open a pull request — the reviewed merge makes it final; then rebuild the graph store (sdem build --estate … --out …).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
