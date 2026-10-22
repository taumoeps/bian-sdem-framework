"""Traceability gate: the official-mapping file, the planning document and the connector diagram agree."""
import json, re, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / 'metamodel/official-mappings.json').read_text())
DOC = (ROOT / 'docs/mapping-logic-planning.md').read_text()
PUML = (ROOT / 'metamodel/official-mappings.puml').read_text()
IDS = {m['id'] for m in DATA['mappings']}
GAP = json.loads((ROOT / 'metamodel/new-mappings.json').read_text())
DATA_BY = {m['id']: m for m in DATA['mappings']}


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

    def test_committed_diagram_equals_render_from_json(self):
        from sdmm.diagram import render
        self.assertEqual(PUML, render())

    def test_document_embeds_the_committed_diagram(self):
        a = DOC.index('```plantuml\n') + len('```plantuml\n'); b = DOC.index('```', a)
        self.assertEqual(DOC[a:b].strip(), PUML.strip())

    def test_gap_mapping_covers_every_id_with_required_fields(self):
        self.assertEqual({m['id'] for m in GAP['mappings']}, IDS)
        for m in GAP['mappings']:
            self.assertIn(m['confidence'], ('high', 'medium', 'low'), m['id'])
            self.assertIn(m['rule_decision'], GAP['rule_decisions'], m['id'])
            self.assertTrue(m['reasoning'] and len(m['reasoning']) > 40, m['id'])
            self.assertTrue(m['fill_step'] is None or str(m['fill_step']) in GAP['steps'], m['id'])
            self.assertEqual(m['official'], DATA_BY[m['id']]['verification'] in ('verified', 'verified_intent_or_target_only'), m['id'])

    def test_document_gap_table_carries_every_id(self):
        sec = section('### 5.3 ', '\n## ') if '\n## ' in DOC[DOC.index('### 5.3 '):] else DOC[DOC.index('### 5.3 '):]
        self.assertEqual(set(re.findall(r'^\| ([BS]\d{2}) \|', sec, flags=re.M)), IDS)

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


class NewMappingsDiagramTests(unittest.TestCase):
    def test_committed_new_diagram_equals_render_from_json(self):
        from sdmm.diagram import render_new
        self.assertEqual((ROOT / 'metamodel/new-mappings.puml').read_text(encoding='utf-8'), render_new())

    def test_new_diagram_draws_every_drawable_row_with_its_id(self):
        from sdmm.diagram import load_new, new_entries
        text = (ROOT / 'metamodel/new-mappings.puml').read_text(encoding='utf-8')
        rows = new_entries(load_new())
        self.assertEqual(len(rows), 50)
        for m in rows:
            self.assertIn(f": {m['id']} ", text)

    def test_planning_document_embeds_the_new_diagram(self):
        doc = (ROOT / 'docs/mapping-logic-planning.md').read_text(encoding='utf-8')
        self.assertIn((ROOT / 'metamodel/new-mappings.puml').read_text(encoding='utf-8'), doc)


class LevelStructureDiagramTests(unittest.TestCase):
    def test_committed_level_diagram_equals_render(self):
        from sdmm.diagram import render_levels
        self.assertEqual((ROOT / 'metamodel/level-relationships.puml').read_text(encoding='utf-8'), render_levels())

    def test_a2_section_draws_every_constraint(self):
        lr = json.loads((ROOT / 'metamodel/level-relationships.json').read_text(encoding='utf-8'))
        text = (ROOT / 'metamodel/level-relationships.puml').read_text(encoding='utf-8')
        a2 = text[text.index('package "A2'):text.index('package "A3')]
        self.assertEqual(a2.count(']-> '), sum(1 for c in lr['constraints'] if c['level'] == 'A2'))


class MergedDiagramTests(unittest.TestCase):
    def test_committed_merged_diagram_equals_render(self):
        from sdmm.diagram import render_merged
        self.assertEqual((ROOT / 'metamodel/merged-mappings.puml').read_text(encoding='utf-8'), render_merged())

    def test_merged_holds_every_cross_level_id_and_the_a2_constraints(self):
        from sdmm.diagram import load_new, new_entries
        text = (ROOT / 'metamodel/merged-mappings.puml').read_text(encoding='utf-8')
        for m in new_entries(load_new()):
            self.assertIn(f": {m['id']}", text)
        lr = json.loads((ROOT / 'metamodel/level-relationships.json').read_text(encoding='utf-8'))
        a2 = text[text.index('package "A2'):text.index('package "A3')]
        self.assertEqual(a2.count('#B0BEC5'), sum(1 for c in lr['constraints'] if c['level'] == 'A2'))
