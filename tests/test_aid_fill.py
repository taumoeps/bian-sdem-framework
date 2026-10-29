"""`sdem aid` fills a workspace (owner's decision DA2-05; spec docs/design/aid-spec.md AID-W*): inferred records go into the real
layer files, marked with source, reasoning and confidence; connections are only proposals; a person confirms or rejects each
record; nothing a person wrote is changed; a rejected record is not inferred again; a record that lost its mark is refused.
Also the S06 matching decision (DA2-04): with the full BIAN layer, only the best-covered domains."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
W = 'workspaces/payments'


def sdem(*args, cwd):
    env = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}   # installed or not (CI is not)
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], cwd=cwd, capture_output=True, text=True, env=env)
    return r.returncode, r.stdout + r.stderr


def rec(i, t, n, desc, **a): return {'id': i, 'type': t, 'version': '1.0', 'name': n, 'lifecycle_status': 'active', 'description': desc, 'attributes': a}


class AidFillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = Path(tempfile.mkdtemp())
        assert sdem('new', '--workspace', W, '--person', 'jane.architect', cwd=cls.base)[0] == 0   # all 258 BIAN service domains
        p = cls.base / W / 'a1-business.json'; d = json.loads(p.read_text())
        d['instances'] = [rec('CAP-PAY-INIT', 'A1.BusinessCapability', 'Payment Initiation', 'Take a customer payment order and get it ready to execute.', level=2),
                          rec('PRC-PAY', 'A1.BusinessProcess', 'Make a payment', 'From the customer request to the money leaving the account.', level=2),
                          rec('ACT-1', 'A1.BusinessActivity', 'Initiate payment order', 'Record the payee, amount and date.', sequence=1),
                          rec('ACT-2', 'A1.BusinessActivity', 'Execute payment', 'Send the payment through the payment rail.', sequence=2)]
        d['relationships'] = [{'source': 'PRC-PAY', 'kind': 'composition', 'target': 'ACT-1'}, {'source': 'PRC-PAY', 'kind': 'composition', 'target': 'ACT-2'}]
        p.write_text(json.dumps(d)); cls.a1 = d
        cls.first = sdem('aid', '--workspace', W, '--person', 'jane.architect', cwd=cls.base)   # one AID run, shared by the tests (it reads 258 domains)

    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.base, ignore_errors=True)

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); shutil.copytree(self.base / 'workspaces', self.tmp / 'workspaces')

    def tearDown(self): shutil.rmtree(self.tmp, ignore_errors=True)

    def layer(self, f): return json.loads((self.tmp / W / f).read_text())

    def test_only_the_best_covered_domains(self):  # DA2-04 (rule S06) with the full BIAN layer
        self.assertEqual(self.first[0], 0, self.first[1])
        props = json.loads((self.tmp / W / 'aid' / 'AID-001-proposals.json').read_text())['mappings']
        doms = {m['target']['id'] for m in props if m['source']['id'] == 'PRC-PAY'}
        self.assertEqual(doms, {'SD-PAYMENT-ORDER-INITIATION', 'SD-PAYMENT-RAIL'})

    def test_inferred_records_go_into_the_layers_marked(self):  # AID-W01, AID-W02
        code, out = self.first
        self.assertEqual(code, 0, out); self.assertIn('added (AID-001)', out)
        a3 = self.layer('a3-application.json')['instances']
        comp = next(i for i in a3 if i['id'] == 'AID-APP-SD-PAYMENT-ORDER-INITIATION')
        mark = comp['attributes']['inferred']
        self.assertEqual((mark['by'], mark['run'], mark['requested_by']), ('sdem aid', 'AID-001', 'jane.architect'))
        for k in ('source', 'reasoning', 'confidence', 'from'): self.assertTrue(mark[k], k)
        self.assertEqual(comp['lifecycle_status'], 'planned'); self.assertTrue(comp['name'].endswith('(inferred)'))
        names = [i['name'] for i in self.layer('a4-technology.json')['instances']]
        self.assertTrue(names and all('projected' not in n and n.endswith('(inferred)') for n in names), names)
        props = json.loads((self.tmp / W / 'aid' / 'AID-001-proposals.json').read_text())['mappings']   # BIAN ends carry their canonical id, as sdem link writes
        self.assertTrue(all(m['target'].get('canonical_id') for m in props if m['target']['type'].startswith('A2.')))
        self.assertTrue(all(i['attributes'].get('inferred') for i in a3))
        self.assertEqual(self.layer('a1-business.json'), self.a1)                        # what a person wrote is unchanged
        self.assertEqual(json.loads((self.tmp / W / 'mappings.json').read_text())['mappings'], [])   # connections are only proposed
        code, out = sdem('check', '--workspace', W, cwd=self.tmp)
        self.assertEqual(code, 0, out); self.assertIn('inferred record(s) to confirm', out)

    def test_confirm_reject_and_run_again(self):  # AID-W03…W05
        code, out = sdem('aid', 'confirm', 'AID-APP-SD-PAYMENT-RAIL', '--workspace', W, '--person', 'jane.architect', cwd=self.tmp)
        self.assertEqual(code, 0, out)
        m = next(i for i in self.layer('a3-application.json')['instances'] if i['id'] == 'AID-APP-SD-PAYMENT-RAIL')['attributes']['inferred']
        self.assertEqual((m['status'], m['confirmed_by']), ('confirmed', 'jane.architect'))   # the mark stays, with who confirmed it
        code, out = sdem('aid', 'reject', 'AID-DEP-SD-PAYMENT-RAIL', '--workspace', W, '--person', 'jane.architect', cwd=self.tmp)
        self.assertNotEqual(code, 0); self.assertIn('--reason', out)
        code, out = sdem('aid', 'reject', 'AID-DEP-SD-PAYMENT-RAIL', '--workspace', W, '--person', 'jane.architect', '--reason', 'shared platform', cwd=self.tmp)
        self.assertEqual(code, 0, out)
        self.assertNotIn('AID-DEP-SD-PAYMENT-RAIL', {i['id'] for i in self.layer('a4-technology.json')['instances']})
        code, out = sdem('aid', '--workspace', W, '--person', 'jane.architect', cwd=self.tmp)            # run again
        self.assertEqual(code, 0, out); self.assertIn('nothing to add', out)
        self.assertNotIn('AID-DEP-SD-PAYMENT-RAIL', {i['id'] for i in self.layer('a4-technology.json')['instances']})
        code, out = sdem('aid', 'confirm', 'PRC-PAY', '--workspace', W, '--person', 'jane.architect', cwd=self.tmp)
        self.assertEqual(code, 2); self.assertIn('not inferred records', out)
        code, out = sdem('aid', 'confirm', '--all', '--workspace', W, '--person', 'sdem-agent', cwd=self.tmp)
        self.assertEqual(code, 2); self.assertIn('person', out)

    def test_only_the_relevant_bian_domains_come_in(self):  # WS-01, AID-W01: the catalogue is read, not copied
        sds = [i for i in self.layer('a2-service-domain.json')['instances'] if i['type'] == 'A2.ServiceDomain']
        self.assertEqual(sorted(i['name'] for i in sds), ['Payment Order Initiation', 'Payment Rail'])
        self.assertTrue(all(i['attributes']['inferred']['reasoning'] for i in sds))
        self.assertLess((self.tmp / W / 'a2-service-domain.json').stat().st_size, 500_000)   # not the 10 MB of all of BIAN

    def test_a_domain_is_confirmed_with_its_parts_and_rejected_with_what_was_built_on_it(self):  # AID-W04, AID-W05
        code, out = sdem('aid', 'confirm', 'SD-PAYMENT-ORDER-INITIATION', '--workspace', W, '--person', 'jane.architect', cwd=self.tmp)
        self.assertEqual(code, 0, out)
        a2 = self.layer('a2-service-domain.json')['instances']
        ops = [i for i in a2 if i['type'] == 'A2.ServiceOperation' and i['id'].startswith('SO-PAYMENT-ORDER-INITIATION')]
        self.assertTrue(ops and all(i['attributes']['inferred'].get('status') == 'confirmed' for i in ops))
        code, out = sdem('aid', 'reject', 'SD-PAYMENT-RAIL', '--workspace', W, '--person', 'jane.architect', '--reason', 'not this design', cwd=self.tmp)
        self.assertEqual(code, 0, out)
        left = {i['id'] for f in ('a2-service-domain.json', 'a3-application.json', 'a4-technology.json') for i in self.layer(f)['instances']}
        self.assertFalse({x for x in left if 'PAYMENT-RAIL' in x})                              # its parts, application, APIs and deployment went too
        self.assertIn('SD-PAYMENT-ORDER-INITIATION', left)
        self.assertEqual(sdem('check', '--workspace', W, cwd=self.tmp)[0], 0)                     # nothing the kept domain uses was removed

    def test_an_existing_design_gets_the_domain_its_business_layer_names(self):  # AID-M02: either side, for a person to review
        ws = self.tmp / 'workspaces' / 'hist'
        self.assertEqual(sdem('new', '--workspace', ws, '--person', 'jane.architect', cwd=self.tmp)[0], 0)
        a1 = json.loads((ws / 'a1-business.json').read_text()); a1['instances'] = [rec('CAP-1', 'A1.BusinessCapability', 'Payment Initiation', 'Initiate customer payments.', level=2)]
        a3 = json.loads((ws / 'a3-application.json').read_text())
        a3['instances'] = [{'id': 'APP-HUB', 'type': 'A3.ApplicationComponent', 'version': '1.0', 'name': 'Payments Hub', 'lifecycle_status': 'active'}]
        (ws / 'a1-business.json').write_text(json.dumps(a1)); (ws / 'a3-application.json').write_text(json.dumps(a3))
        code, out = sdem('aid', '--workspace', ws, '--person', 'jane.architect', cwd=self.tmp)
        self.assertEqual(code, 0, out)
        self.assertIn('Payment Order Initiation', {i['name'] for i in json.loads((ws / 'a2-service-domain.json').read_text())['instances'] if i['type'] == 'A2.ServiceDomain'})

    def test_a_record_that_lost_its_mark_is_refused(self):  # CTL-16
        p = self.tmp / W / 'a3-application.json'; d = json.loads(p.read_text())
        d['instances'][0]['attributes'].pop('inferred'); p.write_text(json.dumps(d))
        code, out = sdem('check', '--workspace', W, cwd=self.tmp)
        self.assertNotEqual(code, 0); self.assertIn("'inferred' mark is missing", out)

    def test_proposals_are_approved_as_usual_and_trace_follows_only_approved(self):  # AID-W03
        f = self.tmp / W / 'aid' / 'AID-001-proposals.json'
        pid = next(m['mapping_id'] for m in json.loads(f.read_text())['mappings'] if m['relationship'] == 'USES_DOMAIN')
        code, out = sdem('approve', pid, '--proposals', f, '--workspace', W, '--reviewer', 'jane.architect', '--evidence', 'process_model:PM-PAY', cwd=self.tmp)
        self.assertEqual(code, 0, out)
        self.assertEqual(sdem('build', '--workspace', W, '--out', 'g', cwd=self.tmp)[0], 0)
        code, out = sdem('trace', 'PRC-PAY', '--direction', 'down', '--graph', 'g', cwd=self.tmp)
        self.assertEqual(code, 0, out); self.assertIn('USES_DOMAIN', out); self.assertNotIn('AID-APP', out)   # inferred, not approved: not followed

    def test_needs_a_workspace_and_something_to_start_from(self):  # AID-W01
        code, out = sdem('aid', '--workspace', 'nowhere', '--person', 'jane.architect', cwd=self.tmp)
        self.assertEqual(code, 2); self.assertIn('sdem new', out)
        self.assertEqual(sdem('new', '--workspace', 'empty', '--person', 'jane.architect', '--no-bian', cwd=self.tmp)[0], 0)
        code, out = sdem('aid', '--workspace', 'empty', '--person', 'jane.architect', cwd=self.tmp)
        self.assertEqual(code, 2); self.assertIn('write what you have first', out)


if __name__ == '__main__':
    unittest.main()
