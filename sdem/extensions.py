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
    """Where extensions are looked for: SDEM_EXTENSIONS_PATH when set (exactly those folders — an organisation pinning its extensions, a
    test), otherwise the folder SDEM's own Python runs from (a virtual environment's bin), then the PATH."""
    if os.environ.get('SDEM_EXTENSIONS_PATH') is not None: return os.environ['SDEM_EXTENSIONS_PATH']
    here = str(Path(sys.executable).parent)
    return os.pathsep.join([here, os.environ.get('PATH', '')])


IN_PROCESS = 'python:'   # MX-56: an extension SDEM calls in its own process — `python:<module>`, where no program can be started (a browser)


def _in_process():
    """MX-56: the extension modules SDEM calls in its own process — SDEM_EXTENSIONS_IN_PROCESS, comma-separated (`sdem_bian`), or a
    bundle's sdem-in-process.json: where a program cannot be started (Pyodide, in DESNRE's workbench), an extension's package is imported
    and its entry() called."""
    if 'SDEM_EXTENSIONS_IN_PROCESS' in os.environ:
        return [m.strip() for m in os.environ['SDEM_EXTENSIONS_IN_PROCESS'].split(',') if m.strip()]
    from .paths import DATA_ROOT   # or a bundle laid out as a checkout says so beside SDEM: sdem-in-process.json {"extensions": ["sdem_bian"]}
    try: return [m for m in json.loads((DATA_ROOT / 'sdem-in-process.json').read_text(encoding='utf-8')).get('extensions', []) if isinstance(m, str) and m]
    except (OSError, ValueError, AttributeError): return []


def find(name):
    """The program for extension <name> (or `python:<module>`, MX-56), or None."""
    if not NAME.match(name or '') or f'sdem-{name}' in _own():
        return None
    mod = f"sdem_{name.replace('-', '_')}"
    if mod in _in_process(): return IN_PROCESS + mod
    return shutil.which(f'sdem-{name}', path=_search_path())


def _call(program, argv, timeout=None):
    """Run an extension: its program, or (MX-56) its module's entry() in this process, SDEM's own state kept as it was — the answer
    the same either way: (returncode, stdout, stderr)."""
    if str(program).startswith(IN_PROCESS):
        import contextlib, importlib, io, types
        from . import profile
        o, e = io.StringIO(), io.StringIO()
        try:
            entry = importlib.import_module(str(program)[len(IN_PROCESS):]).entry
        except (ImportError, AttributeError) as x:
            return types.SimpleNamespace(returncode=127, stdout='', stderr=f'{program}: {x}\n')
        keep = getattr(profile, 'kept', None)   # absent while SDEM's profile is still loading (the manifest asked then changes nothing)
        with (keep() if keep else contextlib.nullcontext()), contextlib.redirect_stdout(o), contextlib.redirect_stderr(e):
            try: code = entry(list(map(str, argv)))
            except SystemExit as x: code = x.code
        code = code if isinstance(code, int) else (0 if code is None else 1)
        return types.SimpleNamespace(returncode=code, stdout=o.getvalue(), stderr=e.getvalue())
    return subprocess.run([program, *map(str, argv)], capture_output=True, text=True, timeout=timeout, encoding='utf-8', errors='replace',
                          env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})   # the answer is UTF-8 JSON on every platform (Windows' console is not)


def manifest(program):
    """The extension's manifest (it answers --manifest), or None if it does not — then it is not an SDEM extension."""
    try:
        r = _call(program, ['--manifest'], timeout=20)
        m = json.loads(r.stdout) if r.returncode == 0 else None
        return m if isinstance(m, dict) and m.get('name') else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def installed():
    """Every installed extension: [{name, program, manifest}], by name."""
    seen, out = set(), []
    for mod in _in_process():   # MX-56: called in this process
        name = mod[5:].replace('_', '-') if mod.startswith('sdem_') else ''
        m = manifest(IN_PROCESS + mod) if NAME.match(name) else None
        if m: seen.add(name); out.append({'name': name, 'program': IN_PROCESS + mod, 'manifest': m})
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
        if sys.stdout is sys.__stdout__ and sys.stderr is sys.__stderr__ and not str(prog).startswith(IN_PROCESS):
            return subprocess.call([prog, *argv])   # straight to the terminal, as it runs
        r = _call(prog, argv)
        sys.stdout.write(r.stdout); sys.stderr.write(r.stderr)   # SDEM's own output redirected (a test, the agent): the extension's goes there too
        return r.returncode
    except KeyboardInterrupt:
        return 130


def infer(program, workspace, step, timeout, phase=None, state=None, options=None):
    """MX-47: ask an installed extension for its inference — `sdem-<name> infer --workspace DIR --step aid|link --json`. Only for one the
    workspace's profile includes and whose manifest says it infers (sdem.ext_infer.askable, MX-45, MX-46); the one other place SDEM runs an extension."""
    extra = ['--phase', phase, '--state', str(state)] if phase else []   # MX-54: one phase of a built-in extension's part of sdem aid, its state in a file
    if options: extra += ['--options', json.dumps(options)]   # MX-53: the engine's options (an acceptance case's), for its rules too
    return _call(program, ['infer', '--workspace', str(workspace), '--step', step, *extra, '--json'], timeout=timeout)


def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem extensions', description='The installed SDEM extensions — run one as sdem <name> … (EXT-15)')
    ap.add_argument('--json', action='store_true', help='as data: {"count", "items", "built_in"}')
    ap.add_argument('--workspace', dest='estate', metavar='DIR', help="also say whether each built-in extension is on in this workspace, and why (BX-10…BX-13)")
    a = ap.parse_args(argv)
    items = installed()
    from .profile import BUILTIN
    from . import parts
    if a.estate:
        from . import profile as _p; _p.activate_from(a.estate)
    built = []   # BX-15 (0.22): SDEM builds in no extension — BIAN comes only from sdem-bian
    for x in items:   # BX-15: BIAN comes from the installed sdem-bian — whether it is on in this workspace, and why, said there
        if x['name'] == parts.EXT_BIAN.split(':', 1)[1] and (parts.package() or {}).get('refused'): x['refused'] = parts.package()['refused']   # said, not used
        if a.estate and x['name'] == parts.EXT_BIAN.split(':', 1)[1]:
            x.update({'on': parts.bian_on(), 'why': parts.why(), **({'make_explicit': f'sdem profile include {parts.EXT_BIAN} --workspace {a.estate} --person <you> --reason "…"'}
                      if parts.bian_on() and 'BX-11' in parts.why() else {})})
    if a.json:
        print(json.dumps({'count': len(items), 'items': items, 'built_in': built}, indent=2, ensure_ascii=False))
        return 0
    for x in built:
        print(f"  {x['name']:<14} {x['manifest'].get('version', ''):<8} built in — {x['manifest'].get('description', '')}"
              + (f"\n  {'':<14} {'on' if x['on'] else 'off'} in this workspace: {x['why']}" + (f"\n  {'':<14} make it explicit: {x['make_explicit']}" if x.get('make_explicit') else '') if 'on' in x else ''))
    if not items:
        print('No SDEM extensions installed. An extension is a program called sdem-<name>; install it into the same environment as SDEM '
              '(for example pip install <its folder>), then run it as sdem <name>.')
        return 0
    print(f'{len(items)} extension(s) — run one as sdem <name> …')
    for x in items:
        m = x['manifest']
        print(f"  {x['name']:<14} {m.get('version', ''):<8} {m.get('description', '')}" + (f"\n  {'':<14} not usable: {x['refused']}" if x.get('refused') else '')
              + (f"\n  {'':<14} {'on' if x['on'] else 'off'} in this workspace: {x['why']}" + (f"\n  {'':<14} make it explicit: {x['make_explicit']}" if x.get('make_explicit') else '') if 'on' in x else ''))
        print(f"  {'':<14} supports SDEM {m.get('sdem', '?')}; sends to {', '.join(m.get('sends_to') or ['nothing'])}; data: {m.get('data', '?')}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
