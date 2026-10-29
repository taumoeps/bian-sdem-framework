# Workspaces

One folder per workspace — usually one per domain (any domain: payments, lending, cards, customer …):

```
workspaces/
  <domain>/
    a1-business.json  a2-service-domain.json  a3-application.json  a4-technology.json   (one to four)
    mappings.json        the approved links between architectures — changed only by `sdem approve` / `sdem connect`
    designs/             design and gap records (design onboarding) — changed by `sdem load`, `sdem designs`
    loads/  migrations/  bian-updates/  coordination/    records SDEM writes; never edit them by hand
```

Start a workspace by onboarding designs (`sdem transform` → `sdem load --workspace workspaces/<domain>`), or by copying your datasets in with an empty registry. CI checks every folder here that has a `mappings.json`.

The same list, with what writes each file and what may be edited by hand: SDEM's [architecture — inside a workspace](https://github.com/taumoeps/bian-sdem-framework/blob/main/docs/sdem-architecture.md#inside-a-workspace).
