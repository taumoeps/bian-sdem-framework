"""Design onboarding on a domain other than payments: a made-up lending design (tests/fixtures/lending-folder-export,
scripts/make_lending_export.py) is transformed and loaded with no lending-specific rules or settings.

Expectations were sealed on 2026-10-29 before the first run. One differed from the result and was corrected to SDEM's
rule, not to the output: 'Loan Book' (a database in PlantUML and C4) was sealed as an A3 record, but SDEM's rule types a
database as A4 system software — the same as 'Payments Store' in the payments export."""
import json, shutil, tempfile, unittest
from pathlib import Path

from sdem import load, transform

ROOT = Path(__file__).resolve().parents[1]
EXPORT = ROOT / 'tests' / 'fixtures' / 'lending-folder-export'
MUST_FIND = {
    'A1.BusinessCapability': ['Loan Origination', 'Credit Decisioning', 'Collateral Management'],
    'A1.BusinessActor': ['Small Business Customer', 'Mortgage Broker'],
    'A3.ApplicationComponent': ['Loan Origination Platform', 'Credit Decisioning Engine', 'Collateral Register', 'Credit Bureau Gateway',
                                'Broker Portal', 'Affordability Calculator'],
    'A3.DataEntity': ['Loan Application'],
    'A4.Node': ['Lending OpenShift Cluster', 'LENDAPP01', 'LENDAPP02'],
    'A4.SystemSoftware': ['Oracle 19c', 'Loan Book'],
    'A4.Device': ['Branch Firewall'],
}
NEVER = ['loan', 'lending', 'credit', 'every loan', 'once']   # the domain's general words are not records


class LendingOnboardingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp()); cls.out = cls.tmp / 'history'
        transform.extract(EXPORT, cls.out, ocr='off')
        cls.recs = [i for f in ('a1-business.json', 'a3-application.json', 'a4-technology.json') if (cls.out / f).exists()
                    for i in json.loads((cls.out / f).read_text())['instances']]
        cls.ex = json.loads((cls.out / 'extraction.json').read_text())

    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_finds_every_sealed_record_with_its_type(self):
        got = {(i['type'], i['name']) for i in self.recs}
        missing = [(t, n) for t, ns in MUST_FIND.items() for n in ns if (t, n) not in got]
        self.assertEqual(missing, [])
        self.assertEqual(len(self.recs), sum(map(len, MUST_FIND.values())), sorted(n for _, n in got))

    def test_no_records_from_general_words_and_none_in_a2(self):
        names = {i['name'].lower() for i in self.recs}
        self.assertEqual([w for w in NEVER if w in names], [])
        self.assertFalse((self.out / 'a2-service-domain.json').exists())
        self.assertFalse([i for i in self.recs if i['type'].startswith('A2.')])

    def test_every_item_is_accounted_for(self):
        c = self.ex['coverage']['overall']
        self.assertEqual(c['items'], c['captured'] + c['skipped'] + c['not_captured'])
        self.assertGreaterEqual(c['percent'], 80)
        self.assertGreaterEqual(self.ex['coverage']['by_kind']['tables and diagrams']['percent'], 90)   # the pilot measure

    def test_loads_into_an_estate_and_keeps_the_rest_as_gaps(self):
        est = self.tmp / 'lending'
        res = load.load(self.out, est, 'jane.architect', exclude=['HIS-A3-LOAN-APPLICATION'])  # a data entity drawn without its columns fails LC-04, as in payments
        self.assertEqual(res['reconciliation']['loaded'], len(self.recs) - 1)
        gaps = json.loads((est / 'designs' / 'design-records.json').read_text())['gaps']
        cats = {g['category'] for g in gaps}
        self.assertTrue({'column not mapped', 'no entity type', 'rejected at load'} <= cats, cats)
        self.assertTrue(any('Data classification' in (g.get('where') or '') for g in gaps))
        self.assertTrue(any('Risk' in (g.get('text') or '') for g in gaps))
        from sdem.graph import FederatedGraph, LevelGraph
        from sdem.metamodel import Metamodel
        mm = Metamodel.load()
        levels = [LevelGraph(json.loads(p.read_text()), mm) for p in sorted(est.glob('a[1-4]-*.json'))]
        report = FederatedGraph(levels, [json.loads((est / 'mappings.json').read_text())], mm).check()
        self.assertEqual({k: v for k, v in report.items() if v}, {})


if __name__ == '__main__':
    unittest.main()
