"""Missing information and duplicate keys (owner's decisions D1 and D6, 2026-11-09; LC-04, LC-09, LC-09n in sdem/logical.py):
a placeholder or empty string in a required attribute is not a value; a key held as a whole-part link is compared; near-duplicate names are said."""
import copy, json, unittest
from pathlib import Path

from sdem.conformance import check_level, estate_index, unknown_value
from sdem.metamodel import Metamodel

ROOT = Path(__file__).resolve().parents[1]
PAY = ROOT / 'examples' / 'payment-initiation'


def _j(p): return json.loads(Path(p).read_text(encoding='utf-8'))


class CompletenessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mm = Metamodel.load(); cls.a2 = _j(PAY / 'a2-service-domain.json'); cls.a3 = _j(PAY / 'a3-application.json')

    def _check(self, doc): return check_level(doc, self.mm, estate_index([doc]))[:2]

    def _with(self, iid, status=None, **attrs):
        d = copy.deepcopy(self.a3)
        for i in d['instances']:
            if i['id'] == iid:
                i['attributes'].update(attrs)
                if status: i['lifecycle_status'] = status
        return d

    def test_what_says_nothing(self):
        for v in ('TBD', ' tbd ', 'Unknown', '?', '/TBD', '/payments/tbd/x', '', '   ', ['TBD'], ['x', 'TODO']):
            self.assertTrue(unknown_value(v), v)
        for v in ('/payments', 'POST', 'unknown-payee', [], ['amount'], 0, False, {'a': 'b'}, 'n/a-ish text'):
            self.assertIsNone(unknown_value(v), v)
        self.assertIsNone(unknown_value('TBD', allowed=('TBD',)))   # an allowed enumeration value is a value

    def test_a_placeholder_is_an_error_on_an_active_record(self):      # O9 reproduced
        errs, _ = self._check(self._with('API-PI-01', path='TBD', payload_fields=['TBD']))
        self.assertTrue(any("API-PI-01: required attribute 'path' has no value" in e and 'LC-04' in e for e in errs), errs)
        self.assertTrue(any("'payload_fields'" in e for e in errs))
        errs, _ = self._check(self._with('API-PI-01', path=''))
        self.assertTrue(any("'path' has no value" in e and 'empty' in e for e in errs))

    def test_on_a_planned_record_it_is_a_warning(self):
        errs, warns = self._check(self._with('API-PI-01', status='planned', path='TBD'))
        self.assertFalse(any('API-PI-01' in e for e in errs), errs)
        self.assertTrue(any("API-PI-01: planned instance — required attribute 'path' not yet known" in w for w in warns))

    def test_leaving_it_out_on_a_planned_record_is_the_way(self):
        d = copy.deepcopy(self.a3)
        for i in d['instances']:
            if i['id'] == 'API-PI-01': i['lifecycle_status'] = 'planned'; i['attributes'].pop('path')
        errs, warns = self._check(d)
        self.assertFalse(any('API-PI-01' in e for e in errs)); self.assertTrue(any("'path' not yet known (LC-04)" in w for w in warns))

    def test_a_placeholder_in_an_optional_attribute_is_a_warning(self):
        errs, warns = self._check(self._with('API-PI-01', operation_id='TBD'))
        self.assertFalse(any('API-PI-01' in e for e in errs))
        self.assertTrue(any("optional attribute 'operation_id' is a placeholder" in w for w in warns), warns)

    def test_an_empty_list_is_a_value(self):
        errs, warns = self._check(self._with('API-PI-01', payload_fields=[]))
        self.assertFalse(any('API-PI-01' in x for x in errs + warns))

    def test_an_api_operation_key_includes_its_interface(self):         # LC-09 was never evaluated for this type
        d = copy.deepcopy(self.a3); op = next(i for i in d['instances'] if i['id'] == 'API-PI-01')
        dup = {**copy.deepcopy(op), 'id': 'API-PI-01B', 'name': 'Create payment instruction again'}
        d['instances'].append(dup)
        self.assertFalse(any('LC-09' in e for e in self._check(d)[0]), 'no owner: the key is not complete')
        d['relationships'].append({'source': 'IFC-PAY-API', 'kind': 'composition', 'target': 'API-PI-01B'})
        self.assertTrue(any('2 instances of A3.APIOperation share the natural key "IFC-PAY-API", "POST", "/payment-instructions" (LC-09)' in e for e in self._check(d)[0]))

    def test_a_service_operation_key_reaches_its_domain_through_its_group(self):
        d = copy.deepcopy(self.a2); so = next(i for i in d['instances'] if i['id'] == 'SO-PI-01')
        d['instances'].append({**copy.deepcopy(so), 'id': 'SO-PI-01B', 'canonical_id': 'SO-PI-01B'})
        grp = next(r['source'] for r in d['relationships'] if r['target'] == 'SO-PI-01' and r['kind'] == 'composition')
        d['relationships'].append({'source': grp, 'kind': 'composition', 'target': 'SO-PI-01B'})
        self.assertTrue(any('A2.ServiceOperation share the natural key "SD-PI"' in e for e in self._check(d)[0]), self._check(d)[0])

    def test_names_that_differ_only_in_case_or_spacing_are_a_possible_duplicate(self):
        d = copy.deepcopy(self.a3); c = next(i for i in d['instances'] if i['type'] == 'A3.ApplicationComponent')
        d['instances'].append({**copy.deepcopy(c), 'id': c['id'] + '-2', 'name': '  ' + c['name'].upper() + '.'})
        errs, warns = self._check(d)
        self.assertFalse(any('LC-09)' in e for e in errs))
        self.assertTrue(any('possible duplicate: A3.ApplicationComponent' in w and '(LC-09n)' in w for w in warns), warns)

    def test_the_examples_stay_clean(self):
        for ws in sorted(p for p in (ROOT / 'examples').iterdir() if (p / 'mappings.json').exists()):
            docs = [_j(f) for f in sorted(ws.glob('a[1-4]-*.json'))]; idx = estate_index(docs)
            for d in docs:
                errs, warns = check_level(d, self.mm, idx)[:2]
                self.assertEqual(errs, [], ws.name)
                self.assertFalse([w for w in warns if 'LC-09n' in w or 'optional attribute' in w], ws.name)


if __name__ == '__main__':
    unittest.main()
