"""Evidence classes and calibration (owner's decision D3, 2026-11-09; docs/design/aid-spec.md AID-E01…E03): every engine proposal and
every AID element says what kind of evidence it rests on; a name or a description alone is weak, whatever its words; observed precision
per band and class is reported, not used to set anything."""
import json, shutil, tempfile, unittest
from pathlib import Path

from sdem import acceptance, aid
from sdem.aid import LOW
from sdem.rules_engine import EVIDENCE_CLASSES, RulesEngine, Run, strongest
from sdem.validate import check_schema

ROOT = Path(__file__).resolve().parents[1]


class EngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.results = {}
        for case in acceptance.load_cases():
            cls.results[case['id']] = RulesEngine().infer(acceptance.open_case(case, cls.tmp), case)

    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_every_proposal_and_candidate_has_a_class(self):                            # AID-E01
        n = 0
        for res in self.results.values():
            for m in (res.get('proposals') or []) + (res.get('candidates') or []):
                self.assertIn(m.get('evidence_class'), EVIDENCE_CLASSES, m['mapping_id']); n += 1
        self.assertGreater(n, 100)

    def test_the_class_follows_the_rule_not_the_words(self):
        e = Run.evidence_class
        self.assertEqual(e('S32', 1, 'data join; …'), 'attribute_join')
        self.assertEqual(e('S06', 4, "verb and noun match: 'x' ~ 'y'"), 'name_token')
        self.assertEqual(e('S17', 4, 'fallback B: asset-type tokens'), 'name_token')
        self.assertEqual(e('S17', 3, 'fallback A (information perspective): accesses …'), 'structural')   # attributes, not a name
        self.assertEqual(e('S01', 5, 'shared description words'), 'text')
        self.assertEqual(e('DESIGN', 'design', 'one component per Service Domain'), 'pattern')
        self.assertEqual(strongest('text', 'structural', None), 'structural')

    def test_a_derived_link_is_no_stronger_than_what_it_rests_on(self):
        s04 = [m for res in self.results.values() for m in res.get('proposals') or [] if m['evidence'][0].startswith('engine_rationale:S04')]
        self.assertTrue(s04)
        for m in s04:   # an invokes field names the operation, or only an S06 name match does
            self.assertEqual(m['evidence_class'], 'attribute_join' if '.invokes)' in m['rationale'] else 'name_token', m['rationale'])

    def test_registry_schema_accepts_the_class(self):
        schema = json.loads((ROOT / 'schema' / 'relationship-registry.schema.json').read_text())
        m = next(iter(self.results.values()))['proposals'][0]
        self.assertEqual(check_schema(m, schema['$defs']['mapping'], schema), [])
        self.assertTrue(check_schema({**m, 'evidence_class': 'hunch'}, schema['$defs']['mapping'], schema))


class AidTests(unittest.TestCase):
    def test_weak_is_read_from_the_class_when_there_is_one(self):                       # AID-B6 by class
        fallback_a = {'confidence': 0.6, 'evidence': ['engine_rationale:S17 step3 fallback A (information perspective): …'], 'evidence_class': 'structural'}
        self.assertFalse(aid.is_weak(fallback_a)); self.assertEqual(aid.conf_of(fallback_a), 0.6)
        name = {'confidence': 0.6, 'evidence': ['engine_rationale:S06 step4 shared words'], 'evidence_class': 'name_token'}
        self.assertTrue(aid.is_weak(name)); self.assertEqual(aid.conf_of(name), LOW)
        old = {'confidence': 0.6, 'evidence': ['engine_rationale:S17 step4 fallback B: tokens']}   # a package from before AID-E01
        self.assertTrue(aid.is_weak(old))

    def test_projected_elements_carry_their_class_and_check_reads_it(self):
        ex = ROOT / 'examples' / 'payment-initiation'
        have = {l: json.loads((ex / f).read_text()) for l, f in (('A2', 'a2-service-domain.json'),)}
        pkg = aid.project(have)
        els = [r for d in pkg['layers'].values() for r in d['instances']] + pkg['links']['links']
        self.assertTrue(els)
        self.assertTrue(all(r['projection'].get('evidence_class') in EVIDENCE_CLASSES for r in els), [r['projection'] for r in els if 'evidence_class' not in r['projection']][:2])
        self.assertEqual(aid.check(pkg), [])
        bad = json.loads(json.dumps(pkg)); l = bad['links']['links'][0]
        l['confidence'] = l['projection']['confidence'] = 0.6; l['projection']['evidence_class'] = 'name_token'
        self.assertTrue(any('name-only evidence above low' in i for i in aid.check(bad)))


class CalibrationTests(unittest.TestCase):
    def test_observed_precision_per_band_and_class(self):                               # AID-E03 (OPEN-06)
        r = acceptance.calibrate(ids=['M1', 'C1'])
        self.assertTrue(r['band']); self.assertTrue(r['evidence_class'])
        for row in r['band'] + r['evidence_class']:
            self.assertGreater(row['proposed'], 0); self.assertTrue(0 <= row['precision'] <= 1); self.assertLessEqual(row['right'], row['proposed'])
        self.assertIn('not a setting', r['note'])
        self.assertIn('by evidence class', acceptance.render_calibration(r)); self.assertIn('cases', r['blind'])


class BlindCaseTests(unittest.TestCase):
    def test_the_blind_case_is_scored_apart_with_precision_and_recall(self):          # AID-E04
        cases = acceptance.load_cases(blind=True)
        self.assertTrue(cases)
        for c in cases:
            readme = (ROOT / 'examples' / c['estate'] / 'README.md').read_text(encoding='utf-8')
            self.assertIn('synthetic', readme.lower())
            self.assertFalse(any(x['id'] == c['id'] for x in acceptance.load_cases()), 'a blind case is not an acceptance case')
        r = acceptance.calibrate(ids=[cases[0]['id']])
        b = r['blind']['cases'][0]
        self.assertEqual(r['band'], [])                                                  # no acceptance case asked for
        self.assertGreater(b['gold'], 0); self.assertTrue(0 < b['precision'] <= 1); self.assertTrue(0 < b['recall'] <= 1)
        self.assertEqual(b['right'] + len(b['missed']), b['gold'])
        self.assertIn('Blind cases', acceptance.render_calibration(r))

if __name__ == '__main__':
    unittest.main()
