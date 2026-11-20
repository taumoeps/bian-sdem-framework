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
            self.assertRegex(x['id'], r'^(business|bian|data|application|technology)\.[A-Z][A-Za-z]+$')
        self.assertEqual([l['id'] for l in identity.table()['layers']], ['business', 'bian', 'data', 'application', 'technology'])

    def test_in_step_3_every_name_is_0_19s(self):   # ST-03 with 0.19's stack: P1
        for x in identity.table()['types']: self.assertEqual(T(x['id']), x['name_0_19'])
        self.assertEqual([layer(i) for i in ('business', 'bian', 'application', 'technology')], ['A1', 'A2', 'A3', 'A4'])
        self.assertEqual(layer('data'), 'A3')   # an unmigrated workspace: Data's types in Application, as in 0.19 (DL-12)

    def test_old_names_and_ids_both_read(self):   # ST-05
        self.assertEqual(type_id('A3.ApplicationComponent'), 'application.ApplicationComponent')
        self.assertEqual(type_id('application.DataEntity'), 'data.DataEntity')   # DL-02: the id it had before the Data layer
        self.assertEqual(type_id('A3.DataEntity'), 'data.DataEntity')
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



def _strings():
    """Every string in SDEM's code that is not a docstring: (module, line, token)."""
    import io, tokenize
    for p in sorted((ROOT / 'sdem').glob('*.py')):
        if p.name in ('identity.py', 'paths.py'): continue
        for t in tokenize.generate_tokens(io.StringIO(p.read_text(encoding='utf-8')).readline):
            if t.type in (tokenize.STRING, getattr(tokenize, 'FSTRING_MIDDLE', -1)) and not t.string.startswith(('"""', "'''")):
                yield p.name, t.start[0], t.string


class NamesInCode(unittest.TestCase):   # step 3b: SDEM's code names layers and types by id (spec §7)
    def test_no_type_name_layer_code_or_prefix_is_written_in_the_code(self):
        import re
        names = {x['name_0_19'] for x in identity.table()['types']} | {l['code_0_19'] for l in identity.table()['layers'] if l.get('code_0_19')}
        bad = [f'{m}:{n} {s}' for m, n, s in _strings() if s[:1] in '\'"' and (s[1:-1] in names or re.fullmatch(r'A[1-4]\.', s[1:-1]))]
        self.assertEqual(bad, [], "write _T('<type id>') or _L('<layer id>') (sdem/identity.py) instead")

    def test_no_f_string_nests_its_own_quote(self):
        """Python 3.12 allows f'{_L('bian')}'; 3.10 and 3.11, which SDEM supports, do not (a syntax error) — the CI failure on 7587442."""
        import io, tokenize
        if not hasattr(tokenize, 'FSTRING_START'): self.skipTest('Python < 3.12 would not even compile such a module')
        bad = []
        for p in sorted((ROOT / 'sdem').rglob('*.py')):
            stack = []
            for t in tokenize.generate_tokens(io.StringIO(p.read_text(encoding='utf-8')).readline):
                if t.type == tokenize.FSTRING_START: stack.append(t.string.lstrip('rRfFbB'))
                elif t.type == tokenize.FSTRING_END: stack.pop()
                elif t.type in (tokenize.STRING, tokenize.FSTRING_START) and stack and len(stack[-1]) == 1 and t.string.lstrip('rRfFbB').startswith(stack[-1]):
                    bad.append(f'{p.name}:{t.start[0]}')
        self.assertEqual(bad, [], 'use the other quote inside an f-string')

    def test_labels_and_messages_that_carry_a_code_only_go_down(self):
        """The ratchet: text that carries an A-number is computed (DL-07, step 4a: 266 labels and messages). What is left names no
        layer of the stack: record and dataset ids (HIS-A3-…, …-A2), an organisation's own type names (BANK.A3.…), the raw page
        templates (their labels come from data) and history. A module may lower its count (then lower it here), never raise it."""
        import collections, re
        pat = re.compile(r'\bA[1-4](\.[A-Za-z]|\b)')
        now = collections.Counter(m for m, _, s in _strings() if pat.search(s))
        base = json.loads((ROOT / 'tests' / 'data' / 'identity-text-baseline.json').read_text())
        self.assertEqual({m: (c, base.get(m, 0)) for m, c in now.items() if c > base.get(m, 0)}, {}, 'new text with an A-number: compute it (identity.layer) instead')


if __name__ == '__main__':
    unittest.main()
