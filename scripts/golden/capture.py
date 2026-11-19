"""Golden outputs (BX-30): what SDEM says about the examples, normalised (no times, ids of runs, local paths), so a later version can
be compared with it command by command. Run from a checkout:  python scripts/golden/capture.py <out-dir>
Synthetic data only — SDEM's own examples."""
import json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV = {**os.environ, 'PYTHONPATH': str(ROOT)}
VOLATILE = re.compile(r'^(at|generated_at|written_at|recorded_at|started_at|ended_at|built_at|date|created|timestamp|now|as_of|run_id|id_run|fingerprint|duration_ms|seconds|elapsed)$')


def sdem(*args, cwd=None):
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], capture_output=True, text=True, env=ENV, cwd=cwd or ROOT)
    return r.returncode, r.stdout, r.stderr


def norm(x, tmp):
    if isinstance(x, dict): return {k: ('<volatile>' if VOLATILE.match(k) else norm(v, tmp)) for k, v in x.items() if k != 'sdem'}
    if isinstance(x, list): return [norm(v, tmp) for v in x]
    if isinstance(x, str):
        x = x.replace(str(tmp), '<tmp>').replace(str(ROOT), '<root>')
        return re.sub(r'GD-\d{8}T\d{6}-[0-9a-f]{6}', 'GD-<id>', re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[^"\s]*', '<time>', x))
    return x


def capture(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix='sdem-golden-'))
    try:
        cases = {}
        ws = tmp / 'pi'
        sdem('new', '--workspace', ws, '--person', 'golden.check', '--example', 'payment-initiation')
        v3 = tmp / 'v3'; shutil.copytree(ROOT / 'examples' / 'payment-initiation-v3' / 'sdem', v3, ignore=shutil.ignore_patterns('graph', 'links', 'aid'))
        for name, w in (('payment-initiation', ws), ('payment-initiation-v3', v3)):
            cases[f'{name}/check'] = ('check', '--workspace', w, '--json')
            cases[f'{name}/comply'] = ('comply', '--workspace', w, '--json')
            cases[f'{name}/status'] = ('status', '--workspace', w, '--json')
            cases[f'{name}/aid'] = ('aid', '--workspace', w, '--person', 'golden.check', '--dry-run', '--json')
            cases[f'{name}/link'] = ('link', '--workspace', w, '--out', tmp / f'{name}-links', '--json')
            for L in ('A1', 'A2', 'A3', 'A4'): cases[f'{name}/document-{L}'] = ('document', '--workspace', w, '--layer', L, '--json')
            cases[f'{name}/build'] = ('build', '--workspace', w, '--out', tmp / f'{name}-graph', '--json')
        for L in ('A1', 'A2', 'A3', 'A4'): cases[f'types/{L}'] = ('types', L, '--json')
        cases['trace/pi-A1'] = ('trace', 'A1', '--graph', tmp / 'payment-initiation-graph', '--json')
        cases['impact/pi-APP'] = ('impact', 'APP-PAY-HUB', '--change', 'retire', '--graph', tmp / 'payment-initiation-graph', '--json')
        cases['bian/search'] = ('bian', 'search', 'payment', 'order', '--json')
        for d in ('card-fraud-alerts', 'digital-lending', 'legacy-core-ledger'):
            ex = ROOT / 'examples' / d
            files = sorted(str(p) for p in ex.glob('a[1-4]-*.json')) + [str(ex / 'mappings.json')]
            cases[f'datasets/{d}/check'] = ('check', *files, '--json')
        for key, args in cases.items():
            code, so, se = sdem(*args)
            try: body = norm(json.loads(so), tmp)
            except ValueError: body = {'text': norm(so.strip()[-4000:], tmp)}
            f = out / (key.replace('/', '__') + '.json')
            f.write_text(json.dumps({'command': norm([str(a) for a in args], tmp), 'exit': code, 'output': body}, indent=1, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
        return sorted(cases)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    print('\n'.join(capture(sys.argv[1] if len(sys.argv) > 1 else ROOT / 'tests' / 'golden' / '0.19')))
