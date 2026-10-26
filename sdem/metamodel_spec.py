"""Generate docs/architecture-metamodel-detail-level-spec.md (and its diagram, .puml) — the governing, detail-level specification of the
Architecture Metamodel — from the records, the gap register (metamodel/metamodel-spec-gaps.json) and the frozen
high-level specification (docs/architecture-metamodel-high-level-spec.md).

The detail spec follows the high-level spec section by section. Every section states either "Aligned to high-level §n"
or the gap(s) where the implementation differs; sections the high-level spec does not have are marked as additions.
Catalogue alignment (§5) is computed by reading the high-level spec's own tables, not asserted.
Usage: python -m sdem.metamodel_spec [--check]
"""
import argparse, glob, hashlib, json, re
from collections import Counter
from pathlib import Path

from .metamodel import ROOT

DOCS = ROOT / 'docs'
HIGH = DOCS / 'architecture-metamodel-high-level-spec.md'
OUT = DOCS / 'architecture-metamodel-detail-level-spec.md'
PUML = DOCS / 'architecture-metamodel-detail-level-spec.puml'
MM = ROOT / 'metamodel'
LEVELS = (('A1', 'a1-business.json', 'A1 Business'), ('A2', 'a2-service-domain.json', 'A2 Service Domain (BIAN)'),
          ('A3', 'a3-application.json', 'A3 Application'), ('A4', 'a4-technology.json', 'A4 Technology'))


def _j(p): return json.loads(Path(p).read_text(encoding='utf-8'))


def high_level_catalogue(text):
    """Entity rows of the high-level spec's §5 tables: type -> (definition_source, alignment_kind or None)."""
    sec = text[text.index('## 5. Core entity catalogue'):text.index('## 6. Relationships')]
    rows, a2 = {}, False
    for line in sec.splitlines():
        if line.startswith('### 5.2'): a2 = True
        elif line.startswith('### '): a2 = False
        m = re.match(r'\| `(A[1-4]\.[A-Za-z]+)` \|(.*)\|\s*$', line)
        if not m: continue
        cells = [c.strip() for c in m.group(2).split('|')]
        if a2:
            rows[m.group(1)] = ('bian_reference', None); continue
        src = cells[-1]; ds = re.search(r'`([a-z_]+)`', src)
        al = re.search(r'/\s*([a-z]+)', src)
        rows[m.group(1)] = (ds.group(1).replace('sdmm_', 'sdem_') if ds else None, al.group(1) if al else None)
    return rows

ROW_MEANING = {'id': 'permanent row ID (RA<level>-nn)', 'level': 'the architecture the row belongs to', 'source_type': 'entity type the link starts from (subtypes included, is-a)',
               'kind': 'relationship kind (ArchiMate / BIAN vocabulary)', 'target_type': 'entity type the link points to (subtypes included)',
               'cardinality': '{source_per_target, target_per_source, basis, reasoning} — e.g. 1..1 / 0..*; checked by LC-10 (maximum, error) and LC-10m (minimum, warning) where the basis is BIAN or ArchiMate',
               'basis': 'the reference architecture the row comes from', 'official_id': 'the BIAN structural row (B-row) it encodes, if any', 'description': 'what the link means',
               'reference_source': 'source reference (standard, section)', 'verification': 'how it was checked', 'enforceable': '`false` only for documentation rows (A2 artefacts); otherwise enforced by `sdem-graph check` (LC-03)',
               'inference': 'how the row was first inferred, before checking {pattern, reasoning, confidence}', 'reasoning': 'why the link is allowed', 'confidence': 'high / medium / low (single rule)', 'confidence_basis': 'which clause of the rule applied'}
INHERIT_MEANING = {'id': 'permanent row ID (XA<level>-nn)', 'level': 'architecture', 'entity': 'the specialised entity type', 'extends': 'its parent type', 'description': 'the is-a statement',
                   'reference_source': 'source reference', 'verification': 'how it was checked', 'reasoning': 'why the type specialises the parent', 'confidence': 'high / medium / low'}
TYPE_MEANING = {'mapping_type_id': 'permanent ID of the type (legacy name)', 'source_type': 'entity type at the source end (is-a)', 'relationship': 'the type name used in registry records',
                'target_type': 'entity type at the target end (is-a)', 'cardinality': 'many_to_many, one_to_many, …', 'perspective': 'architecture, process or information',
                'authority': 'bian_reference, bian_alignment_guidance or enterprise_rule (high-level §1.2)', 'direction_semantics': 'what the arrow means, read source → target',
                'required_evidence': 'evidence kinds a record must carry before approval', 'rule_version': 'version of this type definition', 'owner': 'who governs the type',
                'source_reference': 'source reference', 'verification': 'how the type was checked', 'confidence': 'high / medium / low', 'confidence_basis': 'which clause of the rule applied', 'reasoning': 'why the type exists'}
RULE_MEANING = {'id': 'plan row ID (S01…S54 cross-level, B01…B15 BIAN-internal)', 'tier': 'official BIAN only, or BIAN with supporting frameworks', 'source': 'entity type the rule starts from',
                'target': 'entity type it points to', 'relation': 'the catalogue type it produces, or `candidate` for a report', 'official': 'whether BIAN itself states the link',
                'verification': 'how the rule\'s basis was checked', 'source_reference': 'source reference', 'rule_decision': 'registry_rule (produces registry records), candidate_rule, conditional_rule, institution_only, derived_path, … — which outputs it may produce',
                'fill_step': 'the inference step that applies it (0–5); `None` for rows no step applies (not a mapping, not encodable, historical)', 'data_needed': 'the architecture dataset data the step reads (plain text; the step logic is in the engine — see §18)',
                'confidence': 'the band given to its output (high 0.8, medium 0.6, low 0.4)', 'reasoning': 'why the rule is shaped as it is', 'basis_confidence': 'confidence in the rule\'s basis (the single rule)',
                'basis_confidence_reason': 'which clause applied'}


def field_table(records, meaning, required=()):
    """One row per field found in the records: how many records carry it, the values it takes (when few), and its meaning."""
    keys = list(meaning) + sorted(set().union(*[set(r) for r in records]) - set(meaning))
    out = ['| Field | Required | In records | Values | Meaning |', '|---|---|---|---|---|']
    for k in keys:
        n = sum(1 for r in records if k in r)
        if not n: continue
        vals = Counter(str(r[k]) for r in records if k in r and not isinstance(r[k], (dict, list)))
        shown = ', '.join(f'`{v}`' for v in sorted(vals)) if 0 < len(vals) <= 12 and all(len(v) <= 40 for v in vals) else ('object' if any(isinstance(r.get(k), dict) for r in records) else 'list' if any(isinstance(r.get(k), list) for r in records) else 'text')
        out.append(f"| `{k}` | {'yes' if (k in required or n == len(records)) else 'no'} | {n} of {len(records)} | {shown} | {meaning.get(k, '')} |")
    return out


def render():
    high = HIGH.read_text(encoding='utf-8'); sha = hashlib.sha256(HIGH.read_bytes()).hexdigest()
    gaps = _j(MM / 'metamodel-spec-gaps.json')['gaps']; G = {g['id']: g for g in gaps}
    ents = [(lvl, e) for lvl, f, _ in LEVELS for e in _j(MM / f)['entities']]
    E = {e['type']: e for _, e in ents}
    lr = _j(MM / 'level-relationships.json'); rows = lr['constraints']
    rt = _j(ROOT / 'schema' / 'relationship-types.json')['relationships']
    rules = _j(MM / 'relationship-rules.json')['mappings']
    at = _j(MM / 'entity-attributes.json')
    es_text = (MM / 'entity.schema.json').read_text(encoding='utf-8')
    enum = lambda k: json.loads('[' + re.search(r'"%s":\s*\{[^}]*"enum":\s*\[([^\]]*)\]' % k, es_text).group(1) + ']')
    reg_schema = json.dumps(_j(ROOT / 'schema' / 'relationship-registry.schema.json'))
    has = lambda f: ('"%s"' % f) in reg_schema
    cases = _j(ROOT / 'examples' / 'acceptance-cases.json')['cases']
    lm_rel = _j(ROOT / 'schema' / 'level-model.schema.json')['$defs']['relationship']
    reg_map = _j(ROOT / 'schema' / 'relationship-registry.schema.json')['$defs']['mapping']
    from .diff import ALLOWED_TRANSITIONS, FROZEN_STATUSES, THAWED_ON_SUPERSEDE
    from .spec import REGISTRY_FIELD_MEANING
    hl = high_level_catalogue(high)
    st = lambda gid: f"**Gap {gid}** ({G[gid]['kind']}; {G[gid]['status']})"
    al = lambda n: f'*Aligned to high-level {n}.*'
    out = ['# SDEM Architecture Metamodel — Detail-Level Specification', '',
           '> **Status: governing specification** (from 2026-10-25). Generated by `python -m sdem.metamodel_spec` from the records in `metamodel/` and `schema/`, the gap register `metamodel/metamodel-spec-gaps.json` and the high-level specification; CI fails if it is stale. Do not edit by hand.', '',
           '## How this document relates to the high-level specification', '',
           f'[`architecture-metamodel-high-level-spec.md`](architecture-metamodel-high-level-spec.md) is the owner\'s v0.4 specification, kept as the **reference** and **frozen**: its content is pinned by checksum (`sha256 {sha[:16]}…`) and a test fails if it changes. This document follows its structure section for section and adds the implemented detail. Each section says either *Aligned to high-level §n* or names the **gap** where the implementation differs. Sections 15–19 cover what the high-level specification does not. Where the two differ, **this document governs**; gaps change status only on the owner\'s decision.', '',
           '### Data model of the metamodel — where each part is defined', '',
           '| Part | Record | Field-level definition |', '|---|---|---|',
           '| Entity type | `metamodel/a1…a4-*.json` | §3 |', '| Entity instance and its attributes | architecture dataset instances; `metamodel/entity-attributes.json` | §16 (and the attribute and logical data model documents) |',
           '| Relationship **within** an architecture — the allowed link | `metamodel/level-relationships.json` | §6.1a, §6.1b (inheritance) |',
           '| Relationship within an architecture — an actual link | `relationships` of an architecture dataset | §6.1c |',
           '| Relationship type **between** architectures | `schema/relationship-types.json` | §6.2a |',
           '| **Mapping** — an actual link between architectures | Relationship Registry (`mappings.json`) | §6.4 |',
           '| Mapping rule — how a link is found | `metamodel/relationship-rules.json` | §15a |', '',
           '### Gap summary', '', '| ID | Kind | High-level § | Status |', '|---|---|---|---|']
    out += [f"| [{g['id']}](#gap-register) | {g['kind']} | {g['high_level_section']} | {g['status']} |" for g in gaps]
    # ---- 1
    ds = Counter(e['definition_source'] for _, e in ents); au = Counter(x['authority'] for x in rt)
    out += ['', '## 1. Purpose and normative boundary', '', al('§1.1 and §1.2') + ' The purpose has grown beyond v0.4: within-level relationships are stored and enforced (' + st('G-01') + '), a persistent graph store exists (' + st('G-15') + ').', '',
            '**Entity taxonomy (`definition_source`)** — values allowed by `metamodel/entity.schema.json` and their use:', '', '| Value | Entity types |', '|---|---|']
    out += [f"| `{v}` | {ds.get(v, 0)} |" for v in enum('definition_source')]
    out += ['', '`sdmm_extension` is the pre-v0.7 spelling of `sdem_extension`, still accepted. `bank_extension` is reserved for profiles (' + st('G-08') + ').', '',
            '**Rule taxonomy (`authority`)** — on the relationship types:', '', '| Value | Relationship types |', '|---|---|'] + [f'| `{k}` | {v} |' for k, v in sorted(au.items())]
    out += ['', 'Registry self-check (high-level §1.2) — a `bian_*` rule needs a `bian_*` endpoint: **enforced** (`sdem/validate.py` `validate_registry`).']
    # ---- 2
    stds = Counter(e['reference']['standard'] for _, e in ents)
    out += ['', '## 2. Reference architectures', '', al('§2') + ' R1–R7 are the sources in use. The entity catalogue cites:', '', '| Standard cited by entity records | Entity types |', '|---|---|']
    out += [f'| {k} | {v} |' for k, v in sorted(stds.items())]
    out += ['', 'Attributes add further public sources (Dublin Core, W3C ORG and SKOS, ISO 20022, CycloneDX, SPDX, NIST, OpenAPI, AsyncAPI, CloudEvents, IANA, OCI, package-url, IETF) — ' + st('G-12') + '. Per-entity provenance: [`reference-architecture-provenance.md`](reference-architecture-provenance.md).']
    # ---- 3
    hl_fields = ['type', 'level', 'abstract', 'extends', 'definition', 'definition_source', 'alignment_kind', 'reference', 'evidence_status', 'artefact']
    fields = sorted(set().union(*[set(e) for _, e in ents]))
    out += ['', '## 3. Entity record', '', al('§3') + ' The record carries every high-level field; added fields are ' + st('G-13') + '.', '', '| Field | In high-level §3 | In every record | Notes |', '|---|---|---|---|']
    notes = {'reference': 'standard, release, concept, uri; records add `locator` (section/page)', 'evidence_status': 'see below — ' + st('G-02'), 'alignment_kind': 'values: ' + ', '.join(f'`{v}`' for v in enum('alignment_kind')),
             'reasoning': 'why the entity is defined as it is', 'confidence': 'high / medium / low under the single confidence rule (`sdem/confidence.py`)', 'confidence_basis': 'which clause of the rule applied', 'identifier': 'natural key {key, basis, reasoning}'}
    for f in hl_fields + [x for x in fields if x not in hl_fields]:
        out.append(f"| `{f}` | {'yes' if f in hl_fields else '**added**'} | {'yes' if all(f in e for _, e in ents) else 'some'} | {notes.get(f, '')} |")
    ev = Counter((e['evidence_status'], e['definition_source']) for _, e in ents)
    out += ['', '**Evidence status as recorded** (high-level: `bian_reference` types ship `pending_release_validation`; confirmation only through a register entry):', '', '| evidence_status | definition_source | Entity types |', '|---|---|---|']
    out += [f'| `{a}` | `{b}` | {n} |' for (a, b), n in sorted(ev.items())]
    out += ['', 'All `bian_reference` types are `pending_release_validation` — aligned. The `confirmed_in_official_source` rows have no verification record — ' + st('G-02') + '.', '',
            'Rules (high-level §3): artefacts are never endpoints — **enforced** (`sdem/validate.py`; `sdem-graph check` rejects artefact instances); is-a matching — **enforced** (`sdem/metamodel.py` `is_a`).']
    # ---- 4
    out += ['', '## 4. Entity reference (relationship endpoint)', '', 'The registry endpoint fields as implemented in `schema/relationship-registry.schema.json`:', '', '| Field | High-level §4 | Implemented |', '|---|---|---|']
    for f, req in (('id', 'yes'), ('type', 'yes'), ('version', 'yes'), ('canonical_id', 'A2 ends of bian_* rules'), ('source_system', 'optional'), ('source_entity_id', 'optional')):
        out.append(f"| `{f}` | {req} | {'yes' if has(f) else '**no** — ' + st('G-05')} |")
    out += ['', f"Document pins: `registry_version` — yes; `metamodel_version` — {'yes' if has('metamodel_version') else 'no'}; `profile_id` — {'yes' if has('profile_id') else '**no** — ' + st('G-05')}. `lifecycle_status` is not a reference field — aligned."]
    # ---- 5
    out += ['', '## 5. Entity catalogue', '', f"{len(E)} entity types: {sum(1 for e in E.values() if not e.get('abstract') and not e.get('artefact'))} instance types, {sum(1 for e in E.values() if e.get('artefact'))} artefacts, {sum(1 for e in E.values() if e.get('abstract'))} abstract — as high-level §5 (41 + 3 artefacts). The **Alignment** column is computed against the high-level §5 tables."]
    mism = []
    for lvl, f, name in LEVELS:
        es_ = [e for l, e in ents if l == lvl]
        title = name if lvl != 'A4' else name + ' (high-level: "Infrastructure") — ' + st('G-04')
        out += ['', f'### 5.{lvl[1]} {title} ({len(es_)})', '', '| Type | Kind | Definition | definition_source | alignment_kind | evidence_status | Confidence | Alignment |', '|---|---|---|---|---|---|---|---|']
        for e in es_:
            kind = 'artefact' if e.get('artefact') else 'abstract' if e.get('abstract') else ('extends `' + e['extends'] + '`' if e.get('extends') else 'concrete')
            h = hl.get(e['type'])
            if e.get('artefact'): verdict = 'listed as artefact in §5.2'
            elif not h: verdict = '**not in high-level §5**'
            else:
                bad = []
                if h[0] and h[0] != e['definition_source'].replace('sdmm_', 'sdem_'): bad.append(f"source {h[0]} → {e['definition_source']}")
                if h[1] and h[1] in ('exact', 'specialization', 'related', 'conceptual', 'none', 'composite') and h[1] != e.get('alignment_kind'): bad.append(f"alignment {h[1]} → {e.get('alignment_kind')}")
                if bad: mism.append(e['type']); verdict = '; '.join(bad) + (' — ' + st('G-03') if e['type'] == 'A4.Deployment' else '')
                else: verdict = '✓'
            out.append(f"| `{e['type']}` | {kind} | {e['definition']} | `{e['definition_source']}` | `{e.get('alignment_kind')}` | `{e['evidence_status']}` | {e['confidence']} | {verdict} |")
    out += ['', f"Catalogue check: {len(hl)} entity rows read from high-level §5; {len(mism)} {'differs' if len(mism) == 1 else 'differ'} ({', '.join(mism) or 'none'}). Dropped from core per high-level §5.3 and absent here: `A3.Application`, `A3.Integration` — aligned. The example-cloud types moved to profiles do not exist — {st('G-08')}."]
    # ---- 6
    by = Counter(c['level'] for c in rows); ver = Counter(c['verification'] for c in rows)
    out += ['', '## 6. Relationships', '', '### 6.1 Within-level relationships', '', st('G-01') + ' — **this section supersedes high-level §6.1.** Within-level relationships are in scope: each architecture\'s allowed links come from its own reference architecture and are enforced by `sdem-graph check` (LC-03).', '',
            f"{len(rows)} rows + {len(lr['inheritance'])} inheritance rows ({', '.join(f'{k} {v}' for k, v in sorted(by.items()))}); {sum(1 for c in rows if c.get('enforceable') is not False)} enforced (A2 artefact rows are documentation only). Verification: " + ', '.join(f'{k} {v}' for k, v in sorted(ver.items())) + '. Every row carries cardinality, source reference, reasoning and confidence. Detail: [`relationships-planning.md`](relationships-planning.md).', '',
            '#### 6.1a Within-level relationship row — the allowed link', '', 'One row per (source type, kind, target type) an architecture allows. ' + st('G-01') + '.', ''] + field_table(rows, ROW_MEANING) + [
            '', '#### 6.1b Inheritance row', '', 'One row per is-a link between entity types (the `extends` of §3), so a link allowed for a parent is allowed for its subtypes.', ''] + field_table(lr['inheritance'], INHERIT_MEANING) + [
            '', '#### 6.1c Within-level relationship — an actual link', '', 'In an architecture dataset\'s `relationships` list (`schema/level-model.schema.json`); never in the Relationship Registry.', '',
            '| Field | Required | Meaning |', '|---|---|---|'] + [f"| `{k}` | {'yes' if k in lm_rel.get('required', []) else 'no'} | {dict(source='id of the source instance in the same architecture dataset', kind='relationship kind; must match a row of §6.1a through inheritance, or be `association`', target='id of the target instance in the same architecture dataset', name='optional label').get(k, '')} |" for k in lm_rel['properties']] + [
            '', 'Checked by `sdem-graph check`: both ends in the architecture dataset (LC-03), kind allowed for the types (LC-03), cardinality (LC-10, LC-10m).', '',
            '### 6.2 Cross-level relationship types', '', al('§6.2') + ' The eight v0.2.1 rules plus `DEPLOYED_AS` with the governance of high-level §14 decision 2.', '',
            '| Source | Relationship | Target | Perspective | Authority | Required evidence | Confidence |', '|---|---|---|---|---|---|---|']
    out += [f"| `{x['source_type']}` | `{x['relationship']}` | `{x['target_type']}` | {x['perspective']} | `{x['authority']}` | {', '.join(x.get('required_evidence') or []) or '—'} | {x.get('confidence', '')} |" for x in rt]
    out += ['', '#### 6.2a Relationship type record', '', 'Every field of a relationship type in `schema/relationship-types.json`. ' + al('§6.2') + ' (fields beyond `authority` and `perspective` came from v0.2.1, high-level R7; provenance fields are ' + st('G-13') + ').', ''] + field_table(rt, TYPE_MEANING)
    out += ['', f"Is-a matching lets `DEPLOYED_ON → A4.InfrastructureComponent` accept any concrete A4 type — aligned. Detail: [`relationship-registry-spec.md`](relationship-registry-spec.md).", '',
            '### 6.3 Derived relationships', '', 'Level-skipping traceability is a query over approved edges with provenance (`sdem-graph trace`) and never a registry record — aligned. The inference engine also writes derived-path rows as **candidate reports** in a separate file, never registry records — ' + st('G-07') + '.']
    out += ['', '### 6.4 Relationship record — the mapping between architectures', '', al('§4 and §6.2') + ' (the v0.2.1 record, retained; high-level R7). One record per actual link between instances of adjacent architectures, in the **Architecture Relationship Registry** (`examples/<estate>/mappings.json`). Field definitions are shared with [`relationship-registry-spec.md`](relationship-registry-spec.md).', '',
            '| Field | Type / values | Required | Meaning |', '|---|---|---|---|']
    for k, v in reg_map['properties'].items():
        t = ', '.join(f'`{x}`' for x in v['enum']) if v.get('enum') else v.get('type') or 'entity reference (§4)'
        m = REGISTRY_FIELD_MEANING.get(k, '').replace('(§5)', '(§6.2)').replace('(§4)', '(lifecycle below)').replace('(§3)', '(§4)')  # registry-spec section numbers -> this document's
        out.append(f"| `{k}` | {t} | {'yes' if k in reg_map.get('required', []) else 'no'} | {m} |")
    out += ['', '**Lifecycle** (`sdem/diff.py`):', '', '| From | May become |', '|---|---|'] + [f"| `{a_}` | {', '.join(f'`{x}`' for x in sorted(b_)) or '— (final)'} |" for a_, b_ in ALLOWED_TRANSITIONS.items()]
    out += ['', f"**Immutability.** Records in {', '.join(f'`{x}`' for x in sorted(FROZEN_STATUSES))} are frozen; an `approved` record may only become `superseded`, changing {', '.join(f'`{x}`' for x in sorted(THAWED_ON_SUPERSEDE))}. A change is a new record whose `previous_mapping_id` names the one it supersedes; records are never deleted (enforced by `sdem-diff`). Only `approved` records enter the federated graph (graph store GD-04).", '',
            '**Who writes what.** The inference engine writes records with status `proposed` only; an architect moves them through the lifecycle; `reviewer_id` and `approved_at` are set only on approval. Candidate reports (rule rows that are not catalogue types) are never registry records — ' + st('G-07') + '.']
    # ---- 7
    out += ['', '## 7. Bank Architecture Profiles', '', st('G-08') + '. Nothing of high-level §7 is built; the `ReferenceResolver` interface exists (`sdem/reference.py`), the `resolve_entity(ref)` form does not — ' + st('G-06') + '.']
    # ---- 8
    out += ['', '## 8. Validation stages and verdicts', '', al('§8') + ' except where noted. Verdicts are kept per stage and never collapsed (`sdem-validate --json`).', '',
            '| Stage | High-level question | Implemented by | Status |', '|---|---|---|---|',
            '| 1 Schema | well-formed document | `sdem/validate.py` `check_schema` | built |',
            '| 2 Metamodel | endpoint types exist (is-a); relationship registered for them | `sdem/validate.py` | built |',
            f"| 3 Profile | bank types satisfy their mapping | — | not built — {st('G-08')} |",
            '| 4 Identity | both ends resolve at the stated version | `sdem-graph check` (`FederatedGraph.resolve_entity`) | built (`unverified` without architecture datasets) |',
            f"| 5 BIAN | canonical_id valid in the stated release | `ReferenceResolver` | always `unverified` — {st('G-10')} |",
            '| 6 Governance | evidence, reviewer, timestamp, baseline, supersession, transitions | `sdem/validate.py`, `sdem-diff` | built |',
            '| 7 Semantics | evidence justifies the relationship | — | `unverified` by design (high-level §8) |',
            '', 'Architecture datasets are additionally checked against the data model — logical rules LC-01…LC-13 (`sdem/conformance.py`) — ' + st('G-12') + '.']
    # ---- 9, 10
    out += ['', '## 9. BIAN verification register', '', st('G-09') + '. `evidence_status` is recorded in the entity records (see §3).', '',
            '## 10. Compatibility and migration', '', al('§10') + ' `tests/test_v02_compatibility.py` is in the suite; unknown entity types are errors; v0.2.1 registry field names are kept (`mapping_id`, `mappings`, …) so approved records never change.']
    # ---- 11, 12, 13, 14
    out += ['', '## 11. Sequencing', '', st('G-17') + '. Current plan: [`ROADMAP.md`](ROADMAP.md).', '',
            '## 12. Repository layout', '', st('G-17') + '. As implemented:', '', '```text',
            'metamodel/   entity.schema.json, a1-business.json, a2-service-domain.json, a3-application.json, a4-technology.json,',
            '             level-relationships.json, entity-attributes.json, relationship-rules.json, export-conventions.json,',
            '             official-mappings.json, metamodel-spec-gaps.json, drafts/',
            'schema/      level-model, relationship-registry and graph-store schemas, relationship-types.json, impact-rules.json, entities/ (per-entity schemas)',
            'sdem/        metamodel, validate, diff, trace, graph, conformance, store, view, inference, rules_engine, acceptance, reference, generators',
            'examples/    synthetic estates, each with its graph store (graph/); acceptance-cases.json', '```', '',
            '## 13. References and licensing boundary', '', al('§13') + ' Nothing from BIAN or The Open Group is reproduced; definitions are SDEM paraphrases; `reference.uri` points to the source.', '',
            '## 14. Decisions', '', '| High-level decision | Status |', '|---|---|',
            f"| 1 Core entity list | 41 core + 3 artefacts, as §5 — the decision's \"31\" is {st('G-16')} |",
            '| 2 `DEPLOYED_AS` governance | aligned (§6.2 above) |',
            f"| 3 Register `verified_by` is a role | not built — {st('G-09')} |",
            f"| 4 `source_system` optional in core | not in the registry schema — {st('G-05')} |",
            '', 'Later decisions live with the parts they govern: data-model reviews (`metamodel/drafts/`), engine decisions DEC-E-01…09 ([`relationship-rules-spec.md`](relationship-rules-spec.md)), graph-store decisions GD-01…09 ([`graph-store-design.md`](graph-store-design.md)).']
    # ---- additions
    fs = Counter(str(m.get('fill_step')) for m in rules); rd = Counter(m['rule_decision'] for m in rules)
    acts = [a for a in at['attributes'] if a['status'] == 'active']
    conf = Counter(x['confidence'] for x in [e for _, e in ents] + rows + rt + acts + at.get('common_attributes', []) + at['core_fields'])
    passing = sum(1 for c in cases if c.get('engine_status') == 'passing')
    out += ['', '## 15. Architecture Relationship Rules Model', '', st('G-11') + '.', '',
            f"{len(rules)} plan rows (`metamodel/relationship-rules.json`): " + ', '.join(f'{k} {v}' for k, v in sorted(rd.items())) + '. By fill step: ' + ', '.join(f'step {k} {v}' for k, v in sorted(fs.items())) + f". Join keys: `metamodel/export-conventions.json`. Specification: [`relationship-rules-spec.md`](relationship-rules-spec.md).", '',
            '### 15a Mapping rule record', '', 'Every field of a plan row in `metamodel/relationship-rules.json`.', ''] + field_table(rules, RULE_MEANING) + ['',
            '## 16. Data model', '', st('G-12') + '.', '',
            f"{len(at['core_fields'])} core fields, {len(at.get('common_attributes', []))} common attributes, {len(acts)} entity-specific attributes, {len(at.get('derived_attributes', []))} derived attributes (`metamodel/entity-attributes.json`); 14 logical rules enforced by `sdem-graph check`; one JSON Schema per instance type (`schema/entities/`). Documents: [`architecture-attribute-design.md`](architecture-attribute-design.md), [`logical-data-model.md`](logical-data-model.md), [`physical-data-model.md`](physical-data-model.md).", '',
            '## 17. Provenance and confidence', '', st('G-13') + '.', '',
            f"Every entity, within-level row, relationship type and attribute names its source and carries reasoning and a confidence from one rule (`sdem/confidence.py`; CI fails on disagreement). Across these records: {conf['high']} high, {conf['medium']} medium, {conf['low']} low.", '',
            '## 18. Inference engine', '', st('G-14') + '.', '',
            f"`sdem/rules_engine.py` (`sdem-infer rules`) applies the rules model in fill-step order to the graph store and writes proposals (always `proposed`), candidate reports and an inference log; design mode where no A3 architecture dataset exists. Acceptance: `sdem-accept` — {passing} of {len(cases)} cases passing. Decisions DEC-E-01…09; open item OPEN-05 (a blind case).", '',
            '## 19. Graph store', '', st('G-15') + '.', '',
            'Local and federated knowledge graphs saved as JSON Graph Format v2 files with a load record and baselines; one graph access layer (`sdem/store.py`). Design and specification: [`graph-store-design.md`](graph-store-design.md), [`graph-store-spec.md`](graph-store-spec.md).', '',
            '## Gap register', '', 'From `metamodel/metamodel-spec-gaps.json`. Status changes only on the owner\'s decision.', '',
            '| ID | Kind | High-level § | High-level says | Implemented | Recommendation | Status |', '|---|---|---|---|---|---|---|']
    out += [f"| {g['id']} | {g['kind']} | {g['high_level_section']} | {g['high_level_says']} | {g['implemented']} | {g['recommendation']} | **{g['status']}** |" for g in gaps]
    return '\n'.join(out) + '\n'


COLOUR = {'bian_reference': '#BBDEFB', 'bian_aligned': '#E3F2FD', 'archimate_native': '#C8E6C9', 'archimate_aligned': '#E8F5E9',
          'togaf_informed': '#FFE0B2', 'sdem_extension': '#EEEEEE', 'sdmm_extension': '#EEEEEE', 'bank_extension': '#F8BBD0'}


def render_diagram():
    """docs/architecture-metamodel-detail-level-spec.puml: the detail spec's structure for visual review."""
    gaps = {g['id']: g for g in _j(MM / 'metamodel-spec-gaps.json')['gaps']}
    ents = [(lvl, e) for lvl, f, _ in LEVELS for e in _j(MM / f)['entities']]
    rows = _j(MM / 'level-relationships.json')['constraints']; byl = Counter(c['level'] for c in rows)
    rt = _j(ROOT / 'schema' / 'relationship-types.json')['relationships']
    rules = _j(MM / 'relationship-rules.json')['mappings']; at = _j(MM / 'entity-attributes.json')
    cases = _j(ROOT / 'examples' / 'acceptance-cases.json')['cases']
    a = lambda t: t.replace('.', '_').lower()
    short = lambda st: 'decided' if st.startswith('decided') else 'OPEN' if st.startswith('open') else st.split(' ')[0]
    gtag = lambda gid: f"{gid} ({short(gaps[gid]['status'])})"
    out = ['@startuml architecture-metamodel-detail-level-spec', '!pragma layout smetana', 'skinparam shadowing false', 'skinparam defaultFontSize 11',
           'skinparam rectangleBorderColor #546E7A', 'skinparam packageBorderColor #90A4AE', 'skinparam packageBackgroundColor #FAFAFA', 'skinparam noteBackgroundColor #FFF8E1', 'skinparam noteBorderColor #FFB300',
           'title SDEM Architecture Metamodel — detail-level specification (governing)\\nfollows the high-level spec section by section; generated from the records — python -m sdem.metamodel_spec', '']
    titles = {'A1': 'A1 Business', 'A2': 'A2 Service Domain (BIAN)', 'A3': 'A3 Application', 'A4': 'A4 Technology  [high-level: Infrastructure — ' + gtag('G-04') + ']'}
    for lvl, _, _ in LEVELS:
        out.append(f'package "{titles[lvl]}  —  detail §5.{lvl[1]}, within-level rows: {byl[lvl]} (§6.1, {gtag("G-01")})" as P{lvl} {{')
        for l, e in ents:
            if l != lvl: continue
            kind = '\\n«artefact — evidence only»' if e.get('artefact') else '\\n«abstract»' if e.get('abstract') else ''
            out.append(f"  rectangle \"{e['type']}{kind}\\n{e['definition_source']} / {e.get('alignment_kind')}\\nevidence: {e['evidence_status'].replace('_', ' ')}\" as {a(e['type'])} {COLOUR.get(e['definition_source'], '#FFFFFF')}")
        out.append('}')
    out.append('')
    for _, e in ents:
        if e.get('extends'): out.append(f"{a(e['type'])} -[#9E9E9E,dashed]-|> {a(e['extends'])}")
    out += ['', "' the nine cross-level relationship types (detail §6.2, aligned to high-level §6.2)"]
    for x in rt:
        out.append(f"{a(x['source_type'])} -[#1565C0,bold]-> {a(x['target_type'])} : **{x['relationship']}**\\n{x['authority']}")
    conf = sum(1 for _, e in ents if e['evidence_status'] == 'confirmed_in_official_source')
    dep = next(e for _, e in ents if e['type'] == 'A4.Deployment')
    out += ['', f'note "**{gtag("G-03")}**\\nhigh-level: composite\\nimplemented: {dep.get("alignment_kind")}" as N_G03', 'N_G03 .. a4_deployment', '',
            f'note "**{gtag("G-02")}**\\n{conf} ArchiMate-derived entities say\\nconfirmed in official source\\nwithout a verification record\\n(high-level §3, §9)" as N_G02', 'N_G02 .. a3_applicationcomponent', '',
            'package "Relationship Registry — record format (detail §4, §6.2)" as PREG {',
            f'  rectangle "Registry record\\nmapping_id · source · relationship · target\\nstatus · evidence · reviewer_id · approved_at\\nend fields: id · type · version · canonical_id\\n+ source_system · source_entity_id (optional — {gtag("G-05")})\\ndocument: registry_version · metamodel_version\\n+ profile_id (optional — {gtag("G-05")})" as reg #FFFFFF',
            f'  rectangle "Candidate reports\\nrelationship = plan ID; never registry records\\n({gtag("G-07")})" as cand #FFFFFF', '}', '',
            'package "Not built yet — in the high-level spec" as PNB {',
            f'  rectangle "Bank Architecture Profiles\\nhigh-level §7 — {gtag("G-08")}\\nresolve_entity(ref) — {gtag("G-06")}" as prof #FFEBEE',
            f'  rectangle "BIAN verification register\\nhigh-level §9 — {gtag("G-09")}" as vreg #FFEBEE', '}', '',
            'package "Beyond the high-level spec — detail §15–19" as PADD {',
            f"  rectangle \"Relationship Rules Model\\n{len(rules)} plan rows · fill steps · join keys\\n§15 — {gtag('G-11')}\" as rules #E1F5FE",
            f"  rectangle \"Data model\\n{len(at['core_fields'])} core · {len(at.get('common_attributes', []))} common · {sum(1 for x in at['attributes'] if x['status'] == 'active')} specific · {len(at.get('derived_attributes', []))} derived attributes\\n14 logical rules · per-entity JSON Schemas\\n§16 — {gtag('G-12')}\" as dm #E1F5FE",
            f"  rectangle \"Provenance and confidence\\nsource · reasoning · confidence on every record\\n§17 — {gtag('G-13')}\" as prov #E1F5FE",
            f"  rectangle \"Inference engine\\nsteps 1–5 + design mode\\nacceptance {sum(1 for c in cases if c.get('engine_status') == 'passing')}/{len(cases)} cases\\n§18 — {gtag('G-14')}\" as eng #E1F5FE",
            f"  rectangle \"Graph store\\nJSON Graph Format v2 · load record · baselines\\n§19 — {gtag('G-15')}\" as gstore #E1F5FE", '}', '',
            'rules -[#0277BD]-> eng : drives', 'gstore -[#0277BD]-> eng : reads', 'eng -[#0277BD]-> reg : proposes (status proposed)', 'eng -[#0277BD]-> cand : reports',
            'reg -[#0277BD]-> gstore : approved links', 'dm .[#0277BD].> gstore : shape of every record', 'vreg ..> prov : would compute evidence status', '',
            'legend right',
            '  |= Fill |= definition_source |', '  |<#BBDEFB>| bian_reference |', '  |<#E3F2FD>| bian_aligned |', '  |<#C8E6C9>| archimate_native |', '  |<#E8F5E9>| archimate_aligned |',
            '  |<#FFE0B2>| togaf_informed |', '  |<#EEEEEE>| sdem_extension |',
            '  Blue bold arrows: the 9 cross-level relationship types', '  Grey dashed arrows: extends (is-a)', '  Yellow notes: gaps against the high-level spec',
            '  Within-level rows are counted per package, not drawn — see architecture-model-diagram.puml', 'endlegend', '@enduml']
    return '\n'.join(out) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem-metamodel-spec', description='Generate the detail-level Architecture Metamodel specification.')
    ap.add_argument('--check', action='store_true'); args = ap.parse_args(argv)
    files = {OUT: render(), PUML: render_diagram()}
    if args.check:
        stale = [p for p, t in files.items() if not p.exists() or p.read_text(encoding='utf-8') != t]
        for p in files: print(f"{p.name}: {'STALE: regenerate with python -m sdem.metamodel_spec' if p in stale else 'up to date'}")
        return 1 if stale else 0
    for p, t in files.items(): p.write_text(t, encoding='utf-8'); print(f'wrote {p.relative_to(ROOT)}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
