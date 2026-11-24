"""MX-54 (docs/design/sdem-metamodel-extensions-spec.md §16; the 0.22 plan, step 3c): BIAN's part of `sdem aid`, given by the extension that
provides BIAN, at its phases. A made-up `sdem-bian` answers each phase through SDEM's own copy of BIAN's part (sdem/aid_bian.py, as the real
sdem-bian carries it, BP-11): `sdem aid` asks it — never imports it (R-D5) — infers exactly what it infers without it, and says who gave
BIAN's part (`phases_by`); one that fails stops the run with nothing written. Compared with the real sdem-bian (R-D2: since 0.22 a banking
design needs it). The state crosses in ids, so neither side's numbering
matters (to_wire). The proof on every example is sdem-bian's tests/test_infer_aid.py. Synthetic data only."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem import profile as P  # noqa: E402

MANIFEST = {'name': 'bian', 'command': 'sdem-bian', 'version': '9.9.9', 'kind': ['metamodel'], 'sdem': '>=0.0', 'infers': ['aid-phases'],
            'description': 'a made-up stand-in for sdem-bian: BIAN\'s part of sdem aid, through SDEM\'s own copy'}
PROGRAM = r'''
import contextlib, json, os, sys
a = sys.argv[1:]
if "--manifest" in a: print(json.dumps(MANIFEST)); sys.exit(0)
if a[:1] == ["infer"] and "--phase" in a:
    if os.environ.get("FAKE_BIAN_FAILS"): print("broken on purpose", file=sys.stderr); sys.exit(3)
    sys.path.insert(0, ROOT)
    from sdem import api
    from sdem.aid_bian import answer
    ws, phase, state = a[a.index("--workspace") + 1], a[a.index("--phase") + 1], a[a.index("--state") + 1]
    api.activate(ws)
    with open(state, encoding="utf-8") as f: st = json.load(f)
    with (api.view_019() if api.parts.migrated() else contextlib.nullcontext()):
        result = answer(phase, st, ws)
    with open(os.environ["FAKE_BIAN_LOG"], "a") as f: f.write(phase + "\n")
    print(json.dumps({"format": "sdem-inference/1", "phase": phase, "result": result})); sys.exit(0)
if a[:1] == ["infer"]: print(json.dumps({"format": "sdem-inference/1"})); sys.exit(0)
sys.exit(2)
'''


def install(folder):
    real = json.loads(subprocess.run([shutil.which('sdem-bian'), '--manifest'], capture_output=True, text=True, encoding='utf-8').stdout)
    man = {**MANIFEST, **{k: real[k] for k in ('bian_data', 'pack', 'api', 'commands') if k in real}}   # BIAN's data from the real one (R-D2): only its part of sdem aid is made up
    body = f'MANIFEST = {man!r}\nROOT = {str(ROOT)!r}\n' + PROGRAM
    if os.name == 'nt':
        (folder / 'sdem-bian.py').write_text(body)
        (folder / 'sdem-bian.cmd').write_text(f'@"{sys.executable}" "%~dp0sdem-bian.py" %*\r\n')
    else:
        prog = folder / 'sdem-bian'; prog.write_text(f'#!{sys.executable}\n' + body); prog.chmod(0o755)


def _real_bian():
    return any((Path(p) / n).exists() for p in os.environ.get('PATH', '').split(os.pathsep) if p for n in ('sdem-bian', 'sdem-bian.exe', 'sdem-bian.cmd'))


@unittest.skipUnless(_real_bian(), 'needs sdem-bian installed (R-D2): the made-up one is compared with it')
class AidPhases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = t = Path(tempfile.mkdtemp()); (t / 'bin').mkdir(); install(t / 'bin')
        cls.log = t / 'phases.log'
        base = {**os.environ, 'PYTHONPATH': str(ROOT), 'PYTHONIOENCODING': 'utf-8', 'FAKE_BIAN_LOG': str(cls.log)}
        path = [p for p in os.environ.get('PATH', '').split(os.pathsep) if not (Path(p) / 'sdem-bian').exists() and not (Path(p) / 'sdem-bian.exe').exists()]
        cls.own_env = {**base, 'PATH': os.environ.get('PATH', '')}   # the real sdem-bian, installed (R-D2: a banking design needs it)
        cls.ext_env = {**base, 'PATH': os.pathsep.join([str(t / 'bin'), *path])}
        cls.sdem(cls.own_env, 'new', '--workspace', t / 'own', '--person', 'steven', '--example', 'payment-initiation')
        shutil.copytree(t / 'own', t / 'ext'); shutil.copytree(t / 'own', t / 'broken')
        cls.own = json.loads(cls.sdem(cls.own_env, 'aid', '--workspace', t / 'own', '--person', 'steven', '--json')[1])
        cls.ext = json.loads(cls.sdem(cls.ext_env, 'aid', '--workspace', t / 'ext', '--person', 'steven', '--json')[1])
        cls.broken = cls.sdem({**cls.ext_env, 'FAKE_BIAN_FAILS': '1'}, 'aid', '--workspace', t / 'broken', '--person', 'steven', '--json', ok=None)

    @classmethod
    def sdem(cls, env, *args, ok=(0,)):
        r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], cwd=cls.tmp, capture_output=True, text=True, encoding='utf-8', env=env)
        assert ok is None or r.returncode in ok, f'sdem {" ".join(map(str, args))}: exit {r.returncode}\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}'
        return r.returncode, r.stdout, r.stderr

    @classmethod
    def tearDownClass(cls): P.deactivate(); shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_mx54_the_extension_is_asked_at_each_phase_never_imported(self):
        asked = self.log.read_text().split()
        self.assertEqual(asked[0], 'projection')
        self.assertEqual(asked, ['projection', 'existing', 'information', 'access', 'direct'])   # in sdem aid's order (no pattern fits this design: no patterns phase)
        self.assertEqual(self.ext['phases_by'], 'bian 9.9.9')
        self.assertTrue(self.own['phases_by'].startswith('bian '))   # the real sdem-bian named too

    def test_mx54_it_infers_exactly_what_sdems_own_copy_infers(self):
        for k in ('added', 'proposed_connections', 'zone_placements', 'a4_connections', 'draft', 'projection_ends', 'tables_not_inferred'):
            self.assertEqual(self.ext.get(k), self.own.get(k), k)
        for f in sorted(p.name for p in (self.tmp / 'own').glob('*.json')):
            own, ext = (self.tmp / 'own' / f).read_text(encoding='utf-8'), (self.tmp / 'ext' / f).read_text(encoding='utf-8')
            strip = lambda s: json.dumps(_no_time(json.loads(s)), sort_keys=True)
            self.assertEqual(strip(ext), strip(own), f)

    def test_mx54_a_provider_that_fails_stops_the_run_with_nothing_written(self):
        code, _, err = self.broken
        self.assertNotEqual(code, 0)
        self.assertIn('phase projection: exit 3', err)
        self.assertIn('nothing written', err)
        self.assertFalse((self.tmp / 'broken' / 'aid').exists())

    def test_mx54_the_state_crosses_in_ids_and_comes_back_whole(self):
        from sdem import identity, parts
        from sdem.aid_fill import _workspace
        P.activate_from(self.tmp / 'own')
        with (identity.view_019() if parts.migrated() else _null()):
            _, docs, registry = _workspace(self.tmp / 'own')
            x = {'after': docs, 'maps': registry['mappings'][:20]}
            wire = json.loads(json.dumps(identity.to_wire(x)))
            self.assertFalse(any(k in wire['after'] for k in docs), 'layers cross by id, not by code')
            self.assertEqual(identity.from_wire(wire), x)

    def test_bp11_the_package_carries_aid_bian_as_sdem_has_it(self):
        from sdem import parts
        code = parts.package_code()
        self.assertIn('aid_bian.py', code)
        self.assertNotRegex(code['aid_bian.py'], r'(?m)^\s*from \.(?!rules_bian |bian )\w* import')   # only sdem.api, and the package's own


def _no_time(x):
    if isinstance(x, dict): return {k: _no_time(v) for k, v in x.items() if k not in ('at', 'model_version')}
    if isinstance(x, list): return [_no_time(v) for v in x]
    return x


class _null:
    def __enter__(self): return self
    def __exit__(self, *a): return False


if __name__ == '__main__':
    unittest.main()
