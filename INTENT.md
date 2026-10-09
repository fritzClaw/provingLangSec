# Intent: Provably injection-free code from AI agents

> **Status:** grilling rounds 1–3 were decided on 2026-10-08 and 2026-10-09. The consolidated intent below now waits for the owner's confirmation before implementation starts. The literature review is in [docs/literature-review.md](docs/literature-review.md), with its BibTeX in [docs/references.bib](docs/references.bib).

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

## Consolidated intent

This section summarizes the shared understanding reached in grilling rounds 1–3. The decision log below has the details of each decision.

### Why

LLM-generated code is often insecure. About 40% of Copilot's programs in security-relevant scenarios were vulnerable, and exploits worked against about half of the functionally correct backends in BaxBench (see section 6.1 of the [literature review](docs/literature-review.md)). Injections arise when a program emits text in a formal language and the receiving parser reads data as structure (Hermerschmidt et al. 2015). This project lets AI agents write code together with a machine-checked proof that its output cannot be injected into. Injection-freedom is then proven, not assumed.

### What

- **A research prototype** (Q1). It is packaged as a self-contained VS Code DevContainer for arm64 and x86_64 (Q11, Q23). Inside it, Claude Code writes the specification and the implementation together with its proofs (Q18, Q25).
- **The property** (Q3, Q4):
  - R1: `parse_decode(unparse_encode(t)) = t` holds for all syntax trees, including data with arbitrary strings;
  - R2: only the unparser produces text that reaches the interpreter;
  - R3: untrusted input appears only as literal leaves.

  Only injection-freedom is proven. Functional behavior is covered by tests.
- **The trust model** (Q5, Q20, Q26) is proof-carrying code:
  - the agent is untrusted;
  - a pinned, deterministic Dafny/Z3 check is the only judge;
  - theorem statements and specifications are frozen once the owner approves them;
  - constructs that skip a proof are rejected;
  - everything that remains trusted is documented.
- **The tool** (Q6, Q13) is Dafny, compiled to Python. The verified code is exactly the code that runs.
- **The first target** (Q7, Q15, Q16) is SQL injection against SQLite, using a small `SELECT` subset. The example app `userdir` has a vulnerable variant that leaks secrets through a `UNION` exploit.
- **Generality** (Q14, Q24): the approach covers any language emitted to an interpreter, including custom ones.
  - Now: a language-definition format, a fixed theorem template and a lemma library.
  - Later: a generic engine proven once.
- **Parser fidelity** (Q17, Q27):
  - the SQL grammar subset comes from SQLite's `parse.y`;
  - the parser model is tested against an instrumented SQLite debug build, plus exhaustive tests of literal lexing up to a bounded length;
  - the double-quote misfeature is switched off and NUL is rejected.
- **"Always"** (Q10, Q19) is enforced by a deterministic gate. It checks:
  - frozen-file hashes;
  - that no proof-skipping constructs are used;
  - verification with pinned versions, seed and resource limits;
  - functional and exploit tests.

  It runs as a pre-commit hook, in CI and as a Claude Code hook. CI also runs a multi-seed stability check.
- **Done** (Q2, Q22) means:
  - `make demo` re-checks the committed code and proofs offline, rejects the vulnerable variant, and shows that the exploit fails on the verified variant;
  - the evaluation reports the agent's success rate, time and cost over 10 runs, plus mutation tests.

### How: milestones

1. **Framework skeleton:** DevContainer (Dafny, Z3, Python, Claude Code, and SQLite including a debug build), Makefile, gate CLI with manifest, and CI.
2. **Theorem template and SQL library:** the language-definition format, the SQL subset definition derived from `parse.y`, and its round-trip proof. The statements are submitted for approval (Q20, Q26).
3. **Fidelity harness:** differential tests against the instrumented SQLite, plus exhaustive literal-lexing tests up to a bounded length.
4. **Example app:** the `examples/userdir` intent, the vulnerable variant, the exploit, and `make demo`.
5. **Agent integration:** agent instructions, `make agent`, `make approve`, and the Claude Code hook.
6. **Generality check:** a custom language that the in-container agent defines and proves.
7. **Evaluation:** 10 agent runs and mutation tests.

## Open items

These are decided when the work reaches them:

- How the toy interpreter in the generality check (milestone 6) parses its custom language. Q27 covers SQLite only.
- Stage 2 of Q24, the generic engine, and validating SQLite's generated parser. Both come after the prototype.

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
| 13 | Proof tool | Owner's rule: decide by experiment if unsure, and switch tools if the implementation looks unlikely to succeed. The experiment ([spikes/q13-dafny-vs-fstar](spikes/q13-dafny-vs-fstar/README.md)) chose Dafny, compiled to Python. The gate verifies with a pinned seed and resource limit, and CI adds a multi-seed stability check. | 2026-10-08 |
| 14 | Layers and generality | A library of reusable proofs is one building block. The approach must also apply to every language emitted to an interpreter, including custom, non-standard ones. The mechanism is decided in Q24. | 2026-10-08 |
| 15 | SQL subset | `SELECT … FROM … [WHERE …]` with comparisons, `AND`/`OR`/`NOT`, parentheses, allowlisted columns, string and integer literals; fully parenthesized. `LIKE … ESCAPE` is a stretch goal. | 2026-10-08 |
| 16 | Example app | Command-line `userdir search <name>` on a seeded SQLite database with a secret column. The vulnerable variant leaks the secrets via a `UNION` exploit. The intent is in `examples/userdir/INTENT.md`. | 2026-10-08 |
| 17 | Parser fidelity | The owner asked for an analysis of the options, judged by precision ([docs/analysis/receiver-fidelity.md](docs/analysis/receiver-fidelity.md)). The decision is Q27. | 2026-10-08 |
| 18 | Agent harness | The setup is self-contained. Claude Code inside the DevContainer writes the implementation and the specification. The owner expects the prototype app plus its specification to take well under 30 minutes. The roles are decided in Q25. | 2026-10-08 |
| 19 | Gate | Checks frozen-file hashes, proof-skipping constructs, verification with pinned versions and limits, then functional and exploit tests. Runs as a pre-commit hook, in GitHub Actions and as a Claude Code hook. | 2026-10-08 |
| 20 | Theorem approval | A pull request with the statement, a plain-English reading and a list of what it does not cover. Approval updates the manifest. | 2026-10-08 |
| 21 | License | Apache-2.0 (applied 2026-10-08). | 2026-10-08 |
| 22 | Evaluation | 10 `make agent` runs (success rate, time, cost), plus mutation tests on encoders and theorem statements. | 2026-10-08 |
| 23 | DevContainer build | Built locally from a Dockerfile, with the same steps on arm64 and x86_64. A prebuilt image is added only if the build exceeds about 10 minutes. | 2026-10-08 |
| 24 | Covering every output language | Two stages. In the prototype: a language-definition format (syntax tree, encoders, parser model) with a fixed theorem template, and per-language round-trip proofs built from a lemma library. SQL is the first definition. As a generality check, the in-container agent defines and proves a second, non-standard language on its own. Later: one generic engine, proven once, for all well-formed definitions. | 2026-10-09 |
| 25 | Roles | Claude in the cloud session builds the framework once. Claude Code in the DevContainer writes each project's specification, gets the owner's approval, then writes the implementation and its proofs until the gate passes. The 30-minute limit is a hard stop; the evaluation measures the real time. | 2026-10-09 |
| 26 | Approval without GitHub | `make approve` shows new or changed specifications in plain English and records their hashes in the manifest through a commit by the owner. Pull requests remain the route through GitHub. | 2026-10-09 |
| 27 | Parser fidelity | Main approach only. The grammar subset comes from SQLite's `parse.y`. The parser model is tested against an instrumented SQLite debug build (its own tokens and parse trees) and with exhaustive literal-lexing tests up to a bounded length. The double-quote misfeature is switched off and NUL is rejected. Not pursued now: the parameter-binding variant, and validating SQLite's generated parser. | 2026-10-09 |
