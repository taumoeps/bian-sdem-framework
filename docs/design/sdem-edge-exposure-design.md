# What an edge component exposes — the `EXPOSED_THROUGH` connection

> **Status: approved — the owner approved X1–X5 as recommended and added X6 (2026-11-14); being built as metamodel 0.12.0.** It follows network zones and hosting (metamodel 0.10.0 and 0.11.0) and LC-21. A metamodel change: a new `metamodel_version` and a migration.

## 1. The problem

An internet-facing shape in a DMZ — an API gateway, a web server, a reverse proxy — exists to expose something inside: an API, a site. Today SDEM cannot say what:

- **The data has no place for it.** A4's rules have no link from a gateway to what it fronts; the payment example's gateway is linked to the Payments Hub's production deployment by ArchiMate's general association — accepted, but meaning only "related".
- **Nothing infers it.** AID works from the business layer down; it has no rule that an internet-facing API is exposed through an edge component.
- **Only LC-21 notices** — and only when the edge component has no link at all.

What a gateway really fronts is an **application interface** (A3) — Payments API v2 — not a platform. So the precise connection crosses layers.

## 2. The connection (proposed)

| Id | Source | Relationship | Target | Evidence a person gives to approve it |
|---|---|---|---|---|
| `INTERFACE_EXPOSED_THROUGH_NODE`, `…_DEVICE`, `…_SYSTEM_SOFTWARE` | `A3.ApplicationInterface` | `EXPOSED_THROUGH` | `A4.Node`, `A4.Device` or `A4.SystemSoftware` that is `internet_facing` | `network_design` (required; `api_gateway_configuration` may be given too) |

- **Like every connection between layers**: proposed, then approved by a person with its evidence (CTL-21); recorded in `mappings.json`; followed by trace and impact. Retiring the gateway reaches the interface, its API operations, the application and on up to the business; replacing the API reaches the gateway.
- **Basis:** ArchiMate 3.2 — an application interface is *served by* the technology that makes it reachable, and a technology interface (the gateway's endpoint) is *assigned to* it; SDEM names the pattern one connection, as it does for `DEPLOYED_ON` (B1). An SDEM link type, `enterprise_rule`, like the deployment types.
- **Where the target must be:** in a DMZ (LC-18 holds already); an `EXPOSED_THROUGH` to a shape that is not internet facing is refused.

## 3. Inference (proposed AID rule)

`sdem aid` proposes `EXPOSED_THROUGH` — never approves it — when:

- an A3 interface is marked **internet facing** (a new attribute on `A3.ApplicationInterface`, X2, or one of its API operations is), and
- the workspace's DMZ holds exactly **one** internet-facing platform of the gateway kind (name or type says gateway, proxy, ingress, load balancer — a signal table like the hosting signals).

Two or more candidates: **unresolved**, both named, never guessed. The proposal cites what it read, as every AID proposal does.

## 4. The checks change

- **LC-21** stays; an internet-facing shape with an approved `EXPOSED_THROUGH` is connected.
- **New LC-22 (warning):** an internet-facing A3 interface with no `EXPOSED_THROUGH` — something says it is reached from the internet, but nothing says through what.
- The payment example's association (gateway → Payments Hub deployment) becomes `EXPOSED_THROUGH` from Payments API v2 to the gateway, with evidence; the association is removed (one source of truth).

## 5. What people see

The hero and the workbench draw `EXPOSED_THROUGH` like any approved connection between layers: a line from A3's Payments API v2 down to A4's gateway in the DMZ. Pinning the gateway lights the API and the application above it.

## 6. Decisions for the owner

| # | Question | Recommendation |
|---|---|---|
| X1 | A cross-layer connection `EXPOSED_THROUGH` (A3 interface → A4 edge platform), approved with evidence — or a within-layer A4 link (gateway → deployment)? | **cross-layer** — what is exposed is the API; it is a fact a person approves, like `DEPLOYED_ON` |
| X2 | Mark internet-facing interfaces with an `internet_facing` attribute on `A3.ApplicationInterface` (as on A4 shapes)? | **yes** — one word for one idea across layers |
| X3 | Evidence kinds: `network_design` and `api_gateway_configuration`? | **yes** |
| X4 | AID proposes it only with exactly one candidate gateway; otherwise unresolved? | **yes** — never guessed |
| X5 | The payment example: Payments API v2 marked internet facing, `EXPOSED_THROUGH` the Managed API gateway (approved, made up), the association removed? | **yes** |
| X6 | *(the owner's addition)* At A4 — the physical deployment level — AID infers a connection for **every** shape that has none (LC-21) | **approved** — the rules are §7 |

Version: metamodel **0.12.0** — a link type, an attribute, AID rules, LC-22.

## 7. A4: a connection for every shape (X6)

A4 is the physical deployment: every shape there is connected to something. For each A4 shape LC-21 names (linked to nothing besides its zone, and to no other layer), `sdem aid` proposes connections — each a link marked **inferred** (H5) with the rule, what it read and its confidence; a person confirms or rejects them by the shape's id (`sdem aid confirm|reject <shape>`). Nothing is set silently; a shape no rule reaches stays **unresolved**, named, never guessed.

| Rule | For a shape that is | It proposes | From | Confidence |
|---|---|---|---|---|
| AID-C01 | a deployment no platform runs (even one with a `DEPLOYED_AS` connection) | `assignment` from the platform its component is `DEPLOYED_ON`, where the component is `DEPLOYED_AS` this deployment | approved connections | high |
| AID-C02 | a data platform (its name or product says a database) | `association` from each platform that runs a component using a data entity `stored_in` it — else from the platforms that run deployments in its zone | A3 data entities; zones | medium; low |
| AID-C03 | a technology service | `serving` to each platform that runs deployments in its zone (or the zone it is in) | zones | low |
| AID-C04 | an artifact | `assignment` from the platform that runs a deployment whose name shares a word with it | names | low |
| AID-C05 | any other platform | `association` with the platforms that run deployments in its innermost zone | zones | low |


AID-X01 proposes `EXPOSED_THROUGH` in the run's proposals file (a person approves it with `sdem approve`); AID-C01…C05 add links marked inferred to `a4-technology.json`. LC-19 counts both kinds of inferred link still to decide.
