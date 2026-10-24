"""Traceability gate: the official-mapping file, the planning document and the connector diagram agree."""
import json, re, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / 'metamodel/official-mappings.json').read_text())
DOC = (ROOT / 'docs/mapping-logic-planning.md').read_text()
PUML = (ROOT / 'metamodel/official-mappings.puml').read_text()
IDS = {m['id'] for m in DATA['mappings']}
GAP = json.loads((ROOT / 'metamodel/relationship-rules.json').read_text())
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
        from sdem.diagram import render
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
        from sdem.metamodel import Metamodel
        mm = Metamodel.load()
        for m in DATA['mappings']:
            self.assertTrue(mm.known(m['source']), m['id']); self.assertTrue(mm.known(m['target']), m['id'])

    def test_registry_rules_named_in_file_exist(self):
        rules = {(r['source_type'], r['relationship'], r['target_type']) for r in json.loads((ROOT / 'schema/relationship-types.json').read_text())['relationships']}
        for m in DATA['mappings']:
            if m.get('sdem_rule'):
                self.assertIn((m['source'], m['sdem_rule'], m['target']), rules, m['id'])


if __name__ == '__main__':
    unittest.main()


class NewMappingsDiagramTests(unittest.TestCase):
    def test_committed_new_diagram_equals_render_from_json(self):
        from sdem.diagram import render_new
        self.assertEqual((ROOT / 'metamodel/relationship-rules.puml').read_text(encoding='utf-8'), render_new())

    def test_new_diagram_draws_every_drawable_row_with_its_id(self):
        from sdem.diagram import load_new, new_entries
        text = (ROOT / 'metamodel/relationship-rules.puml').read_text(encoding='utf-8')
        rows = new_entries(load_new())
        self.assertEqual(len(rows), 50)
        for m in rows:
            self.assertIn(f": {m['id']} ", text)

    def test_planning_document_embeds_the_new_diagram(self):
        doc = (ROOT / 'docs/mapping-logic-planning.md').read_text(encoding='utf-8')
        self.assertIn((ROOT / 'metamodel/relationship-rules.puml').read_text(encoding='utf-8'), doc)


class LevelStructureDiagramTests(unittest.TestCase):
    def test_committed_level_diagram_equals_render(self):
        from sdem.diagram import render_levels
        self.assertEqual((ROOT / 'metamodel/level-relationships.puml').read_text(encoding='utf-8'), render_levels())

    def test_a2_section_draws_every_constraint(self):
        lr = json.loads((ROOT / 'metamodel/level-relationships.json').read_text(encoding='utf-8'))
        text = (ROOT / 'metamodel/level-relationships.puml').read_text(encoding='utf-8')
        a2 = text[text.index('package "A2'):text.index('package "A3')]
        self.assertEqual(a2.count(']-> '), sum(1 for c in lr['constraints'] if c['level'] == 'A2'))


class MergedDiagramTests(unittest.TestCase):
    def test_committed_merged_diagram_equals_render(self):
        from sdem.diagram import render_merged
        self.assertEqual((ROOT / 'metamodel/merged-relationships.puml').read_text(encoding='utf-8'), render_merged())

    def test_merged_holds_every_cross_level_id_and_the_a2_constraints(self):
        from sdem.diagram import load_new, new_entries
        text = (ROOT / 'metamodel/merged-relationships.puml').read_text(encoding='utf-8')
        for m in new_entries(load_new()):
            self.assertIn(f": {m['id']}", text)
        lr = json.loads((ROOT / 'metamodel/level-relationships.json').read_text(encoding='utf-8'))
        a2 = text[text.index('package "A2'):text.index('package "A3')]
        self.assertEqual(a2.count('#B0BEC5'), sum(1 for c in lr['constraints'] if c['level'] == 'A2'))


class OfficialRowsAreConstraintsTests(unittest.TestCase):
    """Every BIAN-internal row of the official record (B02–B15, inside A2) must be an A2 constraint the
    graph checker enforces — the two records may not drift apart again (found by the within-level diagram, v0.5.14)."""

    def test_every_b_row_inside_a2_has_a_constraint(self):
        official = json.loads((ROOT / 'metamodel/official-mappings.json').read_text(encoding='utf-8'))['mappings']
        lr = json.loads((ROOT / 'metamodel/level-relationships.json').read_text(encoding='utf-8'))
        pairs = {(c['source_type'], c['target_type']) for c in lr['constraints'] if c['level'] == 'A2'}
        missing = [m['id'] for m in official if m['id'].startswith('B') and m['id'] != 'B01'
                   and m['source'].startswith('A2.') and m['target'].startswith('A2.')
                   and (m['source'], m['target']) not in pairs and (m['target'], m['source']) not in pairs]
        self.assertEqual(missing, [])


class RelationshipsPlanningTests(unittest.TestCase):
    def test_document_equals_render_from_json(self):
        from sdem.relationships import render
        self.assertEqual((ROOT / 'docs/relationships-planning.md').read_text(encoding='utf-8'), render())

    def test_every_row_has_id_and_provenance_fields(self):
        lr = json.loads((ROOT / 'metamodel/level-relationships.json').read_text(encoding='utf-8'))
        ids = [c['id'] for c in lr['constraints']]
        self.assertEqual(len(ids), len(set(ids)))
        for c in lr['constraints']:
            for k in ('id', 'description', 'reference_source', 'reasoning', 'confidence', 'verification'):
                self.assertTrue(c.get(k), f"{c.get('id')} lacks {k}")
            self.assertIn(c['confidence'], ('high', 'medium', 'low'))
        a2_official = {c['official_id'] for c in lr['constraints'] if c['level'] == 'A2' and c.get('official_id')}
        self.assertEqual(a2_official, {f'B{n:02d}' for n in range(2, 16)})


class InferredRowsTests(unittest.TestCase):
    def test_every_non_a2_row_carries_a_complete_inference(self):
        lr = json.loads((ROOT / 'metamodel/level-relationships.json').read_text(encoding='utf-8'))
        for c in lr['constraints']:
            if c['level'] == 'A2':
                self.assertNotIn('inference', c); continue
            i = c.get('inference'); self.assertIsNotNone(i, c['id'])
            for k in ('archimate_source', 'archimate_target', 'pattern', 'reasoning', 'confidence', 'test'):
                self.assertTrue(i.get(k), f"{c['id']} inference lacks {k}")
            self.assertIn(i['confidence'], ('high', 'medium', 'low'))


class PlanTableStepAndConfidenceTests(unittest.TestCase):
    """§5.3's fill-step and confidence columns must equal relationship-rules.json (the reasoning column is already checked)."""

    def test_step_and_confidence_columns_match_json(self):
        import re
        nm = {m['id']: m for m in json.loads((ROOT / 'metamodel/relationship-rules.json').read_text(encoding='utf-8'))['mappings']}
        doc = (ROOT / 'docs/mapping-logic-planning.md').read_text(encoding='utf-8')
        sec = doc[doc.index('### 5.3 New mappings'):doc.index('### 5.4')]
        seen = 0
        for mo in re.finditer(r"^\| (S\d+|B\d+) \| (?:[^|]*\| ){4}([^|]*?) \| (\*\*\w+\*\*|\w+) \| ", sec, flags=re.M):
            mid, step, conf = mo.groups(); m = nm[mid]; seen += 1
            self.assertEqual(step, '—' if m.get('fill_step') is None else str(m['fill_step']), mid)
            self.assertEqual(conf.strip('*'), m['confidence'], mid)
        self.assertEqual(seen, 69)


class DesignSpecTests(unittest.TestCase):
    def test_spec_equals_render_from_records(self):
        from sdem.spec import render
        self.assertEqual((ROOT / 'docs/relationship-rules-spec.md').read_text(encoding='utf-8'), render())

    def test_every_requirement_is_traced(self):
        import re
        doc = (ROOT / 'docs/relationship-rules-spec.md').read_text(encoding='utf-8')
        idx = doc[doc.index('## 10. Requirements index'):]
        rows = [l for l in idx.splitlines() if l.startswith('| REQ-')]
        self.assertGreaterEqual(len(rows), 30)
        ids = []
        for l in rows:
            cells = [c.strip() for c in l.strip().strip('|').split(' | ')]
            self.assertGreaterEqual(len(cells), 4, l[:60]); ids.append(cells[0])
            self.assertTrue(cells[-1] and cells[-2], cells[0])
        self.assertEqual(len(ids), len(set(ids)))
        nm = {m['id'] for m in json.loads((ROOT / 'metamodel/relationship-rules.json').read_text(encoding='utf-8'))['mappings'] if m['rule_decision'] == 'registry_rule'}
        for pid in nm:
            self.assertIn(f"{pid}: propose", idx)


class DesignDiagramTests(unittest.TestCase):
    def test_design_diagram_equals_render_and_carries_every_id(self):
        from sdem.spec import render_diagram
        from sdem.diagram import load_new, new_entries
        text = (ROOT / 'docs/architecture-model-diagram.puml').read_text(encoding='utf-8')
        self.assertEqual(text, render_diagram())
        lr = json.loads((ROOT / 'metamodel/level-relationships.json').read_text(encoding='utf-8'))
        for c in lr['constraints']:
            self.assertIn(c['id'], text)
        for m in new_entries(load_new()):
            self.assertIn(f": {m['id']}", text)

    def test_every_convention_key_has_an_id_in_the_record_and_the_spec(self):
        conv = json.loads((ROOT / 'metamodel/export-conventions.json').read_text(encoding='utf-8'))
        doc = (ROOT / 'docs/relationship-rules-spec.md').read_text(encoding='utf-8')
        for ent, keys in conv['conventions'].items():
            for k in keys:
                kid = conv['key_ids'][f'{ent}.{k}']; self.assertIn(f"| {kid} | {ent} | `{k}` |", doc)


class KnowledgeGraphSpecTests(unittest.TestCase):
    def test_kg_spec_equals_render(self):
        from sdem.kgspec import render
        self.assertEqual((ROOT / 'docs/knowledge-graph-spec.md').read_text(encoding='utf-8'), render())

    def test_every_registry_relationship_and_schema_field_is_specified(self):
        doc = (ROOT / 'docs/knowledge-graph-spec.md').read_text(encoding='utf-8')
        reg = json.loads((ROOT / 'schema/relationship-types.json').read_text(encoding='utf-8'))
        for r in reg['relationships']:
            self.assertIn(r['mapping_type_id'], doc)
        ms = json.loads((ROOT / 'schema/relationship-registry.schema.json').read_text(encoding='utf-8'))
        for f in ms['$defs']['mapping']['properties']:
            self.assertIn(f"| `{f}` |", doc)


class MappingModelDocsAlignTests(unittest.TestCase):
    """The overview, the spec and the diagram use the same terms and the same numbers."""

    def test_overview_numbers_match_the_records(self):
        import re
        from collections import Counter
        from sdem.metamodel import Metamodel
        from sdem.diagram import new_entries, load_new
        doc = (ROOT / 'docs/sdem-overview.md').read_text(encoding='utf-8')
        sec = doc[doc.index('## The architecture model in numbers'):doc.index('## Reading the architecture-model diagram')]
        counts = [int(x) for x in re.findall(r"^\| [^|]+ \| (\d+) \|", sec, flags=re.M)]
        lr = json.loads((ROOT / 'metamodel/level-relationships.json').read_text(encoding='utf-8'))
        nm = json.loads((ROOT / 'metamodel/relationship-rules.json').read_text(encoding='utf-8'))['mappings']
        reg = json.loads((ROOT / 'schema/relationship-types.json').read_text(encoding='utf-8'))['relationships']
        conv = json.loads((ROOT / 'metamodel/export-conventions.json').read_text(encoding='utf-8'))
        spec = (ROOT / 'docs/relationship-rules-spec.md').read_text(encoding='utf-8')
        reqs = len([l for l in spec[spec.index('## 10. Requirements index'):].splitlines() if l.startswith('| REQ-')])
        expected = [len(Metamodel.load().entities), len(lr['constraints']), len(reg), len(nm), len(new_entries(load_new())),
                    Counter(m['rule_decision'] for m in nm)['registry_rule'], len(conv['key_ids']), reqs]
        self.assertEqual(counts, expected)

    def test_diagram_title_counts_match(self):
        from sdem.diagram import new_entries, load_new
        text = (ROOT / 'docs/architecture-model-diagram.puml').read_text(encoding='utf-8')
        lr = json.loads((ROOT / 'metamodel/level-relationships.json').read_text(encoding='utf-8'))
        self.assertIn(f"{len(lr['constraints'])} within-level rows", text)
        self.assertIn(f"{len(new_entries(load_new()))} cross-level rules", text)

    def test_shared_terms_and_no_stale_term(self):
        for f in ('docs/sdem-overview.md', 'docs/relationship-rules-spec.md'):
            t = (ROOT / f).read_text(encoding='utf-8')
            t = '\n'.join(l for l in t.splitlines() if 'Until v0.6.2 it was called SDMM' not in l)  # the one documented historical mention
            for term in ('relationship rules model', 'relationship registry', 'architecture metamodel'):
                self.assertIn(term, t.lower(), f)
            for stale in ('mapping document', 'mapping set', 'mapping model', 'SDMM'):
                self.assertNotIn(stale, t, f)
        puml = (ROOT / 'docs/architecture-model-diagram.puml').read_text(encoding='utf-8')
        self.assertIn('relationship registry', puml.lower()); self.assertNotIn('mapping set', puml.lower())


class KnowledgeGraphDesignTests(unittest.TestCase):
    def test_example_counts_match_the_payment_initiation_estate(self):
        doc = (ROOT / 'docs/knowledge-graph-design.md').read_text(encoding='utf-8')
        P = ROOT / 'examples/payment-initiation'
        for lvl, f in (('A1', 'a1-business.json'), ('A2', 'a2-service-domain.json'), ('A3', 'a3-application.json'), ('A4', 'a4-technology.json')):
            d = json.loads((P / f).read_text(encoding='utf-8'))
            self.assertIn(f"| {lvl} local | {len(d['instances'])} | {len(d['relationships'])} within {lvl} |", doc)
        approved = [m for m in json.loads((P / 'mappings.json').read_text(encoding='utf-8'))['mappings'] if m['status'] == 'approved']
        self.assertIn(f"| {len(approved)} approved cross-architecture links |", doc)

    def test_linked_from_spec_and_overview(self):
        self.assertIn('knowledge-graph-design.md', (ROOT / 'docs/knowledge-graph-spec.md').read_text(encoding='utf-8'))
        self.assertIn('knowledge-graph-design.md', (ROOT / 'docs/sdem-overview.md').read_text(encoding='utf-8'))


class ServiceSpecTests(unittest.TestCase):
    def test_every_service_is_fully_specified_and_maps_to_a_component(self):
        from sdem.kgspec_services import SERVICES
        doc = (ROOT / 'docs/knowledge-graph-spec.md').read_text(encoding='utf-8')
        self.assertEqual([s['id'] for s in SERVICES], [f'SVC-0{i}' for i in range(1, 8)])
        for s in SERVICES:
            for k in ('purpose', 'interface', 'inputs', 'steps', 'valid', 'target', 'records', 'status'):
                self.assertTrue(s.get(k), f"{s['id']} lacks {k}")
            self.assertIn(f"| {s['component']} |", doc)
            self.assertIn(f"{s['id']} {s['name']} ({s['component']})", doc)


class PackagingTests(unittest.TestCase):
    def test_checkout_uses_repository_data_and_bundle_mapping_is_declared(self):
        from sdem.paths import DATA_ROOT
        self.assertEqual(DATA_ROOT, ROOT)
        toml = (ROOT / 'pyproject.toml').read_text(encoding='utf-8')
        self.assertIn('"sdem.data.schema" = "schema"', toml); self.assertIn('"sdem.data.metamodel" = "metamodel"', toml)


class EntityCatalogueDocTests(unittest.TestCase):
    def test_doc_is_current_and_every_entity_has_reasoning_and_confidence(self):
        from sdem.catalogue import render
        self.assertEqual((ROOT / 'docs/architecture-entity-design.md').read_text(encoding='utf-8'), render())
        import glob
        for f in glob.glob(str(ROOT / 'metamodel/a[1-4]-*.json')):
            for e in json.loads(Path(f).read_text(encoding='utf-8'))['entities']:
                self.assertTrue(e.get('reasoning'), e['type']); self.assertIn(e.get('confidence'), ('high', 'medium', 'low'), e['type'])


class AttributeDesignTests(unittest.TestCase):
    def test_doc_is_current_and_records_are_complete(self):
        from sdem.attributes import render, load
        self.assertEqual((ROOT / 'docs/architecture-attribute-design.md').read_text(encoding='utf-8'), render())
        rec = load(); ids = [a['id'] for a in rec['attributes']]
        self.assertEqual(len(ids), len(set(ids)))
        from sdem.metamodel import Metamodel
        mm = Metamodel.load()
        for a in rec['attributes']:
            self.assertTrue(mm.known(a['entity']), a['id'])
            for k in ('type', 'source', 'reasoning', 'verification', 'read_by', 'description'):
                self.assertTrue(a.get(k), f"{a['id']} lacks {k}")
            self.assertIn(a['confidence'], ('high', 'medium', 'low')); self.assertIn(a['status'], ('active', 'deprecated'))

    def test_every_join_key_is_an_attribute_and_every_used_attribute_is_recorded(self):
        import glob
        from sdem.attributes import load
        rec = {(a['entity'], a['name']) for a in load()['attributes']}
        conv = json.loads((ROOT / 'metamodel/export-conventions.json').read_text(encoding='utf-8'))['conventions']
        keys = {(e, k) for e, ks in conv.items() for k in ks} - {('A1.BusinessCapability', 'description')}  # a core field
        self.assertEqual(keys - rec, set())
        used = set()
        for f in glob.glob(str(ROOT / 'examples/*/a[1-4]-*.json')):
            for i in json.loads(Path(f).read_text(encoding='utf-8'))['instances']:
                used |= {(i['type'], k) for k in (i.get('attributes') or {})}
        self.assertEqual(used - rec, set())


class SourceReferenceCompletenessTests(unittest.TestCase):
    """Every item in every layer of the model names its source (found missing in four places on 2026-10-24)."""

    def _blank(self, v):
        return v in (None, '', '—', '-') or (isinstance(v, str) and not v.strip())

    def test_every_layer_has_a_source_reference(self):
        import glob
        for f in glob.glob(str(ROOT / 'metamodel/a[1-4]-*.json')):
            for e in json.loads(Path(f).read_text(encoding='utf-8'))['entities']:
                for k in ('standard', 'concept', 'uri', 'locator'):
                    self.assertFalse(self._blank(e['reference'].get(k)), f"entity {e['type']} reference.{k}")
        at = json.loads((ROOT / 'metamodel/entity-attributes.json').read_text(encoding='utf-8'))
        for a in at['attributes']:
            for k in ('standard', 'locator', 'uri'):
                self.assertFalse(self._blank(a['reference'].get(k)), f"attribute {a['id']} reference.{k}")
        for c in at['core_fields']:
            for k in ('standard', 'locator', 'uri'):
                self.assertFalse(self._blank((c.get('reference') or {}).get(k)), f"core field {c['name']} reference.{k}")
        lr = json.loads((ROOT / 'metamodel/level-relationships.json').read_text(encoding='utf-8'))
        for c in lr['constraints'] + lr['inheritance']:
            self.assertFalse(self._blank(c.get('reference_source')), f"within-level {c['id']}")
        for m in json.loads((ROOT / 'metamodel/relationship-rules.json').read_text(encoding='utf-8'))['mappings']:
            self.assertFalse(self._blank(m.get('source_reference')), f"rule {m['id']}")
        for x in json.loads((ROOT / 'schema/relationship-types.json').read_text(encoding='utf-8'))['relationships']:
            self.assertFalse(self._blank(x.get('source_reference')), f"relationship type {x['mapping_type_id']}")
        for m in json.loads((ROOT / 'metamodel/official-mappings.json').read_text(encoding='utf-8'))['mappings']:
            self.assertFalse(self._blank(m.get('sources') or m.get('verification_note')), f"official {m['id']}")


class ConfidenceRuleTests(unittest.TestCase):
    def test_every_record_agrees_with_the_single_confidence_rule(self):
        from sdem.confidence import apply
        self.assertEqual(apply(write=False), [])


class LogicalDataModelTests(unittest.TestCase):
    def test_doc_current_and_model_complete(self):
        from sdem.logical import render
        self.assertEqual((ROOT / 'docs/logical-data-model.md').read_text(encoding='utf-8'), render())
        from sdem.metamodel import Metamodel
        mm = Metamodel.load()
        lr = json.loads((ROOT / 'metamodel/level-relationships.json').read_text(encoding='utf-8'))
        for c in lr['constraints']:
            cd = c.get('cardinality'); self.assertTrue(cd, c['id'])
            for k in ('source_per_target', 'target_per_source'): self.assertIn(cd[k], ('0..1', '1..1', '0..*', '1..*'), c['id'])
        at = json.loads((ROOT / 'metamodel/entity-attributes.json').read_text(encoding='utf-8'))
        for a in at['attributes']:
            self.assertIn(a.get('kind'), ('reference', 'value', 'alias map', 'enumeration'), a['id'])
            for t in a.get('references', []): self.assertTrue(mm.known(t), f"{a['id']} → {t}")
        for t, e in mm.entities.items():
            self.assertIn('identifier', e, t)

    def test_examples_conform_with_no_errors(self):
        from sdem.logical import conformance, _j
        from sdem.metamodel import Metamodel, MM_DIR
        _, _, res = conformance(Metamodel.load(), _j(MM_DIR / 'entity-attributes.json')['attributes'])
        for lc in ('LC-04', 'LC-05', 'LC-06', 'LC-07', 'LC-08', 'LC-09', 'LC-10'):
            self.assertEqual(res[f'{lc} failed'], 0, lc)
        self.assertEqual(res['undefined'], 0)
