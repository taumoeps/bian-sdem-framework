"""BIAN's link rules for the rules engine (`sdem link`) — the 0.22 plan, step 3b: split out of sdem/rules_engine.py unchanged, so they can
move to the sdem-bian extension (R-D5, MX-45…MX-52). Steps 2, 4 and 5, the target design, BIAN's part of step 3 (S17…S29) and its
row of step 1 (S06), with the helpers only they use; the engine and the core's rules stay in rules_engine.CoreRun."""
from .rules_engine import BAND, HTTP, METHODS, _L, _T, _list, norm, re, stems, tokens, weakest  # noqa: F401 — the engine's own helpers


class BianSteps:
    def extra_joins(self):   # step 1's attribute joins: an activity invokes a BIAN operation
        return [('S06', _T('business.BusinessActivity'), 'invokes', _T('bian.ServiceOperation'), None)]

    # ------------------------------------------------------------ step 2 — BIAN REST decision procedure (S24, S26)
    def _qual(self, name):
        """A behaviour qualifier's tokens: its name and the institution's aliases (A2.BehaviorQualifier.attributes.aliases)."""
        if not name: return set(), None
        bq = next((b for b in self.of(_T('bian.BehaviorQualifier')) if b['name'].lower() == str(name).lower()), None)
        return stems(tokens(name, *_list(self.attr(bq, 'aliases') if bq else None))), bq

    @staticmethod
    def _path_segments(path):
        segs = [x for x in str(path or '').split('/') if x and not x.startswith('{')]
        return [stems(tokens(x)) for x in segs]

    def _check2(self, term, method, qual_in_path):
        if term not in METHODS: return 'fail', f'action term {term!r} has no REST form'
        if term == 'Execute' and method == 'POST':
            return ('pass', 'Execute on POST to a sub-resource named for the qualifier') if qual_in_path else ('fail', 'Execute on POST without a qualifier sub-resource')
        return ('pass', f'{term} ↔ {method}') if method in METHODS[term] else ('fail', f'{term} on {method}')

    def _check3(self, op_qual, other_quals, path):
        segs = self._path_segments(path); after = set().union(*segs[1:]) if len(segs) > 1 else set()
        if op_qual:
            return ('pass', 'qualifier in path') if op_qual & after else ('fail', 'qualifier not in path')
        for q in other_quals:
            if q & after: return 'fail', f'path carries another operation\'s qualifier ({sorted(q & after)[0]})'
        return 'neutral', 'no qualifier, none in path'

    def _overlap(self, op, api, aliases):
        want = {norm(a) for a in _list(self.attr(op, 'input_attributes')) + _list(self.attr(op, 'output_attributes'))}
        have = set()
        for f in _list(self.attr(api, 'payload_fields')):
            have.add(norm(f))
            if f in aliases: have.add(norm(aliases[f]))
        m = want & have
        return len(m), (len(m) / len(want) if want else 0.0), sorted(m)

    def step2(self):
        ops = self.of(_T('bian.ServiceOperation')); apis = self.of(_T('application.APIOperation'))
        pairs = []
        for op in ops:
            dom = self.climb(op['id'], _T('bian.ServiceDomain'), _L('bian'))
            term = self.attr(op, 'action_term'); qual, _ = self._qual(self.attr(op, 'behavior_qualifier'))
            siblings = [o for o in ops if o['id'] != op['id'] and dom and self.climb(o['id'], _T('bian.ServiceDomain'), _L('bian')) == dom]
            other_quals = [q for q in (self._qual(self.attr(o, 'behavior_qualifier'))[0] for o in siblings) if q]
            if dom is None:
                self.attempt('S24', op['id'], None, 2, [f"{op['id']} composition ancestors"], 'operation belongs to no Service Domain in the architecture dataset — no boundary'); continue
            at = self.get(self.attr(dom, 'asset_type'), _T('bian.AssetType')) if self.attr(dom, 'asset_type') else None
            gate = tokens(at['name'], *_list(self.attr(at, 'aliases'))) if at else set()
            for api in apis:
                comp = self.climb(api['id'], _T('application.ApplicationComponent'), _L('application'))
                ifc = self.climb(api['id'], _T('application.ApplicationInterface'), _L('application'))
                method = str(self.attr(api, 'method') or '').upper()
                conn = f"{op['id']} → {api['id']}"
                # precondition — boundary
                comps = {comp['id']} | ({c for c in self.descendants(comp['id'])} if comp else set()) if comp else set()
                anc = [x['id'] for x in [comp] if x]
                realized = comp and any((dom['id'], 'REALIZED_BY', c) in self.approved for c in anc + [p for p in self.parents(comp['id'])])
                if not realized:
                    if not gate:
                        self.log.append({'plan_id': 'S24', 'connection': conn, 'step_assigned': 2, 'step_used': 2, 'fallback': False, 'data_read': [dom['id']],
                                         'reasoning': 'boundary untestable: no approved REALIZED_BY and no asset type/aliases in the architecture dataset', 'outcome': 'no_proposal', 'proposal_id': None,
                                         'confidence_predicted': 'high', 'confidence_given': None}); continue
                    hit = gate & self._boundary_tokens(comp)
                    if not hit: continue  # outside the boundary: not a candidate pair (not logged per pair; the gate is per component)
                if method not in HTTP:
                    self.attempt('S24', op['id'], api['id'], 2, [f"{api['id']}.method"], f'method {method or "?"} is not HTTP — the BIAN REST mapping does not apply'); continue
                c3, why3 = self._check3(qual, other_quals, self.attr(api, 'path'))
                c2, why2 = self._check2(term, method, c3 == 'pass')
                aliases = (self.attr(ifc, 'field_aliases') or {}) if ifc else {}
                cnt, ratio, matched = self._overlap(op, api, aliases)
                pairs.append({'op': op, 'api': api, 'c2': c2, 'c3': c3, 'cnt': cnt, 'ratio': ratio, 'matched': matched, 'why': f'{why2}; {why3}; payload {cnt} matched ({ratio:.0%}): {matched}',
                              'qual_hit': bool(qual & stems(tokens(self.attr(api, 'path')) | tokens(api['name'])))})
        filed, removed = [], set()
        def live(): return [p for p in pairs if id(p) not in removed]
        def c4_winners(pool):
            """C4 for every pair at once: per operation, the single best payload overlap (count, then ratio, then the qualifier
            in the path). Grouped by operation — the same result as checking each pair against the whole pool."""
            groups = {}
            for q in pool:
                if q['cnt'] >= 2 and q['ratio'] >= 0.5: groups.setdefault(id(q['op']), []).append(q)
            ok = set()
            for mine in groups.values():
                best = max((q['cnt'], q['ratio']) for q in mine)
                tops = [q for q in mine if (q['cnt'], q['ratio']) == best]
                if len(tops) > 1:
                    tops = [q for q in tops if q['qual_hit']] or tops
                if len(tops) == 1: ok.add(id(tops[0]))
            return ok
        def award(cands):
            """Contention for one API between operations: count, then ratio, then the qualifier the path carries; a tie is no proposal."""
            out = []
            by_api = {}
            for p in cands: by_api.setdefault(p['api']['id'], []).append(p)
            for group in by_api.values():
                if len(group) == 1: out.append(group[0]); continue
                group.sort(key=lambda q: (q['cnt'], q['ratio'], q['qual_hit']), reverse=True)
                a, b = group[0], group[1]
                if (a['cnt'], a['ratio'], a['qual_hit']) == (b['cnt'], b['ratio'], b['qual_hit']):
                    for q in group:
                        self.attempt('S24', q['op']['id'], q['api']['id'], 2, [], f"contention tie for {q['api']['id']} between {[g['op']['id'] for g in group]} — no proposal")
                    continue
                out.append(a)
            return out
        def file(p, decision):
            filed.append((p, decision))
            for q in live():
                if q is not p and (q['op'] is p['op'] or q['api'] is p['api']): removed.add(id(q))
            removed.add(id(p))
        while True:
            pool = live(); win = c4_winners(pool)
            d1 = award([p for p in pool if p['c2'] == 'pass' and p['c3'] != 'fail' and id(p) in win])
            for p in d1: file(p, 1)
            pool = live(); win = c4_winners(pool)
            d2 = award([p for p in pool if p['c2'] == 'fail' and p['c3'] != 'fail' and id(p) in win]) if not d1 else []
            for p in d2: file(p, 2)
            if not d1 and not d2: break
        for p in live():
            self.attempt('S24', p['op']['id'], p['api']['id'], 2, [f"{p['op']['id']}.action_term/qualifier/attributes", f"{p['api']['id']}.method/path/payload_fields"], f"no decision: {p['why']}")
        for p, decision in filed:
            working = f"decision {decision}: {p['why']}" + ('' if decision == 1 else ' — method mismatch, proposed one band lower')
            rec = self.propose('S24', 'IMPLEMENTED_BY', p['op'], p['api'], 2, working, [f"{p['op']['id']}.action_term/behavior_qualifier/input_attributes/output_attributes", f"{p['api']['id']}.method/path/payload_fields"], fallback=decision == 2)
            if rec and p['c3'] == 'pass':
                _, bq = self._qual(self.attr(p['op'], 'behavior_qualifier'))
                if bq: self.report('S26', bq, p['api'], 2, f"qualifier {bq['name']} in path of {p['api']['id']}, which implements {p['op']['id']} ({rec['mapping_id']})", [f"{p['api']['id']}.path"])

    def domain_of(self, op_id):
        return self.climb(op_id, _T('bian.ServiceDomain'), _L('bian'))

    def entity_aliases(self, de):
        """field_aliases a data entity carries: inherited from every interface of a component that accesses it; its own take precedence."""
        if de['id'] not in self._aliases:
            al = {}
            for src in self.parents(de['id'], 'access'):   # the components that access it, in the data's order
                comp = self.get(src, _T('application.ApplicationComponent'), _L('application'))
                for x in (self.descendants(comp['id']) if comp else []):
                    ifc = self.get(x, _T('application.ApplicationInterface'), _L('application'))
                    if ifc: al.update(self.attr(ifc, 'field_aliases') or {})
            al.update(self.attr(de, 'field_aliases') or {})
            self._aliases[de['id']] = al
        return dict(self._aliases[de['id']])

    def verbs(self, term):
        t = str(term or '').lower(); return stems(self.VERB.get(t, {t}))

    def attr_match(self, want, have, aliases=None):
        w = {norm(a) for a in want}; h = set()
        for f in have:
            h.add(norm(f))
            if aliases and f in aliases: h.add(norm(aliases[f]))
        return w & h

    def step4(self):
        # S30 MAPPED_TO (BOM object -> data entity) and S20 (control record -> data entity): >= 50 % of the BIAN object's attributes, one-to-one
        des = self.of(_T('data.DataEntity'))
        for plan, stype in (('S30', _T('bian.BusinessObject')), ('S20', _T('bian.ControlRecord'))):
            scored = []
            for b in self.of(stype):
                want = _list(self.attr(b, 'attributes'))
                if not want: continue
                for de in des:
                    m = self.attr_match(want, _list(self.attr(de, 'attributes')), self.entity_aliases(de))
                    sc = len(m) / len(want)
                    if sc >= 0.5: scored.append((sc, b, de, sorted(m), [f"{b['id']}.attributes", f"{de['id']}.attributes"]))
            if plan == 'S30':
                self.one_to_one(plan, scored, lambda x: self.propose('S30', 'MAPPED_TO', x[1], x[2], 4, f"{len(x[3])}/{len(_list(self.attr(x[1], 'attributes')))} BOM attributes matched ({x[0]:.0%}): {x[3]}", x[4]))
            else:
                self.one_to_one(plan, scored, lambda x: self.report('S20', x[1], x[2], 4, f"{len(x[3])}/{len(_list(self.attr(x[1], 'attributes')))} control-record attributes matched ({x[0]:.0%})", x[4]))
        # S31: attributes of a mapped BOM object found in the data entity
        for b_id, de_id, lab in self.links('MAPPED_TO'):
            b = self.get(b_id, _T('bian.BusinessObject')); de = self.get(de_id, _T('data.DataEntity'))
            if not (b and de): continue
            have = self.attr_match([x['name'] for x in (self.get(c, _T('bian.BusinessObjectAttribute')) for c in self.children(b_id)) if x], _list(self.attr(de, 'attributes')), self.entity_aliases(de))
            for c in self.children(b_id):
                boa = self.get(c, _T('bian.BusinessObjectAttribute'))
                if boa and norm(boa['name']) in have:
                    self.report('S31', boa, de, 4, f"attribute {boa['name']} of {b_id} is in {de_id} (MAPPED_TO {lab})", [f"{de_id}.attributes"])
        # S12 ALIGNED_TO (bank glossary object -> BOM object): glossary attributes through the bank's aliases, one-to-one
        scored = []
        for a in self.of(_T('business.BusinessObject')):
            have = _list(self.attr(a, 'attributes')); al = self.attr(a, 'field_aliases') or {}
            for b in self.of(_T('bian.BusinessObject')):
                want = _list(self.attr(b, 'attributes'))
                if not want or not have: continue
                m = self.attr_match(want, have, al); sc = len(m) / len(want)
                if sc >= 0.5: scored.append((sc, a, b, sorted(m), [f"{a['id']}.attributes/field_aliases", f"{b['id']}.attributes"]))
        self.one_to_one('S12', scored, lambda x: self.propose('S12', 'ALIGNED_TO', x[1], x[2], 4, f"{len(x[3])}/{len(_list(self.attr(x[2], 'attributes')))} BOM attributes covered by the glossary ({x[0]:.0%})", x[4]))
        # S02 ALIGNED_TO (value stream -> scenario): coverage of the scenario's operations, in order, by stage action verbs (>= 60 %)
        for vs in self.of(_T('business.ValueStream')):
            stages = [self.get(x, _T('business.ValueStreamStage')) for x in _list(self.attr(vs, 'stages'))]
            stages = [x for x in stages if x]
            for sc_ in self.of(_T('bian.BusinessScenario')):
                ops = [self.get(x, _T('bian.ServiceOperation')) for x in _list(self.attr(sc_, 'operation_sequence'))]
                ops = [o for o in ops if o]
                if not ops or not stages: continue
                i, hits = 0, []
                for o in ops:
                    v = self.verbs(self.attr(o, 'action_term'))
                    for j in range(i, len(stages)):
                        if v & stems(tokens(stages[j]['name'])):
                            hits.append((o['id'], stages[j]['id'])); i = j + 1; break
                cov = len(hits) / len(ops)
                data = [f"{vs['id']}.stages", f"{sc_['id']}.operation_sequence"]
                if cov >= 0.6:
                    self.propose('S02', 'ALIGNED_TO', vs, sc_, 4, f"{len(hits)}/{len(ops)} scenario operations covered in order by stage verbs ({cov:.0%}): {hits}", data)
                    for _, st in hits:
                        self.report('S03', self.get(st, _T('business.ValueStreamStage')), sc_, 4, f"stage {st} matches an operation of {sc_['id']} (S02 for {vs['id']})", data)
                else:
                    self.attempt('S02', vs['id'], sc_['id'], 4, data, f'coverage {cov:.0%} < 60 %')
        # S06 (activity -> operation) by verb + noun when the activity names no operation
        # The noun must cover at least half of the domain's asset type, and only the best-covered domains are kept (DA2-04): one shared
        # common word ('order', 'payment') is not a match — with a full BIAN layer it named every domain with that word.
        for act in self.of(_T('business.BusinessActivity')):
            if _list(self.attr(act, 'invokes')): continue
            at = stems(tokens(act['name'])); found = []
            for o in self.of(_T('bian.ServiceOperation')):
                dom = self.domain_of(o['id']); asset = self.get(self.attr(dom, 'asset_type'), _T('bian.AssetType')) if dom and self.attr(dom, 'asset_type') else None
                noun = stems(tokens(asset['name'], *_list(self.attr(asset, 'aliases')))) if asset else stems(tokens(re.sub(r'\s*\(.*?\)', '', dom['name']))) if dom else set()   # no asset type published: the domain's name
                if self.verbs(self.attr(o, 'action_term')) & at and noun & at:
                    cover = len(noun & at) / len(noun)
                    if cover >= 0.5: found.append((cover, o))
            best = max((c for c, _ in found), default=0)
            for cover, o in found:
                if cover == best:
                    self.report('S06', act, o, 4, f"verb and noun match: '{act['name']}' ~ '{o['name']}' (covers {cover:.0%} of the asset type)", [f"{act['id']}.name", f"{o['id']}.action_term", 'asset type'])
        # S09 (business service -> operation): inputs/outputs vs operation attributes, >= 50 % and >= 2, unique best per service
        for bs in self.of(_T('business.BusinessService')):
            have = []
            for x in _list(self.attr(bs, 'inputs')) + _list(self.attr(bs, 'outputs')):   # CT-01 (metamodel 0.15.0): a business object's id stands for its fields
                bo = self.get(x, _T('business.BusinessObject')) if isinstance(x, str) else None
                have += _list(self.attr(bo, 'attributes')) if bo else [x]
            if not have: continue
            sc = []
            for o in self.of(_T('bian.ServiceOperation')):
                want = _list(self.attr(o, 'input_attributes')) + _list(self.attr(o, 'output_attributes'))
                m = self.attr_match(want, have)
                if want and len(m) >= 2 and len(m) / len(want) >= 0.5: sc.append((len(m), len(m) / len(want), o, sorted(m)))
            if sc:
                top = max(x[:2] for x in sc); best = [x for x in sc if x[:2] == top]
                if len(best) == 1:
                    self.report('S09', bs, best[0][2], 4, f"{best[0][0]} attributes matched ({best[0][1]:.0%}): {best[0][3]}", [f"{bs['id']}.inputs/outputs"])
                else:
                    self.attempt('S09', bs['id'], None, 4, [], f"tie between {[x[2]['id'] for x in best]} — no report")
        # S19 (asset type -> data entity) and S27 (qualifier -> data entity): a name or alias token in the entity name
        for plan, stype, src in (('S19', _T('bian.AssetType'), lambda x: tokens(*_list(self.attr(x, 'aliases')))), ('S27', _T('bian.BehaviorQualifier'), lambda x: tokens(*_list(self.attr(x, 'aliases'))))):
            for a in self.of(stype):
                toks = stems(src(a))
                for de in des:
                    hit = toks & stems(tokens(de['name']))
                    if hit: self.report(plan, a, de, 4, f"{sorted(hit)} of {a['id']} in entity name '{de['name']}'", [f"{a['id']}.aliases", f"{de['id']}.name"])

    def concepts(self, *texts):
        return stems({w for w in tokens(*texts) if w not in self.GENERIC and len(w) > 2})

    def rank(self, plan, src, text, rel=None):
        if plan not in self.rules: return None   # BX-02, BX-13: a rule of an extension that is off (e.g. ext:bian) does not run
        doms = self.of(_T('bian.ServiceDomain'))
        if len(doms) < 2:
            self.attempt(plan, src['id'], None, 5, [], 'single-candidate — no proposal'); return
        def dtext(d):
            at = self.get(self.attr(d, 'asset_type'), _T('bian.AssetType')) if self.attr(d, 'asset_type') else None
            return self.concepts(d['name'], d.get('description'), at['name'] if at else None, *_list(self.attr(at, 'aliases') if at else None))
        mine = self.concepts(text)
        sc = sorted(((len(mine & dtext(d)), d) for d in doms), key=lambda x: -x[0])
        best, runner = sc[0], (sc[1][0] if len(sc) > 1 else 0)
        working = f"shares {sorted(mine & dtext(best[1]))} with {best[1]['id']}; runner-up shares {runner}"
        if best[0] >= 2 and best[0] - runner >= 1:
            if rel: self.propose(plan, rel, src, best[1], 5, working, ['descriptions'], band='low')
            else: self.report(plan, src, best[1], 5, working, ['descriptions'], band='low')
        else:
            self.attempt(plan, src['id'], best[1]['id'], 5, ['descriptions'], f'{working} — below threshold, no proposal')

    def step5(self, options):
        supported = {k[0] for k in self.proposed if k[1] == 'SUPPORTED_BY'} | {a for a, r, _ in self.approved if r == 'SUPPORTED_BY'}
        for cap in self.of(_T('business.BusinessCapability')):
            prcs = [e for e in self.wedges if e['kind'] == 'realization' and e['target'] == cap['id']]
            if cap['id'] in supported or prcs: continue  # step 5 only for a capability with no mapped processes
            kids = [c for c in self.children(cap['id']) if self.get(c, _T('business.BusinessCapability'))]
            if kids:  # a parent's scope covered by a child's domain is a judgement, not a derivation (M0 run 2): report-only
                self.attempt('S01', cap['id'], None, 5, [f"{cap['id']} composes {kids}"], 'parent capability — report-only, never proposed (M0 run 2)'); continue
            self.rank('S01', cap, f"{cap['name']} {cap.get('description') or ''}", 'SUPPORTED_BY')
        if options.get('S08'):
            for bs in self.of(_T('business.BusinessService')):
                self.rank('S08', bs, f"{bs['name']} {bs.get('description') or ''}")

    @staticmethod
    def _collection(asset_name):
        words = re.findall(r'[A-Za-z0-9]+', asset_name.lower())
        if words: words[-1] = words[-1][:-1] + 'ies' if words[-1].endswith('y') else (words[-1] if words[-1].endswith('s') else words[-1] + 's')
        return '/' + '-'.join(words)

    def _rest_form(self, op, coll):
        term = self.attr(op, 'action_term'); q = self.attr(op, 'behavior_qualifier')
        if term in self.CREATE_TERMS and q: return 'POST', f"{coll}/{{id}}/{str(q).lower()}", 'create-type term with a qualifier ⇔ POST on the qualifier sub-resource (AID-Q04)'
        if term in self.CREATE_TERMS: return 'POST', coll, 'create-instance term ⇔ POST on the collection'
        if term == 'Retrieve': return 'GET', coll + '/{id}', 'Retrieve ⇔ GET (SAPG §3.5, verified)'
        if term == 'Update': return 'PATCH', coll + '/{id}', 'Update ⇔ PATCH on the instance'
        if term == 'Execute' and q: return 'POST', f"{coll}/{{id}}/{str(q).lower()}", 'Execute ⇔ POST on the qualifier sub-resource'
        if term == 'Control': return 'PUT', coll + '/{id}/control', "Control ⇔ PUT on the instance's control action"
        if term in METHODS: return 'PUT', coll + '/{id}' + (f'/{str(q).lower()}' if q else ''), f'{term} ⇔ PUT on the instance'
        return None, None, f'{term} has no REST form'

    def design(self):
        """When no A3 architecture dataset exists, mapping ends at A2: produce a TARGET DESIGN from BIAN's container pattern (planned instances, low)."""
        levels = set(self.r.levels())
        if _L('application') in levels or _L('bian') not in levels:
            return []
        self.log.append({'plan_id': 'DESIGN', 'connection': f'mapping ends at {_L("bian")}', 'step_assigned': None, 'step_used': 'design', 'fallback': False, 'data_read': ['architecture datasets: ' + ', '.join(sorted(levels))],
                         'reasoning': f'no {_L("application")} or {_L("technology")} architecture dataset: no step applies below {_L("bian")}; a target design is produced from the BIAN container pattern', 'confidence_predicted': 'low', 'confidence_given': None, 'proposal_id': None, 'outcome': 'design'})
        a3 = {'level': _L('application'), 'model_id': f'{self.uc.lower()}-a3-TARGET-DESIGN', 'model_version': 'design', 'metamodel_version': self.mm.version,
              'source_system': 'DESIGN-PROPOSAL (bian-container-pattern; not an APM architecture dataset)', 'instances': [], 'relationships': []}
        a4 = {'level': _L('technology'), 'model_id': f'{self.uc.lower()}-a4-TARGET-DESIGN', 'model_version': 'design', 'metamodel_version': self.mm.version,
              'source_system': 'DESIGN-PROPOSAL (bian-container-pattern; not a CMDB architecture dataset)', 'instances': [], 'relationships': []}
        tag = 'TARGET DESIGN, not a mapping'
        for dom in self.of(_T('bian.ServiceDomain')):
            ops = [o for o in self.of(_T('bian.ServiceOperation')) if (self.domain_of(o['id']) or {}).get('id') == dom['id']]
            if not ops: continue
            at = self.get(self.attr(dom, 'asset_type'), _T('bian.AssetType')) if self.attr(dom, 'asset_type') else None
            base = at['name'] if at else dom['name']; coll = self._collection(base)
            app = {'id': f"DSN-APP-{dom['id']}", 'type': _T('application.ApplicationComponent'), 'version': '1.0', 'name': f'{base} service (target)', 'lifecycle_status': 'planned',
                   'description': f"{tag}: one deployable component for {dom['name']}, exposing its service operations as a REST API (BIAN container pattern)."}
            a3['instances'].append(app)
            self.propose('DESIGN', 'REALIZED_BY', dom, app, 'design', f'{tag}: one component per Service Domain (BIAN container pattern)', [dom['id']], band='low')
            for op in ops:
                method, path, why = self._rest_form(op, coll)
                if not method:
                    self.attempt('S24', op['id'], None, 'design', [f"{op['id']}.action_term"], f'{tag}: {why} — no API designed'); continue
                payload = sorted(set(_list(self.attr(op, 'input_attributes')) + _list(self.attr(op, 'output_attributes'))))
                api = {'id': f"DSN-API-{op['id']}", 'type': _T('application.APIOperation'), 'version': '1.0', 'name': f'{method} {path}', 'lifecycle_status': 'planned',
                       'description': f"Reference API for {op['name']} ({self.attr(op, 'action_term')}); {why}.",
                       'attributes': {'method': method, 'path': path, 'payload_fields': payload}}
                a3['instances'].append(api); a3['relationships'].append({'source': app['id'], 'kind': 'composition', 'target': api['id']})
                self.propose('S24', 'IMPLEMENTED_BY', op, api, 'design', f'{tag}: the API derived from the operation by the REST mapping — {why}; payload = input ∪ output', [op['id']], band='low')
            dep = {'id': f"DSN-DEP-{dom['id']}", 'type': _T('technology.Deployment'), 'version': '1.0', 'name': f'{base} service — target deployment', 'lifecycle_status': 'planned',
                   'description': f"{tag}: one deployment of {app['id']}. No environment or platform exists to name.", 'attributes': {'component_id': app['id']}}
            a4['instances'].append(dep)
            self.propose('S32', 'DEPLOYED_AS', app, dep, 'design', f'{tag}: one deployment per component (BIAN container pattern); no platform, environment or data entity is invented', [app['id']], band='low')
        return [a3, a4] if a3['instances'] else []

    def step3_bian(self):
        impl = self.links('IMPLEMENTED_BY')
        # S17 REALIZED_BY: a component exposing APIs that implement a domain's operations realises the domain (cap: strongest input, DEC-E-02)
        real = {}
        for op_id, api_id, lab in impl:
            dom = self.domain_of(op_id); comp = self.component_of(api_id)
            if dom and comp: real.setdefault((dom['id'], comp['id']), []).append((op_id, api_id, lab))
        for (d, c), via in real.items():
            band = max((self.band_of(l) for _, _, l in via), key=lambda b: BAND[b])
            self.propose('S17', 'REALIZED_BY', self.get(d, _T('bian.ServiceDomain')), self.get(c, _T('application.ApplicationComponent')), 3,
                         'implements ' + '; '.join(f'{o} via {a} ({l})' for o, a, l in via), [f'IMPLEMENTED_BY {l}' for _, _, l in via], band=band)
        done = {d for d, _ in real}
        # fallback A: the component accesses a data entity MAPPED_TO the business object of the domain's control record
        mapped = self.links('MAPPED_TO')
        for dom in self.of(_T('bian.ServiceDomain')):
            if dom['id'] in done: continue
            crs = [x for x in self.children(dom['id'], 'aggregation') if self.get(x, _T('bian.ControlRecord'))]
            bos = {e['target'] for e in self.wedges if e['source'] in crs and self.get(e['target'], _T('bian.BusinessObject'))} | {e['source'] for e in self.wedges if e['target'] in crs and self.get(e['source'], _T('bian.BusinessObject'))}
            found = {}
            for b, de, lab in mapped:
                if b not in bos: continue
                for e in self.wedges:
                    if e['kind'] == 'access' and e['target'] == de:
                        comp = self.component_of(e['source'])
                        if comp: found.setdefault(comp['id'], []).append((b, de, lab))
            for c, via in found.items():
                band = max((self.band_of(l) for _, _, l in via), key=lambda b: BAND[b])
                self.propose('S17', 'REALIZED_BY', dom, self.get(c, _T('application.ApplicationComponent')), 3, 'fallback A (information perspective): ' + '; '.join(f'accesses {de}, MAPPED_TO {b} ({l})' for b, de, l in via),
                             [f'MAPPED_TO {l}' for _, _, l in via], band=band)
                done.add(dom['id'])
        # fallback B (step 4, one band lower): an asset-type token in the component's API paths or data entity names
        for dom in self.of(_T('bian.ServiceDomain')):
            if dom['id'] in done: continue
            at = self.get(self.attr(dom, 'asset_type'), _T('bian.AssetType')) if self.attr(dom, 'asset_type') else None
            if not at: self.attempt('S17', dom['id'], None, 3, [], 'no implemented operation, no mapped object, no asset type — no proposal'); continue
            toks = stems(tokens(at['name'], *_list(self.attr(at, 'aliases'))))
            for comp in self.of(_T('application.ApplicationComponent')):
                # DEC-E-08: a token shared with the asset type of a domain this component (or one containing it) already realises explains nothing new
                lineage = {comp['id']} | set(self.parents(comp['id']))
                explained = set()
                for dd, cc, _ in self.links_by('REALIZED_BY', tgts=lineage):
                    if cc in lineage and dd != dom['id']:
                        a2 = self.get(self.attr(self.get(dd, _T('bian.ServiceDomain')), 'asset_type'), _T('bian.AssetType'))
                        if a2: explained |= stems(tokens(a2['name'], *_list(self.attr(a2, 'aliases'))))
                texts = []
                for x in self.descendants(comp['id']):
                    n = self.get(x, _T('application.APIOperation'), _L('application'))
                    if n: texts.append(self.attr(n, 'path'))
                for x in self.descendants(comp['id']):
                    for e in self.children(x, 'access'):
                        de = self.get(e, _T('data.DataEntity'), _L('application'))
                        if de: texts.append(de['name'])
                hit = (toks - explained) & stems(tokens(*texts))
                if hit: self.propose('S17', 'REALIZED_BY', dom, comp, 4, f'fallback B: asset-type tokens {sorted(hit)} in API paths / entity names', [f"{comp['id']} API paths, data entities"], fallback=True, band='low')  # name-only evidence: low, never more (T6, owner 2026-10-28)
        # S04 USES_DOMAIN: a process (or one of its activities) invokes an operation of the domain, or an S06 report links its activity
        for prc in self.of(_T('business.BusinessProcess')):
            if self.mm.is_a(prc['type'], _T('business.BusinessActivity')): continue
            acts = [a for a in self.children(prc['id']) if self.get(a, _T('business.BusinessActivity'))]
            ops = {o: f"{prc['id']}.invokes" for o in _list(self.attr(prc, 'invokes'))}
            for a in acts:
                for o in _list(self.attr(self.get(a, _T('business.BusinessActivity')), 'invokes')): ops.setdefault(o, f'{a}.invokes')
                for s_, o, lab in self.reports_from('S06', a):
                    if s_ == a: ops.setdefault(o, f'S06 {lab}')
            doms = {}
            for o, why in ops.items():
                d = self.domain_of(o)
                if d: doms.setdefault(d['id'], []).append(f'{o} ({why})')
            for d, why in doms.items():
                ev = 'attribute_join' if any(w.endswith('.invokes)') for w in why) else 'name_token'   # an invokes field, or only an S06 name match
                self.propose('S04', 'USES_DOMAIN', prc, self.get(d, _T('bian.ServiceDomain')), 3, 'invokes ' + '; '.join(why), why, ev=ev)
        # S01 SUPPORTED_BY: every process of the capability uses the domain (medium); only some (low)
        for cap in self.of(_T('business.BusinessCapability')):
            prcs = [e['source'] for e in self.wedges if e['kind'] == 'realization' and e['target'] == cap['id'] and self.get(e['source'], _T('business.BusinessProcess')) and not self.get(e['source'], _T('business.BusinessActivity'))]
            if not prcs: continue
            uses, basis = {}, {}
            for p_, d, lab in self.links_by('USES_DOMAIN', srcs=list(dict.fromkeys(prcs))):
                if p_ in prcs: uses.setdefault(d, set()).add(p_); basis.setdefault(d, []).append((self._by_mapping_id.get(lab) or {}).get('evidence_class') or 'structural')   # approved: a person's fact
            for d, ps in uses.items():
                if len(ps) == len(prcs):
                    self.propose('S01', 'SUPPORTED_BY', cap, self.get(d, _T('bian.ServiceDomain')), 3, f"all {len(prcs)} processes of the capability use the domain", sorted(ps), ev=weakest(*basis[d]))
                else:  # DEC-E-09: partial coverage is not evidence enough for a registry arrow
                    self.attempt('S01', cap['id'], d, 3, sorted(ps), f'only {len(ps)} of {len(prcs)} processes use the domain — no proposal (DEC-E-09)')
        # candidate derivations (reported, never registry records)
        for a, o, lab in self.reports('S06'):
            d = self.domain_of(o)
            if d: self.report('S07', self.get(a, _T('business.BusinessActivity')), d, 3, f'S06 {lab}: {a} → {o}, in {d["id"]}', [lab])
        for req in self.of(_T('business.BusinessRequirement')):
            for t in _list(self.attr(req, 'applies_to')):
                tn = self.get(t, level=_L('business'))
                if not tn: continue
                if self.mm.is_a(tn['type'], _T('business.BusinessActivity')):
                    ops = [o for s_, o, _ in self.reports_from('S06', t) if s_ == t] + _list(self.attr(tn, 'invokes'))
                    for o in dict.fromkeys(ops):
                        on = self.get(o, _T('bian.ServiceOperation')); d = self.domain_of(o)
                        if on: self.report('S14', req, on, 3, f'applies to activity {t}, which invokes {o}', [f"{req['id']}.applies_to"])
                        if d: self.report('S13', req, d, 3, f'applies to activity {t}, whose operation {o} is in {d["id"]}', [f"{req['id']}.applies_to"])
                else:
                    for p_, d, lab in self.links_by('USES_DOMAIN', src=t):
                        if p_ == t: self.report('S13', req, self.get(d, _T('bian.ServiceDomain')), 3, f'applies to {t}, which USES_DOMAIN {d} ({lab})', [f"{req['id']}.applies_to"])
        for d, c, lab in self.links('REALIZED_BY'):
            comp = self.get(c, _T('application.ApplicationComponent'))
            bd = [p_ for p_ in self.parents(d) if self.get(p_, _T('bian.BusinessDomain'))]
            for b in bd:
                self.report('S16', self.get(b, _T('bian.BusinessDomain')), comp, 3, f'{b} composes {d}, REALIZED_BY {c} ({lab})', [lab])
                for a in self.parents(b):
                    if self.get(a, _T('bian.BusinessArea')): self.report('S15', self.get(a, _T('bian.BusinessArea')), comp, 3, f'{a} composes {b} composes {d}, REALIZED_BY {c} ({lab})', [lab])
        for op_id, api_id, lab in impl:
            op = self.get(op_id, _T('bian.ServiceOperation')); ifc = self.climb(api_id, _T('application.ApplicationInterface'), _L('application'))
            svcs = [self.get(e['target'], _T('application.ApplicationService')) for e in self.wedges if ifc and e['kind'] == 'assignment' and e['source'] == ifc['id']]
            for sv in [x for x in svcs if x]:
                self.report('S25', op, sv, 3, f'{op_id} IMPLEMENTED_BY {api_id} ({lab}); {ifc["id"]} composes it and is assigned to {sv["id"]}', [lab])
            for sg in [p_ for p_ in self.parents(op_id) if self.get(p_, _T('bian.ServiceGroup'))]:
                for sv in [x for x in svcs if x]: self.report('S22', self.get(sg, _T('bian.ServiceGroup')), sv, 3, f'{sg} contains {op_id}, IMPLEMENTED_BY {api_id} exposed through {ifc["id"]} → {sv["id"]}', [lab])
                if ifc: self.report('S23', self.get(sg, _T('bian.ServiceGroup')), ifc, 3, f'{sg} contains {op_id}, IMPLEMENTED_BY {api_id} in {ifc["id"]}', [lab])
            for fn in self.of(_T('application.ApplicationFunction')):
                if api_id in _list(self.attr(fn, 'exposed_through')):
                    d = self.domain_of(op_id)
                    fp = self.get(self.attr(d, 'functional_pattern'), _T('bian.FunctionalPattern')) if d and self.attr(d, 'functional_pattern') else None
                    if fp: self.report('S18', fp, fn, 3, f'{fn["id"]} exposed through {api_id}, which implements {op_id} of {d["id"]} (pattern {fp["id"]})', [lab])
                    for cr in self.children(op_id, 'access'):
                        crn = self.get(cr, _T('bian.ControlRecord'))
                        if crn: self.report('S21', crn, fn, 3, f'{fn["id"]} exposed through {api_id}; {op_id} accesses {cr}', [lab])
        for sc_ in self.of(_T('bian.BusinessScenario')):
            for o in _list(self.attr(sc_, 'operation_sequence')):
                for s_, sv, lab in self.reports_from('S25', o):
                    if s_ == o: self.report('S28', sc_, self.get(sv, _T('application.ApplicationService')), 3, f'{o} in the sequence → {sv} (S25 {lab})', [lab])
                d = self.domain_of(o)
                for dd, c, lab in (self.links_by('REALIZED_BY', src=d['id']) if d else []):
                    if d and dd == d['id']: self.report('S29', sc_, self.get(c, _T('application.ApplicationComponent')), 3, f'{o} in the sequence is in {dd}, REALIZED_BY {c} ({lab})', [lab])
