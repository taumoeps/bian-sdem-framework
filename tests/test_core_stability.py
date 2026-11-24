"""The stable core (the owner, 2026-11-21): the metamodel without extensions, then with BIAN and with security, then with each removed —
the core identical throughout (every layer, entity type, attribute, link type between layers and rule inside a layer, by stable id), what
an extension adds only its own, and the end equal to the start; the design's own data byte for byte. In both forms. Made-up data only.
The snapshot: scripts/core_stability.py."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import core_stability as C   # noqa: E402

ENV = {**os.environ, 'PYTHONPATH': str(ROOT), 'PYTHONIOENCODING': 'utf-8'}
ME = 'steven'
SECURITY = '\nsecurity ' in subprocess.run([sys.executable, '-m', 'sdem', 'extensions'], capture_output=True, text=True, encoding='utf-8', errors='replace', env=ENV, cwd=ROOT).stdout.replace('  security', '\nsecurity ')   # sdem-security installed beside SDEM


def sdem(*args):
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], capture_output=True, text=True, encoding='utf-8', env=ENV, cwd=ROOT)
    assert r.returncode == 0, f"sdem {' '.join(map(str, args))}: exit {r.returncode}\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}"
    return r.stdout


def snap(ws):   # a fresh process each time: nothing of one step's state reaches the next
    r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'core_stability.py'), str(ws)], capture_output=True, text=True, encoding='utf-8', env=ENV, cwd=ROOT)
    assert r.returncode == 0, r.stderr[-1500:]
    return json.loads(r.stdout)


class StableCore(unittest.TestCase):
    FORM = '0.20'

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp()); ws = cls.ws = cls.tmp / 'ws'
        src = ROOT / 'examples' / '0.20' / 'library-holds'   # a made-up design in the default four layers, with records in each
        sdem('new', '--workspace', ws, '--person', ME, '--core', '--from', src, '--form', cls.FORM)
        S = cls.S = {}
        S['core'] = snap(ws)
        sdem('profile', 'include', 'ext:bian', '--workspace', ws, '--person', ME, '--reason', 'BIAN on')
        S['+bian'] = snap(ws)
        if SECURITY:   # an installed extension: SDEM's own CI has BIAN (built in); the extensions' CI and a full install have security too
            sdem('profile', 'include', 'ext:security', '--workspace', ws, '--person', ME, '--reason', 'security on')
            sdem('profile', 'adopt', '--workspace', ws, '--person', ME, '--reason', 'the security layer')
            S['+bian+security'] = snap(ws)
            sdem('profile', 'exclude', 'ext:security', '--workspace', ws, '--person', ME, '--reason', 'security off')
            S['-security'] = snap(ws)
        sdem('profile', 'exclude', 'ext:bian', '--workspace', ws, '--person', ME, '--reason', 'BIAN off')
        S['-bian'] = snap(ws)
        cls.split = {k: C.split(v) for k, v in S.items()}

    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_the_core_is_identical_at_every_step(self):
        base = self.split['core']
        for step, sp in self.split.items():
            for kind in base:
                with self.subTest(step=step, part=kind):
                    self.assertEqual(sp[kind][0], base[kind][0])   # every core item, field for field
            with self.subTest(step=step, part='data'):
                self.assertEqual(self.S[step]['data'], self.S['core']['data'])   # the design's core layer files byte for byte, its links between them
            with self.subTest(step=step, part='core layers'):
                self.assertEqual([l for l in self.S[step]['layers'] if l in C.CORE], [l for l in self.S['core']['layers'] if l in C.CORE])   # their order

    def test_the_core_s_prose_differs_only_in_layer_numbers(self):   # descriptions name layers by the number shown now (DL-07) — nothing else in them moves
        import re
        num = lambda t: re.sub(r'\bA[1-9]\b|\bBIAN\b', 'A#', t)   # a layer's number — or, for a layer not in use, its name
        for step in self.S:   # never the mark of a layer not in use (it is named instead)
            with self.subTest(step=step, check='no (bian) mark'): self.assertNotIn('(bian)', ''.join(self.S[step]['attribute_text'].values()))
        core = {k for k in self.S['core']['attribute_text'] if C.is_core('attributes', k, {'entity': k.rsplit('.', 1)[0]})}
        for step in self.S:
            with self.subTest(step=step):
                self.assertEqual({k: num(self.S[step]['attribute_text'][k]) for k in core}, {k: num(self.S['core']['attribute_text'][k]) for k in core})

    def test_an_extension_adds_only_what_names_its_own_types(self):
        own = {'+bian': ('bian.',), '+bian+security': ('bian.', 'SEC.')}
        for step, prefixes in ((k, v) for k, v in own.items() if k in self.S):
            for kind in ('entities', 'attributes', 'link_types', 'rules'):
                added = set(self.split[step][kind][1]) - set(self.split['core'][kind][1])
                with self.subTest(step=step, part=kind):
                    self.assertTrue(added, f'{step} adds no {kind}')
                    for k in added:
                        item = self.S[step][kind][k]
                        named = [k] if kind == 'entities' else [item['entity']] if kind == 'attributes' else [item['source'], item['target']]
                        self.assertTrue(any(str(n).startswith(prefixes) for n in named), f'{step}: {kind} {k} names no type of its own: {named}')

    def test_removing_an_extension_leaves_the_metamodel_as_before_it(self):
        for kind in ('entities', 'attributes', 'attribute_text', 'link_types', 'rules', 'layers', 'common_attributes'):
            with self.subTest(part=kind):
                if SECURITY: self.assertEqual(self.S['-security'][kind], self.S['+bian'][kind])   # security off: as with BIAN alone
                self.assertEqual(self.S['-bian'][kind], self.S['core'][kind])        # BIAN off too: as the core alone — nothing left behind

    def test_the_core_alone_carries_nothing_of_an_extension(self):   # BX-04: BIAN's types, links, rules and attributes come with BIAN
        for kind in ('entities', 'attributes', 'link_types', 'rules'):
            with self.subTest(part=kind): self.assertEqual(self.split['core'][kind][1], {}, f'the core alone has extension {kind}')

    def test_the_layers_in_use_follow_the_extensions(self):
        self.assertEqual(self.S['core']['layers'], ['business', 'data', 'application', 'technology'] if self.FORM == '0.20' else ['business', 'application', 'technology'])
        self.assertIn('bian', self.S['+bian']['layers']); self.assertNotIn('bian', self.S['-bian']['layers'])


class StableCore019(StableCore):   # an unmigrated workspace: 0.19's three core layers, Data inside Application
    FORM = '0.19'


if __name__ == '__main__':
    unittest.main()
