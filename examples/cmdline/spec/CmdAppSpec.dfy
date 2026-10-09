// Approved specification of the application's script. Frozen.
//
// Reading in plain English: whatever script text Store returns is EXACTLY the text of the
// script `put "note" "<note>"; get "note"`, where the untrusted note appears only as the
// content of put's second argument. The command names and the key are fixed.
include "CmdLang.dfy"

abstract module CmdAppSpec {
  import L = CmdLang

  function Intended(note: L.Data): L.Script {
    [L.Cmd("put", ["note", note]), L.Cmd("get", ["note"])]
  }

  method Store(note: L.Data) returns (script: string)
    ensures script == L.Unparse(Intended(note))
}
