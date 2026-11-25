"""`sdem aid` completes the first draft (docs/design/sdem-completeness-design.md stage 4; docs/design/aid-spec.md AID-D01…AID-D05): what a
standard or pattern finds missing, SDEM's written rules infer where the design gives evidence — every link marked inferred with the rule
that asked for it, for a person to confirm or reject. Rules, never an AI. Synthetic data only."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem import aid_complete  # noqa: E402
from sdem.metamodel import Metamodel  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
from forms import lf   # noqa: E402 — a layer's file in either form

ENV = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}
PATTERN = 'sdem:sdem-pattern-payment-initiation.json'


def sdem(*args, cwd):
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], cwd=cwd, capture_output=True, text=True, env=ENV)
    return r.returncode, r.stdout, r.stderr


def rec(i, t, n, **a): return {'id': i, 'type': t, 'version': '1', 'name': n, 'lifecycle_status': 'planned', 'attributes': a}
def mark(rule, why, frm, **k): return {'rule': rule, 'reasoning': why, 'from': frm, **k}


RULES = json.loads((ROOT / 'standards' / 'sdem-completeness.json').read_text(encoding='utf-8'))['rules']



def _pattern_file():   # BX-15: the Payment initiation pattern ships with sdem-bian (a banking pattern), under its old name
    from sdem import profile
    return profile.shipped('sdem:sdem-pattern-payment-initiation.json')

class Links(unittest.TestCase):
    """AID-D01, AID-D02 — the function, on a made-up application layer."""
    def run_(self, instances, rels=(), rejected=()):
        docs = {'A3': {'level': 'A3', 'instances': instances, 'relationships': [dict(zip(('source', 'kind', 'target'), r)) for r in rels]}}
        links, open_ = aid_complete.propose_links(docs, [], Metamodel.load(), RULES, mark, set(rejected))
        return [(r['source'], r['kind'], r['target'], r['inferred']['rule']) for r in links.get('A3', [])], open_, links.get('A3', [])

    APPS = [rec('APP-LEDGER', 'A3.ApplicationComponent', 'Account ledger'), rec('APP-RISK', 'A3.ApplicationComponent', 'Fraud service'), rec('APP-DOOR', 'A3.ApplicationComponent', 'Front door')]

    def test_a_distinctive_shared_word_gives_the_link(self):   # AID-D01
        got, open_, raw = self.run_(self.APPS + [rec('API-LEDGER', 'A3.ApplicationInterface', 'Ledger internal API'), rec('API-AUTH', 'A3.ApplicationInterface', 'Customer authorisation'),
                                                 rec('API-PAY', 'A3.ApplicationInterface', 'Payments')])
        self.assertEqual(got, [('APP-LEDGER', 'composition', 'API-LEDGER', 'AID-D01')])
        m = raw[0]['inferred']
        self.assertEqual((m['confidence'], m['evidence_class'], m['asked_by']), ('low', 'name_token', 'CPL-A3-01'))
        self.assertIn("share the word 'ledger'", m['reasoning'])
        self.assertEqual({(o['record'], o['rule']) for o in open_}, {('API-AUTH', 'CPL-A3-01'), ('API-PAY', 'CPL-A3-01')})   # no evidence: said, not guessed
        self.assertTrue(all('no name evidence' in o['why'] for o in open_))

    def test_a_word_many_records_share_is_no_evidence(self):   # AID-D01
        got, open_, _ = self.run_([rec('APP-A', 'A3.ApplicationComponent', 'Payments API hub'), rec('APP-B', 'A3.ApplicationComponent', 'Front door'),
                                   rec('API-ONE', 'A3.ApplicationInterface', 'One'), rec('API-TWO', 'A3.ApplicationInterface', 'Two'), rec('API-SIX', 'A3.ApplicationInterface', 'Six')])
        self.assertEqual(got, [])   # 'api' is in every interface's id: it singles out nothing

    def test_two_candidates_is_a_question_not_a_link(self):   # AID-D01
        got, open_, _ = self.run_([rec('APP-LEDGER', 'A3.ApplicationComponent', 'Account ledger'), rec('APP-POSTING', 'A3.ApplicationComponent', 'Posting engine'), rec('APP-C', 'A3.ApplicationComponent', 'Other'),
                                   rec('API-X', 'A3.ApplicationInterface', 'Ledger posting API'), rec('API-Y', 'A3.ApplicationInterface', 'Why'), rec('API-Z', 'A3.ApplicationInterface', 'Zed')])
        self.assertEqual(got, [])
        self.assertIn('APP-LEDGER or APP-POSTING', next(o['why'] for o in open_ if o['record'] == 'API-X'))

    def test_the_last_one_left_is_placed_by_elimination_and_flagged(self):   # AID-D02
        got, open_, raw = self.run_([rec('APP-LEDGER', 'A3.ApplicationComponent', 'Account ledger'), rec('APP-DOOR', 'A3.ApplicationComponent', 'Front door'),
                                     rec('API-LEDGER', 'A3.ApplicationInterface', 'Ledger internal API'), rec('API-AUTH', 'A3.ApplicationInterface', 'Customer authorisation')])
        self.assertEqual(got, [('APP-LEDGER', 'composition', 'API-LEDGER', 'AID-D01'), ('APP-DOOR', 'composition', 'API-AUTH', 'AID-D02')])
        m = raw[1]['inferred']
        self.assertEqual((m['confidence'], m['evidence_class']), ('low', 'structural')); self.assertIn('by elimination', m['reasoning']); self.assertIn('review this first', m['reasoning'])
        self.assertEqual(open_, [])

    def test_what_a_person_wrote_or_rejected_is_left_alone(self):   # AID-D01, AID-W05
        base = self.APPS + [rec('API-LEDGER', 'A3.ApplicationInterface', 'Ledger internal API'), rec('API-B', 'A3.ApplicationInterface', 'Bee'), rec('API-C', 'A3.ApplicationInterface', 'Sea')]
        self.assertEqual(self.run_(base, rels=[('APP-DOOR', 'composition', 'API-LEDGER')])[0], [])                # stated: no gap
        self.assertEqual(self.run_(base, rejected={'APP-LEDGER|composition|API-LEDGER'})[0], [])                 # rejected: never again
        self.assertIn('rejected', next(o['why'] for o in self.run_(base, rejected={'APP-LEDGER|composition|API-LEDGER'})[1] if o['record'] == 'API-LEDGER'))

    def test_one_link_that_closes_two_gaps_is_written_once(self):   # AID-D01 — found loading a design ChatGPT authored: the process's gap and the requirement's gap are the same link
        docs = {'A1': {'level': 'A1', 'instances': [rec('PROC-CONSENT', 'A1.BusinessProcess', 'Capture consent'), rec('PROC-PAY', 'A1.BusinessProcess', 'Take payment'),
                                                    rec('PROC-POST', 'A1.BusinessProcess', 'Post it'),
                                                    rec('R-01', 'A1.BusinessRequirement', 'Consent is recorded'), rec('R-02', 'A1.BusinessRequirement', 'Limits apply'), rec('R-03', 'A1.BusinessRequirement', 'Logs kept')], 'relationships': []}}
        links, open_ = aid_complete.propose_links(docs, [], Metamodel.load(), RULES, mark, set())
        self.assertEqual([(r['source'], r['kind'], r['target']) for r in links['A1']], [('PROC-CONSENT', 'realization', 'R-01')])
        self.assertFalse([o for o in open_ if o['record'] in ('PROC-CONSENT', 'R-01')])

    def test_nothing_is_built_on_an_unconfirmed_inferred_record(self):   # AID-W08
        ghost = rec('AID-APP', 'A3.ApplicationComponent', 'Ledger (inferred)', inferred={'rule': 'AID-F02'})
        got, _, _ = self.run_([ghost, rec('APP-DOOR', 'A3.ApplicationComponent', 'Front door'), rec('APP-E', 'A3.ApplicationComponent', 'Else'),
                               rec('API-LEDGER', 'A3.ApplicationInterface', 'Ledger internal API'), rec('API-B', 'A3.ApplicationInterface', 'Bee'), rec('API-C', 'A3.ApplicationInterface', 'Sea')])
        self.assertEqual(got, [])


class Defaults(unittest.TestCase):
    """AID-D08 — the option to complete the draft: a gap with no evidence is placed by default, said to be so, to review first."""
    def run_(self, instances, rels=(), rejected=(), complete=True):
        docs = {'A3': {'level': 'A3', 'instances': instances, 'relationships': [dict(zip(('source', 'kind', 'target'), r)) for r in rels]}}
        links, open_ = aid_complete.propose_links(docs, [], Metamodel.load(), RULES, mark, set(rejected), complete=complete)
        return [(r['source'], r['kind'], r['target'], r['inferred']['rule']) for r in links.get('A3', [])], open_, links.get('A3', [])

    BASE = [rec('APP-HUB', 'A3.ApplicationComponent', 'Hub'), rec('APP-DOOR', 'A3.ApplicationComponent', 'Front door'), rec('APP-SIDE', 'A3.ApplicationComponent', 'Side'),
            rec('API-ONE', 'A3.ApplicationInterface', 'One'), rec('API-TWO', 'A3.ApplicationInterface', 'Two'), rec('API-SIX', 'A3.ApplicationInterface', 'Six'),
            rec('DATA-A', 'A3.DataEntity', 'a'), rec('DATA-B', 'A3.DataEntity', 'b')]
    RELS = [('APP-HUB', 'access', 'DATA-A'), ('APP-HUB', 'access', 'DATA-B'), ('APP-HUB', 'flow', 'APP-DOOR'), ('APP-DOOR', 'composition', 'API-SIX')]

    def test_without_the_option_nothing_is_placed_without_evidence(self):   # AID-D03 stands
        got, open_, _ = self.run_(self.BASE, self.RELS, complete=False)
        self.assertEqual(got, []); self.assertEqual({o['record'] for o in open_ if o['rule'] == 'CPL-A3-01'}, {'API-ONE', 'API-TWO'})

    def test_with_it_every_gap_is_placed_and_marked_as_a_default(self):   # AID-D08
        got, open_, raw = self.run_(self.BASE, self.RELS)
        self.assertEqual(got, [('APP-HUB', 'composition', 'API-ONE', 'AID-D08'), ('APP-HUB', 'composition', 'API-TWO', 'AID-D08')])   # the most connected component
        m = raw[0]['inferred']
        self.assertEqual((m['confidence'], m['evidence_class'], m['default'], m['asked_by']), ('low', 'structural', True, 'CPL-A3-01'))
        self.assertIn('placed by default', m['reasoning']); self.assertIn('nothing in the design supports this link', m['reasoning']); self.assertIn('review this first', m['reasoning'])
        self.assertFalse([o for o in open_ if o['rule'] == 'CPL-A3-01'])

    def test_a_record_it_already_touches_comes_before_the_most_connected(self):   # AID-D08
        got, _, raw = self.run_(self.BASE, self.RELS + [('APP-SIDE', 'serving', 'API-ONE')])
        self.assertIn(('APP-SIDE', 'composition', 'API-ONE', 'AID-D08'), got)   # APP-SIDE already serves it: the one candidate linked to it
        self.assertIn('already linked', next(r['inferred']['reasoning'] for r in raw if r['target'] == 'API-ONE'))

    def test_a_default_a_person_rejected_is_not_replaced_by_another_guess(self):   # AID-D08, AID-W05
        got, open_, _ = self.run_(self.BASE, self.RELS, rejected={'APP-HUB|composition|API-ONE'})
        self.assertEqual(got, [('APP-HUB', 'composition', 'API-TWO', 'AID-D08')])
        self.assertIn('rejected', next(o['why'] for o in open_ if o['record'] == 'API-ONE'))


class DefaultsBetweenLayers(unittest.TestCase):
    """AID-D09 — with the option, a gap between layers no rule proposes a link for gets a default PROPOSAL: where the others of its kind go."""
    def docs(self):
        return {'A3': {'instances': [rec(f'DATA-{x}', 'A3.DataEntity', f'table {x}') for x in 'ABC'] + [rec('APP-1', 'A3.ApplicationComponent', 'App')],
                       'relationships': [{'source': 'APP-1', 'kind': 'access', 'target': f'DATA-{x}'} for x in 'ABC']},
                'A4': {'instances': [rec('SYS-DB', 'A4.SystemSoftware', 'Database'), rec('SYS-OLD', 'A4.SystemSoftware', 'Archive')], 'relationships': []}}

    def test_it_goes_where_the_others_go_and_says_it_is_a_default(self):
        got = aid_complete.default_across(self.docs(), [('DATA-A', 'STORED_IN', 'SYS-DB')], [('DATA-B', 'STORED_IN', 'SYS-DB')], Metamodel.load(), RULES)
        self.assertEqual([g[:3] for g in got if g[1] == 'STORED_IN'], [('DATA-C', 'STORED_IN', 'SYS-DB')])
        why = next(g[3] for g in got if g[0] == 'DATA-C')
        self.assertIn('placed by default', why); self.assertIn('2 other', why); self.assertIn('review this first', why)

    def test_one_other_record_is_not_where_the_others_go(self):   # AID-D09 — found on a real design: a component given another component's deployment
        docs = self.docs()
        docs['A3']['instances'] += [rec('APP-2', 'A3.ApplicationComponent', 'Other')]
        docs['A4']['instances'] += [rec('DEP-1', 'A4.Deployment', 'App — production', component_id='APP-1')]
        got = aid_complete.default_across(docs, [('APP-1', 'DEPLOYED_AS', 'DEP-1')], [], Metamodel.load(), RULES)
        self.assertEqual([g for g in got if g[0] == 'APP-2'], [])   # each component has its own deployment: one other having DEP-1 says nothing of APP-2
        self.assertEqual([g[:3] for g in aid_complete.default_across(self.docs(), [('DATA-A', 'STORED_IN', 'SYS-DB')], [], Metamodel.load(), RULES) if g[1] == 'STORED_IN'], [])   # one table in a store is not a habit either

    def test_with_nowhere_the_others_go_nothing_is_proposed(self):
        self.assertEqual([g for g in aid_complete.default_across(self.docs(), [], [], Metamodel.load(), RULES) if g[1] == 'STORED_IN'], [])

    def test_a_link_a_person_rejected_is_not_proposed_by_default(self):
        got = aid_complete.default_across(self.docs(), [('DATA-A', 'STORED_IN', 'SYS-DB')], [('DATA-B', 'STORED_IN', 'SYS-DB')], Metamodel.load(), RULES, decided={('DATA-C', 'STORED_IN', 'SYS-DB')})
        self.assertEqual([g for g in got if g[0] == 'DATA-C'], [])


class Parts(unittest.TestCase):
    """AID-D06, AID-D07 — a part a pattern requires: added when the design has nothing of its kind, named when a name says which it is."""
    PID = 'PAT-PAYMENT-INITIATION'

    def setUp(self):
        self.st = [{'pattern': (d := json.loads(_pattern_file().read_text(encoding='utf-8')))['pattern'], 'structure': d['structure'], 'file': 'x'}]

    def docs(self, a3=(), a3rels=(), a4=()):
        act = lambda i, t, n, **a: {**rec(i, t, n, **a), 'lifecycle_status': 'active'}
        return {'A1': {'instances': [act('PROC-PAY', 'A1.BusinessProcess', 'Take the payment')], 'relationships': []},
                'A2': {'instances': [act('SD-POI', 'A2.ServiceDomain', 'Payment Order Initiation')], 'relationships': []},
                'A3': {'instances': [act('APP-HUB', 'A3.ApplicationComponent', 'Hub'), *a3], 'relationships': [dict(zip(('source', 'kind', 'target'), r)) for r in a3rels]},
                'A4': {'instances': list(a4), 'relationships': []}}
    MAPS = [('PROC-PAY', 'USES_DOMAIN', 'SD-POI'), ('SD-POI', 'REALIZED_BY', 'APP-HUB')]

    def test_a_part_the_design_has_nothing_of_is_added_marked_inferred_and_linked(self):   # AID-D06
        new, links, props, ids = aid_complete.pattern_parts(self.docs(), self.MAPS, Metamodel.load(), self.st, mark)
        got = {r['id']: r for rs in new.values() for r in rs}
        stores = sorted(i for i in got if 'PAYMENT-RECORDS' in i)
        self.assertEqual(stores, [f'AID-{self.PID}-PAYMENT-RECORDS-{n}' for n in (1, 2, 3)])   # the pattern asks for three
        r = got[stores[0]]; m = r['attributes']['inferred']
        self.assertEqual((r['type'], r['lifecycle_status'], r['name']), ('A3.DataEntity', 'planned', 'Records of the consent, the payment and duplicate protection 1 (inferred)'))
        self.assertEqual((m['rule'], m['evidence_class'], m['confidence'], m['asked_by'], m['from']), ('AID-D06', 'pattern', 'low', f'{self.PID}/payment-records', 'SD-POI'))
        self.assertEqual(sorted((x['source'], x['kind'], x['target'], x['inferred']['rule']) for x in links['A3'] if x['kind'] == 'access' and x['source'] == 'APP-HUB'),
                         [('APP-HUB', 'access', s, 'AID-D06') for s in stores])
        self.assertIn(f'AID-{self.PID}-DATABASE', got)                                           # found through the records, so it follows them
        self.assertEqual(sorted(p[:3] for p in props if p[1] == 'STORED_IN'), [(s, 'STORED_IN', f'AID-{self.PID}-DATABASE') for s in stores])   # between layers: proposed, for a person to approve
        api = got[f'AID-{self.PID}-API']; self.assertIs(api['attributes']['internet_facing'], True)   # what the part says of itself
        self.assertEqual(len([i for i in got if 'API-OPERATIONS' in i]), 4)
        self.assertNotIn(f'AID-{self.PID}-EDGE-PLATFORM', got)                                    # 'an infrastructure component' is not a kind of record: a person says which
        self.assertFalse([i for i in got if got[i]['type'].startswith('A2.')])                    # BIAN records come from BIAN only (AID-S05, AID-D05)
        self.assertEqual(sorted(ids), sorted(got))

    def test_where_the_design_has_records_of_the_kind_nothing_is_added(self):   # AID-D06
        d = self.docs(a3=[rec('DATA-X', 'A3.DataEntity', 'a table')])
        new, links, props, ids = aid_complete.pattern_parts(d, self.MAPS, Metamodel.load(), self.st, mark)
        self.assertFalse([i for i in ids if 'RECORDS' in i or 'AUDIT' in i or 'DATABASE' in i])   # a table exists: which part it is, and what uses it, is a link to state — not a record to invent

    def test_a_rejected_part_is_not_added_again(self):   # AID-D06, AID-W05
        _, _, _, ids = aid_complete.pattern_parts(self.docs(), self.MAPS, Metamodel.load(), self.st, mark, {f'AID-{self.PID}-KEY-STORE'})
        self.assertNotIn(f'AID-{self.PID}-KEY-STORE', ids); self.assertIn(f'AID-{self.PID}-API', ids)

    def test_which_record_is_the_part_is_suggested_from_its_name_never_written(self):   # AID-D07
        a4 = [rec('SYS-DB', 'A4.SystemSoftware', 'Managed database'), rec('SYS-KMS', 'A4.SystemSoftware', 'Managed key custody'), rec('SYS-MQ', 'A4.SystemSoftware', 'Durable events')]
        d = self.docs(a4=a4); before = json.dumps(d, sort_keys=True)
        got = aid_complete.name_parts(d, self.MAPS, Metamodel.load(), self.st)
        self.assertEqual(json.dumps(d, sort_keys=True), before)
        k = next(x for x in got if x['part'] == 'key-store')
        self.assertEqual((k['pattern'], k['anchor'], k['candidates'], k['suggested'], k['conforms_to']), (self.PID, 'SD-POI', ['SYS-DB', 'SYS-KMS', 'SYS-MQ'], 'SYS-KMS', f'{self.PID}#key-store'))
        self.assertIn("'key'", k['why'])
        d2 = self.docs(a4=a4 + [rec('SYS-HSM', 'A4.SystemSoftware', 'Key module')])
        self.assertIsNone(next(x for x in aid_complete.name_parts(d2, self.MAPS, Metamodel.load(), self.st) if x['part'] == 'key-store')['suggested'])   # two say 'key': a person says which


class InAWorkspace(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, self.tmp, True); self.ws = self.tmp / 'ws'

    def ok(self, *a):
        code, out, err = sdem(*a, cwd=self.tmp); self.assertEqual(code, 0, (out + err)[-900:]); return out

    def propose(self, layer, agent, recs, rels=()):
        cs = {'layer': layer, 'reason': 'test', 'changes': [{'op': 'add', 'record': r} for r in recs], 'relationships': {'add': [dict(zip(('source', 'kind', 'target'), r)) for r in rels]}}
        f = self.tmp / f'{layer}.json'; f.write_text(json.dumps(cs), encoding='utf-8')
        self.ok('change', 'propose', f, '--workspace', self.ws, '--agent', agent, '--person', 'jane.architect')

    def a3(self): return json.loads(lf(self.ws, 'application').read_text(encoding='utf-8'))
    def inferred(self): return sorted((r['source'], r['kind'], r['target'], r['inferred']['rule'], r['inferred'].get('status')) for r in self.a3()['relationships'] if isinstance(r.get('inferred'), dict))

    def design(self):
        self.ok('new', '--workspace', self.ws, '--person', 'jane.architect')
        self.propose('application', 'sdem-a3-application', [rec('APP-LEDGER', 'A3.ApplicationComponent', 'Account ledger'), rec('APP-DOOR', 'A3.ApplicationComponent', 'Front door'), rec('APP-HUB', 'A3.ApplicationComponent', 'Hub'), rec('APP-OTHER', 'A3.ApplicationComponent', 'Other'),
                                                   rec('API-LEDGER', 'A3.ApplicationInterface', 'Ledger internal API'), rec('API-AUTH', 'A3.ApplicationInterface', 'Customer authorisation'),
                                                   rec('API-OPEN', 'A3.ApplicationInterface', 'Open payments')], [('APP-DOOR', 'composition', 'API-OPEN')])

    def test_aid_fills_the_gap_marks_it_and_says_what_it_could_not(self):   # AID-D01, AID-D03
        self.design()
        dry = json.loads(self.ok('aid', '--workspace', self.ws, '--person', 'jane.architect', '--dry-run', '--json'))
        self.assertEqual(dry['draft']['links_inferred'], 1); self.assertEqual(self.inferred(), [])   # a dry run writes nothing
        run = json.loads(self.ok('aid', '--workspace', self.ws, '--person', 'jane.architect', '--json'))
        self.assertEqual(self.inferred(), [('APP-LEDGER', 'composition', 'API-LEDGER', 'AID-D01', None)])
        self.assertEqual([(o['record'], o['rule']) for o in run['draft']['left_open'] if o['rule'] == 'CPL-A3-01'], [('API-AUTH', 'CPL-A3-01')])
        self.assertEqual(sdem('check', '--workspace', self.ws, cwd=self.tmp)[0], 0)
        s = json.loads(self.ok('status', '--workspace', self.ws, '--json'))
        self.assertEqual(s['completeness']['inferred_to_confirm'], 1)
        self.assertRegex(self.ok('status', '--workspace', self.ws), r'Completeness: .* — \d+ gaps?, 1 record connected only by an inferred link, to confirm')
        self.assertEqual(json.loads(self.ok('aid', '--workspace', self.ws, '--person', 'jane.architect', '--dry-run', '--json'))['draft']['links_inferred'], 0)   # not twice

    def test_the_option_completes_the_draft_and_status_says_what_rests_on_what(self):   # AID-D08, CPL-15
        self.design()
        self.propose('technology', 'sdem-a4-technology', [rec('DEP-LEDGER', 'A4.Deployment', 'Account ledger — production', component_id='APP-LEDGER')])
        run = json.loads(self.ok('aid', '--workspace', self.ws, '--person', 'jane.architect', '--complete-draft', '--json'))
        self.assertEqual(run['draft']['defaults'], 1)
        self.assertEqual([r for r in self.inferred() if r[3] == 'AID-D08'][0][:3][1:], ('composition', 'API-AUTH'))
        self.assertFalse([o for o in run['draft']['left_open'] if o['rule'] == 'CPL-A3-01'])
        self.ok('link', '--workspace', self.ws, '--out', self.ws / 'links', '--no-review')
        c = json.loads(self.ok('status', '--workspace', self.ws, '--json'))['completeness']
        self.assertEqual((c['inferred_to_confirm'], c['placed_by_default']), (3, 1))   # two interfaces, and the deployment SDEM placed (CPL-A4-05, standard 1.3)
        self.assertGreaterEqual(c['proposed_to_approve'], 1)   # APP-LEDGER DEPLOYED_AS DEP-LEDGER: proposed, not yet a person's — a gap still, and said to be covered
        text = self.ok('status', '--workspace', self.ws)
        self.assertRegex(text, r'Draft: \d+ of \d+ records connected counting what is inferred or proposed')
        self.assertIn('1 placed by default with no evidence — review first', text)

    def test_a_person_confirms_or_rejects_an_inferred_link_by_naming_it(self):   # AID-D04
        self.design(); self.ok('aid', '--workspace', self.ws, '--person', 'jane.architect')
        key = 'APP-LEDGER|composition|API-LEDGER'
        code, out, err = sdem('aid', 'confirm', key, '--workspace', self.ws, '--person', 'sdem-a3-application', cwd=self.tmp); self.assertNotEqual(code, 0)   # CTL-21: never an agent
        self.ok('aid', 'confirm', key, '--workspace', self.ws, '--person', 'jane.architect')
        self.assertEqual(self.inferred(), [('APP-LEDGER', 'composition', 'API-LEDGER', 'AID-D01', 'confirmed')])
        self.assertEqual(json.loads(self.ok('status', '--workspace', self.ws, '--json'))['completeness']['inferred_to_confirm'], 0)

    def test_a_rejected_link_is_removed_and_not_inferred_again(self):   # AID-D04
        self.design(); self.ok('aid', '--workspace', self.ws, '--person', 'jane.architect')
        self.ok('aid', 'reject', 'APP-LEDGER|composition|API-LEDGER', '--workspace', self.ws, '--person', 'jane.architect', '--reason', 'the hub offers it')
        self.assertEqual(self.inferred(), [])
        self.ok('aid', '--workspace', self.ws, '--person', 'jane.architect')
        self.assertEqual(self.inferred(), [])

    def test_aid_adds_the_parts_and_the_workspace_still_passes_its_checks(self):   # AID-D06, AID-D07
        self.ok('new', '--workspace', self.ws, '--person', 'jane.architect')
        self.ok('bian', 'add', 'Payment Order Initiation', '--workspace', self.ws, '--person', 'jane.architect')
        self.propose('business', 'sdem-a1-business', [rec('PROC-PAY', 'A1.BusinessProcess', 'Take the payment')])
        self.ok('profile', 'include', PATTERN, '--workspace', self.ws, '--person', 'jane.architect')
        run = json.loads(self.ok('aid', '--workspace', self.ws, '--person', 'jane.architect', '--json'))
        self.assertIn('AID-PAT-PAYMENT-INITIATION-KEY-STORE', run['draft']['parts_added']); self.assertTrue(all(i.startswith('AID-PAT-') for i in run['draft']['parts_added']))   # the solution's pattern, and its domain's kind (CPL-16: every pattern that fits is asked)
        a4 = {i['id']: i for i in json.loads(lf(self.ws, 'technology').read_text(encoding='utf-8'))['instances']}
        self.assertEqual(a4['AID-PAT-PAYMENT-INITIATION-KEY-STORE']['attributes']['inferred']['rule'], 'AID-D06')
        self.assertEqual(run['draft']['parts_to_name'], [])
        self.assertEqual(sdem('check', '--workspace', self.ws, cwd=self.tmp)[0], 0)
        one = 'AID-PAT-PAYMENT-INITIATION-KEY-STORE'
        self.ok('aid', 'reject', one, '--workspace', self.ws, '--person', 'jane.architect', '--reason', 'not in this design')
        again = json.loads(self.ok('aid', '--workspace', self.ws, '--person', 'jane.architect', '--dry-run', '--json'))
        self.assertNotIn(one, again['draft']['parts_added'])

    def test_a_bian_domain_the_pattern_names_is_brought_in_marked_inferred(self):   # AID-D05
        self.ok('new', '--workspace', self.ws, '--person', 'jane.architect')
        self.ok('bian', 'add', 'Payment Order Initiation', '--workspace', self.ws, '--person', 'jane.architect')
        self.propose('business', 'sdem-a1-business', [rec('PROC-SCREEN', 'A1.BusinessProcess', 'Screen for fraud'), rec('PROC-PAY', 'A1.BusinessProcess', 'Take the payment')])
        self.ok('profile', 'include', PATTERN, '--workspace', self.ws, '--person', 'jane.architect')
        run = json.loads(self.ok('aid', '--workspace', self.ws, '--person', 'jane.architect', '--json'))
        a2 = {i['id']: i for i in json.loads(lf(self.ws, 'bian').read_text(encoding='utf-8'))['instances']}
        m = a2['SD-FRAUD-EVALUATION']['attributes']['inferred']
        self.assertEqual((m['rule'], m['evidence_class'], m['asked_by']), ('AID-D05', 'pattern', 'PAT-PAYMENT-INITIATION/fraud-evaluation'))
        self.assertIn('SD-PARTY-AUTHENTICATION', a2)
        self.assertEqual(sorted(run['draft']['domains_added']), ['SD-FRAUD-EVALUATION', 'SD-PARTY-AUTHENTICATION'])
        props = json.loads((self.ws / run['proposals']).read_text(encoding='utf-8'))['mappings']
        uses = [(p['source']['id'], p['target']['id'], p['confidence']) for p in props if p['relationship'] == 'USES_DOMAIN' and 'AID-D05' in p['rationale']]
        self.assertEqual(uses, [('PROC-SCREEN', 'SD-FRAUD-EVALUATION', 0.4)])   # 'fraud' — proposed, for a person to approve; nothing points a process at Party Authentication
        self.assertEqual(sdem('check', '--workspace', self.ws, cwd=self.tmp)[0], 0)


if __name__ == '__main__':
    unittest.main()
