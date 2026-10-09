// Theorem template for output languages. Frozen: changes require owner approval.
//
// A language definition refines this module. It defines the syntax tree (Tree),
// the unparser (Unparse), and a model of the receiver's parser (Parse). The
// definition is reviewed and approved by the owner. The proof of RoundTrip is
// then written in a separate module that refines the definition; Dafny does
// not allow a refining module to change any function body, so the proof cannot
// weaken the definition.
//
// RoundTrip is the extended (un)parse round-trip of Hermerschmidt et al. (2015):
// it must hold for EVERY tree, including trees whose data tokens contain
// arbitrary strings. Then the receiver reads exactly the tree that was sent.

include "Prelude.dfy"

abstract module LanguageSpec {
  import opened Prelude

  type Tree
  function Unparse(t: Tree): string
  function Parse(s: string): Option<Tree>

  lemma RoundTrip(t: Tree)
    ensures Parse(Unparse(t)) == Some(t)
}
