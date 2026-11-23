## What and why

<!-- What this changes, and the rule ids it cites (CTL-…, AF-…, AID-…, MID-… in docs/design/). -->

## Checklist

- [ ] `make test` (or `python -m unittest discover -s tests`) passes
- [ ] `make check` (`python -m sdem model check`) — every generated file current; none edited by hand
- [ ] Made-up data only — no real organisation's architecture, names or identifiers
- [ ] No new dependencies (`pyproject.toml`: `dependencies = []`)
- [ ] `CHANGELOG.md` says what changed, in plain words
- [ ] A metamodel change (`metamodel/`) has the owner's approval
