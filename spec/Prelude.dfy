// Shared definitions for language specifications. Frozen: changes require owner approval.

module Prelude {
  datatype Option<T> = None | Some(value: T)

  // Remove the prefix p from s, if s starts with p.
  function Strip(p: string, s: string): (r: Option<string>)
    ensures r.Some? ==> |r.value| == |s| - |p|
  {
    if |p| <= |s| && s[..|p|] == p then Some(s[|p|..]) else None
  }

  lemma StripAppend(p: string, rest: string)
    ensures Strip(p, p + rest) == Some(rest)
  {
    assert (p + rest)[..|p|] == p;
    assert (p + rest)[|p|..] == rest;
  }
}
