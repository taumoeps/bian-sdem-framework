"""The ArchiMate notation and the Architecture viewpoint as data (docs/design/sdem-architecture-viewpoint-spec.md §10, ARV-12…ARV-22)."""
import json, os, subprocess, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem import notation as N, viewpoint as V, profile as P  # noqa: E402
from sdem.metamodel import Metamodel  # noqa: E402
from sdem.validate import load_registry  # noqa: E402


class Notation(unittest.TestCase):
    def test_every_type_link_and_relationship_has_a_notation(self):   # ARV-12, ARV-14, ARV-16
        self.assertEqual(N.check(Metamodel.base(), load_registry()), [])

    def test_notation_is_not_source(self):   # ARV-13: a BIAN type is drawn as an ArchiMate element, with the reason
        n = N.for_type(Metamodel.base(), 'A2.ServiceDomain')
        self.assertEqual((n['element'], n['layer'], n['from']), ('Business Function', 'business', 'SDEM')); self.assertIn('BIAN', n['why'])

    def test_a_subtype_inherits_and_a_profile_type_names_its_own(self):   # ARV-15
        mm = Metamodel.base()
        self.assertEqual(N.for_type(mm, 'A1.BusinessActivity')['from'], 'inherited from A1.BusinessProcess')
        doc = {'format': 'sdem-profile/1', 'name': 'made-up', 'version': 1, 'types': [
            {'type': 'NET.A4.Firewall', 'extends': 'A4.Node', 'definition': 'a made-up firewall'},
            {'type': 'NET.A4.Rule', 'extends': 'A4.Artifact', 'definition': 'a made-up rule', 'archimate': 'Artifact'}]}
        import tempfile
        f = Path(tempfile.mkdtemp()) / 'p.json'; f.write_text(json.dumps(doc))
        mm2 = P.apply(mm, P.resolve(f))
        self.assertEqual((N.for_type(mm2, 'NET.A4.Firewall')['element'], N.for_type(mm2, 'NET.A4.Firewall')['from']), ('Node', 'inherited from A4.Node'))
        self.assertEqual(N.for_type(mm2, 'NET.A4.Rule')['from'], 'profile or extension')

    def test_sdem_types_says_it(self):   # ARV-16
        r = subprocess.run([sys.executable, '-m', 'sdem', 'types', 'A2', '--json'], capture_output=True, text=True, cwd=ROOT,
                           env={**os.environ, 'PYTHONPATH': str(ROOT)})
        sd = next(t for t in json.loads(r.stdout)['types'] if t['type'] == 'A2.ServiceDomain')
        self.assertEqual(sd['archimate']['element'], 'Business Function')


class Viewpoint(unittest.TestCase):
    def test_the_architecture_viewpoint_agrees_with_the_metamodel(self):   # ARV-18, ARV-21, ARV-05
        self.assertIn('architecture', V.names())
        self.assertEqual(V.check(Metamodel.base(), V.load('architecture')), [])
        self.assertEqual([p['code'] for p in V.load('architecture')['plates']], ['A1', 'A2', 'A3-1', 'A3-2', 'A4'])

    def test_a_type_neither_drawn_nor_left_out_is_found(self):   # ARV-05: never silently dropped
        d = V.load('architecture'); d['plates'][1]['left_out'] = []
        self.assertTrue(any('A2.ServiceOperation' in x for x in V.check(Metamodel.base(), d)))

    def test_an_unknown_layout_or_type_is_refused(self):
        d = json.loads(json.dumps(V.load('architecture'))); d['plates'][0]['layout'] = 'freehand'; d['plates'][0]['shapes'].append('A1.Nope')
        probs = V.check(Metamodel.base(), d)
        self.assertTrue(any('freehand' in x for x in probs) and any('A1.Nope' in x for x in probs))

    def test_the_command(self):
        r = subprocess.run([sys.executable, '-m', 'sdem', 'viewpoint', 'check', '--json'], capture_output=True, text=True, cwd=ROOT, env={**os.environ, 'PYTHONPATH': str(ROOT)})
        d = json.loads(r.stdout); self.assertTrue(d['ok']); self.assertEqual(d['problems'], [])


if __name__ == '__main__':
    unittest.main()
