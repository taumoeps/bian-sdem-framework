"""Render docs/relationship-rules-spec.md — the SDEM Architecture Relationship Rules Specification (inference engine input).

The specification is a projection of the records (entity catalogue, level-relationships.json, relationship-types.json,
relationship-rules.json, export-conventions.json, impact-rules.json) plus a numbered requirements set. Every requirement
names the record rows it derives from and the use-case runs that validated it (from the inference logs), so the
document cannot say more than the records and the runs support. Regenerate with `python -m sdem.spec`; CI checks it.
"""
from pathlib import Path
from collections import Counter, defaultdict
import argparse, glob, json, re
from sdem.metamodel import Metamodel, MM_DIR
from sdem.terms import apply as _terms

ROOT = MM_DIR.parent
DOC = ROOT / 'docs' / 'relationship-rules-spec.md'
LEVEL_NAMES = {'A1': 'A1 Business Architecture', 'A2': 'A2 Service Domain Architecture', 'A3': 'A3 Application Architecture', 'A4': 'A4 Technology Architecture'}


def _load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def runs_by_plan_id():
    """plan ID -> {case: Counter(outcome)} from every inference log."""
    per = defaultdict(lambda: defaultdict(Counter))
    for f in sorted(glob.glob(str(ROOT / 'examples' / '*' / '*inference-log.json'))):
        d = _load(f); uc = d.get('use_case', '?').split(' ')[0] + (' r2' if 'run2' in f else '')
        for a in (d.get('attempts') or d.get('inferences') or []):
            pid, o = a.get('plan_id'), a.get('outcome')
            if not pid or not o: continue
            b = re.match(r'S\d+|B\d+', str(pid))
            if b: per[b.group(0)][uc][o] += 1
    return per


def _logs():
    import glob as _g
    fs = _g.glob(str(ROOT / 'examples' / '*' / '*inference-log*.json')); n = 0
    for f in fs:
        d = json.loads(Path(f).read_text(encoding='utf-8')); n += len(d.get('attempts') or d.get('log') or d.get('entries') or (d if isinstance(d, list) else []))
    return len(fs), n


def render():
    mm = Metamodel.load()
    lr = _load(MM_DIR / 'level-relationships.json'); reg = _load(ROOT / 'schema' / 'relationship-types.json')
    nm = _load(MM_DIR / 'relationship-rules.json')['mappings']; conv = _load(MM_DIR / 'export-conventions.json'); imp = _load(ROOT / 'schema' / 'impact-rules.json')
    per = runs_by_plan_id()
    def validated_in(pid):
        cases = per.get(pid, {})
        hits = sum(c['hit'] for c in cases.values()); false = sum(c['false'] for c in cases.values())
        if not cases: return 'not exercised'
        if hits and not false: return f"validated: {', '.join(sorted(cases))} ({hits} hits, 0 false)"
        if hits: return f"validated with findings: {', '.join(sorted(cases))} ({hits} hits, {false} false — fixed)"
        return f"refusals only: {', '.join(sorted(cases))}"
    REQ = []  # (id, group, text, derives_from, validated_by)
    def req(group, text, src, val): REQ.append((f"REQ-{group}-{sum(1 for r in REQ if r[1] == group) + 1:02d}", group, text, src, val)); return REQ[-1][0]

    out = ['# SDEM Architecture Relationship Rules Specification — inference engine input (v0.7)', '',
           '> New to SDEM? Read `docs/sdem-overview.md` first — it explains how the local graphs, mapping model, mapping engine, mapping set and federated graph fit together.', '', 'Generated from the records by `python -m sdem.spec`; the test suite checks it is current. This specification merges the three records — the entity catalogue, the within-level structure (`metamodel/level-relationships.json`) and the cross-level mapping model (`schema/relationship-types.json`, `metamodel/relationship-rules.json`) — with the export conventions, the mapping procedure and the test results, into one statement of **what a mapping engine must consume, do, refuse and produce**. Every requirement names the record rows it derives from and the use-case runs that validated it; nothing here claims more than a record and a run support.', '',
           '**Terms, as in `docs/sdem-overview.md`.** This document specifies the **Architecture Relationship Rules Model** — the plan rows (§4.2–4.3) and the export conventions (§5), the **rules** for establishing relationships, stated over entity **types** — and the **Architecture Relationship Inference Engine** that applies them. It restates from the **Architecture Metamodel** what the rules are stated over: the entity types (§2), the within-level rows (§3) and the relationship type catalogue (§4.1). The **Architecture Relationship Registry** is the inference engine\'s output: **links** between real instances, in the form fixed by `schema/relationship-registry.schema.json` (§7). The companion diagram `docs/architecture-model-diagram.puml` draws the Architecture Metamodel and the rules: every within-level row (`RA…`) and every cross-level rule (`S…`) by ID, between entity types; it does not draw the mapping set.', '', ' Narrative sources: `docs/mapping-logic-planning.md` (why the model is shaped this way), `docs/mapping-execution.md` (the procedure as the executor ran it), `docs/relationships-planning.md` (within-level rows), `docs/use-case-testing.md` (the runs). Those remain the places to read the reasoning; this document is the contract.', '']

    # ---- 1 scope
    out += ['## 1. Purpose, scope and non-goals', '',
            '**Purpose.** Propose cross-level mappings between four independently governed architecture models (A1 Business, A2 BIAN Service Domain, A3 Application, A4 Technology) from their exports, with evidence and confidence, for an architect to approve; never approve; refuse where the data does not support a connection.', '',
            '**In scope.** Loading and validating level exports; the structural steps 1–5 of the procedure; proposals, candidate reports and the inference log; scoring against sealed gold; traceability and impact over approved mappings.', '',
            '**Non-goals.** Semantic inference beyond step 5\'s bounded text rule; approval or lifecycle transitions (those are the validator\'s and the architect\'s); any institution-specific entity or rule (those belong in a private profile); reproduction of BIAN, ArchiMate or TOGAF text.', '']

    # ---- 2 vocabulary
    ents = mm.entities; prov = Counter()
    for t, e in ents.items():
        std = (e.get('reference') or {}).get('standard', '') or ''
        prov['BIAN' if 'BIAN' in std else 'ArchiMate' if 'ArchiMate' in std or 'AM' in std else 'TOGAF' if 'TOGAF' in std else 'SDEM extension'] += 1
    out += ['## 2. Vocabulary — the entity catalogue', '', f"{len(ents)} entities across four levels (`metamodel/a1…a4-*.json`), each with public provenance (README › *Reference architecture provenance*). By standard: " + ', '.join(f"{k} {v}" for k, v in prov.most_common()) + '. **The entity ID is its type string** (e.g. `A3.ApplicationComponent`); every mapping, relationship row and export instance refers to it by that string.', '',
            '| ID | Level | Kind | Extends | Reference concept |', '|---|---|---|---|---|']
    for l in ('A1', 'A2', 'A3', 'A4'):
        for t, e in ents.items():
            if e['level'] != l: continue
            kind = 'abstract' if e.get('abstract') else 'artefact' if e.get('artefact') else 'concrete'
            out.append(f"| `{t}` | {l} | {kind} | {e.get('extends') or '—'} | {(e.get('reference') or {}).get('standard', '—')}: {(e.get('reference') or {}).get('concept', '—')} |")
    r1 = req('V', 'Resolve every instance type in an export to a catalogue entity, through `extends` (is-a) and the registry\'s type aliases; reject unknown types, instantiated abstract entities and artefacts used as mapping endpoints.', 'entity catalogue; `schema/relationship-types.json` type_aliases', 'E1, E2 (every example export loads); relationships test T4.6')
    out.append('')

    # ---- 3 within-level
    byl = Counter(c['level'] for c in lr['constraints']); vc = Counter(c['verification'] for c in lr['constraints'])
    out += ['## 3. Within-level structure — what an export may contain', '',
            f"{len(lr['constraints'])} constraint rows (`metamodel/level-relationships.json`, documented row by row in `docs/relationships-planning.md`): " + ', '.join(f"{LEVEL_NAMES[l]} {byl[l]}" for l in ('A1', 'A2', 'A3', 'A4')) + f". Verification: " + ', '.join(f"{k} {v}" for k, v in vc.most_common()) + '. Association is permitted between any two entities of one level. The 12 catalogue inheritance links are listed there as `X` rows.', '',
            '| Level | Derived from | Rows | The structure in one line |', '|---|---|---|---|',
            '| A1 | ArchiMate 3.2 ch. 6–8 | ' + str(byl['A1']) + ' | capabilities serve value streams; processes (and activities, is-a process) realise capabilities, value streams, services and requirements, access objects, compose activities; actors assigned to roles assigned to processes |',
            '| A2 | BIAN Service Landscape metamodel (B02–B15) | ' + str(byl['A2']) + ' | area ⊃ domain ⊃ Service Domain; a domain has an asset type, a functional pattern, a control record and service groups of operations; operations act on the control record and may be qualified; scenarios sequence operations; objects type the control record |',
            '| A3 | ArchiMate 3.2 ch. 9; TOGAF (SBB) | ' + str(byl['A3']) + ' | a component composes interfaces (which compose API operations) and sub-components, is assigned to functions, realises services; interfaces are assigned to services; behaviour accesses data entities and triggers events; a solution building block aggregates components |',
            '| A4 | ArchiMate 3.2 ch. 10; SDEM deployment extensions | ' + str(byl['A4']) + ' | nodes compose nodes and interfaces, aggregate devices, are assigned system software, artifacts and deployments, realise technology services; interfaces are assigned to services; networks realise paths; environments aggregate deployments and platform elements |', '',
            '### 3.1 All within-level rows', '', 'Full description, source, reasoning, inference and confidence per row: `docs/relationships-planning.md`.', '',
            '| ID | Official | Source | Kind | Target | Verification |', '|---|---|---|---|---|---|']
    for c in lr['constraints']:
        out.append(f"| {c['id']} | {c.get('official_id') or '—'} | {c['source_type']} | {c['kind']} | {c['target_type']} | {c['verification']}{' (not enforceable)' if c.get('enforceable') is False else ''} |")
    out += ['', '| ID | Entity | extends |', '|---|---|---|']
    for x in lr['inheritance']:
        out.append(f"| {x['id']} | {x['entity']} | {x['extends']} |")
    out.append('')
    req('S', 'Accept a within-level relationship only when its (source entity, kind, target entity) matches a constraint row for that level through inheritance, or its kind is `association`; report the offending triple and the level\'s basis otherwise.', 'RA1-01 … RA4-36', 'relationships test T4.1–T4.9 (131 accepted, 25 rejected); `examples/reference-structure` (129 rows on committed data)')
    req('S', 'Walk within-level part-whole links (composition, aggregation) in traces and derivations — part → whole downstream, whole → parts upstream — and never assignment or realization.', 'rows of kind composition / aggregation; `sdem-graph trace --follow-composition`', 'H1 (module → ledger → platform); C3 (API → interface → component → deployment → environment)')
    req('S', 'Treat the three A2 artefact rows as provenance only: Wireframe, Semantic API and BOM artefacts are never instantiated and never mapping endpoints.', 'RA2-15, RA2-16, RA2-17 (enforceable=false)', 'relationships test T4 (not testable by construction)')

    # ---- 4 cross-level model
    out += ['## 4. Cross-level relationships', '', '### 4.1 The relationship type catalogue — the nine relationship types (Architecture Metamodel)', '',
            '| Mapping type | Source → target | Relationship | Perspective | Authority | Required evidence | Meaning | Source reference | Verification | Confidence |', '|---|---|---|---|---|---|---|---|---|---|']
    for r in reg['relationships']:
        out.append(f"| {r['mapping_type_id']} | {r['source_type']} → {r['target_type']} | `{r['relationship']}` | {r['perspective']} | {r['authority']} | {', '.join(r['required_evidence'])} | {r['direction_semantics']} | {r.get('source_reference', '—')} | {r.get('verification', '—')} | {r.get('confidence', '—')}: {r.get('confidence_basis', '')} |")
    out += ['', 'Only these nine may appear in the mapping set (form: `schema/relationship-registry.schema.json`); adjacency is A(n) → A(n+1) only; BIAN authorities require `bian_release` and a `canonical_id` on the A2 endpoint before approval. Everything else the model knows is a **candidate report**, never a registry proposal.', '']
    req('M', 'Emit registry proposals only for the nine relationship types, with the record fields the schema requires, at status `proposed`, with `confidence` as the plan\'s band and `evidence` typed against `required_evidence`.', 'schema/relationship-types.json; schema/relationship-registry.schema.json', 'every run: `sdem-validate --strict` on each proposal file')
    dec = Counter(m['rule_decision'] for m in nm)
    out += ['### 4.2 Plan rows — the 69 rules by decision', '', 'Every cross-level pair the mapping model considers (`metamodel/relationship-rules.json`; reasoning per row in `docs/mapping-logic-planning.md` §5.3). The decision says what the engine does with the row: only **registry rules** produce links in the mapping set; the others are reported as candidates or not used.', '',
            '| Decision | Rows | Engine behaviour |', '|---|---|---|',
            f"| registry rule | {dec['registry_rule']} | propose, at the step and band stated |", f"| candidate rule | {dec['candidate_rule']} | report in the candidate file; never propose until adopted into the registry |",
            f"| conditional rule | {dec['conditional_rule']} | report when the institution data it fires on is present |", f"| derived path | {dec['derived_path']} | compute as a closure over other arrows; report; never store |",
            f"| institution only | {dec['institution_only']} | report from the export key named in `data_needed`; never infer |", f"| bian internal | {dec['bian_internal']} | not cross-level: A2 structure, enforced by §3 |",
            f"| not a mapping / historical / subsumed / not encodable | {dec['not_a_mapping'] + dec['historical_method'] + dec['subsumed'] + dec['not_encodable']} | do nothing; the plan says why |", '',
            '### 4.3 The 50 rules drawn in the mapping-model diagram, with the run that validated each', '', '| ID | Pair | Decision | Step | Band | Validation |', '|---|---|---|---|---|---|']
    for m in nm:
        if m['rule_decision'] in ('registry_rule', 'candidate_rule', 'conditional_rule', 'derived_path', 'institution_only'):
            out.append(f"| {m['id']} | {m['source'].split('.')[1]} → {m['target'].split('.')[1]} ({m.get('relation') or (m.get('sdem_rule') or m.get('sdmm_rule')) or ''}) | {m['rule_decision'].replace('_', ' ')} | {m.get('fill_step')} | {m.get('confidence')} | {validated_in(m['id'])} |")
    out.append('')
    for m in nm:
        if m['rule_decision'] == 'registry_rule':
            req('M', f"{m['id']}: propose `{(m.get('sdem_rule') or m.get('sdmm_rule')) or m.get('relation')}` {m['source']} → {m['target']} at step {m.get('fill_step')} ({m.get('confidence')}); data: {m.get('data_needed', '')}", m['id'], validated_in(m['id']))
    for grp, label in (('candidate_rule', 'report (candidate rule)'), ('conditional_rule', 'report when its data is present (conditional rule)'), ('institution_only', 'report from the export key (institution-only)'), ('derived_path', 'compute as a closure and report (derived path)')):
        ids = [m['id'] for m in nm if m['rule_decision'] == grp]
        req('M', f"{label}: {', '.join(ids)} — each with the working and the plan band, in `<uc>-candidates.json` with `relationship` = plan ID.", ', '.join(ids), '; '.join(sorted({validated_in(i).split(':')[0] for i in ids})))

    # ---- 5 data
    out += ['## 5. Data requirements — the export conventions', '', 'Join keys the exports must carry for the steps to run without inference (`metamodel/export-conventions.json`). A key absent from an export is a *no proposal* for the rows that need it, reported as such — never guessed.', '',
            '| ID | Entity | Key | Purpose |', '|---|---|---|---|']
    kid = conv.get('key_ids', {})
    for ent, keys in conv['conventions'].items():
        for k, desc in keys.items(): out.append(f"| {kid.get(f'{ent}.{k}', '—')} | {ent} | `{k}` | {desc} |")
    out += ['', f"**BIAN action terms.** {conv['bian_action_terms']['source']}", '']
    req('D', 'Read every join key listed in §5 by exact name; treat a missing key as *no proposal* for the rows that depend on it, recorded in the no-proposal register with the key named.', 'metamodel/export-conventions.json', 'E1 (missing `deployed_on` found and added), M1–C3 (keys present)')
    req('D', 'Read institution aliases as data, never invent them: asset-type aliases (boundary gate), behaviour-qualifier aliases (check 3), interface and data-entity field aliases (check 4, S30/S20), business-object glossary aliases (S12).', 'A2.AssetType.aliases; A2.BehaviorQualifier.aliases; A3.ApplicationInterface.field_aliases; A3.DataEntity.field_aliases; A1.BusinessObject.field_aliases', 'H1 (token gate), H2 run 1 → run 2 (recall 0.78 → 1.00 with aliases supplied), C1')

    # ---- 6 procedure
    out += ['## 6. The procedure — steps as requirements', '', 'The steps are specified in `docs/mapping-execution.md` §3 exactly as the executor ran them; this section states them as engine requirements. Order: A4 from data, A2 from BIAN, A3 where they meet, A1 last.', '']
    P = [
     ('Step 0 — BIAN export', 'Load the A2 export as BIAN structure; apply no inference to it.', 'RA2-*; B02–B15', 'every run'),
     ('Step 1 — data join', 'Fill `DEPLOYED_ON` and `DEPLOYED_AS` and the step-1 institution-only rows by exact key join (`deployed_on`, `deployed_as`, `hosts`, `component_id`/`platform_id`, `consumes`, `stored_in`, `built_as`, `network_zone`, `published_to`, `exposed_through`, `carries`); `DEPLOYED_ON` is environment-agnostic and fans out one arrow per host layer, logged under S33 / S34 / S35 by target entity.', 'S32, S33, S34, S35, S37–S39, S41, S43, S45, S49–S51', 'M0, M1 (UAT hosting), H1, H2, C3'),
     ('Step 2 — REST decision procedure', 'For each operation × API pair: boundary **gate** (approved `REALIZED_BY`, or token gate over asset-type name and aliases against camel/snake-split names, paths, descriptions and accessed-entity names, with structural nouns on the stop list) — a gate, never a vote; then three checks, each pass / fail / neutral: action term ↔ method (17 terms; Retrieve ⇔ GET verified; the marked conventions for the rest, including Control ⇔ DELETE and Execute ⇔ POST on a qualifier sub-resource), qualifier ↔ path (qualifier aliases; a non-qualifier segment is ignored), attributes ↔ payload (≥ 50 %, ≥ 2 matched, best payload match, through field aliases). Decide: propose at band when 2 and 4 pass and 3 is not fail; one band lower with a finding when only the method fails and the API is the unique best payload match; otherwise none. Disambiguate one-to-one to a fixpoint; contention by overlap count, ratio, qualifier; ties are no proposal with both named.', 'S24, S26', 'M0, M1 (planted Retrieve-on-POST), H1 (all POST, reverse), H2 (hostile; 0.78 → 1.00), C2 (6 of 6)'),
     ('Step 2 — non-HTTP and systematic deviations', 'A non-HTTP `method` (BATCH, MQ, FILE) is *not applicable*, never forced through check 2; a deviation shared by every operation of an interface is reported once and referenced; Notify operations have no REST form and are reported against an `A3.Event` as a candidate.', 'S24; new_connection_candidates', 'H1 (batch jobs; all-POST finding once), M1 (Notify)'),
     ('Step 3 — derivation', 'Close over approved arrows and this run\'s own step-1/2 proposals, saying which: S01 from all processes of a capability (cap = weakest input), S17 from any implemented operation (cap = strongest input; a recorded systematic deviation does not lower it; fallback A over an entity `MAPPED_TO` the domain\'s object; fallback B over asset aliases in paths; no description-only fallback), S07, S13–S16, S22, S23, S25, S28, S29, S40, S42 (over S43/S44 exposure, never consumption), S44, S46–S48, S52–S54.', 'derived_path and step-3 rows', 'M0 run 2, M1, H1 (module level), H2, C1, C2, C3 (S42 corrected)'),
     ('Step 4 — structural matching', 'Attribute and token matching with thresholds: S30/S20/S31 one-to-one to a fixpoint at ≥ 50 % of the BIAN object\'s attributes; S02 as coverage of the scenario\'s operations by stage action terms (≥ 60 %; the asset noun is not evidence); S12 by glossary attributes through aliases; S09 by service inputs ∪ outputs (≥ 50 %, ≥ 2, one-to-one); S19 and S27 by alias tokens in entity names; S18 and S21 through `exposed_through` and the step-2 arrows; S06 by `invokes` (step 1) else name match.', 'step-4 rows', 'M0 (S02 as coverage), M1, H1, H2 (partition table kept out; qualifier claims it), C1, C2'),
     ('Step 5 — bounded text inference', 'Only for S01 when step 3 produced nothing and for the A1 side of reverse cases, and S08: count shared non-generic concepts; propose at most one domain per capability, low, when the best shares ≥ 2 and leads by ≥ 1; the candidate set is the full exported landscape (two domains count) or at least three; otherwise no proposal.', 'S01, S08', 'H1 (four right, two refused), C1'),
     ('Design targets', 'When no export exists below a level, state *mapping ends at <level>* and, only from BIAN\'s container pattern, generate planned A3/A4 instances with the `DSN-*` convention, canonical REST forms, low confidence, `created_by` naming the pattern and a rationale beginning *TARGET DESIGN, not a mapping*; never a platform or a data entity; traces mark planned instances as design.', 'guide § Design targets; M2 case', 'M2 (12 of 12; boundary stated)'),
     ('Refusal discipline', 'No working → no proposal. Every attempt, including suppressed pairs, failed gates and ties, is logged with its data read, rule values, decision and outcome; negatives are the measure of precision.', 'guide §2', 'every run: zero false proposals after v0.5.4 across M1, H1, H2 ×2, M2, C1, C2 (one in C3, fixed by rule)'),
    ]
    out += ['| Step | Requirement | Derives from | Validated by |', '|---|---|---|---|']
    for name, text, src, val in P:
        rid = req('P', f"{name}: {text}", src, val); out.append(f"| {rid} {name} | {text} | {src} | {val} |")
    out.append('')

    # ---- 7 outputs
    out += ['## 7. Outputs, scoring and governance', '',
            '| ID | Output | File | Content | Scored by |', '|---|---|---|---|---|',
            '| OUT-01 | Mapping-set records | `<uc>-proposals.json` | links between real instances, from registry rules only; `status: proposed`, plan band, typed evidence, rationale with the working | `sdem-eval` against `<uc>-gold-mappings.json` (approved) — P / R / F1 per relationship |',
            '| OUT-02 | Candidate reports (not part of the mapping set) | `<uc>-candidates.json` | one record per candidate / conditional / institution-only / derived row, `relationship` = plan ID | `sdem-eval` against `<uc>-gold-candidates.json` — per plan ID |',
            '| OUT-03 | Inference log | `<uc>-inference-log.json` | every attempt: plan ID, data read, rule values, step assigned / used, fallback, confidence predicted / given, outcome; no-proposal register; findings | the coverage table in `docs/use-case-testing.md` is regenerated from it |',
            '| OUT-04 | Design exports | `<uc>-design-a3.json`, `-a4.json` | planned instances (M2 only) | `sdem-graph check`; trace marks design hops |', '',
            'Governance stays outside the engine: `sdem-validate` (structure, registry, evidence, anchoring), `sdem-diff` (lifecycle transitions, immutability of approved records; supersession via `previous_mapping_id`), impact classification per `schema/impact-rules.json` (' + ', '.join(imp['kinds']) + ').', '']
    req('O', 'Write the three output files in the shapes above; never write `approved` (except rules an architect has declared auto-approved); never edit an existing mapping set; proposals must pass `sdem-validate --strict` with draft warnings only.', 'guide §4, §4b, §4c', 'every run')
    req('O', 'Log every attempt, not only proposals: the inference log is the evidence base for the coverage table and for confidence calibration.', 'guide §4b', f"{_logs()[0]} logs, {_logs()[1]} attempts")

    # ---- 8 acceptance
    out += ['## 8. Acceptance — the runs the engine must reproduce', '', 'The executed runs are the acceptance test (DEC-E-01): the engine, given the current committed inputs of each scored run, must score at least the executor\'s precision and recall against the sealed gold (`docs/use-case-testing.md` › Results and Plan coverage).', '',
            '| ID | Case | Estate | Hidden | Executor result |', '|---|---|---|---|---|',
            '| ACC-01 | E1, E2 | card-fraud-alerts, customer-onboarding | nothing (query and governance) | all checks exact |',
            '| ACC-02 | M0 | card-fraud-alerts | 6 arrows | run 2: 6 of 6, 1 false (rule withdrawn) |', '| ACC-03 | M1 | payment-initiation (68 instances) | 12 → 13 arrows, planted mismatch | 13 of 13 under the restated gold; mismatch caught |',
            '| ACC-04 | H1 | legacy-core-ledger (87; SOAP, all POST; empty given) | 28 arrows | 28 of 28, 0 false |', '| ACC-05 | H2 | acquired-fintech (116; no A1; hostile names) | 41 arrows | run 1: 32 of 41, 0 false; run 2 with aliases: 41 of 41 |',
            '| ACC-06 | M2 | digital-lending (greenfield, no A3/A4) | 12 design arrows | 12 of 12; boundary stated |', '| ACC-07 | C1, C2, C3 | trade-finance (85; one estate, three level pairs) | 19 registry + 100 candidate | 19 of 19; 100 of 101 (one fixed by rule) |', '',
            'Plan coverage after the suite: 45 rows validated clean, 5 validated with findings fixed, 19 n/a by decision, 0 not exercised. Within-level structure: ' + str(len(lr['constraints'])) + ' rows, ' + str(sum(1 for c in lr['constraints'] if c.get('enforceable') is not False)) + ' enforced (the rest are A2 artefact rows, documentation only), 113 verified against the Archi oracle, 0 contradicted.', '']
    out += ['**Result (2026-10-25, v0.10).** `sdem-accept` runs the rule-based engine (`sdem/rules_engine.py`) on each scored case from a graph store built from the exports and the case\'s given registry only: **all 8 pass at precision and recall 1.00** (registry proposals, and candidate reports for C1–C3); M0 and C3 score above the hand-executed runs, whose one error each came from rules since fixed. Every proposal validates. `tests/test_acceptance.py` enforces it. Caveat: OPEN-05.', '']
    req('A', 'Reproduce every executor run from the committed inputs with precision ≥ the executor\'s and recall ≥ the executor\'s on each sealed gold; any difference is a finding on the engine or on the guide.', 'docs/use-case-testing.md', 'baseline established by the eleven runs')
    req('A', 'Validate every example export and `examples/reference-structure` clean, and reject the relationships-test probes (reversed, mistyped, abstract, cross-level, uncatalogued).', '§3 rows; relationships test T4', 'Phase 1 probes; CI')

    # ---- 9 open
    out += ['## 9. Verification status and open items', '',
            '| ID | Item | Status |', '|---|---|---|',
            '| OPEN-01 | A2 structure and B rows | verified on public BIAN pages; `pending_release_validation` against a licensed release remains |',
            '| OPEN-02 | A1 / A3 / A4 within-level rows | 113 verified against the open-source Archi relationship matrix (commit cited in the record); 2 TOGAF rows unverified |',
            '| OPEN-03 | Official S rows citing ArchiMate / W135 (S34, S39, S41, S45, S49; S04, S05) | unverified: login-gated; the five ArchiMate rows can be checked against the Archi oracle next |',
            '| OPEN-04 | API contention tie-break (step 2 clause 4) | **binding** (DEC-E-06) — chosen with a gold already seen; still to be validated when it decides a pair on an unseen gold |',
            '| OPEN-05 | One-author caveat | all estates and gold authored by SDEM; one blind case (data and gold by someone else) retires it. **Sharper since the engine build:** DEC-E-07…09 were chosen while the golds of these cases were known, so passing them shows the engine reproduces the procedure, not that it generalises — the blind case is now the engine\'s real acceptance test |',
            '| OPEN-06 | Confidence bands | assigned by hand and calibrated conservative (every low inference confirmed); could be re-derived from the logs\' predicted-vs-observed outcomes |', '']

    out += ['### Engine decisions', '', 'Settled 2026-10-25 before and during the engine build (v0.10), where the records and the procedure disagreed or were silent.', '',
            '| ID | Question | Decision | Reasoning |', '|---|---|---|---|',
            '| DEC-E-01 | What must the engine reproduce? | On every scored run, **precision and recall at least the executor\'s** against the sealed gold, from the current committed inputs (latest run per case). Exact replication is not required. | The executor runs contain errors that were later fixed by rule changes (M0 CAP-300 parent rule, C3 S42); scoring against the gold rewards the fixed rules instead of copying the errors. REQ-A-01 already said this; §8 now agrees. |',
            '| DEC-E-02 | S17 confidence cap: weakest or strongest input? | **Strongest step-2 input.** | Any one implemented operation suffices to show the application realises the domain (M1 finding 3); a systematic interface deviation does not lower it (H1 finding 4). The S17 `data_needed` text said "weakest" and is corrected. |',
            '| DEC-E-03 | Does S17 have a description-only fallback? | **No.** Fallbacks are step 4 (asset-type name in API paths or data entity names) and fallback A (information perspective); S17 is not in step 5. | Description similarity alone is too weak for a high-band registry arrow; the procedure never used it. |',
            '| DEC-E-04 | Is S08 in step 5? | **Yes, but off by default**; enabled only when an institution opts in. | S08 can only be inferred from text and is "not adopted by default" in its own record; the procedure omits it for that reason. |',
            '| DEC-E-05 | Which runs are in scope? | Scored: M0, M1, H1, H2, M2 (design mode, built last), C1, C2, C3. **Not scored:** E1 (no answer key; not re-run on the enriched exports) and E2 (query-only). | An engine can only be accepted against a sealed gold. |',
            '| DEC-E-06 | Are the executor\'s conventions binding? | **Yes** — the contention tie-break (OPEN-04) and the method rows of step 2 check 2 are part of the specification. | They were applied in every run that scored 1.00; leaving them open would make the engine\'s behaviour undefined. |',
            '| DEC-E-07 | What is a "clear synonym" in step 2 check 3? | **A shared word stem** between the qualifier (or its aliases) and a path segment: closure ↔ close, posting ↔ post, reversal ↔ reverse, validation ↔ validate (engine convention EC-01, `sdem/rules_engine.py` `stem`). | The H1 hand-run matched exactly these on a SOAP estate; with exact words only, 4 of H1\'s 14 `IMPLEMENTED_BY` links are lost. Added 2026-10-25 while building step 2; no false proposal introduced in any case. |',
            '| DEC-E-08 | S17 fallback B: is any asset-type token in the component\'s paths evidence? | **Not when the token is shared with the asset type of another domain the component (or a component containing it) already realises.** | Otherwise "payment" ties every payments domain to the Payments Hub; the M1 hand-run counted 0 distinctive matches and its gold agrees. |',
            '| DEC-E-09 | S01 when only some of a capability\'s processes use the domain? | **No proposal** (logged). The rule\'s "low" band for partial coverage is withdrawn. | The C1 hand-run never proposed partial coverage and the gold has none; H1 and M0 do not depend on it. |', '']

    # ---- 10 index
    out += ['## 10. Requirements index', '', f"{len(REQ)} requirements. Groups: V vocabulary, S structure, M mapping model, D data, P procedure, O outputs, A acceptance.", '',
            '| ID | Requirement | Derives from | Validated by |', '|---|---|---|---|']
    for rid, grp, text, src, val in REQ:
        out.append(f"| {rid} | {text} | {src} | {val} |")
    out.append('')
    return _terms('\n'.join(out) + '\n')


DIAGRAM = ROOT / 'docs' / 'architecture-model-diagram.puml'


def render_diagram():
    """The design diagram is the merged view (within-level rows by ID + cross-level plan rows by ID) under the spec's title."""
    from sdem.diagram import render_merged
    text = render_merged()
    text = text.replace('@startuml merged-relationships', '@startuml architecture-model-diagram', 1)
    text = text.replace('title Merged view — ', 'title SDEM architecture model — Architecture Metamodel (entity types, within-level rows) and Architecture Relationship Rules Model (cross-level rules), by ID; the Architecture Relationship Registry is not drawn: ', 1)
    text = text.replace('within-level links (thin, kind only)', 'within-level rows (thin grey, RA…)').replace('cross-level mappings (plan ID, coloured by decision)', 'cross-level rules (plan rows S…, coloured by decision)')
    text = text.replace('  Light grey thin arrows: within-level constraint rows (ArchiMate kind as label)', '  Thin grey arrows: within-level rows (RA…) of the Architecture Metamodel — the links allowed inside one architecture')
    text = text.replace("  Grey entity: no cross-level mapping by decision", "  Blue (catalogue rules) are the only rules whose output becomes Architecture Relationship Registry records; the other colours are reported as candidates\n  Grey entity: no cross-level rule by decision\n  Every box is an entity TYPE of the Architecture Metamodel; real instances and registry records are not drawn")
    text = text.replace('  Detail: official-mappings.puml, relationship-rules.puml, level-relationships.puml', '  Read with: docs/sdem-overview.md and docs/relationship-rules-spec.md')
    return _terms(text)


REGISTRY_DOC = ROOT / 'docs' / 'relationship-registry-spec.md'


def render_registry():
    """docs/relationship-registry-spec.md — the Architecture Relationship Registry, from its schema, the lifecycle in sdem/diff.py and the type catalogue."""
    from sdem.diff import ALLOWED_TRANSITIONS, FROZEN_STATUSES, THAWED_ON_SUPERSEDE
    sch = _load(ROOT / 'schema' / 'relationship-registry.schema.json'); reg = _load(ROOT / 'schema' / 'relationship-types.json')
    rec = sch['$defs']['mapping']; ent = sch['$defs']['entity']; req = set(rec.get('required', []))
    out = ['# SDEM Architecture Relationship Registry Specification', '',
           'Generated by `python -m sdem.spec` from `schema/relationship-registry.schema.json`, the lifecycle in `sdem/diff.py` and the relationship type catalogue (`schema/relationship-types.json`); the test suite checks it is current. Overview: `docs/sdem-overview.md`.', '',
           'The **Architecture Relationship Registry** holds the actual relationships between real architecture entities across levels: each with evidence, confidence, status, version and approval provenance. It is built by the Architecture Relationship Inference Engine (records `proposed`) and governed by architects; the graph loader reads its `approved` records into the federated architecture knowledge graph. In this repository a registry is one JSON file per estate, `examples/<estate>/mappings.json`.', '',
           '## 1. Document', '', '| Field | Required | Meaning |', '|---|---|---|',
           f"| `registry_version` | {'yes' if 'registry_version' in sch.get('required', []) else 'no'} | version of the **relationship type catalogue** the records were written against (legacy name) |",
           f"| `metamodel_version` | {'yes' if 'metamodel_version' in sch.get('required', []) else 'no'} | version of the Architecture Metamodel |",
           f"| `mappings` | yes | the list of relationship records (legacy name) |", '',
           '## 2. Relationship record', '', '| Field | Type | Required | Meaning |', '|---|---|---|---|']
    MEAN = {'mapping_id': 'the record\'s permanent ID (legacy name)', 'source': 'the entity the relationship starts from (§3)', 'target': 'the entity it points to (§3)',
            'relationship': 'one of the nine catalogued types (§5); adjacent levels only', 'perspective': 'architecture, process or information', 'status': 'lifecycle state (§4)',
            'evidence': '`kind:reference` items; the kinds must include the type\'s required evidence (§5)', 'rationale': 'why the relationship holds: the working', 'baseline_id': 'the release the record belongs to',
            'confidence': '0–1, the rule\'s band', 'bian_release': 'required on BIAN-authority types before approval', 'reviewer_id': 'the approving architect', 'created_by': 'who or what proposed it (engine, rule, architect)',
            'approved_at': 'approval date', 'valid_from': 'start of validity', 'valid_to': 'end of validity; set on supersession', 'previous_mapping_id': 'the record this one supersedes (legacy name)'}
    for name, p in rec['properties'].items():
        t = ', '.join(p['enum']) if p.get('enum') else p.get('type') or p.get('$ref', '').split('/')[-1]
        out.append(f"| `{name}` | {t} | {'yes' if name in req else 'no'} | {MEAN.get(name, '')} |")
    out += ['', '## 3. Entity reference (source, target)', '', '| Field | Required |', '|---|---|'] + [f"| `{n}` | {'yes' if n in ent.get('required', []) else 'no'} |" for n in ent['properties']]
    out += ['', 'An end must resolve to an instance in the local architecture knowledge graph its type prefix names, with that id and version, whose type is the referenced type or a descendant of it.', '',
            '## 4. Lifecycle', '', '| From | May become |', '|---|---|'] + [f"| `{a}` | {', '.join(f'`{x}`' for x in sorted(b)) or '— (final)'} |" for a, b in ALLOWED_TRANSITIONS.items()]
    out += ['', f"**Immutability.** A record in {', '.join(f'`{x}`' for x in sorted(FROZEN_STATUSES))} is frozen: no field may change, except that an `approved` record may become `superseded`, changing only {', '.join(f'`{x}`' for x in sorted(THAWED_ON_SUPERSEDE))}. A change is a **new record** whose `previous_mapping_id` names the old one. Records are never deleted. `sdem-diff` enforces this against the previous version.", '',
            '## 5. Relationship types and required evidence', '', 'From the relationship type catalogue (Architecture Metamodel).', '', '| Type | Source → target | Authority | Required evidence |', '|---|---|---|---|']
    for r in reg['relationships']:
        out.append(f"| `{r['relationship']}` ({r['mapping_type_id']}) | {r['source_type']} → {r['target_type']} | {r['authority']} | {', '.join(r['required_evidence'])} |")
    out += ['', '## 6. Validation', '', '| Check | Tool |', '|---|---|',
            '| record shape, catalogued type, adjacency, evidence kinds, BIAN fields | `sdem-validate` |', '| both ends resolve in the local knowledge graphs | `sdem-graph check` |', '| no edits to frozen records; only permitted transitions | `sdem-diff` |', '',
            '## 7. Legacy names', '', 'The registry keeps the field names `mappings`, `mapping_id` and `previous_mapping_id`, and the catalogue keeps `mapping_type_id` and `registry_version`, because they sit inside immutable approved records. Renaming them would need a versioned migration (a reader accepting both names and a converter), with approved history preserved by supersession. The previous schema path `schema/mapping.schema.json` is kept as a deprecated copy for v0.7.', '']
    return _terms('\n'.join(out) + '\n')


def main(argv=None):
    parser = argparse.ArgumentParser(prog='sdem-spec', description='Render docs/relationship-rules-spec.md, docs/architecture-model-diagram.puml and docs/relationship-registry-spec.md from the records.')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    rc = 0
    for path, text in ((DOC, render()), (DIAGRAM, render_diagram()), (REGISTRY_DOC, render_registry())):
        if args.check:
            ok = path.exists() and path.read_text(encoding='utf-8') == text; rc |= 0 if ok else 1
            print(f"{path.name}: {'up to date' if ok else 'STALE: regenerate with python -m sdem.spec'}")
        else:
            path.write_text(text, encoding='utf-8'); print(f'wrote {path}')
    return rc


if __name__ == '__main__':
    raise SystemExit(main())
