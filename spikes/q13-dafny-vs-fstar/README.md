# Spike: Dafny vs. F\* for the round-trip proof (Q13)

*2026-10-08.* This experiment backs the decision on open question Q13 in [INTENT.md](../../INTENT.md).

## Question

Which proof tool handles the core proof of this project better? That proof is the extended round-trip `parse(unparse(t)) == t`, for syntax trees whose string literals contain arbitrary, attacker-chosen data.

## Setup

The same tiny SQL-like language is implemented and proven in both tools:

```
cond ::= "name" = '<literal>' | "email" = '<literal>' | ( cond AND cond )
```

The *encoder* doubles every single quote inside a literal. The *parser* is a character-level recursive-descent parser. The literal lexer works like SQLite's `tokenize.c`, where `''` stands for one quote and a single `'` ends the literal.

| File | What it is |
|---|---|
| [`RoundTrip.dfy`](RoundTrip.dfy) | Dafny version, including an executable `Render` method that is compiled to Python |
| [`RoundTrip.fst`](RoundTrip.fst) | F\* version |
| [`difftest.py`](difftest.py) | Differential test of the compiled Dafny code against the real SQLite |

## Results

| | Dafny 4.11.0 | F\* 2026.07.24 |
|---|---|---|
| Install on Linux x86_64 | .NET 8 SDK + `dotnet tool install dafny` + `z3` 4.12.1 from the `z3-solver` wheel, about 3 minutes | one 247 MB tarball with Z3 included, about 1 minute |
| Size of code plus proof | 195 lines | 161 lines |
| Attempts until the first full proof | 2 (one missing hint about sequence slicing) | 4 (one restructuring, two typing issues with refined return types) |
| Verification time | about 4 s | about 4.7 s |
| Stability over 10 solver seeds | **The first version failed under seed 1.** After splitting one lemma into two, 10/10 pass. The most expensive proof's cost varies 7.6× between seeds. | 10/10 pass with the default deterministic resource limit |
| Negative control: encoder without quote doubling | rejected (proof fails) | rejected (proof fails) |
| Runs as | Python; the gate runs it with the standard `sqlite3` module | OCaml (extraction works; running it needs an OCaml toolchain, which was not installed for the spike) |
| Differential test against SQLite 3.45.1 | 20,000 random trees with hostile data, 5 seeds; query results, literal decoding and compiled structure all match | not run |

Three side findings matter for later decisions:

- **SMT proofs can be brittle.** A proof that passes with one solver seed can fail with another. Therefore the gate verifies with a pinned seed and resource limit, which makes it deterministic. CI additionally runs a multi-seed stability check, so brittle proofs fail early.
- **`EXPLAIN` bytecode is an imprecise test oracle.** SQLite's optimizer merges identical `WHERE` terms, so the compiled bytecode depends on literal values. A naive comparison raised false alarms until the harmless replacement data kept the same equality pattern as the original. This is relevant for Q17.
- **NUL fails closed.** Python's `sqlite3` refuses SQL text that contains a NUL character (`ProgrammingError`).

## Conclusion

Both tools handle this proof pattern with similar effort. In this sample F\* was more robust across solver seeds. Dafny was robust after a standard fix.

The decision goes to **Dafny**, for two reasons:

- it has the stronger evidence that LLM agents can write its proofs (see section 7 of the literature review);
- it compiles to mainstream languages, which matters for adoption by other projects.

Following the owner's rule for Q13, we switch tools if larger proofs show persistent brittleness.

## Reproduce

```sh
dafny verify RoundTrip.dfy --solver-path <z3-4.12.1>
dafny build --target py RoundTrip.dfy --output build/RoundTrip
python3 -I difftest.py build/RoundTrip-py 4000 1
fstar.exe RoundTrip.fst
```
