"""Stable identity for layers and types (docs/design/sdem-stable-identity-spec.md, ST-01…ST-05)."""
import json, subprocess, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem import identity  # noqa: E402
from sdem.identity import T, IdentityError, layer, layer_id, type_id  # noqa: E402


class IdentityTests(unittest.TestCase):
    def test_the_table_holds_every_type_of_the_metamodel_and_nothing_else(self):   # ST-04
        names = {e['type'] for f in sorted((ROOT / 'metamodel').glob('a[1-4]-*.json')) for e in json.loads(f.read_text())['entities']}
        self.assertEqual({x['name_0_19'] for x in identity.table()['types']}, names)
        ids = [x['id'] for x in identity.table()['types']]
        self.assertEqual(len(ids), len(set(ids)))

    def test_ids_never_carry_a_position(self):   # ST-01, ST-02
        for x in identity.table()['types']:
            self.assertRegex(x['id'], r'^(business|bian|application|technology)\.[A-Z][A-Za-z]+$')
        self.assertEqual([l['id'] for l in identity.table()['layers']], ['business', 'bian', 'application', 'technology'])

    def test_in_step_3_every_name_is_0_19s(self):   # ST-03 with 0.19's stack: P1
        for x in identity.table()['types']: self.assertEqual(T(x['id']), x['name_0_19'])
        self.assertEqual([layer(i) for i in ('business', 'bian', 'application', 'technology')], ['A1', 'A2', 'A3', 'A4'])

    def test_old_names_and_ids_both_read(self):   # ST-05
        self.assertEqual(type_id('A3.ApplicationComponent'), 'application.ApplicationComponent')
        self.assertEqual(type_id('application.ApplicationComponent'), 'application.ApplicationComponent')
        self.assertEqual(layer_id('A2'), 'bian'); self.assertEqual(layer_id('technology'), 'technology')
        self.assertIsNone(type_id('SEC.S.SecurityControl')); self.assertIsNone(layer_id('X9'))

    def test_an_unknown_id_is_refused_never_guessed(self):   # ST-04
        with self.assertRaises(IdentityError): T('application.Nothing')
        with self.assertRaises(IdentityError): layer('A3')

    def test_sdem_types_ids_and_a_type_by_its_id(self):
        r = subprocess.run([sys.executable, '-m', 'sdem', 'types', '--ids', '--json'], capture_output=True, text=True, cwd=ROOT)
        d = json.loads(r.stdout)
        self.assertIn({'id': 'bian.ServiceDomain', 'name': 'A2.ServiceDomain'}, d['types'])
        r = subprocess.run([sys.executable, '-m', 'sdem', 'types', 'technology.Node', '--json'], capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(json.loads(r.stdout)['type'], 'A4.Node')


if __name__ == '__main__':
    unittest.main()
