# SDEM Data Architecture (DAR, metamodel 0.19.0) for payment-v3-020 — prepared by Claude, run by a person.
# Each read/write is stated in the design document (narrative/design.md §5, §6); check each before running.
set -e
S=sdem; W=.; P=steven.taumoepeau
$S migrate --workspace $W --person $P                                   # 0.18.0 → 0.19.0, version only
$S change propose coordination/drafts/dar-data-domains.json --workspace $W --agent sdem-data --person $P
$S data mode MIG-020-035 write      --workspace $W --person $P --rationale "consent creation stores the consent (design §4, POST /domestic-payment-consents)"
$S data mode MIG-020-036 read       --workspace $W --person $P --rationale "consent read returns it (design §4, GET /domestic-payment-consents/{ConsentId})"
$S data mode MIG-020-037 write      --workspace $W --person $P --rationale "payment submission creates the payment request (design §6)"
$S data mode MIG-020-038 read       --workspace $W --person $P --rationale "payment read returns its status (design §4, GET /domestic-payments/{id})"
$S data mode MIG-020-039 read_write --workspace $W --person $P --rationale "APP-CONSENT controls the consent's lifecycle and persistence (design §5)"
$S data mode MIG-020-040 read       --workspace $W --person $P --rationale "the hub checks the consent is authorised and unconsumed (design §6)"
$S data mode MIG-020-041 write      --workspace $W --person $P --rationale "the hub creates the payment request and persists its status (design §6)"
$S data mode MIG-020-042 write      --workspace $W --person $P --rationale "the hub records the idempotency key (design §6)"
$S data mode MIG-020-043 write      --workspace $W --person $P --rationale "APP-EDGE produces the correlated security events (design §5)"
$S data mode MIG-020-044 read       --workspace $W --person $P --rationale "the debtor-account read route reads the consent (design §4)"
$S check --workspace $W
$S data lineage DATA-PAYMENT --workspace $W
$S status --workspace $W
