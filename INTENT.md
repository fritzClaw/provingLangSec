# Intent: Provably injection-free code from AI agents

> **Status:** draft. Round 1 was decided on 2026-10-08 and grilling round 2 is open. Each decision goes into the log below once the owner answers it. Literature review v1 is in [docs/literature-review.md](docs/literature-review.md), with its BibTeX in [docs/references.bib](docs/references.bib).

## Original (German, verbatim)

> Es geht darum KI Agenten Software und einen Beweis schreiben zu lassen. Nachdem der Agent den Code erzeugt hat läuft ein deterministischer automatischer Beweiser über den generierten Code und beweist die definierten Security Eigenschaften. Mit diesem Ansatz möchte ich die Korrektheit des vom LLM erzeugten Codes bezüglich Injections zeigen gemäß der Literatur von LangSec.org insbesondere die Arbeiten von Hermerschmidt er. al.
> Für den formalen Beweis musst du das Sicherheitsverhalten als Spezifikation formulieren. Danach kannst du versuchen, das Ganze in ein Theorem umzuwandeln und mit einem Proof Assistant wie F* oder Coq zu beweisen.
> Mach eine Literaturrecherche nach verwandten Ansätzen und Werkzeugen die man verwenden kann um das Problem zu lösen.
> Im ersten Prototypen muss der Ansatz für eine Injection Schwachstelle in einer kleinen Beispiel Anwendung funktionieren. Das ganze muss in einem DevContainer verpackt sein, damit alle notwendigen Komponenten vorhanden sind wenn ich das Setup selber ausprobiere. Der Ansatz soll leicht von anderen Agenten in andere Softwareprojekte integriert werden können, sodass diese immer beweisbar sicheren Code erzeugen.

## English translation

> The idea is to have AI agents write both software and a proof. After the agent has generated the code, a deterministic automated prover runs over the generated code and proves the defined security properties. With this approach, I want to demonstrate the correctness of LLM-generated code with respect to injections, in line with the literature from LangSec.org, in particular the work of Hermerschmidt et al.
>
> For the formal proof, you need to formulate the security behavior as a specification. After that, you can try to turn the whole thing into a theorem and prove it with a proof assistant such as F* or Coq.
>
> Do a literature review of related approaches and of tools that can be used to solve the problem.
>
> In the first prototype, the approach must work for one injection vulnerability in a small example application. Everything must be packaged in a DevContainer so that all required components are present when I try out the setup myself. Other agents should be able to integrate the approach easily into other software projects, so that they always produce provably secure code.

Translator's notes:

- "er. al." is read as "et al.".
- "eine Injection Schwachstelle" can mean one concrete vulnerability or one class of injection (Q7).
- "deterministischer automatischer Beweiser" can mean an automated prover (for example an SMT solver) or a checker for a proof the agent wrote (Q5).

## Open questions (round 2)

The recommended answer is in parentheses.

13. Proof tool: Dafny, with the example app compiled to Python and run with Python's built-in `sqlite3`. This replaces the round-1 lean towards F\*, because Dafny has the strongest evidence that LLMs can write its proofs and compiles to mainstream languages. (yes)
14. Two layers:
    - an SQL layer that I write and prove once against the approved theorem, then freeze;
    - an application layer written by the agent, where R2 and R3 hold through Dafny's types and modules: untrusted input can only become literals, identifiers come from an allowlist, and the unparser is the only source of executable queries;
    - the Python glue is frozen framework code;
    - `make agent` regenerates the application layer only.

    (yes)
15. SQL subset: `SELECT … FROM … [WHERE …]` with comparisons, `AND`/`OR`/`NOT`, parentheses, allowlisted column names, string and integer literals. The unparser fully parenthesizes. `LIKE … ESCAPE` is a stretch goal for nested encoding. (yes)
16. Example app: a command-line user directory (`userdir search <name>`) on a seeded SQLite database with a secret column. The vulnerable variant concatenates strings and leaks the secrets through a `UNION` exploit. The app's intent is in `examples/userdir/INTENT.md`. (yes)
17. Differential tests against the real SQLite: string literals must decode back to the original, and `EXPLAIN` structure must not depend on the data. Known SQLite quirks are handled explicitly: identifiers come only from the schema, and input with NUL is rejected, so the theorem covers NUL-free data. (yes)
18. Agent harness: Claude Code headless in the DevContainer, using your own login or `ANTHROPIC_API_KEY` (never committed). Budget of 5 attempts or 30 minutes; the gate decides success; transcripts are saved. (yes)
19. The gate checks, in order:
    1. frozen files match the manifest hashes;
    2. there are no proof-skipping constructs;
    3. everything verifies with pinned Dafny and Z3 versions and resource limits;
    4. functional and exploit tests pass.

    It runs as a pre-commit hook, in GitHub Actions and as a Claude Code hook. (yes)
20. Theorem approval: each theorem statement comes to the owner as a pull request with a plain-English reading and a list of what it does not cover. Approval updates the manifest. (yes)
21. License: switch from GPLv3 to Apache-2.0, so that other projects can adopt the gate, skill and SQL layer. (yes)
22. Evaluation: 10 runs of `make agent` with success rate, time and cost, plus mutation tests showing the gate rejects broken encoders and weakened theorems. (yes)
23. DevContainer: built locally from a Dockerfile with identical steps on arm64 and x86_64. A prebuilt image on GitHub's registry is added only if the build takes longer than about 10 minutes. (yes)

## Decision log

| # | Question | Decision | Date |
|---|----------|----------|------|
| 1 | Purpose | Research prototype first. Turning it into a product is a later intent. | 2026-10-08 |
| 2 | Definition of done | `make demo` re-checks the committed agent-generated code and proof offline and deterministically. It rejects a vulnerable variant and runs an exploit that succeeds only against that variant. `make agent` (live LLM) is optional and not part of pass/fail. | 2026-10-08 |
| 3 | Meaning of injection-free | Output is built only by an unparser. `parse_decode(unparse_encode(t)) = t` holds for all trees, including data tokens with arbitrary strings. Untrusted input appears only as literal leaves. | 2026-10-08 |
| 4 | Scope of the proof | Only injection-freedom is proven. Functional behavior is covered by tests. | 2026-10-08 |
| 5 | Trust model | Proof-carrying code. The LLM is untrusted, and a pinned deterministic checker is the only judge. Claude drafts the theorem statements, the owner approves them, and they are then frozen (hash-pinned). Proof-skipping constructs are rejected. Everything still trusted is listed in a TCB document. | 2026-10-08 |
| 6 | Proven code is running code | The generated code is proven, and exactly that code is executed. The owner said, "I don't care in which language". No hand-written model of other code is used. | 2026-10-08 |
| 7 | First target | SQL injection against SQLite, on a small SQL subset, with one vulnerable query in the example app. | 2026-10-08 |
| 8 | Prover | F\* and Coq are only examples. The tool is chosen after the literature review, against explicit criteria (see Q13). | 2026-10-08 |
| 9 | Literature review | Comes first, as `docs/literature-review.md` plus `docs/references.bib`. Version 1 is done. | 2026-10-08 |
| 10 | Meaning of "always" | A deterministic gate (CLI, pre-commit hook, CI) enforces it and blocks anything unproven. Agent adapters are thin layers on top, Claude Code first. | 2026-10-08 |
| 11 | DevContainer host | VS Code Dev Containers on arm64 and x86_64. | 2026-10-08 |
| 12 | Way of working | This file is the single source of truth. All documentation is in English. | 2026-10-08 |
