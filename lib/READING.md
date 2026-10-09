# Reading of the SQL layer (`lib/SqlSpec.dfy` and `lib/SqlProof.dfy`, for owner approval)

**The language.** A strict, canonical subset of SQLite's SELECT:

    SELECT "c1", "c2" FROM "t" [WHERE <cond>]
    <cond> ::= (<operand> <op> <operand>) | (NOT <cond>) | (<cond> AND <cond>) | (<cond> OR <cond>)
    <operand> ::= "identifier" | 'string literal' | integer      <op> ::= = <> < <= > >=

Every condition is fully parenthesized. Identifiers are letters, digits and `_`, always double-quoted. Integers are in the range of a 64-bit signed integer, minus the most negative value. Text data may contain any character except NUL.

**Where untrusted data can go.** In the syntax tree, only `Str(...)` holds free text, and it is a literal. Everything else (identifiers, operators, keywords) is either fixed by the program or restricted to a safe alphabet. So untrusted text can reach the SQL only as the *contents* of a string literal.

**The unparser.** It writes a string literal as `'` + the text with every `'` doubled + `'`. This is SQLite's rule (no backslash escapes).

**The model of the receiver.** `Parse` is a strict recognizer for exactly the texts the unparser writes. It reads a literal the way SQLite's tokenizer does: a doubled quote is one quote, a single quote ends the literal.

**The theorem (`RoundTrip`).** For every query tree, parsing the unparsed text returns the same tree. Example: the data `x') UNION SELECT secret FROM users --` becomes the literal `'x'') UNION SELECT secret FROM users --'`, which the receiver reads as one string, not as SQL.

**What it does not cover.**
- Whether SQLite agrees with `Parse` on these texts: tested, not proven (`make fidelity`; see `docs/analysis/receiver-fidelity.md`).
- Anything outside this subset (other statements, functions, comments, `LIKE ... ESCAPE`).
- Data containing NUL: the type excludes it; the glue rejects it before the app runs.
