"""`sdem new` — start a workspace: the folder where one area's architecture is kept (docs/design/sdem-workspace-spec.md, WS-*).

It creates the four layer datasets — all empty — and an empty registry of connections, checks the workspace, and records who
started it and which **BIAN catalogue** it uses (workspace.json): your organisation's shared BIAN layer (bian/a2-service-domain.json)
when there is one, otherwise the base BIAN that ships with SDEM. The catalogue is read, never copied: `sdem aid` brings into the
workspace's A2 layer only the service domains its design needs, and `sdem bian add` adds one by hand (WS-01).
`--bian FILE` starts instead with exactly that BIAN layer in A2.

  sdem new --workspace workspaces/payments --person jane.architect

An **organisation** (WS-08…WS-10) is the folder above its workspaces: `sdem new --organisation bank-xyz --person P` starts it with a
starter base profile (`profiles/bank-xyz-base.json`) and `workspaces/`; a workspace started in it gets its own profile, which extends
that base, so the organisation's types, attributes and rules apply from the start.

  sdem new --organisation bank-xyz --person jane.architect
  sdem new --workspace workspaces/ledger --organisation bank-xyz --person jane.architect
"""
import argparse, datetime, json, re, sys
from pathlib import Path

from .layers import FILES as DATASETS   # LR-03
SHARED = Path('bian') / 'a2-service-domain.json'
RECORD = 'workspace.json'
FORMAT = 'sdem-workspace/1'
SYSTEM = 'SDEM-NEW'


class NewError(ValueError):
    """The request cannot be done (exit 2)."""


def base_layer():
    """Every service domain of the base BIAN, accepted inferences applied — as `sdem bian import --base --all`."""
    from . import bian
    from .inferences import installed_file, read, accepted
    from .metamodel import Metamodel
    domains = bian.read_pack(bian.base_file())
    f = installed_file(max((d['release'] for d in domains), default=''))
    dataset, _ = bian.build(domains, Metamodel.load().version, patterns=None, inferences=accepted(read(f)) if f else {})
    return dataset, f"the base BIAN {dataset['model_version']} that ships with SDEM — all {len(domains)} service domains"


EXAMPLES = {'payment-initiation': 'payment_initiation'}   # synthetic examples that ship with SDEM (made-up data)


def example_dir(name):
    """A bundled example's folder: examples/<name> in a checkout, sdem/data/examples/<package> when installed."""
    from .paths import CHECKOUT, DATA_ROOT
    d = DATA_ROOT / 'examples' / (name if CHECKOUT else EXAMPLES[name])
    if not (d / 'a1-business.json').exists(): raise NewError(f'the example {name} is not installed with this SDEM — reinstall it')
    return d


def profile_copy(src, ws):
    """A profile file as the workspace will keep it (sdem-profile.json): its `extends` re-pointed from the workspace, so the base it
    names is still found (LR-03)."""
    import os
    src = Path(src); doc = json.loads(src.read_text(encoding='utf-8'))
    if doc.get('extends'):
        base = (src.parent / doc['extends']).resolve()
        try: doc['extends'] = Path(os.path.relpath(base, Path(ws).resolve())).as_posix()
        except ValueError: doc['extends'] = base.as_posix()   # another drive (Windows): an absolute path
    return doc


ORG_RECORD = 'sdem-organisation.json'
ORG_FORMAT = 'sdem-organisation/1'


def org_files(name, person, today=None):
    """WS-08: the files of a new organisation — its record and a starter base profile that passes `sdem profile check`."""
    from .profile import FORMAT as PFORMAT
    today = today or datetime.date.today().isoformat()
    base = f'profiles/{name}-base.json'
    rec = {'format': ORG_FORMAT, 'name': name, 'created': today, 'created_by': person.strip(), 'base_profile': base, 'workspaces': 'workspaces'}
    prof = {'format': PFORMAT, 'name': f'{name}-base', 'version': 1,
            'description': f"{name}'s design specification on top of SDEM's metamodel — every workspace's profile extends it. Add the "
                           "organisation's types, attributes, rules, link kinds and names here, and its standards and patterns under includes; "
                           f"check with: sdem profile check --file {base}",
            'types': [], 'attributes': [], 'rules': []}
    return {ORG_RECORD: rec, base: prof}


def _org_at(folder):
    """The organisation record in `folder`, or None."""
    f = Path(folder) / ORG_RECORD
    if not f.is_file(): return None
    try: rec = json.loads(f.read_text(encoding='utf-8'))
    except ValueError: return None
    return rec if rec.get('format') == ORG_FORMAT else None


def find_org(start):
    """WS-09: the nearest organisation folder at `start` or above it, or None."""
    p = Path(start).resolve()
    for d in [p, *p.parents]:
        if _org_at(d): return d
    return None


def resolve_org(name_or_dir):
    """WS-09: `--organisation` as a folder (bank-xyz, ../bank-xyz), or the name of the organisation the current folder is in."""
    p = Path(name_or_dir)
    if _org_at(p): return p
    here = find_org(Path.cwd())
    if here and _org_at(here)['name'] == p.name: return here
    raise NewError(f"--organisation {name_or_dir}: no such organisation — start it with: sdem new --organisation {name_or_dir} --person <you>")


def org_workspace(org, workspace):
    """WS-09: the workspace's folder inside the organisation — a relative path is from the organisation's folder; one outside it is refused."""
    import os
    ws = Path(workspace) if Path(workspace).is_absolute() else Path(org) / workspace
    root, full = Path(org).resolve(), ws.resolve()
    if full == root or root not in full.parents:
        raise NewError(f'--workspace {workspace}: not inside the organisation {_org_at(org)["name"]} ({Path(org).as_posix()}) — a workspace of an organisation is a folder inside it, e.g. workspaces/<name>')
    try: return Path(os.path.relpath(full, Path.cwd()))
    except ValueError: return full   # another drive (Windows)


def org_profile(org, ws):
    """WS-10: a new workspace's own profile in an organisation — it extends the organisation's base profile and adds nothing yet."""
    import os
    rec = _org_at(org); base = (Path(org) / rec['base_profile']).resolve()
    if not base.is_file(): raise NewError(f"the organisation {rec['name']}'s base profile {rec['base_profile']} is missing — restore it, or give --profile FILE")
    try: ext = Path(os.path.relpath(base, Path(ws).resolve())).as_posix()
    except ValueError: ext = base.as_posix()
    from .profile import FORMAT as PFORMAT
    return {'format': PFORMAT, 'name': f"{rec['name']}-{Path(ws).name}", 'version': 1, 'extends': ext,
            'description': f"The {Path(ws).name} workspace's additions to {rec['name']}'s base profile — add its own types, attributes and rules here"}


def plan(workspace, person, bian_file=None, today=None, no_bian=False, from_dir=None, label=None, profile_file=None, profile_doc=None, org=None):
    """The files of a new workspace and its record — nothing written here (WS-01, WS-02)."""
    from .connect import estate_errors
    from .load import EMPTY_REGISTRY
    from .metamodel import Metamodel
    from .validate import is_person
    ws = Path(workspace); today = today or datetime.date.today().isoformat()
    if not is_person(person): raise NewError(f"--person {person!r}: starting a workspace is a person's decision — give your own name (CTL-21)")
    if ws.exists() and any(ws.iterdir()): raise NewError(f'{ws}: already exists and is not empty — a workspace is started once; load into it with `sdem load`')
    mm = Metamodel.load()
    shared = Path(bian_file) if bian_file else SHARED
    if bian_file and not shared.exists(): raise NewError(f'--bian {bian_file}: not found')
    stem = re.sub(r'[^A-Z0-9]+', '-', ws.name.upper()).strip('-') or 'WORKSPACE'
    if no_bian:
        a2, catalogue = None, None
        source = 'none — business does not connect to applications until a BIAN layer is added (sdem bian add)'
    elif bian_file:   # started with exactly this BIAN layer
        a2 = json.loads(shared.read_text(encoding='utf-8'))
        if a2.get('level') != 'A2': raise NewError(f'{shared}: not an A2 dataset (level {a2.get("level")!r})')
        source, catalogue = f'the BIAN layer {shared.as_posix()}', shared.as_posix()   # recorded with / on every platform
    else:             # WS-01: the catalogue is read, not copied; A2 holds only the domains the design needs
        a2 = {'level': 'A2', 'model_id': f'{stem}-A2', 'model_version': today, 'metamodel_version': mm.version, 'source_system': SYSTEM,
              'instances': [], 'relationships': []}
        catalogue = SHARED.as_posix() if SHARED.exists() else 'base'
        source = 'sdem aid brings in the service domains your design needs, from ' + (f'your shared BIAN layer {SHARED}' if SHARED.exists() else 'the base BIAN that ships with SDEM')
    docs = {f: ({'level': lvl, 'model_id': f'{stem}-{lvl}', 'model_version': today, 'metamodel_version': mm.version, 'source_system': SYSTEM,
                 'instances': [], 'relationships': []} if lvl != 'A2' else a2) for lvl, f in DATASETS.items() if lvl != 'A2' or a2}
    registry = {**EMPTY_REGISTRY, 'metamodel_version': mm.version}
    extra = {}
    if from_dir:   # GV-05: the workspace's first content — a baseline, checked like any other, and recorded as one
        src = Path(from_dir)
        if not src.is_dir(): raise NewError(f'--from {from_dir}: no such folder')
        found = {f: json.loads((src / f).read_text(encoding='utf-8')) for f in DATASETS.values() if (src / f).exists()}
        if not found: raise NewError(f'--from {from_dir}: no architecture datasets ({", ".join(DATASETS.values())})')
        docs.update(found)
        if (src / 'mappings.json').exists(): registry = json.loads((src / 'mappings.json').read_text(encoding='utf-8'))
        if (src / 'requirements.json').exists(): extra['requirements.json'] = json.loads((src / 'requirements.json').read_text(encoding='utf-8'))
        if a2 is not None and 'a2-service-domain.json' in found: catalogue, source = 'base', f'the BIAN layer of the baseline ({label or src.as_posix()})'
    errors = estate_errors(docs, registry)
    if extra.get('requirements.json'):
        from .requirements import check as rcheck
        errors += [f'requirements.json: {x}' for x in rcheck(extra['requirements.json'], {d['level']: d for d in docs.values()})]
    if errors: raise NewError('the new workspace would not pass its checks — nothing written:\n  ' + '\n  '.join(errors[:10]))
    sds = sum(1 for i in (a2 or {}).get('instances', []) if i['type'] == 'A2.ServiceDomain')
    record = {'format': FORMAT, 'name': ws.name, 'created': today, 'created_by': person.strip(),
              'bian': {'catalogue': catalogue, 'source': source, 'selection': 'none' if no_bian else 'given' if bian_file else 'relevant',
                       'service_domains': sds}}
    if from_dir: record['baseline'] = {'from': label or Path(from_dir).as_posix(), 'files': sorted(list(docs) + ['mappings.json'] + list(extra))}
    if profile_file:   # PR-07, LR-03: the baseline's profile, or the one given with --profile; its layers' files are among docs
        from . import profile as _p
        extra['sdem-profile.json'] = profile_copy(profile_file, ws)
        record['profile'] = {'file': 'sdem-profile.json', 'from': 'baseline' if from_dir and Path(profile_file).resolve() == (Path(from_dir) / 'sdem-profile.json').resolve() else Path(profile_file).as_posix(),
                             **(_p.record() or {})}
    elif profile_doc:  # WS-10: the organisation's base, through the workspace's own profile
        from . import profile as _p
        extra['sdem-profile.json'] = profile_doc
        record['profile'] = {'file': 'sdem-profile.json', 'from': 'organisation', **(_p.record() or {})}
    if org is not None:
        import os
        o = _org_at(org)
        try: rel = Path(os.path.relpath(Path(org).resolve(), ws.resolve())).as_posix()
        except ValueError: rel = Path(org).resolve().as_posix()
        record['organisation'] = {'name': o['name'], 'folder': rel, 'base_profile': o['base_profile']}
    return docs, registry, record, extra


def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem new', formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description='Start a workspace — the folder where one area\'s architecture is kept: the four layers (A2 your BIAN layer) '
                                             'and the approved connections between them. Checked before anything is written.',
                                 epilog='Examples:\n  sdem new --organisation bank-xyz --person jane.architect                                  # once per organisation\n'
                                        '  sdem new --workspace workspaces/ledger --organisation bank-xyz --person jane.architect    # each workspace\n'
                                        '  sdem new --workspace workspaces/payments --person jane.architect                         # a workspace on its own\n\n'
                                        'Next: existing designs — sdem transform run … then sdem load work/history --workspace workspaces/payments --person <you>; '
                                        'a new design — sdem aid project --workspace workspaces/payments --out workspaces/payments/plans/<name>.')
    ap.add_argument('--workspace', dest='estate', metavar='DIR', help='the folder to start, e.g. workspaces/payments — inside an organisation, a path from its folder')
    ap.add_argument('--organisation', metavar='NAME', help='alone: start an organisation — the folder NAME with a starter base profile (profiles/NAME-base.json) and workspaces/ (WS-08); '
                    'with --workspace: start the workspace inside that organisation, its profile extending the base (WS-09, WS-10). Inside an organisation\'s folder it is found without this')
    ap.add_argument('--person', required=True, help='your name — a person')
    ap.add_argument('--bian', metavar='FILE', help=f'start with exactly this BIAN layer in A2 (default: A2 empty; sdem aid brings in the domains your design needs from {SHARED.as_posix()} if it exists, else the base BIAN)')
    ap.add_argument('--no-bian', action='store_true', help='start without a BIAN layer (add it later); business then does not connect to applications')
    ap.add_argument('--example', choices=sorted(EXAMPLES), help='start with a synthetic example that ships with SDEM as the baseline (made-up data, for learning) — the same as --from its folder')
    ap.add_argument('--from', dest='source', metavar='DIR', help='start with this content as the baseline: the four layers, mappings.json and requirements.json found in DIR — checked first, '
                    'recorded in the ledger and as a decision; only when the workspace is created (a baseline is never re-taken)')
    ap.add_argument('--profile', metavar='FILE', help="start with this organisation profile (kept as sdem-profile.json; its base is still found): its types, rules and names apply, "
                    'and the layers it adds above A1 or below A4 start empty beside the core four')
    ap.add_argument('--explore', action='store_true', help='also build the knowledge graph and write the pages to explore it — the graph page, the workspace dashboard '
                    'and SDEM Home (work/sdem/index.html) — in one step; derived outputs only, the workspace is not changed (EX-01)')
    ap.add_argument('--dry-run', action='store_true'); ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    from . import profile as _p
    if not a.estate:
        if not a.organisation: ap.error('give --workspace DIR (a workspace) or --organisation NAME (an organisation)')
        return new_org(a)
    try:
        org = resolve_org(a.organisation) if a.organisation else find_org(Path(a.estate).parent)
        if org is not None and a.organisation: a.estate = str(org_workspace(org, a.estate))
        if a.no_bian and a.bian: raise NewError('give --bian or --no-bian, not both')
        if a.example and a.source: raise NewError('give --example or --from, not both')
        if a.example: a.source = str(example_dir(a.example))
        pf = a.profile or (str(Path(a.source) / 'sdem-profile.json') if a.source and (Path(a.source) / 'sdem-profile.json').exists() else None)
        pdoc = org_profile(org, a.estate) if org is not None and not pf else None
        if pf: _p.activate_file(pf)
        elif pdoc:   # WS-10: checked as it will be kept — a temporary copy whose extends points at the base
            import tempfile
            with tempfile.TemporaryDirectory() as t:
                tf = Path(t) / 'sdem-profile.json'
                tf.write_text(json.dumps({**pdoc, 'extends': (Path(org) / _org_at(org)['base_profile']).resolve().as_posix()}), encoding='utf-8')
                _p.activate_file(tf)
        else: _p.deactivate()
        docs, registry, record, extra = plan(a.estate, a.person, a.bian, no_bian=a.no_bian, from_dir=a.source, label=f'the synthetic example {a.example}' if a.example else None,
                                             profile_file=pf, profile_doc=pdoc, org=org)
    except _p.ProfileError as e:
        print(f'ERROR: {e}', file=sys.stderr); return 2
    except NewError as e:
        print(f'ERROR: {e}', file=sys.stderr); return 2
    if a.json:
        if not (a.explore and not a.dry_run): print(json.dumps(record, indent=2))   # with --explore, one document at the end
    else:
        b_ = record['bian']
        if record.get('organisation'):
            pr = record.get('profile') or {}
            print(f"organisation {record['organisation']['name']} — profile {' → '.join(pr.get('chain') or []) or 'none'}"
                  + (f" v{pr['version']}" if pr.get('version') is not None else '') + (f" (from {pr['from']})" if pr.get('from') not in (None, 'organisation') else ''))
        if a.source:
            n = {d['level']: len(d['instances']) for d in docs.values()}
            print(f"{'would start' if a.dry_run else 'started'} {a.estate} from the baseline {record['baseline']['from']}: "
                  + ', '.join(f'{k} {v} record(s)' for k, v in sorted(n.items())) + f", {len(registry.get('mappings', []))} connection(s)"
                  + (f", {len(extra['requirements.json']['requirements'])} requirement(s)" if 'requirements.json' in extra else '') + ' — checked')
        else:
            print(f"{'would start' if a.dry_run else 'started'} {a.estate}: "
                  + (f"A1, A3, A4 empty; A2 {b_['service_domains']} service domains from {b_['source']}" if a.bian else f"all {len(docs)} layers empty; BIAN: {b_['source']}")
                  + (f"; profile {record['profile']['name']} ({', '.join(d['level'] for d in docs.values() if d['level'] not in ('A1', 'A2', 'A3', 'A4')) or 'no extra layers'})" if record.get('profile') else '')
                  + '; no connections yet — checked')
    if a.dry_run: return 0
    from .files import Batch
    ws = Path(a.estate); b = Batch()
    for f, d in docs.items(): b.json(ws / f, d)
    for f, d in extra.items(): b.json(ws / f, d)
    b.json(ws / 'mappings.json', registry); b.json(ws / RECORD, record); b.commit()
    if a.source:   # GV-05: the ledger records the baseline as such, and the decision is on record (attributed)
        from .files import record as led, TRACKED
        from .governance import record as gd
        src = record['baseline']['from']
        g = gd(a.estate, 'establish_baseline', a.person, ws.name, {'from': src, 'files': record['baseline']['files']})
        led([ws / f for f in TRACKED if (ws / f).exists()], by=f'sdem new (baseline from {src}, {g["id"]})')
    if a.explore: return explore(a.estate, a.json, record=record)
    if not a.json and a.source:
        print(f'Next — sdem build --workspace {a.estate} --out {a.estate}/graph, then sdem trace <id or A1…A4> --graph {a.estate}/graph, '
              f'sdem impact <id> --change rehost --graph {a.estate}/graph, sdem requirements evaluate --workspace {a.estate} --record <id> --change <kind>')
    elif not a.json:
        print(f'Next — write what you have (any of a1…a4), or load existing designs (sdem load work/history --workspace {a.estate} --person <you>); '
              f'then sdem aid --workspace {a.estate} --person <you> fills the gaps, including the BIAN service domains your design needs')
    return 0


def new_org(a):
    """WS-08: start an organisation — its folder, record, starter base profile (checked) and workspaces/. A person's decision."""
    from .validate import is_person
    from . import profile as _p
    try:
        if any((a.bian, a.no_bian, a.example, a.source, a.profile, a.explore)): raise NewError('--organisation alone starts an organisation; --bian, --no-bian, --example, --from, --profile and --explore are for a workspace (add --workspace)')
        if not is_person(a.person): raise NewError(f"--person {a.person!r}: starting an organisation is a person's decision — give your own name (CTL-21)")
        root = Path(a.organisation); name = root.name
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', name): raise NewError(f'--organisation {a.organisation}: a name of letters, digits, ".", "_" and "-", e.g. bank-xyz')
        if root.exists() and (not root.is_dir() or any(root.iterdir())): raise NewError(f'{root}: already exists and is not empty — an organisation is started once')
        if find_org(root.resolve().parent): raise NewError(f'{root}: inside the organisation {_org_at(find_org(root.resolve().parent))["name"]} — an organisation is not started inside another')
        files = org_files(name, a.person)
        import tempfile
        with tempfile.TemporaryDirectory() as t:   # the starter base passes its own check
            tf = Path(t) / 'base.json'; tf.write_text(json.dumps(files[files[ORG_RECORD]['base_profile']]), encoding='utf-8')
            _p.activate_file(tf); _p.deactivate()
    except (NewError, _p.ProfileError) as e:
        print(f'ERROR: {e}', file=sys.stderr); return 2
    rec = files[ORG_RECORD]
    out = {**rec, 'folder': root.as_posix(), 'files': sorted(files) + ['workspaces/'], 'dry_run': bool(a.dry_run)}
    if not a.dry_run:
        from .files import Batch
        b = Batch()
        for f, d in files.items(): b.json(root / f, d)
        b.commit(); (root / 'workspaces').mkdir(exist_ok=True)
    if a.json: print(json.dumps(out, indent=2)); return 0
    print(f"{'would start' if a.dry_run else 'started'} organisation {name} in {root.as_posix()}: {rec['base_profile']} (a starter base profile — checked), workspaces/\n"
          f"Next — add {name}'s types, attributes and rules to {rec['base_profile']} (check: sdem profile check --file {(root / rec['base_profile']).as_posix()}); "
          f"start a workspace: sdem new --workspace workspaces/<name> --organisation {a.organisation} --person <you>")
    return 0


def explore(workspace, as_json=False, home_out='work/sdem', record=None):
    """EX-01: build a workspace's knowledge graph and write the three pages to explore it — `sdem build`, `sdem view`, `sdem dashboard`,
    `sdem home` exactly as documented, run in order. Writes derived outputs only; a step that fails stops here and says which."""
    import contextlib, io
    from .cli import main as sdem
    ws = Path(workspace); graph = ws / 'graph'
    steps = [['build', '--workspace', str(ws), '--out', str(graph)], ['view', '--graph', str(graph)], ['dashboard', '--workspace', str(ws)],
             ['home', '--root', str(ws.parent), '-o', home_out]]
    for s in steps:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf): code = sdem(s)
        if code:
            print(buf.getvalue()[-1500:], end=''); print(f"ERROR: sdem {' '.join(s)} did not succeed — fix what it says, then run it again", file=sys.stderr); return code
    index = Path(home_out) / 'index.html'
    if as_json:
        print(json.dumps({**(record or {}), 'explore': {'graph': graph.as_posix(), 'view': (graph / 'view.html').as_posix(), 'dashboard': (ws / 'dashboard.html').as_posix(),
                                                       'home': index.as_posix()}}, indent=2)); return 0
    print(f'built the knowledge graph ({graph.as_posix()}) and wrote the pages to explore it:\n'
          f'  SDEM Home            {index.as_posix()}\n  Workspace Dashboard  {(ws / "dashboard.html").as_posix()}\n  Architecture Graph   {(graph / "view.html").as_posix()}\n'
          f'Open SDEM Home: open {index.as_posix()}   (Linux: xdg-open · Windows: start) — or file://{index.resolve().as_posix()}\n'
          'They are read-only snapshots: after the workspace changes, run the same commands again (sdem build, view, dashboard, home).')
    return 0


if __name__ == '__main__':
    sys.exit(main())


def catalogue(workspace):
    """The BIAN catalogue a workspace chooses its service domains from (WS-01): its own A2 layer plus the catalogue its record
    names — the shared layer, or the base BIAN. An A2 dataset (the workspace's own records first), or None."""
    ws = Path(workspace)
    from . import profile as _p; _p.activate_from(ws)   # PR-07
    rec = json.loads((ws / RECORD).read_text(encoding='utf-8')) if (ws / RECORD).exists() else {}
    src = (rec.get('bian') or {}).get('catalogue', 'base')
    if src is None: cat = None
    elif src == 'base' or not Path(src).exists(): cat, _ = base_layer()
    else: cat = json.loads(Path(src).read_text(encoding='utf-8'))
    own = json.loads((ws / DATASETS['A2']).read_text(encoding='utf-8')) if (ws / DATASETS['A2']).exists() else None
    if not cat: return own
    if not own or not own.get('instances'): return cat
    have = {i['id'] for i in own['instances']}
    # WS-07: a catalogue element the workspace already holds under its own id (same type and natural key, LC-09 — e.g. the asset
    # type 'Consumer Loan' as AT-LO) is that record: it is not added twice, and the catalogue's references point to the workspace's id
    from .conformance import natural_keys
    from .metamodel import Metamodel
    mm = Metamodel.load()
    mine = {k[0]: rid for rid, k in natural_keys(own, mm).items()}
    same = {}
    for _ in range(4):   # in rounds: a matched service domain makes its control record's key (its owner) comparable too
        rels = [{**r, 'source': same.get(r['source'], r['source']), 'target': same.get(r['target'], r['target'])} for r in cat.get('relationships', [])]
        ids = [{**i, 'id': same.get(i['id'], i['id'])} for i in cat['instances']]
        keyed = natural_keys({'instances': own['instances'] + [i for i in ids if i['id'] not in have],
                              'relationships': own.get('relationships', []) + rels}, mm)
        more = {}
        for i in cat['instances']:
            cid = i['id']
            if cid in have or cid in same: continue
            k = keyed.get(cid)
            if k and k[0] in mine and mine[k[0]] != cid: more[cid] = mine[k[0]]
        if not more: break
        same.update(more)
    fix = lambda v: [same.get(x, x) for x in v] if isinstance(v, list) else same.get(v, v) if isinstance(v, str) else v
    added = [{**i, 'attributes': {k: fix(v) for k, v in i['attributes'].items()}} if i.get('attributes') else i
             for i in cat['instances'] if i['id'] not in have and i['id'] not in same]
    keys = {(r['source'], r['kind'], r['target']) for r in own.get('relationships', [])}
    typ = {i['id']: i['type'] for i in own['instances'] + cat['instances']}
    held = {(r['source'], r['kind'], 'out', typ.get(r['target'])) for r in own.get('relationships', [])} | \
           {(r['target'], r['kind'], 'in', typ.get(r['source'])) for r in own.get('relationships', [])}
    rels = []
    for r in cat.get('relationships', []):
        r = {**r, 'source': same.get(r['source'], r['source']), 'target': same.get(r['target'], r['target'])}
        k = (r['source'], r['kind'], r['target'])
        if r['source'] == r['target'] or k in keys: continue
        if (r['source'] in have and (r['source'], r['kind'], 'out', typ.get(r['target'])) in held) or \
           (r['target'] in have and (r['target'], r['kind'], 'in', typ.get(r['source'])) in held): continue   # the workspace's own link of this kind wins (WS-01)
        keys.add(k); rels.append(r)
    return {**own, 'instances': own['instances'] + added, 'relationships': own.get('relationships', []) + rels}
