"""Patterns for BIAN's functional patterns — Transact and Fulfill, shipped with SDEM (docs/design/sdem-completeness-design.md CPL-12…CPL-14).
What any service domain of that kind has in each layer of a complete design; they apply by the domain's functional pattern, so one file
covers every such domain. Synthetic data only."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem import aid_complete, comply, patterns, profile  # noqa: E402
from sdem.metamodel import Metamodel  # noqa: E402

T, F = 'sdem:sdem-pattern-bian-transact.json', 'sdem:sdem-pattern-bian-fulfill.json'
ENV = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}


def sdem(*args, cwd):
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], cwd=cwd, capture_output=True, text=True, env=ENV)
    return r.returncode, r.stdout, r.stderr


def _w(p, d): Path(p).write_text(json.dumps(d, indent=1), encoding='utf-8')
def rec(i, t, n, **a): return {'id': i, 'type': t, 'version': '1', 'name': n, 'lifecycle_status': 'active', 'attributes': a}
def link(s, k, t): return {'source': s, 'kind': k, 'target': t}


def design(fp='FP-TRANSACT'):
    """A made-up design around one service domain, with every part either pattern asks for."""
    return {
        'A1': ([rec('CAP-1', 'A1.BusinessCapability', 'Widget trading'), rec('PROC-1', 'A1.BusinessProcess', 'Trade a widget'),
                rec('SVC-1', 'A1.BusinessService', 'Widget service'), rec('PROD-1', 'A1.Product', 'Widget account')],
               [link('PROC-1', 'realization', 'SVC-1'), link('PROD-1', 'aggregation', 'SVC-1')]),
        'A2': ([rec('SD-W', 'A2.ServiceDomain', 'Widget Handling', asset_type='AT-W', functional_pattern=fp), rec('SG-W', 'A2.ServiceGroup', 'Widget group'),
                rec('SO-W', 'A2.ServiceOperation', 'Widget Handling: Initiate')], [link('SD-W', 'composition', 'SG-W'), link('SG-W', 'composition', 'SO-W')]),
        'A3': ([rec('APP-W', 'A3.ApplicationComponent', 'Widget engine'), rec('OP-W', 'A3.APIOperation', 'Create widget'), rec('DATA-W', 'A3.DataEntity', 'widgets')],
               [link('APP-W', 'access', 'DATA-W')]),
        'A4': ([rec('SYS-W', 'A4.SystemSoftware', 'Database'), rec('DEP-W', 'A4.Deployment', 'Widget engine — production')], []),
        'maps': [('CAP-1', 'SUPPORTED_BY', 'SD-W'), ('PROC-1', 'USES_DOMAIN', 'SD-W'), ('SD-W', 'REALIZED_BY', 'APP-W'), ('SO-W', 'IMPLEMENTED_BY', 'OP-W'),
                 ('DATA-W', 'STORED_IN', 'SYS-W'), ('APP-W', 'DEPLOYED_AS', 'DEP-W')]}


import sys as _s, pathlib as _pl; _s.path.insert(0, str(_pl.Path(__file__).resolve().parent)); from needs import bian as _needs_bian  # noqa: E402 — BX-15: tests that need sdem-bian

class Base(unittest.TestCase):
    def setUp(self):
        self.addCleanup(profile.deactivate)
        self.tmp = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, self.tmp, True); self.ws = self.tmp / 'ws'

    def build(self, d, includes=(T, F)):
        self.ws.mkdir(exist_ok=True)
        for layer, f in (('A1', 'a1-business.json'), ('A2', 'a2-service-domain.json'), ('A3', 'a3-application.json'), ('A4', 'a4-technology.json')):
            _w(self.ws / f, {'level': layer, 'model_id': f'T-{layer}', 'model_version': '1', 'metamodel_version': Metamodel.base().version, 'source_system': 'test',
                             'instances': d[layer][0], 'relationships': d[layer][1]})
        _w(self.ws / 'mappings.json', {'mappings': [{'mapping_id': f'M-{n}', 'source': {'id': s}, 'relationship': r, 'target': {'id': t}, 'status': 'approved'} for n, (s, r, t) in enumerate(d['maps'])]})
        _w(self.ws / 'sdem-profile.json', {'format': 'sdem-profile/1', 'name': 'test', 'version': 1, 'includes': list(includes)})

    def parts(self):
        datasets, maps, mm, _ = comply.workspace_data(self.ws)
        found, _ = patterns.evaluate(datasets, maps, mm, profile.structures(), profile.exceptions())
        return {(f['pattern']['id'], f['part']['id']): (f['outcome'], f['detail']) for f in found}


@_needs_bian
class Shipped(Base):
    def test_both_ship_and_pass_the_profile_check(self):   # CPL-12
        for name, pid, fp, artefact in ((T, 'PAT-BIAN-TRANSACT', 'FP-TRANSACT', 'transaction'), (F, 'PAT-BIAN-FULFILL', 'FP-FULFILL', 'arrangement')):
            d = json.loads(profile.shipped(name).read_text(encoding='utf-8'))
            self.assertEqual((d['pattern']['id'], d['pattern']['owner'], d['pattern']['severity']), (pid, 'SDEM', 'warning'))
            self.assertEqual(d['pattern']['applies_when'], {'entity': 'A2.ServiceDomain', 'when': {'functional_pattern': fp}})
            self.assertIn(artefact, json.dumps(d['structure']['roles']))   # said in BIAN's word for what the domain handles
            self.assertTrue(all(r.get('reasoning') for r in d['structure']['roles'] if r['id'] != d['structure']['anchor']))
        self.build(design()); self.assertEqual(profile.check(profile.resolve(self.ws / 'sdem-profile.json'), Metamodel.base()), [])

    def test_a_transact_domain_with_every_part_meets_it_and_fulfill_says_nothing(self):   # CPL-12
        self.build(design('FP-TRANSACT')); out = self.parts()
        self.assertEqual({k: v[0] for k, v in out.items() if v[0] != 'compliant'}, {})
        self.assertEqual({p for p, _ in out}, {'PAT-BIAN-TRANSACT'})
        self.assertEqual(sorted(part for _, part in out if not part.startswith('B')),
                         sorted(['domain', 'capability', 'process', 'service-groups', 'service-operations', 'api-operations', 'component', 'record', 'store', 'deployment']))

    def test_a_fulfill_domain_also_has_the_product_its_arrangements_are_for(self):   # CPL-13
        self.build(design('FP-FULFILL')); out = self.parts()
        self.assertEqual({k: v[0] for k, v in out.items() if v[0] != 'compliant'}, {})
        self.assertEqual({p for p, _ in out}, {'PAT-BIAN-FULFILL'}); self.assertIn(('PAT-BIAN-FULFILL', 'product'), out); self.assertIn(('PAT-BIAN-FULFILL', 'business-service'), out)
        d = design('FP-FULFILL'); d['A1'] = (d['A1'][0], [r for r in d['A1'][1] if r['source'] != 'PROD-1'])
        self.build(d); out = self.parts()
        self.assertEqual({k[1] for k, v in out.items() if v[0] != 'compliant' and v[0] != 'not_applicable'}, {'product'})

    def test_what_is_missing_is_named(self):   # CPL-12
        d = design(); d['maps'] = [m for m in d['maps'] if m[1] not in ('DEPLOYED_AS', 'IMPLEMENTED_BY')]
        self.build(d); out = self.parts()
        self.assertEqual({k[1] for k, v in out.items() if v[0] == 'non_compliant'}, {'deployment', 'api-operations'})
        self.assertIn('through B6 from SO-W', out[('PAT-BIAN-TRANSACT', 'api-operations')][1])

    def test_two_patterns_on_one_design_do_not_each_add_the_same_kind_of_part(self):   # CPL-14, AID-D06
        d = design(); d['A2'] = ([rec('SD-W', 'A2.ServiceDomain', 'Payment Order Initiation', asset_type='AT-W', functional_pattern='FP-TRANSACT')], [])
        d['A3'] = ([rec('APP-W', 'A3.ApplicationComponent', 'Engine')], []); d['A4'] = ([], []); d['maps'] = [('PROC-1', 'USES_DOMAIN', 'SD-W'), ('SD-W', 'REALIZED_BY', 'APP-W')]
        self.build(d, includes=('sdem:sdem-pattern-payment-initiation.json', T))
        datasets, maps, mm, _ = comply.workspace_data(self.ws)
        mark = lambda rule, why, frm, **k: {'rule': rule, 'reasoning': why, 'from': frm, **k}
        new, _, _, ids = aid_complete.pattern_parts(datasets, maps, mm, profile.structures(), mark)
        self.assertEqual(len([r for r in new.get('A3', []) if r['type'] == 'A3.DataEntity']), 3)       # the first pattern's three records — not a fourth for the second
        self.assertEqual(len([r for r in new.get('A4', []) if r['type'] == 'A4.SystemSoftware']), 2)   # its database and its key store
        self.assertIn('AID-PAT-BIAN-TRANSACT-DEPLOYMENT', ids)                                          # what only the second asks for


@_needs_bian
class InAWorkspace(Base):
    def test_status_offers_the_pattern_for_the_domains_kind(self):   # CPL-12, CPL-09
        for domain, want in (('Payment Order Initiation', T), ('Current Account', F)):
            ws = self.tmp / domain.replace(' ', '-')
            self.assertEqual(sdem('new', '--with', 'bian', '--workspace', ws, '--person', 'jane.architect', cwd=self.tmp)[0], 0)
            code, out, err = sdem('bian', 'add', domain, '--workspace', ws, '--person', 'jane.architect', cwd=self.tmp); self.assertEqual(code, 0, out + err)
            s = json.loads(sdem('status', '--workspace', ws, '--json', cwd=self.tmp)[1])
            got = [p['include'] for p in s['patterns_available']]
            self.assertIn(want, got); self.assertNotIn(F if want == T else T, got)
            self.assertEqual(sdem('profile', 'include', want, '--workspace', ws, '--person', 'jane.architect', cwd=self.tmp)[0], 0)
            self.assertEqual(sdem('check', '--workspace', ws, cwd=self.tmp)[0], 0)


if __name__ == '__main__':
    unittest.main()
