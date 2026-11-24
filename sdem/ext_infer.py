"""Metamodel extensions that infer — MX-45…MX-52 (docs/design/sdem-metamodel-extensions-spec.md §16; the 0.22 plan, step 2, R-D5).

An extension that infers says so in its manifest:   "infers": ["aid", "link"]
SDEM asks it — only where the workspace's profile includes it (MX-10) — by running its program, never by importing it (EXT-02):

    sdem-<name> infer --workspace DIR --step aid|link --json

and reads one answer, format "sdem-inference/1":

    {"format": "sdem-inference/1",
     "records":   [{"layer": "<code or layer id>", "record": {id, type, version, name, lifecycle_status, …},
                    "rule": "<its rule id>", "reasoning": "…", "confidence": "low|medium|high", "evidence_class": "…", "source": "…", "from": "<ids>"}],
     "links":     [{"layer": "…", "source": id, "kind": "<link kind inside the layer>", "target": id, "rule", "reasoning", "confidence"}],
     "proposals": [{"source": id, "relationship": "<link type between layers>", "target": id, "rule", "rationale", "confidence", "evidence_class"}]}

SDEM checks every item as its own: a record's type must be one the metamodel (with the profile) knows, in a layer the workspace has; a
proposal's link type one the metamodel or the profile declares; nothing approved, rejected or already present is added again. What it
keeps it marks — a record or link `inferred` by the extension, a proposal `created_by` it — and writes only if the whole workspace still
passes its checks; what it refuses it says, with the reason, in the run record. An extension that fails, times out or answers in another
format is reported, never fatal (MX-50).
"""
import json, subprocess   # subprocess: its exceptions only — the program is run by sdem.extensions
from . import extensions as _ext

FORMAT = 'sdem-inference/1'
STEPS = ('aid', 'link')
BAND = {'low': 0.4, 'medium': 0.6, 'high': 0.8}
TIMEOUT = 300


def askable(step):
    """MX-45, MX-46: the installed extensions active in the workspace's profile whose manifest says they infer for this step — [(name, program, manifest)]."""
    from . import profile as _prof
    active = {str(a.get('extension') or '').strip() for a in ((_prof.ACTIVE or {}).get('aspects') or [])}
    from . import parts   # a built-in extension switched on (0.20's default for BIAN, BX-11) is included though no profile names it
    if parts.bian_on(): active.add(parts.EXT_BIAN.split(':', 1)[1])
    out = []
    for x in _ext.installed():
        m = x['manifest']; inf = m.get('infers') or []
        if x['name'] in active and step in (inf if isinstance(inf, list) else [inf]):
            out.append((x['name'], x['program'], m))
    return out


def ask(program, workspace, step):
    """MX-47: one extension's answer — (answer, None) or (None, why it could not be used)."""
    try:
        r = _ext.infer(program, workspace, step, TIMEOUT)   # run where SDEM runs extensions (PRIVACY.md §2)
    except subprocess.TimeoutExpired:
        return None, f'no answer within {TIMEOUT} s'
    except OSError as e:
        return None, f'could not be run: {e}'
    if r.returncode != 0:
        return None, f'exit {r.returncode}: ' + (r.stderr or r.stdout).strip()[-300:]
    try:
        d = json.loads(r.stdout)
    except ValueError:
        return None, 'its answer is not JSON'
    if not isinstance(d, dict) or d.get('format') != FORMAT:
        return None, f'its answer is not {FORMAT}'
    return d, None


def contribute(step, workspace, docs, known, *, run, person, now, rejected=(), approved=(), mm=None):
    """MX-48…MX-50: ask every extension that infers for this step, and check what it gives.
    docs: {layer code: layer document} — the workspace as it would be; changed in place with the records and links kept.
    known: {id: record} of every record (updated with the records kept). Returns (added {layer: [ids]}, proposals, report)."""
    from .metamodel import Metamodel
    from . import profile as _prof
    mm = mm or Metamodel.load()
    rels = {x['relationship'] for x in _prof.load_registry_rows()} | {x['relationship'] for x in ((_prof.ACTIVE or {}).get('link_types') or [])}
    code_of = {}   # a layer named by its code or its id
    for code in docs: code_of[code] = code
    try:
        from .identity import layer_id
        for code in docs:
            lid = layer_id(code)
            if lid: code_of[lid] = code
        from . import parts
        if parts.migrated() and 'application' in code_of: code_of.setdefault('data', code_of['application'])   # DL-12: in AID's 0.19 view Data is inside Application
    except Exception:
        pass
    added, proposals, report = {}, [], []
    proposals_only = step == 'link'   # MX-51: sdem link proposes links between layers; records and links inside a layer are aid's
    seen = set()
    for name, prog, m in askable(step):
        who = f"{name} {m.get('version', '')}".strip()
        ans, why = ask(prog, workspace, step)
        entry = {'extension': name, 'version': m.get('version'), 'records': 0, 'links': 0, 'proposals': 0, 'refused': []}
        report.append(entry)
        if ans is None:
            entry['refused'].append({'item': 'the answer', 'why': why}); continue
        def mark(x):
            return {'by': who, 'run': run, 'at': now, 'requested_by': person, 'step': f'extension:{name}', 'rule': str(x.get('rule') or ''),
                    'source': str(x.get('source') or f'the {name} extension'), 'reasoning': str(x.get('reasoning') or x.get('rationale') or ''),
                    'confidence': x.get('confidence') if x.get('confidence') in BAND else 'low', 'evidence_class': str(x.get('evidence_class') or 'rule'),
                    **({'from': x['from']} if x.get('from') else {})}
        if proposals_only and (ans.get('records') or ans.get('links')):
            entry['not_used'] = f"{len(ans.get('records') or [])} record(s) and {len(ans.get('links') or [])} link(s) inside a layer — sdem link takes proposals only; sdem aid takes them"
        for x in ([] if proposals_only else ans.get('records') or []):
            rec = x.get('record') if isinstance(x, dict) else None
            lvl = code_of.get(str((x or {}).get('layer') or ''))
            if not isinstance(rec, dict) or not rec.get('id') or not rec.get('type'):
                entry['refused'].append({'item': str(rec)[:80], 'why': 'a record needs an id and a type'}); continue
            if lvl is None:
                entry['refused'].append({'item': rec['id'], 'why': f"no layer {x.get('layer')!r} in this workspace"}); continue
            if rec['type'] not in mm.entities:
                entry['refused'].append({'item': rec['id'], 'why': f"{rec['type']} is not a type the metamodel or the profile knows"}); continue
            if rec['id'] in known or rec['id'] in rejected:
                continue   # already there, or a person rejected it: never inferred again
            rec = json.loads(json.dumps(rec))
            rec.setdefault('version', '1'); rec.setdefault('lifecycle_status', 'planned')
            rec.setdefault('attributes', {})['inferred'] = mark(x)
            docs[lvl].setdefault('instances', []).append(rec); known[rec['id']] = rec
            added.setdefault(lvl, []).append(rec['id']); entry['records'] += 1
        for x in ([] if proposals_only else ans.get('links') or []):
            lvl = code_of.get(str((x or {}).get('layer') or ''))
            s, k, t = (x or {}).get('source'), (x or {}).get('kind'), (x or {}).get('target')
            if lvl is None or not (s in known and t in known and k):
                entry['refused'].append({'item': f'{s} {k} {t}', 'why': 'a link needs its layer, its kind and two records the workspace holds'}); continue
            if f'{s}|{k}|{t}' in rejected or any((r.get('source'), r.get('kind'), r.get('target')) == (s, k, t) for r in docs[lvl].get('relationships', [])):
                continue
            docs[lvl].setdefault('relationships', []).append({'source': s, 'kind': k, 'target': t, 'inferred': mark(x)})
            added.setdefault(lvl, []); entry['links'] += 1
        if proposals_only:   # MX-53: a target design the extension drafts (no application layer yet) — its records may be a proposal's end
            for d in (ans.get('design') or []):
                for r in (d.get('instances') or []) if isinstance(d, dict) else []:
                    if isinstance(r, dict) and r.get('id') and r['id'] not in known: known[r['id']] = r
        for x in ans.get('proposals') or []:
            full = x.get('record') if isinstance(x, dict) and isinstance(x.get('record'), dict) else None   # MX-53: a proposal as its engine recorded it, kept whole
            if full: x = {**full, 'source': (full.get('source') or {}).get('id'), 'target': (full.get('target') or {}).get('id')}
            s, r_, t = (x or {}).get('source'), (x or {}).get('relationship'), (x or {}).get('target')
            if r_ not in rels:
                entry['refused'].append({'item': f'{s} {r_} {t}', 'why': f'{r_!r} is not a link type between layers the metamodel or the profile declares'}); continue
            if s not in known or t not in known:
                entry['refused'].append({'item': f'{s} {r_} {t}', 'why': 'both ends must be records the workspace holds'}); continue
            if (s, r_, t) in approved or (s, r_, t) in seen:
                continue
            seen.add((s, r_, t))
            ref = lambda i: {'id': i, 'type': known[i]['type'], 'version': known[i].get('version', '1'), **({'canonical_id': known[i]['canonical_id']} if known[i].get('canonical_id') else {})}
            if full:   # kept as recorded — only who made it is SDEM's to say (R-D11)
                proposals.append({**json.loads(json.dumps(full)), 'status': 'proposed', 'created_by': who}); entry['proposals'] += 1; continue
            conf = x.get('confidence'); conf = BAND.get(conf, conf if isinstance(conf, (int, float)) else 0.4)
            proposals.append({'source': ref(s), 'relationship': r_, 'target': ref(t), 'status': 'proposed', 'confidence': conf,
                              'evidence_class': str(x.get('evidence_class') or 'rule'), 'evidence': [f"engine_rationale:{run} {name}:{x.get('rule') or ''}".strip()],
                              'rationale': f"Inferred by {who} ({x.get('rule') or 'its rule'}): {x.get('rationale') or x.get('reasoning') or ''}".rstrip(': '),
                              'baseline_id': run, 'created_by': who})
            entry['proposals'] += 1
        if proposals_only:   # MX-53: what its rules reported but did not propose, and a target design — sdem link writes them with its own
            ok = lambda c: isinstance(c, dict) and (c.get('source') or {}).get('id') in known and (c.get('target') or {}).get('id') in known
            entry['_candidates'] = [{**c, 'created_by': who} for c in (ans.get('candidates') or []) if ok(c)]
            entry['_design'] = [d for d in (ans.get('design') or []) if isinstance(d, dict) and d.get('level')]
    return added, proposals, report


def for_link(workspace, now):
    """MX-51: the proposals the workspace's extensions make for `sdem link` — (proposals, report), each end a record of the workspace,
    its own layers included, and nothing a person approved or rejected proposed again."""
    from .connect import estate_docs
    from .identity import load
    from pathlib import Path
    docs, registry = estate_docs(workspace)
    from . import profile as _prof
    for l in ((_prof.ACTIVE or {}).get('layers') or []):   # the extensions' own layers (MX-48): their records may be a proposal's end
        f = Path(workspace) / str(l.get('file') or '')
        if l.get('file') and f.is_file() and l['file'] not in docs: docs[l['file']] = load(f)
    known = {i['id']: i for d in docs.values() for i in d.get('instances', [])}
    approved = {(m['source']['id'], m['relationship'], m['target']['id']) for m in registry.get('mappings', []) if m.get('status') in ('approved', 'rejected')}
    rej = Path(workspace) / 'aid' / 'rejected.json'
    rejected = {r.get('id') for r in (load(rej).get('rejected') or [])} if rej.exists() else set()
    _, props, report = contribute('link', workspace, {}, known, run='RUN', person='sdem link', now=now, rejected=rejected, approved=approved)
    return props, report


class PhaseError(Exception):
    """MX-54: the extension that provides a built-in extension's part of sdem aid did not answer a phase — the run stops (its part cannot be skipped)."""


def ask_phase(phase, workspace, state):
    """MX-54: one phase of the built-in extension's part of `sdem aid` (BIAN's) from the extension that provides it — its result, or PhaseError.
    The state goes in a file of its own, outside the workspace, removed after."""
    import os, tempfile
    from . import parts
    on = parts.EXT_BIAN.split(':', 1)[1]
    found = builtin_provider('aid-phases')
    if not found: raise PhaseError(f'no installed extension provides {on}\'s part of sdem aid')
    prog = found[1]
    fd, path = tempfile.mkstemp(prefix='sdem-aid-', suffix='.json')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f: json.dump(state, f)
        try:
            r = _ext.infer(prog, workspace, 'aid', TIMEOUT, phase=phase, state=path)
        except (subprocess.TimeoutExpired, OSError) as e:
            raise PhaseError(f'{on}: phase {phase}: {e}')
    finally:
        os.unlink(path)
    if r.returncode != 0: raise PhaseError(f'{on}: phase {phase}: exit {r.returncode}: ' + (r.stderr or r.stdout).strip()[-300:])
    try:
        d = json.loads(r.stdout)
    except ValueError:
        raise PhaseError(f'{on}: phase {phase}: its answer is not JSON')
    if not isinstance(d, dict) or d.get('format') != FORMAT or d.get('phase') != phase or not isinstance(d.get('result'), dict):
        raise PhaseError(f'{on}: phase {phase}: its answer is not {FORMAT} for this phase')
    return d['result']


def builtin_provider(step):
    """The installed extension that provides the built-in extension that is on (BIAN) for this step — (name, program, manifest), or None."""
    from . import parts
    on = parts.EXT_BIAN.split(':', 1)[1] if parts.bian_on() else None
    return next((x for x in askable(step) if x[0] == on), None) if on else None


def provides_builtin(step):
    """0.22 step 3b: does an installed extension provide the inference of a built-in extension that is on (BIAN)? Then SDEM's own copy of
    its steps does not run — the extension's answer stands in for it (MX-53)."""
    from . import parts
    on = parts.EXT_BIAN.split(':', 1)[1] if parts.bian_on() else None
    return bool(on) and any(n == on for n, _, _ in askable(step))
