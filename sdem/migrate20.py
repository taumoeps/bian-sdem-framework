"""Migrate a workspace to SDEM 0.20's form (docs/design/sdem-data-layer-spec.md, DL-10…DL-13): files named by layer id, records that
store type ids, the Data layer of its own — and a backup, so `sdem migrate --rollback` restores every byte.

What it does, only on a person's command (DL-12):
  - every design file is read as 0.19 wrote it and stored with ids (DL-11); graph stores are derived and left to be rebuilt;
  - the layer files are renamed by layer id (a3-application.json → application.json, DL-10);
  - the data entities and data attributes, with the links among them, move from the Application file to data.json (DL-01, DL-02);
  - each access link from an application element to a data entity becomes an approved link between the layers, ACCESSED_BY,
    approved by the migration — the person who ran it — with the original link's source kept (DL-04, DL-13);
  - the workspace is checked in its new form; if it does not pass, the backup is restored and nothing has changed.
"""
import datetime, json, shutil
from pathlib import Path

from .files import dumps, write_text

BACKUP = '.sdem-backup-0.20'
OLD = {'a1-business.json': 'business', 'a2-service-domain.json': 'bian', 'a3-application.json': 'application', 'a4-technology.json': 'technology'}
DATA_TYPES = ('data.DataEntity', 'data.DataAttribute')
EVIDENCE = 'application_architecture_document:sdem-migrate-0.20#within-layer-access'


class Migrate20Error(ValueError):
    """The workspace cannot be migrated as it is — nothing written."""


def _design_files(ws):
    from .identity import _derived
    return sorted(p for p in Path(ws).rglob('*.json') if BACKUP not in p.parts and not _derived(p))


def plan(ws, person, today=None):
    """{relative path: new document} for every file the migration writes, the old paths it removes, and what it did."""
    from . import profile as _p, parts
    from .identity import load, store_names, _ids_folder
    ws = Path(ws)
    if not (ws / 'workspace.json').is_file(): raise Migrate20Error(f'{ws}: not a workspace (no workspace.json)')
    if _ids_folder(str(ws.resolve())): raise Migrate20Error(f'{ws}: already in the 0.20 form (workspace.json "names": "ids")')
    _p.activate_from(ws)   # the 0.19 form: its names and codes read as 0.19 wrote them
    if parts.migrated(): raise Migrate20Error(f'{ws}: already in the 0.20 form')
    today = today or datetime.date.today().isoformat()
    docs = {p.relative_to(ws).as_posix(): store_names(load(p), True) for p in _design_files(ws)}   # DL-11: ids, whatever the stack
    out, removed, did = {}, [], {'renamed': [], 'data_records': 0, 'data_links': 0, 'access_links': 0}
    for rel, d in docs.items():
        name = Path(rel).name
        if Path(rel).parent == Path('.') and name in OLD:
            new = f'{OLD[name]}.json'; out[new] = d; removed.append(rel); did['renamed'].append(f'{rel} → {new}')
        else:
            out[rel] = d
    app = out.get('application.json')
    if app is not None:
        typ = {i['id']: i['type'] for i in app.get('instances', [])}
        data_ids = {k for k, t in typ.items() if t in DATA_TYPES}
        inside, accesses, keep, odd = [], [], [], []
        for r in app.get('relationships', []):
            s, t = r.get('source') in data_ids, r.get('target') in data_ids
            if s and t: inside.append(r)
            elif t and r.get('kind') == 'access': accesses.append(r)
            elif s or t: odd.append(r)
            else: keep.append(r)
        if odd:
            raise Migrate20Error('links between an application element and a data entity that are not access cannot move between the layers: '
                                 + '; '.join(f"{r.get('source')} {r.get('kind')} {r.get('target')}" for r in odd[:5]))
        if data_ids:
            data = {'level': 'data', 'model_id': f"{app.get('model_id', 'workspace')}-data", 'model_version': app.get('model_version'),
                    'metamodel_version': app.get('metamodel_version'), 'source_system': app.get('source_system'),
                    'instances': [i for i in app['instances'] if i['id'] in data_ids], 'relationships': inside}
            out['data.json'] = {k: v for k, v in data.items() if v is not None}
            out['application.json'] = {**app, 'instances': [i for i in app['instances'] if i['id'] not in data_ids], 'relationships': keep}
            did['data_records'], did['data_links'] = len(data_ids), len(inside)
        if accesses:
            ver = {i['id']: i.get('version', '1.0') for i in app.get('instances', [])}
            maps = out.get('mappings.json') or {'mappings': []}
            n = len(maps.get('mappings', []))
            import collections   # the workspace's own baseline — what its approved links carry most; MIGRATION-0.20 when it has none
            base = (collections.Counter(m.get('baseline_id') for m in maps.get('mappings', []) if m.get('baseline_id')).most_common(1) or [('MIGRATION-0.20', 0)])[0][0]
            new = [{'mapping_id': f'MIG-020-{k:03d}', 'source': {'id': r['target'], 'type': typ[r['target']], 'version': ver.get(r['target'], '1.0')},
                    'relationship': 'ACCESSED_BY', 'target': {'id': r['source'], 'type': typ[r['source']], 'version': ver.get(r['source'], '1.0')},
                    'perspective': 'information', 'status': 'approved', 'evidence': [EVIDENCE],
                    'rationale': (f"Approved by the migration to 0.20 (sdem migrate --to 0.20, {person}, {today}): an access link inside the Application layer "
                                  f"of SDEM 0.19, now between the Data and Application layers (DL-04, DL-13)" + (f"; as stated in {r['source_id']}" if r.get('source_id') else '')),
                    'baseline_id': base, 'reviewer_id': person, 'approved_at': today}
                   for k, r in enumerate(accesses, start=n + 1)]
            out['mappings.json'] = {**maps, 'mappings': list(maps.get('mappings', [])) + new}
            did['access_links'] = len(new)
    rec = out['workspace.json']
    out['workspace.json'] = {**rec, 'names': 'ids', 'migrated': {'to': '0.20', 'at': today, 'by': person, 'backup': BACKUP}}
    return out, removed, did


def migrate(ws, person, dry_run=False, today=None):
    """DL-12: plan, back up, write, check — restore the backup if the check does not pass."""
    from . import parts, profile as _p
    from .identity import changed
    ws = Path(ws)
    out, removed, did = plan(ws, person, today)
    res = {'workspace': str(ws), 'to': '0.20', **did, 'files_written': sorted(out), 'files_removed': sorted(removed), 'backup': str(ws / BACKUP)}
    if dry_run: return {**res, 'dry_run': True}
    bk = ws / BACKUP
    if bk.exists(): raise Migrate20Error(f'{bk} exists — an earlier migration\'s backup; roll it back (sdem migrate --rollback) or remove it first')
    originals = [p.relative_to(ws).as_posix() for p in ws.rglob('*') if p.is_file() and BACKUP not in p.parts]
    for rel in originals:
        (bk / rel).parent.mkdir(parents=True, exist_ok=True); shutil.copy2(ws / rel, bk / rel)
    (bk / 'manifest.json').write_text(json.dumps({'originals': originals, 'created': sorted(set(out) - set(originals))}, indent=1), encoding='utf-8')
    try:
        for rel, d in out.items(): write_text(ws / rel, dumps(d))   # already in ids: written as they are
        for rel in removed: (ws / rel).unlink()
        changed(); _p.activate_from(ws)   # the new form
        from .files import record, TRACKED
        record([ws / f for f in out if Path(f).name in TRACKED])
        from .cli import main as sdem
        import contextlib, io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = sdem(['check', '--workspace', str(ws)])
        if code != 0: raise Migrate20Error('the workspace does not pass its checks in the 0.20 form — restored as it was:\n' + buf.getvalue()[-2000:])
    except BaseException:
        rollback(ws, keep_backup=False); raise
    finally:
        parts.reset()
    return res


def rollback(ws, keep_backup=False):
    """Restore every byte from the backup: the files the migration created removed, the originals put back."""
    from .identity import changed
    ws = Path(ws); bk = ws / BACKUP
    if not bk.is_dir(): raise Migrate20Error(f'{ws}: no backup to roll back to ({BACKUP})')
    man = json.loads((bk / 'manifest.json').read_text(encoding='utf-8'))
    for rel in man['created']:
        if (ws / rel).exists(): (ws / rel).unlink()
    for rel in man['originals']:
        (ws / rel).parent.mkdir(parents=True, exist_ok=True); shutil.copy2(bk / rel, ws / rel)
    if not keep_backup: shutil.rmtree(bk)
    changed()
    return {'workspace': str(ws), 'restored': len(man['originals']), 'removed': man['created']}
