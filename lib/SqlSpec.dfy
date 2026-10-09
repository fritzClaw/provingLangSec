// SQL subset: syntax tree, unparser, and a model of the receiver's parser.
// Frozen: changes require owner approval. The proof is in SqlProof.dfy.
//
// The subset is a strict (canonical) fragment of SQLite's grammar (parse.y):
//   SELECT "c1", "c2" FROM "t" [WHERE <cond>]
//   <cond> ::= (<operand> <op> <operand>) | (NOT <cond>) | (<cond> AND <cond>) | (<cond> OR <cond>)
// Untrusted data can only enter the tree as Str(...) literals (requirement R3).
// Data must not contain NUL: SQLite's tokenizer stops at NUL.

include "../spec/LanguageSpec.dfy"

abstract module SqlSpec refines LanguageSpec {
  // ---------------------------------------------------------------- syntax tree
  predicate NoNul(s: string) { forall i :: 0 <= i < |s| ==> s[i] != '\0' }
  type Data = s: string | NoNul(s) witness ""

  predicate IdentChar(c: char) {
    ('a' <= c <= 'z') || ('A' <= c <= 'Z') || ('0' <= c <= '9') || c == '_'
  }
  predicate IsIdent(s: string) { |s| > 0 && forall i :: 0 <= i < |s| ==> IdentChar(s[i]) }
  type Ident = s: string | IsIdent(s) witness "a"

  const MaxInt: int := 9223372036854775807
  type Int = n: int | -MaxInt <= n <= MaxInt witness 0

  datatype Operand = Col(id: Ident) | Str(value: Data) | Num(n: Int)
  datatype CmpOp = Eq | Ne | Lt | Le | Gt | Ge
  datatype Cond =
    | Cmp(l: Operand, op: CmpOp, r: Operand)
    | Not(c: Cond)
    | And(a: Cond, b: Cond)
    | Or(a: Cond, b: Cond)
  type Cols = cs: seq<Ident> | |cs| > 0 witness ["a"]
  datatype Query = Select(cols: Cols, table: Ident, where: Option<Cond>)

  type Tree = Query

  // ------------------------------------------------------------------- unparser
  // Encoder for the data token of a string literal: double every single quote.
  function Esc(s: string): string {
    if |s| == 0 then "" else (if s[0] == '\'' then "''" else [s[0]]) + Esc(s[1..])
  }

  function DigitChar(d: nat): char requires d < 10 { (('0' as int) + d) as char }
  function Digits(n: nat): string decreases n {
    if n < 10 then [DigitChar(n)] else Digits(n / 10) + [DigitChar(n % 10)]
  }
  function IntText(n: Int): string { if n < 0 then "-" + Digits(-n) else Digits(n) }

  function QIdent(id: Ident): string { "\"" + id + "\"" }

  function UnOperand(o: Operand): string {
    match o
    case Col(id) => QIdent(id)
    case Str(v) => "'" + Esc(v) + "'"
    case Num(n) => IntText(n)
  }

  function OpText(op: CmpOp): string {
    match op
    case Eq => "="
    case Ne => "<>"
    case Lt => "<"
    case Le => "<="
    case Gt => ">"
    case Ge => ">="
  }

  function UnCond(c: Cond): string {
    match c
    case Cmp(l, op, r) => "(" + (UnOperand(l) + (" " + (OpText(op) + (" " + (UnOperand(r) + ")")))))
    case Not(x) => "(NOT " + (UnCond(x) + ")")
    case And(a, b) => "(" + (UnCond(a) + (" AND " + (UnCond(b) + ")")))
    case Or(a, b) => "(" + (UnCond(a) + (" OR " + (UnCond(b) + ")")))
  }

  function UnCols(cs: seq<Ident>): string
    requires |cs| > 0
  {
    if |cs| == 1 then QIdent(cs[0]) else QIdent(cs[0]) + ", " + UnCols(cs[1..])
  }

  function Unparse(t: Tree): string {
    "SELECT " + UnCols(t.cols) + " FROM " + QIdent(t.table) +
    (match t.where case None => "" case Some(c) => " WHERE " + UnCond(c))
  }

  // ------------------------------------------- model of the receiver's parser
  // Strict recognizer for exactly the language produced by Unparse. The harness
  // in tools/fidelity checks that SQLite reads these texts the same way.

  // Body of a string literal (after the opening quote): decoded body and the
  // input after the closing quote. A doubled quote stands for one quote.
  function LitBody(s: string): (r: Option<(string, string)>)
    ensures r.Some? ==> |r.value.1| < |s|
    decreases |s|
  {
    if |s| == 0 then None
    else if s[0] == '\'' then
      if |s| >= 2 && s[1] == '\'' then
        match LitBody(s[2..])
        case None => None
        case Some(p) => Some(([s[0]] + p.0, p.1))
      else Some(("", s[1..]))
    else
      match LitBody(s[1..])
      case None => None
      case Some(p) => Some(([s[0]] + p.0, p.1))
  }

  predicate IsDigit(c: char) { '0' <= c <= '9' }

  function SpanDigits(s: string): (r: (string, string))
    ensures r.0 + r.1 == s
    ensures forall i :: 0 <= i < |r.0| ==> IsDigit(r.0[i])
    decreases |s|
  {
    if |s| > 0 && IsDigit(s[0]) then
      var p := SpanDigits(s[1..]);
      ([s[0]] + p.0, p.1)
    else ("", s)
  }

  function Value(ds: string): nat
    requires forall i :: 0 <= i < |ds| ==> IsDigit(ds[i])
    decreases |ds|
  {
    if |ds| == 0 then 0
    else
      assert IsDigit(ds[|ds| - 1]);
      Value(ds[..|ds| - 1]) * 10 + ((ds[|ds| - 1] as int) - ('0' as int))
  }

  function SpanIdent(s: string): (r: (string, string))
    ensures r.0 + r.1 == s
    ensures forall i :: 0 <= i < |r.0| ==> IdentChar(r.0[i])
    decreases |s|
  {
    if |s| > 0 && IdentChar(s[0]) then
      var p := SpanIdent(s[1..]);
      ([s[0]] + p.0, p.1)
    else ("", s)
  }

  function ParseQIdent(s: string): (r: Option<(Ident, string)>)
    ensures r.Some? ==> |r.value.1| < |s|
  {
    match Strip("\"", s)
    case None => None
    case Some(t) =>
      var p := SpanIdent(t);
      if IsIdent(p.0) then
        var id: Ident := p.0;
        match Strip("\"", p.1)
        case Some(u) => Some((id, u))
        case None => None
      else None
  }

  function ParseNum(s: string): (r: Option<(Operand, string)>)
    ensures r.Some? ==> |r.value.1| < |s|
  {
    var neg := |s| > 0 && s[0] == '-';
    var body := if neg then s[1..] else s;
    var p := SpanDigits(body);
    if |p.0| == 0 then None
    else
      var v: int := if neg then 0 - Value(p.0) else Value(p.0);
      if -MaxInt <= v <= MaxInt then Some((Num(v), p.1)) else None
  }

  function ParseOperand(s: string): (r: Option<(Operand, string)>)
    ensures r.Some? ==> |r.value.1| < |s|
  {
    if |s| == 0 then None
    else if s[0] == '"' then
      match ParseQIdent(s)
      case Some(p) => Some((Col(p.0), p.1))
      case None => None
    else if s[0] == '\'' then
      match LitBody(s[1..])
      case Some(p) => if NoNul(p.0) then Some((Str(p.0), p.1)) else None
      case None => None
    else ParseNum(s)
  }

  function ParseOp(s: string): (r: Option<(CmpOp, string)>)
    ensures r.Some? ==> |r.value.1| < |s|
  {
    if |s| >= 2 && s[..2] == "<>" then Some((Ne, s[2..]))
    else if |s| >= 2 && s[..2] == "<=" then Some((Le, s[2..]))
    else if |s| >= 2 && s[..2] == ">=" then Some((Ge, s[2..]))
    else if |s| >= 1 && s[0] == '=' then Some((Eq, s[1..]))
    else if |s| >= 1 && s[0] == '<' then Some((Lt, s[1..]))
    else if |s| >= 1 && s[0] == '>' then Some((Gt, s[1..]))
    else None
  }

  function ParseCond(s: string): (r: Option<(Cond, string)>)
    ensures r.Some? ==> |r.value.1| < |s|
    decreases |s|
  {
    match Strip("(", s)
    case None => None
    case Some(t) =>
      if |t| >= 4 && t[..4] == "NOT " then
        var u := t[4..];
        match ParseCond(u)
        case None => None
        case Some(p) =>
          match Strip(")", p.1)
          case Some(v) => Some((Not(p.0), v))
          case None => None
      else if |t| > 0 && t[0] == '(' then
        match ParseCond(t)
        case None => None
        case Some(p1) =>
          if |p1.1| >= 5 && p1.1[..5] == " AND " then
            match ParseCond(p1.1[5..])
            case None => None
            case Some(p2) =>
              match Strip(")", p2.1)
              case Some(v) => Some((And(p1.0, p2.0), v))
              case None => None
          else if |p1.1| >= 4 && p1.1[..4] == " OR " then
            match ParseCond(p1.1[4..])
            case None => None
            case Some(p2) =>
              match Strip(")", p2.1)
              case Some(v) => Some((Or(p1.0, p2.0), v))
              case None => None
          else None
      else
        match ParseOperand(t)
        case None => None
        case Some(po1) =>
          match Strip(" ", po1.1)
          case None => None
          case Some(u1) =>
            match ParseOp(u1)
            case None => None
            case Some(pop) =>
              match Strip(" ", pop.1)
              case None => None
              case Some(u2) =>
                match ParseOperand(u2)
                case None => None
                case Some(po2) =>
                  match Strip(")", po2.1)
                  case Some(v) => Some((Cmp(po1.0, pop.0, po2.0), v))
                  case None => None
  }

  function ParseCols(s: string): (r: Option<(Cols, string)>)
    ensures r.Some? ==> |r.value.1| < |s|
    decreases |s|
  {
    match ParseQIdent(s)
    case None => None
    case Some(p) =>
      match Strip(", ", p.1)
      case None =>
        var one: Cols := [p.0];
        Some((one, p.1))
      case Some(u) =>
        match ParseCols(u)
        case None => None
        case Some(more) =>
          var all: Cols := [p.0] + more.0;
          Some((all, more.1))
  }

  function Parse(s: string): Option<Tree> {
    match Strip("SELECT ", s)
    case None => None
    case Some(a) =>
      match ParseCols(a)
      case None => None
      case Some(pc) =>
        match Strip(" FROM ", pc.1)
        case None => None
        case Some(b) =>
          match ParseQIdent(b)
          case None => None
          case Some(pt) =>
            if |pt.1| == 0 then Some(Select(pc.0, pt.0, None))
            else
              match Strip(" WHERE ", pt.1)
              case None => None
              case Some(c) =>
                match ParseCond(c)
                case None => None
                case Some(pw) => if |pw.1| == 0 then Some(Select(pc.0, pt.0, Some(pw.0))) else None
  }
}
