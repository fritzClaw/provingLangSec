#!/usr/bin/env python3
"""Run Claude Code headless on a project and let the gate decide (`make agent`).

    run_agent.py [--project examples/userdir/gate.toml] [--runs N] [--attempts 5]
                 [--timeout-min 30] [--max-budget-usd 5] [--claude-bin claude] [--model M]

Each run happens in a fresh copy of the repository under runs/<timestamp>-<n>/work, where
the agent's file is reset to the project's stub. Nothing in the original tree changes. The
run directory keeps the transcript, the gate's verdict and result.json (time, cost, attempts).
A passing implementation is copied to runs/<timestamp>-<n>/<file>.

The 30-minute limit is a hard stop against runaway runs, not an expectation: the result
files record the real durations.
"""
import argparse
import datetime
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "gate"))
import gate  # noqa: E402

IGNORE = shutil.ignore_patterns(".git", "build", "runs", "__pycache__", ".gate-state")
TOOLS = "Read,Write,Edit,MultiEdit,Glob,Grep,Bash(python3 -I tools/gate/gate.py:*),Bash(dafny:*),Bash(ls:*),Bash(cat:*),Bash(make:*)"


def build_prompt(project: str, proj: dict, attempts: int) -> str:
    agent_files = ", ".join(f"`{f}`" for f in proj["agent"]["files"])
    return (ROOT / "tools/agent/prompt.md").read_text().format(
        project_dir=str(Path(project).parent), agent_files=agent_files, agent_dir=proj["agent"]["dirs"][0],
        project=project, attempts=attempts)


def parse_transcript(path: Path) -> dict:
    info = {}
    if path.exists():
        for line in path.read_text(errors="replace").splitlines():
            try:
                msg = json.loads(line)
            except Exception:
                continue
            if msg.get("type") == "result":
                info = {k: msg.get(k) for k in ("subtype", "is_error", "duration_ms", "num_turns", "total_cost_usd")}
    return info


def one_run(a, idx: int, stamp: str) -> dict:
    cfg = (ROOT / a.project).resolve()
    proj = tomllib.loads(cfg.read_text())
    run_dir = ROOT / "runs" / f"{stamp}-{idx}"
    work = run_dir / "work"
    shutil.copytree(ROOT, work, ignore=IGNORE)
    for f in proj["agent"]["files"]:
        stub = work / Path(a.project).parent / "stub" / Path(f).name
        shutil.copyfile(stub, work / f)
    env = dict(os.environ, GATE_AGENT_RUN="1", GATE_PROJECT=a.project, GATE_MAX_ATTEMPTS=str(a.attempts))
    if a.allow_proposed:
        env["GATE_ALLOW_PROPOSED"] = "1"
    prompt = build_prompt(a.project, proj, a.attempts)
    cmd = [a.claude_bin, "-p", prompt, "--output-format", "stream-json", "--verbose",
           "--permission-mode", "acceptEdits", "--permission-prompts", "none", "--allowedTools", TOOLS,
           "--max-budget-usd", str(a.max_budget_usd)]
    if a.model:
        cmd += ["--model", a.model]
    t0, timed_out = time.time(), False
    with open(run_dir / "transcript.jsonl", "w") as out, open(run_dir / "stderr.txt", "w") as err:
        try:
            subprocess.run(cmd, cwd=work, env=env, stdout=out, stderr=err, timeout=a.timeout_min * 60)
        except subprocess.TimeoutExpired:
            timed_out = True
    wall = time.time() - t0
    # The verdict is always a fresh, independent gate run in the work copy.
    gcmd = [sys.executable, "-I", str(work / "tools/gate/gate.py"), "check", a.project, "--json"]
    if a.allow_proposed:
        gcmd.append("--allow-proposed")
    g = subprocess.run(gcmd, cwd=work, env=dict(os.environ), capture_output=True, text=True)
    try:
        verdict = json.loads(g.stdout.splitlines()[-1])
    except Exception:
        verdict = {"ok": False, "steps": [{"step": "gate crashed", "ok": False, "details": [g.stdout[-300:], g.stderr[-300:]]}]}
    (run_dir / "gate.json").write_text(json.dumps(verdict, indent=1))
    state = work / ".gate-state" / "attempts.json"
    attempts = json.loads(state.read_text())["attempts"] if state.exists() else 0
    info = parse_transcript(run_dir / "transcript.jsonl")
    result = {"run": f"{stamp}-{idx}", "passed": bool(verdict["ok"]), "timed_out": timed_out,
              "wall_seconds": round(wall, 1), "gate_checked_attempts": attempts,
              "cost_usd": info.get("total_cost_usd"), "turns": info.get("num_turns"),
              "failed_steps": [s["step"] for s in verdict["steps"] if not s["ok"]]}
    if verdict["ok"]:
        for f in proj["agent"]["files"]:
            shutil.copyfile(work / f, run_dir / Path(f).name)
    (run_dir / "result.json").write_text(json.dumps(result, indent=1))
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default="examples/userdir/gate.toml")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--attempts", type=int, default=5)
    ap.add_argument("--timeout-min", type=float, default=30)
    ap.add_argument("--max-budget-usd", type=float, default=5)
    ap.add_argument("--claude-bin", default=os.environ.get("CLAUDE_BIN", "claude"))
    ap.add_argument("--model")
    ap.add_argument("--allow-proposed", action="store_true", default=os.environ.get("GATE_ALLOW_PROPOSED") == "1")
    a = ap.parse_args()
    if shutil.which(a.claude_bin) is None and not Path(a.claude_bin).exists():
        sys.exit(f"{a.claude_bin}: not found. Install Claude Code (the DevContainer does) and log in, or set ANTHROPIC_API_KEY.")
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    results = []
    for i in range(1, a.runs + 1):
        r = one_run(a, i, stamp)
        results.append(r)
        print(f"run {i}/{a.runs}: {'PASS' if r['passed'] else 'FAIL'}  {r['wall_seconds']}s  "
              f"attempts={r['gate_checked_attempts']}  cost={r['cost_usd']}  failed={r['failed_steps']}", flush=True)
    passed = [r for r in results if r["passed"]]
    summary = {"runs": len(results), "passed": len(passed), "success_rate": len(passed) / len(results),
               "median_wall_seconds": statistics.median(r["wall_seconds"] for r in results),
               "total_cost_usd": sum(r["cost_usd"] or 0 for r in results), "results": results}
    (ROOT / "runs").mkdir(exist_ok=True)
    (ROOT / "runs" / f"{stamp}-summary.json").write_text(json.dumps(summary, indent=1))
    print(f"\n{summary['passed']}/{summary['runs']} runs passed the gate; "
          f"median {summary['median_wall_seconds']}s; cost ${summary['total_cost_usd']:.2f}")
    sys.exit(0 if len(passed) == len(results) else 1)


if __name__ == "__main__":
    main()
