"""DAR-01…DAR-11 (docs/design/sdem-data-architecture-spec.md): a data domain, ownership, read and write on an access link, lineage derived
from them, the trace through a domain, two requirement categories and what sdem status says. On the bundled example in the 0.20 form —
made-up data."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = {**os.environ, 'PYTHONPATH': str(ROOT), 'PYTHONIOENCODING': 'utf-8'}


def sdem(*a, ok=(0,)):
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, a)], capture_output=True, text=True, encoding='utf-8', env=ENV)
    assert r.returncode in ok, f"sdem {' '.join(map(str, a))}: {r.returncode}\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}"
    return r.stdout if '--json' in a else r.stdout + r.stderr   # --json: the answer alone (a baseline line goes to stderr)


def ids(tree):
    out = set()
    def walk(n): out.add(n['id']); [walk(c['node']) for c in n.get('children') or []]
    walk(tree); return out


class DataArchitecture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp()); ws = cls.ws = cls.tmp / 'ws'
        sdem('new', '--workspace', ws, '--person', 'steven', '--example', 'payment-initiation', '--form', '0.20')
        cs = {'layer': 'data', 'reason': 'a payments domain (made-up)', 'changes': [
            {'op': 'add', 'record': {'id': 'DOM-PAY', 'type': 'data.DataDomain', 'version': '1', 'name': 'Payments', 'lifecycle_status': 'planned',
                                     'attributes': {'domain_kind': 'domain', 'data_owner': 'ROLE-PAY-OFFICER'}}},
            {'op': 'add', 'record': {'id': 'DOM-PAY-INSTR', 'type': 'data.DataDomain', 'version': '1', 'name': 'Payment instructions', 'lifecycle_status': 'planned',
                                     'attributes': {'domain_kind': 'subject_area'}}}],
            'relationships': {'add': [{'source': 'DOM-PAY', 'kind': 'aggregation', 'target': 'DOM-PAY-INSTR'},
                                      {'source': 'DOM-PAY-INSTR', 'kind': 'aggregation', 'target': 'ENT-PAY-INSTR'},
                                      {'source': 'DOM-PAY', 'kind': 'aggregation', 'target': 'ENT-PAY-EVENT'}]}}
        (cls.tmp / 'cs.json').write_text(json.dumps(cs))
        sdem('change', 'propose', cls.tmp / 'cs.json', '--workspace', ws, '--agent', 'sdem-data', '--person', 'steven')
        ms = json.loads((ws / 'mappings.json').read_text(encoding='utf-8'))['mappings']
        acc = {(m['source']['id'], m['target']['id']): m['mapping_id'] for m in ms if m['relationship'] == 'ACCESSED_BY'}
        cls.write_instr, cls.read_instr = acc[('ENT-PAY-INSTR', 'CMP-PAY-CAPTURE')], acc[('ENT-PAY-INSTR', 'CMP-PAY-EXEC')]
        sdem('data', 'mode', cls.write_instr, 'write', '--workspace', ws, '--person', 'steven', '--rationale', 'capture records the instruction')
        sdem('data', 'mode', cls.read_instr, 'read', '--workspace', ws, '--person', 'steven', '--rationale', 'execution reads it')
        sdem('connect', 'ENT-PAY-EVENT', 'ACCESSED_BY', 'CMP-PAY-EXEC', '--workspace', ws, '--person', 'steven', '--evidence',
             'application_architecture_document:made-up#1', '--rationale', 'execution writes the event', '--access-mode', 'write')
        cls.g = cls.tmp / 'graph'; sdem('build', '--workspace', ws, '-o', cls.g)

    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_a_domain_nests_and_the_design_passes(self):   # DAR-01
        self.assertIn('OK', sdem('check', '--workspace', self.ws))
        bad = {'layer': 'data', 'reason': 'x', 'changes': [], 'relationships': {'add': [{'source': 'DOM-PAY', 'kind': 'composition', 'target': 'ENT-ACCOUNT-CACHE'}]}}
        (self.tmp / 'bad.json').write_text(json.dumps(bad))
        out = sdem('change', 'propose', self.tmp / 'bad.json', '--workspace', self.ws, '--agent', 'sdem-data', '--person', 'steven', '--dry-run', ok=(1, 2))
        self.assertIn('composition', out)                                                                   # aggregation only

    def test_the_mode_is_on_access_links_only(self):   # DAR-03
        ms = {m['mapping_id']: m for m in json.loads((self.ws / 'mappings.json').read_text(encoding='utf-8'))['mappings']}
        self.assertEqual(ms[self.write_instr]['access_mode'], 'write')
        other = next(i for i, m in ms.items() if m['relationship'] != 'ACCESSED_BY')
        self.assertIn('only on ACCESSED_BY', sdem('data', 'mode', other, 'read', '--workspace', self.ws, '--person', 'steven', '--rationale', 'x', ok=(1,)))
        self.assertIn('only on ACCESSED_BY', sdem('connect', 'CAP-PAY-010', 'SUPPORTED_BY', 'SD-PI', '--workspace', self.ws, '--person', 'steven', '--evidence',
                                                  'x:y#1', '--rationale', 'x', '--access-mode', 'read', '--dry-run', ok=(1,)))
        decisions = [json.loads(f.read_text()) for f in (self.ws / 'decisions').glob('GD-*.json')]
        self.assertTrue(any(d['kind'] == 'state_access_mode' and d['subject'] == self.write_instr for d in decisions))   # a person's decision, recorded

    def test_lineage_from_read_and_write_and_never_guessed(self):   # DAR-04
        r = json.loads(sdem('data', 'lineage', 'ENT-PAY-EVENT', '--workspace', self.ws, '--json'))
        self.assertIn({'from': 'ENT-PAY-INSTR', 'through': 'CMP-PAY-EXEC', 'to': 'ENT-PAY-EVENT'}, r['upstream'])
        r = json.loads(sdem('data', 'lineage', 'ENT-PAY-INSTR', '--workspace', self.ws, '--json'))
        self.assertEqual(r['written_by'], ['CMP-PAY-CAPTURE']); self.assertIn('CMP-PAY-EXEC', r['read_by'])
        self.assertTrue(r['mode_not_stated'])                                                               # the validation step's access: listed, not guessed
        self.assertNotIn('CMP-PAY-VALIDATE', r['read_by'] + r['written_by'])

    def test_the_trace_climbs_to_a_domain_never_into_its_other_entities(self):   # DAR-05
        j = json.loads(sdem('trace', 'ENT-PAY-INSTR', '--graph', self.g, '--direction', 'up', '--json'))
        up = ids(j['up'])
        self.assertIn('DOM-PAY-INSTR', up); self.assertIn('DOM-PAY', up)
        self.assertNotIn('ENT-PAY-EVENT', up)

    def test_quality_and_retention_are_requirement_categories(self):   # DAR-06
        schema = json.loads((ROOT / 'schema' / 'requirements.schema.json').read_text(encoding='utf-8'))
        self.assertTrue({'data_quality', 'data_retention'} <= set(json.dumps(schema).split('"')))

    def test_status_says_the_gaps_once_the_design_uses_it(self):   # DAR-07
        j = json.loads(sdem('status', '--workspace', self.ws, '--json', ok=(0, 1)))
        text = json.dumps(j['warnings'])
        self.assertIn('ENT-ACCOUNT-CACHE', text)                                                           # in no domain
        self.assertIn('DAR-07', text)
        fresh = self.tmp / 'fresh'; sdem('new', '--workspace', fresh, '--person', 'steven', '--example', 'payment-initiation', '--form', '0.20')
        self.assertNotIn('DAR-07', sdem('status', '--workspace', fresh, '--json', ok=(0, 1)))               # a design that has not started: nothing said


if __name__ == '__main__':
    unittest.main()
