"""Traceability gate: the official-mapping file, the planning document and the connector diagram agree."""
import json, re, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / 'metamodel/official-mappings.json').read_text())
DOC = (ROOT / 'docs/mapping-logic-planning.md').read_text()
PUML = (ROOT / 'docs/diagrams/official-mappings.puml').read_text()
IDS = {m['id'] for m in DATA['mappings']}


def section(start, end):
    return DOC[DOC.index(start):DOC.index(end)]


class TraceabilityTests(unittest.TestCase):
    def test_ids_are_unique_and_complete(self):
        self.assertEqual(len(IDS), len(DATA['mappings']))
        self.assertEqual({m['id'] for m in DATA['mappings'] if m['tier'] == 'official_bian_only'}, {f'B{i:02d}' for i in range(1, 16)})
        self.assertEqual({m['id'] for m in DATA['mappings'] if m['tier'] != 'official_bian_only'}, {f'S{i:02d}' for i in range(1, 55)})

    def test_document_tables_carry_every_id(self):
        b = set(re.findall(r'^\| (B\d{2}) \|', section('### 1.2 ', '### 1.3 '), flags=re.M))
        s = set(re.findall(r'^\| (S\d{2}) \|', section('### 2.3 ', '### 2.4 '), flags=re.M))
        m = set(re.findall(r'^\| ([BS]\d{2}) \|', section('### 3.1 ', '## 4. '), flags=re.M))
        self.assertEqual(b | s, IDS); self.assertEqual(m, IDS)

    def test_diagram_draws_exactly_the_verified_set(self):
        drawn = re.findall(r': ([BS]\d{2}) ', PUML)
        self.assertEqual(len(drawn), len(set(drawn)))
        expected = {m['id'] for m in DATA['mappings'] if m['verification'] in ('verified', 'verified_intent_or_target_only') and m['id'] != 'B01'}
        self.assertEqual(set(drawn), expected)
        self.assertEqual(len(expected), 24)

    def test_every_entity_in_file_exists_in_catalogue(self):
        from sdmm.metamodel import Metamodel
        mm = Metamodel.load()
        for m in DATA['mappings']:
            self.assertTrue(mm.known(m['source']), m['id']); self.assertTrue(mm.known(m['target']), m['id'])

    def test_registry_rules_named_in_file_exist(self):
        rules = {(r['source_type'], r['relationship'], r['target_type']) for r in json.loads((ROOT / 'schema/relationship-types.json').read_text())['relationships']}
        for m in DATA['mappings']:
            if m.get('sdmm_rule'):
                self.assertIn((m['source'], m['sdmm_rule'], m['target']), rules, m['id'])


if __name__ == '__main__':
    unittest.main()
