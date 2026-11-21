# Library holds — a made-up design without BIAN (SDEM 0.20)

**Everything here is synthetic.** The library, its branches, systems and identifiers are invented; no real organisation's
architecture is described.

A municipal library lets its members reserve a catalogue item and collect it at a branch. The design is in SDEM's default
four layers, with no BIAN service domain layer:

| Layer | Records |
|---|---|
| A1 Business | the Lending and Holds management capabilities, the *Reserve and collect an item* value stream and its stages, the processes, the member and the circulation team, the *Reserve an item* service and the *Hold* business object |
| A2 Data | the `hold` data entity |
| A3 Application | the circulation system, its hold placement service, the Holds API and its `POST /holds` operation |
| A4 Technology | the application runtime, the catalogue database, a library server, production, the library network and its zones |

Seven approved connections join the layers: a process served by an application service, a business service realised by
the circulation system, the *Hold* business object mapped to the `hold` data entity, the system's deployment, where holds
are stored, and the system's access to them (`ACCESSED_BY`).

It is SDEM 0.20's proof that a design with no banking content runs every command end to end (DL-21, P3:
`tests/test_non_banking_example.py`). Start a workspace from it:

    sdem new --workspace workspaces/library --person <you> --core --from examples/0.20/library-holds
