"""Release gate: documents written against earlier releases validate unchanged under the current metamodel.

Draft warnings on proposed records ("must be supplied before approval") are expected and ignored, as --strict does."""
import copy, json, re, unittest
from pathlib import Path
from sdmm.validate import validate

ROOT = Path(__file__).resolve().parents[1]


def legacy_form(doc):
    """Rewrite a current document the way a v0.2.1 author would have written it."""
    d = copy.deepcopy(doc)
    d.pop('metamodel_version', None); d.pop('registry_version', None)
    down = lambda t: re.sub(r'^A([1-4])\.', lambda m: f'L{int(m.group(1))-1}.', t)
    d['mappings'] = [m for m in d['mappings'] if m['relationship'] != 'DEPLOYED_AS']  # did not exist in v0.2
    for m in d['mappings']:
        for end in ('source', 'target'):
            m[end]['type'] = down(m[end]['type'])
    return d


class V02CompatibilityTests(unittest.TestCase):
    def test_shipped_examples_in_legacy_form_validate_with_no_issues_or_warnings(self):
        for path in sorted((ROOT / 'examples').glob('*/mappings.json')):
            doc = legacy_form(json.loads(path.read_text()))
            warnings = []
            self.assertEqual(validate(doc, warnings=warnings), [], path)
            self.assertEqual([w for w in warnings if 'must be supplied before approval' not in w], [], path)

    def test_abstract_compatibility_supertype_is_a_legal_endpoint(self):
        doc = json.loads((ROOT / 'examples/card-fraud-alerts/mappings.json').read_text())
        warnings = []
        self.assertEqual(validate(doc, warnings=warnings), [])
        self.assertEqual([w for w in warnings if 'must be supplied before approval' not in w], [])


if __name__ == '__main__':
    unittest.main()
