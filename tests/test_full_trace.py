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


if __name__ == '__main__':
    unittest.main()
