#!/usr/bin/env python3
"""Mutation tests of the gate itself (Q22): each scenario runs the full gate on a copy of the
repository in which something was broken or an agent cheated, and checks that the gate
rejects it at the expected step. Takes a few minutes (each rejection at `verify` runs Dafny).

    python3 -I tools/gate/mutation_test.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IGNORE = shutil.ignore_patterns(".git", "build", "runs", "__pycache__", ".gate-state")
APP = "examples/userdir/src/App.dfy"
SPEC_HEADER = 'include "../spec/UserdirSpec.dfy"\n'


def edit(path, old, new):
    def f(root):
        p = root / path
        s = p.read_text()
        assert old in s, f"{old!r} not found in {path}"
        p.write_text(s.replace(old, new, 1))
    return f


def write(path, text):
    return lambda root: (root / path).write_text(text)


def propose(root):
    subprocess.run([sys.executable, "-I", str(root / "tools/gate/approve.py"), "propose"], check=True, capture_output=True)


def app(body, extra=""):
    return write(APP, SPEC_HEADER + extra + "module App refines UserdirSpec {\n  method Search(name: Sql.Data) returns (sql: string)\n"
                 + body + "\n}\n")


def seq(*fs):
    return lambda root: [f(root) for f in fs]


# (name, mutation, step that must fail)
SCENARIOS = [
    ("agent edits a test", edit("examples/userdir/tests/test_userdir.py", "def test_exact_match", "def test_exact_match_x"), "manifest"),
    ("agent edits the glue", edit("examples/userdir/glue/userdir.py", "DQS_DML, False", "DQS_DML, True"), "manifest"),
    ("agent weakens the theorem statement", edit("spec/LanguageSpec.dfy", "ensures Parse(Unparse(t)) == Some(t)", "ensures true"), "manifest"),
    ("agent adds an unlisted file next to the spec", write("examples/userdir/spec/Extra.dfy", "module Extra {}\n"), "manifest"),
    ("agent concatenates strings (classic injection)", app('  {\n    sql := "SELECT \\"name\\", \\"email\\" FROM \\"users\\" WHERE (\\"name\\" = \'" + name + "\')";\n  }'), "verify"),
    ("agent uses assume", app("  {\n    sql := \"\";\n    assume sql == Sql.Unparse(Intended(name));\n  }"), "scan"),
    ("agent uses a bodyless {:axiom} method", write(APP, SPEC_HEADER + "module App refines UserdirSpec {\n  method {:axiom} Search(name: Sql.Data) returns (sql: string)\n}\n"), "scan"),
    ("agent hides assume after a quote character literal", app("  {\n    var q := '\"'; sql := \"\"; assume false; var r := '\"';\n  }"), "scan"),
    ("agent includes an unlisted file", seq(write("outside.dfy", "module Outside {}\n"),
        write(APP, SPEC_HEADER + 'include "../../../outside.dfy"\nmodule App refines UserdirSpec {\n  method Search(name: Sql.Data) returns (sql: string) { sql := Sql.Unparse(Intended(name)); }\n}\n')), "scan"),
    ("agent does not refine the approved spec", write(APP, "module App {\n  method Search(name: string) returns (sql: string) { sql := \"\"; }\n}\n"), "scan"),
    ("approved but broken encoder (quotes not doubled)", seq(edit("lib/SqlSpec.dfy", "(if s[0] == '\\'' then \"''\" else [s[0]])", "[s[0]]"), propose), "verify"),
    ("cmdline: approved but broken escaping (backslash not escaped)", seq(edit("examples/cmdline/spec/CmdLang.dfy", "s[0] == '\"' || s[0] == '\\\\'", "s[0] == '\"'"), propose), "verify", "examples/cmdline/gate.toml"),
    ("cmdline: agent concatenates strings", write("examples/cmdline/src/CmdApp.dfy", 'include "../spec/CmdAppSpec.dfy"\nmodule CmdApp refines CmdAppSpec {\n  method Store(note: L.Data) returns (script: string) {\n    script := "put \\"note\\" \\"" + note + "\\"; get \\"note\\"";\n  }\n}\n'), "verify", "examples/cmdline/gate.toml"),
    ("cmdline: agent leaves the proof unfinished (stub)", write("examples/cmdline/src/CmdProof.dfy", 'include "../spec/CmdTheorem.dfy"\nmodule CmdProof refines CmdTheorem {\n  lemma RoundTrip(t: Tree) {}\n}\n'), "verify", "examples/cmdline/gate.toml"),
]


def run_gate(root, project="examples/userdir/gate.toml"):
    env = dict(os.environ, GATE_ALLOW_PROPOSED="1")
    r = subprocess.run([sys.executable, "-I", str(root / "tools/gate/gate.py"), "check",
                        str(root / project), "--json", "--skip-tests"],
                       capture_output=True, text=True, env=env, cwd=root)
    try:
        return json.loads(r.stdout.splitlines()[-1])
    except Exception:
        return {"ok": False, "steps": [{"step": "gate crashed", "ok": False, "details": [r.stdout[-300:], r.stderr[-300:]]}]}


def main():
    bad, rows = 0, []
    # baseline must pass, otherwise the scenarios prove nothing
    with tempfile.TemporaryDirectory() as t:
        root = Path(t) / "repo"
        shutil.copytree(ROOT, root, ignore=IGNORE)
        propose(root)
        base = run_gate(root)
        rows.append(("baseline (unmodified)", "pass", "pass" if base["ok"] else "FAIL", base["ok"]))
        if not base["ok"]:
            print(json.dumps(base, indent=1)); sys.exit("baseline does not pass; mutation results would be meaningless")
    for name, mutate, expected, *proj in SCENARIOS:
        t0 = time.time()
        with tempfile.TemporaryDirectory() as t:
            root = Path(t) / "repo"
            shutil.copytree(ROOT, root, ignore=IGNORE)
            propose(root)                       # start from an internally consistent manifest
            mutate(root)
            res = run_gate(root, *proj)
        failed = [s["step"].split(":")[0] for s in res["steps"] if not s["ok"]]
        ok = (not res["ok"]) and bool(failed) and failed[0] == expected
        rows.append((name, f"reject at {expected}", ("rejected at " + failed[0]) if failed else "ACCEPTED", ok))
        print(f"{'ok ' if ok else 'BAD'} {name:55s} expected {expected:9s} got {failed[:1] or 'ACCEPTED'}  ({time.time() - t0:.0f}s)", flush=True)
        bad += not ok
    print(f"\n{len(rows) - bad}/{len(rows)} scenarios behaved as expected (including the baseline)")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
