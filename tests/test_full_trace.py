"""FT-01…FT-06 (docs/design/sdem-full-trace-spec.md): a trace walks a record's chain from A1 to A5 — the links between layers and the
part-whole links inside a layer — climbing to wholes, never into a whole's other parts; --direct-only gives the old answer. On the
made-up Payment Initiation design (examples/0.20/payment-initiation-v3)."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = {**os.environ, 'PYTHONPATH': str(ROOT), 'PYTHONIOENCODING': 'utf-8', 'SDEM_FORM': '0.20'}
SRC = ROOT / 'examples' / '0.20' / 'payment-initiation-v3' / 'sdem'


def sdem(*a, ok=(0,)):
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, a)], capture_output=True, text=True, encoding='utf-8', env=ENV, cwd=ROOT)
    assert r.returncode in ok, f"sdem {' '.join(map(str, a))}: {r.returncode}\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}"
    return r.stdout


def ids(tree):
    out = set()
    def walk(n):
        out.add(n['id']); [walk(c['node']) for c in n.get('children') or []]
    walk(tree); return out


class FullTrace(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp()); ws = cls.tmp / 'ws'; shutil.copytree(SRC, ws); cls.g = cls.tmp / 'graph'
        sdem('build', '--workspace', ws, '-o', cls.g)

    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.tmp, ignore_errors=True)

    def trace(self, rid, d, *flags):
        j = json.loads(sdem('trace', rid, '--graph', self.g, '--direction', d, '--json', *flags, ok=(0, 1)))   # 1: nothing in that direction
        return ids(j[d])

    def test_retrieve_reaches_a1_through_its_domain_and_a5_through_its_interface(self):   # FT-01, FT-02, FT-04
        up, down = self.trace('SO-PAYMENT-ORDER-INITIATION-RETRIEVE', 'up'), self.trace('SO-PAYMENT-ORDER-INITIATION-RETRIEVE', 'down')
        self.assertIn('SD-PAYMENT-ORDER-INITIATION', up); self.assertIn('PROC-STATUS', up)          # A1, through the domain it is part of
        self.assertIn('API-PAYMENT-READ', down); self.assertIn('IFC-PAYMENT-INITIATION', down)       # its API, and the interface that is part of
        self.assertTrue(any(i.startswith('NODE-') for i in down))                                   # A5, through the interface
        self.assertNotIn('SO-PAYMENT-ORDER-INITIATION-INITIATE', up | down)                          # never a sibling operation
        self.assertNotIn('API-PAYMENT-CREATE', up | down)

    def test_direct_only_is_the_old_answer(self):   # FT-03
        self.assertEqual(self.trace('SO-PAYMENT-ORDER-INITIATION-RETRIEVE', 'up', '--direct-only'), {'SO-PAYMENT-ORDER-INITIATION-RETRIEVE'})
        self.assertEqual(self.trace('SO-PAYMENT-ORDER-INITIATION-RETRIEVE', 'down', '--direct-only'), {'SO-PAYMENT-ORDER-INITIATION-RETRIEVE', 'API-PAYMENT-READ'})

    def test_realization_and_assignment_are_walked(self):   # FT-08
        stage, role = self.trace('ST-SUBMIT', 'down'), self.trace('ROLE-BANK', 'down')
        self.assertIn('PROC-SUBMIT', stage); self.assertTrue(any(i.startswith('SD-') for i in stage))   # a stage reaches A2 through the processes that realise it
        self.assertIn('PROC-STATUS', role); self.assertTrue(any(i.startswith('SD-') for i in role))     # a role through the processes it is assigned to
        up = self.trace('PROC-SUBMIT', 'up')
        self.assertIn('ST-SUBMIT', up); self.assertIn('ROLE-BANK', up)                                 # a process climbs to its stage and its role
        self.assertNotIn('PROC-VALIDATE', up)                                                         # never to the stage's other processes
        self.assertEqual(self.trace('ST-SUBMIT', 'down', '--direct-only'), {'ST-SUBMIT'})               # the links between layers alone: none

    def test_a_path_reaches_the_nodes_it_connects(self):   # FT-10
        up = self.trace('PATH-DATA', 'up')
        self.assertTrue({'NODE-APP', 'NODE-DATA'} <= up)                                              # its ends
        self.assertTrue(any(i.startswith('APP-') for i in up))                                        # what runs on them
        self.assertIn('PATH-KEY', self.trace('NODE-APP', 'up'))                                        # a node climbs to the paths it is on
        self.assertEqual(self.trace('PATH-DATA', 'up', '--direct-only'), {'PATH-DATA'})                  # the links between layers alone: none

    def test_a_process_reaches_the_data_of_the_domain_it_uses(self):   # FT-11
        G = ROOT / 'examples' / 'payment-initiation' / 'graph'
        j = json.loads(subprocess.run([sys.executable, '-m', 'sdem', 'trace', 'PRC-PAY-01', '--graph', str(G), '--direction', 'down', '--json'],
                                      capture_output=True, text=True, encoding='utf-8', env={**ENV, 'SDEM_FORM': '0.19'}, cwd=ROOT).stdout)
        down = ids(j['down'])
        self.assertIn('SD-PI', down); self.assertIn('BBO-PAY-INSTR', down); self.assertIn('ENT-PAY-INSTR', down)   # through the domain's business object, to Data
        self.assertNotIn('SO-PI-06', down)                                                                              # the domain's information is opened, never its other operations

    def test_an_actor_reaches_down_through_what_serves_it(self):   # FT-12
        down = self.trace('ACTOR-TPP', 'down')
        self.assertIn('SVC-INIT', down); self.assertTrue(any(i.startswith('SD-') for i in down))                    # the service, what realises it, and below
        self.assertIn('ACTOR-TPP', self.trace('SVC-INIT', 'up'))

    def test_a_domains_classification_is_not_an_orphan(self):   # FT-13
        up = self.trace('AT-PARTY-AUTHENTICATION', 'up')
        self.assertIn('SD-PARTY-AUTHENTICATION', up); self.assertTrue(any(i.startswith('PROC-') for i in up))
        self.assertNotIn('AT-PARTY-AUTHENTICATION', self.trace('PROC-AUTH', 'down'))                                # a domain reached is not opened into its classifiers

    def test_every_records_chain_for_a_view(self):   # MIP-03 (MID-02): one place computes; a view lights what it is given
        d = json.loads(sdem('trace', 'ALL', '--graph', self.g, '--json'))
        self.assertEqual(d['format'], 'sdem-chains/1'); self.assertEqual(d['kinds'], ['link', 'part', 'proposed'])
        ids, rid = d['ids'], 'SO-PAYMENT-ORDER-INITIATION-RETRIEVE'
        up = d['chains'][str(ids.index(rid))]['up']; reached = {ids[up[i]] for i in range(0, len(up), 4)}
        self.assertEqual(reached, self.trace(rid, 'up') - {rid})                                                     # the same chain as sdem trace

    def test_every_record_is_accounted_for_and_no_rule_gap(self):   # MIP-05, MID-05: traced through, or listed as a design gap — never a rule gap
        g = json.loads(sdem('trace', 'GAPS', '--graph', self.g, '--json'))
        self.assertEqual(g['format'], 'sdem-gaps/1'); self.assertEqual(g['records'], g['complete'] + g['within_a_gap'] + len(g['gaps']))
        self.assertEqual(g['within_a_gap'], sum(len(x.get('parts', [])) for x in g['gaps']))                    # a part of a gap is listed once, under its whole
        self.assertEqual([x['id'] for x in g['gaps'] if x['kind'] == 'rule'], [])                             # every link the design states is walked
        self.assertTrue(all(x['missing'] and x['reason'] for x in g['gaps']))                                  # each gap says what it misses and why
        self.assertEqual(sum(v['records'] for v in g['by_layer'].values()), g['records'])                    # MID-02: a view's per-layer figures
        self.assertTrue(all(v['linked'] <= v['records'] and v['complete'] <= v['records'] for v in g['by_layer'].values()))

    def test_a_completed_design_has_no_gap(self):   # MID-05 on a real design: the Payment example completed to every layer (examples/0.20/payment-initiation-v4)
        ws = ROOT / 'examples' / '0.20' / 'payment-initiation-v4' / 'sdem'
        g = Path(tempfile.mkdtemp()) / 'g'; self.addCleanup(shutil.rmtree, g.parent, True)
        sdem('build', '--workspace', ws, '-o', g)
        d = json.loads(sdem('trace', 'GAPS', '--graph', g, '--json'))
        self.assertEqual((d['design_gaps'], d['rule_gaps']), (0, 0), [x['id'] for x in d['gaps']])
        self.assertEqual(d['complete'], d['records'])

    def test_impact_classifies_a_record_by_its_shortest_path(self):   # KG-Q-09
        ms = json.loads((self.tmp / 'ws' / 'mappings.json').read_text(encoding='utf-8'))['mappings']
        for rid in ('APP-PAYHUB', 'SD-PAYMENT-ORDER-INITIATION', 'DATA-PAYMENT'):
            direct = {m['source']['id'] if m['target']['id'] == rid else m['target']['id'] for m in ms
                      if m.get('status') == 'approved' and rid in (m['source']['id'], m['target']['id'])}
            rows = json.loads(sdem('impact', rid, '--change', 'modify', '--graph', self.g, '--json'))['instances']
            for r in rows:
                if r['id'] in direct: self.assertIn(r['relation'], ('up1', 'down1'), (rid, r['id'], r['via']))


if __name__ == '__main__':
    unittest.main()
