"""SDEM extensions — finding and running the installed ones (docs/design/sdem-extensions-spec.md, EXT-15).

    sdem extensions [--json]        the installed extensions and their manifests
    sdem <name> …                   runs the installed extension sdem-<name> with the rest of the line

An extension is its own program, `sdem-<name>`, installed next to SDEM (the same environment's scripts folder) or on the PATH
(EXT-01). SDEM knows no extension by name: it only finds a program called sdem-<name> that answers `--manifest` with its
manifest (EXT-05), and hands it the rest of the command line. SDEM's own sdem-* programs are never taken for extensions.
"""
import argparse, json, os, re, shutil, subprocess, sys
from pathlib import Path

NAME = re.compile(r'^[a-z][a-z0-9-]{0,39}$')


def _own():
    """SDEM's own sdem-* programs (pyproject.toml [project.scripts]) — never extensions."""
    try:
        from importlib.metadata import distribution
        return {ep.name for ep in distribution('sdem').entry_points if ep.group == 'console_scripts'}
    except Exception:
        return {'sdem', 'sdem-validate', 'sdem-diff', 'sdem-trace', 'sdem-graph', 'sdem-infer', 'sdem-aid', 'sdem-transform', 'sdem-load',
                'sdem-eval', 'sdem-relationships', 'sdem-structure', 'sdem-spec', 'sdem-kgspec', 'sdem-diagram', 'sdem-catalogue',
                'sdem-attributes', 'sdem-confidence', 'sdem-logical', 'sdem-physical', 'sdem-accept', 'sdem-metamodel-spec', 'sdem-controls'}


def _search_path():
    """Where extensions are looked for: the folder SDEM's own Python runs from (a virtual environment's bin), then the PATH."""
    here = str(Path(sys.executable).parent)
    return os.pathsep.join([here, os.environ.get('PATH', '')])


def find(name):
    """The program for extension <name>, or None."""
    if not NAME.match(name or '') or f'sdem-{name}' in _own():
        return None
    return shutil.which(f'sdem-{name}', path=_search_path())


def manifest(program):
    """The extension's manifest (it answers --manifest), or None if it does not — then it is not an SDEM extension."""
    try:
        r = subprocess.run([program, '--manifest'], capture_output=True, text=True, timeout=20)
        m = json.loads(r.stdout) if r.returncode == 0 else None
        return m if isinstance(m, dict) and m.get('name') else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def installed():
    """Every installed extension: [{name, program, manifest}], by name."""
    seen, out = set(), []
    for folder in _search_path().split(os.pathsep):
        try:
            entries = sorted(os.listdir(folder))
        except OSError:
            continue
        for f in entries:
            name = f[5:] if f.startswith('sdem-') else ''
            for ext in ('.exe', '.cmd', '.bat'):   # Windows: pip installs sdem-<name>.exe
                if name.lower().endswith(ext): name = name[:-len(ext)]
            if not NAME.match(name) or name in seen or f'sdem-{name}' in _own():
                continue
            prog = os.path.join(folder, f)
            if not (os.path.isfile(prog) and os.access(prog, os.X_OK)):
                continue
            m = manifest(prog)
            if m:
                seen.add(name); out.append({'name': name, 'program': prog, 'manifest': m})
    return out


def run(name, argv):
    """`sdem <name> …`: run the extension with the rest of the line; its exit code is SDEM's. None if there is no such extension."""
    prog = find(name)
    if not prog or not manifest(prog):   # only a program that says it is an SDEM extension — a stray sdem-<name> on the PATH is not run
        return None
    try:
        return subprocess.call([prog, *argv])
    except KeyboardInterrupt:
        return 130


def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem extensions', description='The installed SDEM extensions — run one as sdem <name> … (EXT-15)')
    ap.add_argument('--json', action='store_true', help='as data: {"count", "items"}')
    a = ap.parse_args(argv)
    items = installed()
    if a.json:
        print(json.dumps({'count': len(items), 'items': items}, indent=2, ensure_ascii=False))
        return 0
    if not items:
        print('No SDEM extensions installed. An extension is a program called sdem-<name>; install it into the same environment as SDEM '
              '(for example pip install <its folder>), then run it as sdem <name>.')
        return 0
    print(f'{len(items)} extension(s) — run one as sdem <name> …')
    for x in items:
        m = x['manifest']
        print(f"  {x['name']:<14} {m.get('version', ''):<8} {m.get('description', '')}")
        print(f"  {'':<14} supports SDEM {m.get('sdem', '?')}; sends to {', '.join(m.get('sends_to') or ['nothing'])}; data: {m.get('data', '?')}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
