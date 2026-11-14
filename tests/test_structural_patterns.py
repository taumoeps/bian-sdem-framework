"""Reference-architecture patterns as structures — roles, connectors, zones — extracted from the organisation's diagrams (draw.io, Visio,
PlantUML, Mermaid), checked against the metamodel, filled from a design and drawn over it (docs/design/sdem-profile-spec.md PR-21…PR-31;
the owner's decisions S1–S6, 2026-11-10). Synthetic: the made-up bank in examples/profiles/, its diagrams in examples/profiles/patterns/diagrams/."""
import base64, copy, datetime, hashlib, json, os, re, shutil, subprocess, sys, tempfile, unittest, urllib.parse, zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem import comply, exceptions, patterns, profile  # noqa: E402
from sdem.metamodel import Metamodel  # noqa: E402

AS_OF = datetime.date(2026, 11, 10)
ENV = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', ''), 'SDEM_AS_OF': AS_OF.isoformat()}
PID = 'PAT-SECURE-API-EDGE'
FORMATS = ('drawio', 'vsdx', 'puml', 'mmd')


def _j(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def _w(p, d): Path(p).write_text(json.dumps(d, indent=2), encoding='utf-8')


def sdem(*args, cwd):
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], capture_output=True, text=True, env=ENV, cwd=cwd)
    return r.returncode, r.stdout + r.stderr


def digest():
    h = hashlib.sha256()
    for p in sorted((ROOT / 'metamodel').rglob('*')):
        if p.is_file(): h.update(p.read_bytes())
    return h.hexdigest()


def shape_of(d):
    """What a pattern's structure says, without where it was drawn from."""
    S = d['structure']
    return {'anchor': S['anchor'],
            'roles': sorted((r['id'], r['type'], r.get('min', 1), r.get('max', 1), r.get('zone')) for r in S['roles']),
            'connectors': sorted((c['from'], c['to'], c.get('kind') or c.get('relationship'), c.get('min', 1)) for c in S['connectors']),
            'zones': sorted((z['id'], json.dumps(z.get('check'), sort_keys=True), z.get('entity')) for z in S['zones'])}


class Base(unittest.TestCase):
    def setUp(self):
        self.addCleanup(profile.deactivate)
        self.digest = digest()
        self.tmp = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, self.tmp, True)
        shutil.copytree(ROOT / 'examples' / 'profiles', self.tmp / 'profiles')
        self.diagrams = self.tmp / 'profiles' / 'patterns' / 'diagrams'
        self.merged = profile.resolve(self.tmp / 'profiles' / 'bank-with-standards.json')
        self.base = Metamodel.base()

    def tearDown(self):
        self.assertEqual(digest(), self.digest, "SDEM's metamodel files changed")

    def extract(self, path, anchor='Application', merged=None):
        return patterns.extract(path, merged or self.merged, self.base, {'id': PID, 'title': 'Secure API edge', 'version': '1.0', 'owner': 'security architecture'}, anchor)


class Extraction(Base):
    def test_the_four_formats_give_one_pattern(self):                                  # PR-27, PR-28
        approved = shape_of(_j(self.tmp / 'profiles' / 'patterns' / 'example-secure-api-edge.json'))
        for f in FORMATS:
            draft, rep = self.extract(self.diagrams / f'secure-api-edge.{f}')
            self.assertTrue(rep['clean'], (f, rep))
            self.assertEqual(shape_of(draft), approved, f)
            self.assertTrue(all(r['source'].startswith('secure-api-edge.') for r in draft['structure']['roles']), f)   # each part cites its shape
        self.assertEqual(approved['roles'][1], ('application', 'A3.ApplicationComponent', 1, 1, None))
        self.assertIn(('container-platform', 'A4.SystemSoftware', 1, None, 'restricted-zone'), approved['roles'])     # (1..n)
        self.assertIn(('private-network', 'A4.CommunicationNetwork', 0, 1, 'restricted-zone'), approved['roles'])     # (optional)
        self.assertIn(('application', 'container-platform', 'DEPLOYED_ON', 1), approved['connectors'])

    def test_a_compressed_drawio_file_reads_the_same(self):
        src = (self.diagrams / 'secure-api-edge.drawio').read_text(encoding='utf-8')
        model = re.search(r'<mxGraphModel.*</mxGraphModel>', src, re.S).group(0)
        c = zlib.compressobj(9, zlib.DEFLATED, -15); packed = c.compress(urllib.parse.quote(model).encode()) + c.flush()
        z = self.tmp / 'compressed.drawio'
        z.write_text(re.sub(r'<mxGraphModel.*</mxGraphModel>', base64.b64encode(packed).decode(), src, flags=re.S), encoding='utf-8')
        self.assertEqual(shape_of(self.extract(z)[0]), shape_of(self.extract(self.diagrams / 'secure-api-edge.drawio')[0]))

    def test_the_same_diagram_gives_the_same_draft(self):                               # deterministic
        a = json.dumps(self.extract(self.diagrams / 'secure-api-edge.vsdx')[0], sort_keys=True)
        self.assertEqual(a, json.dumps(self.extract(self.diagrams / 'secure-api-edge.vsdx')[0], sort_keys=True))

    def test_nothing_is_guessed(self):                                                   # PR-28, PR-29
        mmd = self.tmp / 'more.mmd'
        mmd.write_text((self.diagrams / 'secure-api-edge.mmd').read_text(encoding='utf-8').replace(
            '  sec(["Secrets service (optional)"]):::tech', '  sec(["Secrets service (optional)"]):::tech\n  mf["Mainframe"]\n  app -->|calls| mf\n  this is not mermaid'), encoding='utf-8')
        draft, rep = self.extract(mmd)
        self.assertFalse(rep['clean'])
        self.assertEqual([u['label'] for u in rep['unmapped_shapes']], ['Mainframe'])
        self.assertTrue(any('not a mapped part' in u['why'] for u in rep['unmapped_connectors']))
        self.assertEqual([x['line'] for x in rep['ignored_lines']], ['this is not mermaid'])
        self.assertNotIn('mainframe', {r['id'] for r in draft['structure']['roles']})

    def test_a_link_the_metamodel_does_not_allow_is_refused(self):                     # PR-22, PR-29
        puml = self.tmp / 'bad.puml'
        puml.write_text((self.diagrams / 'secure-api-edge.puml').read_text(encoding='utf-8').replace('Rel_Serving_Up(sec, k8s, "serves")', 'Rel_Assignment(sec, k8s, "assigned to")'), encoding='utf-8')
        draft, rep = self.extract(puml)
        self.assertFalse(rep['clean'])
        self.assertTrue(any('metamodel does not allow' in r['why'] for r in rep['refused_connectors']), rep['refused_connectors'])
        self.assertEqual(len(draft['structure']['connectors']), 3)

    def test_an_anchor_is_named_not_guessed(self):
        draft, rep = self.extract(self.diagrams / 'secure-api-edge.drawio', anchor=None)
        self.assertIsNone(draft['structure']['anchor']); self.assertFalse(rep['clean'])
        self.assertTrue(any('no anchor' in n for n in rep['notes']))

    def test_a_changed_diagram_shows_what_changed(self):                                # PR-31
        approved = _j(self.tmp / 'profiles' / 'patterns' / 'example-secure-api-edge.json')
        self.assertTrue(patterns.compare(approved, self.extract(self.diagrams / 'secure-api-edge.mmd')[0])['unchanged'])
        mmd = self.tmp / 'v2.mmd'
        mmd.write_text((self.diagrams / 'secure-api-edge.mmd').read_text(encoding='utf-8')
                       .replace('    net["Private network (optional)"]:::tech\n', '').replace('  k8s ---|connected to| net\n', '')
                       .replace('Container platform (1..n)', 'Container platform (1..2)'), encoding='utf-8')
        ch = patterns.compare(approved, self.extract(mmd)[0])
        self.assertFalse(ch['unchanged'])
        self.assertEqual(ch['roles']['removed'], ['private-network'])
        self.assertEqual(ch['connectors']['removed'], ['container-platform → private-network (association)'])
        self.assertEqual(ch['roles']['changed'][0]['part'], 'container-platform')

    def test_the_command_writes_a_draft_only_when_asked(self):                          # PR-30
        out = self.tmp / 'draft.json'
        code, txt = sdem('pattern', 'extract', '--from', self.diagrams / 'secure-api-edge.vsdx', '--profile', self.tmp / 'profiles' / 'bank-with-standards.json',
                         '--id', PID, '--owner', 'security architecture', '--anchor', 'Application', '--out', out, '--dry-run', cwd=self.tmp)
        self.assertEqual(code, 0, txt); self.assertFalse(out.exists())
        code, txt = sdem('pattern', 'extract', '--from', self.diagrams / 'secure-api-edge.vsdx', '--profile', self.tmp / 'profiles' / 'bank-with-standards.json',
                         '--id', PID, '--owner', 'security architecture', '--anchor', 'Application', '--out', out, '--compare', self.tmp / 'profiles' / 'patterns' / 'example-secure-api-edge.json', cwd=self.tmp)
        self.assertEqual(code, 0, txt); self.assertTrue(out.exists()); self.assertIn('no change', txt); self.assertIn('the pattern owner reviews it', txt)
        code, txt = sdem('pattern', 'extract', '--from', self.tmp / 'x.png', '--profile', self.tmp / 'profiles' / 'bank-with-standards.json', '--id', PID, '--owner', 'o', cwd=self.tmp)
        self.assertEqual(code, 2); self.assertIn('draw.io (.drawio), Visio (.vsdx), PlantUML (.puml) and Mermaid', txt)


class ProfileCheck(Base):
    def issues(self, edit):
        p = self.tmp / 'profiles' / 'patterns' / 'example-secure-api-edge.json'; d = _j(p); edit(d['structure']); _w(p, d)
        return profile.check(profile.resolve(self.tmp / 'profiles' / 'bank-with-structures.json'), self.base)

    def test_the_example_is_clean(self):
        self.assertEqual(profile.check(profile.resolve(self.tmp / 'profiles' / 'bank-with-structures.json'), self.base), [])

    def test_a_pattern_never_adds_a_link_the_metamodel_does_not_allow(self):           # PR-22
        def edit(S): next(c for c in S['connectors'] if c['id'] == 'C4')['kind'] = 'assignment'
        self.assertTrue(any('connector C4' in i and 'never adds a link' in i for i in self.issues(edit)))
        def across(S): next(c for c in S['connectors'] if c['id'] == 'C1').update(kind=None, relationship='DEPLOYED_ON')
        self.assertTrue(any('connector C1' in i for i in self.issues(across)))

    def test_roles_types_anchor_and_reach_are_checked(self):                            # PR-21
        self.assertTrue(any('NOT.A.Type' in i for i in self.issues(lambda S: S['roles'][0].update(type='NOT.A.Type'))))
        self.assertTrue(any('anchor' in i for i in self.issues(lambda S: S.update(anchor='nobody'))))
        def lonely(S): S['roles'].append({'id': 'island', 'type': 'A4.Node'})
        self.assertTrue(any('island is not connected' in i for i in self.issues(lonely)))
        self.assertTrue(any("requires 'no_such'" in i for i in self.issues(lambda S: S['roles'][1].update(require=['no_such']))))


class Design(Base):
    def setUp(self):
        super().setUp()
        self.ws = self.tmp / 'ws'
        shutil.copytree(ROOT / 'examples' / 'payment-initiation', self.ws, ignore=shutil.ignore_patterns('graph', 'm1-*'))
        _w(self.ws / 'sdem-profile.json', {'format': 'sdem-profile/1', 'name': 'payments', 'version': 1, 'extends': '../profiles/bank-with-structures.json'})
        a3 = _j(self.ws / 'a3-application.json')
        for i in a3['instances']:
            if i['type'] == 'A3.ApplicationComponent': i.setdefault('attributes', {}).update(owner='ROLE-PAY-OFFICER', risk_tier='2')
            if i['id'] == 'APP-PAY-HUB': i['attributes'].update(risk_tier='1', exposure='external', authentication='oauth2-mtls', conforms_to=[PID])
        a3['instances'].append({'id': 'GW-PAY-EDGE', 'type': 'BANK.A3.APIGateway', 'version': '1.0', 'name': 'Payments API gateway', 'lifecycle_status': 'active',
                                'attributes': {'owner': 'ROLE-PAY-OFFICER', 'risk_tier': '2'}})
        a3['relationships'] += [{'source': 'GW-PAY-EDGE', 'kind': 'flow', 'target': 'APP-PAY-HUB'}, {'source': 'GW-PAY-EDGE', 'kind': 'composition', 'target': 'APP-PAY-HUB'}]
        _w(self.ws / 'a3-application.json', a3)
        self.set4('INF-K8S-PAY-PROD', environment='production', dr_tier='3', dr_region='region-a', replication_mode='async', network_zone='restricted',
                  monitoring=True, encryption_in_transit='tls1.3', end_of_support='2028-06-30')
        self.set4('INF-K8S-PAY-UAT', network_zone='restricted', monitoring=True, encryption_in_transit='tls1.3', end_of_support='2028-06-30')
        self.set4('NET-PAY-PRIVATE', network_zone='restricted')
        d = _j(self.ws / 'a4-technology.json')   # the scenario starts with no technology service serving a platform; tests add one
        d['relationships'] = [r for r in d['relationships'] if not (r['kind'] == 'serving' and r['source'].startswith('TS-'))]
        _w(self.ws / 'a4-technology.json', d)

    def set4(self, rid, **kv):
        d = _j(self.ws / 'a4-technology.json')
        for i in d['instances']:
            if i['id'] == rid: i.setdefault('attributes', {}).update(kv)
        _w(self.ws / 'a4-technology.json', d)

    def edit3(self, fn):
        d = _j(self.ws / 'a3-application.json'); fn(d); _w(self.ws / 'a3-application.json', d)


class Evaluation(Design):
    def parts(self, record='APP-PAY-HUB'):
        datasets, maps, mm, _ = comply.workspace_data(self.ws)
        found, bindings = patterns.evaluate(datasets, maps, mm, profile.structures(), profile.exceptions(), AS_OF)
        return {f['part']['id']: (f['outcome'], f['detail']) for f in found if f['record'] == record}, next((b['roles'] for b in bindings if b['anchor'] == record), None)

    def test_a_design_that_follows_the_pattern(self):                                  # PR-23, PR-24
        out, binding = self.parts()
        self.assertEqual(binding, {'api-gateway': ['GW-PAY-EDGE'], 'application': ['APP-PAY-HUB'], 'container-platform': ['INF-K8S-PAY-PROD', 'INF-K8S-PAY-UAT'],
                                   'private-network': ['NET-PAY-PRIVATE'], 'secrets-service': []})
        for part in ('api-gateway', 'application', 'container-platform', 'private-network', 'C1', 'C2', 'C3'): self.assertEqual(out[part][0], 'compliant', (part, out[part]))
        self.assertEqual(out['secrets-service'][0], 'not_applicable')                   # optional, and not in the design
        self.assertEqual(sdem('check', '--workspace', self.ws, cwd=self.tmp)[0], 0)

    def test_the_pattern_applies_only_where_a_record_says_it_follows_it(self):
        self.assertIsNone(self.parts('CMP-PAY-EXEC')[1])

    def test_a_missing_part(self):
        self.edit3(lambda d: d.update(relationships=[r for r in d['relationships'] if not (r['source'] == 'GW-PAY-EDGE' and r['kind'] == 'flow')]))
        out, _ = self.parts()
        self.assertEqual(out['api-gateway'][0], 'non_compliant'); self.assertIn('no API Gateway', out['api-gateway'][1])
        self.assertEqual(out['C1'][0], 'not_applicable')                                  # reported once, under the part
        code, txt = sdem('check', '--workspace', self.ws, cwd=self.tmp)
        self.assertEqual(code, 1); self.assertIn(f'{PID}/api-gateway', txt)

    def test_a_part_in_the_wrong_zone(self):
        self.set4('INF-K8S-PAY-UAT', network_zone='dmz')
        out, _ = self.parts()
        self.assertEqual(out['container-platform'][0], 'non_compliant')
        self.assertIn("INF-K8S-PAY-UAT: network_zone is 'dmz' — must be in ['restricted'] (Restricted zone)", out['container-platform'][1])

    def test_a_zone_checked_against_the_zone_records(self):                            # PR-13a: where a part is placed (RA4-38), not an attribute
        import copy
        comply.workspace_data(self.ws)   # activates the workspace's profile
        structs = copy.deepcopy(profile.structures())
        for st in structs:
            for z in st['structure'].get('zones', []):
                if z['id'] == next(r['zone'] for r in st['structure']['roles'] if r['id'] == 'container-platform'): z.pop('check', None); z['zone_kind'] = 'private'
        def parts():
            datasets, maps, mm, _ = comply.workspace_data(self.ws)
            found, _ = patterns.evaluate(datasets, maps, mm, structs, profile.exceptions(), AS_OF)
            return {f['part']['id']: (f['outcome'], f['detail']) for f in found if f['record'] == 'APP-PAY-HUB'}
        self.assertEqual(parts()['container-platform'][0], 'compliant')                 # both clusters sit in the payments private network
        d = _j(self.ws / 'a4-technology.json')
        for r in d['relationships']:
            if r['kind'] == 'aggregation' and r['target'] == 'INF-K8S-PAY-UAT' and r['source'] == 'ZONE-PAY-PRIVATE': r['source'] = 'ZONE-PAY-INTERNAL'
        _w(self.ws / 'a4-technology.json', d)
        out = parts()['container-platform']
        self.assertEqual(out[0], 'non_compliant'); self.assertIn('INF-K8S-PAY-UAT: is in ZONE-PAY-INTERNAL (internal) — must be in a private zone', out[1])

    def test_only_approved_links_fill_a_part(self):                                     # PR-16, PR-22
        reg = _j(self.ws / 'mappings.json')
        for m in reg['mappings']:
            if m['mapping_id'] in ('PAY-108', 'PAY-113'): m['status'] = 'proposed'
        _w(self.ws / 'mappings.json', reg)
        out, binding = self.parts()
        self.assertEqual(binding['container-platform'], []); self.assertEqual(out['container-platform'][0], 'non_compliant')
        self.assertEqual(out['private-network'][0], 'not_applicable')                    # optional, and not reached

    def test_two_candidates_are_never_guessed_a_named_one_wins(self):                   # PR-23
        def second(d):
            d['instances'].append({'id': 'GW-PAY-PARTNER', 'type': 'BANK.A3.APIGateway', 'version': '1.0', 'name': 'Partner gateway', 'lifecycle_status': 'active',
                                   'attributes': {'owner': 'ROLE-PAY-OFFICER', 'risk_tier': '2'}})
            d['relationships'].append({'source': 'GW-PAY-PARTNER', 'kind': 'flow', 'target': 'APP-PAY-HUB'})
        self.edit3(second)
        out, _ = self.parts()
        self.assertEqual(out['api-gateway'][0], 'unresolved'); self.assertIn('ambiguous: GW-PAY-EDGE or GW-PAY-PARTNER', out['api-gateway'][1])
        def name(d):
            next(i for i in d['instances'] if i['id'] == 'GW-PAY-PARTNER')['attributes']['conforms_to'] = [f'{PID}#api-gateway']
        self.edit3(name)
        out, binding = self.parts()
        self.assertEqual(binding['api-gateway'], ['GW-PAY-PARTNER']); self.assertEqual(out['api-gateway'][0], 'compliant')

    def test_an_optional_part_when_it_is_there(self):
        reg = _j(self.ws / 'a4-technology.json')
        reg['relationships'].append({'source': 'TS-SECRETS', 'kind': 'serving', 'target': 'INF-K8S-PAY-PROD'}); _w(self.ws / 'a4-technology.json', reg)
        out, binding = self.parts()
        self.assertEqual(binding['secrets-service'], ['TS-SECRETS']); self.assertEqual(out['C4'][0], 'compliant')

    def test_a_person_s_exception_to_one_part(self):                                    # PR-18, PR-24
        self.set4('INF-K8S-PAY-UAT', network_zone='dmz')
        exceptions.grant(self.ws, f'{PID}/container-platform', ['APP-PAY-HUB'], 'UAT moves to the restricted zone in Q1', '2027-03-31', 'jane.architect', as_of=AS_OF)
        self.assertEqual(self.parts()[0]['container-platform'][0], 'exception_approved')
        code, txt = sdem('check', '--workspace', self.ws, cwd=self.tmp)
        self.assertNotIn(f'{PID}/container-platform', txt)
        self.assertIn('NET-07', txt)   # the bank's network standard still holds: the exception names one part of one pattern

    def test_comply_reports_the_pattern_and_its_binding(self):                          # PR-19, PR-24
        self.set4('INF-K8S-PAY-UAT', network_zone='dmz')
        r = comply.collect(self.ws, AS_OF)
        self.assertTrue(any(g['id'] == PID and g['non_compliant'] == 1 for g in r['groups']))
        self.assertTrue(any(b['pattern'] == PID and b['anchor'] == 'APP-PAY-HUB' for b in r['bindings']))
        code, txt = sdem('comply', '--workspace', self.ws, cwd=self.tmp)
        self.assertEqual(code, 1); self.assertIn(f'NOT MET    {PID}/container-platform', txt)


class Drawing(Design):
    def test_the_pattern_and_the_design_over_it(self):                                  # PR-25
        code, svg = sdem('pattern', 'draw', '--file', self.tmp / 'profiles' / 'patterns' / 'example-secure-api-edge.json', '--profile', self.tmp / 'profiles' / 'bank-with-structures.json', cwd=self.tmp)
        self.assertEqual(code, 0, svg)
        for label in ('API Gateway', 'Application', 'Container platform', 'Restricted zone', 'routes requests to', 'deployed on'): self.assertIn(label, svg)
        self.edit3(lambda d: d.update(relationships=[r for r in d['relationships'] if not (r['source'] == 'GW-PAY-EDGE' and r['kind'] == 'flow')]))
        out = self.tmp / 'over.html'
        code, txt = sdem('pattern', 'draw', '--workspace', self.ws, '--id', PID, '--anchor', 'APP-PAY-HUB', '--format', 'html', '-o', out, cwd=self.tmp)
        self.assertEqual(code, 0, txt)
        page = out.read_text(encoding='utf-8')
        self.assertIn('pt-missing', page); self.assertIn('✗ missing', page); self.assertIn('INF-K8S-PAY-PROD, INF-K8S-PAY-UAT', page)
        self.assertEqual(sdem('pattern', 'draw', '--workspace', self.ws, '--id', PID, '--anchor', 'CMP-PAY-EXEC', cwd=self.tmp)[0], 2)

    def test_a_pattern_without_a_drawing_position_is_laid_out(self):                     # PlantUML and Mermaid carry no positions
        draft, _ = self.extract(self.diagrams / 'secure-api-edge.puml')
        self.assertNotIn('layout', draft['structure'])
        lv = patterns._level_of(self.merged, self.base)
        svg = patterns.draw({'pattern': draft['pattern'], 'structure': draft['structure']}, lv)
        self.assertEqual(svg.count('class="dv-node'), 5); self.assertIn('DMZ', svg)


if __name__ == '__main__':
    unittest.main()
