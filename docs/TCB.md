# Trusted computing base and known gaps

What the prototype guarantees, what it assumes, and what it only tests. The pieces below are not proven; if one of them is wrong, a "verified" application can still be injectable. Keep this file in step with the code.

## What is proven (by the gate)

For the `userdir` example, with the approved specification `examples/userdir/spec/UserdirSpec.dfy`:

1. **Round-trip** (`lib/SqlProof.dfy`, lemma `RoundTrip`): for every SQL syntax tree of the subset, including trees whose string literals hold arbitrary NUL-free text, `Parse(Unparse(t)) == Some(t)`.
2. **Application** (`examples/userdir/src/App.dfy`): the SQL text the application returns equals `Unparse(Intended(name))`, where the intended tree has the untrusted name only as a string literal.

Together: the receiver model reads exactly the intended tree, whatever the name contains.

## What is trusted (assumed, not proven)

| # | Component | Why it is trusted | Mitigation |
|---|---|---|---|
| 1 | Dafny verifier (Boogie, Z3 4.13.4) | A soundness bug there would make any proof worthless | Pinned versions; `dafny audit` must report 0 findings; no skipped proofs allowed |
| 2 | Dafny to Python compiler and the `_dafny` runtime | We assume the compiled code behaves as the verified Dafny semantics | Differential tests (`make fidelity`, `make demo`) execute the compiled code against SQLite |
| 3 | Python, its `sqlite3` module and the system SQLite library | They execute the text | The fidelity harness runs its literal and query checks on the runtime library too. The debug oracle is a different SQLite version (3.53.4), see gap A |
| 4 | **The parser model matches SQLite** (`Parse` in `lib/SqlSpec.dfy`) | The theorem is about our model | Tested, not proven: exhaustive literal lexing up to a bounded length, 3,000+ random trees, SQLite's own tokens and parse trees (`tools/fidelity`). See `docs/analysis/receiver-fidelity.md` |
| 5 | The glue (`examples/userdir/glue/userdir.py`) | It runs the text and is not verified | About 60 lines; frozen and hash-checked; rejects NUL and non-UTF-8 input (the proof's `Data` type excludes NUL); switches off SQLite's double-quoted-string misfeature |
| 6 | The gate (`tools/gate`) | It decides what counts as proven | Frozen and hash-checked; unit tests; 14 mutation tests (`make mutation-test`) that must be rejected; CI runs them |
| 7 | The approved theorem statements and definitions | A weak or wrong statement proves nothing useful | Owner approval (`make approve`) with a plain-English reading (`READING.md` beside each specification); `CODEOWNERS` in CI |
| 8 | The owner's machine and the DevContainer image | Supply chain | Z3 archives are pinned by SHA-256; the SQLite amalgamation is checked against sqlite.org's published SHA3-256; Dafny is pinned by version; the Claude Code package is pinned by version |

## Known gaps

- **A. Oracle and runtime SQLite differ.** The debug oracle is built from SQLite 3.53.4 (pinned, hash-checked). The application runs on the system library (3.45.1 in Ubuntu 24.04). The literal and query checks run on both; token and parse-tree checks only on the oracle. For this subset, quoting rules have been stable for decades, but the gap exists. Fix: build the oracle from the runtime version, or ship the application with the pinned library.
- **B. The parser model is tested, not proven, against SQLite.** Option "validate SQLite's generated parser against `parse.y`" (option 3 in the fidelity analysis) would prove the parser part. It is not done. The hand-written tokenizer would still be tested.
- **C. The model parser is strict.** It accepts only the canonical text of the unparser. The theorem covers the texts the application emits, which is the property needed. The application is forced to emit exactly that text by the specification (`sql == Unparse(Intended(name))`).
- **D. Only injection into this query is covered.** Not covered: access control, denial of service, SQL features outside the subset, other output channels of the application.
- **E. Identifiers are not user-controlled here.** Table and column names are fixed in the specification. A future language definition that lets users choose identifiers needs an allowlist in the specification.
- **F. SMT proofs can be brittle.** The first version of the SQL proof failed on 1 of 10 solver seeds and was restructured; it now passes 20 of 20. The gate uses an explicit seed and a resource limit (not wall-clock time); CI runs 10 seeds.
- **G. The agent harness is untested with a live model.** `make agent` was tested with a stand-in for the `claude` command (`make agent-selftest`, `tools/agent/fake_claude.py`). A live run needs your account and has not been done.
- **H. Hooks are help, not a boundary.** The PreToolUse hook blocks writes to frozen files; a shell trick could slip past it, but the gate's hash check catches any change to a frozen file however it was made.
- **I. Approval is pending.** The frozen files are hashed in `gate/manifest.json` as *proposed*. The gate accepts a proposed manifest only with `--allow-proposed`.
