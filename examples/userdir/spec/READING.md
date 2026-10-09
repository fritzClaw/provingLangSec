# Reading of `UserdirSpec.dfy` (for owner approval)

**Plain English.** `Search(name)` returns SQL text. The specification requires that this text equals the SQL text produced by the verified unparser for exactly one query tree: `SELECT "name", "email" FROM "users" WHERE ("name" = <name as a string literal>)`. The `name` can only appear as that literal.

**What follows.** The SQL layer proves that parsing the text gives back the same tree (`lib/SqlProof.dfy`, lemma `RoundTrip`). So a receiver that parses like our model sees only that tree. No input can add a column, a table, a `UNION` or a comment.

**What it does not cover.**
- That the receiver parses like the model: tested against SQLite by `tools/fidelity`, not proven.
- That the app returns the right rows: covered by tests.
- Access control, resource use, and anything outside injection into this query.
- The Python glue (`glue/userdir.py`), which is trusted. See `docs/TCB.md`.
