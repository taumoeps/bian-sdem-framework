"""MID-07 (docs/design/metamodel-integrity-design.md): every link is ArchiMate's kind; how a trace walks it is SDEM's rule, labelled so;
every type says where it comes from. Checked over the metamodel itself — every type, every link inside a layer, every link between
layers the examples use, every declared trace rule."""
import json, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem.metamodel import Metamodel  # noqa: E402
from sdem import notation  # noqa: E402

ARCHIMATE_KINDS = {'composition', 'aggregation', 'assignment', 'realization', 'serving', 'access', 'influence', 'triggering', 'flow',
                   'specialization', 'association'}   # ArchiMate 3.2 §5
NOTATION = json.loads((ROOT / 'metamodel' / 'archimate-notation.json').read_text(encoding='utf-8'))
RELS = json.loads((ROOT / 'metamodel' / 'level-relationships.json').read_text(encoding='utf-8'))
MM = Metamodel.base()
LEVEL_FILES = ('a1-business.json', 'a2-service-domain.json', 'a3-application.json', 'a4-technology.json')


class ArchiMateLabels(unittest.TestCase):
    def test_every_type_says_where_it_comes_from_and_is_an_archimate_element(self):
        for f in LEVEL_FILES:
            for e in json.loads((ROOT / 'metamodel' / f).read_text(encoding='utf-8'))['entities']:
                ref = e.get('reference') or {}
                self.assertTrue(ref.get('standard') and e.get('definition_source'), f"{e['type']}: no source")
                self.assertTrue((notation.for_type(MM, e['type']) or {}).get('element'), f"{e['type']}: no ArchiMate element, own or inherited")

    def test_every_link_inside_a_layer_is_an_archimate_kind_with_its_source(self):
        for k in RELS['kinds']:
            self.assertIn(k['kind'], ARCHIMATE_KINDS); self.assertTrue(k['source'].startswith('ArchiMate 3.2'), k)
        for c in RELS['constraints']:
            self.assertIn(c['kind'], ARCHIMATE_KINDS, c.get('id'))

    def test_every_link_between_layers_is_an_archimate_kind(self):
        used = {m['relationship'] for f in (ROOT / 'examples').rglob('mappings.json')
                for m in json.loads(f.read_text(encoding='utf-8')).get('mappings', [])}
        self.assertTrue(used)
        for rel in used:
            self.assertIn(notation.for_relationship(rel), ARCHIMATE_KINDS, f'{rel}: no ArchiMate kind')

    def test_sdems_own_notation_check_passes(self):
        self.assertEqual(notation.check(MM), [])

    def test_every_trace_rule_is_labelled_as_sdems(self):   # FT-…: SDEM's rule over ArchiMate's link, with its reason
        for r in Metamodel.base().trace['rules']:
            self.assertTrue(r['id'].startswith('FT-') and r.get('reason'), r)
            self.assertIn(r.get('kind', 'association'), ARCHIMATE_KINDS)


if __name__ == '__main__':
    unittest.main()


class PacksSayTheirKinds(unittest.TestCase):   # MID-07 for an extension's own links: each link type says its ArchiMate kind ("archimate")
    def test_every_shipped_profile_link_type_has_its_kind(self):
        from sdem import profile as P
        for f in list((ROOT / 'examples' / 'profiles').glob('*.json')) + list((ROOT / 'standards').glob('*.json')):
            d = json.loads(f.read_text(encoding='utf-8'))
            for x in (d.get('link_types') or []) if isinstance(d, dict) else []:
                self.assertIn(x.get('archimate'), ARCHIMATE_KINDS, f'{f.name}: {x.get("relationship")}')
        for x in P.example_profiles()['strategy-and-sites-team.json']['link_types'] if hasattr(P, 'example_profiles') else []:
            self.assertIn(x.get('archimate'), ARCHIMATE_KINDS)

    def test_a_link_type_without_its_kind_is_refused(self):
        import tempfile
        from sdem import profile as P
        t = Path(tempfile.mkdtemp())
        (t / 'p.json').write_text(json.dumps({'format': 'sdem-profile/1', 'name': 'x', 'version': 1,
            'layers': [{'code': 'X', 'name': 'X', 'position': 'across', 'file': 'x.json'}], 'types': [{'type': 'XX.X.Thing', 'description': 'made-up', 'archimate': 'Assessment'}],
            'link_types': [{'source_type': 'XX.X.Thing', 'relationship': 'TOUCHES', 'target_type': 'A3.DataEntity', 'required_evidence': ['memo']}]}))
        issues = P.check(P.resolve(t / 'p.json'), MM)
        self.assertTrue(any('no ArchiMate relationship' in i for i in issues), issues)
