"""Golden outputs (BX-30): what SDEM says about the examples, normalised (no times, ids of runs, local paths), so a later version can
be compared with it command by command. Run from a checkout:  python scripts/golden/capture.py <out-dir>
Synthetic data only — SDEM's own examples."""
import json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(os.environ.get('SDEM_GOLDEN_ROOT') or Path(__file__).resolve().parents[2])   # SDEM_GOLDEN_ROOT: capture another checkout, e.g. v0.19.0 (BP-D5)
ENV = {**os.environ, 'PYTHONPATH': str(ROOT), 'PYTHONIOENCODING': 'utf-8'}   # SDEM writes UTF-8 on every platform
_HAS_FORM = "'--form'" in (ROOT / 'sdem' / 'new.py').read_text(encoding='utf-8')   # a checkout from before 0.20 (v0.19.0) has no --form
FORM = (['--form', '0.20'] if os.environ.get('SDEM_GOLDEN_P2') == '1' else ['--form', '0.19']) if _HAS_FORM else []   # P1: 0.19's answers, whatever the default (DL-D9)
if os.environ.get('SDEM_GOLDEN_P2') != '1': ENV['SDEM_FORM'] = '0.19'
if os.environ.get('SDEM_GOLDEN_P2') == '1' and (ROOT / 'examples' / '0.20').is_dir():   # P2: the 0.20 form, opted in (DL-D9), from the migrated example
    ENV.update({'SDEM_FORM': '0.20', 'SDEM_EXAMPLES': str(ROOT / 'examples' / '0.20')})
VOLATILE = re.compile(r'^(at|generated_at|written_at|recorded_at|started_at|ended_at|built_at|date|created|timestamp|now|as_of|run_id|id_run|fingerprint|duration_ms|seconds|elapsed)$')


def sdem(*args, cwd=None):
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], capture_output=True, text=True, encoding='utf-8', errors='replace', env=ENV, cwd=cwd or ROOT)
    return r.returncode, r.stdout, r.stderr


def norm(x, tmp):
    if isinstance(x, dict): return {k: ('<volatile>' if VOLATILE.match(k) else norm(v, tmp)) for k, v in x.items() if k != 'sdem'}
    if isinstance(x, list): return [norm(v, tmp) for v in x]
    if isinstance(x, str):
        for p, tag in ((tmp, '<tmp>'), (ROOT, '<root>')):   # every spelling of the folder: as given, resolved, and with / (Windows)
            for form in sorted({str(p), str(Path(p).resolve()), os.path.realpath(p)}, key=len, reverse=True):   # the longest first
                x = x.replace(form, tag).replace(form.replace('\\', '/'), tag)
        if os.sep == '\\': x = re.sub(r'(<tmp>|<root>)([^\s"]*)', lambda m: m.group(1) + m.group(2).replace('\\', '/'), x)   # paths under them in / form
        if P2:   # the migrated workspaces' file names, as 0.19's
            for old, new in RENAME.items(): x = re.sub(rf'(?<![\w-]){re.escape(new)}', old, x)
        if IDS:
            x = x.replace('<tmp>/ds/', '<root>/examples/')   # the detector's copies of the dataset examples
            for old, new in RENAME.items(): x = re.sub(rf'(?<![\w-]){re.escape(new)}', old, x)   # the migrated workspaces' file names, as 0.19's
        return re.sub(r'GD-\d{8}T\d{6}-[0-9a-f]{6}', 'GD-<id>', re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[^"\s]*', '<time>', x))
    return x


IDS = os.environ.get('SDEM_GOLDEN_IDS') == '1'
P2 = os.environ.get('SDEM_GOLDEN_P2') == '1'   # DL-20: the golden workspaces migrated to 0.20 (sdem migrate --to 0.20) — answers compared after translation
LAYER_0_19 = {'A1': 'business', 'A2': 'bian', 'A3': 'application', 'A4': 'technology'}
RENAME = {'a1-business.json': 'business.json', 'a2-service-domain.json': 'bian.json', 'a3-application.json': 'application.json', 'a4-technology.json': 'technology.json'}   # DL-11's detector: the same answers from workspaces whose files store type ids


def to_ids(folder):
    """Every design file in `folder` as a migrated workspace stores it (type ids, layer ids) — graph stores left as built."""
    sys.path.insert(0, str(ROOT))
    from sdem.identity import store_names, read_names, _derived
    from sdem.files import record, TRACKED
    done = []
    for f in Path(folder).rglob('*.json'):
        if _derived(f): continue
        try: d = json.loads(f.read_text(encoding='utf-8'))
        except ValueError: continue
        if f.name == 'workspace.json': d['names'] = 'ids'
        f.write_bytes((json.dumps(store_names(read_names(d), True), indent=2, ensure_ascii=False) + '\n').encode('utf-8'))
        new = f.with_name(RENAME[f.name]) if f.name in RENAME and (f.parent / 'workspace.json').exists() else f   # DL-10: named by layer id
        if new != f: f.rename(new)
        if new.name in TRACKED or f.name in TRACKED: done.append(new)
    if done and (Path(folder) / 'sdem-ledger.json').exists():   # as the migration does (DL-12): SDEM's own edit, recorded — in the migrated form
        from sdem import parts
        parts._set_form(True)
        try: record(done)
        finally: parts._set_form(False)


def now(code):
    """A 0.19 layer code as a migrated workspace with BIAN reads it (A3 Application → A4)."""
    return {'A1': 'A1', 'A2': 'A2', 'A3': 'A4', 'A4': 'A5'}[code]


def capture(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix='sdem-golden-'))
    try:
        cases = {}
        ws = tmp / 'pi'
        sdem('new', '--workspace', ws, '--person', 'golden.check', '--example', 'payment-initiation', *FORM)
        v3 = tmp / 'v3'; shutil.copytree(ROOT / 'examples' / 'payment-initiation-v3' / 'sdem', v3, ignore=shutil.ignore_patterns('graph', 'links', 'aid'))
        if IDS: to_ids(ws); to_ids(v3)
        if P2:   # the example is in the 0.20 form already (DL-D9); the second workspace is migrated
            for w in (v3,):
                code, so, se = sdem('migrate', '--workspace', w, '--person', 'golden.check', '--to', '0.20')
                assert code == 0, se
        for name, w in (('payment-initiation', ws), ('payment-initiation-v3', v3)):
            cases[f'{name}/check'] = ('check', '--workspace', w, '--json')
            cases[f'{name}/comply'] = ('comply', '--workspace', w, '--json')
            cases[f'{name}/status'] = ('status', '--workspace', w, '--json')
            cases[f'{name}/aid'] = ('aid', '--workspace', w, '--person', 'golden.check', '--dry-run', '--json')
            cases[f'{name}/link'] = ('link', '--workspace', w, '--out', tmp / f'{name}-links', '--json')
            for L in ('A1', 'A2', 'A3', 'A4'): cases[f'{name}/document-{L}'] = ('document', '--workspace', w, '--layer', now(L) if P2 else L, '--json')
            cases[f'{name}/build'] = ('build', '--workspace', w, '--out', tmp / f'{name}-graph', '--json')
        for L in ('A1', 'A2', 'A3', 'A4'): cases[f'types/{L}'] = ('types', now(L) if P2 else L, '--json')
        cases['trace/pi-A1'] = ('trace', 'A1', '--graph', tmp / 'payment-initiation-graph', '--json')
        cases['impact/pi-APP'] = ('impact', 'APP-PAY-HUB', '--change', 'retire', '--graph', tmp / 'payment-initiation-graph', '--json')
        cases['bian/search'] = ('bian', 'search', 'payment', 'order', '--json')
        nb = tmp / 'nb'; sdem('new', '--workspace', nb, '--person', 'golden.check', '--no-bian', *FORM)   # BP-D5: sdem bian add, before BIAN's code moves
        if IDS: to_ids(nb)
        cases['bian/add-pi'] = ('bian', 'add', 'Card Authorization', '--workspace', ws, '--person', 'golden.check', '--dry-run', '--json')
        cases['bian/add-new'] = ('bian', 'add', 'Payment Rail', 'Party Reference Data Directory', '--workspace', nb, '--person', 'golden.check', '--dry-run', '--json')
        for d in ('card-fraud-alerts', 'digital-lending', 'legacy-core-ledger'):
            ex = ROOT / 'examples' / d
            if IDS: shutil.copytree(ex, tmp / 'ds' / d); to_ids(tmp / 'ds' / d); ex = tmp / 'ds' / d
            files = sorted(str(p) for p in ex.glob('a[1-4]-*.json')) + [str(ex / 'mappings.json')]
            cases[f'datasets/{d}/check'] = ('check', *files, '--json')
        for key, args in cases.items():
            code, so, se = sdem(*args)
            try: body = norm(json.loads(so), tmp)
            except ValueError: body = {'text': norm(so.strip()[-4000:], tmp)}
            f = out / (key.replace('/', '__') + '.json')
            f.write_bytes((json.dumps({'command': norm([str(a) for a in args], tmp), 'exit': code, 'output': body}, indent=1, sort_keys=True, ensure_ascii=False) + '\n').encode('utf-8'))   # LF on every platform
        return sorted(cases)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    print('\n'.join(capture(sys.argv[1] if len(sys.argv) > 1 else ROOT / 'tests' / 'golden' / '0.19')))
