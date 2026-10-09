#!/usr/bin/env python3
"""Owner approval of the frozen files.

    approve.py status      show what changed since the manifest was written
    approve.py propose     recompute hashes and mark the manifest 'proposed' (no human step;
                           a proposed manifest is NOT accepted by the gate in strict mode)
    approve.py approve     interactive: show the changes and the plain-English readings,
                           then record the hashes with your name in a commit by you

Only `approve` produces an 'approved' manifest, and it refuses to run without a terminal,
so an agent cannot approve its own changes. The approval commit contains only
gate/manifest.json; the frozen files must already be committed.
"""
import datetime
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate  # noqa: E402

ROOT, MANIFEST = gate.ROOT, gate.MANIFEST

DEFAULT_ROOTS = [
    "Makefile", ".claude/settings.json", ".devcontainer", ".github", "spec", "lib", "tools",
    "examples/userdir/INTENT.md", "examples/userdir/gate.toml", "examples/userdir/gate.vulnerable.toml",
    "examples/userdir/spec", "examples/userdir/glue", "examples/userdir/tests", "examples/userdir/data", "examples/userdir/stub",
    "examples/cmdline/INTENT.md", "examples/cmdline/gate.toml", "examples/cmdline/gate.vulnerable.toml",
    "examples/cmdline/spec", "examples/cmdline/glue", "examples/cmdline/tests", "examples/cmdline/stub",
    "CLAUDE.md", "AGENTS.md",
]


def git(*args, check=True):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    if check and r.returncode != 0:
        sys.exit(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout


def current(roots):
    return {p: gate.sha256(ROOT / p) for p in gate.frozen_files(roots)}


def load():
    if MANIFEST.exists():
        return gate.load_manifest()
    return {"version": 1, "approval": {"status": "proposed", "approved_by": None, "approved_at": None},
            "frozen_roots": DEFAULT_ROOTS, "files": {}}


def changes(old, new):
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    changed = sorted(p for p in set(old) & set(new) if old[p] != new[p])
    return added, removed, changed


def write(m, status, by=None):
    m["approval"] = {"status": status, "approved_by": by,
                     "approved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds") if by else None}
    MANIFEST.parent.mkdir(exist_ok=True)
    MANIFEST.write_text(json.dumps(m, indent=2, sort_keys=True) + "\n")


def cmd_status(_):
    m = load()
    added, removed, changed = changes(m["files"], current(m["frozen_roots"]))
    print(f"approval status: {m['approval']['status']}"
          + (f" by {m['approval']['approved_by']} at {m['approval']['approved_at']}" if m["approval"]["approved_by"] else ""))
    for label, items in (("new", added), ("removed", removed), ("changed", changed)):
        for p in items:
            print(f"  {label}: {p}")
    if not (added or removed or changed):
        print("  frozen files match the manifest")
    return 0


def cmd_propose(_):
    m = load()
    m["frozen_roots"] = sorted(set(DEFAULT_ROOTS) | set(m["frozen_roots"]))
    m["files"] = current(m["frozen_roots"])
    write(m, "proposed")
    print(f"manifest written as 'proposed' with {len(m['files'])} frozen files")
    return 0


def cmd_approve(_):
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        sys.exit("approve needs an interactive terminal: it records a human decision.")
    m = load()
    new = current(m["frozen_roots"])
    added, removed, changed = changes(m["files"], new)
    dirty = [ln for ln in git("status", "--porcelain", "--", *m["frozen_roots"]).splitlines() if ln.strip()]
    if dirty:
        sys.exit("Commit the frozen files first, so the approved hashes match committed content:\n" + "\n".join(dirty))
    last = git("log", "-1", "--format=%H", "--", "gate/manifest.json").strip()
    print(f"== {len(added)} new, {len(changed)} changed, {len(removed)} removed frozen files\n")
    print("Frozen roots (everything under these paths is frozen):\n  " + "\n  ".join(m["frozen_roots"]) + "\n")
    if not (added or removed or changed) and m["approval"]["status"] == "approved":
        print("Nothing to approve."); return 0
    shown = set()
    for p in added + changed:
        print(f"---- {p}  [{'NEW' if p in added else 'CHANGED'}]")
        if p in added or not last:
            print("".join(f"    {ln}" for ln in (ROOT / p).read_text(errors='replace').splitlines(True)[:60]))
        else:
            print(git("diff", last, "--", p, check=False))
        reading = (ROOT / p).parent / "READING.md"
        if reading.exists() and reading not in shown and (p.endswith(".dfy") or "spec" in p):
            shown.add(reading)
            print(f"\n==== Plain-English reading ({reading.relative_to(ROOT)}):\n{reading.read_text()}")
    for p in removed:
        print(f"---- {p}  [REMOVED]")
    who = f"{git('config', 'user.name').strip()} <{git('config', 'user.email').strip()}>"
    print(f"\nYou are about to approve these frozen files as {who}.")
    if input("Type APPROVE to continue: ").strip() != "APPROVE":
        print("Not approved."); return 1
    m["files"] = new
    write(m, "approved", who)
    git("add", "gate/manifest.json")
    git("commit", "-m", f"Approve frozen files ({len(new)} files)", "--", "gate/manifest.json")
    print("Approved and committed.")
    return 0


if __name__ == "__main__":
    cmds = {"status": cmd_status, "propose": cmd_propose, "approve": cmd_approve}
    if len(sys.argv) != 2 or sys.argv[1] not in cmds:
        sys.exit(__doc__)
    sys.exit(cmds[sys.argv[1]](None))
