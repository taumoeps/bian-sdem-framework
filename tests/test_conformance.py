"""Data-model conformance (sdem/conformance.py): each enforced rule rejects a bad architecture dataset and accepts the examples."""
import copy, glob, json, unittest
from pathlib import Path

from sdem.conformance import check_level, estate_index
from sdem.graph import FederatedGraph
from sdem.metamodel import Metamodel

ROOT = Path(__file__).resolve().parents[1]
PAY = ROOT / 'examples' / 'payment-initiation'


def _j(p): return json.loads(Path(p).read_text(encoding='utf-8'))


class ConformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mm = Metamodel.load()
        cls.a1 = _j(PAY / 'a1-business.json'); cls.a2 = _j(PAY / 'a2-service-domain.json'); cls.a3 = _j(PAY / 'a3-application.json')

    def _errors(self, doc, *others):
        return check_level(doc, self.mm, estate_index([doc, *others]))[0]

    def _set(self, doc, iid, **attrs):
        d = copy.deepcopy(doc)
        for i in d['instances']:
            if i['id'] == iid: i.setdefault('attributes', {}).update(attrs)
        return d

    def test_examples_have_no_errors(self):
        for est in sorted(glob.glob(str(ROOT / 'examples' / '*') + '/')):
            docs = [_j(f) for f in sorted(glob.glob(est + 'a[1-4]-*.json'))]; idx = estate_index(docs)
            for d in docs: self.assertEqual(check_level(d, self.mm, idx)[0], [], f"{est} {d['level']}")

    def test_lc04_bian_domain_not_known_yet(self):  # metamodel DA2-02: required unless classification is 'unknown'
        sd = next(i['id'] for i in self.a2['instances'] if i['type'] == 'A2.ServiceDomain')
        bare = copy.deepcopy(self.a2)
        for i in bare['instances']:
            if i['id'] == sd: i['attributes'] = {k: v for k, v in i.get('attributes', {}).items() if k not in ('asset_type', 'functional_pattern')}
        e = self._errors(bare)   # no values and not marked unknown: rejected
        self.assertTrue(any('LC-04' in x and "'asset_type'" in x for x in e) and any("'functional_pattern'" in x for x in e), e)
        marked = self._set(bare, sd, classification='unknown')
        errors, warnings, _ = check_level(marked, self.mm, estate_index([marked]))
        self.assertFalse([x for x in errors if 'LC-04' in x], errors)   # marked unknown: accepted, with advice
        self.assertTrue(any('not known yet' in w and "'asset_type'" in w for w in warnings), warnings)
        e = self._errors(self._set(bare, sd, classification='maybe'))   # an unknown value of the enumeration is still refused
        self.assertTrue(any('LC-06' in x for x in e) or any('LC-04' in x for x in e), e)

    def test_lc05_wrong_type(self):
        e = self._errors(self._set(self.a1, 'PRC-PAY-01', level='two'))
        self.assertTrue(any('LC-05' in x and "'level'" in x for x in e), e)

    def test_lc05_bad_date_and_bool_as_integer(self):
        e = self._errors(self._set(self.a1, 'PRC-PAY-01', modified='30/09/2026', level=True))
        self.assertEqual(sum('LC-05' in x for x in e), 2, e)

    def test_lc05_integer_range(self):
        e = self._errors(self._set(self.a1, 'CAP-PAY-010', maturity_current=7))
        self.assertTrue(any('LC-05' in x and 'maturity_current' in x for x in e), e)

    def test_lc06_value_not_allowed(self):
        e = self._errors(self._set(self.a1, 'PRC-PAY-01', criticality='urgent'))
        self.assertTrue(any('LC-06' in x and 'urgent' in x for x in e), e)

    def test_lc06_lifecycle(self):
        d = copy.deepcopy(self.a1); d['instances'][0]['lifecycle_status'] = 'live'
        self.assertTrue(any('LC-06' in x and 'live' in x for x in self._errors(d)))

    def test_lc07_same_level_reference(self):
        e = self._errors(self._set(self.a1, 'PRC-PAY-01', owner='ROLE-MISSING'))
        self.assertTrue(any('LC-07' in x and 'ROLE-MISSING' in x for x in e), e)
        e = self._errors(self._set(self.a1, 'PRC-PAY-01', owner='BO-PAYEE'))  # exists, but not an actor or role
        self.assertTrue(any('LC-07' in x and 'BO-PAYEE' in x for x in e), e)

    def test_lc04_required(self):
        d = copy.deepcopy(self.a2)
        for i in d['instances']:
            if i['id'] == 'SD-PI': del i['attributes']['asset_type']
        self.assertTrue(any('LC-04' in x and 'asset_type' in x for x in self._errors(d)))

    def test_lc04_planned_instance_warns(self):
        d = copy.deepcopy(self.a2)
        for i in d['instances']:
            if i['id'] == 'SD-PI': del i['attributes']['asset_type']; i['lifecycle_status'] = 'planned'
        errors, warnings, _ = check_level(d, self.mm, estate_index([d]))
        self.assertFalse(any('LC-04' in x for x in errors)); self.assertTrue(any('LC-04' in w and 'asset_type' in w for w in warnings))

    def test_lc08_cross_level_reference_is_a_warning(self):
        d = self._set(self.a2, 'SD-PI', owner='ROLE-MISSING')  # owner refers to an A1 actor or role
        errors, warnings, _ = check_level(d, self.mm, estate_index([d, self.a1]))
        self.assertFalse(any('LC-08' in x for x in errors)); self.assertTrue(any('LC-08' in x and 'ROLE-MISSING' in x for x in warnings), warnings)
        _, warnings, _ = check_level(d, self.mm, estate_index([d]))  # A1 not loaded: nothing to check against
        self.assertFalse(any('LC-08' in x for x in warnings))

    def test_lc10_cardinality_maximum(self):
        d = copy.deepcopy(self.a2)
        sg = next(r for r in d['relationships'] if r['kind'] == 'composition' and r['target'].startswith('SG-'))
        d['relationships'].append({**sg, 'source': 'SD-PE'})  # the same service group in a second Service Domain
        self.assertTrue(any('LC-10' in x for x in self._errors(d)), self._errors(d))

    def test_undefined_and_deprecated_are_warnings(self):
        d = self._set(self.a1, 'PRC-PAY-01', colour='blue')
        errors, warnings, _ = check_level(d, self.mm, estate_index([d]))
        self.assertEqual(errors, []); self.assertTrue(any("'colour'" in w for w in warnings))

    def test_check_command_fails_on_error(self):
        d = self._set(self.a1, 'PRC-PAY-01', criticality='urgent')
        fg = FederatedGraph.load([PAY / 'a2-service-domain.json', PAY / 'mappings.json'])
        from sdem.graph import LevelGraph
        fg.levels['A1'] = LevelGraph(d, fg.mm)
        report = fg.check()
        self.assertTrue(any('LC-06' in x for x in report['level A1 (' + d['model_id'] + ')']))


class PhysicalDataModelTests(unittest.TestCase):
    """The per-entity JSON Schemas (sdem/physical.py) are current, carry provenance, accept the examples and reject bad records."""

    @classmethod
    def setUpClass(cls):
        import glob
        cls.S = {json.loads(Path(p).read_text(encoding='utf-8'))['title']: json.loads(Path(p).read_text(encoding='utf-8')) for p in glob.glob(str(ROOT / 'schema/entities/*/*.schema.json'))}

    def test_current(self):
        from sdem.physical import main
        self.assertEqual(main(['--check']), 0)

    def test_one_schema_per_instance_type(self):
        mm = Metamodel.load()
        self.assertEqual(set(self.S), {t for t, e in mm.entities.items() if not e.get('abstract') and not e.get('artefact')})

    def test_every_property_carries_source_reasoning_confidence(self):
        for t, s in self.S.items():
            props = {k: v for k, v in s['properties'].items() if k != 'attributes'}; props.update(s['properties']['attributes']['properties'])
            for k, p in props.items():
                for x in ('x-sdem-source', 'x-sdem-reasoning', 'x-sdem-confidence'): self.assertIn(x, p, f'{t}.{k} {x}')
            for x in ('source', 'reasoning', 'confidence'): self.assertIn(x, s['x-sdem-entity'], f'{t} entity {x}')

    def test_examples_validate_and_bad_records_fail(self):
        import glob
        from sdem.validate import check_schema
        for f in glob.glob(str(ROOT / 'examples/*/a[1-4]-*.json')):
            for i in json.loads(Path(f).read_text(encoding='utf-8'))['instances']:
                self.assertEqual(check_schema(i, self.S[i['type']]), [], f"{f} {i['id']}")
        s = self.S['A1.BusinessProcess']; ok = {'id': 'P1', 'type': 'A1.BusinessProcess', 'version': '1', 'name': 'p'}
        for bad in ({'criticality': 'urgent'}, {'level': 'two'}, {'modified': '30/09/2026'}, {'owner': 3}):
            self.assertTrue(check_schema({**ok, 'attributes': bad}, s), bad)
        self.assertTrue(check_schema({**ok, 'type': 'A1.BusinessService'}, s))
        self.assertTrue(check_schema({**ok, 'type': 'A1.BusinessCapability', 'attributes': {'maturity_current': 9}}, self.S['A1.BusinessCapability']))


if __name__ == '__main__':
    unittest.main()
