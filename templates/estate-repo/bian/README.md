# Your BIAN layer

`a2-service-domain.json` here is **your BIAN layer** — the BIAN service domains your organisation uses, shared by every estate (`sdem load … --a2 bian/a2-service-domain.json`). Every connection between business and applications passes through it.

**Make it** (once — whoever owns BIAN for you):

```bash
sdem bian import --base --all -o bian/a2-service-domain.json            # every service domain SDEM can import — the simplest start
# or only the ones you use:  sdem bian list --base | grep -i <word>,  then  --only "<service domain>" …
```

Read `a2-service-domain.report.md`: confirm the asset types and functional patterns SDEM worked out; the domains `--all` left out are listed there and in `bian/a2-service-domain.needs-patterns.csv` — fill it in (or keep your own `bian/patterns.csv`) (`service domain,asset type,functional pattern`, from the BIAN portal) and add `--patterns bian/patterns.csv`. Commit this folder.

**Add service domains later:** run the import again with all of them and `--previous bian/a2-service-domain.json` — the report shows what changed. Then bring every estate up to date:

```bash
sdem bian update --root estates --a2 bian/a2-service-domain.json --person <you>     # checked; refuses if an approved connection would lose its BIAN end
```

**Your organisation's own BIAN instead of the base** (a newer release, your own selection or extensions, in BIAN's format): pack it once and use it in place of `--base`:

```bash
sdem bian pack <folder of your BIAN files> -o bian/our-bian.json
sdem bian import --base bian/our-bian.json --only "<service domain>" … -o bian/a2-service-domain.json --previous bian/a2-service-domain.json
```

BIAN® is a trademark of BIAN e.V.; the base BIAN is BIAN's Semantic APIs under Apache-2.0 (see SDEM's `bian/README.md`).
