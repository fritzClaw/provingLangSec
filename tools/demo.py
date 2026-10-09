#!/usr/bin/env python3
"""`make demo`: the whole demonstration, offline and deterministic (no LLM, no network).

  1. unit tests of the gate
  2. the gate accepts the verified userdir app (manifest, scan, proof, audit, build, tests)
  3. the gate REJECTS the vulnerable variant: its proof cannot be completed
  4. the exploit works against the vulnerable variant (compiled without proof) and fails against the verified one
  5. SQLite reads the emitted SQL the way the proven model says (fidelity harness)
  6. generality check: the same template proves a second, non-SQL language (a command language with
     backslash escaping and its own interpreter); the gate accepts it, rejects its vulnerable variant,
     and the injected `grant` command runs only in the vulnerable variant

Exit status 0 only if every step had the expected outcome.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "gate"))
import gate  # noqa: E402

PY = [sys.executable, "-I"]
EXPLOIT = "x') UNION SELECT secret, email FROM users --"
results = []


def run(cmd, **kw):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)


def record(title, ok, detail=""):
    results.append((title, ok))
    print(f"\n[{'PASS' if ok else 'FAIL'}] {title}")
    for line in detail.strip().splitlines():
        print("       " + line)


def main():
    manifest = gate.load_manifest()
    proposed = manifest["approval"]["status"] != "approved"
    flags = ["--allow-proposed"] if proposed else []
    if proposed:
        print("NOTICE: the frozen files (theorem statements, SQL layer, glue, tests, tooling) are PROPOSED, "
              "not yet approved by the owner.\n        The demo runs with --allow-proposed. Review them and run `make approve`.")

    r = run(PY + ["tools/gate/test_gate.py"])
    record("1. gate unit tests", r.returncode == 0, "\n".join(r.stderr.strip().splitlines()[-3:]))

    r = run(PY + ["tools/gate/gate.py", "check", "examples/userdir/gate.toml", *flags])
    record("2. gate ACCEPTS the verified app", r.returncode == 0, "\n".join(l for l in r.stdout.splitlines() if l.startswith(("[", "GATE", "       seed"))))

    r = run(PY + ["tools/gate/gate.py", "check", "examples/userdir/gate.vulnerable.toml", *flags])
    rejected = r.returncode == 1 and "postcondition could not be proved" in r.stdout
    record("3. gate REJECTS the vulnerable app (string concatenation)", rejected,
           "\n".join(l for l in r.stdout.splitlines() if "FAIL" in l or "Error" in l or l.startswith("GATE")))

    # 4. exploit demo
    b = run([gate.dafny_bin(), "build", "--target", "py", "examples/userdir/src/AppVulnerable.dfy", "--output", "build/vulnerable/app",
             "--no-verify", "--solver-path", gate.z3_bin()])
    glue = ["examples/userdir/glue/userdir.py"]
    with tempfile.TemporaryDirectory() as t:
        db = os.path.join(t, "users.db")
        outs = {}
        for name in ("vulnerable", "verified"):
            build = f"build/{name}/app-py"
            run(PY + glue + ["--build", build, "init", db])
            outs[name] = run(PY + glue + ["--build", build, "search", db, EXPLOIT])
    leaked = "S3CR3T" in outs["vulnerable"].stdout
    safe = outs["verified"].returncode == 0 and outs["verified"].stdout == ""
    record("4. exploit: leaks secrets from the vulnerable app, returns nothing from the verified app", b.returncode == 0 and leaked and safe,
           f"search {EXPLOIT!r}\n--- vulnerable app printed:\n{outs['vulnerable'].stdout.strip()}\n--- verified app printed: {outs['verified'].stdout!r}")

    if not (ROOT / "build/fidelity/oracle").exists():
        run(["sh", "tools/fidelity/build_oracle.sh"])
    r = run(PY + ["tools/fidelity/check_fidelity.py", "--trees", "2000", "--max-len", "4"])
    record("5. SQLite (debug oracle) reads the emitted SQL as the model says", r.returncode == 0, r.stdout.strip() or r.stderr.strip()[-400:])

    # 6. generality check: custom command language
    r = run(PY + ["tools/gate/gate.py", "check", "examples/cmdline/gate.toml", *flags])
    ok_gate = r.returncode == 0
    r2 = run(PY + ["tools/gate/gate.py", "check", "examples/cmdline/gate.vulnerable.toml", "--skip-tests", *flags])
    ok_rej = r2.returncode == 1 and "postcondition could not be proved" in r2.stdout
    b2 = run([gate.dafny_bin(), "build", "--target", "py", "examples/cmdline/src/CmdAppVulnerable.dfy", "--output",
              "build/cmdline-vulnerable/app", "--no-verify", "--solver-path", gate.z3_bin()])
    note = 'x"; grant "mallory'
    cg = ["examples/cmdline/glue/cmdline.py"]
    vul = run(PY + cg + ["--build", "build/cmdline-vulnerable/app-py", "run", note])
    ver = run(PY + cg + ["--build", "build/cmdline/app-py", "run", note])
    injected = "admins: ['mallory']" in vul.stdout
    stored = "admins: []" in ver.stdout and "get: " + note in ver.stdout
    record("6. generality check, command language: gate accepts the verified app, rejects the vulnerable one, and the injected command runs only in the vulnerable one",
           ok_gate and ok_rej and b2.returncode == 0 and injected and stored,
           f"gate on verified app: {'PASS' if ok_gate else 'FAIL'}; gate on vulnerable app: {'rejected' if ok_rej else 'NOT rejected'}\n"
           f"note {note!r}\n--- vulnerable app ran:\n{vul.stdout.strip()}\n--- verified app ran:\n{ver.stdout.strip()}")

    bad = [t for t, ok in results if not ok]
    print("\n" + "=" * 70)
    print("DEMO: " + ("ALL STEPS HAD THE EXPECTED OUTCOME" if not bad else f"{len(bad)} STEP(S) FAILED"))
    if proposed:
        print("(frozen files not yet approved by the owner: see NOTICE above)")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
