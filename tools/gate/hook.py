#!/usr/bin/env python3
"""Claude Code hooks for agent runs inside the DevContainer (configured in .claude/settings.json).

    hook.py pretool   PreToolUse: refuse writes to frozen files and to the manifest
    hook.py stop      Stop: run the gate; while it fails, send the failure back to the agent
                      (at most GATE_MAX_ATTEMPTS times), so the agent cannot stop with unproven code

They are active only when GATE_AGENT_RUN=1, which `make agent` sets.
These hooks help the agent; they are not the security boundary. The gate's manifest check
catches any change to a frozen file however it was made, including through the shell.
Exit code 2 tells Claude Code to block the action and show stderr to the agent.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate  # noqa: E402

ROOT = gate.ROOT
STATE = ROOT / ".gate-state"
WRITE_VERBS = re.compile(r"(>>?|\bsed\s+-i|\btee\b|\brm\b|\bmv\b|\bcp\b|\btruncate\b|\bchmod\b|\bgit\s+(checkout|restore|stash|apply)\b)")


def frozen_roots():
    try:
        return gate.load_manifest()["frozen_roots"]
    except Exception:
        return []


def is_frozen(path: str) -> bool:
    try:
        p = (Path(path) if os.path.isabs(path) else ROOT / path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return False
    return p == "gate/manifest.json" or any(p == r or p.startswith(r.rstrip("/") + "/") for r in frozen_roots())


def pretool(event):
    tool, inp = event.get("tool_name", ""), event.get("tool_input", {})
    path = inp.get("file_path") or inp.get("notebook_path")
    if path and is_frozen(path):
        print(f"BLOCKED: {path} is frozen (approved specification, tests, glue or tooling). "
              "Change only the files in the agent's directories; ask the owner to change frozen files.", file=sys.stderr)
        return 2
    if tool == "Bash":
        cmd = inp.get("command", "")
        if "approve.py" in cmd and re.search(r"approve\.py\s+(approve|propose)", cmd):
            print("BLOCKED: only the owner may approve or propose frozen files.", file=sys.stderr)
            return 2
        for root in frozen_roots() + ["gate/manifest.json"]:
            if root in cmd and WRITE_VERBS.search(cmd):
                print(f"BLOCKED: the command appears to modify frozen path {root}.", file=sys.stderr)
                return 2
    return 0


def stop(event):
    project = os.environ.get("GATE_PROJECT", "examples/userdir/gate.toml")
    max_attempts = int(os.environ.get("GATE_MAX_ATTEMPTS", "5"))
    STATE.mkdir(exist_ok=True)
    f = STATE / "attempts.json"
    attempts = json.loads(f.read_text())["attempts"] if f.exists() else 0
    cmd = [sys.executable, "-I", str(ROOT / "tools/gate/gate.py"), "check", project, "--json"]
    if os.environ.get("GATE_ALLOW_PROPOSED") == "1":
        cmd.append("--allow-proposed")
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    try:
        result = json.loads(r.stdout.splitlines()[-1])
    except Exception:
        result = {"ok": False, "steps": [{"step": "gate", "ok": False, "details": [r.stdout[-500:], r.stderr[-500:]]}]}
    attempts += 1
    f.write_text(json.dumps({"attempts": attempts, "last_ok": result["ok"]}))
    if result["ok"]:
        return 0
    lines = []
    for s in result["steps"]:
        lines.append(f"[{'PASS' if s['ok'] else 'FAIL'}] {s['step']}")
        if not s["ok"]:
            lines += [f"    {d}" for d in s["details"][:25]]
    if attempts >= max_attempts:
        (STATE / "gave_up").write_text("\n".join(lines))
        return 0
    print(f"The gate rejected your work (attempt {attempts} of {max_attempts}). Fix the failure and try again.\n"
          + "\n".join(lines), file=sys.stderr)
    return 2


if __name__ == "__main__":
    # The hooks guard agent runs only (tools/agent/run_agent.py sets GATE_AGENT_RUN=1).
    # They must not obstruct the owner or the people who develop the framework.
    if os.environ.get("GATE_AGENT_RUN") != "1":
        sys.exit(0)
    event = {}
    try:
        event = json.load(sys.stdin)
    except Exception:
        pass
    sys.exit({"pretool": pretool, "stop": stop}[sys.argv[1]](event))
