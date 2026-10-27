"""`sdem load` — the L of the ETL for past designs: put the candidate entities `sdem transform run` produced, after an
architect has reviewed them, into an SDEM estate — selected, checked before anything is written, recorded
(docs/sdem-load-design.md; spec LD-*).

  sdem load work/history --estate estates/history --person jane.architect --exclude HIS-A3-X [--a2 FILE] [--dry-run]

Links between architectures are not loaded: `sdem link` proposes them from the loaded data and a person approves them.
Unreviewed candidates never enter a knowledge graph: `sdem build` refuses them (CTL-23); this is the only way in.
"""
import argparse, copy, datetime, json, re, sys
from pathlib import Path

from .graph import FederatedGraph, LevelGraph
from .metamodel import Metamodel
from .transform import DATASETS, SOURCE_SYSTEM
from .validate import NON_PERSON_REVIEWERS

LOADED_SYSTEM = 'SDEM-LOAD'
EMPTY_REGISTRY = {'registry_version': '0.4.0', 'metamodel_version': '0.4.0', 'mappings': []}


class LoadError(Exception):
    pass


def _j(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def read_candidates(src):
    """The transform output: its extraction.json and candidate datasets. Anything else is refused (LD-G02)."""
    src = Path(src)
    if not (src / 'extraction.json').exists():
        raise LoadError(f'{src}: not a transform output (no extraction.json) — run `sdem transform run` first')
    meta, ds = _j(src / 'extraction.json'), {}
    for lvl, name in DATASETS.items():
        if (src / name).exists():
            d = _j(src / name)
            if d.get('source_system') != SOURCE_SYSTEM:
                raise LoadError(f"{src / name}: not a transform candidate dataset (source_system {d.get('source_system')!r})")
            ds[lvl] = d
    if not ds: raise LoadError(f'{src}: no candidate datasets to load')
    return meta, ds


def check_person(person):
    p = (person or '').strip().lower()
    if not p or p.startswith('sdem-') or p in NON_PERSON_REVIEWERS:
        raise LoadError(f'--person {person!r}: loading is a person\'s decision — give your own name, never an agent or tool (as CTL-21)')


def select(ds, all_=False, only=None, exclude=None):
    """Which candidates to load: exactly one of everything, only these, all but these (LD-S01)."""
    ids = {i['id'] for d in ds.values() for i in d['instances']}
    if sum(1 for x in (all_, only, exclude) if x) != 1:
        raise LoadError('choose what to load — one of --all, --only ID …, --exclude ID … or --keep FILE')
    unknown = sorted(set(only or exclude or []) - ids)
    if unknown: raise LoadError(f"not among the candidates: {', '.join(unknown)}")
    keep = set(ids) if all_ else set(only) if only else ids - set(exclude)
    return keep, sorted(ids - keep)


def keep_file(path):
    """Ids from a file: one per line (or whitespace-separated); '#' starts a comment."""
    return [t for line in Path(path).read_text(encoding='utf-8').splitlines() for t in line.split('#', 1)[0].split()]


def plan(estate, ds, keep, a2=None, mm=None, today=None):
    """The estate as it would be after the load, and what changes — nothing is written here."""
    estate = Path(estate); mm = mm or Metamodel.load(); today = today or datetime.date.today().isoformat()
    current = {lvl: _j(estate / f) for lvl, f in DATASETS.items() if (estate / f).exists()}
    existing_ids = {i['id'] for d in current.values() for i in d['instances']}
    allowed = existing_ids | keep
    after, changed = dict(current), {}
    res = {'loaded': {}, 'links': 0, 'skipped_same': [], 'conflicts': [], 'dropped': [], 'a2_added': None, 'notes': []}
    for lvl, d in sorted(ds.items()):
        base = copy.deepcopy(current.get(lvl)) or {'level': lvl, 'model_id': f"{re.sub(r'[^A-Z0-9]+', '-', estate.name.upper()).strip('-') or 'ESTATE'}-{lvl}",
                                                   'model_version': today, 'metamodel_version': mm.version, 'source_system': LOADED_SYSTEM,
                                                   'instances': [], 'relationships': []}
        have = {i['id']: i for i in base['instances']}
        new_i, new_r = [], []
        for i in d['instances']:
            if i['id'] not in keep: continue
            i = copy.deepcopy(i); at = i.get('attributes') or {}
            if at.get('deployed_on'):  # a deployment reference to an entity not loaded is dropped (LD-S02)
                gone = [x for x in at['deployed_on'] if x not in allowed]
                if gone: res['dropped'].append(f"{i['id']}.deployed_on → {', '.join(gone)} (not loaded)")
                at['deployed_on'] = [x for x in at['deployed_on'] if x in allowed]
                if not at['deployed_on']: del at['deployed_on']
            if i['id'] in have:
                if have[i['id']] == i: res['skipped_same'].append(i['id'])
                else: res['conflicts'].append(i['id'])
                continue
            new_i.append(i)
        rels = {(r['source'], r['kind'], r['target']) for r in base.get('relationships', [])}
        for r in d.get('relationships', []):
            if r['source'] in allowed and r['target'] in allowed:
                if (r['source'], r['kind'], r['target']) not in rels: new_r.append(copy.deepcopy(r))
            elif r['source'] in keep or r['target'] in keep:
                res['dropped'].append(f"link {r['source']} -{r['kind']}-> {r['target']} (an end not loaded)")
        if new_i or new_r:
            base['instances'] += new_i; base.setdefault('relationships', []).extend(new_r); base['model_version'] = today
            after[lvl] = changed[lvl] = base
        res['loaded'][lvl] = [i['id'] for i in new_i]; res['links'] += len(new_r)
    if a2:
        d = _j(a2)
        if d.get('level') != 'A2': raise LoadError(f'--a2 {a2}: not an A2 dataset')
        if 'A2' in current: res['notes'].append('the estate already has an A2 dataset — kept, --a2 not used')
        else: after['A2'] = changed['A2'] = d; res['a2_added'] = str(a2)
    registry = _j(estate / 'mappings.json') if (estate / 'mappings.json').exists() else copy.deepcopy(EMPTY_REGISTRY)
    fg = FederatedGraph([LevelGraph(d, mm) for d in after.values()], [registry], mm)
    report = fg.check()
    res['errors'] = [f'{k}: {i}' for k, v in report.items() for i in v]
    res['errors'] += [f'{c}: already in the estate with different content — exclude it, rename it, or change the estate first' for c in res['conflicts']]
    res['warnings'] = sum(len(v) for v in getattr(fg, 'warnings', {}).values())
    return after, changed, registry, res


def load(src, estate, person, keep=None, exclude=None, all_=False, a2=None, dry_run=False, now=None):
    """Select, check, write, record. Returns the result; raises LoadError when refused (nothing written)."""
    check_person(person)
    meta, ds = read_candidates(src)
    keep_ids, excluded = select(ds, all_, keep, exclude)
    mm = Metamodel.load(); now = now or datetime.datetime.now().replace(microsecond=0).isoformat()
    after, changed, registry, res = plan(estate, ds, keep_ids, a2, mm, now[:10])
    res.update({'excluded': excluded, 'estate': str(estate), 'dry_run': dry_run,
                'bian_mentions': meta.get('bian_mentions', []), 'transform': {k: meta.get(k) for k in ('generated', 'export', 'export_sha256', 'rules_sha256')}})
    if res['errors']:
        raise LoadError('refused — nothing written:\n  ' + '\n  '.join(res['errors'][:30]))
    if dry_run: return res
    estate = Path(estate); estate.mkdir(parents=True, exist_ok=True)
    for lvl, d in changed.items():
        (estate / DATASETS[lvl]).write_text(json.dumps(d, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    if not (estate / 'mappings.json').exists():
        (estate / 'mappings.json').write_text(json.dumps(registry, indent=2) + '\n', encoding='utf-8')
    loads = estate / 'loads'; loads.mkdir(exist_ok=True)
    n = 1 + max([int(m.group(1)) for p in loads.glob('LOAD-*.json') for m in [re.match(r'LOAD-(\d+)\.json$', p.name)] if m] or [0])
    res['load_id'] = f'LOAD-{n:03d}'
    record = {'id': res['load_id'], 'at': now, 'person': person, 'from': str(src), 'transform': res['transform'], 'loaded': res['loaded'],
              'links_loaded': res['links'], 'skipped_same_content': res['skipped_same'], 'excluded': excluded, 'dropped': res['dropped'],
              'a2_added': res['a2_added'], 'check': {'errors': 0, 'warnings': res['warnings']}}
    (loads / f"{res['load_id']}.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem load', description='Load reviewed candidate entities from `sdem transform run` into an estate — selected, checked first, recorded (the L of the ETL).')
    ap.add_argument('candidates', help='the folder `sdem transform run` wrote')
    ap.add_argument('--estate', required=True, help='the estate to load into (created if missing); for past designs a separate historical estate is recommended')
    ap.add_argument('--person', required=True, help='who reviewed and loads — a person, never an agent')
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--all', action='store_true', help='load every candidate')
    g.add_argument('--only', nargs='+', metavar='ID', help='load only these')
    g.add_argument('--exclude', nargs='+', metavar='ID', help='load all but these')
    g.add_argument('--keep', metavar='FILE', help='load the ids listed in a file (one per line, # comments)')
    ap.add_argument('--a2', metavar='FILE', help="your organisation's A2 dataset (BIAN catalogue), added if the estate has none")
    ap.add_argument('--dry-run', action='store_true', help='check and show what would be loaded; write nothing')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    try:
        res = load(a.candidates, a.estate, a.person, keep_file(a.keep) if a.keep else a.only, a.exclude, a.all, a.a2, a.dry_run)
    except LoadError as e:
        print(f'ERROR: {e}', file=sys.stderr); return 1
    except (OSError, ValueError) as e:
        print(f'ERROR: {e}', file=sys.stderr); return 2
    if a.json: print(json.dumps(res, indent=2, ensure_ascii=False)); return 0
    n = {l: len(v) for l, v in res['loaded'].items()}
    print(('would load' if a.dry_run else f"loaded ({res['load_id']})") + f" into {a.estate}: " + ', '.join(f'{l} {v} entities' for l, v in sorted(n.items()))
          + f", {res['links']} links inside architectures" + (f"; A2 dataset added from {res['a2_added']}" if res['a2_added'] else ''))
    if res['excluded']: print(f"excluded ({len(res['excluded'])}): " + ', '.join(res['excluded']))
    if res['skipped_same']: print(f"already in the estate, same content ({len(res['skipped_same'])}): " + ', '.join(res['skipped_same']))
    for d in res['dropped']: print(f'dropped: {d}')
    for t in res['notes']: print(f'NOTE: {t}')
    if res['bian_mentions']:
        print('BIAN elements named in the designs — hints for sdem link (never loaded as entities, CTL-17):')
        for m in res['bian_mentions'][:20]: print(f"  {m['name']}" + (f" (= {m['existing_id']})" if m.get('existing_id') else '') + f" — {m['page_title']}")
    if not a.dry_run:
        print(f"next: sdem check --estate {a.estate}  ·  sdem link --estate {a.estate} --out work/links  ·  sdem review work/links/proposals.json  ·  "
              f"sdem approve …  ·  sdem build --estate {a.estate} --out work/graph")
    return 0


if __name__ == '__main__':
    sys.exit(main())
