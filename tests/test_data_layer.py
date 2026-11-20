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
    if isinstance(x, list): return [no_sha(v) for v in x]
    return '<sha>' if k in ('sha256', 'export_sha256') else x


class Boundary(unittest.TestCase):   # DL-10, DL-11
    def test_the_32_answers_are_the_same_from_files_that_store_ids(self):
        """The detector: every reader through the boundary. Only the build's checksums of its inputs (and of the graph that records
        them) may differ — the files' bytes do."""
        out = Path(tempfile.mkdtemp())
        try:
            subprocess.run([sys.executable, str(ROOT / 'scripts' / 'golden' / 'capture.py'), str(out)], check=True, capture_output=True,
                           env={**ENV, 'SDEM_GOLDEN_IDS': '1'}, cwd=ROOT)
            gold = ROOT / 'tests' / 'golden' / '0.19'
            differ = [f.name for f in sorted(gold.glob('*.json'))
                      if no_sha(json.loads(f.read_text(encoding='utf-8'))) != no_sha(json.loads((out / f.name).read_text(encoding='utf-8')))]
            self.assertEqual(differ, [])
        finally:
            shutil.rmtree(out, ignore_errors=True)

    def test_a_workspace_that_stores_ids_is_never_written_with_names(self):   # every writer through the boundary
        import capture
        tmp = Path(tempfile.mkdtemp()); w = tmp / 'ws'
        try:
            sdem('new', '--workspace', w, '--person', 'dl.check', '--example', 'payment-initiation')
            capture.to_ids(w)
            sdem('bian', 'add', 'Card Authorization', '--workspace', w, '--person', 'dl.check')
            sdem('aid', '--workspace', w, '--person', 'dl.check')
            sdem('link', '--workspace', w, '--out', w / 'links')
            sdem('check', '--workspace', w)
            left = {str(f.relative_to(w)): OLD.findall(f.read_text(encoding='utf-8'))[:2] for f in w.rglob('*.json')
                    if not f.name.endswith('.graph.json') and 'graph' not in f.parts and OLD.search(f.read_text(encoding='utf-8'))}
            self.assertEqual(left, {})
            self.assertIn('"application.ApplicationComponent"', (w / 'a3-application.json').read_text(encoding='utf-8'))
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
