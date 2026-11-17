"""`sdem intake` — a design authored as SDEM data comes in through one command (docs/design/sdem-intake-design.md IN-01…IN-10): the whole
package is checked at once, without a workspace, so its author can run the real check before handing over; then one command loads it and
runs the complete-draft order, ending in one report. Synthetic data only — the package below is written for this test."""
import copy, json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}


def rec(i, t, n, **a): return {'id': i, 'type': t, 'version': '1', 'name': n, 'lifecycle_status': 'planned', 'attributes': {'source_id': 'document:design.md#1', **a}}
def link(s, k, t): return {'source': s, 'kind': k, 'target': t}


def package():
    """A made-up design as the eight files of the authoring guide (the read-me left out: it is prose)."""
    return {
        'a1-business.json': {'level': 'A1', 'instances': [rec('PROC-PAY', 'A1.BusinessProcess', 'Take the payment'), rec('PROC-SCREEN', 'A1.BusinessProcess', 'Screen for fraud'),
                                                          rec('R-01', 'A1.BusinessRequirement', 'A payment is taken once'), rec('ACT-CUST', 'A1.BusinessActor', 'Customer')],
                             'relationships': [link('PROC-PAY', 'realization', 'R-01')]},
        'a3-application.json': {'level': 'A3', 'instances': [rec('APP-HUB', 'A3.ApplicationComponent', 'Payments hub'), rec('API-HUB', 'A3.ApplicationInterface', 'Hub API'),
                                                             rec('DATA-PAY', 'A3.DataEntity', 'payments', attributes=['payment_id'])],
                                'relationships': [link('APP-HUB', 'composition', 'API-HUB'), link('APP-HUB', 'access', 'DATA-PAY')]},
        'a4-technology.json': {'level': 'A4', 'instances': [rec('SYS-DB', 'A4.SystemSoftware', 'Database'), rec('DEP-HUB', 'A4.Deployment', 'Payments hub — production', component_id='APP-HUB')],
                               'relationships': []},
        'BIAN-DOMAINS.json': {'release': '14.0.0', 'service_domains': [{'name': 'Payment Order Initiation', 'source': 'document:design.md#4'}],
                              'operations': [{'service_domain': 'Payment Order Initiation', 'name': 'Initiate', 'used_by': ['PROC-PAY'], 'source': 'document:design.md#4'}],
                              'bank_local_not_bian': ['Consent control']},
        'CROSS-LAYER-SUGGESTIONS.json': {'status': 'UNAPPROVED', 'suggestions': [
            {'source': 'DATA-PAY', 'link_type': 'STORED_IN', 'target': 'SYS-DB', 'design_section': '6', 'basis': 'stated', 'reason': 'the payments table is in the database'},
            {'source': 'APP-HUB', 'link_type': 'DEPLOYED_AS', 'target': 'DEP-HUB', 'design_section': '6', 'basis': 'stated', 'reason': 'its deployment'}]},
        'NOT-STATED.json': {'items': [{'record_id': 'ACT-CUST', 'detail': 'what serves the customer is not stated', 'design_section': '1'}]},
        'CHECKLIST.json': {'cli_executed': False},
    }


def complete():
    """A made-up design that IS complete: every record connected, and every part the Transact pattern asks of its one BIAN domain."""
    sys.path.insert(0, str(ROOT))
    from sdem.intake import _bian_catalogue
    op = sorted(_bian_catalogue()['Currency Exchange']['operations'])[0]
    S = lambda s, r, t: {'source': s, 'link_type': r, 'target': t, 'design_section': '3', 'basis': 'stated', 'reason': 'the design says so'}
    return {
        'a1-business.json': {'level': 'A1', 'instances': [rec('CAP-FX', 'A1.BusinessCapability', 'Currency exchange'), rec('PROC-FX', 'A1.BusinessProcess', 'Exchange currency'), rec('R-01', 'A1.BusinessRequirement', 'A rate is quoted')],
                             'relationships': [link('PROC-FX', 'realization', 'R-01')]},
        'a3-application.json': {'level': 'A3', 'instances': [rec('APP-FX', 'A3.ApplicationComponent', 'Exchange engine'), rec('API-FX', 'A3.ApplicationInterface', 'Exchange API'),
                                                             rec('OP-FX', 'A3.APIOperation', 'Create exchange'), rec('DATA-FX', 'A3.DataEntity', 'exchanges')],
                                'relationships': [link('APP-FX', 'composition', 'API-FX'), link('API-FX', 'composition', 'OP-FX'), link('APP-FX', 'access', 'DATA-FX')]},
        'a4-technology.json': {'level': 'A4', 'instances': [rec('ZONE-IN', 'A4.NetworkZone', 'Inside', zone_level=1, zone_kind='internal'), rec('NODE-1', 'A4.Node', 'Compute'),
                                                            rec('SYS-DB', 'A4.SystemSoftware', 'Database'), rec('DEP-FX', 'A4.Deployment', 'Exchange engine — production', component_id='APP-FX')],
                               'relationships': [link('ZONE-IN', 'aggregation', 'NODE-1'), link('NODE-1', 'assignment', 'SYS-DB'), link('NODE-1', 'assignment', 'DEP-FX')]},
        'BIAN-DOMAINS.json': {'release': '14.0.0', 'service_domains': [{'name': 'Currency Exchange', 'source': 'document:design.md#4'}],
                              'operations': [{'service_domain': 'Currency Exchange', 'name': op, 'used_by': ['PROC-FX'], 'source': 'document:design.md#4'}], 'bank_local_not_bian': []},
        'CROSS-LAYER-SUGGESTIONS.json': {'status': 'UNAPPROVED', 'suggestions': [S('CAP-FX', 'SUPPORTED_BY', 'Currency Exchange'), S('PROC-FX', 'USES_DOMAIN', 'Currency Exchange'),
                                                                                 S('Currency Exchange', 'REALIZED_BY', 'APP-FX'), S(f'Currency Exchange: {op}', 'IMPLEMENTED_BY', 'OP-FX'),
                                                                                 S('DATA-FX', 'STORED_IN', 'SYS-DB'), S('APP-FX', 'DEPLOYED_AS', 'DEP-FX')]},
        'NOT-STATED.json': {'items': []},
        'DECISIONS.json': {'decisions': [{'what': 'DATA-FX STORED_IN SYS-DB', 'decision': 'the exchanges table is in the one database', 'reason': 'the document names no other store', 'design_section': '6'}]},
        'CHECKLIST.json': {'cli_executed': True},
    }


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, self.tmp, True); self.pkg = self.tmp / 'pkg'; self.ws = self.tmp / 'ws'

    def write(self, p):
        self.pkg.mkdir(exist_ok=True)
        for f in list(self.pkg.iterdir()): f.unlink()
        for name, doc in p.items(): (self.pkg / name).write_text(json.dumps(doc), encoding='utf-8')

    def sdem(self, *a):
        r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, a)], cwd=self.tmp, capture_output=True, text=True, env=ENV)
        return r.returncode, r.stdout, r.stderr


class Check(Base):
    def test_a_good_package_passes_and_nothing_is_written(self):   # IN-01, IN-02
        self.write(package()); before = sorted(p.name for p in self.tmp.iterdir())
        code, out, err = self.sdem('intake', self.pkg, '--check', '--allow-gaps', '--json'); self.assertEqual(code, 0, out + err)
        r = json.loads(out)
        self.assertEqual((r['ok'], r['errors'], r['complete']), (True, [], False))
        self.assertEqual(r['counts']['records'], {'A1': 4, 'A3': 3, 'A4': 2}); self.assertEqual(r['counts']['suggestions'], 2)
        self.assertEqual(r['bian']['service_domains'], ['Payment Order Initiation'])
        self.assertEqual(r['bian']['operations'], [{'service_domain': 'Payment Order Initiation', 'name': 'Initiate', 'id': 'SO-PAYMENT-ORDER-INITIATION-INITIATE', 'used_by': ['PROC-PAY']}])
        self.assertEqual(sorted(p.name for p in self.tmp.iterdir()), before)

    def test_everything_wrong_is_said_at_once_with_where_and_why(self):   # IN-03
        p = package()
        p['a3-application.json']['instances'][1]['attributes']['contract_format'] = 'OpenAPI 3.x'          # not an allowed value
        p['a1-business.json']['relationships'].append(link('ACT-CUST', 'assignment', 'R-01'))               # a link the metamodel does not allow
        p['a4-technology.json']['relationships'].append(link('DATA-PAY', 'STORED_IN', 'SYS-DB'))            # a link between layers inside a layer file
        p['a2-service-domain.json'] = {'level': 'A2', 'instances': [], 'relationships': []}                 # the BIAN file is never written
        p['BIAN-DOMAINS.json']['service_domains'].append({'name': 'Consent Control', 'source': 'x'})        # not a BIAN service domain
        p['BIAN-DOMAINS.json']['operations'].append({'service_domain': 'Payment Order Initiation', 'name': 'Teleport', 'used_by': ['PROC-NONE'], 'source': 'x'})
        p['CROSS-LAYER-SUGGESTIONS.json']['suggestions'] += [{'source': 'APP-HUB', 'link_type': 'satisfied by', 'target': 'R-01', 'design_section': '2', 'reason': 'x'},
                                                             {'source': 'SYS-DB', 'link_type': 'STORED_IN', 'target': 'DATA-PAY', 'design_section': '6', 'reason': 'backwards'}]
        p['NOT-STATED.json']['items'].append({'record_id': 'a1-value-stream', 'detail': 'the design states no value stream', 'design_section': '1'})   # not an error: the thing is absent, and said to be
        self.write(p)
        code, out, err = self.sdem('intake', self.pkg, '--check', '--json'); self.assertEqual(code, 1, out + err)
        errs = ' | '.join(e['file'] + ': ' + e['message'] for e in json.loads(out)['errors'])
        for want in ("a3-application.json: instance API-HUB: attribute 'contract_format' value 'OpenAPI 3.x' is not one of",
                     'a1-business.json: relationship ACT-CUST -assignment-> R-01',
                     'a4-technology.json: DATA-PAY STORED_IN SYS-DB is a link between layers',
                     'a2-service-domain.json: the BIAN layer is not authored',
                     "BIAN-DOMAINS.json: 'Consent Control' is not a BIAN service domain",
                     "BIAN-DOMAINS.json: Payment Order Initiation has no operation 'Teleport'", "BIAN-DOMAINS.json: used_by PROC-NONE is not a record",
                     "CROSS-LAYER-SUGGESTIONS.json: 'satisfied by' is not a link type between layers",
                     'CROSS-LAYER-SUGGESTIONS.json: SYS-DB STORED_IN DATA-PAY — STORED_IN does not join A4.SystemSoftware to A3.DataEntity'):
            self.assertIn(want, errs)
        text = self.sdem('intake', self.pkg, '--check')[1]
        self.assertIn('9 thing(s) to fix', text); self.assertIn('OpenAPI 3.1', text)   # the allowed values are in the message: the author can fix it without asking

    def test_a_design_that_is_not_complete_fails_and_each_gap_says_what_to_add(self):   # IN-11
        self.write(package())
        code, out, err = self.sdem('intake', self.pkg, '--check', '--json'); self.assertEqual(code, 1, out + err)
        msgs = [e['message'] for e in json.loads(out)['errors']]
        self.assertTrue(all(m.startswith('NOT COMPLETE — ') for m in msgs), msgs)
        text = ' | '.join(msgs)
        self.assertIn('ACT-CUST is not connected: an actor does something in the design, or is served by it (CPL-A1-05)', text)   # listing it as not stated does not excuse it
        self.assertIn('PROC-SCREEN is not connected', text)
        self.assertNotIn('DATA-PAY is not connected', text)                                # its store is given as a link between layers
        self.assertIn('the Payment initiation pattern, which fits this design', text); self.assertIn('no Fraud Evaluation (BIAN) in the design', text); self.assertIn('why it is needed: ', text)
        self.assertNotIn('which is missing', text)                                         # a part that only follows from a missing part is not said twice
        code, out, err = self.sdem('intake', self.pkg, '--check', '--allow-gaps', '--json'); self.assertEqual(code, 0, out + err)
        r = json.loads(out); self.assertEqual((r['ok'], r['complete']), (True, False)); self.assertEqual(len(r['gaps']), len(msgs))

    def test_a_complete_design_passes_with_nothing_left(self):   # IN-11
        self.write(complete())
        code, out, err = self.sdem('intake', self.pkg, '--check', '--json'); self.assertEqual(code, 0, out + err)
        r = json.loads(out); self.assertEqual((r['ok'], r['complete'], r['gaps'], r['errors']), (True, True, [], []))
        self.assertIn('COMPLETE — every record connected, every part of every pattern that fits present', self.sdem('intake', self.pkg, '--check')[1])
        p = complete(); p['CROSS-LAYER-SUGGESTIONS.json']['suggestions'] = [x for x in p['CROSS-LAYER-SUGGESTIONS.json']['suggestions'] if x['link_type'] != 'DEPLOYED_AS']; self.write(p)
        code, out, err = self.sdem('intake', self.pkg, '--check'); self.assertEqual(code, 1)
        self.assertIn('CROSS-LAYER-SUGGESTIONS.json: NOT COMPLETE — APP-FX is not connected: a component has a deployment', out)
        self.assertIn('Deployment of the component', out)                                   # and the pattern's part it leaves empty

    def test_a_missing_file_or_a_folder_that_is_not_a_package_is_refused_plainly(self):   # IN-01
        p = package(); del p['BIAN-DOMAINS.json']; del p['a1-business.json']; self.write(p)
        code, out, err = self.sdem('intake', self.pkg, '--check'); self.assertEqual(code, 1)
        self.assertIn('BIAN-DOMAINS.json: missing', out); self.assertIn('a1-business.json: missing', out)
        code, out, err = self.sdem('intake', self.tmp / 'nowhere', '--check'); self.assertEqual(code, 2); self.assertIn('no such folder', out + err)


class Load(Base):
    def test_one_command_loads_it_and_runs_the_draft_in_order(self):   # IN-05…IN-09
        self.write(package())
        code, out, err = self.sdem('intake', self.pkg, '--workspace', self.ws, '--person', 'sdem-a1-business'); self.assertEqual(code, 2); self.assertIn("a person's", out + err)   # CTL-21
        self.assertFalse(self.ws.exists())
        code, out, err = self.sdem('intake', self.pkg, '--workspace', self.ws, '--person', 'jane.architect', '--json'); self.assertEqual(code, 1)   # not complete: nothing loaded
        self.assertFalse(self.ws.exists())
        code, out, err = self.sdem('intake', self.pkg, '--workspace', self.ws, '--person', 'jane.architect', '--allow-gaps', '--json'); self.assertEqual(code, 0, (out + err)[-1500:])
        r = json.loads(out)
        self.assertEqual([s['step'] for s in r['steps']], ['check', 'workspace', 'load', 'bian', 'patterns', 'draft', 'links', 'report'])   # the skill's order — in the tool
        a1 = {i['id']: i for i in json.loads((self.ws / 'a1-business.json').read_text(encoding='utf-8'))['instances']}
        self.assertEqual(a1['PROC-PAY']['attributes']['invokes'], ['SO-PAYMENT-ORDER-INITIATION-INITIATE'])
        self.assertIn('SD-PAYMENT-ORDER-INITIATION', (self.ws / 'a2-service-domain.json').read_text(encoding='utf-8'))
        inc = json.loads((self.ws / 'sdem-profile.json').read_text(encoding='utf-8'))['includes']
        self.assertIn('sdem:sdem-pattern-payment-initiation.json', inc); self.assertIn('sdem:sdem-pattern-bian-transact.json', inc)
        self.assertEqual({p['title'] for p in r['draft']['patterns_consulted']}, {'Payment initiation', 'BIAN Transact — a transaction'})
        reg = json.loads((self.ws / 'mappings.json').read_text(encoding='utf-8'))['mappings']
        self.assertEqual([m for m in reg if m.get('status') == 'approved'], [])   # nothing is approved, confirmed or rejected by intake
        props = [(m['source']['id'], m['relationship'], m['target']['id']) for f in sorted((self.ws / 'aid').glob('*-proposals.json')) + [self.ws / 'links' / 'proposals.json']
                 for m in json.loads(f.read_text(encoding='utf-8'))['mappings']]
        self.assertIn(('DATA-PAY', 'STORED_IN', 'SYS-DB'), props); self.assertIn(('APP-HUB', 'DEPLOYED_AS', 'DEP-HUB'), props)   # the author's suggestions are proposals now
        rep = (self.ws / r['report']).read_text(encoding='utf-8')
        for h in ('## What came in', '## What the author said the design does not state', '## The draft', '## Yours to decide — weakest first'): self.assertIn(h, rep)
        self.assertIn('ACT-CUST', rep); self.assertIn('Consent control', rep)
        self.assertEqual(self.sdem('check', '--workspace', self.ws)[0], 0)
        code, out, err = self.sdem('intake', self.pkg, '--workspace', self.ws, '--person', 'jane.architect', '--allow-gaps'); self.assertEqual(code, 2); self.assertIn('already holds records', out + err)   # never loaded twice over

    def test_a_complete_design_accepted_as_authored_leaves_nothing_for_anyone(self):   # IN-11, IN-12
        self.write(complete())
        code, out, err = self.sdem('intake', self.pkg, '--workspace', self.ws, '--person', 'jane.architect', '--accept', '--json'); self.assertEqual(code, 0, (out + err)[-1500:])
        r = json.loads(out)
        self.assertIn('accept', [s['step'] for s in r['steps']])
        reg = json.loads((self.ws / 'mappings.json').read_text(encoding='utf-8'))['mappings']
        got = sorted((m['relationship'], m['status'], m['reviewer_id']) for m in reg)
        self.assertEqual(got, sorted((x, 'approved', 'jane.architect') for x in ('SUPPORTED_BY', 'USES_DOMAIN', 'REALIZED_BY', 'IMPLEMENTED_BY', 'STORED_IN', 'DEPLOYED_AS')))
        self.assertTrue(all(any('design.md#3' in e for e in m['evidence']) for m in reg))   # each on the design section it cites
        s = json.loads(self.sdem('status', '--workspace', self.ws, '--json')[1])
        c = s['completeness']; self.assertEqual((c['gaps'], c['inferred_to_confirm'], c['records_connected']), (0, 0, c['records_checked']))
        p = next(x for x in s['patterns'] if x['pattern'] == 'PAT-BIAN-TRANSACT'); self.assertEqual((p['in_place'], p['open']), (p['parts'], []))
        self.assertEqual((s['state'], s['blocking'], s['unresolved']), ('clear', [], []))   # IN-13: nothing to review, confirm, approve or plan — the design's first load is not a change to plan
        self.assertEqual(self.sdem('check', '--workspace', self.ws)[0], 0)
        rep = (self.ws / r['report']).read_text(encoding='utf-8')
        self.assertIn('6 accepted as authored', rep); self.assertIn('## What the author decided where the design document was silent', rep); self.assertIn('the exchanges table is in the one database', rep)
        code, out, err = self.sdem('intake', self.pkg, '--workspace', self.tmp / 'ws2', '--person', 'sdem-orchestrator', '--accept'); self.assertEqual(code, 2)   # accepting is a person's (CTL-21)

    def test_a_package_that_fails_its_check_changes_nothing(self):   # IN-05
        p = package(); p['a3-application.json']['instances'][1]['type'] = 'A3.Gadget'; self.write(p)
        code, out, err = self.sdem('intake', self.pkg, '--workspace', self.ws, '--person', 'jane.architect'); self.assertEqual(code, 1)
        self.assertFalse(self.ws.exists()); self.assertIn('A3.Gadget', out)

    def test_dry_run_says_what_it_would_do(self):   # IN-05
        self.write(package())
        code, out, err = self.sdem('intake', self.pkg, '--workspace', self.ws, '--person', 'jane.architect', '--allow-gaps', '--dry-run', '--json'); self.assertEqual(code, 0, out + err)
        r = json.loads(out); self.assertTrue(r['dry_run']); self.assertFalse(self.ws.exists())
        self.assertEqual(r['would']['bian_add'], ['Payment Order Initiation']); self.assertEqual(r['would']['load'], {'A1': 4, 'A3': 3, 'A4': 2})


if __name__ == '__main__':
    unittest.main()
