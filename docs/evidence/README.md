# Evidence — for builders and reviewers

> **Status: current — for builders and reviewers.** You do not need these to use SDEM. Each use-case example is a test with expected results sealed before it ran; its recorded inputs and outputs are in the folder of the same name. They are replayed or regenerated on every push.

| Read | Tests | Result |
|---|---|---|
| [Use-case example 1](use-case-example-1.md) | four layers of data to approved connections and the knowledge graph, clean and with planted defects | 30 of 30 |
| [Use-case example 2](use-case-example-2.md) | planning missing layers (AID) | 12 of 12; safety 16 of 16 |
| [Use-case example 3](use-case-example-3.md) | the agents carry a technology change through to an approved connection | 8 of 8; controls 19 of 19 |
| [Use-case example 4](use-case-example-4.md) | onboarding existing designs, export to build — also a hands-on walkthrough | replayed on every push |
| [Use-case testing](use-case-testing.md) | the ten use cases and eleven hand-executed runs that validated the rules (a record) | every proposable rule reached its sealed answers |
| [Relationships testing](relationships-testing.md) | the 132 links allowed inside a layer (a record) | 0 contradicted |

Also in the test suite: `tests/test_lending_onboarding.py` — design onboarding on a second domain (lending), 18 of 18 records.
