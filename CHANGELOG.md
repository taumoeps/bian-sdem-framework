# Changelog

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
