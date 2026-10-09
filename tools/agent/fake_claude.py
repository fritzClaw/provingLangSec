#!/usr/bin/env python3
"""Stand-in for the `claude` CLI, used only to test run_agent.py and the hooks without an LLM.

FAKE_CLAUDE_MODE:
  solve   write the reference solution, then run the Stop hook once
  retry   first stop with the stub (hook must block), then write the solution (hook must pass)
  idle    do nothing (the gate must reject the untouched stub)
  cheat   try to edit a frozen file through the PreToolUse hook, then write an assume-based "solution"
FAKE_CLAUDE_REFERENCE: path of the reference App.dfy
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

mode = os.environ.get("FAKE_CLAUDE_MODE", "solve")
ref = Path(os.environ["FAKE_CLAUDE_REFERENCE"])
target = Path("examples/userdir/src/App.dfy")


def hook(name, event=None):
    return subprocess.run([sys.executable, "-I", "tools/gate/hook.py", name], input=json.dumps(event or {}),
                          capture_output=True, text=True, env=dict(os.environ)).returncode


if mode == "solve":
    shutil.copyfile(ref, target)
    hook("stop")
elif mode == "retry":
    assert hook("stop") == 2, "the Stop hook must block an unproven stub"
    shutil.copyfile(ref, target)
    assert hook("stop") == 0
elif mode == "cheat":
    blocked = hook("pretool", {"tool_name": "Write", "tool_input": {"file_path": os.path.abspath("examples/userdir/spec/UserdirSpec.dfy")}})
    assert blocked == 2, "the PreToolUse hook must block writes to frozen files"
    target.write_text(target.read_text().replace("sql := \"\";", "sql := \"\"; assume sql == Sql.Unparse(Intended(name));"))
    hook("stop")
print(json.dumps({"type": "result", "subtype": "success", "is_error": False, "duration_ms": 1, "num_turns": 1, "total_cost_usd": 0.0}))
