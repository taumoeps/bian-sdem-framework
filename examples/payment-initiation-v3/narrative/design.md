# Model A — Reference Bank (fictional) | S1 Domestic Payment Initiation

**Design status:** independent synthetic reference; candidate for architectural review, not a certified implementation. **Prepared:** 17 November 2026. **Public standards baseline:** NZ Banking Data API / Payment Initiation / Security Profile **v2.3.3**, BIAN **14.0.0**. No SDEM-specific schema was used to define this design.

**Evidence convention:** **S** = verified public specification statement (source and section given); **D** = a decision for this invented bank; **S?** = proposed standards attribution not independently verified. A statement labelled D is *not* imposed by the source standard. The internal bank name **Kōwhai Lantern Reference Bank** is invented for this exercise and **not cleared for legal naming or incorporation (official Companies Register exact-name lookup unavailable)**; it must not be represented as an actual registered bank.

## 1. Scope, actors and boundaries

**S** [MBIE standards page]: The 2025 regulated banking standards incorporate NZ Banking Data API v2.3.3 and related security material, effective 1 December 2025. [MBIE](https://www.mbie.govt.nz/business-and-employment/business/consumer-data-right/standards-for-the-consumer-data-right).

**D** Reference Bank is a hypothetical New Zealand retail deposit-taker. An accredited third-party provider facilitates a merchant checkout payment. The customer chooses one NZD domestic electronic credit payment, is redirected to Reference Bank for authentication/authorisation, and returns to the provider. Bank systems then validate, screen, make a debit posting, hand the instruction to an execution boundary and expose payment status. Existing synthetic systems include the bank's API ingress, identity, consent processing, payments hub, fraud service, account ledger, outbound connector and notification service.

**S** [PNZ payment API v2.3.3 §4, §5; consent resource §3; payment resource §3]: Domestic-payment consent, domestic payment submission and status queries have separate resource endpoints and authorisation requirements. **D** The scenario starts at the bank's API and ends at the accepted-for-execution boundary; interbank clearing and settlement, reconciliation with another bank, cards, bulk, high-value and cross-border payments, scheduled/enduring consents and direct debit journeys are excluded.

**S** [PNZ Security Profile v2.3.3 §§3–4, §6]: The standard documents both hybrid redirect and decoupled CIBA security profiles. **D** Only hybrid redirect is implemented in S1; the separate decoupled scenario remains an explicit open item for a larger regulatory conformance programme. S1 alone is **not** a claim that Reference Bank implements all regulated banking API obligations.

**D** Fictional participants: retail customer, merchant, accredited third-party provider and the bank in its account servicing role. Sample account identifiers, if any are introduced during testing, are synthetic and not customer data.


**S** [MBIE Banking Standards 2025 clauses 6(1), 7(5)–(6); MBIE authentication guidance]: The regulated data-holder system must support both redirect/hybrid and decoupled/CIBA authorisation. The accredited requestor selects the flow; this S1 diagram only covers redirect and is **not** a complete regulatory implementation.

**S** [MBIE Banking Standards 2025 clause 4]: The incorporation of v2.3.3 is modified: the general API 429 response rule is aligned to refusal under the Act and its old §3.6.4 is omitted; old Payments NZ onboarding preconditions in common §3.7 are omitted; Security Profile §8.2's API Centre Register is omitted. The separate statement-transactions endpoint removal is outside S1. **D** This bank validates the accredited requestor against the regulated credentials/identity process, not a purported mandatory legacy Payments NZ register.

## 2. Requirements and acceptance intentions

All S requirements below are narrowly stated with their public source; all operational service-level targets and invented bank implementation rules are D. Detailed validation scenarios must include both successful and unsuccessful outcomes.

| ID | Basis | Requirement | Source / justification |
|---|---|---|---|
| R-01 | S | The accredited third party can create a one-off domestic payment consent and receive a bank-generated identifier. | CONS v2.3.3 §3–5 https://paymentsnz.atlassian.net/wiki/spaces/PaymentsNZAPIStandards/pages/1909099280 |
| R-02 | S | The bank uses the redirect authorisation flow to authenticate the customer and accept or reject the complete consent. | Security Profile v2.3.3 §3, §6 https://paymentsnz.atlassian.net/wiki/spaces/PaymentsNZAPIStandards/pages/1909099509 |
| R-03 | S | Unauthorised domestic consent is time-limited to 24 hours; expired consent cannot be used to initiate payment. | CONS v2.3.3 §3–5 https://paymentsnz.atlassian.net/wiki/spaces/PaymentsNZAPIStandards/pages/1909099280 |
| R-04 | S | Only an authorised domestic consent may be used to submit one domestic payment. | PAY v2.3.3 §3–5 https://paymentsnz.atlassian.net/wiki/spaces/PaymentsNZAPIStandards/pages/1909099379 |
| R-05 | D | The same payment request will not create a second debit under supported idempotent replay. | Reference Bank design choice |
| R-06 | S | Payment data use NZD and valid domestic account identification; invalid data are rejected. | CONS v2.3.3 §3–5 https://paymentsnz.atlassian.net/wiki/spaces/PaymentsNZAPIStandards/pages/1909099280 |
| R-07 | D | The bank checks debtor account eligibility and available funds before posting. | Reference Bank design choice |
| R-08 | D | The bank applies a risk screening decision before debit and execution handoff. | Reference Bank design choice |
| R-09 | D | The bank commits exactly one ledger debit per successfully accepted payment. | Reference Bank design choice |
| R-10 | D | After the initial checks, the bank hands the accepted instruction to its execution boundary. | Reference Bank design choice |
| R-11 | S | The third party can retrieve the bank payment resource and its reported status. | PAY v2.3.3 §3–5 https://paymentsnz.atlassian.net/wiki/spaces/PaymentsNZAPIStandards/pages/1909099379 |
| R-12 | D | Customer decline, failed authentication or expired consent do not debit accounts. | Reference Bank design choice |
| R-13 | D | Payment API is available at least 99.95% monthly (fictional target). | Reference Bank design choice |
| R-14 | D | Read p95 response latency ≤ 500 ms at 200 requests/s (fictional target). | Reference Bank design choice |
| R-15 | D | Payments platform recovery time ≤ 30 min and recovery point ≤ 5 min (fictional target). | Reference Bank design choice |
| R-16 | D | Personal/account information is protected and access to consent and payment resources is scoped. | Reference Bank design choice |
| R-17 | D | Payment and consent decisions are correlated and auditable. | Reference Bank design choice |
| R-18 | S | The bank uses version 2.3.3 consistently for consent and payment API resources. | PAY v2.3.3 §3–5 https://paymentsnz.atlassian.net/wiki/spaces/PaymentsNZAPIStandards/pages/1909099379 |
| R-19 | S | A payment accepted for execution is not represented as completed at another bank. | PAY v2.3.3 §3–5 https://paymentsnz.atlassian.net/wiki/spaces/PaymentsNZAPIStandards/pages/1909099379 |
| R-20 | D | Deployments have explicit segment boundaries, private persistence routes and managed secrets. | Reference Bank design choice |
| R-21 | S | A regulated deployment must support hybrid redirect and decoupled/CIBA; only redirect is designed in S1, so full regulated implementation remains outside S1. | MBIE 2025 clauses 6(1),7(5)–(6) (see SOURCES.md) |
| R-22 | S | API request throttling/429 and participant identification follow the MBIE modified v2.3.3 requirements rather than the superseded PNZ onboarding/register clauses. | MBIE 2025 clause 4(1)(b)–(c), clause 9 |
| R-23 | S | An unauthorised domestic payment consent is valid for 24 hours, and status/expiry is checked before submission. | CONS v2.3.3 §3.1 POST /domestic-payment-consents |
| R-24 | S | A payment debtor-account read is only returned where DebtorAccountRelease is true. | PAY v2.3.3 §3.3 GET debtor-account |

## 3. A1 — Business design

**D** The fictional business capability **Domestic payment initiation (CAP-PAY)** is supported by **customer payment consent (CAP-CONSENT)** and **payment risk control (CAP-RISK)**. The merchant payment value stream (VS-MERCHANT) moves through consent (ST-CONSENT), payment submission (ST-SUBMIT), and status enquiry (ST-STATUS). The bank offers an invented retail account product (PROD-ACCOUNT) and business initiation service (SVC-INIT), with a separate consent authorisation service (SVC-AUTH).

**D** The customer (ACTOR-CUSTOMER), merchant (ACTOR-MERCHANT), third-party provider (ACTOR-TPP) and bank role (ROLE-BANK) collaborate through the provider API channel (IF-TPP) and redirected authorisation web channel (IF-WEB). The bank captures consent (PROC-CONSENT), authenticates/authorises (PROC-AUTH), receives the payment (PROC-SUBMIT), validates data/account (PROC-VALIDATE), screens fraud (PROC-RISK), posts one debit (PROC-DEBIT), hands off for execution (PROC-HANDOFF), and responds to status enquiries (PROC-STATUS).

**S** [PNZ Domestic Payment Consents v2.3.3 §§3.1–3.2,4.2]: A newly created consent begins at `AwaitingAuthorisation`, may become `Authorised` or `Rejected`, and becomes `Consumed` when used successfully to create a payment; an unauthorised consent is valid for 24 hours. The API provider generates `ConsentId`; it is not the third party's `InstructionIdentification` or merchant's `EndToEndIdentification`.

**S** [PNZ Domestic Payments v2.3.3 §§3.2.1,4.2]: Payment statuses include `Pending`, `Rejected`, `AcceptedSettlementInProcess`, and `AcceptedSettlementCompleted`. `AcceptedSettlementInProcess` reflects acceptance for execution after checks, **not** completed interbank clearing. **D** This initial scope stops at acceptance for execution; any later reported debtor-account completion would come from an external execution confirmation, not from the acceptance handoff alone.

**D** Customer decline, authentication failure, expiry, invalid account, insufficient funds and duplicate submission are named failure cases. The intended outcomes are no new debit for any pre-execution failure and no second debit for a replay.

## 4. A2 — BIAN alignment

**S** [BIAN 14.0.0 `PaymentOrderInitiation.yaml`, `info` and `paths./PaymentOrderInitiation/Initiate`]: The Service Domain is **Payment Order Initiation** (SD-POI), its control-record path is tagged `PaymentOrderInitiationTransaction` (CR-POI), and the `Initiate` operation (OP-POI-INIT) is exposed in the semantic reference API. This is a reference taxonomy, not proof that Reference Bank must deploy one microservice per domain.

**S** [BIAN 14.0.0 `PartyAuthentication.yaml`, `info.title`]: **Party Authentication** (SD-PARTY) is an available Service Domain. **D** We align the customer authentication concern to that domain; the bank's internal OAuth authorisation and consent service implementation is independently designed.

**S** [BIAN 14.0.0 `PaymentOrderInitiation.yaml`, `components.schemas.PaymentTransaction`; `PartyAuthentication.yaml`, `components.schemas.PartyAuthentication`]: Both are published schema objects. The former contains payment amount, identification, currency and status properties, while the latter contains authentication method, level and result properties. Their presence in BIAN does **not** establish an automatic one-to-one equivalence with the Payments NZ fields or this bank's tables. **D** Reference Bank uses these schemas as semantic mapping candidates requiring explicit architectural review.


**S** [BIAN 14.0.0 `PaymentOrderInitiation.yaml` `paths`; `PartyAuthentication.yaml` `paths`]: Payment Order Initiation publishes both `Initiate` and `Retrieve` operations against its `PaymentOrderInitiationTransaction` control record. Party Authentication publishes the `PartyAuthenticationAssessment` control record and `Evaluate` and `Retrieve` operations. **D** The bank's application functions may implement the business responsibilities without reproducing those reference network paths verbatim.

## 5. A3 — Application architecture and contracts

**D** Application responsibility split: APP-EDGE terminates the accredited provider API channel and produces correlated security events; APP-IDENT handles customer authentication; APP-CONSENT controls lifecycle and persistence; APP-PAYHUB validates and orchestrates initiation, idempotency, risk, status and retries; APP-RISK returns a risk decision; APP-LEDGER owns account eligibility and posting; APP-OUTBOUND performs accepted-instruction handoff; APP-NOTIFY is a non-critical downstream notification component. Application services, functions and state events are logically distinct from the software components, not separate deployables unless explicitly listed in A4.

**S** [PNZ Payment Initiation v2.3.3 §4; Consent resource §3 and Payments resource §3]: This scenario uses `POST /domestic-payment-consents`, `GET /domestic-payment-consents/{ConsentId}`, `POST /domestic-payments`, `GET /domestic-payments/{DomesticPaymentId}` and the separately defined debtor-account read route. Consent creation and read use a client-credentials token with `payments` scope; payment submission follows the selected customer authorisation flow. `x-idempotency-key` applies only to specified POST operations [PNZ common API §Idempotency; resource endpoint tables].

**S** [Consent v2.3.3 §5 NZDomesticConsent1 data dictionary]: `InstructionIdentification` and `EndToEndIdentification` are 36-character reference values, and `InstructedAmount` contains `Amount` and `Currency`; `ConsentId` is assigned by the provider. **S** The account identification scheme shown for this NZ domestic case is `BECSElectronicCredit`. **D** The fictional bank uses a common internal decimal amount and 3-character currency code, and stores provider/merchant identifiers separately. This is a correspondence, **not** an assertion that BIAN has a canonical field of the same name.

### Bank data model (D): typed structures

The following are the bank's invented persistence structures; types and physical keys are **D**, not prescribed by the API standard. PII classification is a bank decision based on likely sensitivity; it is not a verbatim statutory classification.

#### ConsentLedger (DATA-CONSENT) — D

| Column | Bank type | Data handling / key |
|---|---|---|
| `consent_id` | `uuid` | PK |
| `third_party_id` | `varchar(64)` | internal operational data |
| `customer_id` | `uuid` | PII |
| `status` | `varchar(32)` | internal operational data |
| `instruction_identification` | `varchar(36)` | internal operational data |
| `end_to_end_identification` | `varchar(36)` | internal operational data |
| `amount` | `numeric(18,2)` | internal operational data |
| `currency` | `char(3)` | internal operational data |
| `creditor_account` | `varchar(32)` | PII |
| `debtor_account` | `varchar(32)` | PII |
| `expires_at` | `timestamptz` | internal operational data |

#### PaymentLedger (DATA-PAYMENT) — D

| Column | Bank type | Data handling / key |
|---|---|---|
| `payment_id` | `uuid` | PK |
| `consent_id` | `uuid` | FK |
| `instruction_identification` | `varchar(36)` | internal operational data |
| `amount` | `numeric(18,2)` | internal operational data |
| `currency` | `char(3)` | internal operational data |
| `payment_status` | `varchar(40)` | internal operational data |
| `ledger_posting_id` | `uuid` | internal operational data |
| `handoff_id` | `uuid` | internal operational data |
| `created_at` | `timestamptz` | internal operational data |

#### IdempotencyRegistry (DATA-IDEMP) — D

| Column | Bank type | Data handling / key |
|---|---|---|
| `key_hash` | `char(64)` | PK |
| `third_party_id` | `varchar(64)` | internal operational data |
| `request_hash` | `char(64)` | internal operational data |
| `resource_id` | `uuid` | internal operational data |
| `expires_at` | `timestamptz` | internal operational data |

#### SecurityEventLog (DATA-AUDIT) — D

| Column | Bank type | Data handling / key |
|---|---|---|
| `event_id` | `uuid` | PK |
| `actor_ref` | `varchar(64)` | PII |
| `action` | `varchar(64)` | internal operational data |
| `correlation_id` | `uuid` | internal operational data |
| `recorded_at` | `timestamptz` | internal operational data |

### Data correspondence (S at API end, D at storage end)

| Published API member | Fictional storage | Basis |
|---|---|---|
| `ConsentId` | `ConsentLedger.consent_id`, `PaymentLedger.consent_id` | S API identifier; D bank columns |
| `NZDomesticConsent1/InstructionIdentification` | `ConsentLedger.instruction_identification` | S name/type; D persistence mapping |
| `NZDomesticConsent1/EndToEndIdentification` | `ConsentLedger.end_to_end_identification` | S name/type; D persistence mapping |
| `NZDomesticConsent1/InstructedAmount/Amount` | `ConsentLedger.amount`, `PaymentLedger.amount` | S source member; D conversion to numeric(18,2) |
| `NZDomesticConsent1/InstructedAmount/Currency` | `ConsentLedger.currency`, `PaymentLedger.currency` | S source member; D conversion to char(3) |
| Consent resource `Status` | `ConsentLedger.status` | S state; D persistence |
| Payment resource `DomesticPaymentId` / `Status` | `PaymentLedger.payment_id`, `PaymentLedger.payment_status` | S identifiers/states; D persistence |

**D** On payment submission, one database transaction checks the authorised and unconsumed consent, matches the original consent and risk payloads, records the idempotency key scoped to the third party, and creates a payment request with status Pending. Before debit, the hub validates account eligibility, obtains a fraud decision, and requests a ledger posting using a unique payment id. The ledger rejects repeated posting IDs. Upon recorded acceptance the hub persists AcceptedSettlementInProcess and emits a durable handoff event. A failed handoff is retried with the same idempotent handoff identifier. No inferred acceptance is treated as settled.

## 6. A4 — Technology and operational design (all D unless specifically cited)

**D** The deployment is wholly invented: redundant API ingress (NODE-EDGE) in ZONE-EDGE, three-node application compute (NODE-APP) in ZONE-APP, database nodes (NODE-DATA) in ZONE-DATA, identity/secrets (NODE-SEC) in ZONE-SEC, and ledger/execution integration (NODE-INT) in ZONE-INTEG. They reside in a fictional NZ production location (LOC-NZ). The named networks, nodes and service deployments are modelling constructs, not evidence of a particular cloud provider.

**D** HTTPS/TLS crosses the external boundary via PATH-EDGE; application-to-SQL traffic traverses PATH-DATA; secret retrieval uses PATH-KEY; payment handoff uses mutually authenticated TLS via PATH-HANDOFF. The bank's persistence is a fictional PostgreSQL-compatible managed database (SYS-DB) with synchronous local standby and a tested recovery procedure. Durable events (SYS-MQ), managed key custody (SYS-KMS), and audit/metrics (SYS-OBS) support operations. Every application component has a named deployment: DEP-EDGE, DEP-IDENT, DEP-CONSENT, DEP-PAYHUB, DEP-RISK, DEP-LEDGER, DEP-NOTIFY, DEP-OUT.

**D** The consent and payment tables share a restricted storage service. Write access to consent state and ledger posting is scoped to named service identities. No raw secrets appear in logs. Backups are encrypted, restoration is rehearsed quarterly, and the fictional 30-minute RTO/5-minute RPO targets are tested in a separate implementation assurance exercise; neither is proven by this architecture document.

**S?** RBNZ BS11 is relevant to applicable outsourcing arrangements, but bank size, registration conditions and provider arrangements have not been specified enough to conclude a specific BS11 obligation for this made-up bank. **D** Use BS11 as a review lens, not as a false claim of certification. **D** PCI DSS is not claimed applicable to this account-to-account scenario; no cardholder-data environment is modelled.

## 7. Unhappy-path design and architecture decisions

| Case | Outcome and invariant | Basis |
|---|---|---|
| Customer declines | Consent is Rejected; payment is not submitted | S for consent status; D no-debit invariant |
| Authentication fails | Bank blocks authorisation and leaves no usable consent | D response handling, security profile governs flow |
| Consent expires | Unauthorised consent cannot authorise or initiate after 24 hours | S consent resource §3 |
| Invalid debtor account / currency / scheme | Consent or payment rejected according to applicable API resource validation | S consent/payment resource §5 |
| Insufficient funds | No debit; payment Rejected, reason retained internally | D fictional ledger decision; S payment has Rejected state |
| Duplicate payment submit | Replay is resolved to original resource; never a second debit | D defence in depth; S request idempotency constraints where required |
| Fraud screening unavailable | No new debit; queue for bounded retry or reject under bank timeout policy | D fail-closed design |
| Database outage after an external retry | Reconcile durable idempotency/payment records before attempting any posting | D recovery design |
| Handoff timeout | Same handoff id retried; status remains uncompleted until downstream evidence | D event/idempotency design |

**D Architecture decisions:** AD-01 use separate consent and payment stores in one controlled database platform for access separation; AD-02 use a single payment orchestrator rather than per-BIAN-domain deployables; AD-03 use a ledger-owned exactly-once business posting invariant with at-least-once infrastructure delivery; AD-04 use a fail-closed risk check; AD-05 keep BIAN as semantic alignment rather than treating its API as a required network contract; AD-06 use a restricted data zone and independent key custody; AD-07 defer the decoupled flow and clearing/settlement to future scenarios.

## 8. Assumptions, evidence gaps and sign-off

**D** This is a reference *design* only, not executable software. It cannot independently prove API conformance, resiliency or financial correctness in production. The definitive architecture benchmark therefore tests whether the model captures and reasons about the written design, not whether a deployed service works. All record-to-deployment and record-to-zone choices are fictional.

**S** [BIAN 14.0.0 PaymentOrderInitiation.yaml `components.schemas.PaymentTransaction`; PartyAuthentication.yaml `components.schemas.PartyAuthentication`]: The named business-object schemas and their listed fields are verified in the published files. **S?** Some security-profile claim-level constraints are not verified; no one-to-one BIAN-to-Payments-NZ field equivalence is claimed, and unresolved details are excluded from strict standards scoring. **D** Final independent review of Model A by a standards specialist is required before treating this reference as a high-assurance golden set.


**S** [PNZ Domestic Payment Consents v2.3.3 §5.2.3, `NZDomesticConsent1`]: `InstructionIdentification` and `EndToEndIdentification` have `Max36Text` type. `CreditorAccount.SchemeName` identifies `BECSElectronicCredit`; creditor-account `Identification` and `Name`, optional debtor-account information and `DebtorAccountRelease`, and remittance/reference information are represented by the published resource. **D** The bank records the consented creditor and amount as immutable consent snapshots and stores only the minimum personal data needed for the journey.

**S** [PNZ Banking Data API v2.3.3 Headers; Payment Initiation API v2.3.3 §7.1]: `x-idempotency-key` is used on POST requests to resource endpoints designated idempotent, not on arbitrary requests. **D** Reference Bank additionally enforces its own exactly-once debit invariant through a durable payment-idempotency record.

**S** [Payments Initiation API v2.3.3 §§4–5]: Consent creation and read, payment creation and read, and debtor-account read are separate operations with the `payments` scope. Creating consent uses the client-credentials grant; creating a payment uses a customer-authorised token from a redirect or decoupled flow. **D** For S1, the bank models a redirect authorisation adapter and explicitly leaves the regulated CIBA capability for separate delivery.
