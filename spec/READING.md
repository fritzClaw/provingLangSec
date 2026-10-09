# Reading of the theorem template (`spec/LanguageSpec.dfy`, for owner approval)

**What every output language must prove.** A language definition supplies three things: a type of syntax trees (`Tree`), an unparser (`Unparse`: tree to text), and a model of the receiver's parser (`Parse`: text to tree, or failure). The theorem is

> for every tree `t`, `Parse(Unparse(t)) == Some(t)`.

"Every tree" includes trees whose data fields (string literals, names) hold arbitrary, attacker-chosen text. So whatever an attacker types, the receiver reads back exactly the tree the program built: the data never turns into structure. This is the extended round-trip of Hermerschmidt, Kugelmann and Rumpe (2015).

**How cheating is prevented.** The definition (tree type, `Unparse`, `Parse`) is written first and approved by you. The proof is written in a separate module that *refines* the definition. Dafny does not let a refining module change any function body, add preconditions, or change parameter types, so the proof can only prove the approved statement. The gate additionally rejects `assume`, `{:axiom}`, `{:extern}`, `{:verify false}` and `decreases *`, and `dafny audit` must report no findings.

**What it does not say.**
- That `Parse` matches the real receiver. A trivial definition (`Parse` = identity) would satisfy the theorem. That is why you approve the definition, and why `tools/fidelity` tests the model against the real receiver.
- That the program emits the right tree. That is the per-application specification (for example `examples/userdir/spec/UserdirSpec.dfy`).
