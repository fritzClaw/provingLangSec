"""Differential test: Dafny-verified unparser (compiled to Python) vs. the real SQLite.

Checks for random condition trees with adversarial string data:
  1. semantic: SQLite's result rows equal a Python evaluation of the tree;
  2. literal: SELECT '<encoded>' returns the original string;
  3. structure: EXPLAIN opcodes equal those of the same tree with harmless data.
Usage: python3 -I difftest.py <path-to-RoundTrip-py> <iterations> <seed>
"""
import random
import sqlite3
import sys

sys.path.insert(0, sys.argv[1])
import _dafny  # noqa: E402
import RoundTrip as RT  # noqa: E402

ATOMS = ["'", "''", '"', ";", "--", "/*", "*/", " OR ", " UNION SELECT ", "\\", "%", "_", " ", "\n", "\t",
         "a", "b", "ä", "😀", "‮", "x'", "' OR '1'='1", "') OR ('a'='a", "DROP TABLE users", "NULL"]
COLS = {"name": RT.Col_Name(), "email": RT.Col_Email()}
ROWS = [("alice", "a@x"), ("bob", "b@x"), ("' OR '1'='1", "evil@x"), ("o'brien", "ob@x"), ("ä😀", "u@x")]


def rand_str(rng):
    if rng.random() < 0.3:
        return rng.choice([r[0] for r in ROWS] + [r[1] for r in ROWS])
    return "".join(rng.choice(ATOMS) for _ in range(rng.randint(0, 6)))


def rand_tree(rng, depth):
    if depth == 0 or rng.random() < 0.4:
        col = rng.choice(list(COLS))
        return ("eq", col, rand_str(rng))
    return ("and", rand_tree(rng, depth - 1), rand_tree(rng, depth - 1))


def to_dafny(t):
    if t[0] == "eq":
        return RT.Cond_Eq(COLS[t[1]], _dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, t[2])))
    return RT.Cond_And(to_dafny(t[1]), to_dafny(t[2]))


def harmless(t, names=None):
    # Replace each distinct literal by a distinct harmless one, preserving the equality pattern
    # (SQLite's optimizer merges identical WHERE terms, so equal literals must stay equal).
    names = {} if names is None else names
    if t[0] == "eq":
        return ("eq", t[1], names.setdefault(t[2], "x%d" % len(names)))
    return ("and", harmless(t[1], names), harmless(t[2], names))


def evaluate(t, row):
    if t[0] == "eq":
        return row[0 if t[1] == "name" else 1] == t[2]
    return evaluate(t[1], row) and evaluate(t[2], row)


def render(t):
    return RT.default__.Render(to_dafny(t)).VerbatimString(False)


def opcodes(db, where):
    return [r[1] for r in db.execute("EXPLAIN SELECT name, email FROM users WHERE " + where)]


def main():
    iterations, seed = int(sys.argv[2]), int(sys.argv[3])
    rng = random.Random(seed)
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE users (name TEXT, email TEXT)")
    db.executemany("INSERT INTO users VALUES (?, ?)", ROWS)
    stats = {"semantic": 0, "literal": 0, "structure": 0}
    for _ in range(iterations):
        t = rand_tree(rng, 3)
        where = render(t)
        got = sorted(db.execute("SELECT name, email FROM users WHERE " + where).fetchall())
        want = sorted(r for r in ROWS if evaluate(t, r))
        assert got == want, (where, got, want)
        stats["semantic"] += 1
        s = rand_str(rng)
        enc = render(("eq", "name", s)).split(" = ", 1)[1]
        assert db.execute("SELECT " + enc).fetchone()[0] == s, (s, enc)
        stats["literal"] += 1
        assert opcodes(db, where) == opcodes(db, render(harmless(t))), where
        stats["structure"] += 1
    try:
        db.execute("SELECT " + render(("eq", "name", "a\x00b")).split(" = ", 1)[1])
        nul = "accepted"
    except Exception as e:  # sqlite3 refuses SQL text containing NUL
        nul = f"rejected ({type(e).__name__}: {e})"
    print(f"seed={seed} passed: {stats}; SQLite {sqlite3.sqlite_version}; NUL in SQL text: {nul}")


main()
