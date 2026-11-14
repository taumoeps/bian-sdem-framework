# A4: the physical deployment

> **Status: current — explains A4 as built in SDEM 0.18.0 (metamodel 0.14.0).** The decisions behind it are recorded in the design documents listed at the end; this page is for the people who use it.

A4 says **where the software physically runs and how it is allowed to talk**. In SDEM it is a *zoned deployment topology*: the technology shapes of ArchiMate, placed in network trust zones, connected to each other, and connected up to the applications they run — so a change at the bottom can be traced to the business at the top.

It combines three established ideas:

| Idea | Where it comes from | In A4 |
|---|---|---|
| **Network security zoning** (trust zones) | infrastructure and security practice; a cloud provider's region → VPC → public and private subnets | zones at three levels: cloud or on premises → DMZ or internal → private |
| **The ArchiMate Technology viewpoint** | ArchiMate 3.2 | the shapes (nodes, system software, devices, services, artifacts, deployments) and the lines between them |
| **Layered enterprise architecture** | TOGAF — technology serves applications, which serve the business | A4 under A3 application, A2 BIAN and A1 business, joined by approved links |

What SDEM adds: **rules** that check it, **inference** that proposes what is missing for a person to decide, and **one layout** drawn the same way everywhere.

## 1. The model

### Zones — where a shape sits

A zone is an `A4.NetworkZone` record: an ArchiMate **Grouping** with a level and a kind.

| Level | Kind | Meaning |
|---|---|---|
| 0 | `cloud` or `on_premises` | where it is hosted |
| 1 | `internal` or `dmz` | the network inside it — a DMZ only for what the internet reaches |
| 2 | `private` | an optional private segment inside a level-1 zone |

- A zone is part of the zone above it by **composition** (zone → zone, RA4-39).
- A zone holds a shape by **aggregation** (zone → shape, RA4-38). A shape a platform runs — a deployment, an artifact — is in its platform's zone; it is not placed again.
- A zone is not a network. A network is its own `A4.CommunicationNetwork` record that platforms are associated with (RA4-37); its address range belongs on the network, never on the zone.

### Shapes — what runs

The ArchiMate technology elements: `A4.Node` (a server, a host), `A4.Device`, `A4.SystemSoftware` (a cluster, a database, a gateway), `A4.TechnologyService` and `A4.TechnologyInterface`, `A4.Artifact` (an image, a package), `A4.Deployment` (an application in an environment), plus `A4.DeploymentEnvironment` (production, UAT), `A4.CommunicationNetwork` and `A4.Path`, which group or carry shapes rather than being shapes themselves.

`internet_facing: true` on a shape means the internet reaches it: it belongs in a DMZ.

### Connections inside A4 — how shapes work together

Every shape is linked to **another shape**, by an ArchiMate relationship the metamodel allows: a platform runs a deployment (*assignment*), a deployment holds its image (*aggregation*, RA4-35), a service serves a platform (*serving*), a platform uses a database or fronts a deployment (*association*). A link only to a zone, an environment or a network does not count — those group or carry shapes; they are not what a shape works with.

### Connections up to A3 — what the shapes are for

Links between layers are proposed by SDEM and **approved by a person with evidence**:

| Link | From → to | Evidence | Means |
|---|---|---|---|
| `DEPLOYED_ON` | application component → node, device or system software | `deployment_design` | where the application runs |
| `DEPLOYED_AS` | application component → deployment | `deployment_design` | the application in one environment |
| `EXPOSED_THROUGH` | application interface → node, device or system software | `network_design` | the internet reaches this API through this edge platform |
| `BUILT_AS` | application component → artifact | `build_pipeline` | this image or package is the build of this application |

### Zone connections — worked out, never drawn

Zones that may talk are worked out from the structure, never recorded:

| Rule | Connects |
|---|---|
| ZC-01 | the level-0 zones with each other (on premises ↔ cloud) |
| ZC-02 | the level-1 zones of one level 0 with each other (DMZ ↔ internal) |
| ZC-03 | a zone with the zone it is part of |
| ZC-04 | two shapes, through their zones (`sdem zones path A B`) |
| ZC-05 | what is lost when a zone connection fails (`sdem zones cut A B`) |

## 2. The rules `sdem check` applies

| Rule | Checks | Severity |
|---|---|---|
| LC-15 | a platform that hosts something is on a network, or in a zone | warning |
| LC-16 | every shape is in exactly one zone, directly or through what runs it | warning; an **error** in a workspace started with its zones (`sdem new --hosting`) |
| LC-17 | the zone structure holds: level 0 → 1 → 2 | error |
| LC-18 | an internet-facing shape is in a DMZ | warning |
| LC-19 | a zone placement or A4 link `sdem aid` inferred is waiting for a person | warning |
| LC-20 | a shape is not placed against strong hosting evidence (a mainframe in a cloud zone) | warning |
| LC-21 | every shape is linked to another shape inside A4 — not only to its zone, environment or network, and not only to another layer; retired and deprecated shapes are left out | warning |
| LC-22 | an internet-facing application interface is exposed through an edge platform | warning |

Every example in SDEM passes LC-15, LC-16, LC-21 and LC-22, and a test fails the build if one stops passing.

## 3. What SDEM proposes — and who decides

`sdem aid` fills gaps from what the records already say. Every proposal is marked **inferred**, with the rule, what it read and how sure it is; nothing is set silently, and a case it cannot decide is named, never guessed.

| Rules | Proposes | From |
|---|---|---|
| AID-Z01…Z04 | each shape's zone | hosting evidence — a site, a cloud provider or region, a managed-service name, "on premises", "data centre", a physical server (HS-01…HS-13) — else the organisation's default (cloud first). An organisation can add its own signals, or switch one of SDEM's off with a reason (PR-32, PR-33) |
| AID-C01…C06 | the A4 links a shape lacks | a deployment's platform; a database from the platforms whose applications use its data; a service to the platforms in its zone; an artifact to its deployment's platform; platforms in one zone; an edge platform to the deployment it fronts |
| AID-X01 | `EXPOSED_THROUGH` | an internet-facing interface and exactly one internet-facing edge platform |
| AID-X02 | `BUILT_AS` | an artifact naming its application, an application naming its artifact, or the artifact in the application's deployment |

A zone placement or A4 link is decided by the shape's id: `sdem aid confirm <shape>` or `sdem aid reject <shape>` (`--workspace`, `--person`). A link between layers is approved with `sdem approve` and its evidence.

## 4. Commands

| Command | Shows |
|---|---|
| `sdem zones --workspace <dir>` | each zone, what it holds, how the zones connect |
| `sdem zones path <a> <b> --workspace <dir>` | how one shape reaches another through the zones |
| `sdem zones cut <zone> <zone> --workspace <dir>` | what a failed zone connection cuts off, up to the business |
| `sdem zones --layout --workspace <dir> [--json]` | the deployment-zones layout every drawing uses (rules ZL-01…ZL-06) |
| `sdem view --graph <dir>/graph` | the four layers, A4 drawn by zone |
| `sdem diagram --workspace <dir> --template zones` | A4 in ArchiMate notation, zones as Groupings |
| `sdem impact <id> --change retire --graph <dir>/graph` | what a change to a shape or a zone affects |

The DESNRE site's 3D view draws the same layout, one environment at a time; a network is shown through its zone (its address range in the zone's heading), not as a shape.

## 5. A worked example: payment-initiation

| Zone | Level | Holds |
|---|---|---|
| Cloud — payments (`ZONE-PAY-CLOUD`) | 0 | the zones below |
| Security zone (DMZ) — payments (`ZONE-PAY-DMZ`) | 1 | the managed API gateway (`INF-APIGW-PAY`, internet facing) |
| Internal network — payments (`ZONE-PAY-INTERNAL`) | 1 | messaging (`TS-MQ`) and secrets (`TS-SECRETS`) |
| Payments private network zone (`ZONE-PAY-PRIVATE`) | 2 | the production and UAT clusters and PostgreSQL — all on the network `NET-PAY-PRIVATE` (10.20.0.0/16) |
| On premises — core banking (`ZONE-PAY-ONPREM`) → its internal network | 0 → 1 | the core banking ledger host (`INF-CORE-LEDGER-HOST`) |

Inside A4: the production cluster runs the Payments Hub and Execution Gateway deployments and the image `payments-hub:7.1`; the hub's deployment holds that image; the cluster uses PostgreSQL; messaging and secrets serve the clusters; the gateway fronts the hub's deployment; the Execution Gateway reaches the ledger host on premises.

Up to A3: Payments API v2 is `EXPOSED_THROUGH` the gateway; the Payments Hub is `DEPLOYED_ON` the clusters, `DEPLOYED_AS` its deployments and `BUILT_AS` `payments-hub:7.1`.

What a failure reaches: `sdem zones cut ZONE-PAY-DMZ ZONE-PAY-INTERNAL --workspace examples/payment-initiation` cuts the gateway off from the hub and reaches Payments API v2, the Payments Hub, the Payment Initiation service domain and the Initiate Payment capability.

## 6. How it lines up with the standards

- **ArchiMate 3.2.** The shapes and relationships are standard, and each link SDEM relies on was checked against ArchiMate's relationship tables (as implemented by Archi): a Grouping may aggregate every technology element and compose another Grouping (zones); a Node, Device or System Software may serve an Application Interface (`EXPOSED_THROUGH`); an Artifact realises an Application Component (`BUILT_AS`). Zone levels, the checks, the inference and the layout are SDEM's own method — ArchiMate is a language and leaves method open.
- **TOGAF.** A4 is the Technology Architecture (phase D): deployment topology and security zones. The checks and patterns are architecture compliance in practice; `sdem zones cut` and `sdem impact` serve change management (phase H). A site is an attribute (`site`), not yet a Location record.
- **BIAN.** Service domains are independent of technology; A4 does not touch A2. What changes is reach: impact runs from a zone or an image up through the application to its service domain.

## The decisions behind it

[Network zones](design/sdem-network-zones-design.md) · [hosting inference](design/sdem-hosting-inference-design.md) · [hosting evidence and S37](design/sdem-hosting-evidence-s37-design.md) · [edge exposure, A4 connections and BUILT_AS](design/sdem-edge-exposure-design.md) · the records skill (`sdem-records`) for how the records are written.
