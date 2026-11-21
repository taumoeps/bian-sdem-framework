"""BO-01…BO-09 (docs/design/sdem-bian-object-index-spec.md): BIAN's business objects ship as an index beside the base — typed fields,
no BIAN prose; never in a design by themselves; brought in one by one with --object; suggested for a design's data entities with their
evidence, writing nothing; a design with BIAN service domains and no business object is told. Made-up designs only."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem import bian as B  # noqa: E402

ENV = {**os.environ, 'PYTHONPATH': str(ROOT), 'PYTHONIOENCODING': 'utf-8'}
FIELD_KEYS = {'name', 'data_type', 'required', 'many', 'identifier', 'allowed_values', 'refers_to'}


def sdem(*a, ok=(0,)):
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, a)], capture_output=True, text=True, encoding='utf-8', env=ENV, cwd=ROOT)
    assert r.returncode in ok, f"sdem {' '.join(map(str, a))}: {r.returncode}\n{r.stdout[-1200:]}\n{r.stderr[-1200:]}"
    return r.stdout


def files(ws): return {p.name: p.read_bytes() for p in Path(ws).glob('*.json')}


class Index(unittest.TestCase):   # BO-01
    def setUp(self):
        self.base = B.base_file(); self.pack = json.loads(self.base.read_text(encoding='utf-8'))
        self.ix = B.index_for(self.base, self.pack['release'])

    def test_it_ships_beside_the_base_for_every_domain(self):
        self.assertIsNotNone(self.ix); self.assertEqual(self.ix['format'], B.INDEX_FORMAT); self.assertEqual(self.ix['release'], self.pack['release'])
        self.assertEqual(set(self.ix['domains']), {d['name'] for d in self.pack['domains']})
        n = sum(len(v) for v in self.ix['domains'].values()); self.assertGreater(n, 1000)

    def test_typed_fields_only_and_no_bian_prose(self):
        for fs in self.ix['definitions']:
            for f in fs: self.assertLessEqual(set(f), FIELD_KEYS)
        self.assertNotIn('"description"', B.index_for.__module__ and (self.base.parent / f"objects-{self.pack['release']}.json").read_text(encoding='utf-8'))
        crs = {d['name']: d['control_record'] for d in self.pack['domains']}
        for dom, m in self.ix['domains'].items(): self.assertNotIn(crs[dom], m)   # the control record is in the base already

    @unittest.skipUnless(os.environ.get('SDEM_BIAN_RELEASE'), 'set SDEM_BIAN_RELEASE to a downloaded BIAN release folder to compare')
    def test_it_is_what_bians_own_files_give(self):
        doms, refused = B.read_release(os.environ['SDEM_BIAN_RELEASE'])
        self.assertEqual(refused, []); self.assertEqual(B.object_index(doms), self.ix)


class Use(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp()); cls.ws = cls.tmp / 'ws'
        sdem('new', '--workspace', cls.ws, '--person', 'bo.check', '--example', 'payment-initiation', '--form', '0.20')

    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.tmp, ignore_errors=True)

    def bian(self): return json.loads((self.ws / 'bian.json').read_text(encoding='utf-8'))['instances']

    def test_suggest_ranks_the_plain_object_first_and_writes_nothing(self):   # BO-04, BO-05, BO-07
        before = files(self.ws)
        res = json.loads(sdem('bian', 'objects', 'suggest', '--workspace', self.ws, '--json'))
        self.assertEqual(files(self.ws), before)
        self.assertIn('not links', res['note'])
        by = {e['entity']: e for e in res['entities']}
        top = by['ENT-PAY-INSTR']['suggestions'][0]
        self.assertEqual(top['object'], 'PaymentInstruction')
        self.assertIn(['payment_instruction_reference', 'PaymentInstructionIdentification'], top['columns_matched'])
        self.assertTrue(top['already_here'])   # the example holds it already, under its own id
        self.assertEqual(top['id'], 'BBO-PAY-INSTR'); self.assertFalse(any('--object' in c for c in top['commands']))
        self.assertTrue(any('sdem connect BBO-PAY-INSTR MAPPED_TO ENT-PAY-INSTR' in c for c in top['commands']))
        other = next(x for e in res['entities'] for x in e['suggestions'] if not x['already_here'])   # one not in it: brought in first
        self.assertTrue(any(f"--object {other['object']}" in c for c in other['commands']))

    def test_object_from_the_base_is_exactly_the_one_named(self):   # BO-03
        before = {i['id'] for i in self.bian() if i['type'].endswith(('BusinessObject', 'BusinessObjectAttribute'))}
        sdem('bian', 'add', 'Payment Order Initiation', '--object', 'PaymentTransaction', '--workspace', self.ws, '--person', 'bo.check')
        after = [i for i in self.bian() if i['type'].endswith(('BusinessObject', 'BusinessObjectAttribute')) and i['id'] not in before]
        objs = [i for i in after if i['type'].endswith('BusinessObject')]
        self.assertEqual([o['id'] for o in objs], ['BBO-PAYMENT-TRANSACTION'])
        fields = [i for i in after if i['type'].endswith('BusinessObjectAttribute')]
        self.assertGreater(len(fields), 10); self.assertTrue(all((f.get('attributes') or {}).get('data_type') for f in fields))
        sdem('check', '--workspace', self.ws)


class Gap(unittest.TestCase):   # BO-06
    def test_status_says_when_bian_has_no_business_object(self):
        tmp = Path(tempfile.mkdtemp()); ws = tmp / 'ws'
        try:
            sdem('new', '--workspace', ws, '--person', 'bo.check', '--example', 'payment-initiation', '--form', '0.20')
            st = json.loads(sdem('status', '--workspace', ws, '--json', ok=(0, 1)))
            self.assertFalse(any(w['kind'] == 'bian_objects_missing' for w in st['warnings']))   # the example has business objects
            p = ws / 'bian.json'; d = json.loads(p.read_text(encoding='utf-8'))   # a made-up copy without them
            d['instances'] = [i for i in d['instances'] if not i['type'].endswith(('BusinessObject', 'BusinessObjectAttribute'))]
            p.write_text(json.dumps(d), encoding='utf-8')
            gap = subprocess.run([sys.executable, '-c', f'from sdem.bian import objects_gap; print(objects_gap({str(ws)!r}))'], capture_output=True, text=True, env=ENV, cwd=ROOT).stdout
            self.assertIn('service_domains', gap)   # in its own process: it reads the design's own numbering (ST-01), as every command does
            st = json.loads(sdem('status', '--workspace', ws, '--json', ok=(0, 1)))
            self.assertTrue(any(w['kind'] == 'bian_objects_missing' for w in st['warnings']))
            self.assertTrue(any('bian objects suggest' in n['command'] for n in st['next']))
        finally: shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
