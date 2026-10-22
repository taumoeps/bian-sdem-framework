# Changelog

## 0.5.2 — after M0 (first inference run)

- Export conventions: `A2.ServiceDomain.attributes.asset_type` / `functional_pattern`; fraud A2 export gains asset type and functional pattern instances, A1 export gains value-stream stages.
- Fraud example mappings: FRD-004 approved on REST-rule evidence; FRD-008 `USES_DOMAIN` approved; FRD-009 new `proposed` demo record. M0 given/gold regenerated.
- Plan: S36 subsumed by S33 (entity hierarchy); optional step-3 derivations recorded for S02 and S01; derivation confidence capped at the weakest input.
- Executor guide: per-use-case file names (`<uc>-proposals.json`, `<uc>-inference-log.json`); `use_case` allowed in the mapping-document schema; E1's overwritten proposal file restored.

## 0.5.1 — after the first executed use case (E1)

- `metamodel/export-conventions.json`: the attribute keys on level-export instances that mapping steps 1–4 join on; cross-level facts live in attributes, relationships stay within-level. Fraud example exports enriched accordingly (deployment, scenario, action term, API path/method/payload, `invokes`).
- `metamodel/level-relationships.json`: four BIAN-internal A2 constraints added (control record → qualifier, control record → business object, operation → control record, domain → domain).
- `sdmm-validate --strict`: draft warnings on `proposed` records are reported, not promoted.
- `sdmm-graph trace`: exit 1 on an empty trace (consistent with `sdmm-trace`); an approved and a proposed record of the same arrow render as one hop with both ids.
- `metamodel/new-mappings.json`: `data_needed` names export keys; S17 step-4 fallback defined; S01 step-5 candidate-set rule; S04 note on processes without activities.
- `docs/mapping-execution.md`: all 17 BIAN action terms (Notify untestable in REST mapping), export keys per step, `<model>-executor` label.

## 0.5.0 — engine readiness

Everything an automated mapping engine needs, except the engine.

- Level-model exports gain `description` and `definition_uri` per instance — the text an engine reads. Shipped example levels carry descriptions.
- `ReferenceBinding.definition`: BIAN definition text, populated only by an institution's licensed resolver at run time; never stored here.
- `sdmm/engine.py`: the `MappingEngine` protocol, the `proposal()` record shape, and a deliberately naive `baseline` engine (name/description overlap) to exercise the harness. `sdmm-engine baseline <levels>` emits a document of `proposed` records.
- `sdmm/evaluate.py` and `sdmm-eval`: precision / recall / F1 of proposals against approved records, per relationship type, with misses and false proposals listed; `--min-f1` as a CI gate.
- Validator: a `proposed` record missing required evidence kinds warns instead of failing (evidence is gathered during review); `engine` allowed at document level.
- Impact rules moved from code to governed data: `schema/impact-rules.json` with owner, version and per-kind rationale; `sdmm-graph` loads it.
- Docs: `docs/07-engine-readiness.md`.

## 0.4.0 — data architecture

- `metamodel/`: the A1–A4 entity catalogue — 41 core entities and 3 artefacts, each with `extends`, `abstract`, public-standard provenance and `evidence_status` (all `bian_reference` entities pending verification); within-level relationship kinds (ArchiMate) and BIAN's A2 structure as constraints; `metamodel/entity.schema.json`.
- `sdmm/metamodel.py`: catalogue loader, hierarchy (`is_a`), self-check.
- Validator: unknown entity is an error; artefacts cannot be endpoints; registry matching is is-a (a rule naming `A4.InfrastructureComponent` accepts any concrete A4 entity); registry self-check requires endpoints in the catalogue and a `bian_*` endpoint for `bian_*` rules; per-mapping verdicts `structural / governance / referential / bian / semantic` in `--json`; `metamodel_version` pin. New rule `DEPLOYED_AS → A4.Deployment`. Registry 0.4.0.
- `schema/level-model.schema.json`: the export format for an institution's design model — instances (concrete entities only) and within-level relationships.
- `sdmm/graph.py` and `sdmm-graph`: `LevelGraph` (validate an export) and `FederatedGraph` (four exports + mappings, joined on instance id; also the validator's `EntityResolver`). `check`, `trace` (names and concrete entities), `impact` (structural classification by change kind: modify / replace / retire / rehost, with the mappings to supersede), `stats`.
- Examples: synthetic A1–A4 exports for Card Fraud Alerts; `DEPLOYED_AS` record in customer-onboarding.
- Tests: `test_v02_compatibility.py` release gate (legacy-form examples validate with no issues and no warnings), metamodel, validator and graph suites.
- Docs: `docs/06-data-architecture.md`; README Graph component; entity count corrected to 41 (+3).

## 0.3.1

Level naming: the four design models are now the **Service Domain Architecture Design Model (SDADM)** — A1 Business Architecture, A2 Service Domain Architecture, A3 Application Architecture, A4 Technology Architecture. The `L0.`–`L3.` prefixes were an institution's own numbering, not a generic one.

- Entity types are prefixed `A1.`–`A4.`; the registry declares an ordered `levels` list, `bian_level`, and `type_aliases` mapping `L0.`–`L3.` to `A1.`–`A4.`.
- Older documents validate unchanged through the aliases; `sdmm-diff` treats an aliased prefix rename as no change, so approved records can be migrated without violating immutability.
- Registry version 0.3.0 (documents pinning `registry_version` bump the pin; that field is outside the frozen record).
- Adjacency and the BIAN-level `canonical_id` rule are driven by the registry's level list rather than a hard-coded digit.
- Docs renamed: `docs/01-a1-a2-mapping.md`, `02-a2-a3-mapping.md`, `03-a3-a4-mapping.md`.

## 0.3.0

- New `sdmm-trace` command: walk approved mappings downstream (what an entity depends on) or upstream (what depends on it), as a tree or JSON with every hop carrying its `mapping_id`. Superseded and proposed records are excluded unless `--status` includes them. Pure Python, no dependencies.
- Docs: v0.4 entity metamodel specification and roadmap track.

## 0.2.1

Validator hardening, in response to external review.

- `approved`, `rejected` and `superseded` records now require `approved_at` as well as `reviewer_id`.
- Mappings whose type has `bian_*` authority must carry `canonical_id` on their L1 endpoint. An unanchored BIAN-guided mapping no longer passes.
- Evidence may be cited as `kind:reference`; when it is, every kind in the registry's `required_evidence` must be present. Untyped evidence warns (`--strict` makes it an error).
- `EntityResolver` protocol and `CatalogueEntityResolver` (file-backed) let CI confirm every endpoint exists in a level model (`--catalogue`).
- New `sdmm-diff` command: lifecycle transitions and immutability of reviewed records, against a file or a git revision. Wired into CI against `HEAD~1`.
- Examples use typed evidence; `card-fraud-alerts` ships an `entities.json` catalogue.
- Docs: permitted transitions, immutability, evidence typing, authoritative vs derived relationships; roadmap reordered (graph before AI).

## 0.2.0

Registry metadata, JSON-Schema enforcement, supersession rules, reference-adapter interface, two worked examples, packaging and CI matrix.

## 0.1.0

Starter: relationship registry, mapping schema, minimal validator, one example.
