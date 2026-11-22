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
DATA_TYPES = ('data.DataEntity', 'data.DataAttribute', 'data.DataDomain')   # DAR-01: a data domain is Data's too
EVIDENCE = 'application_architecture_document:sdem-migrate-0.20#within-layer-access'


class Migrate20Error(ValueError):
    """The workspace cannot be migrated as it is — nothing written."""


def _design_files(ws):
    from .identity import _derived
    return sorted(p for p in Path(ws).rglob('*.json') if BACKUP not in p.parts and not _derived(p))


def to_019(folder):
    """A folder in the 0.20 form read as 0.19 held it — {0.19 file name: document}, Data's records in the Application file and each
    approved ACCESSED_BY as access inside it — and those ACCESSED_BY links themselves, to be put back as they were (sdem new from a
    0.20 baseline, DL-D9). Read with 0.19's stack (no workspace is active), so the names are 0.19's."""
    from .identity import load
    folder = Path(folder); new = {v: k for k, v in OLD.items()}
    docs = {new[l]: load(folder / f'{l}.json') for l in ('business', 'bian', 'application', 'technology') if (folder / f'{l}.json').is_file()}
    access = []
    if (folder / 'data.json').is_file():
        from .identity import layer
        d = load(folder / 'data.json'); a = docs.setdefault('a3-application.json', {'level': layer('application'), 'instances': [], 'relationships': []})
        a['instances'] = list(a.get('instances', [])) + d.get('instances', []); a['relationships'] = list(a.get('relationships', [])) + d.get('relationships', [])
    reg = load(folder / 'mappings.json') if (folder / 'mappings.json').is_file() else None
    if reg is not None:
        keep = []
        for m in reg.get('mappings', []):
            if m.get('relationship') == 'ACCESSED_BY':
                access.append(m)
                if m.get('status') == 'approved' and 'a3-application.json' in docs:
                    docs['a3-application.json']['relationships'].append({'source': m['target']['id'], 'kind': 'access', 'target': m['source']['id'],
                                                                         **({'access_mode': m['access_mode']} if m.get('access_mode') else {})})   # DAR-03: its mode goes with it
            else: keep.append(m)
        reg = {**reg, 'mappings': keep}
    return docs, reg, access


def _keep_chain(ws, person):
    """CTL-20, AG-S08: every layer file with change sets was rewritten in ids — the rewrite is recorded as a change set the person adopts,
    so the chain of change sets stays whole. Layers without change sets are not touched (nothing to keep whole)."""
    if not (ws / 'coordination' / 'change-sets').exists(): return []
    from .agents import Estate, CoordinationError
    from .layers import FILES
    est = Estate(ws); done = []
    for code in list(FILES):
        if not est._last_change_set(code): continue
        try: est.adopt(code, person, 'sdem migrate --to 0.20: the layer file rewritten in the 0.20 form — its names stored as ids, Data its own layer (DL-11, DL-12); no record changed in meaning'); done.append(code)
        except CoordinationError as e:
            if 'has not changed' not in str(e): raise Migrate20Error(f'recording the migration of layer {code} as a change set: {e}')
    return done


def _ledger(ws):
    from .files import LEDGER
    try: return (json.loads((ws / LEDGER).read_text(encoding='utf-8')).get('files') or {}) if (ws / LEDGER).exists() else {}
    except ValueError: return {}


def _carry_ledger(ws, renamed, old_entries):
    """AF-07: the ledger names the files as they are now — each renamed file keeps its entry's author and note, and says it was migrated;
    the old names leave the ledger with the files (a baseline from sdem new --from stays the baseline)."""
    from .files import LEDGER, write_text, dumps
    f = ws / LEDGER
    if not f.exists(): return
    try: led = json.loads(f.read_text(encoding='utf-8'))
    except ValueError: return
    files = led.get('files') or {}
    for pair in renamed:
        old, new = [Path(x.strip()).name for x in pair.split('→')]
        files.pop(old, None)
        e = old_entries.get(old)
        if e and new in files:   # its new content's fingerprint, its author as before
            files[new] = {**files[new], 'by': e.get('by'), 'note': ((e['note'] + '; ') if e.get('note') else '') + f'{old} until sdem migrate --to 0.20'}
    led['files'] = dict(sorted(files.items())); write_text(f, dumps(led))


def plan(ws, person, today=None, access=None, approve_access=True):
    """{relative path: new document} for every file the migration writes, the old paths it removes, and what it did."""
    from . import profile as _p, parts
    from .identity import load, store_names, _ids_folder
    ws = Path(ws)
    if not (ws / 'workspace.json').is_file(): raise Migrate20Error(f'{ws}: not a workspace (no workspace.json)')
    if _ids_folder(str(ws.resolve())): raise Migrate20Error(f'{ws}: already in the 0.20 form (workspace.json "names": "ids")')
    _p.activate_from(ws)   # the 0.19 form: its names and codes read as 0.19 wrote them
    if parts.migrated(): raise Migrate20Error(f'{ws}: already in the 0.20 form')
    today = today or datetime.date.today().isoformat()
    from .identity import _keys
    docs = {p.relative_to(ws).as_posix(): store_names(load(p), True, keys=_keys(p)) for p in _design_files(ws)}   # DL-11: ids, whatever the stack — a coordination record's layer too
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
        if True:   # DL-01: the Data layer is in use in a migrated workspace — its file is there, empty when no record is data yet
            data = {'level': 'data', 'model_id': f"{app.get('model_id', 'workspace')}-data", 'model_version': app.get('model_version'),
                    'metamodel_version': app.get('metamodel_version'), 'source_system': app.get('source_system'),
                    'instances': [i for i in app['instances'] if i['id'] in data_ids], 'relationships': inside}
            out['data.json'] = {k: v for k, v in data.items() if v is not None}
            out['application.json'] = {**app, 'instances': [i for i in app['instances'] if i['id'] not in data_ids], 'relationships': keep}
            did['data_records'], did['data_links'] = len(data_ids), len(inside)
        if accesses and access is not None:   # the baseline's own ACCESSED_BY links, as they were (to_019) — never re-approved
            maps = out.get('mappings.json') or {'mappings': []}
            from .identity import store_names
            out['mappings.json'] = {**maps, 'mappings': list(maps.get('mappings', [])) + store_names(access, True)}
            did['access_links'] = len(access); accesses = []
        if accesses:
            ver = {i['id']: i.get('version', '1.0') for i in app.get('instances', [])}
            maps = out.get('mappings.json') or {'mappings': []}
            n = len(maps.get('mappings', []))
            import collections   # the workspace's own baseline — what its approved links carry most; MIGRATION-0.20 when it has none
            base = (collections.Counter(m.get('baseline_id') for m in maps.get('mappings', []) if m.get('baseline_id')).most_common(1) or [('MIGRATION-0.20', 0)])[0][0]
            new = [{'mapping_id': f'MIG-020-{k:03d}', 'source': {'id': r['target'], 'type': typ[r['target']], 'version': ver.get(r['target'], '1.0')},
                    'relationship': 'ACCESSED_BY', 'target': {'id': r['source'], 'type': typ[r['source']], 'version': ver.get(r['source'], '1.0')},
                    'perspective': 'information', 'status': 'approved' if approve_access else 'proposed', 'evidence': [EVIDENCE],
                    'rationale': ((f"Approved by the migration to 0.20 (sdem migrate --to 0.20, {person}, {today}): " if approve_access else
                                   f"Proposed by the migration to 0.20 ({today}) for a person to approve — a design just taken in, which nobody has reviewed (DL-26): ")
                                  + "an access link inside the Application layer of SDEM 0.19, now between the Data and Application layers (DL-04, DL-13)"
                                  + (f"; as stated in {r['source_id']}" if r.get('source_id') else '')),
                    'baseline_id': base, **({'reviewer_id': person, 'approved_at': today} if approve_access else {'created_by': 'sdem migrate --to 0.20'})}
                   for k, r in enumerate(accesses, start=n + 1)]
            out['mappings.json'] = {**maps, 'mappings': list(maps.get('mappings', [])) + new}
            did['access_links'] = len(new)
    rec = out['workspace.json']
    out['workspace.json'] = {**rec, 'names': 'ids', 'migrated': {'to': '0.20', 'at': today, 'by': person, 'backup': BACKUP}}
    return out, removed, did


def migrate(ws, person, dry_run=False, today=None, access=None, keep_backup=True, approve_access=True):
    """DL-12: plan, back up, write, check — restore the backup if the check does not pass. `access`: a baseline's ACCESSED_BY links to
    keep as they were (sdem new); keep_backup=False for a workspace just made, which has nothing to go back to."""
    from . import parts, profile as _p
    from .identity import changed
    ws = Path(ws)
    out, removed, did = plan(ws, person, today, access=access, approve_access=approve_access)
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
        from .files import record, TRACKED, LEDGER
        old = _ledger(ws)
        record([ws / f for f in out if Path(f).name in TRACKED])
        _carry_ledger(ws, did['renamed'], old)   # who made each file, and what it was called, stays known (AF-07, GV-05)
        res['chain'] = _keep_chain(ws, person)   # before the check: the chain of change sets is part of what it checks
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
    if not keep_backup: shutil.rmtree(bk, ignore_errors=True); res['backup'] = None
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


def export_019(ws, out):
    """A workspace in the 0.20 form written to `out` as 0.19 held it — Data's records in the Application file, each approved
    ACCESSED_BY as access inside it, 0.19's file names and type names — for a consumer built on 0.19's form (the DESNRE publisher,
    DL-23). The workspace itself is only read. The copy is the design, not its history: its change sets stay with the workspace, where
    they are checked (CTL-20) — their fingerprints are of the 0.20 files; the copy's ledger names the export as what wrote its files."""
    from . import parts
    from .identity import load, _derived
    ws, out = Path(ws), Path(out)
    parts.reset()   # no workspace active: 0.19's stack — every name read as 0.19 named it
    docs, reg, _ = to_019(ws)
    shutil.copytree(ws, out, ignore=shutil.ignore_patterns(BACKUP, 'graph', '*.graph.json', 'coordination'))
    raw = lambda p, d: Path(p).write_bytes((json.dumps(d, indent=2, ensure_ascii=False) + '\n').encode('utf-8'))
    rec = json.loads((ws / 'workspace.json').read_text(encoding='utf-8')) if (ws / 'workspace.json').is_file() else None
    if rec is not None: raw(out / 'workspace.json', {k: v for k, v in rec.items() if k not in ('names', 'migrated', 'core_only')})   # 0.19's stack in the copy
    for l in ('business', 'bian', 'data', 'application', 'technology'):
        if (out / f'{l}.json').exists(): (out / f'{l}.json').unlink()
    if 'a2-service-domain.json' not in docs and docs:   # a design without BIAN: 0.19 always had the layer — here empty, as a design with no service domains yet
        some = next(iter(docs.values()))
        from .identity import _index   # BIAN's code in 0.19's form — what the copy is written in
        docs['a2-service-domain.json'] = {'level': _index()[0]['bian'], 'model_id': f"{ws.name}-a2", 'model_version': some.get('model_version'), 'metamodel_version': some.get('metamodel_version'),
                                         'source_system': some.get('source_system'), 'instances': [], 'relationships': []}
        docs['a2-service-domain.json'] = {k: v for k, v in docs['a2-service-domain.json'].items() if v is not None}
    for f, d in docs.items(): raw(out / f, d)
    if reg is not None: raw(out / 'mappings.json', reg)
    done = set(docs) | {'mappings.json', 'workspace.json'}
    for p in sorted(ws.rglob('*.json')):   # every other design file: 0.19's names
        rel = p.relative_to(ws)
        if BACKUP in rel.parts or 'coordination' in rel.parts or _derived(p) or rel.as_posix() in done or p.name in {f'{l}.json' for l in ('business', 'bian', 'data', 'application', 'technology')}: continue
        try: raw(out / rel, load(p))
        except ValueError: pass
    from .files import record, TRACKED, LEDGER
    if (out / LEDGER).exists():   # AF-07: the copy's files as the export wrote them — not edits outside SDEM
        record([out / f for f in TRACKED if (out / f).exists()], by=f'sdem export_019 (from the 0.20 workspace {ws.name})')
    return out
