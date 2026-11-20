"""Step 4 of 0.20 — the Data layer (docs/design/sdem-data-layer-spec.md, DL-01…DL-24). 4b: a design's files store ids or 0.19's
names; SDEM reads and writes both through one boundary (sdem/identity.py: load, loads, for_file), and works in the names a person reads."""
import json, os, re, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'scripts' / 'golden'))
ENV = {**os.environ, 'PYTHONPATH': str(ROOT), 'PYTHONIOENCODING': 'utf-8'}
OLD = re.compile(r'"(A[1-4]\.[A-Z][A-Za-z]+)"')


def sdem(*args):
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], capture_output=True, text=True, encoding='utf-8', env=ENV, cwd=ROOT)
    assert r.returncode == 0, f"sdem {' '.join(map(str, args))}: exit {r.returncode}\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}"
    return r.stdout


def no_sha(x, k=None):
    if isinstance(x, dict): return {kk: no_sha(v, kk) for kk, v in x.items()}
    if isinstance(x, list): return sorted(map(str, x)) if k == 'would_write' else [no_sha(v, k) for v in x]   # a migrated workspace's files sort differently
    return '<sha>' if k in ('sha256', 'export_sha256') else x


# P2 (DL-20): 0.19's 32 answers, translated to a migrated workspace's numbering (with BIAN: Data A3, Application A4, Technology A5),
# against the answers of the golden workspaces migrated with sdem migrate --to 0.20. These differences — and only these — are the
# Data layer itself; each is named with its reason. Commands without a workspace keep 0.19's form and are compared untranslated.
NAMED = {
    'check': {'.output.report.level A3 (*)': 'the Data layer is checked on its own', '.output.warnings.level A4 (*)': "warnings about data records move to Data's level"},
    'build': {'.output.inputs': 'data.json is read too', '.output.outputs': 'data.graph.json is written too', '.output.stack': 'the store records the layers it was built with (DL-12)',
              '.output.warnings': "warnings about data records move to Data's level"},
    'status': {'.output.layers': 'five layers', '.output.connections.by_status.approved': "0.19's access links are approved links between Data and Application (DL-13)",
               '.output.connections.links': 'the same', '.output.counts.warnings': "warnings about data records move to Data's level", '.output.warnings': 'the same',
               '.output.sources.links_without_source': 'the access links left the layer file (DL-13)'},
    'document-A3': {'.output.sections': 'Application no longer holds the data entities', '.output.summary.*': 'the same', '.output.gaps.no_connection': 'the same'},
    'comply': {'.output.findings[].layer': "findings about data records are in Data's layer", '.output.findings[].detail': "'access link(s)' is 'ACCESSED_BY link(s)' (DL-04)"},
    'aid': {'.output.added.A3': "inferred data records are added to Data", '.output.added.A4': 'the same', '.output.would_write[]': 'data.json among the files, in another order'},
    'trace': {'.output.items[].chains': 'the access links between Data and Application add chains', '.output.items[].reach.A3': 'trace reaches Data', '.output.items[].reach.A5': 'and through it'},
    'impact': {'.output.coverage.A3': 'impact is seen on Data', '.output.coverage.A4.*': "Application's coverage without the data records"},
}


def named(fname, path):
    kind = next((k for k in NAMED if fname.split('__')[-1].startswith(k) or fname.startswith(k + '__')), None)
    if not kind: return None
    import fnmatch
    p = re.sub(r'\[\d+\]', '[]', path)
    return next((why for pat, why in NAMED[kind].items() if fnmatch.fnmatchcase(p, pat) or fnmatch.fnmatchcase(p, pat.replace('[]', '[[]]'))), None)


def tr(x):
    """A 0.19 answer as a migrated workspace with BIAN numbers it: data types stay A3; other A3 are A4, A4 are A5."""
    data = {'A3.DataEntity', 'A3.DataAttribute'}
    def s(v):
        v = re.sub(r'(?<![A-Za-z0-9_.\-])A([34])\.([A-Z][A-Za-z]+)', lambda m: m.group(0) if m.group(0) in data else f'A{int(m.group(1)) + 1}.{m.group(2)}', v)
        return re.sub(r'(?<![A-Za-z0-9_.\-])A([34])(?![A-Za-z0-9_.\-])', lambda m: f'A{int(m.group(1)) + 1}', v)
    if isinstance(x, dict): return {s(k): tr(v) for k, v in x.items()}
    if isinstance(x, list): return [tr(v) for v in x]
    return s(x) if isinstance(x, str) else x


def diffs(a, b, p=''):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            if k not in a or k not in b: yield f'{p}.{k}'
            else: yield from diffs(a[k], b[k], f'{p}.{k}')
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (u, v) in enumerate(zip(a, b)): yield from diffs(u, v, f'{p}[{i}]')
    elif a != b and not p.endswith('sha256'): yield p


class Boundary(unittest.TestCase):   # DL-10…DL-13, DL-20
    def test_p2_the_32_answers_of_0_19_translated_differ_only_where_named(self):
        out = Path(tempfile.mkdtemp())
        try:
            subprocess.run([sys.executable, str(ROOT / 'scripts' / 'golden' / 'capture.py'), str(out)], check=True, capture_output=True,
                           env={**ENV, 'SDEM_GOLDEN_P2': '1'}, cwd=ROOT)
            gold = ROOT / 'tests' / 'golden' / '0.19'
            unnamed = {}
            for f in sorted(gold.glob('*.json')):
                raw = json.loads(f.read_text(encoding='utf-8'))
                a = raw if f.name.startswith(('types__', 'datasets__', 'bian__search')) else tr(raw)   # without a workspace: 0.19's form
                b = json.loads((out / f.name).read_text(encoding='utf-8'))
                left = [p for p in diffs(a, b) if not named(f.name.replace('.json', ''), p)]
                if left: unnamed[f.name] = left[:5]
            self.assertEqual(unnamed, {}, 'a difference from 0.19 the Data layer does not explain — name it (DL-20) or fix it')
        finally:
            shutil.rmtree(out, ignore_errors=True)

    def test_a_migrated_workspace_is_never_written_with_0_19_names(self):   # every writer through the boundary (DL-11)
        tmp = Path(tempfile.mkdtemp()); w = tmp / 'ws'
        try:
            sdem('new', '--workspace', w, '--person', 'dl.check', '--example', 'payment-initiation')
            sdem('migrate', '--workspace', w, '--person', 'dl.check', '--to', '0.20')
            sdem('bian', 'add', 'Card Authorization', '--workspace', w, '--person', 'dl.check')
            sdem('aid', '--workspace', w, '--person', 'dl.check')
            sdem('link', '--workspace', w, '--out', w / 'links')
            sdem('check', '--workspace', w)
            left = {str(f.relative_to(w)): OLD.findall(f.read_text(encoding='utf-8'))[:2] for f in w.rglob('*.json')
                    if not f.name.endswith('.graph.json') and 'graph' not in f.parts and '.sdem-backup-0.20' not in f.parts and OLD.search(f.read_text(encoding='utf-8'))}
            self.assertEqual(left, {})
            self.assertIn('"data.DataEntity"', (w / 'data.json').read_text(encoding='utf-8'))   # DL-01, DL-10
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_migrate_then_roll_back_restores_every_byte(self):   # DL-12
        import filecmp
        tmp = Path(tempfile.mkdtemp()); w = tmp / 'ws'
        try:
            sdem('new', '--workspace', w, '--person', 'dl.check', '--example', 'payment-initiation')
            shutil.copytree(w, tmp / 'orig')
            sdem('migrate', '--workspace', w, '--person', 'dl.check', '--to', '0.20')
            self.assertTrue((w / 'data.json').exists()); self.assertFalse((w / 'a3-application.json').exists())
            sdem('migrate', '--workspace', w, '--person', 'dl.check', '--rollback')
            cmp = filecmp.dircmp(tmp / 'orig', w)
            self.assertEqual((cmp.left_only, cmp.right_only, cmp.diff_files), ([], [], []))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_names_translate_both_ways(self):
        from sdem import identity as I
        doc = {'level': 'A3', 'instances': [{'type': 'A3.ApplicationComponent', 'id': 'X'}], 'layer': 'application'}
        ids = I.store_names(I.read_names(doc), True)
        self.assertEqual(ids, {'level': 'application', 'instances': [{'type': 'application.ApplicationComponent', 'id': 'X'}], 'layer': 'application'})
        self.assertEqual(I.read_names(ids), doc)   # 'layer' is ArchiMate's own word, never translated
        self.assertEqual(I.store_names(I.read_names(ids), False), doc)


if __name__ == '__main__':
    unittest.main()
