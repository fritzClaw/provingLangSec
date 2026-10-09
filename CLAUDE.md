# Instructions for AI agents working in this repository

The authoritative description of the project is `INTENT.md`. Read it first. The rules below apply to every agent.

## The rule

Code you write must pass the gate. The gate is deterministic; you do not decide whether your work is acceptable.

    python3 -I tools/gate/gate.py check <project>/gate.toml      # for example examples/userdir/gate.toml

## What you may edit

Only the files in the project's agent directory (for `userdir`: `examples/userdir/src/`). Everything else is frozen: specifications, the SQL layer, the glue, the tests, the tooling, the manifest. A hook blocks writes to frozen files, and the gate rejects any change to them. If a frozen file looks wrong, tell the owner; do not work around it.

## What is forbidden in your Dafny code

`assume`, `{:axiom}`, `{:verify false}`, `{:extern}`, `decreases *`, lemmas or methods without a body, including files that are not in your directory or frozen. Build SQL only through the verified unparser (`Sql.Unparse`); never concatenate untrusted text into SQL.

## Adding a new project or language

See `docs/INTEGRATION.md`.
