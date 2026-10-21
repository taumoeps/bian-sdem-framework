"""SDMM document diff: enforce lifecycle transitions and immutability between two versions.

A file validator only sees the current state. This compares a previous version of a
mapping document (a file, or a git revision) with the current one and reports:
  - records that were removed
  - status transitions that are not permitted
  - approved / superseded / rejected records whose frozen fields changed
"""
from pathlib import Path
import argparse, json, subprocess, sys
from sdmm.validate import split_evidence, normalize_type, load_registry

ALLOWED_TRANSITIONS = {
    'proposed':     {'validated', 'needs_review', 'rejected', 'approved'},
    'validated':    {'approved', 'needs_review', 'rejected'},
    'needs_review': {'validated', 'approved', 'rejected', 'proposed'},
    'approved':     {'superseded'},
    'rejected':     set(),
    'superseded':   set(),
}
FROZEN_STATUSES = {'approved', 'rejected', 'superseded'}
# Fields that may still change once a record is frozen.
THAWED_ON_SUPERSEDE = {'status', 'valid_to'}


def _frozen_view(field, value, registry):
    # Evidence may be re-typed ('kind:ref' added to an existing ref); the artefacts referenced may not change.
    if field == 'evidence' and isinstance(value, list):
        return frozenset(split_evidence(r)[1] for r in value if isinstance(r, str))
    # Endpoint types may be rewritten through a registry alias (L1. -> A2.); the entity referenced may not change.
    if field in ('source', 'target') and isinstance(value, dict):
        return {**value, 'type': normalize_type(value.get('type'), registry)}
    return value

EXIT_OK, EXIT_ISSUES, EXIT_USAGE = 0, 1, 2


def _by_id(payload):
    return {m['mapping_id']: m for m in payload.get('mappings', []) if isinstance(m, dict) and m.get('mapping_id')}


def diff(old, new, registry=None):
    """Return a list of issue strings describing illegal changes from `old` to `new`."""
    registry = registry or load_registry()
    issues = []
    before, after = _by_id(old), _by_id(new)
    for mid in sorted(set(before) - set(after)):
        issues.append(f'{mid}: record removed; mappings are never deleted, supersede them instead')
    for mid in sorted(set(before) & set(after)):
        a, b = before[mid], after[mid]
        sa, sb = a.get('status'), b.get('status')
        if sa != sb and sb not in ALLOWED_TRANSITIONS.get(sa, set()):
            issues.append(f'{mid}: status transition {sa!r} -> {sb!r} is not permitted')
        if sa in FROZEN_STATUSES:
            allowed = THAWED_ON_SUPERSEDE if (sa == 'approved' and sb == 'superseded') else set()
            changed = sorted(k for k in set(a) | set(b) if _frozen_view(k, a.get(k), registry) != _frozen_view(k, b.get(k), registry) and k not in allowed)
            if changed:
                issues.append(f'{mid}: {sa} record is immutable but field(s) changed: {changed}')
    return issues


def load_revision(path, rev):
    """Read `path` as it was at git revision `rev`. Returns None if it did not exist there."""
    try:
        out = subprocess.run(['git', 'show', f'{rev}:{path}'], capture_output=True, text=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return json.loads(out)


def main(argv=None):
    parser = argparse.ArgumentParser(prog='sdmm-diff', description='Check lifecycle and immutability between two versions of a mapping document.')
    parser.add_argument('new', nargs='+', help='current mapping document(s)')
    parser.add_argument('--old', help='previous version (file); use with a single document')
    parser.add_argument('--git', metavar='REV', help='compare each document against this git revision, e.g. HEAD~1')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    if bool(args.old) == bool(args.git) or (args.old and len(args.new) != 1):
        parser.error('give exactly one of --old <file> (with one document) or --git <rev>')
    report = {}
    for path in args.new:
        try:
            new = json.loads(Path(path).read_text(encoding='utf-8'))
            old = json.loads(Path(args.old).read_text(encoding='utf-8')) if args.old else load_revision(path, args.git)
        except (OSError, ValueError) as exc:
            print(f'ERROR: cannot read inputs for {path}: {exc}', file=sys.stderr)
            return EXIT_USAGE
        report[path] = [] if old is None else diff(old, new)  # no previous version: nothing to compare
    failed = any(report.values())
    if args.json:
        print(json.dumps({'ok': not failed, 'files': report}, indent=2))
    else:
        for path, issues in report.items():
            for issue in issues:
                print(f'ERROR: {path}: {issue}')
            if not issues:
                print(f'OK: {path}')
    return EXIT_ISSUES if failed else EXIT_OK


if __name__ == '__main__':
    raise SystemExit(main())
