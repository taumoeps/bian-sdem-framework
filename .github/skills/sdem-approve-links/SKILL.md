---
name: sdem-approve-links
description: How a person approves the cross-layer links the SDEM rules engine proposes — reviewing proposals, the evidence each link type requires, superseding old links, and the pull request. Use when reviewing `sdem review` output, preparing an approval, drafting a pull-request description, or when `sdem validate` rejects an approved link. An agent never approves.
---

# Approving SDEM links — done by a person

The rules engine (`sdem link`) **proposes** links; **a person approves** them in the registry (`<estate>/mappings.json`), in a reviewed pull request. An agent may prepare the review and draft the pull-request text — never set a link to `approved` itself.

## Steps

1. **Review:** `sdem review <dir>/proposals.json --names <estate>/a*.json` (weakest first) and `sdem explain <P-id> --proposals <dir>/proposals.json` for one link.
2. **For each link the architect accepts**, copy it from `proposals.json` into `mappings.json` and set:
   - `mapping_id` — a new id, unique in the registry;
   - `status: "approved"`, `reviewer_id` (the person), `approved_at` (date);
   - `evidence` — **add the document that proves it**, as `kind:document-reference`; the kinds each link type needs are in [the evidence table](./evidence-by-link-type.md). The engine's reasoning alone is not enough.
3. **Superseding an old link** (e.g. after a rehost): set the old one's `status` to `superseded` and give the new one `previous_mapping_id: "<old id>"`. Never edit an approved link in any other way.
4. **Check:** `sdem validate --strict <estate>/mappings.json` and `sdem check <estate>/a*.json <estate>/mappings.json`.
5. **Pull request** on a branch; a reviewer merges — **the merge is the approval**. Then `sdem build … --out <graph>` and `sdem trace …` show the link in use.

## Messages

| Message | Fix |
|---|---|
| `approved mapping requires reviewer_id` / `approved_at` | add who approved and when |
| `evidence missing required kind(s) [...]` | add evidence of that kind (table) |
| `duplicate mapping_id` | choose an unused id |
| `superseded mapping has no successor referencing it via previous_mapping_id` | the new link needs `previous_mapping_id` |
| `a link to a projected or design record cannot be approved` (CTL-16) | projections are plans — never approve links to `PRJ-` records |
