"""Use-case example 4 — importing past designs from a Confluence export to the knowledge graph (docs/evidence/use-case-example-4.md).
Replays Run A on the made-up export and checks every sealed expected result, so the test script and SDEM cannot drift apart."""
import contextlib, io, json, os, re, shutil, tempfile, unittest
from pathlib import Path

from sdem.cli import main

ROOT = Path(__file__).resolve().parents[1]
A2 = ROOT / 'examples' / 'payment-initiation' / 'a2-service-domain.json'
ME = 'jane.architect'


def sdem(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try: code = main([str(a) for a in argv])
        except SystemExit as e: code = e.code
    return code, out.getvalue() + err.getvalue()


class UseCaseExample4(unittest.TestCase):
    """One run, in step order — each test is one step of the document."""
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp()); cls.cwd = os.getcwd(); os.chdir(cls.tmp)
        shutil.copytree(ROOT / 'examples' / 'designs' / 'confluence-folder-export', 'work/imports/payarch')
        cls.out = {}
        for name, argv in [
            ('inspect', ['transform', 'inspect', 'work/imports/payarch', '--ocr', 'off']),
            ('transform', ['transform', 'run', 'work/imports/payarch', '-o', 'work/history', '--ocr', 'off']),
            ('new', ['new', '--workspace', 'workspaces/history', '--person', ME, '--bian', A2]),
            ('dry', ['load', 'work/history', '--workspace', 'workspaces/history', '--person', ME, '--exclude', 'HIS-A3-PAYMENT-ORDER', '--dry-run']),
            ('load', ['load', 'work/history', '--workspace', 'workspaces/history', '--person', ME, '--exclude', 'HIS-A3-PAYMENT-ORDER']),
            ('check', ['check', '--workspace', 'workspaces/history']),
            ('link', ['link', '--workspace', 'workspaces/history', '--out', 'work/links']),
            ('review', ['review', 'work/links/proposals.json']),
            ('approve1', ['approve', 'P-RUN-001', '--proposals', 'work/links/proposals.json', '--workspace', 'workspaces/history', '--reviewer', ME, '--evidence', 'deployment_design:PAYARCH-55501#notes']),
            ('approve5_no_release', ['approve', 'P-RUN-005', '--proposals', 'work/links/proposals.json', '--workspace', 'workspaces/history', '--reviewer', ME,
                                     '--evidence', 'business_architecture_document:PAYARCH-55501#context', '--evidence', 'domain_scope_assessment:DSA-1']),
            ('approve_by_agent', ['approve', 'P-RUN-002', '--proposals', 'work/links/proposals.json', '--workspace', 'workspaces/history', '--reviewer', 'copilot', '--evidence', 'deployment_design:X']),
            ('approve5', ['approve', 'P-RUN-005', '--proposals', 'work/links/proposals.json', '--workspace', 'workspaces/history', '--reviewer', ME,
                          '--evidence', 'business_architecture_document:PAYARCH-55501#context', '--evidence', 'domain_scope_assessment:DSA-1', '--bian-release', 'BIAN-RELEASE-X']),
            ('build', ['build', '--workspace', 'workspaces/history', '--out', 'work/graph']),
            ('build_candidates', ['build', 'work/history/a1-business.json', 'work/history/a3-application.json', 'workspaces/history/mappings.json', '--out', 'work/refused']),
            ('trace_cap', ['trace', 'HIS-A1-PAYMENT-INITIATION', '--graph', 'work/graph', '--direction', 'down']),
            ('trace_hub', ['trace', 'HIS-A3-PAYMENTS-HUB', '--graph', 'work/graph']),
            ('impact', ['impact', 'HIS-A4-PAYAPP01', '--change', 'retire', '--graph', 'work/graph']),
            ('dashboard', ['dashboard', '--workspace', 'workspaces/history', '-o', 'work/history-dashboard.html']),
            ('gaps', ['designs', '--workspace', 'workspaces/history', '--gaps', '--status', 'open']),
        ]:
            cls.out[name] = sdem(*argv)
            if name == 'inspect': cls.files_after_inspect = sorted(str(f) for f in Path('.').rglob('*') if 'imports' not in f.parts)
        rec = json.loads(Path('workspaces/history/designs/design-records.json').read_text())
        cls.risk = next(g['id'] for g in rec['gaps'] if g['category'] == 'no entity type')
        cls.pdf = next(g['id'] for g in rec['gaps'] if g['category'] == 'file not read')
        for name, argv in [
            ('accept_no_note', ['designs', 'accept', cls.risk, '--workspace', 'workspaces/history', '--person', ME]),
            ('accept_by_agent', ['designs', 'accept', cls.risk, '--workspace', 'workspaces/history', '--person', 'copilot', '--note', 'x']),
            ('accept', ['designs', 'accept', cls.risk, '--workspace', 'workspaces/history', '--person', ME, '--note', 'risks stay in the risk register']),
            ('resolve', ['designs', 'resolve', cls.pdf, '--workspace', 'workspaces/history', '--person', ME, '--note', 'HLD v1 superseded by this design']),
            ('check2', ['check', '--workspace', 'workspaces/history']),
            ('reload', ['load', 'work/history', '--workspace', 'workspaces/history', '--person', ME, '--exclude', 'HIS-A3-PAYMENT-ORDER']),
        ]:
            cls.out[name] = sdem(*argv)

    @classmethod
    def tearDownClass(cls):
        os.chdir(cls.cwd); shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_1_inspect(self):
        code, o = self.out['inspect']
        self.assertIn('6 pages, 6 tables, 7 diagrams read (draw.io and 4 PlantUML; 3 not linked to a page)', o)
        self.assertIn('3 pictures for a person, 3 provenance files in the root', o)
        for t in ('[application | purpose | status | support hours] → HT-01', '[owner | review date | approval] → page facts', '[risk | impact | mitigation] → no entity type'):
            self.assertIn(t, o)
        self.assertIn('Coverage: 80% captured (45 captured, 11 not captured, 4 skipped by design)', o)
        self.assertEqual(self.files_after_inspect, ['work'])   # C1: inspect wrote nothing — only the export (under work/imports) exists

    def test_3_transform(self):
        code, o = self.out['transform']
        self.assertIn('6 pages read: A1 3 records, A3 6 records, A4 8 records, 7 links inside, 6 candidate links between, 3 pictures for a person', o)
        self.assertIn('check: 1 error(s)', o)
        files = sorted(p.name for p in Path('work/history').iterdir())
        self.assertEqual(files, ['a1-business.json', 'a3-application.json', 'a4-technology.json', 'design-index.json', 'extraction-report.md', 'extraction.json'])   # C2: no A2

    def test_4_review(self):
        rep = Path('work/history/extraction-report.md').read_text(); x = json.loads(Path('work/history/extraction.json').read_text())
        self.assertIn("HIS-A3-PAYMENT-ORDER: required attribute 'attributes' missing (LC-04)", rep)
        self.assertEqual(len(x['records']), 17)
        for r in x['records']:
            self.assertIn(r['confidence'], ('low', 'medium'))
            for s in r['sources']: self.assertTrue(s['page_id'] and s['where'] and s['rule'] and s['reasoning'])
        self.assertEqual(x['coverage']['not_captured_by_category'], {'text not read': 5, 'needs a person': 3, 'no entity type': 1, 'column not mapped': 1, 'file not read': 1})

    def test_5_load(self):
        _, dry = self.out['dry']
        self.assertIn('would load into workspaces/history: A1 3 entities, A3 5 entities, A4 8 entities, 7 links inside architectures', dry)
        code, o = self.out['load']
        self.assertEqual(code, 0, o)
        self.assertIn('loaded (LOAD-001) into workspaces/history: A1 3 entities, A3 5 entities, A4 8 entities, 7 links inside architectures', o)
        self.assertIn('gap records: 13 — what did not fit an entity, kept beside the workspace (text not read 5, needs a person 3, column not mapped 2, no entity type 1, file not read 1, rejected at load 1)', o)
        self.assertIn('reconciliation: 17 candidates = 16 loaded + 0 already in the workspace + 1 excluded; 60 items read = 45 captured + 4 skipped by design + 11 not captured', o)
        for f in ('a1-business.json', 'a2-service-domain.json', 'a3-application.json', 'a4-technology.json', 'mappings.json', 'designs/design-records.json', 'loads/LOAD-001.json'):
            self.assertTrue(Path('workspaces/history', f).exists(), f)

    def test_6_check(self):
        code, o = self.out['check']
        self.assertEqual(code, 0, o)
        for k in ('level A1', 'level A2', 'level A3', 'level A4', 'mappings #1', 'design records'): self.assertRegex(o, r'OK: ' + re.escape(k))

    def test_7_link_and_review(self):
        props = json.loads(Path('work/links/proposals.json').read_text())['mappings']
        self.assertEqual(len(props), 5); self.assertTrue(all(p['confidence'] == 0.4 for p in props))
        dep = {(p['source']['id'], p['target']['id']) for p in props if p['relationship'] == 'DEPLOYED_ON'}
        self.assertEqual(dep, {('HIS-A3-CLEARING-GATEWAY', 'HIS-A4-PAYAPP01'), ('HIS-A3-PAYMENTS-HUB', 'HIS-A4-PAYMENTS-KUBERNETES-CLUSTER'),
                               ('HIS-A3-SANCTIONS-SCREENING', 'HIS-A4-PAYMENTS-KUBERNETES-CLUSTER')})
        self.assertTrue(all('DEC-E-11' in p['rationale'] for p in props if p['relationship'] == 'DEPLOYED_ON'))
        sup = {(p['source']['id'], p['target']['id']) for p in props if p['relationship'] == 'SUPPORTED_BY'}
        self.assertEqual(sup, {('HIS-A1-PAYMENT-CLEARING', 'SD-PE'), ('HIS-A1-PAYMENT-INITIATION', 'SD-PI')})

    def test_8_approve(self):
        self.assertIn('approved MAP-001: HIS-A3-CLEARING-GATEWAY -DEPLOYED_ON-> HIS-A4-PAYAPP01', self.out['approve1'][1])
        code, o = self.out['approve5_no_release']; self.assertEqual(code, 1); self.assertIn('add --bian-release', o)
        self.assertEqual(self.out['approve_by_agent'][0], 1)
        self.assertIn('approved MAP-002: HIS-A1-PAYMENT-INITIATION -SUPPORTED_BY-> SD-PI', self.out['approve5'][1])

    def test_9_build(self):
        o = self.out['build'][1]
        for part in ('a2-service-domain.graph.json (24 nodes, 33 edges)', 'a3-application.graph.json (5 nodes, 5 edges)', 'a4-technology.graph.json (8 nodes, 2 edges)',
                     'designs.graph.json (24 nodes, 42 edges)', 'federated.graph.json (4 nodes, 2 edges)'):
            self.assertIn(part, o)
        code, o = self.out['build_candidates']; self.assertNotEqual(code, 0); self.assertIn('CTL-23', o)

    def test_10_use(self):
        self.assertIn("-SUPPORTED_BY-> SD-PI 'Payment Initiation (synthetic selection)'  [A2 BIAN · Service Domain]  (MAP-002)", self.out['trace_cap'][1])
        self.assertIn('DOC-55501  Payments Hub Design  (2022-05-10) — 7 open gap(s)', self.out['trace_hub'][1])
        o = self.out['impact'][1]
        self.assertRegex(o, r'design_change_required\s+A3\s+HIS-A3-CLEARING-GATEWAY.*via MAP-001'); self.assertIn('mappings to supersede: MAP-001', o)
        self.assertIn('13 open gap(s)', self.out['dashboard'][1])
        self.assertIn('"designs","Designs & gaps"', Path('work/history-dashboard.html').read_text())

    def test_11_gaps(self):
        self.assertIn('gaps: 13', self.out['gaps'][1])
        self.assertEqual(self.out['accept_no_note'][0], 1); self.assertEqual(self.out['accept_by_agent'][0], 1)
        self.assertIn('12 open gap(s) left', self.out['accept'][1]); self.assertIn('11 open gap(s) left', self.out['resolve'][1])
        self.assertIn('OK: design records', self.out['check2'][1])

    def test_repeat_load(self):
        o = self.out['reload'][1]
        self.assertIn('loaded (LOAD-002) into workspaces/history: A1 0 entities, A3 0 entities, A4 0 entities', o)
        self.assertIn('reconciliation: 17 candidates = 0 loaded + 16 already in the workspace + 1 excluded', o)
        g = {x['id']: x for x in json.loads(Path('workspaces/history/designs/design-records.json').read_text())['gaps']}
        self.assertEqual(len(g), 13); self.assertEqual((g[self.risk]['status'], g[self.pdf]['status']), ('accepted', 'resolved'))   # C11: kept, not reset


if __name__ == '__main__':
    unittest.main()
