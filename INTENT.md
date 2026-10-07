# Intent: Provably injection-free code from AI agents

> **Status:** draft. We're working through grilling round 1. Each decision goes into the log below once the owner answers it.

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

## Open questions (round 1)

The recommended answer is in parentheses.

1. Purpose: is this a research prototype rather than a product? (yes)
2. Definition of done: a single `make demo` that checks the proof offline and deterministically, rejects the vulnerable variant, and shows the exploit failing on the verified variant. A separate, optional `make agent` regenerates the code live. (yes)
3. Meaning of "injection-free":
   - output is built only by an unparser;
   - `parse(unparse(t)) = t` holds for all trees `t`;
   - untrusted input enters the tree only as leaves.

   (yes)
4. Scope: prove injection-freedom only, and cover functional behavior with tests. (yes)
5. Trust model, following proof-carrying code:
   - the LLM is untrusted;
   - the pinned checker is the only judge;
   - humans own the theorems, which are frozen;
   - no admits or axioms are allowed;
   - an explicit TCB document lists everything that remains trusted.

   (yes)
6. The verified code is the code that runs. There is no hand-written model of other code. (yes)
7. First target: SQL injection against SQLite, on a small SQL subset. (yes)
8. F* and Coq are examples. The prover is picked after the literature review, against explicit criteria. (yes)
9. The literature review comes first: `docs/literature-review.md` plus `references.bib`. (yes)
10. "Always" is enforced by a deterministic gate (CLI, pre-commit, CI) that fails closed. Agent adapters are thin layers on top, Claude Code first. (yes)
11. DevContainer host: Docker with VS Code or the devcontainer CLI, on both x86_64 and arm64. (yes)
12. This file is the single source of truth, and all docs are in English. (yes)

## Decision log

| # | Question | Decision | Date |
|---|----------|----------|------|
| – | (no decisions yet) | | |
