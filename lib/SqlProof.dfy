// Proof of the extended round-trip for the SQL subset (SqlSpec.dfy).
// A refining module cannot change any definition in SqlSpec; it can only add
// lemmas and give RoundTrip its body.

include "SqlSpec.dfy"

module Sql refines SqlSpec {
  // -------------------------------------------------------- string literals
  predicate NoQuoteFirst(rest: string) { |rest| == 0 || rest[0] != '\'' }

  lemma LitRoundTrip(s: string, rest: string)
    requires NoQuoteFirst(rest)
    ensures LitBody(Esc(s) + "'" + rest) == Some((s, rest))
    decreases |s|
  {
    var input := Esc(s) + "'" + rest;
    if |s| == 0 {
      assert input == "'" + rest;
      assert input[1..] == rest;
    } else if s[0] == '\'' {
      assert Esc(s) == "''" + Esc(s[1..]);
      assert input[0] == '\'' && input[1] == '\'';
      assert input[2..] == Esc(s[1..]) + "'" + rest;
      LitRoundTrip(s[1..], rest);
      assert ['\''] + s[1..] == s;
    } else {
      assert Esc(s) == [s[0]] + Esc(s[1..]);
      assert input[0] == s[0];
      assert input[1..] == Esc(s[1..]) + "'" + rest;
      LitRoundTrip(s[1..], rest);
      assert [s[0]] + s[1..] == s;
    }
  }

  // ------------------------------------------------------------- identifiers
  lemma SpanIdentAppend(id: string, rest: string)
    requires forall i :: 0 <= i < |id| ==> IdentChar(id[i])
    requires |rest| == 0 || !IdentChar(rest[0])
    ensures SpanIdent(id + rest) == (id, rest)
    decreases |id|
  {
    if |id| == 0 {
      assert id + rest == rest;
    } else {
      assert (id + rest)[0] == id[0];
      assert (id + rest)[1..] == id[1..] + rest;
      assert forall i :: 0 <= i < |id[1..]| ==> IdentChar(id[1..][i]);
      SpanIdentAppend(id[1..], rest);
      assert [id[0]] + id[1..] == id;
    }
  }

  lemma QIdentRoundTrip(id: Ident, rest: string)
    ensures ParseQIdent(QIdent(id) + rest) == Some((id, rest))
  {
    var s := QIdent(id) + rest;
    var tail := "\"" + rest;
    assert s == "\"" + (id + tail);
    StripAppend("\"", id + tail);
    SpanIdentAppend(id, tail);
    StripAppend("\"", rest);
  }

  // ---------------------------------------------------------------- integers
  predicate AllDigits(ds: string) { forall i :: 0 <= i < |ds| ==> IsDigit(ds[i]) }
  predicate DelimitedRest(rest: string) { |rest| == 0 || rest[0] == ' ' || rest[0] == ')' }

  lemma DigitsFacts(n: nat)
    ensures |Digits(n)| > 0
    ensures AllDigits(Digits(n))
    ensures Value(Digits(n)) == n
    decreases n
  {
    if n < 10 {
      assert Digits(n) == [DigitChar(n)];
      assert Value([DigitChar(n)][..0]) == 0;
    } else {
      DigitsFacts(n / 10);
      var ds := Digits(n);
      assert ds == Digits(n / 10) + [DigitChar(n % 10)];
      assert ds[..|ds| - 1] == Digits(n / 10);
      assert ds[|ds| - 1] == DigitChar(n % 10);
    }
  }

  lemma SpanDigitsAppend(ds: string, rest: string)
    requires AllDigits(ds)
    requires |rest| == 0 || !IsDigit(rest[0])
    ensures SpanDigits(ds + rest) == (ds, rest)
    decreases |ds|
  {
    if |ds| == 0 {
      assert ds + rest == rest;
    } else {
      assert (ds + rest)[0] == ds[0];
      assert (ds + rest)[1..] == ds[1..] + rest;
      assert AllDigits(ds[1..]);
      SpanDigitsAppend(ds[1..], rest);
      assert [ds[0]] + ds[1..] == ds;
    }
  }

  lemma IntTextFacts(n: Int)
    ensures |IntText(n)| > 0
    ensures n < 0 ==> IntText(n)[0] == '-'
    ensures n >= 0 ==> IsDigit(IntText(n)[0])
  {
    DigitsFacts(if n < 0 then -n else n);
  }

  lemma NumRoundTrip(n: Int, rest: string)
    requires DelimitedRest(rest)
    ensures ParseNum(IntText(n) + rest) == Some((Num(n), rest))
  {
    IntTextFacts(n);
    if n < 0 {
      DigitsFacts(-n);
      var s := IntText(n) + rest;
      assert s == "-" + (Digits(-n) + rest);
      assert s[0] == '-';
      assert s[1..] == Digits(-n) + rest;
      SpanDigitsAppend(Digits(-n), rest);
    } else {
      DigitsFacts(n);
      var s := IntText(n) + rest;
      assert s == Digits(n) + rest;
      assert s[0] == Digits(n)[0];
      assert IsDigit(s[0]);
      SpanDigitsAppend(Digits(n), rest);
    }
  }

  // ---------------------------------------------------------------- operands
  lemma OperandFirstChar(o: Operand)
    ensures |UnOperand(o)| > 0
    ensures var c := UnOperand(o)[0]; c == '"' || c == '\'' || c == '-' || IsDigit(c)
  {
    match o
    case Col(id) => assert UnOperand(o) == "\"" + id + "\"";
    case Str(v) => assert UnOperand(o) == "'" + Esc(v) + "'";
    case Num(n) => IntTextFacts(n);
  }

  lemma OperandRoundTrip(o: Operand, rest: string)
    requires DelimitedRest(rest)
    ensures ParseOperand(UnOperand(o) + rest) == Some((o, rest))
  {
    OperandFirstChar(o);
    match o
    case Col(id) =>
      var s := UnOperand(o) + rest;
      assert s[0] == '"';
      QIdentRoundTrip(id, rest);
    case Str(v) =>
      var s := UnOperand(o) + rest;
      assert s == "'" + (Esc(v) + "'" + rest);
      assert s[0] == '\'';
      assert s[1..] == Esc(v) + "'" + rest;
      assert NoQuoteFirst(rest);
      LitRoundTrip(v, rest);
    case Num(n) =>
      var s := UnOperand(o) + rest;
      assert s == IntText(n) + rest;
      IntTextFacts(n);
      assert s[0] == IntText(n)[0];
      NumRoundTrip(n, rest);
  }

  lemma OpRoundTrip(op: CmpOp, rest: string)
    ensures ParseOp(OpText(op) + (" " + rest)) == Some((op, " " + rest))
  {
    var s := OpText(op) + (" " + rest);
    match op
    case Eq => assert s == "= " + rest; assert s[0] == '='; assert s[1..] == " " + rest;
    case Ne => assert s == "<> " + rest; assert s[..2] == "<>"; assert s[2..] == " " + rest;
    case Lt => assert s == "< " + rest; assert s[..2] == "< "; assert s[0] == '<'; assert s[1..] == " " + rest;
    case Le => assert s == "<= " + rest; assert s[..2] == "<="; assert s[2..] == " " + rest;
    case Gt => assert s == "> " + rest; assert s[..2] == "> "; assert s[0] == '>'; assert s[1..] == " " + rest;
    case Ge => assert s == ">= " + rest; assert s[..2] == ">="; assert s[2..] == " " + rest;
  }

  // -------------------------------------------------------------- conditions
  lemma ConcatRight(x: string, y: string, z: string)
    ensures (x + y) + z == x + (y + z)
  {
  }

  lemma CondStartsWithParen(c: Cond)
    ensures |UnCond(c)| > 0 && UnCond(c)[0] == '('
  {
  }

  lemma CondRoundTrip(c: Cond, rest: string)
    ensures ParseCond(UnCond(c) + rest) == Some((c, rest))
    decreases c, 1
  {
    match c
    case Cmp(l, op, r) => CmpRoundTrip(l, op, r, rest);
    case Not(x) => NotRoundTrip(x, rest);
    case And(a, b) => AndRoundTrip(a, b, rest);
    case Or(a, b) => OrRoundTrip(a, b, rest);
  }

  lemma CmpRoundTrip(l: Operand, op: CmpOp, r: Operand, rest: string)
    ensures ParseCond(UnCond(Cmp(l, op, r)) + rest) == Some((Cmp(l, op, r), rest))
  {
    var tailR := ")" + rest;
    var afterOp := " " + (UnOperand(r) + tailR);
    var afterL := " " + (OpText(op) + afterOp);
    var t := UnOperand(l) + afterL;
    ConcatRight("(" , UnOperand(l) + (" " + (OpText(op) + (" " + (UnOperand(r) + ")")))), rest);
    ConcatRight(UnOperand(l), " " + (OpText(op) + (" " + (UnOperand(r) + ")"))), rest);
    ConcatRight(" ", OpText(op) + (" " + (UnOperand(r) + ")")), rest);
    ConcatRight(OpText(op), " " + (UnOperand(r) + ")"), rest);
    ConcatRight(" ", UnOperand(r) + ")", rest);
    ConcatRight(UnOperand(r), ")", rest);
    assert UnCond(Cmp(l, op, r)) + rest == "(" + t;
    StripAppend("(", t);
    OperandFirstChar(l);
    assert t[0] == UnOperand(l)[0];
    assert !(|t| >= 4 && t[..4] == "NOT ");
    assert t[0] != '(';
    assert DelimitedRest(afterL);
    OperandRoundTrip(l, afterL);
    StripAppend(" ", OpText(op) + afterOp);
    OpRoundTrip(op, UnOperand(r) + tailR);
    StripAppend(" ", UnOperand(r) + tailR);
    assert DelimitedRest(tailR);
    OperandRoundTrip(r, tailR);
    StripAppend(")", rest);
  }

  lemma NotRoundTrip(x: Cond, rest: string)
    ensures ParseCond(UnCond(Not(x)) + rest) == Some((Not(x), rest))
    decreases Not(x), 0
  {
    var tailX := ")" + rest;
    var t := "NOT " + (UnCond(x) + tailX);
    ConcatRight("(NOT ", UnCond(x) + ")", rest);
    ConcatRight(UnCond(x), ")", rest);
    assert "(NOT " == "(" + "NOT ";
    assert UnCond(Not(x)) + rest == "(" + t;
    StripAppend("(", t);
    assert t[..4] == "NOT ";
    assert t[4..] == UnCond(x) + tailX;
    CondRoundTrip(x, tailX);
    StripAppend(")", rest);
  }

  lemma AndRoundTrip(a: Cond, b: Cond, rest: string)
    ensures ParseCond(UnCond(And(a, b)) + rest) == Some((And(a, b), rest))
    decreases And(a, b), 0
  {
    var tailB := ")" + rest;
    var afterA := " AND " + (UnCond(b) + tailB);
    var t := UnCond(a) + afterA;
    ConcatRight("(", UnCond(a) + (" AND " + (UnCond(b) + ")")), rest);
    ConcatRight(UnCond(a), " AND " + (UnCond(b) + ")"), rest);
    ConcatRight(" AND ", UnCond(b) + ")", rest);
    ConcatRight(UnCond(b), ")", rest);
    assert UnCond(And(a, b)) + rest == "(" + t;
    StripAppend("(", t);
    CondStartsWithParen(a);
    assert t[0] == '(';
    assert !(|t| >= 4 && t[..4] == "NOT ");
    CondRoundTrip(a, afterA);
    assert afterA[..5] == " AND ";
    assert afterA[5..] == UnCond(b) + tailB;
    CondRoundTrip(b, tailB);
    StripAppend(")", rest);
  }

  lemma OrRoundTrip(a: Cond, b: Cond, rest: string)
    ensures ParseCond(UnCond(Or(a, b)) + rest) == Some((Or(a, b), rest))
    decreases Or(a, b), 0
  {
    var tailB := ")" + rest;
    var afterA := " OR " + (UnCond(b) + tailB);
    var t := UnCond(a) + afterA;
    ConcatRight("(", UnCond(a) + (" OR " + (UnCond(b) + ")")), rest);
    ConcatRight(UnCond(a), " OR " + (UnCond(b) + ")"), rest);
    ConcatRight(" OR ", UnCond(b) + ")", rest);
    ConcatRight(UnCond(b), ")", rest);
    assert UnCond(Or(a, b)) + rest == "(" + t;
    StripAppend("(", t);
    CondStartsWithParen(a);
    assert t[0] == '(';
    assert !(|t| >= 4 && t[..4] == "NOT ");
    CondRoundTrip(a, afterA);
    assert afterA[1] == 'O';
    assert " AND "[1] == 'A';
    assert !(|afterA| >= 5 && afterA[..5] == " AND ");
    assert afterA[..4] == " OR ";
    assert afterA[4..] == UnCond(b) + tailB;
    CondRoundTrip(b, tailB);
    StripAppend(")", rest);
  }

  // ------------------------------------------------------------ column lists
  lemma ColsRoundTrip(cs: Cols, rest: string)
    requires |rest| == 0 || rest[0] != ','
    ensures ParseCols(UnCols(cs) + rest) == Some((cs, rest))
    decreases |cs|
  {
    if |cs| == 1 {
      QIdentRoundTrip(cs[0], rest);
      assert Strip(", ", rest).None?;
      assert cs == [cs[0]];
    } else {
      var more: Cols := cs[1..];
      var tail := ", " + (UnCols(more) + rest);
      assert UnCols(cs) + rest == QIdent(cs[0]) + tail;
      QIdentRoundTrip(cs[0], tail);
      StripAppend(", ", UnCols(more) + rest);
      ColsRoundTrip(more, rest);
      assert [cs[0]] + more == cs;
    }
  }

  // ------------------------------------------------------------------ theorem
  lemma RoundTrip(t: Tree)
    ensures Parse(Unparse(t)) == Some(t)
  {
    var w := match t.where case None => "" case Some(c) => " WHERE " + UnCond(c);
    var b := QIdent(t.table) + w;
    var afterCols := " FROM " + b;
    var a := UnCols(t.cols) + afterCols;
    assert Unparse(t) == "SELECT " + a;
    StripAppend("SELECT ", a);
    ColsRoundTrip(t.cols, afterCols);
    StripAppend(" FROM ", b);
    QIdentRoundTrip(t.table, w);
    match t.where
    case None =>
    case Some(c) =>
      assert w == " WHERE " + (UnCond(c) + "");
      StripAppend(" WHERE ", UnCond(c) + "");
      CondRoundTrip(c, "");
  }
}
