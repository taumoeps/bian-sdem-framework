"""The 0.22 plan, step 3b (proof P1): sdem link from scratch on every 0.20 example: approved links removed, everything re-proposed — the engine's full output, normalised. Usage: python scripts/golden/link_scratch.py <SDEM checkout> <out-dir>"""
import json, shutil, subprocess, sys, tempfile, pathlib
root, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
def _examples_020(root):
    """Every 0.20 example: SDEM's own and an installed extension's (0.22, R-D6: the banking designs are sdem-bian's)."""
    dirs = {}
    sys.path.insert(0, str(root))
    try:
        from sdem.parts import example_roots
        roots = example_roots()
    except Exception: roots = [root / 'examples']
    for r in [root / 'examples', *roots]:
        if (r / '0.20').is_dir():
            for d in (r / '0.20').iterdir(): dirs.setdefault(d.name, d)
    return [dirs[k] for k in sorted(dirs)]
for ex in _examples_020(root):
    src = ex / 'sdem' if (ex / 'sdem' / 'mappings.json').exists() else ex
    if not (src / 'mappings.json').exists(): continue
    t = pathlib.Path(tempfile.mkdtemp()); ws = t / 'ws'; shutil.copytree(src, ws)
    m = json.loads((ws / 'mappings.json').read_text()); m['mappings'] = []; (ws / 'mappings.json').write_text(json.dumps(m))
    env = {'PYTHONPATH': str(root), 'PYTHONIOENCODING': 'utf-8', 'PATH': '/usr/bin:/bin', 'SDEM_FORM': '0.20'}
    r = subprocess.run([sys.executable, '-m', 'sdem', 'link', '--workspace', str(ws), '--out', str(t / 'links'), '--no-review'], capture_output=True, text=True, env=env, cwd=t)
    pf = t / 'links' / 'proposals.json'
    props = json.loads(pf.read_text())['mappings'] if pf.exists() else None
    (out / f'{ex.name}.json').write_text(json.dumps({'exit': r.returncode, 'proposals': props, 'stderr_tail': r.stderr.strip()[-300:] if r.returncode else ''}, indent=1, sort_keys=True))
    print(ex.name, r.returncode, None if props is None else len(props))
    shutil.rmtree(t, ignore_errors=True)
