"""The 0.22 plan, step 3c (proof P1): `sdem aid` from scratch on every 0.20 example, in two scenarios — (a) business only: every other
layer and every approved link removed; (b) without BIAN: the BIAN layer and the links that touch it removed — and what it writes:
the run record, every layer file and its proposals, normalised (times, dates and the temporary folder taken out).
Usage: python scripts/golden/aid_scratch.py <SDEM checkout> <out-dir>   (set PATH to include an installed sdem-bian, or not)"""
import json, os, re, shutil, subprocess, sys, tempfile, pathlib
root, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
VOL = re.compile(r'^(at|confirmed_at|model_version|generated_at|recorded_at|created|date|frozen_at)$')
def norm(x, tmp):
    if isinstance(x, dict): return {k: ('<volatile>' if VOL.match(k) else norm(v, tmp)) for k, v in x.items()}
    if isinstance(x, list): return [norm(v, tmp) for v in x]
    if isinstance(x, str): return x.replace(str(tmp), '<tmp>')
    return x
LAYERS = ('business.json', 'bian.json', 'data.json', 'application.json', 'technology.json')
for ex in sorted((root / 'examples' / '0.20').iterdir()):
    src = ex / 'sdem' if (ex / 'sdem' / 'mappings.json').exists() else ex
    if not (src / 'mappings.json').exists() or not (src / 'business.json').exists(): continue
    for scen in ('a', 'b'):
        t = pathlib.Path(tempfile.mkdtemp()); ws = t / 'ws'; shutil.copytree(src, ws)
        shutil.rmtree(ws / 'aid', ignore_errors=True)
        m = json.loads((ws / 'mappings.json').read_text(encoding='utf-8'))
        keep = lambda r: True
        if scen == 'a':
            for f in LAYERS[1:]:
                if (ws / f).exists():
                    d = json.loads((ws / f).read_text(encoding='utf-8')); d['instances'] = []; d['relationships'] = []; (ws / f).write_text(json.dumps(d), encoding='utf-8')
            m['mappings'] = []
        else:
            if not (ws / 'bian.json').exists(): shutil.rmtree(t, ignore_errors=True); continue
            b = json.loads((ws / 'bian.json').read_text(encoding='utf-8')); gone = {i['id'] for i in b.get('instances', [])}
            b['instances'] = []; b['relationships'] = []; (ws / 'bian.json').write_text(json.dumps(b), encoding='utf-8')
            m['mappings'] = [x for x in m['mappings'] if x['source']['id'] not in gone and x['target']['id'] not in gone]
        (ws / 'mappings.json').write_text(json.dumps(m), encoding='utf-8')
        env = {**os.environ, 'PYTHONPATH': str(root), 'PYTHONIOENCODING': 'utf-8', 'SDEM_FORM': '0.20'}
        r = subprocess.run([sys.executable, '-m', 'sdem', 'aid', '--workspace', str(ws), '--person', 'golden.capture', '--json'], capture_output=True, text=True, encoding='utf-8', env=env, cwd=t)
        try: rec = json.loads(r.stdout)
        except ValueError: rec = None
        files = {f: json.loads((ws / f).read_text(encoding='utf-8')) for f in LAYERS if (ws / f).exists()}
        props = {p.name: json.loads(p.read_text(encoding='utf-8')) for p in sorted((ws / 'aid').glob('AID-*-proposals.json'))} if (ws / 'aid').exists() else {}
        doc = norm({'exit': r.returncode, 'record': rec, 'files': files, 'proposals': props, 'stderr_tail': r.stderr.strip()[-300:] if r.returncode else ''}, t)
        (out / f'{ex.name}__{scen}.json').write_text(json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
        n = sum(len(v) for v in (rec or {}).get('added', {}).values()) if rec else None
        print(ex.name, scen, r.returncode, 'added', n, 'proposals', (rec or {}).get('proposed_connections'))
        shutil.rmtree(t, ignore_errors=True)
