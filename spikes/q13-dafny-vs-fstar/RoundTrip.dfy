// Spike: round-trip property for a tiny SQL-like condition language.
// Theorem: forall c :: Parse(Unparse(c)) == Some(c), with arbitrary strings in literals.

module RoundTrip {

  datatype Option<T> = None | Some(value: T)

  datatype Col = Name | Email
  datatype Cond = Eq(col: Col, lit: string) | And(left: Cond, right: Cond)

  const Q: char := '\''

  function ColText(c: Col): string {
    match c
    case Name => "\"name\""
    case Email => "\"email\""
  }

  // Encoder for the data token: double every single quote.
  function Escape(s: string): string {
    if |s| == 0 then ""
    else (if s[0] == Q then [Q, Q] else [s[0]]) + Escape(s[1..])
  }

  function Unparse(c: Cond): string {
    match c
    case Eq(col, lit) => ColText(col) + " = '" + Escape(lit) + "'"
    case And(l, r) => "(" + Unparse(l) + " AND " + Unparse(r) + ")"
  }

  // Lexer for the body of a string literal (after the opening quote):
  // returns the decoded body and the input after the closing quote.
  function LitBody(s: string): Option<(string, string)>
    decreases |s|
  {
    if |s| == 0 then None
    else if s[0] == Q then
      if |s| >= 2 && s[1] == Q then
        match LitBody(s[2..])
        case None => None
        case Some(p) => Some(([Q] + p.0, p.1))
      else Some(("", s[1..]))
    else
      match LitBody(s[1..])
      case None => None
      case Some(p) => Some(([s[0]] + p.0, p.1))
  }

  lemma LitBodyShrinks(s: string)
    ensures LitBody(s).Some? ==> |LitBody(s).value.1| < |s|
    decreases |s|
  {
    if |s| > 0 && s[0] == Q && |s| >= 2 && s[1] == Q { LitBodyShrinks(s[2..]); }
    else if |s| > 0 && s[0] != Q { LitBodyShrinks(s[1..]); }
  }

  predicate NoLeadingQuote(rest: string) { |rest| == 0 || rest[0] != Q }

  lemma LitRoundTrip(s: string, rest: string)
    requires NoLeadingQuote(rest)
    ensures LitBody(Escape(s) + [Q] + rest) == Some((s, rest))
    decreases |s|
  {
    var input := Escape(s) + [Q] + rest;
    if |s| == 0 {
      assert input == [Q] + rest;
      assert input[1..] == rest;
    } else if s[0] == Q {
      assert Escape(s) == [Q, Q] + Escape(s[1..]);
      assert input[2..] == Escape(s[1..]) + [Q] + rest;
      LitRoundTrip(s[1..], rest);
      assert [Q] + s[1..] == s;
    } else {
      assert Escape(s) == [s[0]] + Escape(s[1..]);
      assert input[1..] == Escape(s[1..]) + [Q] + rest;
      LitRoundTrip(s[1..], rest);
      assert [s[0]] + s[1..] == s;
    }
  }

  predicate StartsWith(s: string, p: string) { |p| <= |s| && s[..|p|] == p }

  function ParseCol(s: string): Option<(Col, string)> {
    if StartsWith(s, "\"name\"") then Some((Name, s[6..]))
    else if StartsWith(s, "\"email\"") then Some((Email, s[7..]))
    else None
  }

  // Recursive-descent parser over characters. The result's rest is always a proper suffix.
  function ParseCond(s: string): Option<(Cond, string)>
    ensures ParseCond(s).Some? ==> |ParseCond(s).value.1| < |s|
    decreases |s|
  {
    if |s| > 0 && s[0] == '(' then
      match ParseCond(s[1..])
      case None => None
      case Some(p1) =>
        var r1 := p1.1;
        if StartsWith(r1, " AND ") then
          match ParseCond(r1[5..])
          case None => None
          case Some(p2) =>
            var r2 := p2.1;
            if |r2| > 0 && r2[0] == ')' then Some((And(p1.0, p2.0), r2[1..])) else None
        else None
    else
      match ParseCol(s)
      case None => None
      case Some(pc) =>
        var r := pc.1;
        if StartsWith(r, " = '") then
          LitBodyShrinks(r[4..]);
          match LitBody(r[4..])
          case None => None
          case Some(pl) => Some((Eq(pc.0, pl.0), pl.1))
        else None
  }

  function Parse(s: string): Option<Cond> {
    match ParseCond(s)
    case Some(p) => if |p.1| == 0 then Some(p.0) else None
    case None => None
  }

  lemma ColRoundTrip(c: Col, rest: string)
    ensures ParseCol(ColText(c) + rest) == Some((c, rest))
  {
    var input := ColText(c) + rest;
    match c
    case Name =>
      assert input[..6] == "\"name\"";
      assert input[6..] == rest;
    case Email =>
      assert input[..6] != "\"name\"" by { assert input[1] == 'e'; }
      assert input[..7] == "\"email\"";
      assert input[7..] == rest;
  }

  lemma CondRoundTrip(c: Cond, rest: string)
    requires NoLeadingQuote(rest)
    ensures ParseCond(Unparse(c) + rest) == Some((c, rest))
    decreases c, 1
  {
    match c
    case Eq(col, lit) => EqRoundTrip(col, lit, rest);
    case And(l, r) => AndRoundTrip(l, r, rest);
  }

  lemma EqRoundTrip(col: Col, lit: string, rest: string)
    requires NoLeadingQuote(rest)
    ensures ParseCond(Unparse(Eq(col, lit)) + rest) == Some((Eq(col, lit), rest))
  {
    var input := Unparse(Eq(col, lit)) + rest;
    var tail := " = '" + Escape(lit) + "'" + rest;
    assert input == ColText(col) + tail;
    ColRoundTrip(col, tail);
    assert input[0] == '"';
    assert tail[..4] == " = '";
    assert tail[4..] == Escape(lit) + [Q] + rest;
    LitRoundTrip(lit, rest);
  }

  lemma AndRoundTrip(l: Cond, r: Cond, rest: string)
    requires NoLeadingQuote(rest)
    ensures ParseCond(Unparse(And(l, r)) + rest) == Some((And(l, r), rest))
    decreases And(l, r), 0
  {
    var input := Unparse(And(l, r)) + rest;
    var afterL := " AND " + Unparse(r) + ")" + rest;
    assert input == "(" + (Unparse(l) + afterL);
    assert input[1..] == Unparse(l) + afterL;
    CondRoundTrip(l, afterL);
    assert afterL[..5] == " AND ";
    var afterR := ")" + rest;
    assert afterL[5..] == Unparse(r) + afterR;
    CondRoundTrip(r, afterR);
    assert afterR[1..] == rest;
  }

  // The security theorem for this spike language.
  lemma UnparseIsInjectionFree(c: Cond)
    ensures Parse(Unparse(c)) == Some(c)
  {
    CondRoundTrip(c, "");
    assert Unparse(c) + "" == Unparse(c);
  }

  // Executable entry point for differential testing after compilation.
  method {:export} Render(c: Cond) returns (sql: string)
    ensures Parse(sql) == Some(c)
  {
    UnparseIsInjectionFree(c);
    sql := Unparse(c);
  }
}
