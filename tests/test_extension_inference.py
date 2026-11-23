"""MX-45…MX-52 (docs/design/sdem-metamodel-extensions-spec.md §16; the 0.22 plan, step 2): a metamodel extension that infers. A made-up
extension, *Recovery* (V1: a layer beside the stack), says in its manifest that it infers for `aid`; `sdem aid` runs it — never imports it
(EXT-02) — and checks what it answers as its own: a recovery plan for each data entity, in the extension's own layer, and a RECOVERS link
proposed for a person to approve. What it gets wrong is refused and said; an extension the workspace does not include is never asked.
No SDEM code names either extension. Synthetic data only."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem import profile as P  # noqa: E402

PACK = {'format': 'sdem-profile/1', 'name': 'recovery', 'version': 1,
        'layers': [{'code': 'D', 'name': 'Disaster Recovery', 'position': 'across', 'file': 'recovery.json', 'description': 'recovery plans (made-up)'}],
        'types': [{'type': 'DRX.D.RecoveryPlan', 'description': 'how something is recovered (made-up)', 'archimate': 'CourseOfAction'}],
        'link_types': [{'source_type': 'DRX.D.RecoveryPlan', 'relationship': 'RECOVERS', 'archimate': 'association', 'target_type': 'A3.DataEntity', 'required_evidence': ['design_document']}]}

# the extension's program: it reads the workspace's documented files (EXT-02) and answers sdem-inference/1
INFER = r'''
import sys, json, pathlib
a = sys.argv[1:]
if "--manifest" in a: print(json.dumps(MANIFEST)); sys.exit(0)
if a[:1] == ["infer"]:
    if NAME == "idle": pathlib.Path(MARK).write_text("asked"); print(json.dumps({"format": "sdem-inference/1"})); sys.exit(0)
    ws = pathlib.Path(a[a.index("--workspace") + 1])
    ents = []
    for f in sorted(ws.glob("*.json")):
        try: d = json.loads(f.read_text())
        except Exception: continue
        for r in d.get("instances", []) if isinstance(d, dict) else []:
            if str(r.get("type", "")).endswith("DataEntity"): ents.append(r)
    ans = {"format": "sdem-inference/1", "records": [], "proposals": []}
    for e in ents[:3]:
        pid = "DRP-" + e["id"]
        ans["records"].append({"layer": "D", "record": {"id": pid, "type": "DRX.D.RecoveryPlan", "name": "Recovery of " + e.get("name", e["id"])},
                               "rule": "REC-01", "reasoning": "every data entity needs a recovery plan", "confidence": "low", "from": e["id"]})
        ans["proposals"].append({"source": pid, "relationship": "RECOVERS", "target": e["id"], "rule": "REC-01", "rationale": "the plan recovers the entity", "confidence": "low"})
    ans["records"].append({"layer": "D", "record": {"id": "BAD-TYPE", "type": "DRX.D.NoSuchThing", "name": "wrong"}, "rule": "REC-99"})
    ans["proposals"].append({"source": "DRP-X", "relationship": "NOT_A_LINK", "target": "Y", "rule": "REC-99"})
    print(json.dumps(ans)); sys.exit(0)
sys.exit(2)
'''


def fake(folder, name, pack, mark):
    p = folder / f'{name}-pack.json'
    if pack: p.write_text(json.dumps(pack))
    man = {'name': name, 'command': f'sdem-{name}', 'version': '0.1.0', 'kind': ['metamodel'], 'sdem': '>=0.0', 'infers': ['aid', 'link'],
           'description': f'a made-up {name} extension', **({'pack': str(p)} if pack else {})}
    body = f'NAME = {name!r}\nMANIFEST = {man!r}\nMARK = {str(mark)!r}\n' + INFER
    if os.name == 'nt':
        (folder / f'sdem-{name}.py').write_text(body)
        (folder / f'sdem-{name}.cmd').write_text(f'@"{sys.executable}" "%~dp0sdem-{name}.py" %*\r\n')
    else:
        prog = folder / f'sdem-{name}'; prog.write_text(f'#!{sys.executable}\n' + body); prog.chmod(0o755)


class ExtensionsThatInfer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = t = Path(tempfile.mkdtemp()); (t / 'bin').mkdir()
        cls.mark = t / 'idle-was-asked'
        fake(t / 'bin', 'recovery', PACK, cls.mark)
        fake(t / 'bin', 'idle', None, cls.mark)   # infers too, but no workspace includes it
        cls.env = {**os.environ, 'PYTHONPATH': str(ROOT), 'PYTHONIOENCODING': 'utf-8', 'PATH': str(t / 'bin') + os.pathsep + os.environ.get('PATH', '')}
        cls.ws = ws = t / 'ws'
        cls.sdem('new', '--workspace', ws, '--person', 'steven', '--example', 'payment-initiation')
        cls.sdem('profile', 'include', 'ext:recovery', '--workspace', ws, '--person', 'steven', '--reason', 'recovery (made-up)')
        cls.sdem('profile', 'adopt', '--workspace', ws, '--person', 'steven', '--reason', 'a made-up extension that infers')
        cls.run_rec = json.loads(cls.sdem('aid', '--workspace', ws, '--person', 'steven', '--json')[1])
        cls.layer = json.loads((ws / 'recovery.json').read_text()) if (ws / 'recovery.json').exists() else {'instances': []}

    @classmethod
    def sdem(cls, *args, ok=(0,)):
        r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], cwd=cls.tmp, capture_output=True, text=True, encoding='utf-8', env=cls.env)
        assert r.returncode in ok, f'sdem {" ".join(map(str, args))}: exit {r.returncode}\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}'
        return r.returncode, r.stdout

    @classmethod
    def tearDownClass(cls): P.deactivate(); shutil.rmtree(cls.tmp, ignore_errors=True)

    def report(self): return next(x for x in self.run_rec.get('extensions', []) if x['extension'] == 'recovery')

    def test_mx48_its_records_are_written_marked_as_its_own(self):
        recs = [r for r in self.layer['instances'] if r['id'].startswith('DRP-')]
        self.assertTrue(recs)
        for r in recs:
            self.assertEqual(r['type'], 'DRX.D.RecoveryPlan')
            inf = r['attributes']['inferred']
            self.assertEqual((inf['by'], inf['rule'], inf['run']), ('recovery 0.1.0', 'REC-01', self.run_rec['id']))
            self.assertNotIn('status', inf)   # inferred, not yet confirmed

    def test_mx48_its_links_between_layers_are_proposed_for_a_person(self):
        props = json.loads((self.ws / 'aid' / f"{self.run_rec['id']}-proposals.json").read_text())['mappings']
        mine = [p for p in props if p['relationship'] == 'RECOVERS']
        self.assertEqual(len(mine), self.report()['proposals']); self.assertTrue(mine)
        self.assertTrue(all(p['status'] == 'proposed' and p['created_by'] == 'recovery 0.1.0' for p in mine))

    def test_mx50_what_it_gets_wrong_is_refused_and_said(self):
        why = ' '.join(x['why'] for x in self.report()['refused'])
        self.assertIn('DRX.D.NoSuchThing is not a type', why)
        self.assertIn("'NOT_A_LINK' is not a link type", why)
        self.assertNotIn('BAD-TYPE', {r['id'] for r in self.layer['instances']})

    def test_mx46_an_extension_the_workspace_does_not_include_is_never_asked(self):
        self.assertFalse(self.mark.exists())
        self.assertNotIn('idle', {x['extension'] for x in self.run_rec.get('extensions', [])})

    def test_mx49_a_person_confirms_or_rejects_it_like_sdems_own(self):
        ids = sorted(r['id'] for r in self.layer['instances'] if r['id'].startswith('DRP-'))
        self.sdem('aid', 'confirm', ids[0], '--workspace', self.ws, '--person', 'steven')
        self.sdem('aid', 'reject', ids[1], '--workspace', self.ws, '--person', 'steven', '--reason', 'not needed (made-up)')
        d = {r['id']: r for r in json.loads((self.ws / 'recovery.json').read_text())['instances']}
        self.assertEqual(d[ids[0]]['attributes']['inferred']['status'], 'confirmed')
        self.assertNotIn(ids[1], d)
        self.sdem('aid', '--workspace', self.ws, '--person', 'steven', '--json')   # asked again: a rejected record is not inferred again
        self.assertNotIn(ids[1], {r['id'] for r in json.loads((self.ws / 'recovery.json').read_text())['instances']})

    def test_mx51_sdem_link_lists_its_proposals_with_sdems_own(self):
        _, out = self.sdem('link', '--workspace', self.ws, '--out', self.tmp / 'links', '--json')
        props = json.loads((self.tmp / 'links' / 'proposals.json').read_text())['mappings']
        self.assertTrue(any(p['relationship'] == 'RECOVERS' and p['created_by'] == 'recovery 0.1.0' and p['status'] == 'proposed' for p in props))

    def test_the_workspace_still_passes_its_checks(self):
        self.sdem('check', '--workspace', self.ws)

    def test_no_sdem_code_names_them(self):
        code = ''.join(p.read_text(encoding='utf-8') for p in (ROOT / 'sdem').rglob('*.py'))
        for word in ('DRX.', 'RECOVERS', "'recovery'", "'idle'", 'REC-01'):
            self.assertNotIn(word, code)


if __name__ == '__main__':
    unittest.main()
