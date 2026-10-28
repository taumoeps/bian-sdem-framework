# Design — for builders and reviewers

> **Status: current — for builders and reviewers.** You do not need these documents to use or run SDEM: start at the [documentation home](../README.md). They record how SDEM was designed, the numbered requirements it is built and tested against, and why the rules are shaped as they are. They use internal codes (requirement ids like `WB-C07`, rule ids like `S24`, controls like `CTL-21`).

| Area | Documents |
|---|---|
| **The rulebook — governing** | [high-level spec](architecture-metamodel-high-level-spec.md) (the owner's frozen reference) · [detail-level spec](architecture-metamodel-detail-level-spec.md) (governing, generated) · [rules spec](relationship-rules-spec.md) (generated) · [registry spec](relationship-registry-spec.md) (generated) · [governance](architecture-governance-spec.md) · [model diagram](architecture-model-diagram.puml) · [rulebook versioning](sdem-rulebook-versioning.md) |
| **Knowledge graph and store** | [knowledge-graph design](knowledge-graph-design.md) · [spec](knowledge-graph-spec.md) (generated) · [graph store design](graph-store-design.md) · [spec](graph-store-spec.md) |
| **Workbench and dashboards** | [workbench design](sdem-workbench-design.md) · [spec](sdem-workbench-spec.md) · [dashboard design](sdem-dashboard-design.md) · [spec](sdem-dashboard-spec.md) |
| **Design onboarding** | [transform design](sdem-transform-design.md) · [spec](sdem-transform-spec.md) · [load design](sdem-load-design.md) · [spec](sdem-load-spec.md) |
| **BIAN import** | [design](sdem-bian-import-design.md) · [spec](sdem-bian-import-spec.md) |
| **Planning missing layers (AID)** | [design](aid-design.md) · [spec](aid-spec.md) |
| **Agent platform** | [principles](sdem-agent-platform-principles.md) · [design](sdem-agent-platform-design.md) · [spec](sdem-agent-platform-spec.md) · [spike checklist](../sdem-agent-platform-spike.md) |
| **Reasoning behind the rules** (records, kept as written) | [mapping logic planning](mapping-logic-planning.md) · [mapping execution](mapping-execution.md) · [inference audit](inference-audit.md) · [`drafts/`](drafts/) (the A1–A4 data-model reviews) |
| **Plans and governance** | [ROADMAP](ROADMAP.md) · [publication checklist](PUBLICATION_CHECKLIST.md) · [`baseline/`](baseline/) (the 0.8 baseline review pack) |

Each feature has a **design** (why and how) and a **spec** (numbered, testable requirements). Rules for changing them: [CONTRIBUTING.md](../../CONTRIBUTING.md).
