#!/usr/bin/env python3
"""Fidelity harness (Q17/Q27): does SQLite read the SQL our verified unparser emits the way our model says?

The theorem (lib/SqlProof.dfy) is about OUR model of the receiver's parser. This harness tests that
the real receiver agrees, using an oracle built from SQLite's own source (tools/fidelity/oracle.c,
compiled with SQLITE_DEBUG): the real tokenizer and the real parse tree.

Checks (each reports how many cases it ran):
  lexing-exhaustive   every string over a hostile alphabet up to a bounded length, embedded as a
                      literal: SQLite's tokenizer must produce exactly the expected tokens, the
                      string token must be exactly our encoded literal, and SQLite must evaluate it
                      back to the original data.
  payloads            a fixed list of classic injection payloads, same checks.
  random-trees        random syntax trees with hostile data: token types in order must match the
                      tree; the tokens must concatenate to the emitted text; SQLite's own parse tree
                      must have the same shape as the tree (newline-free data; newlines are covered by
                      the tokenizer checks); well-typed queries must return the rows Python expects.
  parse-model         the compiled Dafny Parse returns the same tree for the emitted text.
  quirks              NUL stops SQLite's tokenizer (why NUL is rejected); with the double-quote
                      misfeature off, an unknown double-quoted name is an error; quoted keywords
                      tokenize as identifiers.

Usage: check_fidelity.py [--build DIR] [--oracle PATH] [--trees N] [--max-len L] [--seed S]
Exit status 0 only if every check passed.
"""
import argparse
import itertools
import random
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAXINT = 9223372036854775807
ALPHABET = ["a", "'", '"', "\\", " ", "\n", ";", "-", "%", "é"]
PAYLOADS = ["' OR '1'='1", "') OR ('1'='1", "'; DROP TABLE users; --", "x') UNION SELECT secret, email FROM users --",
            "\\' OR 1=1 --", "''", "'''", "' --", "/*", "*/", "' /*", "\"", "\" OR \"1\"=\"1", "`", "‮' OR 1=1",
            "😀'😀", "a\nb' OR '1'='1", "\r\n", "\t", "%", "_", "NULL", "0x41", "1e999", "' AND (SELECT 1) --"]
PIECES = ALPHABET + ["' OR ", " UNION SELECT ", "--", "/*", "x'", "'')", "😀", "DROP TABLE users", "NULL"]
COLS = ["id", "name", "email", "secret"]
TEXT_COLS = ["name", "email", "secret"]
ROWS = [(1, "alice", "alice@x", "s1"), (2, "bob", "b@x", "s2"), (3, "' OR '1'='1", "evil@x", "s3"),
        (4, "o'brien", "ob@x", "s4"), (5, "ä😀", "u@x", "s5"), (-7, "x", "y", "z"), (MAXINT, "big", "big@x", "bigs")]
OPS = ["eq", "ne", "lt", "le", "gt", "ge"]
OPTOK = dict(eq="EQ", ne="NE", lt="LT", le="LE", gt="GT", ge="GE")
PYOP = dict(eq=lambda a, b: a == b, ne=lambda a, b: a != b, lt=lambda a, b: a < b,
            le=lambda a, b: a <= b, gt=lambda a, b: a > b, ge=lambda a, b: a >= b)


# --------------------------------------------------------------------------- Dafny bridge
class Bridge:
    def __init__(self, build):
        sys.path.insert(0, str(build))
        import _dafny, Prelude, Sql
        self.d, self.P, self.S = _dafny, Prelude, Sql
        self.ops = dict(eq=Sql.CmpOp_Eq(), ne=Sql.CmpOp_Ne(), lt=Sql.CmpOp_Lt(), le=Sql.CmpOp_Le(),
                        gt=Sql.CmpOp_Gt(), ge=Sql.CmpOp_Ge())

    def s(self, text):
        return self.d.SeqWithoutIsStrInference(map(self.d.CodePoint, text))

    def operand(self, o):
        S = self.S
        return {"col": lambda: S.Operand_Col(self.s(o[1])), "str": lambda: S.Operand_Str(self.s(o[1])),
                "num": lambda: S.Operand_Num(o[1])}[o[0]]()

    def cond(self, c):
        S = self.S
        if c[0] == "cmp":
            return S.Cond_Cmp(self.operand(c[1]), self.ops[c[2]], self.operand(c[3]))
        if c[0] == "not":
            return S.Cond_Not(self.cond(c[1]))
        return (S.Cond_And if c[0] == "and" else S.Cond_Or)(self.cond(c[1]), self.cond(c[2]))

    def query(self, q):
        cols, table, where = q
        w = self.P.Option_Some(self.cond(where)) if where else self.P.Option_None()
        return self.S.Query_Select(self.d.SeqWithoutIsStrInference(map(self.s, cols)), self.s(table), w)

    def unparse(self, q):
        return self.S.default__.Unparse(self.query(q)).VerbatimString(False)

    def parse_ok(self, q, text):
        r = self.S.default__.Parse(self.s(text))
        return r.is_Some and r.value == self.query(q)


# ------------------------------------------------------------------------------- oracle
class Oracle:
    def __init__(self, path, setup=()):
        self.path, self.setup = str(path), list(setup)

    def call(self, reqs, chunk=4000):
        """Each chunk runs in a fresh oracle process (fresh in-memory database), so the setup
        statements are replayed at the start of every chunk and their answers dropped."""
        out = []
        for i in range(0, len(reqs), chunk):
            part = self.setup + reqs[i:i + chunk]
            inp = "".join(f"{m} {t.encode('utf-8', 'surrogatepass').hex()}\n" for m, t in part)
            p = subprocess.run([self.path], input=inp, capture_output=True, text=True, encoding="utf-8", errors="replace")
            cur, res = [], []
            for line in p.stdout.split("\n"):
                if line == "END":
                    res.append(cur); cur = []
                else:
                    cur.append(line)
            assert len(res) == len(part), f"oracle answered {len(res)} of {len(part)} requests: {p.stderr[:200]}"
            out += res[len(self.setup):]
        return out


def tokens(resp):
    """[(NAME, bytes)] without SPACE; second value is the token text."""
    toks, stop = [], False
    for line in resp:
        if line.startswith("TOK "):
            _, name, _, hx = line.split(" ")
            toks.append((name, bytes.fromhex(hx)))
        elif line.startswith("STOP"):
            stop = True
    return [t for t in toks if t[0] != "SPACE"], toks, stop


def value(resp):
    for line in resp:
        if line.startswith("VAL"):
            parts = line.split(" ")
            hx = parts[1] if len(parts) > 1 else ""
            return b"" if hx == "-" else bytes.fromhex(hx)
        if line.startswith(("NONE", "ERR")):
            return line
    return "no value"


# ----------------------------------------------------------------- expected structure
def exp_tokens(q):
    cols, table, where = q
    t = ["SELECT", "ID"] + sum([["COMMA", "ID"] for _ in cols[1:]], []) + ["FROM", "ID"]
    if where:
        t += ["WHERE"] + cond_tokens(where)
    return t


def operand_tokens(o):
    if o[0] == "col":
        return ["ID"]
    if o[0] == "str":
        return ["STRING"]
    return (["MINUS"] if o[1] < 0 else []) + ["INTEGER"]


def cond_tokens(c):
    if c[0] == "cmp":
        return ["LP"] + operand_tokens(c[1]) + [OPTOK[c[2]]] + operand_tokens(c[3]) + ["RP"]
    if c[0] == "not":
        return ["LP", "NOT"] + cond_tokens(c[1]) + ["RP"]
    return ["LP"] + cond_tokens(c[1]) + [c[0].upper()] + cond_tokens(c[2]) + ["RP"]


def exp_operand(o):
    if o[0] == "col":
        return (f"ID {o[1]}", ())
    if o[0] == "str":
        return (f"STR {o[1]}", ())
    return ("NUM " + str(o[1]), ()) if o[1] >= 0 else ("UMINUS", (("NUM " + str(-o[1]), ()),))


def exp_cond(c):
    if c[0] == "cmp":
        return (OPTOK[c[2]], (exp_operand(c[1]), exp_operand(c[3])))
    if c[0] == "not":
        return ("NOT", (exp_cond(c[1]),))
    return (c[0].upper(), (exp_cond(c[1]), exp_cond(c[2])))


def exp_tree(q):
    cols, table, where = q
    kids = [("result-set", tuple(("SPAN", ((f"ID {c}", ()),)) for c in cols)), ("FROM", ((f"TABLE {table}", ()),))]
    if where:
        kids.append(("WHERE", (exp_cond(where),)))
    return ("SELECT", tuple(kids))


def parse_dump(resp):
    nodes = []
    for line in resp:
        i = line.find("-- ")
        if i < 1 or line[i - 1] not in "|'" or set(line[:i - 1]) - set(" |"):
            continue
        text, depth = line[i + 3:], (i - 1) // 4
        if text.startswith("SELECT ("):
            label = "SELECT"
        elif text.startswith("SPAN("):
            label = "SPAN"
        elif text.startswith("ID "):
            label = "ID " + text[3:].strip('"')
        elif text.startswith("{"):
            label = "TABLE " + text.split("} ", 1)[1].strip()
        elif text.startswith("'"):
            label = "STR " + text[1:-1].replace("''", "'")
        elif re.fullmatch(r"-?\d+", text):
            label = "NUM " + text
        else:
            label = text.strip()
        nodes.append((depth, label))
    def build(pos, depth):
        label = nodes[pos][1]; kids = []; pos += 1
        while pos < len(nodes) and nodes[pos][0] > depth:
            kid, pos = build(pos, depth + 1); kids.append(kid)
        return (label, tuple(kids)), pos
    return build(0, 0)[0] if nodes else None


def decode_literal(b):
    return b[1:-1].replace(b"''", b"'")


# ------------------------------------------------------------------------ generators
def rand_data(rng):
    if rng.random() < 0.25:
        return rng.choice([r[1] for r in ROWS] + [r[2] for r in ROWS])
    return "".join(rng.choice(PIECES) for _ in range(rng.randint(0, 5)))


def rand_operand(rng):
    k = rng.random()
    if k < 0.35:
        return ("col", rng.choice(COLS))
    if k < 0.75:
        return ("str", rand_data(rng))
    return ("num", rng.choice([0, 1, -1, 42, -42, MAXINT, -MAXINT, rng.randint(-10**6, 10**6)]))


def rand_cond(rng, depth, typed):
    if depth == 0 or rng.random() < 0.4:
        if typed:
            if rng.random() < 0.5:
                return ("cmp", ("col", rng.choice(TEXT_COLS)), rng.choice(OPS), ("str", rand_data(rng)))
            return ("cmp", ("col", "id"), rng.choice(OPS), ("num", rng.choice([0, 1, 3, -7, 5, MAXINT, -MAXINT, rng.randint(-9, 9)])))
        return ("cmp", rand_operand(rng), rng.choice(OPS), rand_operand(rng))
    k = rng.random()
    if k < 0.2:
        return ("not", rand_cond(rng, depth - 1, typed))
    return (("and" if k < 0.6 else "or"), rand_cond(rng, depth - 1, typed), rand_cond(rng, depth - 1, typed))


def rand_query(rng, typed):
    cols = [rng.choice(COLS) for _ in range(rng.randint(1, 3))]
    return (cols, "users", rand_cond(rng, 3, typed) if rng.random() < 0.9 else None)


def eval_cond(c, row):
    if c[0] == "cmp":
        val = lambda o: row[COLS.index(o[1])] if o[0] == "col" else o[1]
        return PYOP[c[2]](val(c[1]), val(c[3]))
    if c[0] == "not":
        return not eval_cond(c[1], row)
    f = all if c[0] == "and" else any
    return f([eval_cond(c[1], row), eval_cond(c[2], row)])


def string_literals(q):
    out = []
    def walk(c):
        if c[0] == "cmp":
            out.extend(o[1] for o in (c[1], c[3]) if o[0] == "str")
        else:
            for k in c[1:]:
                walk(k)
    if q[2]:
        walk(q[2])
    return out


def has_newline(q):
    """Newlines in data would make SQLite's tree dump ambiguous; those cases are covered by the tokenizer checks."""
    return any("\n" in x or "\r" in x for x in string_literals(q))


# ---------------------------------------------------------------------------- checks
class Results:
    def __init__(self):
        self.rows, self.fails = [], []

    def add(self, name, count, bad, examples=()):
        self.rows.append((name, count, bad))
        self.fails += [f"{name}: {e}" for e in examples[:3]]


def check_literals(br, orc, datas, name, res):
    sqls = [br.unparse((["name"], "users", ("cmp", ("col", "name"), "eq", ("str", d)))) for d in datas]
    t_resp = orc.call([("T", q) for q in sqls])
    lits = []
    bad, ex = 0, []
    want = ["SELECT", "ID", "FROM", "ID", "WHERE", "LP", "ID", "EQ", "STRING", "RP"]
    for d, q, r in zip(datas, sqls, t_resp):
        toks, all_toks, stop = tokens(r)
        lit_text = ("'" + d.replace("'", "''") + "'").encode()
        ok = ([n for n, _ in toks] == want and not stop and b"".join(t for _, t in all_toks) == q.encode()
              and toks[8][1] == lit_text and decode_literal(toks[8][1]) == d.encode())
        lits.append(toks[8][1].decode("utf-8", "replace") if len(toks) > 8 else "")
        if not ok:
            bad += 1; ex.append(f"data={d!r} sql={q!r} tokens={[n for n, _ in toks]}")
    v_resp = orc.call([("V", lit) for lit in lits])
    for d, lit, r in zip(datas, lits, v_resp):
        got = value(r)
        if got != d.encode():
            bad += 1; ex.append(f"data={d!r} literal={lit!r} SQLite evaluates to {got!r}")
    res.add(name, len(datas), bad, ex)


def runtime_db():
    """The SQLite library that Python's sqlite3 module links: the one the application really runs on."""
    db = sqlite3.connect(":memory:")
    db.setconfig(sqlite3.SQLITE_DBCONFIG_DQS_DML, False)
    db.setconfig(sqlite3.SQLITE_DBCONFIG_DQS_DDL, False)
    db.execute("CREATE TABLE users(id INTEGER, name TEXT, email TEXT, secret TEXT)")
    db.executemany("INSERT INTO users VALUES (?,?,?,?)", ROWS)
    return db


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", default=str(ROOT / "build/verified/app-py"))
    ap.add_argument("--oracle", default=str(ROOT / "build/fidelity/oracle"))
    ap.add_argument("--trees", type=int, default=3000)
    ap.add_argument("--max-len", type=int, default=5)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    if not Path(a.oracle).exists():
        sys.exit(f"{a.oracle} not found: run `sh tools/fidelity/build_oracle.sh` first")
    setup = [("X", "INSERT INTO users VALUES(%d,'%s','%s','%s')" % (r[0], r[1].replace("'", "''"), r[2], r[3])) for r in ROWS]
    br, orc, rng, res = Bridge(a.build), Oracle(a.oracle, setup), random.Random(a.seed), Results()
    t0 = time.time()

    datas = [""] + ["".join(p) for n in range(1, a.max_len + 1) for p in itertools.product(ALPHABET, repeat=n)]
    check_literals(br, orc, datas, f"lexing-exhaustive (alphabet {len(ALPHABET)}, length <= {a.max_len})", res)
    check_literals(br, orc, PAYLOADS, "payloads", res)

    # random trees
    queries = [rand_query(rng, typed=False) for _ in range(a.trees)]
    sqls = [br.unparse(q) for q in queries]
    t_resp = orc.call([("T", s) for s in sqls])
    bad_tok, ex_tok, bad_model, ex_model = 0, [], 0, []
    for q, s, r in zip(queries, sqls, t_resp):
        toks, all_toks, stop = tokens(r)
        ok = ([n for n, _ in toks] == exp_tokens(q) and not stop and b"".join(t for _, t in all_toks) == s.encode())
        strs = [t for n, t in toks if n == "STRING"]
        ok = ok and [decode_literal(t) for t in strs] == [w.encode() for w in string_literals(q)]
        if not ok:
            bad_tok += 1; ex_tok.append(f"sql={s!r}")
        if not br.parse_ok(q, s):
            bad_model += 1; ex_model.append(f"sql={s!r}")
    res.add("random-trees: tokens", len(queries), bad_tok, ex_tok)
    res.add("parse-model: Dafny Parse(Unparse(t)) == t", len(queries), bad_model, ex_model)

    flat = [(q, s) for q, s in zip(queries, sqls) if not has_newline(q)]
    p_resp = orc.call([("P", s) for _, s in flat])
    bad_tree, ex_tree = 0, []
    for (q, s), r in zip(flat, p_resp):
        got = parse_dump(r)
        if got != exp_tree(q) or "RC 0" not in r:
            bad_tree += 1; ex_tree.append(f"sql={s!r}\n      got  {got}\n      want {exp_tree(q)}")
    res.add("random-trees: SQLite parse tree == tree", len(flat), bad_tree, ex_tree)

    typed = [rand_query(rng, typed=True) for _ in range(a.trees)]
    tsqls = [br.unparse(q) for q in typed]
    q_resp = orc.call([("Q", s) for s in tsqls])
    bad_sem, ex_sem = 0, []
    for q, s, r in zip(typed, tsqls, q_resp):
        want = sorted(" ".join((str(row[COLS.index(c)]).encode().hex() or "-") for c in q[0]) for row in ROWS
                      if q[2] is None or eval_cond(q[2], row))
        got = sorted(line[4:] for line in r if line.startswith("ROW "))
        if got != want:
            bad_sem += 1; ex_sem.append(f"sql={s!r}")
    res.add("random-trees: query results", len(typed), bad_sem, ex_sem)

    # the same checks on the SQLite library the application really runs on (Python's sqlite3 module)
    rt = runtime_db()
    bad_rt, ex_rt, n_rt = 0, [], 0
    for d in datas[:: max(1, len(datas) // 20000)] + PAYLOADS:
        lit = "'" + d.replace("'", "''") + "'"
        n_rt += 1
        if rt.execute("SELECT " + br.unparse((["name"], "users", ("cmp", ("col", "name"), "eq", ("str", d)))).split(" = ", 1)[1][:-1]).fetchone()[0] != d:
            bad_rt += 1; ex_rt.append(f"literal {lit!r}")
    for q, s in zip(typed, tsqls):
        n_rt += 1
        got = sorted(map(tuple, rt.execute(s).fetchall()))
        want = sorted(tuple(row[COLS.index(c)] for c in q[0]) for row in ROWS if q[2] is None or eval_cond(q[2], row))
        if got != want:
            bad_rt += 1; ex_rt.append(f"sql={s!r}")
    res.add(f"runtime SQLite {sqlite3.sqlite_version}: literals and query results", n_rt, bad_rt, ex_rt)

    # quirks that the glue and the proof rely on
    nul = orc.call([("T", br.unparse((["name"], "users", ("cmp", ("col", "name"), "eq", ("str", "a")))).replace("'a'", "'a\x00b'"))])[0]
    dq = orc.call([("P", 'SELECT "nosuch" FROM "users"')])[0]
    kw = orc.call([("T", '"select"')])[0]
    quirks = [("NUL stops SQLite's tokenizer", any(l.startswith("STOP") for l in nul)),
              ("unknown double-quoted name is an error (DQS off)", "RC 1" in dq),
              ('"select" tokenizes as an identifier', tokens(kw)[0] == [("ID", b'"select"')])]
    res.add("quirks", len(quirks), sum(not ok for _, ok in quirks), [n for n, ok in quirks if not ok])

    print(f"oracle: SQLite debug build (see tools/fidelity/sqlite.env); runtime library: SQLite {sqlite3.sqlite_version}")
    print(f"{'check':58s} {'cases':>8s}  result")
    for name, count, bad in res.rows:
        print(f"{name:58s} {count:8d}  {'ok' if not bad else f'{bad} FAILED'}")
    print(f"elapsed {time.time() - t0:.0f}s")
    if res.fails:
        print("\nfirst failures:\n  " + "\n  ".join(res.fails[:12]))
    sys.exit(1 if res.fails else 0)


if __name__ == "__main__":
    main()
