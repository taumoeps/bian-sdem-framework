"""Migrate a bundled example (a folder of layer files, not a workspace) to SDEM 0.20's form, in place (DL-20, DL-D9):
SDEM's own migration (sdem/migrate20.py) on a copy made a workspace, the 0.20 layer files copied back and 0.19's removed,
every other design file stored with type ids. Its graph store is rebuilt by the caller (sdem build).

    python scripts/migrate_example_020.py examples/payment-initiation jane.architect"""
import json, shutil, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main(folder, person):
    from sdem import migrate20, parts
    from sdem.identity import load, store_names, _derived, changed
    folder = Path(folder)
    if not any((folder / f).exists() for f in migrate20.OLD): sys.exit(f'{folder}: not in the 0.19 form')   # an example may lack a layer (acquired-fintech: no business)
    tmp = Path(tempfile.mkdtemp()) / 'ws'
    tmp.mkdir()
    layer = list(migrate20.OLD) + ['mappings.json', 'requirements.json']
    for f in layer:
        if (folder / f).exists(): shutil.copy2(folder / f, tmp / f)
    (tmp / 'workspace.json').write_text(json.dumps({'format': 'sdem-workspace/1', 'name': folder.name}), encoding='utf-8')
    migrate20.migrate(tmp, person, keep_backup=False)
    for f in migrate20.OLD: (folder / f).unlink(missing_ok=True)   # an example may lack a layer
    for f in ('business', 'bian', 'data', 'application', 'technology'):
        if (tmp / f'{f}.json').exists(): shutil.copy2(tmp / f'{f}.json', folder / f'{f}.json')
    for f in ('mappings.json', 'requirements.json'):
        if (tmp / f).exists(): shutil.copy2(tmp / f, folder / f)
    parts.reset(); changed()
    for p in sorted(folder.rglob('*.json')):   # the example's other design files (acceptance cases, migrations): ids too
        if _derived(p) or p.name in ('business.json', 'bian.json', 'data.json', 'application.json', 'technology.json', 'mappings.json', 'requirements.json'): continue
        d = json.loads(p.read_text(encoding='utf-8'))
        from sdem.identity import read_names
        p.write_bytes((json.dumps(store_names(read_names(d, legacy=True), True), indent=2, ensure_ascii=False) + '\n').encode('utf-8'))
    shutil.rmtree(tmp.parent, ignore_errors=True)
    print(f'{folder}: in the 0.20 form —', ', '.join(sorted(p.name for p in folder.glob('*.json'))))


if __name__ == '__main__':
    main(*sys.argv[1:3])
