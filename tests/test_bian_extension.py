"""BIAN as a horizontal extension, step 1 of 0.20 (docs/design/sdem-bian-extension-spec.md, BX-01…BX-51): with BIAN on, SDEM answers as
0.19 did (the golden outputs); with it off, the core — A1, A3, A4 — stands alone. Synthetic data only."""
import filecmp, json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
from sdem import parts, profile as P  # noqa: E402
from sdem.metamodel import Metamodel  # noqa: E402
from sdem.validate import load_registry  # noqa: E402
from test_metamodel_extensions import fake_extension  # noqa: E402

ENV = {**os.environ, 'PYTHONPATH': str(ROOT)}


def sdem(*args, ok=(0,), env=None):
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], capture_output=True, text=True, env=env or ENV, cwd=ROOT)
    assert r.returncode in ok, f"sdem {' '.join(map(str, args))}: exit {r.returncode}\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}"
    return r.stdout + r.stderr


def core_workspace(tmp, name='core'):
    """A made-up non-banking workspace with only A1, A3 and A4: the card-fraud example without its A2 and the links that touch it."""
    src = tmp / f'{name}-src'; src.mkdir()
    ex = ROOT / 'examples' / 'card-fraud-alerts'
    for f in ('a1-business.json', 'a3-application.json', 'a4-technology.json'): shutil.copy(ex / f, src / f)
    m = json.loads((ex / 'mappings.json').read_text())
    m['mappings'] = [x for x in m['mappings'] if not x['source']['type'].startswith('A2.') and not x['target']['type'].startswith('A2.')]
    (src / 'mappings.json').write_text(json.dumps(m))
    ws = tmp / name
    sdem('new', '--workspace', ws, '--person', 'bx.check', '--core', '--from', src)
    return ws


class Equivalence(unittest.TestCase):
    def test_with_bian_on_every_answer_is_the_same_as_0_19(self):   # BX-31
        out = Path(tempfile.mkdtemp())
        try:
            subprocess.run([sys.executable, str(ROOT / 'scripts' / 'golden' / 'capture.py'), str(out)], check=True, capture_output=True, env=ENV, cwd=ROOT)
            gold = ROOT / 'tests' / 'golden' / '0.19'
            names = sorted(p.name for p in gold.glob('*.json'))
            self.assertEqual(names, sorted(p.name for p in out.glob('*.json')))
            differ = [n for n in names if not filecmp.cmp(gold / n, out / n, shallow=False)]
            self.assertEqual(differ, [], 'answers that changed since 0.19 — explain and approve, or fix (BX-31)')
        finally:
            shutil.rmtree(out, ignore_errors=True)


class OnAndOff(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.tmp = Path(tempfile.mkdtemp()); cls.core = core_workspace(cls.tmp)

    @classmethod
    def tearDownClass(cls): P.deactivate(); shutil.rmtree(cls.tmp, ignore_errors=True)

    def tearDown(self): P.deactivate()

    def test_when_bian_is_on(self):   # BX-10, BX-11, BX-12, BX-13
        P.deactivate(); self.assertTrue(parts.bian_on())   # no workspace
        P.activate_from(ROOT / 'examples' / 'payment-initiation-v3' / 'sdem'); self.assertTrue(parts.bian_on()); self.assertIn('BX-11', parts.why())
        nb = Path(tempfile.mkdtemp()) / 'nb'; sdem('new', '--workspace', nb, '--person', 'bx.check', '--no-bian')   # 0.19's --no-bian: still a BIAN design, A2 empty
        P.activate_from(nb); self.assertTrue(parts.bian_on())
        P.activate_from(self.core); self.assertFalse(parts.bian_on())

    def test_off_the_metamodel_has_no_a2(self):   # BX-02, BX-04
        P.activate_from(self.core)
        mm = Metamodel.load()
        self.assertFalse([t for t in mm.entities if t.startswith('A2.')])
        self.assertFalse([r for r in load_registry()['relationships'] if 'A2.' in r['source_type'] + r['target_type']])
        from sdem.rules_engine import _rules
        self.assertFalse([k for k, m in _rules().items() if 'A2.' in json.dumps(m)])
        from sdem.layers import codes
        self.assertEqual(codes(), ['A1', 'A3', 'A4'])

    def test_the_core_stands_alone(self):   # BX-32
        g = self.tmp / 'graph'
        for args in (('check', '--workspace', self.core), ('status', '--workspace', self.core, '--json'), ('build', '--workspace', self.core, '--out', g),
                     ('trace', 'A1', '--graph', g), ('link', '--workspace', self.core, '--out', self.tmp / 'links'),
                     ('aid', '--workspace', self.core, '--person', 'bx.check', '--dry-run'), ('document', '--workspace', self.core, '--layer', 'A3'),
                     ('comply', '--workspace', self.core)):
            sdem(*args)
        props = json.loads((self.tmp / 'links' / 'proposals.json').read_text())
        self.assertNotIn('A2.', json.dumps(props))

    def test_bian_commands_and_types_say_how_to_switch_it_on(self):   # BX-13
        out = sdem('bian', 'add', 'Payment Order', '--workspace', self.core, '--person', 'bx.check', ok=(2,))
        self.assertIn('sdem profile include ext:bian', out)
        self.assertIn('A1, A3, A4', sdem('types', 'A2', '--workspace', self.core, ok=(2,)))

    def test_sdem_extensions_names_it_and_says_why(self):   # BX-01, BX-11
        d = json.loads(sdem('extensions', '--workspace', ROOT / 'examples' / 'payment-initiation-v3' / 'sdem', '--json'))
        b = next(x for x in d['built_in'] if x['name'] == 'bian')
        self.assertTrue(b['on']); self.assertIn('sdem profile include ext:bian', b['make_explicit'])

    def test_switched_on_and_off_by_a_person(self):   # BX-10, BX-14
        ws = self.tmp / 'onoff'; shutil.copytree(self.core, ws)
        sdem('profile', 'include', 'ext:bian', '--workspace', ws, '--person', 'bx.check', '--reason', 'a banking design after all')
        P.activate_from(ws); self.assertTrue(parts.bian_on()); P.deactivate()
        sdem('profile', 'exclude', 'ext:bian', '--workspace', ws, '--person', 'bx.check', '--reason', 'not banking')
        P.activate_from(ws); self.assertFalse(parts.bian_on())

    def test_switching_off_a_design_that_needs_bian_is_refused(self):   # BX-14: nothing written, the reason named
        ws = self.tmp / 'pi'; sdem('new', '--workspace', ws, '--person', 'bx.check', '--example', 'payment-initiation')
        sdem('profile', 'include', 'ext:bian', '--workspace', ws, '--person', 'bx.check', '--reason', 'explicit')
        before = (ws / 'a2-service-domain.json').read_text()
        out = sdem('profile', 'exclude', 'ext:bian', '--workspace', ws, '--person', 'bx.check', '--reason', 'try', ok=(1, 2))
        self.assertIn('nothing written', out); self.assertEqual((ws / 'a2-service-domain.json').read_text(), before)


class PackLinkTypes(unittest.TestCase):   # BX-50: a pack's link type that requires BIAN is left out where BIAN is off — said, not an error
    def test_left_out_off_kept_on(self):
        tmp = Path(tempfile.mkdtemp()); (tmp / 'bin').mkdir()
        try:
            import test_metamodel_extensions as T
            pack = json.loads(json.dumps(T.PACK))
            pack['link_types'].append({'source_type': 'SECT.S.SecurityControl', 'relationship': 'PROTECTS', 'target_type': 'A2.ServiceDomain',
                                       'required_evidence': ['design_document'], 'requires': 'ext:bian'})
            orig = T.PACK; T.PACK = pack
            try: fake_extension(tmp / 'bin', 'sectest')
            finally: T.PACK = orig
            env = {**ENV, 'PATH': str(tmp / 'bin') + os.pathsep + os.environ.get('PATH', '')}
            core = core_workspace(tmp)
            sdem('profile', 'include', 'ext:sectest', '--workspace', core, '--person', 'bx.check', '--reason', 'r', env=env)
            sdem('profile', 'adopt', '--workspace', core, '--person', 'bx.check', '--reason', 'r', env=env)
            self.assertIn('"ok": true', sdem('check', '--workspace', core, '--json', env=env))
            shown = json.loads(sdem('profile', 'show', '--workspace', core, '--json', env=env))
            self.assertEqual([x['link_type'] for x in shown.get('left_out', [])], ['SECT.S.SecurityControl PROTECTS A2.ServiceDomain'])
            sdem('profile', 'include', 'ext:bian', '--workspace', core, '--person', 'bx.check', '--reason', 'r', env=env)
            shown = json.loads(sdem('profile', 'show', '--workspace', core, '--json', env=env))
            self.assertFalse(shown.get('left_out'))
            self.assertIn('A2.ServiceDomain', json.dumps(shown['link_types']))
        finally:
            P.deactivate(); shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
