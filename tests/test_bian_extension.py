"""BIAN as a horizontal extension, step 1 of 0.20 (docs/design/sdem-bian-extension-spec.md, BX-01…BX-51): with BIAN on, SDEM answers as
0.19 did (the golden outputs); with it off, the core — A1, A3, A4 — stands alone. Synthetic data only."""
import filecmp, json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys as _s2, pathlib as _pl2; _s2.path.insert(0, str(_pl2.Path(__file__).resolve().parent)); from needs import EXAMPLES  # noqa: E402 — SDEM's examples and sdem-bian's (R-D6)
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



def _same(a, b):
    """Byte for byte — except, in a build, the metamodel version and the inputs' hashes: the examples moved to metamodel 0.20.0 (R-D3)."""
    if filecmp.cmp(a, b, shallow=False): return True
    if not a.name.endswith('__build.json'): return False
    strip = lambda x: {k: strip(v) for k, v in x.items() if k not in ('sha256', 'metamodel_version')} if isinstance(x, dict) else [strip(v) for v in x] if isinstance(x, list) else x
    return strip(json.loads(a.read_text(encoding='utf-8'))) == strip(json.loads(b.read_text(encoding='utf-8')))

def core_workspace(tmp, name='core'):
    """A made-up non-banking workspace with only A1, A3 and A4: the card-fraud example without its A2 and the links that touch it."""
    src = tmp / f'{name}-src'; src.mkdir()
    ex = EXAMPLES / 'card-fraud-alerts'
    for f in ('a1-business.json', 'a3-application.json', 'a4-technology.json'): shutil.copy(ex / f, src / f)
    m = json.loads((ex / 'mappings.json').read_text())
    m['mappings'] = [x for x in m['mappings'] if not x['source']['type'].startswith('A2.') and not x['target']['type'].startswith('A2.')]
    (src / 'mappings.json').write_text(json.dumps(m))
    ws = tmp / name
    sdem('new', '--workspace', ws, '--person', 'bx.check', '--core', '--form', '0.20', '--from', src)   # SDEM's default stack: A1 Business, A2 Data, A3 Application, A4 Technology
    return ws


import sys as _s, pathlib as _pl; _s.path.insert(0, str(_pl.Path(__file__).resolve().parent)); from needs import bian as _needs_bian  # noqa: E402 — BX-15: tests that need sdem-bian


@_needs_bian
class Equivalence(unittest.TestCase):
    def test_with_bian_on_every_answer_is_the_same_as_0_19(self):   # BX-31
        out = Path(tempfile.mkdtemp())
        try:
            subprocess.run([sys.executable, str(ROOT / 'scripts' / 'golden' / 'capture.py'), str(out)], check=True, capture_output=True, env={**ENV, **GOLD_019}, cwd=ROOT)
            gold = ROOT / 'tests' / 'golden' / '0.19'
            names = sorted(p.name for p in gold.glob('*.json'))
            self.assertEqual(names, sorted(p.name for p in out.glob('*.json')))
            differ = [n for n in names if not _same(gold / n, out / n)]
            self.assertEqual(differ, [], 'answers that changed since 0.19 — explain and approve, or fix (BX-31)')
        finally:
            shutil.rmtree(out, ignore_errors=True)


@_needs_bian
class OnAndOff(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.tmp = Path(tempfile.mkdtemp()); cls.core = core_workspace(cls.tmp)

    @classmethod
    def tearDownClass(cls): P.deactivate(); shutil.rmtree(cls.tmp, ignore_errors=True)

    def tearDown(self): P.deactivate()

    def test_when_bian_is_on(self):   # BX-10, BX-11, BX-12, BX-13
        P.deactivate(); self.assertTrue(parts.bian_on())   # no workspace
        P.activate_from(EXAMPLES / 'payment-initiation-v3' / 'sdem'); self.assertTrue(parts.bian_on()); self.assertIn('BX-11', parts.why())
        nb = Path(tempfile.mkdtemp()) / 'nb'; sdem('new', '--workspace', nb, '--person', 'bx.check', '--no-bian')   # 0.22 (BX-15): no BIAN layer, no ext:bian — a core design
        P.activate_from(nb); self.assertFalse(parts.bian_on())
        wb = Path(tempfile.mkdtemp()) / 'wb'; sdem('new', '--workspace', wb, '--person', 'bx.check', '--with', 'bian')   # BIAN's layer, empty: a BIAN design
        P.activate_from(wb); self.assertTrue(parts.bian_on())
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
        d = json.loads(sdem('extensions', '--workspace', EXAMPLES / 'payment-initiation-v3' / 'sdem', '--json'))
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


@_needs_bian
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



def _installed_package():
    """The installed sdem-bian's package folder (sdem_bian/), from its manifest — or None."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from bare_python import bian_dirs
    prog = shutil.which('sdem-bian', path=os.pathsep.join(bian_dirs())) if bian_dirs() else None
    if not prog: return None
    m = json.loads(subprocess.run([prog, '--manifest'], capture_output=True, text=True, encoding='utf-8').stdout)
    return Path(m['bian_data']).parent


def fake_bian(folder, sdem_range='>=0.0', mark=None):
    """A stand-in for an installed sdem-bian (BP-01): a copy of the installed one's package (its data and code — since 0.22 BIAN's only
    source), optionally with a mark in one A2 type, one link type and one inference rule — to see SDEM read this package's data."""
    if (folder / 'sdem_bian').exists(): shutil.rmtree(folder / 'sdem_bian')
    shutil.copytree(_installed_package(), folder / 'sdem_bian', ignore=shutil.ignore_patterns('__pycache__')); data = folder / 'sdem_bian' / 'data'
    if mark:
        for f, key in (('a2-service-domain.json', 'entities'), ('link-types.json', None), ('inference-rules.json', None)):
            d = json.loads((data / f).read_text()); rows = d[key] if key else d
            field = 'definition' if key else 'description'   # a type is shown by its definition (sdem types)
            rows[0][field] = f"{mark} {rows[0].get(field, '')}"
            (data / f).write_text(json.dumps(d))
    man = {'name': 'bian', 'command': 'sdem-bian', 'version': '9.9.9', 'kind': ['metamodel'], 'sdem': sdem_range, 'bian_data': str(data),
           'pack': str(folder / 'sdem_bian' / 'pack.json'), 'examples': str(folder / 'sdem_bian' / 'examples'), 'description': 'a test sdem-bian', 'commands': ['bian'], 'infers': ['link', 'aid-phases'], 'api': '>=0.1,<0.2'}
    body = (f'import sys, json\nif "--manifest" in sys.argv: print(json.dumps({man!r})); sys.exit(0)\n'   # else: its own sdem bian code, through sdem.api
            f'sys.path.insert(0, {str(folder)!r})\n'
            'if sys.argv[1:2] == ["infer"]:\n    from sdem_bian.infer import main as infer\n    sys.exit(infer(sys.argv[2:]))\n'   # BIAN's inference (MX-47, MX-54): the copy's own
            'print("[the package\'s code]", file=sys.stderr)\n'
            'from sdem import api\nfrom sdem_bian.bian import main\nsys.exit(api.run("bian", main, sys.argv[1:]))\n')
    if os.name == 'nt':
        (folder / 'sdem-bian.py').write_text(body)
        (folder / 'sdem-bian.cmd').write_text(f'@"{sys.executable}" "%~dp0sdem-bian.py" %*\r\n')
    else:
        prog = folder / 'sdem-bian'; prog.write_text(f'#!{sys.executable}\n' + body); prog.chmod(0o755)
    return {**ENV, 'PATH': str(folder) + os.pathsep + os.environ.get('PATH', ''), 'SDEM_EXTENSIONS_PATH': str(folder)}   # only the stand-in, not an installed one


@unittest.skipUnless(_installed_package(), 'needs sdem-bian installed: the stand-in is a copy of it (0.22: BIAN only from sdem-bian)')
class Package(unittest.TestCase):   # step 2: BIAN in its own package (docs/design/sdem-bian-package-spec.md, BP-01…BP-11)
    def setUp(self): self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self): shutil.rmtree(self.tmp, ignore_errors=True)

    def test_with_the_package_every_answer_is_the_same_as_0_19(self):   # P1 with sdem-bian installed
        env = fake_bian(self.tmp)
        out = self.tmp / 'golden'
        subprocess.run([sys.executable, str(ROOT / 'scripts' / 'golden' / 'capture.py'), str(out)], check=True, capture_output=True, env={**env, **GOLD_019}, cwd=ROOT)
        gold = ROOT / 'tests' / 'golden' / '0.19'
        self.assertEqual([n.name for n in sorted(gold.glob('*.json')) if not _same(n, out / n.name)], [])

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
        for p in sorted(_installed_package().glob('*.py')):
            f, src = p.name, p.read_text(encoding='utf-8')
            used = {n.module if n.module != 'sdem' or [a.name for a in n.names] != ['api'] else 'sdem.api' for n in ast.walk(ast.parse(src)) if isinstance(n, ast.ImportFrom) and (n.module or '').startswith('sdem')}   # from sdem import api: the same
            self.assertLessEqual(used, {'sdem.api'}, f)

    def test_a_package_that_does_not_support_this_sdem_is_not_used_and_said(self):   # BP-10, BP-05
        env = fake_bian(self.tmp, sdem_range='<0.1', mark='FROM-THE-PACKAGE')
        out = sdem('extensions', env=env)
        self.assertIn('not usable', out); self.assertIn('supports SDEM <0.1', out)   # BX-15: said — and no BIAN to use instead
        self.assertIn('the installed one is not usable', sdem('status', '--workspace', EXAMPLES / '0.20' / 'payment-initiation', env=env, ok=(2,)))

    def test_sdem_ships_no_bian_of_its_own(self):   # BX-15 (0.22): no built-in copy to fall back on
        for p in ('bian', 'metamodel/a2-service-domain.json', 'metamodel/ext-bian-pack.json', 'sdem/bian.py', 'sdem/rules_bian.py', 'sdem/aid_bian.py', 'sdem/inferences.py'):
            self.assertFalse((ROOT / p).exists(), p)


if __name__ == '__main__':
    unittest.main()
