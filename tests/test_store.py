"""Local JSON graph store (docs/design/graph-store-spec.md): acceptance tests AT-01 … AT-10."""
import glob, json, re, shutil, tempfile, unittest
from pathlib import Path

from sdem import store
from sdem.store import GraphReader, build, check_current
from sdem.validate import check_schema

ROOT = Path(__file__).resolve().parents[1]
ESTATES = sorted(p.name for p in (ROOT / 'examples').iterdir() if (p / 'mappings.json').exists())   # p.name: works with \ paths (Windows)
GRAPH_FILES = list(store.LEVEL_FILES.values()) + [store.FEDERATED]


def expected_files(estate):
    lv = {json.loads(Path(p).read_text(encoding='utf-8')).get('level') for p in inputs(estate)}
    return [f for l, f in store.LEVEL_FILES.items() if l in lv] + [store.FEDERATED]


def inputs(estate):
    e = ROOT / 'examples' / estate
    return sorted(str(p) for p in e.glob('a[1-4]-*.json')) + [str(e / 'mappings.json')]


class StoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix='sdem-store-test-'))
        cls.entries = {e: build(inputs(e), cls.tmp / e, now='2026-10-25T00:00:00+00:00') for e in ESTATES}
        cls.profile = json.loads((ROOT / 'schema' / 'graph-store.schema.json').read_text(encoding='utf-8'))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_at01_every_estate_builds(self):
        for e, entry in self.entries.items():
            self.assertEqual(entry['result'], 'accepted', f'{e}: {entry["errors"][:3]}')
            self.assertEqual(sorted(p.name for p in (self.tmp / e).glob('*.json')), sorted(expected_files(e) + [store.LOAD_RECORD]), e)

    def test_at02_files_are_jgf_and_sdem_profile(self):
        for e in ESTATES:
            for f in expected_files(e):
                g = json.loads((self.tmp / e / f).read_text(encoding='utf-8'))
                self.assertEqual(check_schema(g, self.profile), [], f'{e} {f}')
                self.assertEqual(set(g), {'graph'})  # JGF: single-graph variant
                self.assertTrue(set(g['graph']) <= {'id', 'label', 'directed', 'type', 'metadata', 'nodes', 'edges'})
                for k, n in g['graph']['nodes'].items():
                    self.assertTrue(set(n) <= {'label', 'metadata'}, k)  # JGF node: no other properties
                    self.assertEqual(check_schema(n, self.profile['$defs']['node'], self.profile), [], k)
                for x in g['graph']['edges']:
                    self.assertTrue(set(x) <= {'id', 'source', 'target', 'relation', 'directed', 'label', 'metadata'})
                    self.assertIn(x['source'], g['graph']['nodes']); self.assertIn(x['target'], g['graph']['nodes'])

    def test_at03_round_trip(self):
        for e in ESTATES:
            r = GraphReader.from_store(self.tmp / e)
            for p in inputs(e):
                d = json.loads(Path(p).read_text(encoding='utf-8'))
                if 'mappings' in d:
                    want = sorted(json.dumps(m, sort_keys=True) for m in d['mappings'] if m['status'] == 'approved')
                    got = sorted(json.dumps(m, sort_keys=True) for doc in r.fg.mapping_docs for m in doc['mappings'])
                    self.assertEqual(got, want, f'{e} registry')
                else:
                    g = r.fg.levels[d['level']].doc
                    self.assertEqual(g['instances'], d['instances'], f'{e} {d["level"]} instances')
                    self.assertEqual(g['relationships'], d.get('relationships', []), f'{e} {d["level"]} relationships')
                    for k in store.EXPORT_HEADER:
                        if k in d: self.assertEqual(g[k], d[k])

    def test_at04_answers_identical_from_store_and_exports(self):
        for e in ESTATES:
            a, b = GraphReader.from_exports(inputs(e)), GraphReader.from_store(self.tmp / e)
            for n in a.nodes():
                for d in ('down', 'up'):
                    for fc in (False, True):
                        self.assertEqual(a.fg.trace(n['id'], d, follow_composition=fc), b.fg.trace(n['id'], d, follow_composition=fc), f"{e} {n['id']} {d} {fc}")
                for k in ('modify', 'replace', 'retire', 'rehost'):
                    self.assertEqual(a.fg.impact(n['id'], k), b.fg.impact(n['id'], k), f"{e} {n['id']} {k}")
            self.assertEqual(b.baseline()['build'], 1); self.assertEqual(b.baseline()['origin'], 'store')
            self.assertEqual(b.check_store(self.tmp / e), {k: [] for k in b.check_store(self.tmp / e)}, e)

    def test_at05_failed_build_keeps_the_last_good_store(self):
        out = self.tmp / 'at05'; build(inputs('payment-initiation'), out)
        before = {f: (out / f).read_bytes() for f in GRAPH_FILES}
        bad = self.tmp / 'at05-bad'; bad.mkdir()
        for p in inputs('payment-initiation'):
            d = json.loads(Path(p).read_text(encoding='utf-8'))
            if d.get('level') == 'A1':
                d['instances'][0]['lifecycle_status'] = 'live'  # not an allowed value (LC-06)
            (bad / Path(p).name).write_text(json.dumps(d), encoding='utf-8')
        entry = build(sorted(str(p) for p in bad.glob('*.json')), out)
        self.assertEqual(entry['result'], 'rejected'); self.assertTrue(any('lifecycle_status' in x for x in entry['errors']), entry['errors'])
        self.assertEqual({f: (out / f).read_bytes() for f in GRAPH_FILES}, before)
        rec = json.loads((out / store.LOAD_RECORD).read_text(encoding='utf-8'))
        self.assertEqual([x['result'] for x in rec['entries']], ['accepted', 'rejected'])
        # an approved link that does not resolve is also rejected
        reg = json.loads((bad / 'mappings.json').read_text(encoding='utf-8')); reg['mappings'][0]['target']['id'] = 'NOT-THERE'
        good = self.tmp / 'at05-unres'; good.mkdir()
        for p in inputs('payment-initiation'): shutil.copy(p, good / Path(p).name)
        (good / 'mappings.json').write_text(json.dumps(reg), encoding='utf-8')
        self.assertEqual(build(sorted(str(p) for p in good.glob('*.json')), out)['result'], 'rejected')
        self.assertEqual({f: (out / f).read_bytes() for f in GRAPH_FILES}, before)

    def test_at06_deterministic(self):
        out = self.tmp / 'at06'; build(inputs('trade-finance'), out); first = {f: (out / f).read_bytes() for f in GRAPH_FILES}
        build(inputs('trade-finance'), out)
        self.assertEqual({f: (out / f).read_bytes() for f in GRAPH_FILES}, first)
        self.assertEqual(len(json.loads((out / store.LOAD_RECORD).read_text(encoding='utf-8'))['entries']), 2)
        for f in GRAPH_FILES: self.assertNotIn('2026-10-25T', first[f].decode('utf-8'))  # no build timestamp inside graph files

    def test_at07_check_current(self):
        out = self.tmp / 'at07'; build(inputs('payment-initiation'), out)
        self.assertTrue(check_current(inputs('payment-initiation'), out)[0])
        (out / 'a4-technology.graph.json').write_text('{}', encoding='utf-8')
        ok, stale = check_current(inputs('payment-initiation'), out)
        self.assertFalse(ok); self.assertIn('a4-technology.graph.json', stale)

    def test_at08_baseline(self):
        out = self.tmp / 'at08'; build(inputs('payment-initiation'), out)
        store.baseline(out, 'q4')
        with self.assertRaises(store.StoreError): store.baseline(out, 'q4')
        changed = self.tmp / 'at08-src'; changed.mkdir()
        for p in inputs('payment-initiation'): shutil.copy(p, changed / Path(p).name)
        a1 = json.loads((changed / 'a1-business.json').read_text(encoding='utf-8'))
        for i in a1['instances']:
            if i['id'] == 'PRC-PAY-01': i['name'] = 'Capture payment (renamed)'
        (changed / 'a1-business.json').write_text(json.dumps(a1), encoding='utf-8')
        self.assertEqual(build(sorted(str(p) for p in changed.glob('*.json')), out)['result'], 'accepted')
        self.assertEqual(GraphReader.from_store(out).node('A1', 'PRC-PAY-01')['name'], 'Capture payment (renamed)')
        self.assertEqual(GraphReader.from_store(out / 'baselines' / 'q4').node('A1', 'PRC-PAY-01')['name'], 'Capture and validate payment instruction')

    def test_at09_queries(self):
        r = GraphReader.from_store(self.tmp / 'payment-initiation')
        self.assertEqual([n['id'] for n in r.nodes(type='A1.BusinessProcess', where={'criticality': 'high'})], ['PRC-PAY-01', 'PRC-PAY-02'])
        self.assertEqual(len(r.nodes(type='A1.BusinessProcess')), 6)  # subtypes included: 2 processes + 4 activities
        self.assertEqual([n['id'] for n in r.nodes(level='A3', where={'personal_information': 'true'})], ['ENT-PAY-INSTR', 'ENT-ACCOUNT-CACHE'])
        self.assertIn({'direction': 'out', 'relation': 'composition', 'id': 'ACT-PAY-01a'}, r.neighbours('PRC-PAY-01'))
        self.assertEqual(r.neighbours('PRC-PAY-01', relation='realization'), [{'direction': 'out', 'relation': 'realization', 'id': 'CAP-PAY-010'}])
        # unmapped: hand count — A2 records with no approved cross-level link of any type the catalogue expects for them
        self.assertEqual(sorted(n['id'] for n in r.unmapped('A2')), ['BBO-PARTY', 'SD-PA', 'SD-PE', 'SO-PI-06'])
        self.assertEqual(sorted(n['id'] for n in GraphReader.from_store(self.tmp / 'legacy-core-ledger').unmapped('A4')),
                         sorted(n['id'] for n in GraphReader.from_exports(inputs('legacy-core-ledger')).unmapped('A4')))

    def test_at10_view_is_self_contained(self):
        from sdem.view import render
        for e in ESTATES:
            page = render(self.tmp / e)
            data = json.loads(re.search(r'const D=(\{.*?\});const NS', page, re.S).group(1).replace('<\\/', '</'))
            r = GraphReader.from_store(self.tmp / e)
            self.assertEqual(len(data['nodes']), len(r.nodes()), e)
            self.assertEqual(len(data['edges']), len(r.edges('within-level')) + len(r.edges('cross-level')), e)
            self.assertNotRegex(page, r'<(script|link)[^>]+(src|href)=', e)  # nothing loaded from elsewhere

    def test_cli(self):
        import contextlib, io
        from sdem.graph import main as _main
        def main(argv):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                return _main(argv)
        out = self.tmp / 'cli'; p = inputs('payment-initiation')
        self.assertEqual(main(['build', *p, '--out', str(out)]), 0)
        self.assertEqual(main(['build', *p, '--out', str(out), '--check']), 0)
        self.assertEqual(main(['check', '--graph', str(out)]), 0)
        self.assertEqual(main(['trace', 'CAP-PAY-010', '--graph', str(out)]), 0)
        self.assertEqual(main(['query', '--graph', str(out), '--unmapped', 'A2']), 0)
        self.assertEqual(main(['trace', 'CAP-PAY-010', '--graph', str(out), '--status', 'proposed']), 2)
        self.assertEqual(main(['trace', 'CAP-PAY-010', *p, '--graph', str(out)]), 2)


if __name__ == '__main__':
    unittest.main()
