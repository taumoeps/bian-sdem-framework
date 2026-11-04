"""Navigation between SDEM Home, the Workspace Dashboard and the Architecture Graph (docs/design/sdem-dashboard-design.md §4b,
NV-01…NV-08). Every link is checked by resolving it to the file it points to — not by searching for a label. Synthetic data only."""
import json, os, re, shutil, subprocess, sys, tempfile, unittest, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}


def sdem(*args, cwd, ok=(0,)):
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], cwd=cwd, capture_output=True, text=True, env=ENV)
    assert r.returncode in ok, f'sdem {" ".join(map(str, args))}: exit {r.returncode}\n{r.stdout[-900:]}\n{r.stderr[-900:]}'
    return r.stdout + r.stderr


def page_data(f):
    """The data a generated page carries (const D = {...})."""
    t = Path(f).read_text(encoding='utf-8'); i = re.search(r'const D\s*=\s*', t).end()
    return json.JSONDecoder().raw_decode(t, i)[0]


def follow(from_file, link):
    """Where a relative, URL-encoded link from a page leads — as a browser opening the page from file:// resolves it."""
    return (Path(from_file).parent / urllib.parse.unquote(link)).resolve()


def fingerprint(d):
    return {p.relative_to(d).as_posix(): p.read_bytes() for p in sorted(Path(d).rglob('*')) if p.is_file() and 'graph' not in p.relative_to(d).parts and p.suffix != '.html'}


class NavigationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self): shutil.rmtree(self.tmp, ignore_errors=True)

    def workspace(self, rel, build=True, rename=None):
        ws = self.tmp / rel
        sdem('new', '--workspace', ws, '--person', 'steven', '--example', 'payment-initiation', cwd=self.tmp)
        if rename:   # tell two workspaces apart
            f = ws / 'a1-business.json'; d = json.loads(f.read_text()); d['instances'][0]['name'] = rename; f.write_text(json.dumps(d))
            sdem('change', 'adopt', '--workspace', ws, '--layer', 'A1', '--person', 'steven', '--reason', 'test', cwd=self.tmp)
        if build: sdem('build', '--workspace', ws, '--out', ws / 'graph', cwd=self.tmp)
        return ws

    def journey(self, index):
        """Home → each workspace's dashboard → its graph → back; returns {workspace name: (dashboard, graph or None)}."""
        out = {}
        H = page_data(index)
        for p in H['projects']:
            dash = follow(index, p['page']); self.assertTrue(dash.exists(), p)                                   # 1
            D = page_data(dash)
            self.assertEqual(follow(dash, D['home']), index.resolve())                                            # dashboard → Home
            g = None
            if p['graph']['href']:
                g = follow(index, p['graph']['href']); self.assertTrue(g.exists())
                self.assertEqual(follow(dash, D['graph_nav']['href']), g)                                         # 2: the same graph
                G = page_data(g); links = {l['label']: follow(g, l['href']) for l in G['links']}
                self.assertEqual(links['← Workspace Dashboard'], dash)                                            # 3
                self.assertEqual(links['SDEM Home'], index.resolve())                                              # 4
            out[p['name']] = (dash, g)
        return out

    def test_home_dashboard_graph_and_back_in_nested_folders_with_spaces(self):  # NV-01…NV-05, NV-07 — tests 1–6
        ws = self.workspace('work space/pay ments & co (é)')
        out = self.tmp / 'deep' / 'nested out'
        sdem('home', '--root', self.tmp / 'work space', '-o', out, cwd=self.tmp)
        pages = self.journey(out / 'index.html')
        dash, g = pages['pay ments & co (é)']
        self.assertIsNotNone(g)
        for f in [out / 'index.html', dash, g]:
            self.assertNotIn(str(self.tmp.resolve()), f.read_text(encoding='utf-8'))                               # NV-07: no machine paths
            self.assertNotIn('/private/', f.read_text(encoding='utf-8'))
        self.assertIn('<meta name="sdem-graph-build" content="1">', g.read_text())                                # NV-04

    def test_the_standalone_route_links_both_ways(self):  # sdem build → view → dashboard
        ws = self.workspace('workspaces/payments')
        sdem('view', '--graph', ws / 'graph', cwd=self.tmp); sdem('dashboard', '--workspace', ws, cwd=self.tmp)
        D = page_data(ws / 'dashboard.html'); g = follow(ws / 'dashboard.html', D['graph_nav']['href'])
        self.assertEqual(g, (ws / 'graph' / 'view.html').resolve())
        self.assertEqual(follow(g, page_data(g)['links'][0]['href']), (ws / 'dashboard.html').resolve())

    def test_workspaces_never_link_to_each_others_graphs(self):  # NV-06 — test 7
        a = self.workspace('one/ledger', rename='Alpha capability'); b = self.workspace('two/ledger', rename='Beta capability')
        out = self.tmp / 'site'; (self.tmp / 'none').mkdir()   # an empty root: only the two workspaces given
        sdem('home', '--workspace', a, '--workspace', b, '--root', self.tmp / 'none', '-o', out, cwd=self.tmp)
        pages = self.journey(out / 'index.html')
        graphs = [follow(out / 'index.html', p['graph']['href']) for p in page_data(out / 'index.html')['projects']]   # both are named 'ledger'
        self.assertEqual(len(set(graphs)), 2)                                                                     # two distinct graph pages
        texts = sorted(g.read_text() for g in graphs)
        self.assertTrue(any('Alpha capability' in t and 'Beta capability' not in t for t in texts))
        self.assertTrue(any('Beta capability' in t and 'Alpha capability' not in t for t in texts))

    def test_missing_and_stale_graphs_are_never_linked(self):  # NV-03 — test 8
        ws = self.workspace('workspaces/p', build=False)
        sdem('dashboard', '--workspace', ws, cwd=self.tmp)
        g = page_data(ws / 'dashboard.html')['graph_nav']
        self.assertEqual((g['state'], g['href']), ('missing', None)); self.assertTrue(g['commands'][0].startswith('sdem build --workspace'))
        sdem('build', '--workspace', ws, '--out', ws / 'graph', cwd=self.tmp); sdem('view', '--graph', ws / 'graph', cwd=self.tmp)
        f = ws / 'a1-business.json'; d = json.loads(f.read_text()); d['instances'][0]['description'] = 'changed after the build'; f.write_text(json.dumps(d))
        sdem('dashboard', '--workspace', ws, cwd=self.tmp)
        g = page_data(ws / 'dashboard.html')['graph_nav']
        self.assertEqual((g['state'], g['href']), ('stale', None)); self.assertIn('a1-business.json', g['reason'])
        out = self.tmp / 'site'; sdem('home', '--root', self.tmp / 'workspaces', '-o', out, cwd=self.tmp)
        self.assertEqual(page_data(out / 'index.html')['projects'][0]['graph']['href'], None)
        self.assertEqual(list((out / 'workspaces').glob('*-graph.html')), [])                                     # no page that would look current
        sdem('build', '--workspace', ws, '--out', ws / 'graph', cwd=self.tmp); sdem('dashboard', '--workspace', ws, cwd=self.tmp)
        self.assertEqual(page_data(ws / 'dashboard.html')['graph_nav']['state'], 'viewer_stale')                 # rebuilt, viewer not regenerated

    def test_a_workspace_that_needs_migration_or_fails_its_checks_says_so(self):  # NV-03 — test 9
        old = self.workspace('workspaces/old', build=False); bad = self.workspace('workspaces/bad', build=False)
        for f in old.glob('*.json'):
            d = json.loads(f.read_text())
            if isinstance(d, dict) and d.get('metamodel_version'): d['metamodel_version'] = '0.7.0'; f.write_text(json.dumps(d))
        f = bad / 'a3-application.json'; d = json.loads(f.read_text()); d['instances'][0]['attributes']['hosting_model'] = 'NotAModel'; f.write_text(json.dumps(d))
        out = self.tmp / 'site'; sdem('home', '--root', self.tmp / 'workspaces', '-o', out, cwd=self.tmp)
        g = {p['name']: p['graph'] for p in page_data(out / 'index.html')['projects']}
        self.assertEqual(g['old']['state'], 'blocked'); self.assertIn('migrate', g['old']['reason']); self.assertTrue(g['old']['commands'][0].startswith('sdem migrate --workspace'))
        self.assertEqual(g['bad']['state'], 'blocked'); self.assertTrue(g['bad']['commands'][0].startswith('sdem check --workspace'))

    def test_generating_pages_changes_no_workspace(self):  # NV-08 — test 10
        ws = self.workspace('workspaces/payments')
        before = fingerprint(ws)
        sdem('view', '--graph', ws / 'graph', cwd=self.tmp); sdem('dashboard', '--workspace', ws, cwd=self.tmp)
        sdem('home', '--root', self.tmp / 'workspaces', '-o', self.tmp / 'site', cwd=self.tmp)
        self.assertEqual(fingerprint(ws), before)
        self.assertEqual(sdem('check', '--workspace', ws, '--require-recorded', cwd=self.tmp).count('ERROR'), 0)

    def test_existing_invocations_still_work(self):  # test 11
        ws = self.workspace('workspaces/payments')
        sdem('view', '--graph', ws / 'graph', '-o', self.tmp / 'v.html', cwd=self.tmp)
        sdem('dashboard', '--workspace', ws, '-o', self.tmp / 'd.html', cwd=self.tmp)
        sdem('home', '-o', self.tmp / 'h', '--root', self.tmp / 'workspaces', cwd=self.tmp)
        self.assertTrue((self.tmp / 'v.html').exists() and (self.tmp / 'd.html').exists() and (self.tmp / 'h' / 'index.html').exists())
        tmpstore = self.tmp / 'loose-graph'; shutil.copytree(ws / 'graph', tmpstore)
        sdem('view', '--graph', tmpstore, cwd=self.tmp)
        self.assertEqual(page_data(tmpstore / 'view.html')['links'], [])                                          # a store outside a workspace: no guessed link

    def test_the_guides_walkthrough_runs(self):  # test 12 and the v0.18.0 walkthrough: every command in §4a, as written, in order
        for step in guide_steps():
            if step[0] == 'file': (self.tmp / step[1]).write_text(step[2])
            else: sdem(*step[1][1:], cwd=self.tmp)
        pages = self.journey(self.tmp / 'work' / 'sdem' / 'index.html')                                          # Home → dashboard → graph → back
        ws = self.tmp / 'workspaces' / 'payments'
        # step 11: the proposal is in the dashboard's Review, never in the graph; once a person approves it, it is in the graph
        self.assertEqual(page_data(ws / 'dashboard.html')['graph_nav']['state'], 'current')                     # step 12 regenerated everything
        g = page_data(ws / 'graph' / 'view.html')
        self.assertIn('APP-PAY-NOTIFY', json.dumps(g))                                                             # the new record is in the rebuilt graph

    def test_explore_writes_the_three_pages_in_one_step(self):  # EX-01
        out = sdem('new', '--workspace', self.tmp / 'workspaces' / 'payments', '--person', 'jane.architect', '--example', 'payment-initiation', '--explore', cwd=self.tmp)
        self.assertIn('work/sdem/index.html', out)
        self.journey(self.tmp / 'work' / 'sdem' / 'index.html')
        self.assertEqual(sdem('check', '--workspace', self.tmp / 'workspaces' / 'payments', '--require-recorded', cwd=self.tmp).count('ERROR'), 0)   # nothing unrecorded
        r = subprocess.run([sys.executable, '-m', 'sdem', 'new', '--workspace', 'w2', '--person', 'jane', '--example', 'payment-initiation', '--explore', '--json'], cwd=self.tmp, capture_output=True, text=True, env=ENV)
        d = json.loads(r.stdout); self.assertTrue(d['explore']['home'].endswith('index.html')); self.assertIn('baseline', d)   # one JSON document

    def test_a_proposal_is_reviewed_not_drawn(self):  # proposed versus approved, as the walkthrough shows
        ws = self.workspace('workspaces/payments')
        (self.tmp / 'new-app.json').write_text(json.dumps({'layer': 'A3', 'reason': 'synthetic', 'changes': [{'op': 'add', 'record': {
            'id': 'APP-PAY-NOTIFY', 'type': 'A3.ApplicationComponent', 'version': '1.0', 'name': 'Payment Notifications', 'lifecycle_status': 'planned',
            'attributes': {'deployed_on': ['INF-K8S-PAY-PROD']}}}]}))
        sdem('change', 'propose', self.tmp / 'new-app.json', '--workspace', ws, '--agent', 'architect', '--person', 'jane', cwd=self.tmp)
        sdem('build', '--workspace', ws, '--out', ws / 'graph', cwd=self.tmp); sdem('view', '--graph', ws / 'graph', cwd=self.tmp); sdem('dashboard', '--workspace', ws, cwd=self.tmp)
        D = page_data(ws / 'dashboard.html')
        self.assertIn('APP-PAY-NOTIFY', json.dumps(D['review']['rows']))                                          # proposed: in Review
        G = page_data(ws / 'graph' / 'view.html')
        self.assertFalse(any('APP-PAY-NOTIFY' in json.dumps(e) and 'DEPLOYED_ON' in json.dumps(e) for e in G.get('edges', [])))           # not drawn as a link

    def test_the_architect_tasks_name_real_commands(self):  # TK-01, TK-02
        sys.path.insert(0, str(ROOT)); from sdem import home
        cat = json.loads(subprocess.run([sys.executable, '-m', 'sdem', 'commands', '--json'], capture_output=True, text=True, env=ENV, cwd=self.tmp).stdout)['commands']
        self.assertEqual([c for c, _, _ in home.TASKS], ['Explore', 'Design', 'Connect', 'Analyse', 'Govern', 'Operate'])
        for _, _, rows in home.TASKS:
            for r in rows:
                self.assertIn(r[5], home.EFFECT)
                for part in re.split(r'\s+·\s+|\s+\|\s+(?=sdem)|, then |\s+—\s+or\s+', r[1]):
                    m = re.match(r'sdem ([a-z-]+)(?: ([a-z-]+))?', part.strip())
                    if not m: continue
                    name = f'{m.group(1)} {m.group(2)}' if m.group(2) and f'{m.group(1)} {m.group(2)}' in cat else m.group(1)
                    self.assertIn(name, cat, r[0])
                    opts = {o['name'] for o in cat[name].get('options', [])} | {'--json', '--dry-run', '--limit', '--workspace', '-o', '--out'}
                    for o in re.findall(r'(--[a-z-]+)', part): self.assertIn(o, opts, f'{r[0]}: {name} {o}')
        guide = (ROOT / 'docs' / 'sdem-workbench-user-guide.md').read_text(encoding='utf-8')
        for _, _, rows in home.TASKS:
            for r in rows: self.assertIn(f'| {r[0]} |', guide)                                                    # the guide's §4b and Home show the same list
        self.workspace('workspaces/p'); sdem('home', '--root', self.tmp / 'workspaces', '-o', self.tmp / 'site', cwd=self.tmp)
        self.assertEqual(len(page_data(self.tmp / 'site' / 'index.html')['tasks']), 6)

    def test_special_characters_are_encoded_and_escaped(self):  # safe URLs and data
        name = 'a #1 & 50% ü' + ('' if os.name == 'nt' else ' <b> "q"')   # Windows forbids < > " in folder names
        ws = self.workspace(f'workspaces/{name}')
        out = self.tmp / 'site'; sdem('home', '--root', self.tmp / 'workspaces', '-o', out, cwd=self.tmp)
        index = out / 'index.html'; p = page_data(index)['projects'][0]
        for ch in '#<%" ': self.assertNotIn(ch, p['graph']['href'].replace('%23', '').replace('%3C', '').replace('%25', '').replace('%22', '').replace('%20', ''))   # encoded
        self.journey(index)
        self.assertEqual(index.read_text().count('</script>'), index.read_text().count('<script'))                # no data closes the script early

    def test_documented_invocations_still_work(self):  # test 11: build, new, upgrade check as documented
        ws = self.workspace('workspaces/payments', build=False)
        sdem('build', ws / 'a1-business.json', ws / 'a2-service-domain.json', ws / 'a3-application.json', ws / 'a4-technology.json', ws / 'mappings.json', '-o', self.tmp / 'g', cwd=self.tmp)
        sdem('new', '--workspace', self.tmp / 'empty', '--person', 'jane', cwd=self.tmp)
        sdem('upgrade', 'check', '--workspace', ws, '--repo', self.tmp, '--from', '0.17.0', cwd=self.tmp)


def guide_steps():
    """The walkthrough in docs/sdem-workbench-user-guide.md §4a, as a reader copies it: [('file', name, text) | ('cmd', argv)], in order."""
    guide = (ROOT / 'docs' / 'sdem-workbench-user-guide.md').read_text(encoding='utf-8')
    sec = guide[guide.index('### Step by step — the bundled Payments example'):guide.index("### The dashboard's tabs")]
    steps = []
    for block in re.findall(r'```bash\n(.*?)```', sec, flags=re.S):
        lines = [l.strip() for l in block.splitlines()]
        i = 0
        while i < len(lines):
            l = re.sub(r'\s+#.*$', '', lines[i]).strip(); i += 1
            m = re.match(r"cat > (\S+) <<'EOF'", l)
            if m:
                body = []
                while lines[i] != 'EOF': body.append(lines[i]); i += 1
                i += 1; steps.append(('file', m.group(1), '\n'.join(body) + '\n')); continue
            if l.startswith('sdem '):
                argv = [a.replace('<you>', 'jane.architect').replace('<document>', 'DD-1') for a in __import__('shlex').split(l)]
                steps.append(('cmd', argv))
    return steps

if __name__ == '__main__':
    unittest.main()
