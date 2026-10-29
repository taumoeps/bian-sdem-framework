## What changed
<!-- e.g. Onboarded the <design> design into workspaces/<domain> (LOAD-001); approved 2 links; resolved GAP-003 -->

## Checks
- [ ] Approved connections, loads and gaps changed only with SDEM commands (`sdem approve`, `sdem load`, `sdem designs resolve` …); any hand edit is to a layer's records, followed by `sdem check`
- [ ] Approved links are only added or superseded — never edited
- [ ] The evidence for each approval is named in the record
- [ ] No design export (`work/`) and no secrets in this pull request
- [ ] CI (Workspace checks) is green
