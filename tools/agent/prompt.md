You are implementing one Dafny file for a project whose security property is proven by a deterministic checker, the "gate". You do not decide whether your work is acceptable. The gate does.

Read these, in this order:
1. `{project_dir}/INTENT.md`, the application intent in plain English.
2. `{project_dir}/spec/READING.md`, the plain-English reading of the approved specification.
3. Every `.dfy` file in `{project_dir}/spec/`: the approved specifications. Your modules must refine them and satisfy their postconditions.
4. If the project uses the SQL layer: `lib/SqlSpec.dfy` (syntax tree, unparser, parser model) and `lib/SqlProof.dfy` (the proof that parsing inverts unparsing). These are frozen.

Your task: write {agent_files} so that the gate passes. Edit only files inside `{agent_dir}`.

Check your work with:

    python3 -I tools/gate/gate.py check {project}

Rules, all enforced mechanically:
- Files outside `{agent_dir}` are frozen. A hook blocks writes to them, and the gate rejects any change.
- No `assume`, no `{{:axiom}}`, no `{{:verify false}}`, no `{{:extern}}`, no `decreases *`, and no lemma or method without a body.
- Your module must refine the approved specification module. You cannot change its signature, preconditions or postcondition.
- Do not build SQL text by concatenating strings with untrusted data. Build a syntax tree and call the verified unparser.

When the gate prints `GATE: PASS`, stop. If it fails, read the failure, fix it, and run it again. You have at most {attempts} gate-checked attempts.
