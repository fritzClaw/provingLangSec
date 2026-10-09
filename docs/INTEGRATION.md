# Using the gate in another project

The pieces are independent of the `userdir` example. A project needs: a **language definition** for each language its program emits to an interpreter, an **application specification**, a **`gate.toml`**, and the **hooks**. An agent then writes the implementation and the proofs, and the gate decides.

## 1. A language that already has a definition (SQL)

1. Copy `spec/` and `lib/` (or reference them as a submodule) and the `tools/` directory.
2. Write the application specification: an abstract Dafny module that imports `Sql` and states what the program's output must equal, as in `examples/userdir/spec/UserdirSpec.dfy`. Write a `READING.md` beside it in plain English.
3. Write `gate.toml` (copy `examples/userdir/gate.toml`): the agent's file and directory, the module it must refine, the build entry, and the tests.
4. Write glue and tests (frozen): the tests must include functional cases and exploits.
5. Add the paths to `DEFAULT_ROOTS` in `tools/gate/approve.py`, run `python3 -I tools/gate/approve.py propose`, review, and run `make approve`.
6. Point the agent at `INTENT.md` for the project. `CLAUDE.md` / `AGENTS.md` carry the rules; `.claude/settings.json` wires the hooks for Claude Code. For other agents, the gate CLI is the only interface: run it, read the failure, fix, repeat.

## 2. A new output language (including custom ones)

Follow `examples/cmdline/` (a command language with backslash escaping, a different style from SQL):

1. Write the definition as an abstract module that `refines LanguageSpec` (`spec/LanguageSpec.dfy`): the tree type, `Unparse`, and a strict `Parse` that models the receiver. Data fields must be the only place free text can go.
2. Write a `READING.md`. Get it approved.
3. Write the proof in a module that refines the definition and gives `RoundTrip` its body.
4. Test the model against the real receiver. For a custom interpreter that you control, make the interpreter use the verified parser (compile it from the same definition), and the gap disappears.

## What stays your job

- Approve the definitions and specifications: they are the only place a human decides what "secure" means.
- Keep the trusted list in `docs/TCB.md` true for your project.
