// The classic vulnerable implementation: string concatenation. Expected to FAIL verification.
include "../spec/CmdAppSpec.dfy"

module CmdApp refines CmdAppSpec {
  method Store(note: L.Data) returns (script: string)
  {
    script := "put \"note\" \"" + note + "\"; get \"note\"";
  }
}
