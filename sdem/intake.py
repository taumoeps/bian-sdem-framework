"""`sdem intake` — a design authored as SDEM data comes in through one command (docs/design/sdem-intake-design.md IN-01…IN-10).

The package is the eight files of the authoring guide (`sdem types authoring`): three layer files, the BIAN domains named, the links
between layers suggested, what the design does not state, the author's checklist and read-me.

  sdem intake <folder> --check                        # the author's own check, before handing over: everything wrong, at once; no workspace
  sdem intake <folder> --workspace <ws> --person <you>   # check, start the workspace, load, BIAN, patterns, the complete first draft, one report

The second form does, in the one order (the skill sdem-complete-draft), what took eight commands and a memory for their order. It
approves, confirms and rejects nothing: it ends with the report of what is the person's to decide, weakest first.
"""
import argparse, difflib, json, shutil, sys, tempfile
from pathlib import Path

LAYERS = {'A1': 'a1-business.json', 'A3': 'a3-application.json', 'A4': 'a4-technology.json'}
AGENTS = {'A1': 'sdem-a1-business', 'A3': 'sdem-a3-application', 'A4': 'sdem-a4-technology'}
BIAN, SUGG, NOTS, DECS = 'BIAN-DOMAINS.json', 'CROSS-LAYER-SUGGESTIONS.json', 'NOT-STATED.json', 'DECISIONS.json'
CHECKER = 'intake.check'   # the name the throw-away workspace of a check is started under — nothing of it is kept


class IntakeError(ValueError):
    pass


def _sdem(*args):
    """One sdem command, run in this process (SDEM starts no program it does not name — PRIVACY.md): its exit code, output and errors."""
    import contextlib, io
    from . import cli
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try: code = cli.main([str(a) for a in args])
        except SystemExit as e: code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    return code or 0, out.getvalue(), err.getvalue()


def _must(*args, what):
    code, out, err = _sdem(*args)
    if code: raise IntakeError(f"{what} failed — stopped there; what was done before it stays, nothing after it was done:\n{(out + err).strip()[-1500:]}")
    return out


def _load_json(pkg, name, errors, required=True):
    f = pkg / name
    if not f.exists():
        if required: errors.append({'file': name, 'message': 'missing — the package has this file (sdem types authoring, section 1)'})
        return None
    try: return json.loads(f.read_text(encoding='utf-8'))
    except ValueError as e: errors.append({'file': name, 'message': f'not valid JSON — {e}'}); return None


def _bian_catalogue():
    """BIAN's service domains by name, and each one's operations by their short name — from the release SDEM ships."""
    from .new import base_layer
    cat, _ = base_layer()
    by = {i['id']: i for i in cat['instances']}
    kids = {}
    for r in cat.get('relationships', []): kids.setdefault(r['source'], []).append(r['target'])
    out = {}
    for i in cat['instances']:
        if i['type'] != 'A2.ServiceDomain': continue
        ops = {}
        for g in kids.get(i['id'], []):
            for o in kids.get(g, []):
                if o in by and by[o]['type'] == 'A2.ServiceOperation': ops[by[o]['name'].split(': ', 1)[-1]] = o
        out[i['name']] = {'id': i['id'], 'operations': ops}
    return out


def _invokes(ws, tmp, ops, person):
    """The BIAN operations each process uses (BIAN-DOMAINS.json: operations.used_by), recorded on the process as `invokes`."""
    uses = {}
    for o in ops:
        for u in o['used_by']: uses.setdefault(u, []).append(o['id'])
    if not uses: return
    a1 = json.loads((Path(ws) / LAYERS['A1']).read_text(encoding='utf-8')); changes = []
    for i in a1['instances']:
        if i['id'] in uses:
            i = json.loads(json.dumps(i)); at = i.setdefault('attributes', {})
            at['invokes'] = sorted(set(at.get('invokes') or []) | set(uses[i['id']])); changes.append({'op': 'update', 'kind': 'modify', 'record': i})
    if not changes: return
    cs = Path(tmp) / 'cs-invokes.json'
    cs.write_text(json.dumps({'layer': 'A1', 'reason': f"{BIAN}: the BIAN operations each process uses, by their id in the BIAN release", 'changes': changes, 'relationships': {'add': [], 'remove': []}}), encoding='utf-8')
    _must('change', 'propose', cs, '--workspace', ws, '--agent', AGENTS['A1'], '--person', person, what='recording the BIAN operations the processes use')


def check(pkg, allow_gaps=False):
    """IN-01…IN-04, IN-11: everything wrong with a package, at once — and whether the design is COMPLETE: every record connected, every part
    of every pattern that fits present, counting the links between layers the package gives. Without a workspace. Not complete is an error
    unless `allow_gaps`. Returns the result; the keys starting with `_` are for the loader."""
    from .metamodel import Metamodel
    from .validate import load_registry
    pkg = Path(pkg)
    if not pkg.is_dir(): raise IntakeError(f'{pkg}: no such folder — give the folder that holds the package (a1-business.json … NOT-STATED.json)')
    errors, docs = [], {}
    mm = Metamodel.base()
    reg = load_registry()['relationships']; rels = sorted({r['relationship'] for r in reg})
    if (pkg / 'a2-service-domain.json').exists():
        errors.append({'file': 'a2-service-domain.json', 'message': f'the BIAN layer is not authored — name its service domains in {BIAN}; SDEM takes BIAN records from BIAN only (CTL-24)'})
    for layer, name in LAYERS.items():
        d = _load_json(pkg, name, errors)
        if d is None: continue
        if not isinstance(d, dict) or not isinstance(d.get('instances'), list):
            errors.append({'file': name, 'message': 'not a layer file — {"level": "%s", "instances": [records], "relationships": [links]}' % layer}); continue
        d = {**d, 'level': layer, 'relationships': list(d.get('relationships') or [])}
        ids = {i.get('id') for i in d['instances'] if isinstance(i, dict)}
        keep = []
        for r in d['relationships']:
            s, k, t = r.get('source'), r.get('kind') or r.get('relationship') or r.get('link_type'), r.get('target')
            if k in rels: errors.append({'file': name, 'message': f'{s} {k} {t} is a link between layers — list it in {SUGG}; a layer file holds only links inside its layer'}); continue
            if s not in ids or t not in ids:
                errors.append({'file': name, 'message': f"link {s} {k} {t}: {s if s not in ids else t} is not a record in this file — a link inside a layer joins two of its own records"}); continue
            keep.append(r)
        d['relationships'] = keep; docs[layer] = d
    bian = _load_json(pkg, BIAN, errors) or {}
    sugg = _load_json(pkg, SUGG, errors) or {}
    nots = _load_json(pkg, NOTS, errors) or {}
    decs = _load_json(pkg, DECS, errors, required=False) or {}
    recs = {i['id']: i for d in docs.values() for i in d['instances'] if isinstance(i, dict) and i.get('id')}
    layer_of = {i['id']: l for l, d in docs.items() for i in d['instances'] if isinstance(i, dict) and i.get('id')}

    cat = _bian_catalogue()
    domains, ops = [], []
    for x in bian.get('service_domains') or []:
        n = x.get('name') if isinstance(x, dict) else x
        if n in cat: domains.append(n)
        else:
            near = difflib.get_close_matches(n or '', list(cat), 3, 0.5)
            errors.append({'file': BIAN, 'message': f"{n!r} is not a BIAN service domain" + (f" — did you mean {', '.join(near)}?" if near else '') + " (a bank's own concept goes under bank_local_not_bian)"})
    for x in bian.get('operations') or []:
        sd, n = x.get('service_domain'), x.get('name')
        if sd in cat:
            oid = cat[sd]['operations'].get(n)
            if not oid: errors.append({'file': BIAN, 'message': f"{sd} has no operation {n!r} — it has: {', '.join(sorted(cat[sd]['operations']))}"})
        else:
            oid = None
            if sd not in [d.get('name') if isinstance(d, dict) else d for d in bian.get('service_domains') or []]: errors.append({'file': BIAN, 'message': f"operation {n!r}: {sd!r} is not a BIAN service domain"})
        users = []
        for u in x.get('used_by') or []:
            if u in recs and mm.known(recs[u].get('type', '')) and mm.is_a(recs[u]['type'], 'A1.BusinessProcess'): users.append(u)
            else: errors.append({'file': BIAN, 'message': f"used_by {u} is not a record of a business process or activity in a1-business.json"})
        if oid: ops.append({'service_domain': sd, 'name': n, 'id': oid, 'used_by': users})

    def end(x):   # a suggestion's end: a record of the package, or a BIAN domain or operation the package names
        if x in recs: return x, recs[x].get('type', '')
        if x in cat and x in domains: return cat[x]['id'], 'A2.ServiceDomain'
        for n in domains:
            if x == cat[n]['id']: return x, 'A2.ServiceDomain'
            if x in cat[n]['operations'].values(): return x, 'A2.ServiceOperation'
            if isinstance(x, str) and x.startswith(n + ': ') and x[len(n) + 2:] in cat[n]['operations']: return cat[n]['operations'][x[len(n) + 2:]], 'A2.ServiceOperation'
        return None, None
    good = []
    for x in sugg.get('suggestions') or []:
        s, r, t = x.get('source'), x.get('link_type') or x.get('relationship'), x.get('target')
        if r not in rels: errors.append({'file': SUGG, 'message': f"{r!r} is not a link type between layers ({s} → {t}) — the link types: {', '.join(rels)}"}); continue
        (si, st), (ti, tt) = end(s), end(t)
        if not si or not ti: errors.append({'file': SUGG, 'message': f"{s} {r} {t}: {s if not si else t} is not a record of the package, nor a BIAN domain it names"}); continue
        if not any(q['relationship'] == r and mm.known(st) and mm.known(tt) and mm.is_a(st, q['source_type']) and mm.is_a(tt, q['target_type']) for q in reg):
            joins = '; '.join(f"{q['source_type']} to {q['target_type']}" for q in reg if q['relationship'] == r)
            errors.append({'file': SUGG, 'message': f"{s} {r} {t} — {r} does not join {st} to {tt} (it joins {joins})"}); continue
        good.append({'source': si, 'relationship': r, 'target': ti, 'section': x.get('design_section'), 'basis': x.get('basis') or 'stated', 'reason': x.get('reason') or ''})
    declared = set()
    for x in nots.get('items') or []:
        rid = x.get('record_id')
        if rid in recs: declared.add(rid)   # one that names no record says the design lacks the thing altogether (no value stream, no product) — a statement, not an error

    undeclared = []
    if docs:   # IN-02: the real check — SDEM itself, on a workspace that is thrown away
        tmp = Path(tempfile.mkdtemp(prefix='sdem-intake-'))
        try:
            ws = tmp / 'ws'
            _must('new', '--workspace', ws, '--person', CHECKER, what='starting the throw-away workspace of the check')
            passed = []
            for layer, d in docs.items():
                if not d['instances'] and not d['relationships']: continue   # a layer the design says nothing of: nothing to check, nothing to load
                src = tmp / LAYERS[layer]; src.write_text(json.dumps(d), encoding='utf-8'); cs = tmp / f'cs-{layer}.json'
                code, out, err = _sdem('change', 'diff', src, '--workspace', ws, '-o', cs)
                if code or not cs.exists(): errors.append({'file': LAYERS[layer], 'message': (out + err).strip().splitlines()[-1] if (out + err).strip() else 'could not be read as a layer'}); continue
                code, out, err = _sdem('change', 'propose', cs, '--workspace', ws, '--agent', AGENTS[layer], '--person', CHECKER, '--dry-run')
                bad = [l.strip().split('): ', 1)[1] for l in (out + err).splitlines() if l.startswith('  level ') and '): ' in l]
                if code:
                    other = [l.strip() for l in (out + err).splitlines() if l.startswith('ERROR') and 'breaks the metamodel' not in l]
                    for l in bad or other or [(out + err).strip()[-300:]]: errors.append({'file': LAYERS[layer], 'message': l})
                else: passed.append((layer, cs))
            for layer, cs in passed: _must('change', 'propose', cs, '--workspace', ws, '--agent', AGENTS[layer], '--person', CHECKER, what=f'applying {LAYERS[layer]} in the throw-away workspace')
            gaps = []
            if len(passed) == len([d for d in docs.values() if d['instances'] or d['relationships']]) and not errors:
                # IN-11: is the design complete? — in the throw-away workspace, as it would stand once taken in: its BIAN domains, the BIAN
                # operations its processes use, every pattern that fits, and the links between layers the package gives counted as links
                if domains: _must('bian', 'add', *domains, '--workspace', ws, '--person', CHECKER, what='adding the BIAN service domains (throw-away workspace)')
                _invokes(ws, tmp, ops, CHECKER)
                reg_f = ws / 'mappings.json'; regd = json.loads(reg_f.read_text(encoding='utf-8'))
                regd['mappings'] = [{'mapping_id': f'CHK-{n}', 'source': {'id': g['source']}, 'relationship': g['relationship'], 'target': {'id': g['target']}, 'status': 'approved'} for n, g in enumerate(good)]
                reg_f.write_text(json.dumps(regd), encoding='utf-8')
                from .comply import workspace_data
                from . import profile as _p
                ds, _, mm_ws, _ = workspace_data(ws)
                fitting = _p.available(ds, mm_ws)
                for p in fitting: _must('profile', 'include', p['include'], '--workspace', ws, '--person', CHECKER, what=f"including {p['include']} (throw-away workspace)")
                code, out, err = _sdem('comply', '--workspace', ws, '--json')
                if out.strip().startswith('{'):
                    for f in json.loads(out).get('findings', []):
                        if f.get('outcome') not in ('non_compliant', 'unresolved'): continue
                        std, pat = f.get('standard') or {}, f.get('pattern') or {}
                        if std.get('id') == 'SDEM-COMPLETE':
                            across = 'approved' in (f.get('message') or '') or 'approved' in (f.get('detail') or '')
                            gaps.append({'record': f['record'], 'rule': f['rule'], 'kind': 'record', 'declared': f['record'] in declared, 'file': SUGG if across else LAYERS.get(f.get('layer'), 'the layer file'),
                                         'message': f"{f['record']} is not connected: {f.get('message')} ({f['rule']})"})
                        elif pat.get('id') and f.get('part') and f['part'].get('kind') == 'role':
                            d_ = (f.get('detail') or '').replace('planned — ', '')
                            if 'which is missing' in d_: continue   # follows from another part that is missing: said there
                            gaps.append({'record': f['record'], 'rule': f['rule'], 'kind': 'pattern', 'declared': True, 'file': 'the design',
                                         'message': f"the {pat.get('title')} pattern, which fits this design ({f['record']}): {d_}" + (f" — why it is needed: {f['part']['reasoning']}" if f['part'].get('reasoning') else '')
                                                    + _how(pat.get('id'), f['part']['id'])})
                undeclared = gaps
                if not allow_gaps:   # IN-11: every loose end is accounted for — linked, if the design says so, or declared; an author never fills it
                    errors += [{'file': g['file'], 'message': f"NOT ACCOUNTED FOR — {g['message']} — write the link only if the design says it; otherwise add {g['record']} to {NOTS}"} for g in gaps if not g['declared']]
        finally: shutil.rmtree(tmp, ignore_errors=True)
    return {'package': str(pkg), 'ok': not errors, 'errors': errors,
            'counts': {'records': {l: len(d['instances']) for l, d in docs.items()}, 'links': {l: len(d['relationships']) for l, d in docs.items()},
                       'suggestions': len(sugg.get('suggestions') or []), 'not_stated': len(nots.get('items') or [])},
            'bian': {'service_domains': domains, 'operations': ops, 'bank_local_not_bian': bian.get('bank_local_not_bian') or []},
            'gaps': sorted(undeclared, key=lambda g: (g['rule'], g['record'])), 'complete': not undeclared and not errors,
            'decisions': decs.get('decisions') or [],
            '_docs': docs, '_suggestions': good, '_not_stated': nots.get('items') or []}


def _how(pid, part):
    """For an author: what to write so that a pattern's part is there — the link the pattern draws to it, in the author's files' terms."""
    from .profile import shipped_patterns
    for _, d in shipped_patterns():
        if d['pattern']['id'] != pid: continue
        S = d['structure']; roles = {r['id']: r for r in S['roles']}; r = roles.get(part)
        if not r: return ''
        c = next((c for c in S.get('connectors', []) if part in (c['from'], c['to'])), None)
        if r['type'].startswith('A2.') and (r.get('when') or {}).get('name'): what = f" — to fix: name the BIAN service domain \"{r['when']['name']}\" in {BIAN}"
        else: what = f" — to fix: a {r['type']}" + (' where ' + ' and '.join(f'{k} = {v}' for k, v in r['when'].items()) if r.get('when') else '') + (f" (at least {r['min']})" if r.get('min', 1) > 1 else '')
        if c:
            a, b = roles[c['from']], roles[c['to']]
            what += (f", with the link «{a.get('label') or a['id']}» {c.get('kind') or c.get('relationship')} «{b.get('label') or b['id']}»"
                     + (f" in {SUGG}" if c.get('relationship') else ' in the layer file'))
        if r.get('zone'): what += f"; placed in a network zone of kind {next((z.get('zone_kind') for z in S.get('zones', []) if z['id'] == r['zone']), '')}"
        return what
    return ''


def _end(rec):
    """One end of a link between layers, as the registry holds it: id, type, version — and the canonical id a BIAN record carries."""
    return {'id': rec['id'], 'type': rec['type'], 'version': rec['version'], **({'canonical_id': rec['canonical_id']} if rec.get('canonical_id') else {})}


def _public(r): return {k: v for k, v in r.items() if not k.startswith('_')}


def render_check(r):
    L = [f"ERROR {e['file']}: {e['message']}" for e in r['errors']]
    c = r['counts']
    if r['errors']: L.append(f"{len(r['errors'])} thing(s) to fix in {r['package']} — nothing was loaded. Fix them and run the check again: a later check can show what these hid.")
    else:
        L.append(f"OK: {r['package']} passes SDEM's checks — " + ' · '.join(f'{l} {n} record(s), {c["links"][l]} link(s)' for l, n in c['records'].items())
                 + f"; {c['suggestions']} link(s) between layers; BIAN: {', '.join(r['bian']['service_domains']) or 'none named'}"
                 + ('; COMPLETE as written — every record connected, every part of every pattern that fits present' if r['complete'] else ''))
        if r['gaps']:
            L.append(f"For information — {len(r['gaps'])} thing(s) the design does not give, which SDEM's own rules (sdem aid) will go on to complete where they can, each marked inferred. Nothing for the author to do:")
            L += [f"  {g['message'].split(' — to fix:')[0]}" + ('' if g['declared'] else '  [NOT DECLARED]') for g in r['gaps'][:60]]
    return '\n'.join(L)


def load(pkg, workspace, person, dry_run=False, allow_gaps=False, accept=False):
    """IN-05…IN-10: check, then the one order — the workspace, the layers, BIAN, the patterns, the complete first draft, every proposed link,
    the report. A package with errors changes nothing."""
    from .validate import is_person
    from .layers import FILES
    ws = Path(workspace)
    if not is_person(person): raise IntakeError(f"--person {person!r}: taking a design in — its BIAN domains, the patterns it is checked against, the draft — is a person's decision; give your own name (CTL-21)")
    if ws.exists() and any((ws / f).exists() and json.loads((ws / f).read_text(encoding='utf-8')).get('instances') for f in FILES.values()):
        raise IntakeError(f'{ws} already holds records — sdem intake starts a design; change one that exists through change sets (sdem change propose)')
    r = check(pkg, allow_gaps)
    out = {**_public(r), 'workspace': str(ws), 'dry_run': bool(dry_run), 'accepted': bool(accept)}
    if r['errors']: return out
    if dry_run:
        out['would'] = {'load': r['counts']['records'], 'bian_add': r['bian']['service_domains'],
                        'invokes': {u: o['id'] for o in r['bian']['operations'] for u in o['used_by']},
                        'then': ['include every pattern SDEM ships that fits', 'sdem aid --complete-draft', 'sdem link', 'the report']}
        return out
    steps = [{'step': 'check', 'did': f"{sum(r['counts']['records'].values())} records, nothing refused"}]
    if not (ws / 'mappings.json').exists(): _must('new', '--workspace', ws, '--person', person, what='starting the workspace')
    steps.append({'step': 'workspace', 'did': str(ws)})
    tmp = Path(tempfile.mkdtemp(prefix='sdem-intake-'))
    try:
        for layer, d in r['_docs'].items():
            if not d['instances'] and not d['relationships']: continue
            src = tmp / LAYERS[layer]; src.write_text(json.dumps(d), encoding='utf-8'); cs = tmp / f'cs-{layer}.json'
            _must('change', 'diff', src, '--workspace', ws, '-o', cs, what=f'reading {LAYERS[layer]}')
            _must('change', 'propose', cs, '--workspace', ws, '--agent', AGENTS[layer], '--person', person, what=f'loading {LAYERS[layer]}')
        steps.append({'step': 'load', 'did': r['counts']['records']})
        if r['bian']['service_domains']: _must('bian', 'add', *r['bian']['service_domains'], '--workspace', ws, '--person', person, what='adding the BIAN service domains the package names')
        _invokes(ws, tmp, r['bian']['operations'], person)
        ev = ws / 'coordination' / 'events'   # IN-13: the change events of the design's first load — nothing existed before them to be changed, so there is no work to plan from them
        first = sorted(f.stem for f in ev.glob('CE-*.json')) if ev.exists() else []
        (ws / 'intake').mkdir(parents=True, exist_ok=True)
        (ws / 'intake' / 'first-load.json').write_text(json.dumps({'events': first, 'by': person, 'note': 'the change events of sdem intake: the first load of the design'}, indent=1), encoding='utf-8')
        steps.append({'step': 'bian', 'did': {'service_domains': r['bian']['service_domains'], 'operations': [o['id'] for o in r['bian']['operations']]}})
        avail = json.loads(_must('status', '--workspace', ws, '--json', what='reading the status')).get('patterns_available') or []
        for p in avail: _must('profile', 'include', p['include'], '--workspace', ws, '--person', person, '--reason', f"sdem intake: fits the design ({p['because']})", what=f"including {p['include']}")
        steps.append({'step': 'patterns', 'did': [p['include'] for p in avail]})
        accepted = []
        if accept:   # IN-12: the design is taken as authored — its links between layers are the person's, on the evidence of the design's own sections
            from .validate import load_registry
            from .files import write_json
            from .metamodel import Metamodel
            mmb = Metamodel.load(); reg = load_registry()['relationships']
            by0 = {i['id']: i for f in FILES.values() if (ws / f).exists() for i in json.loads((ws / f).read_text(encoding='utf-8'))['instances']}
            allp = []
            for g in r['_suggestions']:
                if g['source'] not in by0 or g['target'] not in by0: continue
                s_, t_ = by0[g['source']], by0[g['target']]
                allp.append({'mapping_id': f'AUTHOR-P{len(allp) + 1:03d}', 'source': _end(s_), 'relationship': g['relationship'],
                             'target': _end(t_), 'status': 'proposed', 'confidence': 0.8,
                             'evidence': [f"author:design section {g['section']}"], 'rationale': f"As authored ({g['basis']}, design section {g['section']}): {g['reason']}",
                             'baseline_id': 'intake', 'created_by': 'the author (sdem intake)', '_section': g['section']})
            pf = ws / 'aid' / 'AUTHOR-proposals.json'; write_json(pf, {'mappings': [{k: v for k, v in m.items() if k != '_section'} for m in allp]})
            release = (json.loads((Path(pkg) / BIAN).read_text(encoding='utf-8')).get('release') or '') if (Path(pkg) / BIAN).exists() else ''
            for m in allp:
                kinds = next((q['required_evidence'] for q in reg if q['relationship'] == m['relationship'] and mmb.is_a(m['source']['type'], q['source_type']) and mmb.is_a(m['target']['type'], q['target_type'])), [])
                bian_end = m['source']['type'].startswith('A2.') or m['target']['type'].startswith('A2.')
                ev = [x for k in kinds + (['bian_alignment_guidance'] if bian_end else []) for x in ('--evidence', f"{k}:design.md#{m['_section'] or ''}")]
                _must('approve', m['mapping_id'], '--proposals', pf, '--workspace', ws, '--reviewer', person, *ev, *(['--bian-release', release or '14.0.0'] if bian_end else []),
                      what=f"accepting {m['source']['id']} {m['relationship']} {m['target']['id']} as authored")
                accepted.append(f"{m['source']['id']} {m['relationship']} {m['target']['id']}")
            steps.append({'step': 'accept', 'did': f'{len(accepted)} link(s) between layers accepted as authored'})
        run = json.loads(_must('aid', '--workspace', ws, '--person', person, '--complete-draft', '--json', what='completing the first draft (sdem aid --complete-draft)'))
        steps.append({'step': 'draft', 'did': run.get('id')})
        _must('link', '--workspace', ws, '--out', ws / 'links', '--no-review', what='listing every proposed link (sdem link)')
        declined = []
        if accept and r['complete']:   # IN-13: taken as authored — what SDEM's rules would propose beside the author's links is not taken, and is recorded so
            lp = ws / 'links' / 'proposals.json'
            ids = [m['mapping_id'] for m in json.loads(lp.read_text(encoding='utf-8')).get('mappings', [])] if lp.exists() else []
            if ids:
                _must('reject', *ids, '--proposals', lp, '--workspace', ws, '--reviewer', person, '--reason', 'the design is taken as authored (sdem intake --accept): not one of its author\'s links',
                      what="declining the links SDEM's rules propose beside the author's")
                declined = ids
            steps.append({'step': 'as-authored', 'did': f"{len(declined)} link(s) SDEM's rules proposed beside the author's, declined"})
        by = {i['id']: i for f in FILES.values() if (ws / f).exists() for i in json.loads((ws / f).read_text(encoding='utf-8'))['instances']}
        have = set()
        for f in sorted((ws / 'aid').glob('*-proposals.json')) + [ws / 'links' / 'proposals.json']:
            if f.exists(): have |= {(m['source']['id'], m['relationship'], m['target']['id']) for m in json.loads(f.read_text(encoding='utf-8')).get('mappings', [])}
        mine = []
        for g in ([] if accept else r['_suggestions']):   # IN-08: what the author suggested and SDEM did not propose itself — proposals too, said to be the author's
            if (g['source'], g['relationship'], g['target']) in have or g['source'] not in by or g['target'] not in by: continue
            s, t = by[g['source']], by[g['target']]
            mine.append({'mapping_id': f'AUTHOR-P{len(mine) + 1:03d}', 'source': _end(s), 'relationship': g['relationship'],
                         'target': _end(t), 'status': 'proposed', 'confidence': 0.6 if g['basis'] == 'stated' else 0.4,
                         'evidence': [f"author_suggestion:design section {g['section']}"],
                         'rationale': f"Suggested by the design's author ({g['basis']}, section {g['section']}): {g['reason']} — not proposed by SDEM's rules; approve with the evidence its type needs",
                         'baseline_id': 'intake', 'created_by': 'the author (sdem intake)'})
        if mine:
            from .files import write_json as _wj
            _wj(ws / 'aid' / 'AUTHOR-proposals.json', {'mappings': mine})
        steps.append({'step': 'links', 'did': {'proposed': len(have) + len(mine), 'of_them_the_authors_alone': len(mine)}})
        kept = ws / 'intake'; (kept / 'package').mkdir(parents=True, exist_ok=True)
        for f in Path(pkg).iterdir():
            if f.is_file(): shutil.copy(f, kept / 'package' / f.name)
        status_text = _must('status', '--workspace', ws, what='reading the status')
        status = json.loads(_must('status', '--workspace', ws, '--json', what='reading the status'))
        report = render_report(r, run, status, status_text, mine, ws, person, accepted)
        (kept / 'report.md').write_text(report, encoding='utf-8')
        steps.append({'step': 'report', 'did': 'intake/report.md'})
        out.update(steps=steps, draft=run.get('draft') or {}, completeness=status.get('completeness'), patterns=status.get('patterns'), report='intake/report.md', author_proposals=len(mine))
        (kept / 'report.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    finally: shutil.rmtree(tmp, ignore_errors=True)
    return out


def render_report(r, run, status, status_text, mine, ws, person, accepted=()):
    """IN-09: one report — what came in, what the design does not state, the draft, and what is the person's to decide, weakest first."""
    d = run.get('draft') or {}; c = r['counts']
    L = [f'# Intake report — {Path(ws).name}', '',
         f"`sdem intake` by {person}. " + (f"{len(accepted)} link(s) between layers the design states were approved as authored (`--accept`). What SDEM's rules then inferred is neither confirmed nor approved: it is marked, below."
                                           if accepted else 'Nothing is approved, confirmed or rejected: that is yours, below.'), '',
         '## What came in', '',
         '| Layer | Records | Links inside |', '|---|---|---|'] + [f"| {l} | {n} | {c['links'][l]} |" for l, n in c['records'].items()] + ['',
         f"- SDEM refused nothing (a package with anything refused is not loaded).",
         f"- BIAN service domains named: {', '.join(r['bian']['service_domains']) or 'none'}" + (f"; operations: {', '.join(o['id'] for o in r['bian']['operations'])}" if r['bian']['operations'] else '') + '.',
         f"- Named by the design but not BIAN's (not loaded as service domains): {', '.join(r['bian']['bank_local_not_bian']) or 'none'}.",
         (f"- Links between layers: {len(accepted)} accepted as authored (`--accept`), each on the design section it cites, under {person}'s name." if accepted else
          f"- Links between layers the author suggested: {c['suggestions']} — now proposals; {len(mine)} of them only the author proposes (`aid/AUTHOR-proposals.json`)."),
         '',
         '## What the author said the design does not state', '']
    ns = r['_not_stated']
    if not ns: L.append('- nothing declared')
    else:   # said briefly: by what is missing, with the records — the author's full list is kept in intake/package/NOT-STATED.json
        groups = {}
        for x in ns: groups.setdefault(' '.join((x.get('detail') or '').split())[:110], []).append(x.get('record_id') or '—')
        L.append(f"{len(ns)} item(s) — the full list is `intake/package/{NOTS}`. By what is missing:")
        L.append('')
        for d_, ids_ in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:12]:
            L.append(f"- {d_}{'…' if len(d_) == 110 else ''} — {len(ids_)} record(s): {', '.join(sorted(set(ids_))[:5])}{' …' if len(set(ids_)) > 5 else ''}")
        if len(groups) > 12: L.append(f"- … and {len(groups) - 12} more kinds")
    if r['gaps']:
        rg = [g for g in r['gaps'] if g['kind'] == 'record']; pg = [g for g in r['gaps'] if g['kind'] == 'pattern']
        L += ['', f"**What the design does not give** — left to SDEM's rules, never filled by the author: {len(rg)} record(s) not connected ({', '.join(sorted({g['record'] for g in rg})[:8])}{' …' if len({g['record'] for g in rg}) > 8 else ''}); {len(pg)} part(s) a fitting pattern asks for. `sdem comply --workspace {ws}` lists each."]
    L += ['', '## The draft', '', 'Patterns asked before anything was inferred: ' + ('; '.join(p['title'] for p in d.get('patterns_consulted') or []) or 'none fits this design') + '.', '', '```']
    L += [l for l in status_text.splitlines() if l.startswith(('Completeness:', 'Draft:', 'Pattern '))] + ['```', '',
          '*Completeness* counts only what the design states. *Draft* counts as well what SDEM completed by its own written rules (`sdem aid`) — never by an AI. Everything SDEM added is marked inferred or proposed, with the rule that produced it.', '',
          '**Nothing below needs you for the design to be used.** It is what SDEM inferred, weakest first, for whenever you choose to confirm or reject it.', '',
          '## Yours to decide — weakest first', '']
    said = {x.get('record_id') for x in r['_not_stated']}
    links = d.get('links') or []
    first = [l for l in links if l['rule'] == 'AID-D08']; names = [l for l in links if l['rule'] != 'AID-D08']
    L += ['### 1. Placed by default — nothing in the design supports these', '']
    L += [f"- `{l['link'].replace('|', ' ')}` (asked by {l['asked_by']})" for l in first] + [f"- proposed: `{x}`" for x in d.get('default_proposals') or []] or ['- none']
    L += ['', '### 2. Inferred from a name, or by elimination', '']
    L += [f"- `{l['link'].replace('|', ' ')}` ({l['rule']}, asked by {l['asked_by']})" + (' — **the author listed this record as not stated: consider rejecting**' if set(l['link'].split('|')[::2]) & said else '') for l in names] or ['- none']
    L += ['', '### 3. Brought in by a pattern', '',
          f"- BIAN service domains: {', '.join(d.get('domains_added') or []) or 'none'}", f"- parts added as planned records: {', '.join(d.get('parts_added') or []) or 'none'}"]
    L += [f"- which record is the {x['label']}? {' or '.join(x['candidates'])} — " + (f"suggested: {x['suggested']}" if x['suggested'] else 'no name singles one out') + f"; you name it: `conforms_to` \"{x['conforms_to']}\" on the record" for x in d.get('parts_to_name') or []]
    L += ['', '### 4. Links between layers to approve', '', f"`sdem review {Path(ws) / 'links' / 'proposals.json'}` lists them with the evidence each needs" + (f"; the author's own {len(mine)} are in `aid/AUTHOR-proposals.json`." if mine else '.'), '',
          '### 5. Gaps left open', '']
    L += [f"- `{o['record']}` — {o['message']} ({o['rule']}): {o['why']}" for o in d.get('left_open') or []] or ['- none']
    L += ['', '### The commands — you run them', '', '```',
          f"sdem aid confirm '<source|kind|target>' --workspace {ws} --person <you>      # or: sdem aid reject '<…>' --workspace {ws} --person <you> --reason <why>",
          f"sdem aid confirm <record id> --workspace {ws} --person <you>                 # a BIAN domain or a part SDEM brought in",
          f"sdem approve <id> --proposals <file> --workspace {ws} --reviewer <you> --evidence <kind>:<ref>",
          f"sdem status --workspace {ws}", '```', '']
    return '\n'.join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem intake', formatter_class=argparse.RawDescriptionHelpFormatter, description=__doc__.split('\n\n')[0] + '\n\n' + __doc__.split('\n\n')[1],
                                 epilog='Examples:\n  sdem intake designs/ledger-package --check\n  sdem intake designs/ledger-package --workspace workspaces/ledger --person your.name --dry-run')
    ap.add_argument('package', help='the folder holding the package (the eight files of the authoring guide)')
    ap.add_argument('--check', action='store_true', help="check the whole package and say everything wrong at once — no workspace, nothing written; what its author runs before handing over")
    ap.add_argument('--workspace', dest='estate', metavar='DIR', help='the workspace to start with this design (a new folder, or one that holds no records yet)')
    ap.add_argument('--person', help='your name — a person')
    ap.add_argument('--dry-run', action='store_true', help='check, and say what would be loaded and done; write nothing')
    ap.add_argument('--allow-gaps', action='store_true', help='do not fail on a record that is neither connected nor declared in NOT-STATED.json (it is still listed). Without it, every loose end must be accounted for')
    ap.add_argument('--accept', action='store_true', help="take the design as authored: the links between layers its author wrote from the design are approved under your name, on the evidence of the design sections they cite — none is left for review. What SDEM's rules then infer stays marked inferred. Your decision, recorded as yours")
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    try:
        if a.check or not a.estate:
            if not a.check: raise IntakeError('give --check (the package alone) or --workspace DIR --person NAME (take it in)')
            r = check(a.package, a.allow_gaps)
            print(json.dumps(_public(r), indent=2) if a.json else render_check(r)); return 0 if r['ok'] else 1
        if not a.person: raise IntakeError('--person is required with --workspace: your own name')
        r = load(a.package, a.estate, a.person, a.dry_run, a.allow_gaps, a.accept)
    except IntakeError as e:
        print(f'ERROR: {e}', file=sys.stderr); return 2
    if a.json: print(json.dumps(r, indent=2)); return 0 if r['ok'] else 1
    if not r['ok']: print(render_check(r)); return 1
    if a.dry_run:
        w = r['would']
        print(render_check(r)); print(f"would start {r['workspace']}, load {w['load']}, add BIAN {w['bian_add'] or 'nothing'}, then: {'; '.join(w['then'])} — nothing written"); return 0
    print(f"taken in to {r['workspace']}: " + ' → '.join(s['step'] for s in r['steps']))
    print((Path(r['workspace']) / r['report']).read_text(encoding='utf-8'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
