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
from forms import lf  # noqa: E402 — a layer's file in either form

ENV = {**os.environ, 'PYTHONPATH': str(ROOT)}
GOLD_019 = {'SDEM_FORM': '0.19'}   # P1: the golden answers are SDEM 0.19's form — the capture's workspaces are made in it, whatever `sdem new` defaults to (DL-D9a)


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
    sdem('new', '--workspace', ws, '--person', 'bx.check', '--core', '--form', '0.20', '--from', src)   # SDEM's default stack: A1 Business, A2 Data, A3 Application, A4 Technology
    return ws


class Equivalence(unittest.TestCase):
    def test_with_bian_on_every_answer_is_the_same_as_0_19(self):   # BX-31
        out = Path(tempfile.mkdtemp())
        try:
            subprocess.run([sys.executable, str(ROOT / 'scripts' / 'golden' / 'capture.py'), str(out)], check=True, capture_output=True, env={**ENV, **GOLD_019}, cwd=ROOT)
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
        mm = Metamodel.load()   # DL-06, DL-D9: SDEM's default — A1 Business, A2 Data, A3 Application, A4 Technology; BIAN's types not in it
        self.assertFalse([t for t in mm.entities if t.startswith('(bian).') or t.endswith('.ServiceDomain')])
        self.assertIn('A3.ApplicationComponent', mm.entities); self.assertIn('A2.DataEntity', mm.entities)
        self.assertFalse([r for r in load_registry()['relationships'] if 'ServiceDomain' in r['source_type'] + r['target_type']])
        from sdem.rules_engine import _rules
        self.assertFalse([k for k, m in _rules().items() if '(bian).' in json.dumps(m) or 'ServiceDomain' in json.dumps(m)])
        from sdem.layers import codes
        self.assertEqual(codes(), ['A1', 'A2', 'A3', 'A4'])

    def test_the_core_stands_alone(self):   # BX-32
        g = self.tmp / 'graph'
        for args in (('check', '--workspace', self.core), ('status', '--workspace', self.core, '--json'), ('build', '--workspace', self.core, '--out', g),
                     ('trace', 'A1', '--graph', g), ('link', '--workspace', self.core, '--out', self.tmp / 'links'),
                     ('aid', '--workspace', self.core, '--person', 'bx.check', '--dry-run'), ('document', '--workspace', self.core, '--layer', 'A3'),
                     ('comply', '--workspace', self.core)):
            sdem(*args)
        props = json.loads((self.tmp / 'links' / 'proposals.json').read_text())
        self.assertNotIn('ServiceDomain', json.dumps(props))

    def test_bian_commands_and_types_say_how_to_switch_it_on(self):   # BX-13
        out = sdem('bian', 'add', 'Payment Order', '--workspace', self.core, '--person', 'bx.check', ok=(2,))
        self.assertIn('sdem profile include ext:bian', out)
        self.assertIn('A1, A2, A3, A4', sdem('types', 'A5', '--workspace', self.core, ok=(2,)))   # DL-D9: four layers, A1–A4

    def test_sdem_extensions_names_it_and_says_why(self):   # BX-01, BX-11
        d = json.loads(sdem('extensions', '--workspace', ROOT / 'examples' / 'payment-initiation-v3' / 'sdem', '--json'))
        b = next(x for x in d['items'] + d['built_in'] if x['name'] == 'bian')   # BX-15: the installed sdem-bian (built in only before 0.22)
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
        before = lf(ws, 'bian').read_text()
        out = sdem('profile', 'exclude', 'ext:bian', '--workspace', ws, '--person', 'bx.check', '--reason', 'try', ok=(1, 2))
        self.assertIn('nothing written', out); self.assertEqual(lf(ws, 'bian').read_text(), before)


class PackLinkTypes(unittest.TestCase):   # BX-50: a pack's link type that requires BIAN is left out where BIAN is off — said, not an error
    def test_left_out_off_kept_on(self):
        tmp = Path(tempfile.mkdtemp()); (tmp / 'bin').mkdir()
        try:
            import test_metamodel_extensions as T
            pack = json.loads(json.dumps(T.PACK))
            pack['link_types'].append({'source_type': 'SECT.S.SecurityControl', 'relationship': 'PROTECTS', 'archimate': 'association', 'target_type': 'A2.ServiceDomain',
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
            self.assertEqual([x['link_type'] for x in shown.get('left_out', [])], ['SECT.S.SecurityControl PROTECTS bian.ServiceDomain'])   # by its id: BIAN is off
            sdem('profile', 'include', 'ext:bian', '--workspace', core, '--person', 'bx.check', '--reason', 'r', env=env)
            shown = json.loads(sdem('profile', 'show', '--workspace', core, '--json', env=env))
            self.assertFalse(shown.get('left_out'))
            self.assertIn('A2.ServiceDomain', json.dumps(shown['link_types']))
        finally:
            P.deactivate(); shutil.rmtree(tmp, ignore_errors=True)



def fake_bian(folder, sdem_range='>=0.0', mark=None):
    """A stand-in for an installed sdem-bian (BP-01): its data folder written from SDEM's own (scripts/bian_package.py), optionally with a
    mark in one A2 type, one link type and one inference rule — to see SDEM read the package, not its built-in copy."""
    from sdem.parts import write_package_data
    write_package_data(folder / 'sdem_bian'); data = folder / 'sdem_bian' / 'data'
    if mark:
        for f, key in (('a2-service-domain.json', 'entities'), ('link-types.json', None), ('inference-rules.json', None)):
            d = json.loads((data / f).read_text()); rows = d[key] if key else d
            field = 'definition' if key else 'description'   # a type is shown by its definition (sdem types)
            rows[0][field] = f"{mark} {rows[0].get(field, '')}"
            (data / f).write_text(json.dumps(d))
    (folder / 'sdem_bian' / '__init__.py').write_text('')
    man = {'name': 'bian', 'command': 'sdem-bian', 'version': '9.9.9', 'kind': ['metamodel'], 'sdem': sdem_range, 'bian_data': str(data),
           'pack': str(ROOT / 'metamodel' / 'ext-bian-pack.json'), 'description': 'a test sdem-bian', 'commands': ['bian'], 'api': '>=0.1,<0.2'}
    body = (f'import sys, json\nif "--manifest" in sys.argv: print(json.dumps({man!r})); sys.exit(0)\n'   # else: its own sdem bian code, through sdem.api
            f'sys.path.insert(0, {str(folder)!r}); print("[the package\'s code]", file=sys.stderr)\n'
            'from sdem import api\nfrom sdem_bian.bian import main\nsys.exit(api.run("bian", main, sys.argv[1:]))\n')
    if os.name == 'nt':
        (folder / 'sdem-bian.py').write_text(body)
        (folder / 'sdem-bian.cmd').write_text(f'@"{sys.executable}" "%~dp0sdem-bian.py" %*\r\n')
    else:
        prog = folder / 'sdem-bian'; prog.write_text(f'#!{sys.executable}\n' + body); prog.chmod(0o755)
    return {**ENV, 'PATH': str(folder) + os.pathsep + os.environ.get('PATH', ''), 'SDEM_EXTENSIONS_PATH': str(folder)}   # only the stand-in, not an installed one


class Package(unittest.TestCase):   # step 2: BIAN in its own package (docs/design/sdem-bian-package-spec.md, BP-01…BP-11)
    def setUp(self): self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self): shutil.rmtree(self.tmp, ignore_errors=True)

    def test_with_the_package_every_answer_is_the_same_as_0_19(self):   # P1 with sdem-bian installed
        env = fake_bian(self.tmp)
        out = self.tmp / 'golden'
        subprocess.run([sys.executable, str(ROOT / 'scripts' / 'golden' / 'capture.py'), str(out)], check=True, capture_output=True, env={**env, **GOLD_019}, cwd=ROOT)
        gold = ROOT / 'tests' / 'golden' / '0.19'
        self.assertEqual([n.name for n in sorted(gold.glob('*.json')) if not filecmp.cmp(n, out / n.name, shallow=False)], [])

    def test_sdem_reads_the_packages_data(self):   # BP-02, BP-05: its types, link types, rules and catalogue — not the built-in copy
        env = fake_bian(self.tmp, mark='FROM-THE-PACKAGE')
        code = ("import json; from sdem import parts; from sdem.metamodel import Metamodel; from sdem.validate import load_registry; "
                "from sdem.rules_engine import _rules; print(json.dumps([parts.package()['version'], str(parts.catalogue_dir()), "
                "json.dumps(Metamodel.load().entities), json.dumps(load_registry()['relationships']), json.dumps(list(_rules().values()))]))")
        r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, env=env, cwd=ROOT)
        v, cat, ents, links, rules = json.loads(r.stdout)
        self.assertEqual(v, '9.9.9'); self.assertTrue(cat.startswith(str(self.tmp)))
        for what in (ents, links, rules): self.assertIn('FROM-THE-PACKAGE', what)
        self.assertIn('FROM-THE-PACKAGE', sdem('types', 'A2', '--json', env=env))   # and what a person sees
        self.assertIn('bian', sdem('profile', 'include', 'ext:bian', '--workspace', core_workspace(self.tmp), '--person', 'bx.check', '--reason', 'r', env=env))

    def test_sdem_bian_runs_the_packages_code(self):   # ST-22: the commands from the package, through sdem.api — the same answer
        env = fake_bian(self.tmp)
        r = subprocess.run([sys.executable, '-m', 'sdem', 'bian', 'search', 'payment', 'rail', '--json'], capture_output=True, text=True, env=env, cwd=ROOT)
        self.assertEqual(r.returncode, 0, r.stderr); self.assertIn("[the package's code]", r.stderr)
        plain = subprocess.run([sys.executable, '-m', 'sdem', 'bian', 'search', 'payment', 'rail', '--json'], capture_output=True, text=True, env=ENV, cwd=ROOT)
        self.assertNotIn("[the package's code]", plain.stderr); self.assertEqual(r.stdout, plain.stdout)

    def test_the_packages_code_uses_only_sdem_api(self):   # ST-21
        import ast
        from sdem.parts import package_code
        for f, src in package_code().items():
            used = {n.module for n in ast.walk(ast.parse(src)) if isinstance(n, ast.ImportFrom) and (n.module or '').startswith('sdem')}
            self.assertLessEqual(used, {'sdem.api'}, f)

    def test_a_package_that_does_not_support_this_sdem_is_not_used_and_said(self):   # BP-10, BP-05
        env = fake_bian(self.tmp, sdem_range='<0.1', mark='FROM-THE-PACKAGE')
        out = sdem('extensions', env=env)
        self.assertIn('used instead of the installed sdem-bian', out); self.assertIn('supports SDEM <0.1', out)
        self.assertNotIn('FROM-THE-PACKAGE', sdem('types', 'A2', '--json', env=env))

    def test_without_the_package_the_built_in_copy(self):   # BP-10
        from sdem import parts
        self.assertIsNone(parts.package()) if not shutil.which('sdem-bian') else None
        self.assertEqual(parts.catalogue_dir(), ROOT / 'bian') if not shutil.which('sdem-bian') else None


if __name__ == '__main__':
    unittest.main()
