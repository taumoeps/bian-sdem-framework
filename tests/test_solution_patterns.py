"""Patterns for kinds of solution — the first: payment initiation, shipped with SDEM (docs/design/sdem-completeness-design.md CPL-08…CPL-11;
docs/design/sdem-profile-spec.md PR-36…PR-38). A pattern says what a kind of solution has and how its parts connect; it is asked before
anything is inferred. Synthetic data only: the made-up design below is written for this test."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem import comply, patterns, profile  # noqa: E402
from sdem.metamodel import Metamodel  # noqa: E402

PID = 'PAT-PAYMENT-INITIATION'
FILE = 'sdem:sdem-pattern-payment-initiation.json'
ENV = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}


def sdem(*args, cwd):
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], cwd=cwd, capture_output=True, text=True, env=ENV)
    return r.returncode, r.stdout, r.stderr


def _j(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def _w(p, d): Path(p).write_text(json.dumps(d, indent=1), encoding='utf-8')


def rec(i, t, n, **a): return {'id': i, 'type': t, 'version': '1', 'name': n, 'lifecycle_status': 'active', 'attributes': a}
def sd(i, n): return rec(i, 'A2.ServiceDomain', n, asset_type='AT-X', functional_pattern='FP-X')
def link(s, k, t): return {'source': s, 'kind': k, 'target': t}


def design():
    """A made-up payment initiation design that has every part of the pattern."""
    return {
        'A1': ([rec('PROC-PAY', 'A1.BusinessProcess', 'Take the payment'), rec('PROC-AUTH', 'A1.BusinessProcess', 'Authorise the consent'),
                rec('PROC-SCREEN', 'A1.BusinessProcess', 'Screen the payment')], []),
        'A2': ([sd('SD-POI', 'Payment Order Initiation'), sd('SD-PAUTH', 'Party Authentication'), sd('SD-FRAUD', 'Fraud Evaluation'), sd('SD-OTHER', 'Term Deposit')], []),
        'A3': ([rec('APP-HUB', 'A3.ApplicationComponent', 'Payments hub'), rec('APP-DOOR', 'A3.ApplicationComponent', 'Front door'),
                rec('IFC-OPEN', 'A3.ApplicationInterface', 'Open payments API', internet_facing=True), rec('IFC-IN', 'A3.ApplicationInterface', 'Internal API'),
                *[rec(f'OP-{n}', 'A3.APIOperation', f'operation {n}') for n in range(1, 5)],
                rec('DATA-A', 'A3.DataEntity', 'table a'), rec('DATA-B', 'A3.DataEntity', 'table b'), rec('DATA-C', 'A3.DataEntity', 'table c'), rec('DATA-LOG', 'A3.DataEntity', 'decision log')],
               [link('APP-HUB', 'access', 'DATA-A'), link('APP-HUB', 'access', 'DATA-B'), link('APP-HUB', 'access', 'DATA-C'), link('APP-DOOR', 'access', 'DATA-LOG'),
                link('APP-DOOR', 'composition', 'IFC-OPEN'), link('APP-HUB', 'composition', 'IFC-IN'), *[link('IFC-OPEN', 'composition', f'OP-{n}') for n in range(1, 5)]]),
        'A4': ([rec('ZONE-D', 'A4.NetworkZone', 'Edge', zone_level=1, zone_kind='dmz'), rec('ZONE-I', 'A4.NetworkZone', 'Inside', zone_level=1, zone_kind='internal'),
                rec('ZONE-S', 'A4.NetworkZone', 'Secrets', zone_level=2, zone_kind='private'),
                rec('NODE-EDGE', 'A4.Node', 'Edge node', internet_facing=True), rec('NODE-IN', 'A4.Node', 'Inner node'), rec('NODE-SEC', 'A4.Node', 'Secure node'),
                rec('SYS-DB', 'A4.SystemSoftware', 'Database'), rec('SYS-KEYS', 'A4.SystemSoftware', 'Key store', conforms_to=[PID + '#key-store'])],
               [link('ZONE-D', 'aggregation', 'NODE-EDGE'), link('ZONE-I', 'aggregation', 'NODE-IN'), link('ZONE-S', 'aggregation', 'NODE-SEC'), link('ZONE-I', 'aggregation', 'ZONE-S'),
                link('NODE-IN', 'assignment', 'SYS-DB'), link('NODE-SEC', 'assignment', 'SYS-KEYS')]),
        'maps': [('PROC-PAY', 'USES_DOMAIN', 'SD-POI'), ('PROC-AUTH', 'USES_DOMAIN', 'SD-PAUTH'), ('PROC-SCREEN', 'USES_DOMAIN', 'SD-FRAUD'), ('SD-POI', 'REALIZED_BY', 'APP-HUB'),
                 ('DATA-A', 'STORED_IN', 'SYS-DB'), ('DATA-B', 'STORED_IN', 'SYS-DB'), ('DATA-C', 'STORED_IN', 'SYS-DB'), ('IFC-OPEN', 'EXPOSED_THROUGH', 'NODE-EDGE')]}


class Base(unittest.TestCase):
    def setUp(self):
        self.addCleanup(profile.deactivate)
        self.tmp = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, self.tmp, True)
        self.ws = self.tmp / 'ws'

    def build(self, d=None, includes=(FILE,), pattern=None):
        """The workspace's files, written as a test fixture (not through change sets: only the pattern is under test)."""
        d = d or design(); self.ws.mkdir(exist_ok=True)
        for layer, f in (('A1', 'a1-business.json'), ('A2', 'a2-service-domain.json'), ('A3', 'a3-application.json'), ('A4', 'a4-technology.json')):
            _w(self.ws / f, {'level': layer, 'model_id': f'T-{layer}', 'model_version': '1', 'metamodel_version': Metamodel.base().version, 'source_system': 'test',
                             'instances': d[layer][0], 'relationships': d[layer][1]})
        _w(self.ws / 'mappings.json', {'mappings': [{'mapping_id': f'M-{n}', 'source': {'id': s}, 'relationship': r, 'target': {'id': t}, 'status': 'approved'} for n, (s, r, t) in enumerate(d['maps'])]})
        if pattern: _w(self.ws / 'own-pattern.json', pattern); includes = ('own-pattern.json',)
        _w(self.ws / 'sdem-profile.json', {'format': 'sdem-profile/1', 'name': 'test', 'version': 1, 'includes': list(includes)})

    def parts(self, anchor='SD-POI'):
        datasets, maps, mm, _ = comply.workspace_data(self.ws)
        found, bindings = patterns.evaluate(datasets, maps, mm, profile.structures(), profile.exceptions())
        return ({f['part']['id']: (f['outcome'], f['detail']) for f in found if f['record'] == anchor},
                next((b['roles'] for b in bindings if b['anchor'] == anchor), None))


class Format(Base):
    """What the pattern format gained: a part may say which records can be it, and may be found anywhere in the design."""
    def pattern(self, **edit):
        p = {'format': 'sdem-pattern/1', 'pattern': {'id': 'PAT-T', 'title': 'Test', 'version': '1', 'owner': 'test', 'severity': 'warning',
                                                     'applies_when': {'entity': 'A2.ServiceDomain', 'when': {'name': 'Payment Order Initiation'}}},
             'structure': {'anchor': 'domain',
                           'roles': [{'id': 'domain', 'type': 'A2.ServiceDomain'},
                                     {'id': 'other-domain', 'type': 'A2.ServiceDomain', 'anywhere': True, 'when': {'name': 'Fraud Evaluation'}},
                                     {'id': 'process', 'type': 'A1.BusinessProcess', 'max': None},
                                     {'id': 'open-api', 'type': 'A3.ApplicationInterface', 'anywhere': True, 'when': {'internet_facing': True}}],
                           'connectors': [{'id': 'C1', 'from': 'process', 'to': 'other-domain', 'relationship': 'USES_DOMAIN'}]}}
        p['structure'].update(edit); return p

    def test_a_pattern_applies_by_a_records_name(self):   # PR-36
        self.build(pattern=self.pattern()); out, roles = self.parts()
        self.assertEqual(roles['domain'], ['SD-POI'])
        self.assertEqual(self.parts('SD-OTHER'), ({}, None))   # another domain: the pattern does not apply

    def test_a_part_is_found_anywhere_in_the_design_and_only_among_the_records_it_names(self):   # PR-36, PR-37
        self.build(pattern=self.pattern()); out, roles = self.parts()
        self.assertEqual((roles['other-domain'], roles['open-api'], roles['process']), (['SD-FRAUD'], ['IFC-OPEN'], ['PROC-SCREEN']))   # not IFC-IN: not internet facing
        self.assertEqual({out[p][0] for p in ('other-domain', 'open-api', 'process', 'C1')}, {'compliant'})

    def test_a_part_that_is_nowhere_is_said_plainly(self):   # PR-37
        d = design(); d['A2'] = ([r for r in d['A2'][0] if r['id'] != 'SD-FRAUD'], [])
        self.build(d, pattern=self.pattern()); out, _ = self.parts()
        self.assertEqual(out['other-domain'], ('non_compliant', 'no other-domain in the design (A2.ServiceDomain where name = Fraud Evaluation)'))
        self.assertEqual(out['process'][0], 'non_compliant'); self.assertIn('found through other-domain, which is missing', out['process'][1])

    def test_the_profile_check_refuses_what_it_cannot_follow(self):   # PR-36, PR-37
        def issues(**edit):
            self.build(pattern=self.pattern(**edit)); return profile.check(profile.resolve(self.ws / 'sdem-profile.json'), Metamodel.base())
        self.assertEqual(issues(), [])
        bad = issues(roles=[{'id': 'domain', 'type': 'A2.ServiceDomain', 'anywhere': True}, {'id': 'x', 'type': 'A1.BusinessProcess', 'anywhere': True, 'when': {'no_such': 1}}], connectors=[])
        self.assertTrue(any('the anchor domain cannot be found anywhere' in i for i in bad), bad)
        self.assertTrue(any("role x: when 'no_such', which is not an attribute of A1.BusinessProcess" in i for i in bad), bad)
        self.assertTrue(any('role x is not connected to the anchor' in i for i in issues(roles=[{'id': 'domain', 'type': 'A2.ServiceDomain'}, {'id': 'x', 'type': 'A1.BusinessProcess'}], connectors=[])))


class PaymentInitiation(Base):
    def test_it_ships_with_sdem_and_passes_the_profile_check(self):   # CPL-08
        d = _j(profile.shipped(FILE))
        self.assertEqual((d['format'], d['pattern']['id'], d['pattern']['owner'], d['pattern']['severity']), ('sdem-pattern/1', PID, 'SDEM', 'warning'))
        self.assertEqual(d['pattern']['applies_when'], {'entity': 'A2.ServiceDomain', 'when': {'name': 'Payment Order Initiation'}})
        self.assertTrue(all(r.get('label') and (r.get('reasoning') or r['id'] == d['structure']['anchor']) for r in d['structure']['roles']))   # every part says why
        self.build(); self.assertEqual(profile.check(profile.resolve(self.ws / 'sdem-profile.json'), Metamodel.base()), [])

    def test_a_design_with_every_part_meets_it(self):   # CPL-08
        self.build(); out, roles = self.parts()
        self.assertEqual({p: o for p, (o, _) in out.items() if o != 'compliant'}, {})
        self.assertEqual(len(out), 25)   # fifteen parts, ten connectors
        self.assertEqual((roles['payment-process'], roles['payments-component'], roles['payment-records'], roles['database']), (['PROC-PAY'], ['APP-HUB'], ['DATA-A', 'DATA-B', 'DATA-C'], ['SYS-DB']))
        self.assertEqual((roles['authorisation-process'], roles['fraud-process'], roles['api'], roles['api-component'], roles['audit-record'], roles['edge-platform'], roles['key-store']),
                         (['PROC-AUTH'], ['PROC-SCREEN'], ['IFC-OPEN'], ['APP-DOOR'], ['DATA-LOG'], ['NODE-EDGE'], ['SYS-KEYS']))

    def test_what_a_design_lacks_is_named_part_by_part(self):   # CPL-08
        d = design()
        d['A2'] = ([r for r in d['A2'][0] if r['id'] != 'SD-FRAUD'], [])                                   # no fraud screening domain
        d['maps'] = [m for m in d['maps'] if m[1] != 'EXPOSED_THROUGH' and m != ('PROC-SCREEN', 'USES_DOMAIN', 'SD-FRAUD')]   # the API is exposed through nothing
        d['A3'] = (d['A3'][0], [r for r in d['A3'][1] if r != link('APP-HUB', 'access', 'DATA-C')])        # two records, not three
        next(r for r in d['A4'][0] if r['id'] == 'SYS-KEYS')['attributes'].pop('conforms_to')              # nobody said which platform holds the keys
        self.build(d); out, _ = self.parts()
        gaps = {p: v for p, v in out.items() if v[0] not in ('compliant', 'not_applicable')}
        self.assertEqual(set(gaps), {'fraud-evaluation', 'fraud-process', 'edge-platform', 'payment-records', 'key-store'})
        self.assertEqual(gaps['fraud-evaluation'][1], 'no Fraud Evaluation (BIAN) in the design (A2.ServiceDomain where name = Fraud Evaluation)')
        self.assertIn('2 found, needs at least 3', gaps['payment-records'][1])
        self.assertEqual(gaps['key-store'][0], 'unresolved'); self.assertIn(f'name it with conforms_to "{PID}#key-store"', gaps['key-store'][1])   # SDEM never guesses which
        self.assertIn('through P10 from IFC-OPEN', gaps['edge-platform'][1])

    def test_the_edge_is_in_a_dmz_and_the_key_store_in_a_restricted_zone(self):   # CPL-08, PR-13a
        d = design(); d['A4'] = (d['A4'][0], [r for r in d['A4'][1] if r['target'] not in ('NODE-EDGE', 'NODE-SEC')] + [link('ZONE-I', 'aggregation', 'NODE-EDGE'), link('ZONE-I', 'aggregation', 'NODE-SEC')])
        self.build(d); out, _ = self.parts()
        self.assertEqual((out['edge-platform'][0], out['key-store'][0]), ('non_compliant', 'non_compliant'))
        self.assertIn('must be in a dmz zone', out['edge-platform'][1]); self.assertIn('must be in a private zone', out['key-store'][1])

    def test_it_says_nothing_about_a_design_that_is_not_payment_initiation(self):   # CPL-08
        d = design(); d['A2'] = ([r for r in d['A2'][0] if r['id'] != 'SD-POI'], []); d['maps'] = [m for m in d['maps'] if 'SD-POI' not in m]
        self.build(d)
        datasets, maps, mm, _ = comply.workspace_data(self.ws)
        self.assertEqual(patterns.evaluate(datasets, maps, mm, profile.structures(), profile.exceptions()), ([], []))


class InAWorkspace(Base):
    """Through the command line: SDEM says a pattern fits, a person includes it, and sdem status says where the design stands — once."""
    def new(self):
        code, out, err = sdem('new', '--workspace', self.ws, '--person', 'jane.architect', cwd=self.tmp); self.assertEqual(code, 0, err)
        code, out, err = sdem('bian', 'add', 'Payment Order Initiation', '--workspace', self.ws, '--person', 'jane.architect', cwd=self.tmp); self.assertEqual(code, 0, out + err)

    def status(self): return json.loads(sdem('status', '--workspace', self.ws, '--json', cwd=self.tmp)[1])

    def test_status_names_the_pattern_that_fits_the_design(self):   # CPL-09
        self.new(); s = self.status()
        self.assertEqual([(p['include'], p['id'], p['because']) for p in s['patterns_available']],
                         [(FILE, PID, 'SD-PAYMENT-ORDER-INITIATION'), ('sdem:sdem-pattern-bian-transact.json', 'PAT-BIAN-TRANSACT', 'SD-PAYMENT-ORDER-INITIATION')])   # the solution's own first, then its kind of domain's (CPL-12)
        self.assertTrue(any(n['person_decides'] and n['command'] == f'sdem profile include {FILE} --workspace {self.ws} --person <you>' for n in s['next']))
        text = sdem('status', '--workspace', self.ws, cwd=self.tmp)[1]
        self.assertIn('A pattern for this kind of solution ships with SDEM: Payment initiation', text)
        self.assertEqual(sdem('check', '--workspace', self.ws, cwd=self.tmp)[0], 0)   # nothing is applied until a person includes it

    def test_a_design_with_no_such_domain_is_offered_nothing(self):   # CPL-09
        code, out, err = sdem('new', '--workspace', self.ws, '--person', 'jane.architect', cwd=self.tmp); self.assertEqual(code, 0, err)
        self.assertEqual(self.status()['patterns_available'], [])

    def test_a_person_includes_it_with_one_command(self):   # CPL-10 (PR-38)
        self.new(); inc = lambda *a: sdem('profile', 'include', *a, '--workspace', self.ws, cwd=self.tmp)
        before = (self.ws / 'sdem-profile.json').read_text(encoding='utf-8')
        code, out, err = inc(FILE, '--person', 'sdem-a2-bian'); self.assertNotEqual(code, 0); self.assertIn("a person's decision", out + err)   # CTL-21
        code, out, err = inc('sdem:no-such.json', '--person', 'jane.architect'); self.assertNotEqual(code, 0); self.assertIn('SDEM ships no such standard or pattern', out + err)
        code, out, err = inc(FILE, '--person', 'jane.architect', '--dry-run', '--json'); self.assertEqual(code, 0, out + err)
        self.assertEqual((json.loads(out)['dry_run'], (self.ws / 'sdem-profile.json').read_text(encoding='utf-8')), (True, before))
        code, out, err = inc(FILE, '--person', 'jane.architect', '--json'); self.assertEqual(code, 0, out + err); r = json.loads(out)
        self.assertEqual((r['included'], r['kind'], r['id']), ([FILE], 'pattern', PID)); self.assertTrue(r['decision'].startswith('GD-'))
        self.assertEqual(_j(self.ws / 'sdem-profile.json')['includes'], ['sdem:sdem-completeness.json', FILE])
        gd = _j(next(self.ws.rglob(r['decision'] + '.json')))
        self.assertEqual((gd['kind'], gd['named_person'], gd['subject']), ('include_in_profile', 'jane.architect', FILE))
        code, out, err = inc(FILE, '--person', 'jane.architect', '--json'); self.assertEqual(code, 0); self.assertEqual(json.loads(out)['included'], [])   # already there: nothing to do
        self.assertEqual([p['id'] for p in self.status()['patterns_available']], ['PAT-BIAN-TRANSACT'])   # the one not yet included
        self.assertEqual(sdem('check', '--workspace', self.ws, cwd=self.tmp)[0], 0)   # every part is a warning: a gap is never a failed check

    def test_an_existing_workspace_takes_a_shipped_file_the_same_way(self):   # CPL-10, CPL-06
        shutil.copytree(ROOT / 'examples' / 'payment-initiation', self.ws, ignore=shutil.ignore_patterns('graph'))
        code, out, err = sdem('profile', 'include', 'sdem:sdem-completeness.json', '--workspace', self.ws, '--person', 'jane.architect', cwd=self.tmp); self.assertEqual(code, 0, out + err)
        self.assertEqual(_j(self.ws / 'sdem-profile.json')['includes'], ['sdem:sdem-completeness.json'])
        self.assertIsNotNone(self.status()['completeness'])

    def test_status_says_where_the_design_stands_against_it_once(self):   # CPL-11
        self.new(); sdem('profile', 'include', FILE, '--workspace', self.ws, '--person', 'jane.architect', cwd=self.tmp)
        s = self.status(); p = s['patterns'][0]
        self.assertEqual((p['pattern'], p['title'], p['anchor'], p['parts'], p['in_place']), (PID, 'Payment initiation', 'SD-PAYMENT-ORDER-INITIATION', 14, 0))
        self.assertIn('payment-process', [o['part'] for o in p['open']])
        self.assertFalse([x for x in s['warnings'] + s['unresolved'] + s['blocking'] if PID in x['text']])   # one block, not a line per part
        self.assertEqual(s['state'], 'open')
        text = sdem('status', '--workspace', self.ws, cwd=self.tmp)[1]
        self.assertIn('Pattern Payment initiation (SD-PAYMENT-ORDER-INITIATION): 0 of 14 parts in place — 14 to decide', text)
        self.assertIn('  no Process that receives the payment (A1.BusinessProcess) linked through P1 from SD-PAYMENT-ORDER-INITIATION — why: the business step that takes the payment order — what the solution is for', text)
        self.assertIn('… and 8 more (sdem comply)', text)


if __name__ == '__main__':
    unittest.main()
