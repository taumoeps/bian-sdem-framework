"""Step 4 of 0.20 — the Data layer (docs/design/sdem-data-layer-spec.md, DL-01…DL-24). 4b: a design's files store ids or 0.19's
names; SDEM reads and writes both through one boundary (sdem/identity.py: load, loads, for_file), and works in the names a person reads."""
import json, os, re, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'scripts' / 'golden'))
ENV = {**os.environ, 'PYTHONPATH': str(ROOT), 'PYTHONIOENCODING': 'utf-8'}
OLD = re.compile(r'"(A[1-4]\.[A-Z][A-Za-z]+)"')


def sdem(*args):
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], capture_output=True, text=True, encoding='utf-8', env=ENV, cwd=ROOT)
    assert r.returncode == 0, f"sdem {' '.join(map(str, args))}: exit {r.returncode}\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}"
    return r.stdout


def no_sha(x, k=None):
    if isinstance(x, dict): return {kk: no_sha(v, kk) for kk, v in x.items()}
    if isinstance(x, list): return sorted(map(str, x)) if k == 'would_write' else [no_sha(v, k) for v in x]   # a migrated workspace's files sort differently
    return '<sha>' if k in ('sha256', 'export_sha256') else x


# P2 (DL-20): 0.19's 32 answers, translated to a migrated workspace's numbering (with BIAN: Data A3, Application A4, Technology A5),
# against the answers of the golden workspaces migrated with sdem migrate --to 0.20. These differences — and only these — are the
# Data layer itself; each is named with its reason. Commands without a workspace keep 0.19's form and are compared untranslated.
NAMED = {
    'check': {'.output.report.level A3 (*)': 'the Data layer is checked on its own', '.output.warnings.level A4 (*)': "warnings about data records move to Data's level"},
    'build': {'.output.inputs': 'data.json is read too', '.output.outputs': 'data.graph.json is written too', '.output.stack': 'the store records the layers it was built with (DL-12)',
              '.output.warnings': "warnings about data records move to Data's level", '.output.metamodel_version': 'metamodel 0.18.0 (the owner, 2026-11-21) — 0.20 itself, not the Data layer'},
    'status': {'.output.layers': 'five layers', '.output.connections.by_status.approved': "0.19's access links are approved links between Data and Application (DL-13)",
               '.output.connections.links': 'the same', '.output.counts.warnings': "warnings about data records move to Data's level", '.output.warnings': 'the same',
               '.output.sources.links_without_source': 'the access links left the layer file (DL-13)',
               '.output.next': "BO-06 (the owner, 2026-11-22): a design with BIAN service domains and no business object is told — sdem bian objects suggest"},
    'document-A3': {'.output.sections': 'Application no longer holds the data entities', '.output.summary.*': 'the same', '.output.gaps.no_connection': 'the same'},
    'comply': {'.output.findings[].layer': "findings about data records are in Data's layer", '.output.findings[].detail': "'access link(s)' is 'ACCESSED_BY link(s)' (DL-04)"},
    'aid': {'.output.added.A3': "inferred data records are added to Data", '.output.added.A4': 'the same', '.output.would_write[]': 'data.json among the files, in another order'},
    'trace': {'.output.items[].chains': 'the access links between Data and Application add chains — and the full trace (FT-D1, 2026-11-22) adds the chains through a record\'s whole', '.output.items[].reach.A3': 'trace reaches Data', '.output.items[].reach.A5': 'and through it'},
    'impact': {'.output.coverage.A3': 'impact is seen on Data', '.output.coverage.A4.*': "Application's coverage without the data records"},
    'types': {'.output.types': "Application's types without Data's (DL-02) — sdem types A4 lists Application in the 0.20 stack (DL-D9)"},
}


def named(fname, path):
    kind = next((k for k in NAMED if fname.split('__')[-1].startswith(k) or fname.startswith(k + '__')), None)
    if not kind: return None
    import fnmatch
    p = re.sub(r'\[\d+\]', '[]', path)
    return next((why for pat, why in NAMED[kind].items() if fnmatch.fnmatchcase(p, pat) or fnmatch.fnmatchcase(p, pat.replace('[]', '[[]]'))), None)


def tr(x):
    """A 0.19 answer as a migrated workspace with BIAN numbers it: data types stay A3; other A3 are A4, A4 are A5."""
    data = {'A3.DataEntity', 'A3.DataAttribute'}
    def s(v):
        v = re.sub(r'(?<![A-Za-z0-9_.\-])A([34])\.([A-Z][A-Za-z]+)', lambda m: m.group(0) if m.group(0) in data else f'A{int(m.group(1)) + 1}.{m.group(2)}', v)
        return re.sub(r'(?<![A-Za-z0-9_.\-])A([34])(?![A-Za-z0-9_.\-])', lambda m: f'A{int(m.group(1)) + 1}', v)
    if isinstance(x, dict): return {s(k): tr(v) for k, v in x.items()}
    if isinstance(x, list): return [tr(v) for v in x]
    return s(x) if isinstance(x, str) else x


def diffs(a, b, p=''):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            if k not in a or k not in b: yield f'{p}.{k}'
            else: yield from diffs(a[k], b[k], f'{p}.{k}')
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (u, v) in enumerate(zip(a, b)): yield from diffs(u, v, f'{p}[{i}]')
    elif a != b and not p.endswith('sha256'): yield p


class Boundary(unittest.TestCase):   # DL-10…DL-13, DL-20
    def test_p2_the_32_answers_of_0_19_translated_differ_only_where_named(self):
        out = Path(tempfile.mkdtemp())
        try:
            subprocess.run([sys.executable, str(ROOT / 'scripts' / 'golden' / 'capture.py'), str(out)], check=True, capture_output=True,
                           env={**ENV, 'SDEM_GOLDEN_P2': '1'}, cwd=ROOT)
            gold = ROOT / 'tests' / 'golden' / '0.19'
            unnamed = {}
            for f in sorted(gold.glob('*.json')):
                raw = json.loads(f.read_text(encoding='utf-8'))
                a = raw if f.name.startswith(('datasets__', 'bian__search')) else tr(raw)   # 0.19's files given directly keep 0.19's form; sdem types shows 0.20's (DL-D9)
                b = json.loads((out / f.name).read_text(encoding='utf-8'))
                left = [p for p in diffs(a, b) if not named(f.name.replace('.json', ''), p)]
                if left: unnamed[f.name] = left[:5]
            self.assertEqual(unnamed, {}, 'a difference from 0.19 the Data layer does not explain — name it (DL-20) or fix it')
        finally:
            shutil.rmtree(out, ignore_errors=True)

    def test_a_migrated_workspace_is_never_written_with_0_19_names(self):   # every writer through the boundary (DL-11)
        tmp = Path(tempfile.mkdtemp()); w = tmp / 'ws'
        try:
            sdem('new', '--workspace', w, '--person', 'dl.check', '--example', 'payment-initiation', '--form', '0.19')
            sdem('migrate', '--workspace', w, '--person', 'dl.check', '--to', '0.20')
            sdem('bian', 'add', 'Card Authorization', '--workspace', w, '--person', 'dl.check')
            sdem('aid', '--workspace', w, '--person', 'dl.check')
            sdem('link', '--workspace', w, '--out', w / 'links')
            sdem('check', '--workspace', w)
            left = {str(f.relative_to(w)): OLD.findall(f.read_text(encoding='utf-8'))[:2] for f in w.rglob('*.json')
                    if not f.name.endswith('.graph.json') and 'graph' not in f.parts and '.sdem-backup-0.20' not in f.parts and OLD.search(f.read_text(encoding='utf-8'))}
            self.assertEqual(left, {})
            self.assertIn('"data.DataEntity"', (w / 'data.json').read_text(encoding='utf-8'))   # DL-01, DL-10
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_migrate_then_roll_back_restores_every_byte(self):   # DL-12
        import filecmp
        tmp = Path(tempfile.mkdtemp()); w = tmp / 'ws'
        try:
            sdem('new', '--workspace', w, '--person', 'dl.check', '--example', 'payment-initiation', '--form', '0.19')
            shutil.copytree(w, tmp / 'orig')
            sdem('migrate', '--workspace', w, '--person', 'dl.check', '--to', '0.20')
            self.assertTrue((w / 'data.json').exists()); self.assertFalse((w / 'a3-application.json').exists())
            sdem('migrate', '--workspace', w, '--person', 'dl.check', '--rollback')
            cmp = filecmp.dircmp(tmp / 'orig', w)
            self.assertEqual((cmp.left_only, cmp.right_only, cmp.diff_files), ([], [], []))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_names_translate_both_ways(self):
        from sdem import identity as I
        doc = {'level': 'A3', 'instances': [{'type': 'A3.ApplicationComponent', 'id': 'X'}], 'layer': 'application'}
        ids = I.store_names(I.read_names(doc), True)
        self.assertEqual(ids, {'level': 'application', 'instances': [{'type': 'application.ApplicationComponent', 'id': 'X'}], 'layer': 'application'})
        self.assertEqual(I.read_names(ids), doc)   # 'layer' is ArchiMate's own word, never translated
        self.assertEqual(I.store_names(I.read_names(ids), False), doc)



class Reconciled(unittest.TestCase):   # DL-20: each example, 0.19 against 0.20 — the data, not only the answers
    def test_every_record_field_and_link_of_0_19_is_in_the_migrated_example(self):
        examples = sorted(p.name for p in (ROOT / 'examples' / '0.20').iterdir() if p.is_dir() and (ROOT / 'examples' / p.name).is_dir())
        self.assertIn('payment-initiation', examples)
        for name in examples:
            old, new = ROOT / 'examples' / name, ROOT / 'examples' / '0.20' / name
            if (old / 'sdem').is_dir(): old, new = old / 'sdem', new / 'sdem'   # payment-initiation-v3: its workspace beside the package it was taken in from
            with self.subTest(example=name): self.reconcile(old, new)

    def reconcile(self, old, new):
        from sdem import identity as I
        j = lambda f: json.loads(f.read_text(encoding='utf-8'))
        o_recs, o_rels = {}, set()
        for f in ('a1-business.json', 'a2-service-domain.json', 'a3-application.json', 'a4-technology.json'):
            if not (old / f).exists(): continue   # an example may lack a layer
            d = j(old / f)
            o_recs.update({r['id']: {**r, 'type': I.type_id(r['type'])} for r in d['instances']})
            o_rels |= {(r['source'], r.get('kind'), r['target']) for r in d.get('relationships', [])}
        n_recs, n_rels, where = {}, set(), {}
        for lid in ('business', 'bian', 'data', 'application', 'technology'):
            if not (new / f'{lid}.json').exists(): continue
            d = j(new / f'{lid}.json')
            for r in d['instances']: n_recs[r['id']] = r; where[r['id']] = lid
            n_rels |= {(r['source'], r.get('kind'), r['target']) for r in d.get('relationships', [])}
        self.assertEqual(n_recs, o_recs)   # the same records, every field, nothing lost or invented
        self.assertEqual({k for k in where if where[k] != n_recs[k]['type'].split('.')[0]}, set())   # each in its type's layer
        acc = {r for r in o_rels if r[1] == 'access' and o_recs[r[2]]['type'].startswith('data.')}
        self.assertEqual(n_rels, o_rels - acc)   # the links inside the layers, but access to data
        o_m, n_m = j(old / 'mappings.json')['mappings'], j(new / 'mappings.json')['mappings']
        self.assertEqual({(m['target']['id'], 'access', m['source']['id']) for m in n_m if m['relationship'] == 'ACCESSED_BY' and m['status'] == 'approved'}, acc)   # DL-13
        norm = lambda m: json.dumps({**m, 'source': {**m['source'], 'type': I.type_id(m['source']['type'])}, 'target': {**m['target'], 'type': I.type_id(m['target']['type'])}}, sort_keys=True)
        self.assertEqual({norm(m) for m in n_m if m['relationship'] != 'ACCESSED_BY'}, {norm(m) for m in o_m})   # every link between layers as it was
        if (old / 'requirements.json').exists():
            self.assertEqual([r['id'] for r in j(new / 'requirements.json')['requirements']], [r['id'] for r in j(old / 'requirements.json')['requirements']])


class NamedInEitherForm(unittest.TestCase):   # DL-25: a layer named in a change set or a profile means one layer, in either form
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp()); t = cls.tmp
        sdem('profile', 'example', '--out', t / 'profiles')
        for form in ('0.19', '0.20'):
            ws = t / form
            sdem('new', '--workspace', ws, '--person', 'steven', '--example', 'payment-initiation', '--form', '0.19')   # made in 0.19's form, whatever the default
            doc = json.loads((t / 'profiles' / 'strategy-and-sites-team.json').read_text()); doc['extends'] = '../profiles/bank-base.json'
            (ws / 'sdem-profile.json').write_text(json.dumps(doc))   # one organisation profile, in 0.19's numbering, for both
            sdem('profile', 'adopt', '--workspace', ws, '--person', 'steven', '--reason', 'team standard')
            f = ws / 'a3-application.json'; d = json.loads(f.read_text())   # what the bank's standard asks of an application (BANK-R01)
            for i in d['instances']:
                if i['type'] == 'A3.ApplicationComponent': i.setdefault('attributes', {}).setdefault('owner', 'ROLE-PAY-OFFICER'); i['attributes'].setdefault('risk_tier', '2')
            f.write_text(json.dumps(d))
            sdem('change', 'adopt', '--workspace', ws, '--layer', 'A3', '--person', 'steven', '--reason', 'bank risk tiers')
            if form == '0.20': sdem('migrate', '--to', '0.20', '--workspace', ws, '--person', 'steven')   # the profile is not changed

    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.tmp, ignore_errors=True)

    def run_sdem(self, *args):
        return subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], capture_output=True, text=True, encoding='utf-8', env=ENV, cwd=ROOT)

    def layers(self, form):
        return {l['level']: l['title'] for l in json.loads(self.run_sdem('status', '--workspace', self.tmp / form, '--json').stdout)['layers']}   # exits 1 while the design has gaps

    def test_the_profile_serves_both_forms_its_own_layer_renumbered(self):
        self.assertEqual(self.layers('0.19'), {'A0': 'A0 Strategy', 'A1': 'A1 Business', 'A2': 'A2 Service domain (BIAN)', 'A3': 'A3 Application',
                                               'A4': 'A4 Technology', 'A5': 'A5 Physical'})
        self.assertEqual(self.layers('0.20'), {'A0': 'A0 Strategy', 'A1': 'A1 Business', 'A2': 'A2 Service domain (BIAN)', 'A3': 'A3 Data',
                                               'A4': 'A4 Application', 'A5': 'A5 Technology', 'A6': 'A6 Physical'})
        cs = self.tmp / 'site.json'   # the own layer's agent keeps its name; the change set uses the workspace's number
        cs.write_text(json.dumps({'layer': 'A6', 'reason': 'a site', 'changes': [{'op': 'add', 'record': {'id': 'FAC-DC1', 'type': 'BANK.A5.Facility', 'version': '1',
                                  'name': 'Data centre 1', 'lifecycle_status': 'active', 'attributes': {'region': 'region-a'}}}]}))
        r = self.run_sdem('change', 'propose', cs, '--workspace', self.tmp / '0.20', '--agent', 'sdem-layer-a5', '--person', 'steven', '--dry-run', '--json')
        self.assertEqual(r.returncode, 0, r.stdout[-800:])

    def change(self, form, layer, agent):
        cs = self.tmp / f'cs-{form}-{layer}.json'
        f = self.tmp / form / ('a3-application.json' if form == '0.19' else 'application.json')
        rec = next(i for i in json.loads(f.read_text())['instances'] if i['id'] == 'APP-PAY-HUB')
        cs.write_text(json.dumps({'layer': layer, 'reason': 'a note', 'changes': [{'op': 'update', 'record': {**rec, 'description': 'The payments hub.'}}]}))
        return self.run_sdem('change', 'propose', cs, '--workspace', self.tmp / form, '--agent', agent, '--person', 'steven', '--dry-run', '--json')

    def test_a_change_set_names_its_layer_by_id_in_either_form(self):
        for form in ('0.19', '0.20'):
            r = self.change(form, 'application', 'sdem-a3-application'); self.assertEqual(r.returncode, 0, r.stdout[-800:])

    def test_an_old_number_is_never_re_read_and_the_refusal_says_why(self):
        r = self.change('0.20', 'A3', 'sdem-a3-application')
        self.assertNotEqual(r.returncode, 0)
        msg = json.loads(r.stdout)['error']['message']
        self.assertIn('A3 is Data', msg); self.assertIn("'application'", msg)
        self.assertEqual(self.change('0.20', 'A4', 'sdem-a3-application').returncode, 0)   # the workspace's own number


if __name__ == '__main__':
    unittest.main()
