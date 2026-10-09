#!/usr/bin/env python3
"""The gate: a deterministic checker that decides whether agent-written code is acceptable.

    gate.py check PROJECT.toml [--seeds N] [--allow-proposed] [--skip-tests] [--json]
    gate.py scan FILE...            # only the forbidden-construct scan

A project passes only if ALL of these hold, in this order:
  1. environment: the pinned Dafny and Z3 versions are in use;
  2. manifest:    every frozen file (specifications, SQL layer, glue, tests, tooling)
                  matches the hash recorded in gate/manifest.json, no unlisted file
                  sits inside a frozen directory, and the manifest is owner-approved
                  (unless --allow-proposed);
  3. scan:        the agent's files, and everything they include, contain no construct
                  that skips a proof (assume, {:axiom}, {:verify}, {:extern}, ...);
  4. verify:      Dafny verifies the agent's files and all included files with pinned
                  settings and an explicit random seed, for each requested seed;
  5. audit:       `dafny audit` reports 0 findings;
  6. tests:       the project's functional and exploit tests pass on the built code.

The gate fails closed: anything unexpected is a failure.
"""
import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "gate" / "manifest.json"
VERSIONS = ROOT / "tools" / "versions.env"
IGNORED = ("__pycache__", ".pyc", ".DS_Store")


# ----------------------------------------------------------------------------- helpers
def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_versions() -> dict:
    out = {}
    for line in VERSIONS.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def frozen_files(roots: list) -> list:
    """All files under the frozen roots (a root may be a file or a directory)."""
    found = []
    for r in roots:
        p = ROOT / r
        if p.is_file():
            found.append(rel(p))
        elif p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and not any(x in f.as_posix() for x in IGNORED):
                    found.append(rel(f))
    return sorted(set(found))


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text())


class Report:
    def __init__(self):
        self.steps = []

    def add(self, name, ok, details=()):
        self.steps.append({"step": name, "ok": ok, "details": list(details)})
        return ok

    @property
    def ok(self):
        return all(s["ok"] for s in self.steps)

    def render(self):
        lines = []
        for s in self.steps:
            lines.append(f"[{'PASS' if s['ok'] else 'FAIL'}] {s['step']}")
            lines += [f"       {d}" for d in s["details"][:40]]
            if len(s["details"]) > 40:
                lines.append(f"       ... {len(s['details']) - 40} more")
        lines.append("GATE: " + ("PASS" if self.ok else "FAIL"))
        return "\n".join(lines)


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)


# ------------------------------------------------------------------------ 1. environment
def dafny_bin():
    return os.environ.get("GATE_DAFNY", "dafny")


def z3_bin():
    return os.environ.get("GATE_Z3", "z3")


def check_environment(rep: Report):
    v = load_versions()
    problems = []
    try:
        d = run([dafny_bin(), "--version"])
        if d.returncode != 0 or not d.stdout.strip().startswith(v["DAFNY_VERSION"]):
            problems.append(f"Dafny {v['DAFNY_VERSION']} required, found: {d.stdout.strip() or d.stderr.strip()!r}")
    except FileNotFoundError:
        problems.append(f"dafny not found ({dafny_bin()})")
    try:
        z = run([z3_bin(), "--version"])
        if z.returncode != 0 or f"Z3 version {v['Z3_VERSION']} " not in z.stdout:
            problems.append(f"Z3 {v['Z3_VERSION']} required, found: {z.stdout.strip()!r}")
    except FileNotFoundError:
        problems.append(f"z3 not found ({z3_bin()})")
    return rep.add(f"environment: Dafny {v['DAFNY_VERSION']}, Z3 {v['Z3_VERSION']}", not problems, problems)


# ---------------------------------------------------------------------------- 2. manifest
def check_manifest(rep: Report, allow_proposed: bool):
    if not MANIFEST.exists():
        return rep.add("manifest", False, ["gate/manifest.json is missing"])
    m = load_manifest()
    problems = []
    listed = m["files"]
    for path, digest in listed.items():
        p = ROOT / path
        if not p.is_file():
            problems.append(f"frozen file missing: {path}")
        elif sha256(p) != digest:
            problems.append(f"frozen file changed: {path}")
    for path in frozen_files(m["frozen_roots"]):
        if path not in listed:
            problems.append(f"unlisted file inside a frozen directory: {path}")
    status = m["approval"]["status"]
    if status != "approved":
        msg = f"manifest status is '{status}': the frozen files are not approved by the owner"
        if allow_proposed:
            print(f"WARNING: {msg} (continuing because --allow-proposed was given)", file=sys.stderr)
        else:
            problems.append(msg + " (run `make approve`)")
    return rep.add(f"manifest: {len(listed)} frozen files unchanged, approval '{status}'", not problems, problems)


# ------------------------------------------------------------------------------- 3. scan
class ScanError(Exception):
    pass


CHAR_LIT = re.compile(r"'(?:\\u\{[0-9a-fA-F]+\}|\\U\{[0-9a-fA-F]+\}|\\u[0-9a-fA-F]{4}|\\.|[^\\'\n])'")


def strip_dafny(src: str, keep_strings: bool = False) -> str:
    """Blank out comments (and string/char literals unless keep_strings) so that the
    scan sees only code. Raises ScanError on anything it cannot tokenize."""
    out, i, n, depth = [], 0, len(src), 0
    blank = lambda s: re.sub(r"[^\n]", " ", s)
    while i < n:
        two = src[i:i + 2]
        c = src[i]
        if depth:
            if two == "/*":
                depth += 1; out.append("  "); i += 2
            elif two == "*/":
                depth -= 1; out.append("  "); i += 2
            else:
                out.append("\n" if c == "\n" else " "); i += 1
            continue
        if two == "//":
            j = src.find("\n", i); j = n if j < 0 else j
            out.append(" " * (j - i)); i = j
        elif two == "/*":
            depth = 1; out.append("  "); i += 2
        elif c == "@" and src[i + 1:i + 2] == '"':
            j = i + 2
            while True:
                j = src.find('"', j)
                if j < 0:
                    raise ScanError("unterminated verbatim string")
                if src[j + 1:j + 2] == '"':
                    j += 2; continue
                break
            seg = src[i:j + 1]
            out.append(seg if keep_strings else blank(seg)); i = j + 1
        elif c == '"':
            j = i + 1
            while j < n and src[j] != '"':
                j += 2 if src[j] == "\\" else 1
            if j >= n:
                raise ScanError("unterminated string literal")
            seg = src[i:j + 1]
            out.append(seg if keep_strings else blank(seg)); i = j + 1
        elif c == "'":
            prev = src[i - 1] if i else " "
            if prev.isalnum() or prev in "_'?":      # a prime inside an identifier, e.g. rest'
                out.append(c); i += 1
            else:
                m = CHAR_LIT.match(src, i)
                if not m:
                    raise ScanError(f"cannot tokenize quote at offset {i}")
                seg = m.group(0)
                out.append(seg if keep_strings else blank(seg)); i = m.end()
        else:
            out.append(c); i += 1
    if depth:
        raise ScanError("unterminated block comment")
    return "".join(out)


FORBIDDEN = [
    (re.compile(r"\bassume\b"), "assume statement"),
    (re.compile(r"\{\s*:\s*(axiom|verify|extern|synthesize|rlimit|resource_limit|timeLimit|timeLimitMultiplier|"
                r"vcs_\w+|selective_checking|nowarn|isolate_assertions)\b"), "attribute that skips or weakens a proof"),
    (re.compile(r"decreases\s*\*"), "decreases * (allows non-termination)"),
]
INCLUDE = re.compile(r'^\s*include\s+"([^"]+)"', re.M)


def scan_text(text: str, name: str) -> list:
    try:
        code = strip_dafny(text)
    except ScanError as e:
        return [f"{name}: cannot scan ({e})"]
    found = []
    for rx, what in FORBIDDEN:
        for m in rx.finditer(code):
            line = code.count("\n", 0, m.start()) + 1
            found.append(f"{name}:{line}: forbidden: {what}: {m.group(0).strip()}")
    return found


def includes_of(path: Path) -> list:
    code = strip_dafny(path.read_text(encoding="utf-8"), keep_strings=True)
    return [(path.parent / inc).resolve() for inc in INCLUDE.findall(code)]


def check_scan(rep: Report, proj: dict, manifest_files: set):
    agent_files = [(ROOT / f).resolve() for f in proj["agent"]["files"]]
    agent_dirs = [(ROOT / d).resolve() for d in proj["agent"]["dirs"]]
    problems, seen, todo = [], set(), list(agent_files)
    all_agent_text = ""
    while todo:
        f = todo.pop()
        if f in seen:
            continue
        seen.add(f)
        try:
            r = rel(f)
        except ValueError:
            problems.append(f"include escapes the repository: {f}")
            continue
        if not f.is_file():
            problems.append(f"missing file: {r}")
            continue
        in_agent = any(d == f.parent or d in f.parents for d in agent_dirs)
        if r in manifest_files:
            pass                                   # frozen library: hash-checked, not scanned for agent rules
        elif in_agent:
            text = f.read_text(encoding="utf-8")
            all_agent_text += strip_dafny(text) + "\n" if not scan_text(text, r) else ""
            problems += scan_text(text, r)
        else:
            problems.append(f"{r}: neither a frozen file nor inside the agent's directories {proj['agent']['dirs']}")
            continue
        try:
            todo += includes_of(f)
        except ScanError as e:
            problems.append(f"{r}: cannot scan includes ({e})")
    specs = proj["project"].get("spec_modules") or ([proj["project"]["spec_module"]] if proj["project"].get("spec_module") else [])
    if specs and not problems:
        for spec in specs:
            if not re.search(rf"\bmodule\s+\w+\s+refines\s+{re.escape(spec)}\b", all_agent_text):
                problems.append(f"no agent module refines {spec}")
    return rep.add(f"scan: {len(seen)} files reached from the agent's files", not problems, problems)


# ----------------------------------------------------------------------- 4/5. verify, audit
SUMMARY = re.compile(r"finished with (\d+) verified, (\d+) errors?(.*)$", re.M)


def dafny_args():
    v = load_versions()
    return ["--solver-path", z3_bin(), "--isolate-assertions", "--resource-limit", v["GATE_RESOURCE_LIMIT"],
            "--verification-time-limit", v["GATE_TIME_LIMIT"], "--verify-included-files"]


def check_verify(rep: Report, proj: dict, seeds: list):
    files = [str(ROOT / f) for f in proj["verify"]["files"]]
    ok_all, details = True, []
    for seed in seeds:
        r = run([dafny_bin(), "verify", *files, *dafny_args(), "--boogie", f"/randomSeed:{seed}"], cwd=ROOT)
        out = r.stdout + r.stderr
        m = SUMMARY.search(out)
        good = r.returncode == 0 and m and int(m.group(1)) > 0 and int(m.group(2)) == 0 and not m.group(3).strip()
        if good:
            details.append(f"seed {seed}: {m.group(1)} verified, 0 errors")
        else:
            ok_all = False
            details.append(f"seed {seed}: FAILED (exit {r.returncode})")
            details += [ln for ln in out.splitlines() if re.search(r"Error|Warning|out of resource|time out|inconclusive", ln)][:12]
            break
    return rep.add(f"verify: {len(seeds)} seed(s), resource limit {load_versions()['GATE_RESOURCE_LIMIT']}", ok_all, details)


def check_audit(rep: Report, proj: dict):
    files = [str(ROOT / f) for f in proj["verify"]["files"]]
    r = run([dafny_bin(), "audit", *files], cwd=ROOT)
    out = r.stdout + r.stderr
    m = re.search(r"auditor completed with (\d+) findings", out)
    good = r.returncode == 0 and m and int(m.group(1)) == 0
    details = [] if good else [ln for ln in out.splitlines() if "Warning" in ln or "Error" in ln][:12] or [out.strip()[-300:]]
    return rep.add("audit: dafny audit reports 0 findings", bool(good), details)


# ---------------------------------------------------------------------------- 6. tests
def check_build_and_tests(rep: Report, proj: dict):
    b = proj["build"]
    out_dir = ROOT / b["out"]
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    r = run([dafny_bin(), "build", "--target", "py", str(ROOT / b["entry"]), "--output", str(out_dir),
             "--no-verify", "--solver-path", z3_bin()], cwd=ROOT)
    if r.returncode != 0:
        return rep.add("build: compile verified code to Python", False, (r.stdout + r.stderr).splitlines()[-10:])
    rep.add("build: compile verified code to Python", True)
    ok_all, details = True, []
    for cmd in proj["tests"]["commands"]:
        t = run(shlex.split(cmd), cwd=ROOT)
        if t.returncode != 0:
            ok_all = False
            details.append(f"FAILED: {cmd}")
            details += (t.stdout + t.stderr).splitlines()[-25:]
            break
        details.append(f"ok: {cmd}")
    return rep.add("tests: functional and exploit tests", ok_all, details)


# ---------------------------------------------------------------------------------- main
def cmd_check(a):
    cfg = Path(a.project).resolve()
    proj = tomllib.loads(cfg.read_text())
    rep = Report()
    if check_environment(rep) and check_manifest(rep, a.allow_proposed):
        manifest_files = set(load_manifest()["files"])
        if check_scan(rep, proj, manifest_files):
            if check_verify(rep, proj, list(range(a.seeds))) and check_audit(rep, proj) and not a.skip_tests:
                check_build_and_tests(rep, proj)
    print(json.dumps({"ok": rep.ok, "steps": rep.steps}) if a.json else rep.render())
    return 0 if rep.ok else 1


def cmd_scan(a):
    problems = []
    for f in a.files:
        problems += scan_text(Path(f).read_text(encoding="utf-8"), f)
    print("\n".join(problems) if problems else "scan: clean")
    return 1 if problems else 0


def main(argv):
    ap = argparse.ArgumentParser(prog="gate")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("project", help="path to the project's gate.toml")
    c.add_argument("--seeds", type=int, default=1, help="verify with random seeds 0..N-1")
    c.add_argument("--allow-proposed", action="store_true",
                   default=os.environ.get("GATE_ALLOW_PROPOSED") == "1",
                   help="accept a manifest that is not yet approved by the owner (development only)")
    c.add_argument("--skip-tests", action="store_true")
    c.add_argument("--json", action="store_true")
    s = sub.add_parser("scan")
    s.add_argument("files", nargs="+")
    a = ap.parse_args(argv)
    return {"check": cmd_check, "scan": cmd_scan}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
