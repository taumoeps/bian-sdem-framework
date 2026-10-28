# Estates

One folder per estate — usually one per domain (any domain: payments, lending, cards, customer …):

```
estates/
  <domain>/
    a1-business.json  a2-service-domain.json  a3-application.json  a4-technology.json   (one to four)
    mappings.json        the approved links between architectures — changed only by `sdem approve`
    designs/             design and gap records (design onboarding)
    loads/  migrations/  coordination/    records SDEM writes; never edit them by hand
```

Start an estate by onboarding designs (`sdem transform` → `sdem load --estate estates/<domain>`), or by copying your datasets in with an empty registry. CI checks every folder here that has a `mappings.json`.
