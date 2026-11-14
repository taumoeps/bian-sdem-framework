# On-premises evidence the hosting signals miss, and S37 without a deprecated attribute

> **Status: proposed — for the owner's decision (G1–G6, §4), 2026-11-14.** Nothing is built. Both were found while placing five examples in network zones with SDEM's own inference (`sdem/hosting.py`, AID-Z01) and checking every proposal against what the records say. A metamodel change: it needs the owner's approval, a new `metamodel_version` (0.13.0) and a migration.

## 1. The hosting signals miss plain on-premises evidence

`metamodel/hosting-signals.json` (HS-01…HS-10) decides whether a shape is on premises or in the cloud; with no signal, the organisation's default wins (cloud first, HS-10). Run on the examples, the inference put these in the **cloud**:

| Example | Record | What the record says | Proposed | Right |
|---|---|---|---|---|
| card-fraud-alerts | `INF-ONPREM-VM-CLUSTER-B` | name "On-prem VM cluster B"; "Legacy on-premises VM cluster" | cloud (default, low) | on premises |
| fx-dealing | the platforms in `ENV-FX-PROD` | environment "primary data centre", `cloud_deployment_model: private` | cloud (default, low) | on premises |
| fx-dealing | `NODE-RATEGW-01` | "Physical low-latency server in the exchange co-location rack"; `virtualisation: physical` | cloud (default, low) | on premises |

The signals know mainframes, vSphere and devices (HS-02…HS-04), but not the words people actually write, nor two attributes SDEM already has. Each proposal was low confidence and a person would correct it — but a person should not have to correct what the record already says.

### Proposed signals

| Id | Points to | Confidence | Reads | Why |
|---|---|---|---|---|
| HS-11 | on premises | high | name or description says *on-prem*, *on premises*, *on-premises*, *data centre* / *data center*, *co-location* / *colo* | the record states it |
| HS-12 | on premises | medium | its deployment environment's `cloud_deployment_model` is `private` (AT-A4-17), or the environment's description says *data centre* | NIST SP 800-145: a private cloud is operated for one organisation, usually on its premises — medium, because it may be hosted off premises |
| HS-13 | on premises | medium | `virtualisation` is `physical` | a physical server the organisation runs — medium, because bare-metal cloud exists |

Words are matched as whole words, case-insensitive, as HS-02 and HS-04 are. When signals at medium or above point both ways, the shape stays **unresolved** — never guessed (AID-Z01, unchanged). An organisation's profile can still add its own (PR-32).

**Check after building:** rerun the inference on the five examples' records with their zones removed; every proposal should match the zones now recorded (a test).

## 2. S37 reads an attribute the metamodel deprecated

S37 (`A3.ApplicationComponent` → `A4.CommunicationNetwork`, a candidate) is implemented in `sdem/rules_engine.py` from one source only: the component's `network_zone` attribute (AT-A3-07), which metamodel 0.9.0 **deprecated** — `sdem check` warns about it (LC-13). So an example that follows the warning loses the link: removing `network_zone` from trade-finance dropped two of case C3's gold candidates (`APP-LC`, `APP-DOC` → `NET-TF`).

S37's own entry already names the right source — *"or the network the component's platform is connected to (RA4-37)"* — but the engine never read it.

### Proposed

- **S37 reads the platform route first:** a component `DEPLOYED_ON` a platform (approved) → the networks that platform is associated with (RA4-37) → a candidate for each. In trade-finance this finds the same two candidates (`APP-LC` and `APP-DOC` run on `NODE-TF-PROD`, which is on `NET-TF`), so C3's answer key stays valid unchanged.
- **`network_zone` stays as a fallback until it is removed**, cited as deprecated in the candidate's reasoning; when both give a network and they differ, the platform route wins and the difference is reported.
- **Removal:** AT-A3-07 removed in metamodel 0.14.0, with a migration step that drops it where the platform route gives the same network and reports any workspace where it does not (a person decides).
- trade-finance drops `network_zone` (LC-13 clears).

## 3. What changes

| Where | Change |
|---|---|
| `metamodel/hosting-signals.json` | HS-11, HS-12, HS-13 |
| `sdem/hosting.py` | read an environment's description (HS-12) as well as its attributes |
| `sdem/rules_engine.py` | S37: the platform route, then the deprecated attribute |
| `metamodel/relationship-rules.json` | S37's `data_needed`: the platform route first |
| `metamodel/entity-attributes.json` | AT-A3-07: `removed_in_metamodel` 0.14.0 |
| `metamodel/migrations.json` | 0.12.0 → 0.13.0, additive |
| examples | trade-finance without `network_zone` |
| tests | the five examples' zones re-inferred; C3 still passes without the attribute |

## 4. Decisions for the owner

| # | Question | Recommendation |
|---|---|---|
| G1 | Add HS-11 (the record says on premises, data centre or co-location), high? | **yes** |
| G2 | Add HS-12 (environment is a private cloud, or in a data centre), medium? | **yes** |
| G3 | Add HS-13 (`virtualisation: physical`), medium? | **yes** |
| G4 | S37 reads the network of the component's platform first (RA4-37), as its entry already says? | **yes** |
| G5 | Keep `network_zone` as S37's fallback until removed in metamodel 0.14.0, with a migration that drops it where the platform route agrees? | **yes** |
| G6 | trade-finance drops `network_zone` once S37 reads the platform route? | **yes** |
