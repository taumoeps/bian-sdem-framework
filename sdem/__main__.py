"""`python -m sdem …` — the same as the `sdem` command, without installing (docs/design/sdem-workbench-spec.md WB-K02)."""
from sdem.cli import main

raise SystemExit(main())
