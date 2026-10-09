// Verified implementation of the application's script (reference solution).
include "../spec/CmdAppSpec.dfy"

module CmdApp refines CmdAppSpec {
  method Store(note: L.Data) returns (script: string)
  {
    script := L.Unparse(Intended(note));
  }
}
