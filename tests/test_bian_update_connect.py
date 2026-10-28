"""`sdem bian update` and `sdem connect` (docs/design/sdem-bian-update-and-connect-design.md, BU-*, SC-*).

The scenario the fourth new-architect walkthrough could not complete: an onboarded design, a BIAN layer from the base,
and a person who knows which application realises a BIAN service domain — ending in a trace from capability to technology."""
import json, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ME = 'jane.architect'


class BianUpdateAndConnectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = Path(tempfile.mkdtemp())
        run = lambda *a: subprocess.run([sys.executable, '-m', 'sdem', *map(str, a)], cwd=cls.base, capture_output=True, text=True, env={'PYTHONPATH': str(ROOT), 'PATH': '/usr/bin:/bin'})
        shutil.copytree(ROOT / 'tests' / 'fixtures' / 'confluence-folder-export', cls.base / 'export')
        for a in (('bian', 'import', '--base', '--only', 'Payment Order Initiation', 'Payment Rail', '-o', 'bian/a2-service-domain.json'),
                  ('transform', 'run', 'export', '-o', 'history', '--ocr', 'off'),
                  ('load', 'history', '--estate', 'estates/payments', '--person', ME, '--exclude', 'HIS-A3-PAYMENT-ORDER', '--a2', 'bian/a2-service-domain.json'),
                  ('link', '--estate', 'estates/payments', '--out', 'links')):
            r = run(*a); assert r.returncode == 0, (a, r.stdout + r.stderr)

    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.base, ignore_errors=True)

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); shutil.copytree(self.base, self.tmp / 'w', dirs_exist_ok=True); self.w = self.tmp / 'w'

    def tearDown(self): shutil.rmtree(self.tmp, ignore_errors=True)

    def sdem(self, *a):
        r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, a)], cwd=self.w, capture_output=True, text=True, env={'PYTHONPATH': str(ROOT), 'PATH': '/usr/bin:/bin'})
        return r.returncode, r.stdout + r.stderr

    def reg(self): return json.loads((self.w / 'estates' / 'payments' / 'mappings.json').read_text())

    CONNECT = ('connect', 'SD-PAYMENT-ORDER-INITIATION', 'REALIZED_BY', 'HIS-A3-PAYMENTS-HUB', '--estate', 'estates/payments',
               '--evidence', 'application_architecture_document:PAYHUB-HLD#s2', '--rationale', 'The design names it')

    # ---- sdem connect
    def test_connect_completes_the_trace_from_capability_to_technology(self):  # SC-01, SC-04
        props = json.loads((self.w / 'links' / 'proposals.json').read_text())['mappings']
        sup = next(p['mapping_id'] for p in props if p['relationship'] == 'SUPPORTED_BY')
        dep = next(p['mapping_id'] for p in props if p['relationship'] == 'DEPLOYED_ON' and p['source']['id'] == 'HIS-A3-PAYMENTS-HUB')
        self.assertEqual(self.sdem('approve', sup, '--proposals', 'links/proposals.json', '--estate', 'estates/payments', '--reviewer', ME,
                                   '--evidence', 'business_architecture_document:BA#caps', '--evidence', 'domain_scope_assessment:DSA-1', '--bian-release', '14.0.0')[0], 0)
        self.assertEqual(self.sdem('approve', dep, '--proposals', 'links/proposals.json', '--estate', 'estates/payments', '--reviewer', ME,
                                   '--evidence', 'deployment_design:DEP#k8s')[0], 0)
        code, out = self.sdem(*self.CONNECT, '--reviewer', ME)
        self.assertEqual(code, 0, out); self.assertIn('connected', out)
        r = next(m for m in self.reg()['mappings'] if m['relationship'] == 'REALIZED_BY')
        self.assertEqual((r['status'], r['reviewer_id'], r['created_by']), ('approved', ME, 'sdem connect'))
        self.assertIn('Stated by jane.architect', r['rationale'])
        self.assertEqual(self.sdem('build', '--estate', 'estates/payments', '--out', 'graph')[0], 0)
        code, out = self.sdem('trace', 'HIS-A1-PAYMENT-INITIATION', '--direction', 'down', '--graph', 'graph')
        for step in ('SUPPORTED_BY-> SD-PAYMENT-ORDER-INITIATION', 'REALIZED_BY-> HIS-A3-PAYMENTS-HUB', 'DEPLOYED_ON-> HIS-A4-PAYMENTS-KUBERNETES-CLUSTER'):
            self.assertIn(step, out)

    def test_connect_has_approves_checks(self):  # SC-02
        before = self.reg()
        for extra, why, code_ in ((('--reviewer', 'copilot'), 'CTL-21', 1),
                                  (('--reviewer', ME, '--evidence', 'x'), 'kind:reference', 1)):
            code, out = self.sdem(*self.CONNECT, *extra)
            self.assertEqual(code, code_, out); self.assertIn(why, out)
        code, out = self.sdem('connect', 'SD-PAYMENT-ORDER-INITIATION', 'OWNS', 'HIS-A3-PAYMENTS-HUB', '--estate', 'estates/payments',
                              '--reviewer', ME, '--evidence', 'application_architecture_document:X', '--rationale', 'r')
        self.assertEqual(code, 1); self.assertIn('nothing was written', out)
        code, out = self.sdem('connect', 'HIS-A1-PAYMENT-INITIATION', 'SUPPORTED_BY', 'SD-PAYMENT-ORDER-INITIATION', '--estate', 'estates/payments',
                              '--reviewer', ME, '--evidence', 'business_architecture_document:BA', '--rationale', 'r')
        self.assertEqual(code, 1); self.assertIn('domain_scope_assessment', out)
        self.assertEqual(self.reg(), before)

    def test_connect_needs_both_ends_and_no_duplicate(self):  # SC-03, SC-04
        code, out = self.sdem('connect', 'SD-NOPE', 'REALIZED_BY', 'HIS-A3-PAYMENTS-HUB', '--estate', 'estates/payments', '--reviewer', ME,
                              '--evidence', 'application_architecture_document:X', '--rationale', 'r')
        self.assertEqual(code, 1); self.assertIn("source 'SD-NOPE' is not a record", out)
        self.assertEqual(self.sdem(*self.CONNECT, '--reviewer', ME)[0], 0)
        code, out = self.sdem(*self.CONNECT, '--reviewer', ME)
        self.assertEqual(code, 1); self.assertIn('already approved', out)

    # ---- sdem bian update
    def test_update_adds_service_domains_and_records_it(self):  # BU-01, BU-04
        self.assertEqual(self.sdem('bian', 'import', '--base', '--only', 'Payment Order Initiation', 'Payment Rail', 'Account Reconciliation',
                                   '-o', 'bian/a2-service-domain.json')[0], 0)
        code, out = self.sdem('bian', 'update', '--root', 'estates', '--a2', 'bian/a2-service-domain.json', '--person', ME, '--dry-run')
        self.assertIn('would update', out); self.assertFalse((self.w / 'estates' / 'payments' / 'bian-updates').exists())
        code, out = self.sdem('bian', 'update', '--root', 'estates', '--a2', 'bian/a2-service-domain.json', '--person', ME)
        self.assertEqual(code, 0, out); self.assertIn('updated (BU-001)', out)
        est = self.w / 'estates' / 'payments'
        self.assertEqual(json.loads((est / 'a2-service-domain.json').read_text()), json.loads((self.w / 'bian' / 'a2-service-domain.json').read_text()))
        rec = json.loads((est / 'bian-updates' / 'BU-001.json').read_text())
        self.assertEqual(rec['person'], ME); self.assertIn('SD-ACCOUNT-RECONCILIATION', rec['added']); self.assertEqual(rec['dropped'], [])
        code, out = self.sdem('bian', 'update', '--root', 'estates', '--a2', 'bian/a2-service-domain.json', '--person', ME)
        self.assertIn('unchanged', out); self.assertFalse((est / 'bian-updates' / 'BU-002.json').exists())

    def test_update_never_strands_an_approved_connection(self):  # BU-02
        self.assertEqual(self.sdem(*self.CONNECT, '--reviewer', ME)[0], 0)
        self.assertEqual(self.sdem('bian', 'import', '--base', '--only', 'Payment Rail', '-o', 'smaller.json')[0], 0)
        before = (self.w / 'estates' / 'payments' / 'a2-service-domain.json').read_text()
        code, out = self.sdem('bian', 'update', '--estate', 'estates/payments', '--a2', 'smaller.json', '--person', ME)
        self.assertEqual(code, 1); self.assertIn('supersede them first', out); self.assertIn('SD-PAYMENT-ORDER-INITIATION', out)
        self.assertEqual((self.w / 'estates' / 'payments' / 'a2-service-domain.json').read_text(), before)

    def test_update_is_a_persons_decision_and_needs_an_a2_file(self):  # BU-05, BU-01
        code, out = self.sdem('bian', 'update', '--estate', 'estates/payments', '--a2', 'bian/a2-service-domain.json', '--person', 'copilot')
        self.assertEqual(code, 2); self.assertIn("person's decision", out)
        code, out = self.sdem('bian', 'update', '--estate', 'estates/payments', '--a2', 'estates/payments/a3-application.json', '--person', ME)
        self.assertEqual(code, 2); self.assertIn('not an A2 dataset', out)


if __name__ == '__main__':
    unittest.main()
