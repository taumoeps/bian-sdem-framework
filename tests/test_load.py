"""`sdem load` — the L of the ETL: reviewed candidates from `sdem transform` into a workspace (spec docs/design/sdem-load-spec.md).
Also CTL-23 (build refuses candidates) and DEC-E-11 (document-derived links capped at low), end to end."""
import contextlib, io, json, shutil, tempfile, unittest
from pathlib import Path

from sdem import load, transform
from sdem.cli import main

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'examples' / 'designs' / 'confluence-folder-export'
A2 = ROOT / 'examples' / 'payment-initiation' / 'a2-service-domain.json'
BAD = 'HIS-A3-PAYMENT-ORDER'   # a data entity drawn without its attribute list: fails the check (LC-04)


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(map(str, argv)))
    return code, out.getvalue(), err.getvalue()


class LoadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.cand = cls.tmp / 'cand'
        transform.extract(FOLDER, cls.cand, now='2026-10-28T00:00:00', ocr='off')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def est(self, name):
        p = self.tmp / name
        shutil.rmtree(p, ignore_errors=True)
        return p

    def test_refuses_a_folder_that_is_not_a_transform_output(self):  # LD-G02
        with self.assertRaises(load.LoadError): load.load(ROOT / 'examples' / 'payment-initiation', self.est('e0'), 'jane.architect', all_=True)

    def test_selection_is_required_and_checked(self):  # LD-S01
        with self.assertRaises(load.LoadError): load.load(self.cand, self.est('e1'), 'jane.architect')
        with self.assertRaises(load.LoadError): load.load(self.cand, self.est('e1'), 'jane.architect', exclude=['HIS-A3-NOT-THERE'])

    def test_person_must_be_a_person(self):  # LD-C02
        for who in ('copilot', 'sdem-a3-application', ''):
            with self.assertRaises(load.LoadError): load.load(self.cand, self.est('e2'), who, all_=True)

    def test_check_failure_writes_nothing(self):  # LD-C01
        e = self.est('e3')
        with self.assertRaises(load.LoadError) as c: load.load(self.cand, e, 'jane.architect', all_=True)
        self.assertIn('LC-04', str(c.exception)); self.assertFalse(e.exists())

    def test_loads_into_a_new_estate(self):  # LD-M02, LD-R01
        e = self.est('e4')
        res = load.load(self.cand, e, 'jane.architect', exclude=[BAD], now='2026-10-28T10:00:00')
        self.assertEqual(res['load_id'], 'LOAD-001'); self.assertEqual(res['excluded'], [BAD])
        a3 = json.loads((e / 'a3-application.json').read_text())
        self.assertEqual(a3['source_system'], 'SDEM-LOAD'); self.assertEqual(a3['model_id'], 'E4-A3')
        self.assertNotIn(BAD, {i['id'] for i in a3['instances']})
        self.assertTrue((e / 'mappings.json').exists())
        rec = json.loads((e / 'loads' / 'LOAD-001.json').read_text())
        self.assertEqual(rec['person'], 'jane.architect'); self.assertTrue(rec['transform']['export_sha256'])
        self.assertEqual(sum(len(v) for v in rec['loaded'].values()), sum(len(v) for v in res['loaded'].values()))
        self.assertEqual(run('check', '--workspace', e)[0], 0)

    def test_links_follow_the_selection(self):  # LD-S02
        res = load.load(self.cand, self.est('e5'), 'jane.architect', exclude=[BAD, 'HIS-A4-PAYAPP01'])
        self.assertTrue(any('HIS-A3-CLEARING-GATEWAY.deployed_on' in d for d in res['dropped']))
        self.assertTrue(any(d.startswith('link HIS-A4-CORE-SWITCH -flow-> HIS-A4-PAYAPP01') for d in res['dropped']))
        a3 = {i['id']: i for i in json.loads((self.tmp / 'e5' / 'a3-application.json').read_text())['instances']}
        self.assertNotIn('deployed_on', a3['HIS-A3-CLEARING-GATEWAY'].get('attributes', {}))

    def test_same_content_skipped_different_refused(self):  # LD-M01
        e = self.est('e6')
        load.load(self.cand, e, 'jane.architect', exclude=[BAD])
        again = load.load(self.cand, e, 'jane.architect', exclude=[BAD])
        self.assertEqual(again['load_id'], 'LOAD-002'); self.assertIn('HIS-A3-PAYMENTS-HUB', again['skipped_same'])
        p = e / 'a3-application.json'; d = json.loads(p.read_text())
        next(i for i in d['instances'] if i['id'] == 'HIS-A3-PAYMENTS-HUB')['description'] = 'changed in the workspace'
        p.write_text(json.dumps(d)); before = p.read_text()
        with self.assertRaises(load.LoadError) as c: load.load(self.cand, e, 'jane.architect', exclude=[BAD])
        self.assertIn('different content', str(c.exception)); self.assertEqual(p.read_text(), before)
        self.assertFalse((e / 'loads' / 'LOAD-003.json').exists())

    def test_a2_dataset_added_once(self):  # LD-A01
        e = self.est('e7')
        res = load.load(self.cand, e, 'jane.architect', exclude=[BAD], a2=A2)
        self.assertEqual(res['a2_added'], str(A2)); self.assertTrue((e / 'a2-service-domain.json').exists())
        res2 = load.load(self.cand, e, 'jane.architect', exclude=[BAD], a2=A2)
        self.assertIsNone(res2['a2_added']); self.assertTrue(any('already has an A2' in n for n in res2['notes']))

    def test_dry_run_writes_nothing(self):  # LD-D01
        e = self.est('e8')
        res = load.load(self.cand, e, 'jane.architect', exclude=[BAD], dry_run=True)
        self.assertTrue(res['loaded']['A3']); self.assertFalse(e.exists())

    def test_build_refuses_candidates(self):  # LD-X01, CTL-23
        files = [self.cand / f for f in ('a1-business.json', 'a3-application.json', 'a4-technology.json')]
        reg = self.tmp / 'reg.json'; reg.write_text(json.dumps(load.EMPTY_REGISTRY))
        code, out, err = run('build', *files, reg, '--out', self.tmp / 'g-refused')
        self.assertNotEqual(code, 0); self.assertIn('CTL-23', out + err)

    def test_end_to_end_transform_load_link_approve_build(self):  # AT-LD-01, LD-E01 (DEC-E-11)
        e = self.est('e9'); links = self.tmp / 'links'; graph = self.tmp / 'graph'
        load.load(self.cand, e, 'jane.architect', exclude=[BAD])
        self.assertEqual(run('link', '--workspace', e, '--out', links)[0], 0)
        props = json.loads((links / 'proposals.json').read_text())['mappings']
        p = next(m for m in props if m['source']['id'] == 'HIS-A3-CLEARING-GATEWAY' and m['target']['id'] == 'HIS-A4-PAYAPP01')
        self.assertEqual(p['relationship'], 'DEPLOYED_ON')
        self.assertEqual(p['confidence'], 0.4); self.assertIn('DEC-E-11', p['rationale'])            # capped: read from a document
        code, out, err = run('approve', p['mapping_id'], '--proposals', links / 'proposals.json', '--workspace', e,
                             '--reviewer', 'jane.architect', '--evidence', 'deployment_design:PAYARCH-55501#notes')
        self.assertEqual(code, 0, out + err)
        self.assertEqual(run('build', '--workspace', e, '--out', graph)[0], 0)
        code, out, _ = run('trace', 'HIS-A3-CLEARING-GATEWAY', '--graph', graph)
        self.assertIn('HIS-A4-PAYAPP01', out)

    def test_bian_link_approved_with_its_release(self):  # with --a2 the engine proposes capability → Service Domain; approval needs the BIAN release
        e = self.est('e12'); links = self.tmp / 'links12'
        load.load(self.cand, e, 'jane.architect', exclude=[BAD], a2=A2)
        run('link', '--workspace', e, '--out', links)
        p = next(m for m in json.loads((links / 'proposals.json').read_text())['mappings'] if m['relationship'] == 'SUPPORTED_BY')
        ev = ['--evidence', 'business_architecture_document:PAYARCH-55501#context', '--evidence', 'domain_scope_assessment:DSA-1']
        code, out, err = run('approve', p['mapping_id'], '--proposals', links / 'proposals.json', '--workspace', e, '--reviewer', 'jane.architect', *ev)
        self.assertEqual(code, 1); self.assertIn('--bian-release', err)
        code, out, err = run('approve', p['mapping_id'], '--proposals', links / 'proposals.json', '--workspace', e, '--reviewer', 'jane.architect', *ev, '--bian-release', 'BIAN-RELEASE-X')
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads((e / 'mappings.json').read_text())['mappings'][-1]['bian_release'], 'BIAN-RELEASE-X')

    # ---- data that did not fit an entity: design and gap records (LD-R02…R04, GS-D-01…03)
    def test_design_and_gap_records_written(self):  # LD-R02
        e = self.est('g1'); load.load(self.cand, e, 'jane.architect', exclude=[BAD])
        rec = json.loads((e / 'designs' / 'design-records.json').read_text())
        from sdem import designs
        self.assertEqual(designs.check(rec)[0], [])
        cats = {g['category'] for g in rec['gaps']}
        self.assertTrue({'no entity type', 'column not mapped', 'text not read', 'needs a person', 'file not read', 'rejected at load'} <= cats, cats)
        hub = next(g for g in rec['gaps'] if g['category'] == 'column not mapped' and g['about'] == ['HIS-A3-PAYMENTS-HUB'])
        self.assertEqual(hub['text'], 'Support hours: 24x7'); self.assertTrue(hub['where'].startswith('table'))   # placed at the table it came from
        for g in [g for g in rec['gaps'] if g['category'] == 'column not mapped' and 'Support hours' in g['text']]:
            self.assertIn("'Payments Hub Design / Applications'", g['where'], g)   # the applications table — not another table the entity appears in
        page = next(d for d in rec['documents'] if d['id'] == 'DOC-55501')
        self.assertEqual(page['facts']['Owner'], 'Payments architecture team'); self.assertIn('HIS-A3-PAYMENTS-HUB', page['entities'])
        rej = next(g for g in rec['gaps'] if g['category'] == 'rejected at load')
        self.assertIn(BAD, rej['text']); self.assertIn('jane.architect', rej['reason'])
        again = load.load(self.cand, e, 'jane.architect', exclude=[BAD])                      # stable ids: nothing added twice
        self.assertEqual(again['designs']['gaps_added'], 0)
        self.assertEqual(len(json.loads((e / 'designs' / 'design-records.json').read_text())['gaps']), len(rec['gaps']))

    def test_link_table_columns_kept(self):  # a column of a source/target table belongs to links — kept as a gap too
        tmp = self.tmp / 'std'; transform.extract(ROOT / 'tests' / 'fixtures' / 'confluence-export-sample', tmp, now='2026-10-28T00:00:00', ocr='off')
        e = self.est('g2'); load.load(tmp, e, 'jane.architect', all_=True)
        rec = json.loads((e / 'designs' / 'design-records.json').read_text())
        self.assertTrue(any(g['category'] == 'column not mapped' and 'Protocol' in g['text'] and 'REST' in g['text'] for g in rec['gaps']))

    def test_reconciliation(self):  # LD-R03
        e = self.est('g3'); res = load.load(self.cand, e, 'jane.architect', exclude=[BAD])
        rc = res['reconciliation']
        self.assertTrue(rc['balances']); self.assertEqual(rc['candidates'], rc['loaded'] + rc['already_in_estate'] + rc['excluded'])
        self.assertEqual(rc['transform_items'], rc['captured'] + rc['skipped_by_design'] + rc['not_captured'])
        self.assertEqual(json.loads((e / 'loads' / 'LOAD-001.json').read_text())['reconciliation'], rc)

    def test_designs_command_and_trace(self):  # LD-R04, GS-D-01…03
        e = self.est('g4'); g = self.tmp / 'g4graph'
        load.load(self.cand, e, 'jane.architect', exclude=[BAD])
        self.assertEqual(run('check', '--workspace', e)[0], 0)
        code, out, _ = run('build', '--workspace', e, '--out', g); self.assertEqual(code, 0, out)
        self.assertTrue((g / 'designs.graph.json').exists())
        from sdem.store import GraphReader
        r = GraphReader.from_store(g); self.assertTrue(r.designs()['gaps'])
        fed = json.loads((g / 'federated.graph.json').read_text())['graph']
        self.assertFalse(any(n['id'].startswith(('DOC-', 'GAP-')) for n in fed['nodes']))   # beside the knowledge graph, not in it
        code, out, _ = run('trace', 'HIS-A3-PAYMENTS-HUB', '--graph', g)
        self.assertIn('DOCUMENTED IN', out); self.assertIn('DOC-55501', out)
        code, out, _ = run('designs', '--workspace', e, '--gaps', '--category', 'no entity type')
        self.assertEqual(code, 0); self.assertIn('Clearing file late', out)
        code, out, _ = run('designs', '--graph', g, '--entity', 'HIS-A3-PAYMENTS-HUB', '--json')
        self.assertIn('DOC-55501', out)

    def test_bad_design_records_reject_the_build(self):  # GS-D-02
        e = self.est('g5'); load.load(self.cand, e, 'jane.architect', exclude=[BAD])
        p = e / 'designs' / 'design-records.json'; d = json.loads(p.read_text()); d['gaps'][0]['document'] = 'DOC-NOPE'; p.write_text(json.dumps(d))
        code, out, err = run('build', '--workspace', e, '--out', self.tmp / 'g5graph')
        self.assertNotEqual(code, 0); self.assertIn('DOC-NOPE', out + err)

    def test_gap_resolve_accept_reopen(self):  # LD-R05
        e = self.est('g6'); load.load(self.cand, e, 'jane.architect', exclude=[BAD])
        rec = json.loads((e / 'designs' / 'design-records.json').read_text())
        risk = next(g['id'] for g in rec['gaps'] if g['category'] == 'no entity type')
        pdf = next(g['id'] for g in rec['gaps'] if g['category'] == 'file not read')
        self.assertEqual(run('designs', 'accept', risk, '--workspace', e, '--person', 'jane.architect')[0], 1)                       # a note is required
        self.assertEqual(run('designs', 'resolve', pdf, '--workspace', e, '--person', 'copilot', '--note', 'x')[0], 1)              # never an agent
        code, out, _ = run('designs', 'accept', risk, '--workspace', e, '--person', 'jane.architect', '--note', 'risks stay in the risk register')
        self.assertEqual(code, 0); self.assertIn('open gap(s) left', out)
        code, _, _ = run('designs', 'resolve', pdf, '--workspace', e, '--person', 'jane.architect', '--note', 'HLD recorded as HIS-A3-… by hand')
        rec = json.loads((e / 'designs' / 'design-records.json').read_text()); g = {x['id']: x for x in rec['gaps']}
        self.assertEqual((g[risk]['status'], g[pdf]['status']), ('accepted', 'resolved'))
        self.assertEqual(g[risk]['history'][-1]['person'], 'jane.architect')
        self.assertEqual(run('check', '--workspace', e)[0], 0)
        run('designs', 'reopen', pdf, '--workspace', e, '--person', 'jane.architect', '--note', 'not complete')
        self.assertEqual(json.loads((e / 'designs' / 'design-records.json').read_text())['gaps'][[x['id'] for x in rec['gaps']].index(pdf)]['status'], 'open')
        p = e / 'designs' / 'design-records.json'; d = json.loads(p.read_text())                                                      # a status changed by hand, with no person on record
        next(x for x in d['gaps'] if x['status'] == 'open')['status'] = 'resolved'; p.write_text(json.dumps(d))
        code, out, _ = run('check', '--workspace', e); self.assertEqual(code, 1); self.assertIn("without a person's decision", out)

    def test_dashboard_shows_open_gaps(self):  # DB-C09, DB-H08
        e = self.est('g7'); load.load(self.cand, e, 'jane.architect', exclude=[BAD])
        from sdem import dashboard, home
        d = dashboard.collect(e)
        self.assertEqual(len(d['designs']['open']), len(json.loads((e / 'designs' / 'design-records.json').read_text())['gaps']))
        self.assertTrue(any('open gap(s)' in a['text'] and a['tab'] == 'designs' for a in d['attention']))
        self.assertIn('"designs","Designs & gaps"', dashboard.render(d))
        h = home.collect_home([e], [('projects/g7.html', d)])
        self.assertEqual(h['projects'][0]['open_gaps'], len(d['designs']['open']))

    def test_cli(self):  # LD-G01, LD-B01
        cand = self.tmp / 'cand-bian'; shutil.rmtree(cand, ignore_errors=True); shutil.copytree(self.cand, cand)
        x = json.loads((cand / 'extraction.json').read_text())
        x['bian_mentions'] = [{'name': 'Payment Initiation', 'type': 'A2.ServiceDomain', 'existing_id': 'SD-PI', 'page_title': 'Payments Hub Design', 'where': 'text'}]
        (cand / 'extraction.json').write_text(json.dumps(x))
        code, out, _ = run('load', cand, '--workspace', self.est('e10'), '--person', 'jane.architect', '--exclude', BAD)
        self.assertEqual(code, 0); self.assertIn('loaded (LOAD-001)', out); self.assertIn('hints for sdem link', out); self.assertIn('SD-PI', out)
        self.assertEqual(run('load', cand, '--workspace', self.est('e11'), '--person', 'jane.architect', '--all')[0], 1)   # refused: check error
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit): main(['load', str(cand), '--workspace', 'x', '--person', 'p'])        # no selection: usage error


if __name__ == '__main__':
    unittest.main()
