"""Metamodel 0.15.0, slice 1 — the information model (docs/design/sdem-full-design-metamodel-design.md, IM-01…IM-09, CT-01…CT-04;
the owner's decisions D1–D8, 2026-11-16). Made-up data only."""
import copy, json, tempfile, unittest
from pathlib import Path
from sdem.metamodel import Metamodel
from sdem.graph import FederatedGraph

ROOT = Path(__file__).resolve().parents[1]
import sys as _s2, pathlib as _pl2; _s2.path.insert(0, str(_pl2.Path(__file__).resolve().parent)); from needs import EXAMPLES  # noqa: E402 — SDEM's examples and sdem-bian's (R-D6)
TYPED = ROOT / 'tests/fixtures/bian-release-typed'


def level(code, instances, relationships=()):
    return {'level': code, 'model_id': f'test-{code.lower()}', 'model_version': '1', 'metamodel_version': Metamodel.load().version,
            'source_system': 'TEST', 'instances': instances, 'relationships': list(relationships)}


def rec(id_, type_, name, **attrs):
    return {'id': id_, 'type': type_, 'version': '1', 'name': name, 'lifecycle_status': 'active', **({'attributes': attrs} if attrs else {})}


import sys as _s, pathlib as _pl; _s.path.insert(0, str(_pl.Path(__file__).resolve().parent)); from needs import bian as _needs_bian  # noqa: E402 — BX-15: tests that need sdem-bian

@_needs_bian
class MetamodelTests(unittest.TestCase):
    def test_the_information_model_is_in_the_metamodel(self):   # IM-02 … IM-05, CT-03, CT-04
        mm = Metamodel.load()
        self.assertIn('A3.DataAttribute', mm.entities)
        for s, k, t in [('A1.BusinessObject', 'association', 'A1.BusinessObject'), ('A2.BusinessObject', 'association', 'A2.BusinessObject'),
                        ('A2.BusinessObject', 'specialization', 'A2.BusinessObject'), ('A2.BusinessObjectAttribute', 'association', 'A2.BusinessObject'),
                        ('A2.ServiceOperation', 'access', 'A2.BusinessObject'), ('A3.DataEntity', 'association', 'A3.DataEntity'),
                        ('A3.DataEntity', 'composition', 'A3.DataAttribute'), ('A3.DataAttribute', 'association', 'A3.DataEntity')]:
            self.assertIsNone(mm.relationship_issue(s[:2], s, k, t), (s, k, t))
        ea = json.loads((ROOT / 'metamodel/entity-attributes.json').read_text(encoding='utf-8'))['attributes']
        names = {(a['entity'], a['name']) for a in ea}
        for x in [('A3.DataAttribute', 'physical_type'), ('A3.DataAttribute', 'primary_key'), ('A3.APIOperation', 'request_fields'),
                  ('A3.APIOperation', 'response_fields'), ('A4.Path', 'carries_data')]:
            self.assertIn(x, names)
        # FIELD_MAPPED_TO (A2.BusinessObjectAttribute → A3.DataAttribute) is BIAN's link type: sdem-bian's since 0.22 (BX-15)

    def test_stricter_attributes_report_old_data_never_refuse_it(self):   # FD-P2
        from sdem.conformance import check_level
        mm = Metamodel.load()
        old = level('A2', [rec('BO-1', 'A2.BusinessObject', 'Payment', attributes=['amount']), rec('BOA-1', 'A2.BusinessObjectAttribute', 'amount', data_type='Amount')],
                    [{'source': 'BO-1', 'kind': 'composition', 'target': 'BOA-1'}])
        errors, warnings, _ = check_level(old, mm)
        self.assertEqual(errors, []); self.assertTrue(any("'data_type' value 'Amount'" in w for w in warnings))
        from sdem.physical import schema_for, _j, MM_DIR
        sch = schema_for(mm, 'A2.BusinessObjectAttribute', _j(MM_DIR / 'entity-attributes.json')['core_fields'])
        self.assertNotIn('enum', sch['properties']['attributes']['properties']['data_type'])   # the generated schema reports it too, never enforces it


class ChecksTests(unittest.TestCase):   # IM-08: LC-23 … LC-27
    def graph(self, a2, a3, mappings=()):
        tmp = Path(tempfile.mkdtemp())
        (tmp / 'a2.json').write_text(json.dumps(a2)); (tmp / 'a3.json').write_text(json.dumps(a3))
        (tmp / 'm.json').write_text(json.dumps({'registry_version': '1', 'mappings': list(mappings)}))
        return FederatedGraph.load([tmp / 'a2.json', tmp / 'a3.json', tmp / 'm.json'])

    def test_a_column_whose_type_cannot_hold_what_its_name_says(self):   # LC-29 — the public twin's first run, F7 (2026-11-17)
        F = lambda i, name, pt: rec(i, 'A3.DataAttribute', name, physical_type=pt)
        cols = [F('F-1', 'amount', 'date'), F('F-2', 'currency', 'boolean'), F('F-3', 'consent_id', 'numeric(18,2)'), F('F-4', 'expires_at', 'varchar(20)'),
                F('F-5', 'amount', 'numeric(18,2)'), F('F-6', 'currency', 'char(3)'), F('F-7', 'consent_id', 'uuid'), F('F-8', 'payment_id', 'bigint'), F('F-9', 'created_at', 'timestamptz'),
                F('F-10', 'payment_status', 'varchar(40)'), F('F-11', 'key_hash', 'char(64)'), F('F-12', 'paymentAmount', 'timestamp'), F('F-13', 'amount', 'custom_money_type')]
        a3 = level('A3', [rec('ENT-1', 'A3.DataEntity', 't', attributes=[c['name'] for c in cols])] + cols, [{'source': 'ENT-1', 'kind': 'composition', 'target': c['id']} for c in cols])
        fg = self.graph(level('A2', [], []), a3); fg.check()
        w = [x for v in fg.warnings.values() for x in v if 'LC-29' in x]
        self.assertEqual(sorted(x.split(':')[0].replace('instance ', '') for x in w), ['F-1', 'F-12', 'F-2', 'F-3', 'F-4'])   # the unmistakable ones only; an unknown type is not judged
        self.assertIn('F-1: is named as an amount (amount) but its type is date — check the type, or the name (LC-29)', ' '.join(w))

    def test_thin_disagreeing_keyless_and_mistyped(self):
        a2 = level('A2', [rec('BO-1', 'A2.BusinessObject', 'Payment', attributes=['amount', 'value_date']),
                          rec('BOA-1', 'A2.BusinessObjectAttribute', 'amount', data_type='amount'),
                          rec('BO-2', 'A2.BusinessObject', 'Party', attributes=['name'])],
                    [{'source': 'BO-1', 'kind': 'composition', 'target': 'BOA-1'}])
        a3 = level('A3', [rec('ENT-1', 'A3.DataEntity', 'payment', attributes=['amount', 'account_id'], system_of_record=True),
                          rec('F-1', 'A3.DataAttribute', 'amount', physical_type='date'), rec('F-2', 'A3.DataAttribute', 'account_id', physical_type='varchar(34)'),
                          rec('ENT-2', 'A3.DataEntity', 'account', attributes=['iban'])],
                    [{'source': 'ENT-1', 'kind': 'composition', 'target': 'F-1'}, {'source': 'ENT-1', 'kind': 'composition', 'target': 'F-2'},
                     {'source': 'F-2', 'kind': 'association', 'target': 'ENT-2'}])
        m = {'mapping_id': 'M-1', 'source': {'id': 'BOA-1', 'type': 'A2.BusinessObjectAttribute', 'version': '1'}, 'relationship': 'FIELD_MAPPED_TO',
             'target': {'id': 'F-1', 'type': 'A3.DataAttribute', 'version': '1'}, 'status': 'proposed'}
        fg = self.graph(a2, a3, [m]); fg.check()
        w = ' | '.join(x for v in fg.warnings.values() for x in v)
        self.assertIn('BO-1: its field names and its field records disagree — no record for value_date (LC-24)', w)
        self.assertIn('BO-2: is thin', w); self.assertIn('(LC-23)', w)
        self.assertIn('ENT-1: is a system of record but none of its fields is a primary key (LC-25)', w)
        self.assertIn('F-2: is a foreign key to ENT-2, which has no primary key (LC-26)', w)
        self.assertIn('F-1: holds BOA-1 (amount) as date — the types do not match (LC-27)', w)


class BianImportTests(unittest.TestCase):   # IM-09
    def setUp(self):
        from sdem import profile as _p; _p.deactivate()   # 0.22 (BX-15): outside a workspace, as a command run alone (BX-12)

    def test_objects_come_typed_with_their_references_and_values(self):
        try: from sdem_bian.bian import main
        except ImportError: self.skipTest('needs sdem-bian installed (BX-15)')
        out = Path(tempfile.mkdtemp()) / 'a2.json'
        import io, contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['import', str(TYPED), '--all', '--objects', '-o', str(out)]), 0)
        d = json.loads(out.read_text(encoding='utf-8')); i = {x['id']: x for x in d['instances']}
        a = lambda k: i[f'BBOA-PAYMENT-TRANSACTION-{k}']['attributes']
        self.assertEqual((a('PAYMENT-TRANSACTION-IDENTIFICATION')['data_type'], a('PAYMENT-TRANSACTION-IDENTIFICATION')['required'],
                          a('PAYMENT-TRANSACTION-IDENTIFICATION')['identifier']), ('string', True, True))
        self.assertEqual(a('PAYMENT-TRANSACTION-AMOUNT')['data_type'], 'amount')
        self.assertEqual(a('PAYMENT-TRANSACTION-VALUE-DATE')['data_type'], 'date')
        self.assertEqual(a('PAYMENT-TRANSACTION-CREATED')['data_type'], 'datetime')
        self.assertEqual(a('PAYMENT-TRANSACTION-STATUS')['allowed_values'], ['Pending', 'Accepted', 'Rejected', 'Settled'])
        self.assertEqual(a('PAYMENT-TRANSACTION-CHARGES')['multiplicity'], '0..n')
        rels = {(r['source'], r['kind'], r['target']) for r in d['relationships']}
        self.assertIn(('BBOA-PAYMENT-TRANSACTION-PAYMENT-TRANSACTION-PAYER', 'association', 'BBO-PARTY'), rels)
        self.assertIn(('BBO-PAYMENT-TRANSACTION', 'association', 'BBO-PARTY'), rels)
        self.assertNotIn('BBO-CURRENCY-AMOUNT', i)   # an amount is a type, not an object

    def test_the_base_still_ships_no_objects(self):   # BB-D2 unchanged
        try: from sdem_bian.bian import pack, read_domain
        except ImportError: self.skipTest('needs sdem-bian installed (BX-15)')
        self.assertNotIn('object_fields', pack([read_domain(TYPED / 'SamplePaymentOrder.yaml')])['domains'][0])


@_needs_bian
class AidTests(unittest.TestCase):   # IM-10: AID-I01 … I04
    def test_no_table_is_inferred_for_an_object_whose_domain_nothing_here_realises(self):   # AID-I08 — the public twin's first run, F4 (2026-11-17)
        try: from sdem_bian.aid_bian import propose_information
        except ImportError: self.skipTest('needs sdem-bian installed: AID-I01…I07 are BIAN\'s (BX-15)')
        R = lambda i, t, **a: {'id': i, 'type': t, 'version': '1', 'name': i, 'attributes': a}
        a2 = {'instances': [R('SD-1', 'A2.ServiceDomain'), R('CR-1', 'A2.ControlRecord'), R('BO-1', 'A2.BusinessObject'), R('BOA-1', 'A2.BusinessObjectAttribute', data_type='identifier', identifier=True)],
              'relationships': [{'source': 'SD-1', 'kind': 'aggregation', 'target': 'CR-1'}, {'source': 'CR-1', 'kind': 'association', 'target': 'BO-1'}, {'source': 'BO-1', 'kind': 'composition', 'target': 'BOA-1'}]}
        app = {'instances': [R('APP-1', 'A3.ApplicationComponent')], 'relationships': []}
        mark = lambda rule, why, frm: {'rule': rule}
        inst, rels, links, skipped = propose_information(a2, app, [], mark)
        self.assertEqual((inst, links), ([], [])); self.assertEqual([s['id'] for s in skipped], ['BO-1'])   # applications exist, none realises SD-1: said, not inferred
        realised = [{'source': {'id': 'SD-1', 'type': 'A2.ServiceDomain'}, 'relationship': 'REALIZED_BY', 'target': {'id': 'APP-1', 'type': 'A3.ApplicationComponent'}, 'status': 'proposed'}]
        inst, rels, links, skipped = propose_information(a2, app, realised, mark)
        self.assertEqual(([i['id'] for i in inst][0], skipped), ('AID-ENT-BO-1', []))
        inst, rels, links, skipped = propose_information(a2, {'instances': [], 'relationships': []}, [], mark)   # no applications yet (AID builds the layer): as before
        self.assertEqual(([i['id'] for i in inst][0], skipped), ('AID-ENT-BO-1', []))

    def test_aid_infers_entities_fields_keys_and_proposes_the_links(self):
        import shutil
        from sdem.aid_fill import fill
        ws = Path(tempfile.mkdtemp()) / 'ws'; shutil.copytree(EXAMPLES / 'payment-initiation', ws)
        p = ws / 'a2-service-domain.json'; d = json.loads(p.read_text(encoding='utf-8'))
        F = [('PaymentInstructionReference', 'identifier', True, True), ('DebtorAccountReference', 'reference', True, False), ('Amount', 'amount', True, False), ('ValueDate', 'date', False, False)]
        bo = next(i for i in d['instances'] if i['id'] == 'BBO-PAY-INSTR'); bo['attributes']['attributes'] = [f[0] for f in F]
        d['instances'] = [i for i in d['instances'] if i['id'] != 'BBOA-AMOUNT']
        d['relationships'] = [r for r in d['relationships'] if not (r['source'] == 'BBO-PAY-INSTR' and r['kind'] == 'composition')]
        for n, t, req, ident in F:
            d['instances'].append(rec(f'BBOA-PI-{n.upper()}', 'A2.BusinessObjectAttribute', n, data_type=t, required=req, **({'identifier': True} if ident else {})))
            d['relationships'].append({'source': 'BBO-PAY-INSTR', 'kind': 'composition', 'target': f'BBOA-PI-{n.upper()}'})
        d['relationships'].append({'source': 'BBOA-PI-DEBTORACCOUNTREFERENCE', 'kind': 'association', 'target': 'BBO-PARTY'})
        next(i for i in d['instances'] if i['id'] == 'BBOA-PARTY-REF')['attributes']['identifier'] = True
        p.write_text(json.dumps(d), encoding='utf-8')
        m = ws / 'mappings.json'; md = json.loads(m.read_text(encoding='utf-8'))
        md['mappings'] = [x for x in md['mappings'] if x['relationship'] != 'MAPPED_TO']; m.write_text(json.dumps(md), encoding='utf-8')
        run = fill(ws, 'a tester', now='2026-11-16T00:00:00+00:00')
        a3 = json.loads((ws / 'a3-application.json').read_text(encoding='utf-8')); i = {x['id']: x for x in a3['instances']}
        self.assertEqual(i['AID-ENT-PAYMENT-INSTRUCTION']['attributes']['inferred']['rule'], 'AID-I01')
        key = i['AID-ENTF-PAYMENT-INSTRUCTION-PAYMENTINSTRUCTIONREFERENCE']['attributes']
        self.assertEqual((key['primary_key'], key['required'], key['physical_type']), (True, True, 'varchar(35)'))
        self.assertEqual(i['AID-ENTF-PAYMENT-INSTRUCTION-AMOUNT']['attributes']['physical_type'], 'numeric(18,2)')
        rels = {(r['source'], r['kind'], r['target']) for r in a3['relationships']}
        self.assertIn(('AID-ENTF-PAYMENT-INSTRUCTION-DEBTORACCOUNTREFERENCE', 'association', 'AID-ENT-PARTY'), rels)   # AID-I02: a foreign key
        props = json.loads((ws / run['proposals']).read_text(encoding='utf-8'))['mappings']
        got = {(x['source']['id'], x['relationship'], x['target']['id']) for x in props}
        self.assertIn(('BBO-PAY-INSTR', 'MAPPED_TO', 'AID-ENT-PAYMENT-INSTRUCTION'), got)
        self.assertIn(('BBOA-PI-AMOUNT', 'FIELD_MAPPED_TO', 'AID-ENTF-PAYMENT-INSTRUCTION-AMOUNT'), got)
        self.assertTrue(all(x['status'] == 'proposed' for x in props))                      # AID-I03: never approved by SDEM


class RealBianShapesTests(unittest.TestCase):   # found importing BIAN 14.0.0's payment files (2026-11-16)
    def setUp(self):
        from sdem import profile as _p; _p.deactivate()   # 0.22 (BX-15): outside a workspace, as a command run alone (BX-12)

    def test_a_field_is_named_within_its_object_and_bian_data_types_are_types(self):
        try: from sdem_bian.bian import _fields, DATATYPES
        except ImportError: self.skipTest('needs sdem-bian installed (BX-15)')
        doc = {'components': {'schemas': {
            'Payment': {'type': 'object', 'properties': {'PaymentIdentification': {'$ref': '#/components/schemas/Identifier'}, 'Booked': {'$ref': '#/components/schemas/Datetime'}}},
            'Refund': {'type': 'object', 'properties': {'PaymentIdentification': {'$ref': '#/components/schemas/Identifier'}}},
            'Identifier': {'type': 'object', 'properties': {'IdentifierValue': {'type': 'string'}}}, 'Datetime': {'type': 'object', 'properties': {'DateTimeContent': {'type': 'string'}}}}}}
        self.assertEqual([f['data_type'] for f in _fields(doc, 'Payment')], ['identifier', 'datetime'])
        self.assertIn('Identifier', DATATYPES)
        mm = Metamodel.load()
        self.assertEqual(mm.entities['A2.BusinessObjectAttribute']['identifier']['key'], ['owning business object', 'name'])
        self.assertEqual(mm.entities['A3.DataAttribute']['identifier']['key'], ['owning data entity', 'name'])
        from sdem.conformance import check_level
        two = level('A2', [rec('BO-1', 'A2.BusinessObject', 'Payment', attributes=['PaymentIdentification']), rec('BO-2', 'A2.BusinessObject', 'Refund', attributes=['PaymentIdentification']),
                           rec('F-1', 'A2.BusinessObjectAttribute', 'PaymentIdentification', data_type='identifier'), rec('F-2', 'A2.BusinessObjectAttribute', 'PaymentIdentification', data_type='identifier')],
                    [{'source': 'BO-1', 'kind': 'composition', 'target': 'F-1'}, {'source': 'BO-2', 'kind': 'composition', 'target': 'F-2'}])
        errors, _, _ = check_level(two, mm)
        self.assertEqual([e for e in errors if 'LC-09' in e], [])   # the same field name in two objects is two fields

    def test_bian_add_objects_needs_an_object_index(self):   # BO-03 (was BB-D2): the base has its index; a pack of one's own has none
        import io, contextlib, shutil
        try: from sdem_bian.bian import main, BianError, base_file
        except ImportError: self.skipTest('needs sdem-bian installed (BX-15)')
        ws = Path(tempfile.mkdtemp())
        (ws / 'mappings.json').write_text('{"mappings": []}')
        (ws / 'a2-service-domain.json').write_text('{"level": "A2", "model_id": "T-A2", "model_version": "1", "metamodel_version": "0.19.0", "source_system": "test", "instances": [], "relationships": []}')   # a BIAN design (BX-15)
        own = ws / 'own' / base_file().name; own.parent.mkdir(); shutil.copy(base_file(), own)   # the same pack, with no index beside it
        with self.assertRaises(BianError) as e, contextlib.redirect_stdout(io.StringIO()):
            main(['add', 'Payment Order', '--workspace', str(ws), '--person', 'a tester', '--objects', '--base', str(own)])
        self.assertIn('--folder', str(e.exception)); self.assertIn('object index', str(e.exception))


if __name__ == '__main__':
    unittest.main()
