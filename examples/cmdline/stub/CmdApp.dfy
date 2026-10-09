// Starting point of every `make agent` run: the agent replaces this file.
include "../spec/CmdAppSpec.dfy"

module CmdApp refines CmdAppSpec {
  method Store(note: L.Data) returns (script: string)
  {
    script := "";
  }
}
