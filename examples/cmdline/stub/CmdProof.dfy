// Starting point of every `make agent` run: the agent replaces this file.
include "../spec/CmdTheorem.dfy"

module CmdProof refines CmdTheorem {
  lemma RoundTrip(t: Tree)
  {
  }
}
