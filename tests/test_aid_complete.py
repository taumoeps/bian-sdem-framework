"""`sdem aid` completes the first draft (docs/design/sdem-completeness-design.md stage 4; docs/design/aid-spec.md AID-D01…AID-D05): what a
standard or pattern finds missing, SDEM's written rules infer where the design gives evidence — every link marked inferred with the rule
that asked for it, for a person to confirm or reject. Rules, never an AI. Synthetic data only."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem import aid_complete  # noqa: E402
from sdem.metamodel import Metamodel  # noqa: E402

ENV = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}
PATTERN = 'sdem:sdem-pattern-payment-initiation.json'


def sdem(*args, cwd):
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], cwd=cwd, capture_output=True, text=True, env=ENV)
    return r.returncode, r.stdout, r.stderr


def rec(i, t, n, **a): return {'id': i, 'type': t, 'version': '1', 'name': n, 'lifecycle_status': 'planned', 'attributes': a}
def mark(rule, why, frm, **k): return {'rule': rule, 'reasoning': why, 'from': frm, **k}


RULES = json.loads((ROOT / 'standards' / 'sdem-completeness.json').read_text(encoding='utf-8'))['rules']


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

    def test_nothing_is_built_on_an_unconfirmed_inferred_record(self):   # AID-W08
        ghost = rec('AID-APP', 'A3.ApplicationComponent', 'Ledger (inferred)', inferred={'rule': 'AID-F02'})
        got, _, _ = self.run_([ghost, rec('APP-DOOR', 'A3.ApplicationComponent', 'Front door'), rec('APP-E', 'A3.ApplicationComponent', 'Else'),
                               rec('API-LEDGER', 'A3.ApplicationInterface', 'Ledger internal API'), rec('API-B', 'A3.ApplicationInterface', 'Bee'), rec('API-C', 'A3.ApplicationInterface', 'Sea')])
        self.assertEqual(got, [])


class InAWorkspace(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, self.tmp, True); self.ws = self.tmp / 'ws'

    def ok(self, *a):
        code, out, err = sdem(*a, cwd=self.tmp); self.assertEqual(code, 0, (out + err)[-900:]); return out

    def propose(self, layer, agent, recs, rels=()):
        cs = {'layer': layer, 'reason': 'test', 'changes': [{'op': 'add', 'record': r} for r in recs], 'relationships': {'add': [dict(zip(('source', 'kind', 'target'), r)) for r in rels]}}
        f = self.tmp / f'{layer}.json'; f.write_text(json.dumps(cs), encoding='utf-8')
        self.ok('change', 'propose', f, '--workspace', self.ws, '--agent', agent, '--person', 'jane.architect')

    def a3(self): return json.loads((self.ws / 'a3-application.json').read_text(encoding='utf-8'))
    def inferred(self): return sorted((r['source'], r['kind'], r['target'], r['inferred']['rule'], r['inferred'].get('status')) for r in self.a3()['relationships'] if isinstance(r.get('inferred'), dict))

    def design(self):
        self.ok('new', '--workspace', self.ws, '--person', 'jane.architect')
        self.propose('A3', 'sdem-a3-application', [rec('APP-LEDGER', 'A3.ApplicationComponent', 'Account ledger'), rec('APP-DOOR', 'A3.ApplicationComponent', 'Front door'), rec('APP-HUB', 'A3.ApplicationComponent', 'Hub'), rec('APP-OTHER', 'A3.ApplicationComponent', 'Other'),
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

    def test_a_bian_domain_the_pattern_names_is_brought_in_marked_inferred(self):   # AID-D05
        self.ok('new', '--workspace', self.ws, '--person', 'jane.architect')
        self.ok('bian', 'add', 'Payment Order Initiation', '--workspace', self.ws, '--person', 'jane.architect')
        self.propose('A1', 'sdem-a1-business', [rec('PROC-SCREEN', 'A1.BusinessProcess', 'Screen for fraud'), rec('PROC-PAY', 'A1.BusinessProcess', 'Take the payment')])
        self.ok('profile', 'include', PATTERN, '--workspace', self.ws, '--person', 'jane.architect')
        run = json.loads(self.ok('aid', '--workspace', self.ws, '--person', 'jane.architect', '--json'))
        a2 = {i['id']: i for i in json.loads((self.ws / 'a2-service-domain.json').read_text(encoding='utf-8'))['instances']}
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
