# provingLangSec

AI agents write code **and** a machine-checked proof that it cannot be injected into. A deterministic checker, the *gate*, decides. Based on the LangSec work of Hermerschmidt et al.: injection happens when a program emits text in a formal language and the receiver parses data as structure. We prove the opposite for the program's output: **the receiver reads exactly the tree the program built**, whatever the data contains.

Status: research prototype. See "Implementation status" in `INTENT.md` for what was run and what was not. The project description, all design decisions and their reasons are in [`INTENT.md`](INTENT.md). What is proven, assumed and only tested is in [`docs/TCB.md`](docs/TCB.md).

## Try it

Open the folder in VS Code and choose **Reopen in Container** (Dev Containers extension; works on x86_64 and Apple Silicon). Then:

```sh
make demo
```

It runs offline in about a minute and shows, in order: the gate **accepts** the verified `userdir` app; the gate **rejects** the string-concatenating variant because its proof cannot be completed; the same `UNION` exploit **leaks the secrets** from the vulnerable variant and **returns nothing** from the verified one; and SQLite's own tokenizer and parse tree agree with the proven model.

| Command | What it does |
|---|---|
| `make demo` | the demonstration above |
| `make verify` | the gate on the verified example |
| `make fidelity` | does SQLite read our SQL as the model says? |
| `make test` / `make mutation-test` | gate unit tests / the gate must reject 14 broken or cheating submissions |
| `make agent` | Claude Code re-implements the example in a fresh copy; the gate decides (needs your login or `ANTHROPIC_API_KEY`) |
| `make approve` | owner only: review and approve the frozen files |

The frozen files (theorem statements, SQL layer, glue, tests, tooling) are hash-pinned in `gate/manifest.json`. Until you run `make approve` they are *proposed*, and the gate needs `--allow-proposed`.

## Layout

| Path | Content |
|---|---|
| `spec/` | the theorem template every output language must satisfy |
| `lib/` | the SQL language definition (`SqlSpec`) and its proof (`SqlProof`) |
| `examples/userdir/` | intent, approved specification, verified and vulnerable implementations, glue, tests |
| `tools/gate/` | the gate, approval tool, Claude Code hooks, mutation tests |
| `tools/agent/` | `make agent` harness |
| `tools/fidelity/` | SQLite debug oracle and the fidelity harness |
| `docs/` | literature review, parser-fidelity analysis, trusted base, integration guide |
| `spikes/` | the Dafny vs F\* experiment |

To use the approach in another project or for another output language, see [`docs/INTEGRATION.md`](docs/INTEGRATION.md).

## License

Apache-2.0.
