"""`sdem migrate` — move an estate to the current rulebook (metamodel) version (docs/design/sdem-rulebook-versioning.md).

A dataset or registry carries the `metamodel_version` it was written for; SDEM refuses one that differs from the loaded
rulebook. `metamodel/migrations.json` records, for every rulebook change, the steps that carry data from the old version to
the new. `sdem migrate --estate DIR --person NAME` applies the chain from each file's version to the current one, checks
the whole estate as it would be, and only then writes it (all-or-nothing) with a record in `<estate>/migrations/`.

  sdem migrate --estate estates/history --person jane.architect [--dry-run] [--json]
"""
import argparse, copy, datetime, json, re, sys
from pathlib import Path

from .paths import DATA_ROOT

DATASETS = ('a1-business.json', 'a2-service-domain.json', 'a3-application.json', 'a4-technology.json')
RECORD = DATA_ROOT / 'metamodel' / 'migrations.json'


class MigrateError(Exception):
    """The estate cannot be migrated (no path, or it would fail its checks) — exit 1."""


def _j(p): return json.loads(Path(p).read_text(encoding='utf-8'))


def chain(start, current, migrations):
    """The migrations from `start` to `current`, in order — or None when there is no path."""
    by_from = {m['from']: m for m in migrations}
    out, v, seen = [], start, set()
    while v != current:
        if v in seen or v not in by_from: return None
        seen.add(v); m = by_from[v]; out.append(m); v = m['to']
    return out


def _apply_dataset(doc, steps, counts):
    for st in steps:
        kind = st['step']
        for i in doc.get('instances', []):
            at = i.get('attributes') or {}
            if kind == 'rename_type' and i['type'] == st['from']: i['type'] = st['to']; counts[kind] += 1
            elif kind == 'rename_attribute' and st['from'] in at and st.get('type') in (None, i['type']):
                at[st['to']] = at.pop(st['from']); counts[kind] += 1
            elif kind == 'drop_attribute' and st['name'] in at and st.get('type') in (None, i['type']):
                at.pop(st['name']); counts[kind] += 1
            elif kind == 'set_attribute' and i['type'] == st['type'] and st['name'] not in at:
                i.setdefault('attributes', {})[st['name']] = st['value']; counts[kind] += 1
        if kind == 'rename_kind':
            for r in doc.get('relationships', []):
                if r['kind'] == st['from']: r['kind'] = st['to']; counts[kind] += 1


def _apply_registry(doc, steps, counts):
    for st in steps:
        if st['step'] == 'rename_relationship':
            for m in doc.get('mappings', []):
                if m.get('relationship') == st['from']: m['relationship'] = st['to']; counts['rename_relationship'] += 1
        if st['step'] == 'rename_type':
            for m in doc.get('mappings', []):
                for end in ('source', 'target'):
                    if m.get(end, {}).get('type') == st['from']: m[end]['type'] = st['to']; counts['rename_type (registry)'] += 1


def migrate(estate, person, dry_run=False, migrations=None, now=None):
    """Plan, check and (unless dry_run) write the migration. Returns the result; raises MigrateError when refused."""
    import collections
    from .validate import is_person
    from .metamodel import Metamodel
    from .graph import FederatedGraph, LevelGraph
    if not is_person(person): raise ValueError(f"--person {person!r}: migrating an estate is a person's decision — give your own name")
    estate = Path(estate)
    files = [estate / f for f in DATASETS if (estate / f).exists()]
    if not (estate / 'mappings.json').exists() or not files:
        raise ValueError(f'{estate}: not an estate folder (it needs mappings.json and at least one of {", ".join(DATASETS)})')
    mm = Metamodel.load(); current = mm.version
    rec = migrations if migrations is not None else _j(RECORD)
    docs = {p: _j(p) for p in files + [estate / 'mappings.json']}
    plan, counts = [], collections.Counter()
    out = {}
    for p, d in docs.items():
        v = d.get('metamodel_version') or current
        if v == current: out[p] = d; continue
        steps = chain(v, current, rec['migrations'])
        if steps is None:
            raise MigrateError(f'{p.name}: no migration path from metamodel {v} to {current} — the rulebook changed without a recorded migration (metamodel/migrations.json)')
        nd = copy.deepcopy(d)
        for m in steps:
            (_apply_registry if p.name == 'mappings.json' else _apply_dataset)(nd, m.get('steps', []), counts)
        nd['metamodel_version'] = current
        out[p] = nd; plan.append({'file': p.name, 'from': v, 'to': current, 'migrations': [f"{m['from']} → {m['to']}" for m in steps]})
    res = {'estate': str(estate), 'current': current, 'files': plan, 'changes': dict(counts), 'dry_run': dry_run}
    if not plan:
        res['note'] = f'already at metamodel {current} — nothing to do'; return res
    levels = [LevelGraph(d, mm) for p, d in out.items() if p.name != 'mappings.json']
    report = FederatedGraph(levels, [out[estate / 'mappings.json']], mm).check()
    errors = [f'{k}: {i}' for k, v in report.items() for i in v]
    if errors: raise MigrateError('the estate would not pass its checks after migrating — nothing written:\n  ' + '\n  '.join(errors[:20]))
    if dry_run: return res
    from .files import Batch
    b = Batch()
    for p, d in out.items():
        if any(x['file'] == p.name for x in plan): b.json(p, d)
    mig = estate / 'migrations'
    n = 1 + max([int(m.group(1)) for f in (mig.glob('MIG-*.json') if mig.exists() else []) for m in [re.match(r'MIG-(\d+)\.json$', f.name)] if m] or [0])
    res['id'] = f'MIG-{n:03d}'
    b.json(mig / f"{res['id']}.json", {'id': res['id'], 'at': now or datetime.datetime.now().replace(microsecond=0).isoformat(), 'person': person, **{k: res[k] for k in ('current', 'files', 'changes')}})
    b.commit()
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem migrate', description='Move an estate to the current rulebook (metamodel) version — the recorded migrations applied, the estate checked, then written all-or-nothing and recorded.')
    ap.add_argument('--estate', required=True, metavar='DIR'); ap.add_argument('--person', required=True, help='your name — a person')
    ap.add_argument('--dry-run', action='store_true', help='check and show what would change; write nothing'); ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    try: res = migrate(a.estate, a.person, a.dry_run)
    except MigrateError as e:
        print(f'ERROR: {e}', file=sys.stderr); return 1
    if a.json: print(json.dumps(res, indent=2)); return 0
    if res.get('note'): print(res['note']); return 0
    for f in res['files']: print(f"{f['file']}: metamodel {f['from']} → {f['to']} ({', '.join(f['migrations'])})")
    print('changes: ' + (', '.join(f'{k} {v}' for k, v in res['changes'].items()) or 'version only'))
    print('would migrate (dry run) — the estate passes its checks' if a.dry_run else f"migrated ({res['id']}); the estate passes its checks. Commit it on a branch and open a pull request.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
