module RoundTrip

(* Spike: the same round-trip property as the Dafny version, in F*.
   Theorem: forall c. parse (unparse c) == Some c, with arbitrary strings in literals. *)

open FStar.List.Tot

type col = | Name | Email
type cond =
  | Eq  : col -> list FStar.Char.char -> cond
  | And : cond -> cond -> cond

let q : FStar.Char.char = '\''

let col_text (c: col) : list FStar.Char.char =
  match c with
  | Name -> ['"'; 'n'; 'a'; 'm'; 'e'; '"']
  | Email -> ['"'; 'e'; 'm'; 'a'; 'i'; 'l'; '"']

(* Encoder for the data token: double every single quote. *)
let rec escape (s: list FStar.Char.char) : list FStar.Char.char =
  match s with
  | [] -> []
  | c :: tl -> if c = q then q :: q :: escape tl else c :: escape tl

let eq_sep : list FStar.Char.char = [' '; '='; ' '; '\'']
let and_sep : list FStar.Char.char = [' '; 'A'; 'N'; 'D'; ' ']

let rec unparse (c: cond) : list FStar.Char.char =
  match c with
  | Eq col lit -> col_text col @ (eq_sep @ (escape lit @ [q]))
  | And l r -> '(' :: (unparse l @ (and_sep @ (unparse r @ [')'])))

(* Lexer for a string literal body; returns decoded body and the input after the closing quote. *)
let rec lit_body (s: list FStar.Char.char)
  : Tot (option (list FStar.Char.char & (r: list FStar.Char.char{length r < length s}))) (decreases (length s)) =
  match s with
  | [] -> None
  | c :: tl ->
    if c = q then
      (match tl with
       | c2 :: tl2 ->
         if c2 = q then
           (match lit_body tl2 with
            | None -> None
            | Some (b, r) -> Some (q :: b, r))
         else Some ([], tl)
       | [] -> Some ([], tl))
    else
      (match lit_body tl with
       | None -> None
       | Some (b, r) -> Some (c :: b, r))

let no_leading_quote (rest: list FStar.Char.char) : bool =
  match rest with
  | [] -> true
  | c :: _ -> c <> q

let rec lit_round_trip (s rest: list FStar.Char.char)
  : Lemma (requires no_leading_quote rest)
          (ensures (match lit_body (escape s @ (q :: rest)) with
                    | Some (b, r) -> b == s /\ r == rest
                    | None -> False))
  = match s with
    | [] -> ()
    | c :: tl -> lit_round_trip tl rest

(* strip a fixed prefix *)
let rec strip (p s: list FStar.Char.char)
  : Tot (option (r: list FStar.Char.char{length r <= length s})) (decreases p) =
  match p, s with
  | [], _ -> Some s
  | pc :: ptl, sc :: stl -> if pc = sc then (match strip ptl stl with None -> None | Some r -> Some r) else None
  | _, _ -> None

let rec strip_append (p rest: list FStar.Char.char)
  : Lemma (ensures (match strip p (p @ rest) with Some r -> r == rest | None -> False)) (decreases p)
  = match p with
    | [] -> ()
    | _ :: tl -> strip_append tl rest

let parse_col (s: list FStar.Char.char)
  : option (col & (r: list FStar.Char.char{length r < length s})) =
  match strip (col_text Name) s with
  | Some r -> Some (Name, r)
  | None ->
    (match strip (col_text Email) s with
     | Some r -> Some (Email, r)
     | None -> None)

let rec parse_cond (s: list FStar.Char.char)
  : Tot (option (cond & (r: list FStar.Char.char{length r < length s}))) (decreases (length s)) =
  match s with
  | '(' :: tl ->
    (match parse_cond tl with
     | None -> None
     | Some (l, r1) ->
       (match strip and_sep r1 with
        | None -> None
        | Some r1' ->
          (match parse_cond r1' with
           | None -> None
           | Some (r, r2) ->
             (match r2 with
              | ')' :: r3 -> Some (And l r, r3)
              | _ -> None))))
  | _ ->
    (match parse_col s with
     | None -> None
     | Some (c, r) ->
       (match strip eq_sep r with
        | None -> None
        | Some r' ->
          (match lit_body r' with
           | None -> None
           | Some (lit, r'') -> Some (Eq c lit, r''))))

let parse (s: list FStar.Char.char) : option cond =
  match parse_cond s with
  | Some (c, []) -> Some c
  | _ -> None

let col_round_trip (c: col) (rest: list FStar.Char.char)
  : Lemma (match parse_col (col_text c @ rest) with
           | Some (c', r) -> c' == c /\ r == rest
           | None -> False)
  = strip_append (col_text c) rest

let assoc_and (l r: cond) (rest: list FStar.Char.char)
  : Lemma (unparse (And l r) @ rest == '(' :: (unparse l @ (and_sep @ (unparse r @ (')' :: rest)))))
  = append_assoc (unparse l) (and_sep @ (unparse r @ [')'])) rest;
    append_assoc and_sep (unparse r @ [')']) rest;
    append_assoc (unparse r) [')'] rest

let rec cond_round_trip (c: cond) (rest: list FStar.Char.char)
  : Lemma (requires no_leading_quote rest)
          (ensures (match parse_cond (unparse c @ rest) with
                    | Some (c', r) -> c' == c /\ r == rest
                    | None -> False))
          (decreases c)
  = match c with
    | Eq col lit ->
      let tail = eq_sep @ (escape lit @ [q]) in
      append_assoc (col_text col) tail rest;
      col_round_trip col (tail @ rest);
      append_assoc eq_sep (escape lit @ [q]) rest;
      strip_append eq_sep ((escape lit @ [q]) @ rest);
      append_assoc (escape lit) [q] rest;
      lit_round_trip lit rest
    | And l r ->
      let after_r = unparse r @ (')' :: rest) in
      let after_l = and_sep @ after_r in
      assoc_and l r rest;
      cond_round_trip l after_l;
      strip_append and_sep after_r;
      cond_round_trip r (')' :: rest)

let unparse_is_injection_free (c: cond)
  : Lemma (parse (unparse c) == Some c)
  = cond_round_trip c [];
    append_l_nil (unparse c)
