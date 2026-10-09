// Proof that parsing inverts unparsing for the command language (reference solution).
include "../spec/CmdTheorem.dfy"

module CmdProof refines CmdTheorem {
  predicate NotArgStart(rest: string) { !(|rest| >= 2 && rest[0] == ' ' && rest[1] == '"') }

  lemma ConcatRight(x: string, y: string, z: string)
    ensures (x + y) + z == x + (y + z)
  {
  }

  lemma ArgBodyRoundTrip(s: string, rest: string)
    ensures L.ArgBody(L.Esc(s) + ("\"" + rest)) == Some((s, rest))
    decreases |s|
  {
    var input := L.Esc(s) + ("\"" + rest);
    if |s| == 0 {
      assert input == "\"" + rest;
      assert input[1..] == rest;
    } else if s[0] == '"' || s[0] == '\\' {
      assert L.Esc(s) == ['\\', s[0]] + L.Esc(s[1..]);
      ConcatRight(['\\', s[0]], L.Esc(s[1..]), "\"" + rest);
      assert input[0] == '\\' && input[1] == s[0];
      assert input[2..] == L.Esc(s[1..]) + ("\"" + rest);
      ArgBodyRoundTrip(s[1..], rest);
      assert [s[0]] + s[1..] == s;
    } else {
      assert L.Esc(s) == [s[0]] + L.Esc(s[1..]);
      ConcatRight([s[0]], L.Esc(s[1..]), "\"" + rest);
      assert input[0] == s[0];
      assert input[1..] == L.Esc(s[1..]) + ("\"" + rest);
      ArgBodyRoundTrip(s[1..], rest);
      assert [s[0]] + s[1..] == s;
    }
  }

  lemma ArgsRoundTrip(args: seq<L.Data>, rest: string)
    requires NotArgStart(rest)
    ensures L.ParseArgs(L.UnArgs(args) + rest) == Some((args, rest))
    decreases |args|
  {
    if |args| == 0 {
      assert L.UnArgs(args) + rest == rest;
    } else {
      var a := args[0];
      var tail := args[1..];
      var rest2 := L.UnArgs(tail) + rest;
      var input := L.UnArgs(args) + rest;
      assert L.UnArgs(args) == " " + (L.UnArg(a) + L.UnArgs(tail));
      assert L.UnArg(a) == "\"" + (L.Esc(a) + "\"");
      assert input == " " + ("\"" + (L.Esc(a) + ("\"" + rest2)));
      assert input[0] == ' ' && input[1] == '"';
      assert input[2..] == L.Esc(a) + ("\"" + rest2);
      ArgBodyRoundTrip(a, rest2);
      ArgsRoundTrip(tail, rest);
      assert [a] + tail == args;
    }
  }

  lemma SpanWordAppend(w: string, rest: string)
    requires forall i :: 0 <= i < |w| ==> L.WordChar(w[i])
    requires |rest| == 0 || !L.WordChar(rest[0])
    ensures L.SpanWord(w + rest) == (w, rest)
    decreases |w|
  {
    if |w| == 0 {
      assert w + rest == rest;
    } else {
      assert (w + rest)[0] == w[0];
      assert (w + rest)[1..] == w[1..] + rest;
      assert forall i :: 0 <= i < |w[1..]| ==> L.WordChar(w[1..][i]);
      SpanWordAppend(w[1..], rest);
      assert [w[0]] + w[1..] == w;
    }
  }

  lemma CmdRoundTrip(c: L.Cmd, rest: string)
    requires |rest| == 0 || rest[0] == ';'
    ensures L.ParseCmd(L.UnCmd(c) + rest) == Some((c, rest))
  {
    var after := L.UnArgs(c.args) + rest;
    assert L.UnCmd(c) + rest == c.name + after;
    if |c.args| > 0 {
      assert after[0] == ' ';
    }
    assert |after| == 0 || !L.WordChar(after[0]);
    SpanWordAppend(c.name, after);
    assert NotArgStart(rest);
    ArgsRoundTrip(c.args, rest);
  }

  lemma ScriptRoundTrip(cs: seq<L.Cmd>)
    requires |cs| > 0
    ensures L.ParseScript(L.UnScript(cs)) == Some((cs, ""))
    decreases |cs|
  {
    if |cs| == 1 {
      assert L.UnScript(cs) == L.UnCmd(cs[0]) + "";
      CmdRoundTrip(cs[0], "");
      assert Strip("; ", "").None?;
      assert cs == [cs[0]];
    } else {
      var tail := cs[1..];
      var rest := "; " + L.UnScript(tail);
      assert L.UnScript(cs) == L.UnCmd(cs[0]) + rest;
      CmdRoundTrip(cs[0], rest);
      StripAppend("; ", L.UnScript(tail));
      ScriptRoundTrip(tail);
      assert [cs[0]] + tail == cs;
    }
  }

  lemma RoundTrip(t: Tree)
    ensures Parse(Unparse(t)) == Some(t)
  {
    ScriptRoundTrip(t);
  }
}
