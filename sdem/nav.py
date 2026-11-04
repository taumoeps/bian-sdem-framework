"""Navigation between SDEM Home, a workspace's dashboard and its architecture graph (docs/design/sdem-dashboard-design.md,
"Navigation", NV-01…NV-08).

The pages are generated, read-only HTML files that open offline (file://). Links between them are relative and URL-encoded, so a
folder of pages can be moved or zipped, and paths with spaces work. A graph is linked only when it is current; otherwise the page
says why — not built, out of date, or the workspace cannot be built yet — and gives the command that fixes it.
"""
import json, os, shlex, urllib.parse
from pathlib import Path

STORE_MARK = 'federated.graph.json'


def href(from_file, to_file):
    """The relative, URL-encoded link from one generated file to another (works under file://, with spaces and special characters)."""
    rel = os.path.relpath(Path(to_file).resolve(), Path(from_file).resolve().parent)
    return urllib.parse.quote(Path(rel).as_posix())


def shown(path):
    """NV-07: a path as pages show it — relative to the folder the command runs in, so no machine-specific path is written into a
    page and the commands it suggests work from there (falls back to the path as given, e.g. on another Windows drive)."""
    try: return Path(os.path.relpath(Path(path))).as_posix()
    except ValueError: return Path(path).as_posix()


def default_store(workspace):
    """The workspace's own graph store, <workspace>/graph, when one has been built there."""
    p = Path(workspace) / 'graph'
    return p if (p / STORE_MARK).exists() else None


def view_build(view_file):
    """The graph build a generated graph viewer shows (NV-04), or None for a viewer from before v0.17.1 or no viewer."""
    try: text = Path(view_file).read_text(encoding='utf-8')
    except OSError: return None
    import re
    m = re.search(r'<meta name="sdem-graph-build" content="(\d+)"', text)
    return int(m.group(1)) if m else None


def graph_state(workspace, store=None):
    """NV-03: the state of a workspace's architecture graph — 'blocked' (the workspace needs migrating, or fails its checks, so no graph
    can be built), 'missing' (never built), 'stale' (built from inputs that have changed since, or new files), 'current' — with the
    reason and the command that fixes it. Read-only."""
    from . import profile as _p
    from .metamodel import Metamodel
    from .layers import DATASET_FILES
    from .store import stale_inputs, StoreError
    ws = Path(workspace); store = Path(store) if store else default_store(ws)
    q = lambda p: shlex.quote(Path(p).as_posix())
    target = store or ws / 'graph'
    out = {'workspace': ws.as_posix(), 'store': target.as_posix(), 'build': None}
    build_cmd = f'sdem build --workspace {q(ws)} --out {q(target)}'
    try: _p.activate_from(ws)
    except _p.ProfileError as e:
        return {**out, 'state': 'blocked', 'reason': f'the organisation profile does not pass: {str(e).splitlines()[0]}', 'command': f'sdem profile check --workspace {q(ws)}'}
    try:
        current = Metamodel.base().version
        files = [ws / f for f in DATASET_FILES if (ws / f).exists()] + ([ws / 'mappings.json'] if (ws / 'mappings.json').exists() else [])
        old = sorted({json.loads(f.read_text(encoding='utf-8')).get('metamodel_version') for f in files} - {current, None})
        if old:
            return {**out, 'state': 'blocked', 'reason': f"the workspace is on metamodel {', '.join(old)}; this SDEM uses {current} — migrate it before building its graph",
                    'command': f'sdem migrate --workspace {q(ws)} --person <you> --dry-run'}
        from .connect import estate_docs, estate_errors
        docs, reg = estate_docs(ws)
        errors = estate_errors(docs, reg)
        if errors:
            return {**out, 'state': 'blocked', 'reason': f'{len(errors)} check error(s) — a graph is built only from a workspace that passes its checks; e.g. {errors[0][:140]}',
                    'command': f'sdem check --workspace {q(ws)}'}
        if not store:
            return {**out, 'state': 'missing', 'reason': 'no graph has been built for this workspace', 'command': build_cmd}
        try: build, changed = stale_inputs(store)
        except (StoreError, OSError, ValueError) as e:
            return {**out, 'state': 'missing', 'reason': f'the graph store cannot be read ({e})', 'command': build_cmd}
        from .store import _load_record
        last = next((e for e in reversed(_load_record(store)['entries']) if e.get('result') == 'accepted'), None) or {}
        built_from = {Path(i['path']).name for i in last.get('inputs', []) if isinstance(i, dict)}
        new = sorted(f.name for f in files if f.name not in built_from)
        out['build'] = build
        if changed or new:
            what = ', '.join([Path(c).name for c in changed] + [f'{n} (new)' for n in new])
            return {**out, 'state': 'stale', 'reason': f'built (build {build}) before the workspace changed: {what}', 'command': build_cmd}
        return {**out, 'state': 'current', 'reason': f'current — build {build}', 'command': None}
    finally:
        _p.deactivate()


def graph_link(state, from_file, view_file):
    """NV-02, NV-04: what a page shows for the architecture graph — a link when the graph is current and its viewer shows the current
    build; otherwise the state, the reason and the command(s)."""
    q = lambda p: shlex.quote(Path(p).as_posix())
    if state['state'] != 'current':
        return {'state': state['state'], 'href': None, 'reason': state['reason'], 'commands': [state['command']] + ([f"sdem view --graph {q(state['store'])}"] if state['state'] != 'blocked' else [])}
    vb = view_build(view_file)
    if vb != state['build']:
        why = 'the graph viewer has not been generated' if not Path(view_file).exists() else f"the graph viewer shows {'an earlier build' if vb else 'an unknown build'}; the graph is at build {state['build']}"
        return {'state': 'viewer_missing' if not Path(view_file).exists() else 'viewer_stale', 'href': None, 'reason': why,
                'commands': [f"sdem view --graph {q(state['store'])}" + (f' -o {q(view_file)}' if Path(view_file).resolve() != (Path(state['store']) / 'view.html').resolve() else '')]}
    return {'state': 'current', 'href': href(from_file, view_file), 'reason': state['reason'], 'commands': []}
