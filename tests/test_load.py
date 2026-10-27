"""`sdem load` — the L of the ETL: reviewed candidates from `sdem transform` into an estate (spec docs/sdem-load-spec.md).
Also CTL-23 (build refuses candidates) and DEC-E-11 (document-derived links capped at low), end to end."""
import contextlib, io, json, shutil, tempfile, unittest
from pathlib import Path

from sdem import load, transform
from sdem.cli import main

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'tests' / 'fixtures' / 'confluence-folder-export'
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
        self.assertEqual(run('check', '--estate', e)[0], 0)

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
        next(i for i in d['instances'] if i['id'] == 'HIS-A3-PAYMENTS-HUB')['description'] = 'changed in the estate'
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
        self.assertEqual(run('link', '--estate', e, '--out', links)[0], 0)
        props = json.loads((links / 'proposals.json').read_text())['mappings']
        p = next(m for m in props if m['source']['id'] == 'HIS-A3-CLEARING-GATEWAY' and m['target']['id'] == 'HIS-A4-PAYAPP01')
        self.assertEqual(p['relationship'], 'DEPLOYED_ON')
        self.assertEqual(p['confidence'], 0.4); self.assertIn('DEC-E-11', p['rationale'])            # capped: read from a document
        code, out, err = run('approve', p['mapping_id'], '--proposals', links / 'proposals.json', '--estate', e,
                             '--reviewer', 'jane.architect', '--evidence', 'deployment_design:PAYARCH-55501#notes')
        self.assertEqual(code, 0, out + err)
        self.assertEqual(run('build', '--estate', e, '--out', graph)[0], 0)
        code, out, _ = run('trace', 'HIS-A3-CLEARING-GATEWAY', '--graph', graph)
        self.assertIn('HIS-A4-PAYAPP01', out)

    def test_cli(self):  # LD-G01, LD-B01
        cand = self.tmp / 'cand-bian'; shutil.rmtree(cand, ignore_errors=True); shutil.copytree(self.cand, cand)
        x = json.loads((cand / 'extraction.json').read_text())
        x['bian_mentions'] = [{'name': 'Payment Initiation', 'type': 'A2.ServiceDomain', 'existing_id': 'SD-PI', 'page_title': 'Payments Hub Design', 'where': 'text'}]
        (cand / 'extraction.json').write_text(json.dumps(x))
        code, out, _ = run('load', cand, '--estate', self.est('e10'), '--person', 'jane.architect', '--exclude', BAD)
        self.assertEqual(code, 0); self.assertIn('loaded (LOAD-001)', out); self.assertIn('hints for sdem link', out); self.assertIn('SD-PI', out)
        self.assertEqual(run('load', cand, '--estate', self.est('e11'), '--person', 'jane.architect', '--all')[0], 1)   # refused: check error
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit): main(['load', str(cand), '--estate', 'x', '--person', 'p'])        # no selection: usage error


if __name__ == '__main__':
    unittest.main()
