"""`sdem new` — start a workspace: the folder where one area's architecture is kept (docs/design/sdem-workspace-spec.md, WS-*).

It creates the four layer datasets — A1, A3 and A4 empty; A2 your BIAN layer — and an empty registry of connections, checks
the whole workspace, and records who started it and where its BIAN layer came from (workspace.json). The BIAN layer is your
organisation's shared one (bian/a2-service-domain.json) when there is one; otherwise every service domain of the base BIAN
that ships with SDEM, with the accepted inferences applied. Narrow it later with `sdem bian custom`.

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
    if no_bian:
        a2, source = None, 'none yet — business does not connect to applications until a BIAN layer is added (sdem bian custom, or sdem load --a2)'
    elif shared.exists():
        a2 = json.loads(shared.read_text(encoding='utf-8'))
        if a2.get('level') != 'A2': raise NewError(f'{shared}: not an A2 dataset (level {a2.get("level")!r})')
        source = f'your shared BIAN layer {shared}'
    else:
        a2, source = base_layer()
    stem = re.sub(r'[^A-Z0-9]+', '-', ws.name.upper()).strip('-') or 'WORKSPACE'
    docs = {f: ({'level': lvl, 'model_id': f'{stem}-{lvl}', 'model_version': today, 'metamodel_version': mm.version, 'source_system': SYSTEM,
                 'instances': [], 'relationships': []} if lvl != 'A2' else a2) for lvl, f in DATASETS.items() if lvl != 'A2' or a2}
    registry = {**EMPTY_REGISTRY, 'metamodel_version': mm.version}
    errors = estate_errors(docs, registry)
    if errors: raise NewError('the new workspace would not pass its checks — nothing written:\n  ' + '\n  '.join(errors[:10]))
    sds = sum(1 for i in (a2 or {}).get('instances', []) if i['type'] == 'A2.ServiceDomain')
    record = {'format': FORMAT, 'name': ws.name, 'created': today, 'created_by': person.strip(),
              'bian': {'source': source, 'release': (a2 or {}).get('model_version'), 'selection': 'none' if no_bian else 'all', 'service_domains': sds}}
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
    ap.add_argument('--bian', metavar='FILE', help=f'the BIAN layer to start from (default: {SHARED} if it exists, else the full base BIAN)')
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
        print(f"{'would start' if a.dry_run else 'started'} {a.estate}: A1, A3, A4 empty; "
              + (f"no BIAN layer ({record['bian']['source']})" if a.no_bian else f"A2 {record['bian']['service_domains']} service domains from {record['bian']['source']}")
              + '; no connections yet — checked')
    if a.dry_run: return 0
    from .files import Batch
    ws = Path(a.estate); b = Batch()
    for f, d in docs.items(): b.json(ws / f, d)
    b.json(ws / 'mappings.json', registry); b.json(ws / RECORD, record); b.commit()
    if not a.json:
        print(f'Next — existing designs: sdem load work/history --workspace {a.estate} --person <you>  ·  '
              f'a new design: sdem aid project --workspace {a.estate} --out {a.estate}/plans/<name>  ·  '
              f'narrow the BIAN layer: sdem bian custom --workspace {a.estate} --only "<service domain>" … --person <you>')
    return 0


if __name__ == '__main__':
    sys.exit(main())
