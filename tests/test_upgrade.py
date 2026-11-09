"""The update framework (docs/design/sdem-update-framework.md, UF-01…UF-08): release notes, version requirements in profiles, and
`sdem upgrade check` — read-only, run by the new version against your workspaces. Synthetic data only."""
import json, os, re, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem.metamodel import Metamodel  # noqa: E402
CURRENT = Metamodel.load().version   # the metamodel a migration ends at
from sdem import upgrade as U  # noqa: E402
from sdem.paths import version  # noqa: E402

ENV = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}


def sdem(*args, cwd, ok=(0,)):
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], cwd=cwd, capture_output=True, text=True, env=ENV)
    assert r.returncode in ok, f'sdem {" ".join(map(str, args))}: exit {r.returncode}\n{r.stdout[-900:]}\n{r.stderr[-900:]}'
    return r.returncode, r.stdout + r.stderr, (json.loads(r.stdout) if r.stdout.strip().startswith('{') else None)


def fingerprint(d):
    return {p.relative_to(d).as_posix(): p.read_bytes() for p in sorted(d.rglob('*')) if p.is_file() and '.git' not in p.parts}


class ReleaseNotesTests(unittest.TestCase):
    def test_every_release_since_0_10_has_its_notes(self):  # UF-03
        doc = json.loads(U.NOTES.read_text())
        noted = [r['version'] for r in doc['releases']]
        self.assertEqual(noted, sorted(noted, key=U._v))
        self.assertIn(version(), noted)                                                                   # this release is noted
        changelog = re.findall(r'^## (\d+\.\d+\.\d+) ', (ROOT / 'CHANGELOG.md').read_text(), flags=re.M)
        self.assertEqual(sorted((v for v in changelog if U._v(v) >= U._v(doc['first'])), key=U._v), noted)
        for r in doc['releases']:
            self.assertEqual(set(r), {'version', 'date', 'kind', 'metamodel', 'migration', 'breaking', 'deprecations', 'actions', 'summary'}, r['version'])
            self.assertIn(r['kind'], ('patch', 'minor', 'major'))

    def test_the_notes_agree_with_the_metamodel_and_its_migrations(self):  # UF-03, UF-05
        from sdem.metamodel import Metamodel
        doc = json.loads(U.NOTES.read_text())
        self.assertEqual(doc['releases'][-1]['metamodel'], Metamodel.base().version)
        migs = {(m['from'], m['to']) for m in json.loads((ROOT / 'metamodel' / 'migrations.json').read_text())['migrations']}
        prev = None
        for r in doc['releases']:
            if prev and r['metamodel'] != prev:
                self.assertEqual((r['migration']['from'], r['migration']['to']), (prev, r['metamodel']), r['version'])   # a metamodel change is announced
                self.assertIn((prev, r['metamodel']), migs); self.assertEqual(r['kind'], 'minor')                         # …recorded, and never a patch
            elif r['kind'] == 'patch': self.assertIsNone(r['migration'], r['version'])
            prev = r['metamodel']

    def test_version_requirements(self):  # UF-04
        self.assertTrue(U.satisfies('0.16.1', '>=0.13')); self.assertTrue(U.satisfies('0.16.1', '>=0.13,<1.0'))
        self.assertFalse(U.satisfies('0.12.0', '>=0.13')); self.assertTrue(U.satisfies('0.16.1', '==0.16.1')); self.assertFalse(U.satisfies('1.0.0', '<1.0'))


class UpgradeCheckTests(unittest.TestCase):
    def setUp(self):
        """A repository as an architect has it on SDEM 0.14.0: pinned, two workspaces on metamodel 0.7.0, a team change to AGENTS.md."""
        self.tmp = Path(tempfile.mkdtemp()); self.repo = r = self.tmp / 'repo'; r.mkdir()
        sdem('agents', 'install', '--to', r, cwd=self.tmp)
        (r / 'requirements.txt').write_text('sdem @ git+https://github.com/taumoeps/bian-sdem-framework@v0.14.0\n')
        for w in ('payments', 'cards'): sdem('new', '--workspace', r / 'workspaces' / w, '--person', 'steven', '--example', 'payment-initiation', cwd=self.tmp)
        for f in (r / 'workspaces').glob('*/*.json'):
            d = json.loads(f.read_text())
            if isinstance(d, dict) and d.get('metamodel_version') == CURRENT: d['metamodel_version'] = '0.7.0'; f.write_text(json.dumps(d))
        f = r / 'workspaces' / 'payments' / 'mappings.json'; d = json.loads(f.read_text())
        next(m for m in d['mappings'] if m['relationship'] == 'DEPLOYED_ON' and m['status'] == 'approved')['target']['type'] = 'A4.InfrastructureComponent'
        f.write_text(json.dumps(d))
        (r / 'AGENTS.md').write_text((r / 'AGENTS.md').read_text() + '\n## Our team rule\n')

    def tearDown(self): shutil.rmtree(self.tmp, ignore_errors=True)

    def test_it_tells_what_upgrading_means_and_writes_nothing(self):  # UF-01, UF-02
        before = fingerprint(self.repo)
        _, _, d = sdem('upgrade', 'check', '--repo', self.repo, '--json', cwd=self.repo)
        self.assertEqual(fingerprint(self.repo), before)                                                 # read-only
        self.assertEqual((d['from'], d['from_source'], d['verdict']), ('0.14.0', 'requirements.txt', 'migrate'))
        self.assertIn('0.15.0', [r['version'] for r in d['releases']]); self.assertNotIn('0.14.0', [r['version'] for r in d['releases']])
        w = {Path(x['workspace']).name: x for x in d['workspaces']}
        self.assertEqual(w['payments']['migration']['changes'], {'narrow_endpoint_type': 1})              # what the migration will do
        self.assertEqual(w['cards']['migration']['changes'], {})
        self.assertIn('AGENTS.md', d['agent_files']['kept_your_changes'])                                  # your team's change is kept
        self.assertTrue(any(s.startswith('sdem migrate --workspace') for s in d['steps']))

    def test_a_profile_this_version_does_not_meet_blocks(self):  # UF-04
        sdem('profile', 'example', '--out', self.tmp / 'p', cwd=self.tmp)
        prof = json.loads((self.tmp / 'p' / 'bank-base.json').read_text()); prof['requires_sdem'] = '>=99.0'
        (self.repo / 'workspaces' / 'cards' / 'sdem-profile.json').write_text(json.dumps(prof))
        code, out, d = sdem('upgrade', 'check', '--repo', self.repo, '--json', cwd=self.repo, ok=(1,))
        self.assertEqual(d['verdict'], 'blocked')
        self.assertIn('requires SDEM >=99.0', json.dumps(d))

    def test_a_deprecated_link_in_use_is_named(self):  # UF-02
        ws = self.tmp / 'now'; sdem('new', '--workspace', ws, '--person', 'steven', '--example', 'payment-initiation', cwd=self.tmp)
        f = ws / 'mappings.json'; d = json.loads(f.read_text())
        next(m for m in d['mappings'] if m['relationship'] == 'DEPLOYED_ON' and m['status'] == 'approved')['target'].update(id='TS-MQ', type='A4.TechnologyService', version='1.0')
        f.write_text(json.dumps(d))
        _, _, r = sdem('upgrade', 'check', '--workspace', ws, '--repo', self.tmp, '--from', '0.15.0', '--json', cwd=self.tmp)
        self.assertTrue(any('deprecated link type' in x for x in r['workspaces'][0]['warnings']))

    def test_releases_since(self):
        _, _, d = sdem('releases', '--since', '0.15.0', '--json', cwd=self.tmp)
        self.assertEqual(d['releases'][0]['version'], '0.16.0')


if __name__ == '__main__':
    unittest.main()
