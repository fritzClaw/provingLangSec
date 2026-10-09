// The custom command language: syntax tree, unparser, model of the receiver's parser.
// Frozen: changes require owner approval. The proof is in the agent's CmdProof.dfy.
//
//   script  ::= command ("; " command)*
//   command ::= word (" " "\"" argument "\"")*
//   argument: backslash escapes the next character:  \"  is a quote,  \\  is a backslash
// Untrusted data can only enter as an argument (requirement R3).

include "../../../spec/Prelude.dfy"

module CmdLang {
  import opened Prelude

  predicate NoNul(s: string) { forall i :: 0 <= i < |s| ==> s[i] != '\0' }
  type Data = s: string | NoNul(s) witness ""
  predicate WordChar(c: char) { ('a' <= c <= 'z') || c == '_' }
  predicate IsWord(s: string) { |s| > 0 && forall i :: 0 <= i < |s| ==> WordChar(s[i]) }
  type Word = s: string | IsWord(s) witness "a"

  datatype Cmd = Cmd(name: Word, args: seq<Data>)
  type Script = cs: seq<Cmd> | |cs| > 0 witness [Cmd("a", [])]

  // ------------------------------------------------------------------ unparser
  // Encoder for the data token of an argument: backslash before every quote and backslash.
  function Esc(s: string): string {
    if |s| == 0 then ""
    else (if s[0] == '"' || s[0] == '\\' then ['\\', s[0]] else [s[0]]) + Esc(s[1..])
  }
  function UnArg(a: Data): string { "\"" + (Esc(a) + "\"") }
  function UnArgs(args: seq<Data>): string {
    if |args| == 0 then "" else " " + (UnArg(args[0]) + UnArgs(args[1..]))
  }
  function UnCmd(c: Cmd): string { c.name + UnArgs(c.args) }
  function UnScript(cs: seq<Cmd>): string requires |cs| > 0 {
    if |cs| == 1 then UnCmd(cs[0]) else UnCmd(cs[0]) + ("; " + UnScript(cs[1..]))
  }
  function Unparse(s: Script): string { UnScript(s) }

  // ------------------------------------------- model of the receiver's parser
  // Body of an argument (after the opening quote): decoded text and the input after the closing quote.
  function ArgBody(s: string): (r: Option<(string, string)>)
    ensures r.Some? ==> |r.value.1| < |s|
    decreases |s|
  {
    if |s| == 0 then None
    else if s[0] == '"' then Some(("", s[1..]))
    else if s[0] == '\\' then
      if |s| >= 2 && (s[1] == '"' || s[1] == '\\') then
        match ArgBody(s[2..])
        case None => None
        case Some(p) => Some(([s[1]] + p.0, p.1))
      else None
    else
      match ArgBody(s[1..])
      case None => None
      case Some(p) => Some(([s[0]] + p.0, p.1))
  }

  function ParseArgs(s: string): (r: Option<(seq<Data>, string)>)
    ensures r.Some? ==> |r.value.1| <= |s|
    decreases |s|
  {
    if |s| >= 2 && s[0] == ' ' && s[1] == '"' then
      match ArgBody(s[2..])
      case None => None
      case Some(p) =>
        if NoNul(p.0) then
          var d: Data := p.0;
          match ParseArgs(p.1)
          case None => None
          case Some(more) =>
            var all: seq<Data> := [d] + more.0;
            Some((all, more.1))
        else None
    else Some(([], s))
  }

  function SpanWord(s: string): (r: (string, string))
    ensures r.0 + r.1 == s
    ensures forall i :: 0 <= i < |r.0| ==> WordChar(r.0[i])
    decreases |s|
  {
    if |s| > 0 && WordChar(s[0]) then
      var p := SpanWord(s[1..]);
      ([s[0]] + p.0, p.1)
    else ("", s)
  }

  function ParseCmd(s: string): (r: Option<(Cmd, string)>)
    ensures r.Some? ==> |r.value.1| < |s|
  {
    var w := SpanWord(s);
    if IsWord(w.0) then
      var name: Word := w.0;
      match ParseArgs(w.1)
      case None => None
      case Some(pa) => Some((Cmd(name, pa.0), pa.1))
    else None
  }

  function ParseScript(s: string): (r: Option<(seq<Cmd>, string)>)
    ensures r.Some? ==> |r.value.0| > 0 && |r.value.1| < |s|
    decreases |s|
  {
    match ParseCmd(s)
    case None => None
    case Some(pc) =>
      match Strip("; ", pc.1)
      case None => Some(([pc.0], pc.1))
      case Some(u) =>
        match ParseScript(u)
        case None => None
        case Some(more) => Some(([pc.0] + more.0, more.1))
  }

  function Parse(s: string): Option<Script> {
    match ParseScript(s)
    case Some(p) =>
      if |p.1| == 0 then
        var sc: Script := p.0;
        Some(sc)
      else None
    case None => None
  }
}
