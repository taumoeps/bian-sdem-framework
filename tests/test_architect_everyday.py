"""Everyday design work in few commands (an external usability review; the owner's approval, 2026-11-12): the workspace found from the
current folder (WS-11), `sdem status` (ST-01…ST-05), every option described and no summary cut (CR-04), the ten everyday commands
first (CR-05) — synthetic examples only."""
import hashlib, json, os, re, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem.cli import EVERYDAY, JOURNEYS  # noqa: E402

EX = ROOT / 'examples'
REF = ROOT / 'docs' / 'reference' / 'cli-reference.md'


def sdem(*args, cwd):
    env = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], cwd=cwd, capture_output=True, text=True, env=env)
    return r.returncode, r.stdout, r.stderr


def fingerprint(d):
    return {str(p.relative_to(d)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(d).rglob('*')) if p.is_file()}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, self.tmp, True)

    def copy(self, name, to=None):
        d = self.tmp / (to or name); shutil.copytree(EX / name, d, ignore=shutil.ignore_patterns('graph')); return d


class WorkspaceFoundTests(Base):   # WS-11
    def test_inside_a_workspace_it_is_found(self):
        ws = self.copy('payment-initiation')
        code, out, err = sdem('status', cwd=ws)
        self.assertEqual(code, 0, err); self.assertIn('payment-initiation — CLEAR', out)
        self.assertIn('sdem: workspace payment-initiation — found from the current folder', err)
        (ws / 'notes').mkdir()
        code, out, err = sdem('check', cwd=ws / 'notes')   # from a folder below it
        self.assertEqual(code, 0, err); self.assertIn('sdem: workspace ..', err)
        code, out, err = sdem('comply', cwd=ws)
        self.assertEqual(code, 0, err); self.assertIn('no organisation profile', out)

    def test_given_beats_found(self):
        here, there = self.copy('payment-initiation'), self.copy('digital-lending')
        code, out, err = sdem('status', '--workspace', there, cwd=here)
        self.assertIn('digital-lending — OPEN', out); self.assertNotIn('found from the current folder', err)

    def test_outside_a_workspace_it_must_be_given(self):
        code, out, err = sdem('status', cwd=self.tmp)
        self.assertEqual(code, 2); self.assertIn('--workspace', err)

    def test_new_is_never_given_the_workspace_it_is_in(self):
        ws = self.copy('payment-initiation')
        code, out, err = sdem('new', '--workspace', 'inner', '--person', 'jane.architect', '--dry-run', cwd=ws)
        self.assertEqual(code, 0, err); self.assertNotIn('found from the current folder', err)

    def test_it_looks_no_higher_than_the_repository(self):
        ws = self.copy('payment-initiation'); (ws / 'repo' / '.git').mkdir(parents=True)
        code, out, err = sdem('status', cwd=ws / 'repo')
        self.assertEqual(code, 2); self.assertNotIn('found from the current folder', err)


class StatusTests(Base):   # ST-01…ST-05
    def test_clear_open_and_blocked(self):
        clear = self.copy('payment-initiation')
        code, out, _ = sdem('status', '--workspace', clear, '--json', cwd=self.tmp)
        s = json.loads(out); self.assertEqual((code, s['state'], s['counts']['blocking'], s['counts']['unresolved']), (0, 'clear', 0, 0))
        self.assertTrue(s['next'][0]['command'].startswith('sdem document'))
        lending = self.copy('digital-lending')
        code, out, _ = sdem('status', '--workspace', lending, '--json', cwd=self.tmp)
        s = json.loads(out); self.assertEqual((code, s['state']), (0, 'open'))
        self.assertTrue(all(u['kind'] == 'link_to_review' for u in s['unresolved']))
        self.assertEqual(s['missing_layers'], ['A3', 'A4'])
        broken = self.copy('payment-initiation', 'broken')
        d = json.loads((broken / 'a3-application.json').read_text()); d['instances'][0]['type'] = 'A3.NoSuchType'
        (broken / 'a3-application.json').write_text(json.dumps(d))
        code, out, _ = sdem('status', '--workspace', broken, cwd=self.tmp)
        self.assertEqual(code, 1); self.assertIn('BLOCKED', out); self.assertIn("'A3.NoSuchType' is not in the metamodel", out)
        self.assertIn('1. sdem check --workspace', out)

    def test_a_persons_decision_is_marked_never_run(self):   # ST-02, CTL-21
        lending = self.copy('digital-lending')
        s = json.loads(sdem('status', '--workspace', lending, '--json', cwd=self.tmp)[1])
        approve = next(n for n in s['next'] if n['command'].startswith('sdem approve'))
        self.assertTrue(approve['person_decides']); self.assertIn('--reviewer <you>', approve['command'])
        self.assertTrue(all(not n['person_decides'] for n in s['next'] if n['command'].startswith(('sdem link', 'sdem aid --'))))
        self.assertFalse((lending / 'mappings.json').read_text() != (EX / 'digital-lending' / 'mappings.json').read_text())
        self.assertIn('👤 sdem approve', sdem('status', '--workspace', lending, cwd=self.tmp)[1])

    def test_it_writes_nothing(self):   # ST-04
        ws = self.copy('digital-lending'); before = fingerprint(ws)
        sdem('status', '--workspace', ws, cwd=self.tmp); sdem('status', '--workspace', ws, '--json', cwd=self.tmp)
        self.assertEqual(fingerprint(ws), before)

    def test_the_json_contract_and_limit(self):   # ST-05
        ws = self.copy('digital-lending')
        s = json.loads(sdem('status', '--workspace', ws, '--json', '--limit', '2', cwd=self.tmp)[1])
        self.assertEqual(s['sdem']['command'], 'status')
        for k in ('state', 'counts', 'blocking', 'unresolved', 'warnings', 'next', 'layers', 'connections'): self.assertIn(k, s)
        self.assertLessEqual(len(s['unresolved']), 2)

    def test_not_a_workspace(self):   # ST-03
        code, out, err = sdem('status', '--workspace', self.tmp, cwd=self.tmp)
        self.assertEqual(code, 2); self.assertIn('not a workspace folder', err)


class DiscoveryDocsTests(unittest.TestCase):   # CR-04, CR-05
    def test_ten_everyday_commands_first(self):
        names = [n for n, _ in EVERYDAY]
        self.assertEqual(len(names), 10); self.assertTrue(set(names) <= set(JOURNEYS))
        out = sdem('--help', cwd=ROOT)[1]
        every = out.index('Everyday'); rest = out.index('Everything else')
        self.assertTrue(all(out.index(f'  {n} ', every) < rest for n in names))
        ref = REF.read_text(encoding='utf-8'); quick = (ROOT / 'docs' / 'sdem-quick-start.md').read_text(encoding='utf-8')
        section = ref[ref.index('## Everyday'):ref.index('## Index')]
        self.assertEqual(re.findall(r'\[`sdem (\w+)`\]', section), names)
        self.assertEqual(re.findall(r'^\| `sdem (\w+)` \|', quick, re.M), names)

    def test_every_option_is_described(self):
        ref = REF.read_text(encoding='utf-8')
        bare = [l for l in ref.splitlines() if re.match(r'^\| `[^|]*\| (yes)? *\| — \|$', l)]
        self.assertEqual(bare, [], 'describe these options where the command defines them, or in sdem/helptext.py')

    def test_no_summary_is_cut_mid_word(self):
        ref = REF.read_text(encoding='utf-8'); index = ref[ref.index('## Index'):ref.index('## Commands')]
        cut = [l for l in index.splitlines() if '…' in l and not re.search(r' … \|$|…\]|…`|, …', l) and l.rstrip(' |').endswith('…')]
        self.assertEqual(cut, [])


if __name__ == '__main__':
    unittest.main()
