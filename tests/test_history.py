"""`sdem history`: a Confluence HTML export of past designs → candidate architecture records (spec docs/sdem-history-spec.md).
Run against the synthetic export in tests/fixtures/confluence-export-sample (scripts/make_confluence_sample.py)."""
import json, re, shutil, tempfile, unittest
from pathlib import Path

from sdem import history
from sdem.graph import LevelGraph
from sdem.metamodel import Metamodel

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / 'tests' / 'fixtures' / 'confluence-export-sample'
KNOWN = ROOT / 'examples' / 'payment-initiation' / 'a3-application.json'


class HistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.x, cls.ds, cls.issues = history.extract(SAMPLE, cls.tmp / 'out', known=[KNOWN], now='2026-10-28T00:00:00')
        cls.doc = json.loads((cls.tmp / 'out' / 'extraction.json').read_text())
        cls.by_name = {r['name']: r for r in cls.doc['records']}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_tables_become_records(self):  # HI-R01
        r = self.by_name['Fraud Screening']
        self.assertEqual(r['type'], 'A3.ApplicationComponent'); self.assertEqual(r['confidence'], 'medium')
        self.assertEqual(r['sources'][0]['rule'], 'HT-01')
        self.assertEqual(self.by_name['Payment Initiation']['type'], 'A1.BusinessCapability')
        self.assertEqual(self.by_name['PAYDB01']['type'], 'A4.Node')
        a3 = {i['name']: i for i in self.ds['A3']['instances']}
        self.assertEqual(a3['Fraud Screening']['lifecycle_status'], 'planned')
        self.assertEqual(a3['Legacy Payment Forms']['lifecycle_status'], 'retired')
        self.assertEqual(a3['Fraud Screening']['attributes']['vendor'], 'VendorCo')

    def test_every_kind_of_drawio_file_is_read(self):  # HI-R02: plain XML without extension, compressed, PNG with the diagram inside
        files = {d['file'] for p in json.loads((self.tmp / 'out' / 'design-index.json').read_text())['designs'] for d in p['diagrams']}
        self.assertEqual(files, {'attachments/1001/1001', 'attachments/1002/3001.drawio', 'attachments/1002/3002.png'})
        self.assertEqual(self.by_name['Payment Initiation Service']['type'], 'A3.ApplicationService')   # ArchiMate shape
        self.assertEqual(self.by_name['Alerts DB']['type'], 'A4.SystemSoftware')                      # label word in a compressed diagram
        self.assertEqual(self.by_name['Fraud AWS EKS Cluster']['type'], 'A4.Node')                    # diagram inside a PNG
        self.assertNotIn('Payments Hub — application view', self.by_name)                             # a text box is not a record

    def test_lines_and_containment(self):  # HI-R03
        links = {(l['source'], l['kind'], l['target']) for l in self.doc['links_within']}
        self.assertIn(('HIS-A3-PAYMENTS-HUB', 'flow', 'HIS-A3-EXECUTION-GATEWAY'), links)
        self.assertIn(('HIS-A3-FRAUD-SCORING-ENGINE', 'triggering', 'HIS-A3-CASE-MANAGEMENT-SYSTEM'), links)
        self.assertIn(('HIS-A3-PAYMENTS-HUB', 'flow', 'HIS-A3-FRAUD-SCREENING'), links)            # source/target table
        cross = {(c['source'], c['target'], c['mapping_type_id']) for c in self.doc['links_between_candidates']}
        self.assertIn(('HIS-A3-LEDGER-POSTING-SERVICE', 'HIS-A4-PAYMENTS-KUBERNETES-CLUSTER', 'COMPONENT_DEPLOYED_ON_INFRASTRUCTURE'), cross)
        self.assertEqual(len(cross), len(self.doc['links_between_candidates']))                   # merged, not repeated
        gw = next(c for c in self.doc['links_between_candidates'] if c['source'] == 'HIS-A3-EXECUTION-GATEWAY')
        self.assertEqual(len(gw['sources']), 2)                                                     # the diagram and the text
        for l in self.doc['links_within']:  # every kind is one the rulebook allows
            a = next(r for r in self.doc['records'] if r['id'] == l['source']); b = next(r for r in self.doc['records'] if r['id'] == l['target'])
            self.assertIsNone(Metamodel.load().relationship_issue(a['type'][:2], a['type'], l['kind'], b['type']))

    def test_narrative_uses_known_names_only(self):  # HI-R04
        links = {(l['source'], l['kind'], l['target']): l for l in self.doc['links_within']}
        l = links[('HIS-A3-PAYMENTS-HUB', 'serving', 'HIS-A3-MOBILE-BANKING-APP')]          # "the App calls the Hub": the Hub serves the App
        self.assertEqual(l['confidence'], 'low'); self.assertEqual(l['sources'][0]['rule'], 'HP-02')
        self.assertNotIn('Branch Payment Forms', self.by_name)                               # words in text never create records
        self.assertEqual(self.by_name['Payment Initiation Service']['same_as_existing']['id'], 'SVC-PAY-INIT')

    def test_pictures_and_unknown_shapes_go_to_a_person(self):  # HI-R05
        what = [(v['what'], v.get('name')) for v in self.doc['for_review']]
        self.assertIn(('picture', 'rack-photo'), what)
        self.assertIn(('shape', 'Card Authorisation Switch'), what)
        self.assertEqual(sum(1 for w, _ in what if w == 'picture'), 1)   # draw.io previews and emoticons are not reported

    def test_candidates_never_above_medium_and_carry_their_source(self):  # HI-C01, HI-C02
        for r in self.doc['records']:
            self.assertEqual(r['status'], 'candidate'); self.assertIn(r['confidence'], ('low', 'medium'))
            for s in r['sources']:
                self.assertTrue(s['page_id'] and s['where'] and s['rule'] and s['reasoning'])
        for d in self.ds.values():
            self.assertEqual(d['source_system'], 'CONFLUENCE-EXTRACT')
            for i in d['instances']: self.assertTrue(i['attributes']['source_id'].startswith('confluence:'))

    def test_candidate_datasets_pass_sdem_check(self):  # HI-C03
        for lvl, d in self.ds.items():
            self.assertEqual(LevelGraph(d, Metamodel.load()).validate(), [], lvl)
        self.assertEqual(self.ds['A3']['instances'][0]['version'][:2], '20')   # the page's last-modified date

    def test_design_index_and_report(self):  # HI-O02, HI-O03
        idx = {p['page_id']: p for p in json.loads((self.tmp / 'out' / 'design-index.json').read_text())['designs']}
        self.assertEqual(set(idx), {'1001', '1002'})
        self.assertEqual(idx['1002']['modified'], '2019-06-03'); self.assertEqual(idx['1001']['title'], 'Payments Hub Solution Design')
        self.assertIn('HIS-A3-PAYMENTS-HUB', idx['1001']['records'])
        rep = (self.tmp / 'out' / 'extraction-report.md').read_text()
        for part in ('## Records', '## Links between architectures', '## For a person', '## Designs'): self.assertIn(part, rep)

    def test_deterministic(self):  # HI-G03
        out2 = self.tmp / 'again'
        history.extract(SAMPLE, out2, known=[KNOWN], now='2026-10-28T00:00:00')
        for f in ('a3-application.json', 'extraction.json', 'design-index.json', 'extraction-report.md'):
            self.assertEqual((self.tmp / 'out' / f).read_text().replace(str(self.tmp / 'out'), ''), (out2 / f).read_text().replace(str(out2), ''), f)

    def test_rules_file_tunes_without_code(self):  # HI-G02
        rules = json.loads(history.RULES.read_text())
        rules['label_words']['A3.ApplicationComponent'].append('switch')
        p = self.tmp / 'rules.json'; p.write_text(json.dumps(rules))
        x, _, _ = history.extract(SAMPLE, self.tmp / 'tuned', rules=p, now='2026-10-28T00:00:00')
        names = {r['name'] for r in x.records.values()}
        self.assertIn('Card Authorisation Switch', names)
        self.assertFalse(any(v.get('name') == 'Card Authorisation Switch' for v in x.review))

    def test_inspect_shows_structure(self):  # HI-I01
        r = history.inspect(SAMPLE)
        rules = {tuple(t['columns']): t['rule'] for t in r['tables']}
        self.assertEqual(rules[('application', 'description', 'vendor', 'status')], 'HT-01')
        self.assertTrue(any(t['rule'].startswith('not read') for t in r['tables']))
        self.assertTrue(any(s['type'] == 'unclassified' for s in r['shapes']))

    def test_no_ai_no_network(self):  # HI-G01
        src = (ROOT / 'sdem' / 'history.py').read_text()
        self.assertIsNone(re.search(r'\bimport (socket|requests|http\.client)|urllib\.request|anthropic|openai', src))

    def test_cli(self):
        from sdem.cli import main
        self.assertEqual(main(['history', 'extract', str(SAMPLE), '-o', str(self.tmp / 'cli'), '--json']), 0)
        self.assertTrue((self.tmp / 'cli' / 'a3-application.json').exists())
        self.assertEqual(main(['history', 'extract', str(self.tmp / 'missing'), '-o', str(self.tmp / 'x')]), 2)


if __name__ == '__main__':
    unittest.main()
