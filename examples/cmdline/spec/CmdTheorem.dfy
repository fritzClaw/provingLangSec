// The theorem the agent must prove for the command language. Frozen.
include "../../../spec/LanguageSpec.dfy"
include "CmdLang.dfy"

abstract module CmdTheorem refines LanguageSpec {
  import L = CmdLang
  type Tree = L.Script
  function Unparse(t: Tree): string { L.Unparse(t) }
  function Parse(s: string): Option<Tree> { L.Parse(s) }
}
