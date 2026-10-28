# Reference structure — one relationship per within-level constraint row

**Not a bank.** This estate is generated from `metamodel/level-relationships.json`: two synthetic instances of every concrete, non-artefact entity, and exactly one relationship per enforceable constraint row (`name` = the row ID). It exists so that every row the record allows is exercised on committed data and accepted by `sdem check`, not only by scratch probes during a test run. Regenerate with `python -m sdem.structure` after any change to the record; the test suite checks it is current and that every enforceable row occurs here.

```bash
python -m sdem.graph check examples/reference-structure/a*.json examples/reference-structure/mappings.json
```
