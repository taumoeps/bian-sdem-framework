"""`sdem new` — start a workspace: the folder where one area's architecture is kept (docs/design/sdem-workspace-spec.md, WS-*).

It creates the four layer datasets — all empty — and an empty registry of connections, checks the workspace, and records who
started it and which **BIAN catalogue** it uses (workspace.json): your organisation's shared BIAN layer (bian/a2-service-domain.json)
when there is one, otherwise the base BIAN that ships with SDEM. The catalogue is read, never copied: `sdem aid` brings into the
workspace's A2 layer only the service domains its design needs, and `sdem bian custom --add` adds one by hand (WS-01).
`--bian FILE` starts instead with exactly that BIAN layer in A2.

  sdem new --workspace workspaces/payments --person jane.architect
"""
import argparse, datetime, json, re, sys
from pathlib import Path

DATASETS = {'A1': 'a1-business.json', 'A2': 'a2-service-domain.json', 'A3': 'a3-application.json', 'A4': 'a4-technology.json'}
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


def plan(workspace, person, bian_file=None, today=None, no_bian=False):
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
        source = 'none — business does not connect to applications until a BIAN layer is added (sdem bian custom --add)'
    elif bian_file:   # started with exactly this BIAN layer
        a2 = json.loads(shared.read_text(encoding='utf-8'))
        if a2.get('level') != 'A2': raise NewError(f'{shared}: not an A2 dataset (level {a2.get("level")!r})')
        source, catalogue = f'the BIAN layer {shared}', str(shared)
    else:             # WS-01: the catalogue is read, not copied; A2 holds only the domains the design needs
        a2 = {'level': 'A2', 'model_id': f'{stem}-A2', 'model_version': today, 'metamodel_version': mm.version, 'source_system': SYSTEM,
              'instances': [], 'relationships': []}
        catalogue = str(SHARED) if SHARED.exists() else 'base'
        source = 'sdem aid brings in the service domains your design needs, from ' + (f'your shared BIAN layer {SHARED}' if SHARED.exists() else 'the base BIAN that ships with SDEM')
    docs = {f: ({'level': lvl, 'model_id': f'{stem}-{lvl}', 'model_version': today, 'metamodel_version': mm.version, 'source_system': SYSTEM,
                 'instances': [], 'relationships': []} if lvl != 'A2' else a2) for lvl, f in DATASETS.items() if lvl != 'A2' or a2}
    registry = {**EMPTY_REGISTRY, 'metamodel_version': mm.version}
    errors = estate_errors(docs, registry)
    if errors: raise NewError('the new workspace would not pass its checks — nothing written:\n  ' + '\n  '.join(errors[:10]))
    sds = sum(1 for i in (a2 or {}).get('instances', []) if i['type'] == 'A2.ServiceDomain')
    record = {'format': FORMAT, 'name': ws.name, 'created': today, 'created_by': person.strip(),
              'bian': {'catalogue': catalogue, 'source': source, 'selection': 'none' if no_bian else 'given' if bian_file else 'relevant',
                       'service_domains': sds}}
    return docs, registry, record


def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem new', formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description='Start a workspace — the folder where one area\'s architecture is kept: the four layers (A2 your BIAN layer) '
                                             'and the approved connections between them. Checked before anything is written.',
                                 epilog='Example:\n  sdem new --workspace workspaces/payments --person jane.architect\n\n'
                                        'Next: existing designs — sdem transform run … then sdem load work/history --workspace workspaces/payments --person <you>; '
                                        'a new design — sdem aid project --workspace workspaces/payments --out workspaces/payments/plans/<name>.')
    ap.add_argument('--workspace', dest='estate', required=True, metavar='DIR', help='the folder to start, e.g. workspaces/payments')
    ap.add_argument('--person', required=True, help='your name — a person')
    ap.add_argument('--bian', metavar='FILE', help=f'start with exactly this BIAN layer in A2 (default: A2 empty; sdem aid brings in the domains your design needs from {SHARED} if it exists, else the base BIAN)')
    ap.add_argument('--no-bian', action='store_true', help='start without a BIAN layer (add it later); business then does not connect to applications')
    ap.add_argument('--dry-run', action='store_true'); ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    try:
        if a.no_bian and a.bian: raise NewError('give --bian or --no-bian, not both')
        docs, registry, record = plan(a.estate, a.person, a.bian, no_bian=a.no_bian)
    except NewError as e:
        print(f'ERROR: {e}', file=sys.stderr); return 2
    if a.json: print(json.dumps(record, indent=2))
    else:
        b_ = record['bian']
        print(f"{'would start' if a.dry_run else 'started'} {a.estate}: "
              + (f"A1, A3, A4 empty; A2 {b_['service_domains']} service domains from {b_['source']}" if a.bian else f"all four layers empty; BIAN: {b_['source']}")
              + '; no connections yet — checked')
    if a.dry_run: return 0
    from .files import Batch
    ws = Path(a.estate); b = Batch()
    for f, d in docs.items(): b.json(ws / f, d)
    b.json(ws / 'mappings.json', registry); b.json(ws / RECORD, record); b.commit()
    if not a.json:
        print(f'Next — write what you have (any of a1…a4), or load existing designs (sdem load work/history --workspace {a.estate} --person <you>); '
              f'then sdem aid --workspace {a.estate} --person <you> fills the gaps, including the BIAN service domains your design needs')
    return 0


if __name__ == '__main__':
    sys.exit(main())


def catalogue(workspace):
    """The BIAN catalogue a workspace chooses its service domains from (WS-01): its own A2 layer plus the catalogue its record
    names — the shared layer, or the base BIAN. An A2 dataset (the workspace's own records first), or None."""
    ws = Path(workspace)
    rec = json.loads((ws / RECORD).read_text(encoding='utf-8')) if (ws / RECORD).exists() else {}
    src = (rec.get('bian') or {}).get('catalogue', 'base')
    if src is None: cat = None
    elif src == 'base' or not Path(src).exists(): cat, _ = base_layer()
    else: cat = json.loads(Path(src).read_text(encoding='utf-8'))
    own = json.loads((ws / DATASETS['A2']).read_text(encoding='utf-8')) if (ws / DATASETS['A2']).exists() else None
    if not cat: return own
    if not own or not own.get('instances'): return cat
    have = {i['id'] for i in own['instances']}
    keys = {(r['source'], r['kind'], r['target']) for r in own.get('relationships', [])}
    return {**own, 'instances': own['instances'] + [i for i in cat['instances'] if i['id'] not in have],
            'relationships': own.get('relationships', []) + [r for r in cat.get('relationships', []) if (r['source'], r['kind'], r['target']) not in keys]}
