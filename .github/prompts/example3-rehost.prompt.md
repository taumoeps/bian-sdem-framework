---
name: example3-rehost
description: "Spike: the A4 agent rehosts the production payments cluster (use-case example 3)"
agent: sdem-a4-technology
argument-hint: "workspace copy, e.g. work/est, and your name"
---

In workspace ${input:workspace:work/est}, for ${input:person:your name}: the production payments workloads move from cluster INF-K8S-PAY-PROD to a new cluster INF-K8S-PAY-PROD2.

Write an A4 change set in `${input:workspace}/coordination/drafts/` (skill `sdem-change-sets`; compare with its example-a4-rehost.json) that:
- adds INF-K8S-PAY-PROD2 (A4.SystemSoftware) hosting APP-PAY-HUB and CMP-PAY-EXEC;
- updates INF-K8S-PAY-PROD with `"kind": "rehost"`, lifecycle `deprecated`, hosting nothing;
- moves DEP-PAYHUB-PROD and DEP-PAYEXEC-PROD to the new platform.

Propose it with `sdem change propose … --agent sdem-a4-technology --person ${input:person}` and report the change set, the change event and the impact. Expected (use-case example 3): APP-PAY-HUB and CMP-PAY-EXEC need a design change; links PAY-108, PAY-111 to supersede.
