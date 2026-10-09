# Literature review: provably injection-free code from AI agents

*Version 1.2, 2026-10-09.* This review covers the literature-review task in [INTENT.md](../INTENT.md). BibTeX for every cited work is in [`references.bib`](references.bib).

## How this review was made

- **Read in full:**
  - Hermerschmidt et al. 2015
  - Bieschke et al. 2017 (McHammerCoder)
  - chapter 8 of Hermerschmidt's dissertation
  - Bratus et al. 2017
  - Su & Wassermann 2006
  - Ray & Ligatti 2012
  - the slides of Hermerschmidt et al. 2020
  - the relevant sections of the Ur/Web paper
- **Read at abstract level:** all other works. The sources were publisher pages, arXiv, USENIX, Crossref and Semantic Scholar. ACM and IEEE full texts were not reachable for automated download. Statements about these works stay within what their abstracts say.
- **Bibliographic data:** taken from Crossref, DataCite, arXiv and USENIX metadata, never typed from memory.
- **Tool facts:** release platforms, licenses and code-generation targets were checked in each tool's repository and documentation on 2026-10-08.
- **Search method:** web searches combined LangSec, unparsing, injection, verified parsing and serialization, LLMs with formal verification, and intent formalization. The references of the core papers were followed one level deep. This is a focused review, not a systematic one.

## 1. Key findings

1. **The security property has been defined, but no one has proven it mechanically.**
   - Hermerschmidt et al. define injection-freedom of output as a correct *(un)parse round-trip*. It must also hold for syntax trees whose data tokens contain attacker-chosen strings: `parse_decode(unparse_encode(m)) = m` [[hermerschmidt2015unparsers](#hermerschmidt2015unparsers), [hermerschmidt2019dissertation](#hermerschmidt2019dissertation)].
   - McHammerCoder restates this requirement. It explicitly leaves "proving correctness of the generated (un)parser" out of scope and is evaluated by fuzzing instead [[bieschke2017mchammercoder](#bieschke2017mchammercoder)].
   - We found no mechanized proof of this property for a textual output language.
2. **The classic definitions of injection agree with this property, with one caveat.**
   - Su and Wassermann call input an injection when it is not a complete syntactic form in the output's parse tree [[su2006essence](#su2006essence)].
   - Ray and Ligatti show that purely syntactic definitions both miss attacks and flag harmless inputs. A missed attack is, for example, an input `exit()` that forms a complete function-call node. They define injection as untrusted symbols used outside of closed values instead [[ray2012defining](#ray2012defining)].
   - If untrusted data may only appear as *literal* leaves, both definitions are satisfied.
3. **Verified parsers and serializers prove the same inverse property, but for binary formats.**
   - EverParse, EverParse3D, PulseParse and Comparse (all in F\*), Narcissus (Coq), Vest (Verus) and VUPER prove that parsing inverts serialization, often together with non-malleability [[ramananandro2019everparse](#ramananandro2019everparse), [swamy2022everparse3d](#swamy2022everparse3d), [ramananandro2025pulseparse](#ramananandro2025pulseparse), [wallez2023comparse](#wallez2023comparse), [delaware2019narcissus](#delaware2019narcissus), [cai2025vest](#cai2025vest), [zhou2026vuper](#zhou2026vuper)].
   - In these binary formats, data fields are delimited by length, so data needs no escaping.
   - Textual languages with quoting and escaping are not covered, and that is where SQL injection and XSS happen.
4. **AI agents already produce provably correct parsers.**
   - 3DGen has AI agents write EverParse 3D specifications from RFCs and sample inputs. From these it generates verified C parsers for 20 formats [[fakhoury2025threedgen](#fakhoury2025threedgen)].
   - 3DGen works on the input side of binary formats. This project targets the output side (unparsing) of textual languages.
   - Here the agent writes both the code and its proof against a fixed theorem.
5. **How well an LLM proves things depends heavily on the tool.**
   - On the vericoding benchmark, off-the-shelf LLMs solve 82% of Dafny tasks, 44% of Verus tasks and 27% of Lean tasks [[bursuc2025vericoding](#bursuc2025vericoding)].
   - AlgoVeri gives every tool identical contracts and reports 40.3%, 24.7% and 7.8% [[zhao2026algoveri](#zhao2026algoveri)].
   - F\* has its own corpus and synthesis results [[chakraborty2025fstar](#chakraborty2025fstar)].
   - For Coq, Rango proves 32% of a large benchmark [[thompson2025rango](#thompson2025rango)].
6. **LLMs are known to game specifications.**
   - AlphaVerus needs a filtering step that removes misaligned specifications to prevent reward hacking [[aggarwal2025alphaverus](#aggarwal2025alphaverus)].
   - The vericoding benchmark counts solutions that change the specification or use `assume` as failures [[bursuc2025vericoding](#bursuc2025vericoding)].
   - Our checker must therefore pin the theorem statements and reject any construct that skips a proof.
7. **LLM-generated code is measurably insecure.**
   - About 40% of Copilot's programs in security-relevant scenarios were vulnerable [[pearce2022copilot](#pearce2022copilot)].
   - In a user study, people with an AI assistant wrote less secure code, yet believed it was more secure [[perry2023insecure](#perry2023insecure)].
   - BaxBench could execute exploits against about half of the functionally correct backends that LLMs generated [[vero2025baxbench](#vero2025baxbench)].
8. **Turning intent into a formal specification is the open gap in intent-driven development.**
   - No algorithm can check that a formal specification matches the user's informal intent [[lahiri2024fmcad](#lahiri2024fmcad)].
   - Humans therefore have to review the theorem statements. After review, the statements must be frozen.

## 2. LangSec and the work of Hermerschmidt et al.

### 2.1 LangSec in brief

LangSec treats the valid inputs of a program as a formal language. It rests on three rules:
- recognize the input completely before processing it;
- keep the input language no more powerful than necessary;
- avoid *parser differentials*, where two components parse "the same" language differently [[sassaman2011halting](#sassaman2011halting), [sassaman2013formal](#sassaman2013formal), [bratus2014frontier](#bratus2014frontier)].

Momot et al. collect the resulting classes of errors in a taxonomy [[momot2016turrets](#momot2016turrets)]. Bratus et al., with Hermerschmidt as co-author, turn the approach into three design patterns: the *Recognizer*, the *Most Restrictive Input Definition* and the *Unparser* [[bratus2017curing](#bratus2017curing)].

### 2.2 Unparsers with context-sensitive encoders (Hermerschmidt, Kugelmann, Rumpe 2015)

[[hermerschmidt2015unparsers](#hermerschmidt2015unparsers)] places injections on the output side. Any program that uses input to produce a document in a context-free language can be vulnerable.

- **Definition.**
  - Following Danielsson [[danielsson2013pretty](#danielsson2013pretty)] and Arnoldus et al. [[arnoldus2011unparser](#arnoldus2011unparser)], (un)parsing is a *correct round-trip* if `parse(unparse(x)) = x` for every AST `x`.
  - The paper extends this to ASTs `m` that contain malicious data, meaning that no document `d ∈ L` parses to `m`. For these it requires `parse_decode(unparse_encode(m)) = m`.
  - An injection vulnerability means that an adversary can make the program produce documents in `L` that the developer did not intend.
- **Mechanism.**
  - The grammar gets an *encoding table* per token, because each token corresponds to one context.
  - A generator derives context-sensitive encoders for the unparser and matching decoders for the parser.
  - For composed languages, such as JavaScript inside HTML, encoding starts at the innermost language and decoding at the outermost.
- **Injecting up vs. injecting down.**
  - The round-trip prevents "injecting up", that is, breaking out of a token.
  - "Injecting down" puts control tokens *inside* a context to change its meaning, for example user-supplied HTML in a forum. Preventing it requires a reduced grammar for either the output or the input.
- **Implementation and evaluation.**
  - The approach is implemented in MontiCore. Templates are parsed into ASTs whose data tokens hold placeholders.
  - It was evaluated on HTML with JavaScript, using OWASP ZAP and FuzzDB attack strings, and no XSS was found.
  - This is penetration testing, not proof.
- **Stated assumption.** The paper assumes "an idealized world, where unparsers and parsers are generated from the same grammar". It names differing parser implementations as another dimension of the problem.

### 2.3 The dissertation (Hermerschmidt 2019, chapter 8)

[[hermerschmidt2019dissertation](#hermerschmidt2019dissertation)] states the round-trip as Definition 8.2.1, together with the same extension. It adds three points.

- **Data tokens vs. control tokens** (after Bagge and Hasu [[bagge2013formatting](#bagge2013formatting)]). Malicious input that tries to inject control tokens always sits in the data tokens of the AST.
- **Checking an encoding table.**
  - Escape sequences must match the token's regular expression.
  - Encoded words must never combine into a control token. This can be checked by enumerating the allowed words up to the length of the longest control token.
  - Prefixes and suffixes of control tokens must also be encoded.
  - The first symbol of the escape sequence must be encoded as well, so that decoding is unambiguous.
- **A limit for executable output languages.**
  - Some output languages are themselves executed, such as HTML with JavaScript that builds a DOM.
  - There a correct round-trip protects the receiver's parser, but the sender cannot prevent injection into what the executed program outputs later.

### 2.4 McHammerCoder (Bieschke, Hermerschmidt, Rumpe, Stanchev 2017)

[[bieschke2017mchammercoder](#bieschke2017mchammercoder)] generates parsers, unparsers, encoders and decoders from a single grammar. It handles both textual and binary languages and is built on the Hammer parser combinators. Its "formal problem definition" lists four conditions:

1. Valid input and output are defined by a deterministic context-free grammar.
2. The parser rejects every message outside the language.
3. The program uses only the parts of the input parse tree that are meant to be variable. The paper calls this "a design decision which corresponds to the intended program behaviour".
4. For all parse trees `t` containing any kind of data, `parse(unparse(t)) = t`.

How the encoding works:
- It is derived automatically: every keyword and every keyword part (prefix or suffix) gets an escape code.
- An encoding must be *uniquely decipherable*, *instantaneous* and *secure*.
- Encoding is applied exactly once, and decoding uses a sliding window.

How it was evaluated:
- DNS, using Peach fuzzing and a differential comparison with the BIND server.
- HTML with JavaScript, using ZAP, AppScan and FuzzDB.
- The paper states that "proving correctness of the generated (un)parser is out of scope".
- It lists parser differentials as future work. The code is on GitHub [[mchammercoder](#mchammercoder)].

### 2.5 Language-agnostic injection detection (Hermerschmidt, Straub, Piskachev 2020)

[[hermerschmidt2020detection](#hermerschmidt2020detection)] finds injection vulnerabilities in existing unparsers without a specification of their language:
- dynamic taint analysis infers the unparse trees;
- keywords extracted from those trees drive a fuzzer;
- an injection is detected when the parse tree changes across an unparser–parser round-trip.

The talk concludes: "Detection is never complete; use a constructive approach like McHammerCoder."

For this project the paper offers a ready-made *test oracle*. The same round-trip comparison can check our formal parser model against the real interpreter.

### 2.6 The Unparser pattern (Bratus et al. 2017)

In the pattern of [[bratus2017curing](#bratus2017curing)], the business logic fills `OutputData` objects without caring about special tokens. Only the `Unparser` writes to `RawOutput`, and it uses the `OutputGrammar` to encode. SQL prepared statements are named as a special case of this pattern that had not yet been generalized to other output languages.

### 2.7 What this project takes from this strand

| ID | Requirement | Source |
|---|---|---|
| R1 | The central theorem is the extended round-trip: `parse_decode(unparse_encode(t)) = t` for **all** syntax trees, including data tokens with arbitrary strings. | [[hermerschmidt2015unparsers](#hermerschmidt2015unparsers)], [[bieschke2017mchammercoder](#bieschke2017mchammercoder)] |
| R2 | Only the unparser may produce strings that reach the interpreter. | [[bratus2017curing](#bratus2017curing)] |
| R3 | Untrusted data may only appear in data tokens (literal leaves). | [[bieschke2017mchammercoder](#bieschke2017mchammercoder)] (condition 3), [[ray2012defining](#ray2012defining)] |
| R4 | Nested languages, such as a `LIKE` pattern inside a string literal, are encoded from the inside out and decoded from the outside in. | [[hermerschmidt2015unparsers](#hermerschmidt2015unparsers)] |
| R5 | That the formal parser model agrees with the real interpreter's parser is an explicit, tested assumption. | [[hermerschmidt2015unparsers](#hermerschmidt2015unparsers)], [[sassaman2013formal](#sassaman2013formal)] |
| R6 | "Injecting down" is out of scope unless a reduced grammar is specified. | [[hermerschmidt2015unparsers](#hermerschmidt2015unparsers)] |

## 3. Formal definitions of injection

| Work | What counts as an injection | How it is enforced | Relation to R1–R3 |
|---|---|---|---|
| Su & Wassermann 2006 [[su2006essence](#su2006essence)] | Some filtered input in the query is not a *valid syntactic form*. That is, no single parse-tree node of an allowed type spans exactly that input. | At runtime: inputs are marked with meta-characters and the query is parsed with an augmented grammar (SqlCheck). | If literals are the only allowed node type, R1 and R3 imply this. |
| Ray & Ligatti 2012 [[ray2012defining](#ray2012defining)] | An injected symbol is used outside a closed value (normal form) in the output program. | Requires white-box runtime monitoring. Static or black-box analysis cannot decide it precisely. | R3 restricts untrusted data to values. |
| Bisht et al. 2010, CANDID [[bisht2010candid](#bisht2010candid)] | The actual query's structure differs from the intended structure, which is mined by running the program on harmless candidate inputs. | Dynamic program transformation. | Our approach fixes the intended structure by construction instead. |
| Buehrer et al. 2005, SQLGuard [[buehrer2005sqlguard](#buehrer2005sqlguard)] | The parse tree of the query differs before and after the input is inserted. | Comparison at runtime. | The runtime counterpart of R1. |
| Halfond & Orso 2005, AMNESIA [[halfond2005amnesia](#halfond2005amnesia)] | The query does not match a statically built model of legitimate queries. | Static model plus runtime monitor. | — |

Three observations matter for this project:
- **Restricting untrusted input to literals avoids Ray and Ligatti's objections.** Their critique applies only when the policy lets untrusted input form non-literal nodes, such as a whole function call. With literals only, both their false negatives and their false positives go away.
- **Copying input verbatim is always vulnerable.** Ray and Ligatti prove that applications which copy untrusted input *verbatim* into an output program are vulnerable, so encoding is unavoidable.
- **There is a ready-made starting grammar.** Su and Wassermann's simplified `SELECT` grammar (with `AND`, `OR`, `NOT`, comparisons, identifiers, and string and numeric literals) is a natural starting point for our SQL subset.

## 4. Verified parsing, unparsing and serialization

### 4.1 Foundations of round-trips and unparsing

- Danielsson proves in Agda that pretty-printing a value and parsing the result with the same unambiguous grammar returns the original value [[danielsson2013pretty](#danielsson2013pretty)]. This is the round-trip, but only for well-formed trees.
- Other foundational work on unparsing:
  - Arnoldus et al. define when template metalanguages are *unparser-complete* [[arnoldus2011unparser](#arnoldus2011unparser)].
  - Rendel and Ostermann describe a parser and a pretty-printer as a single program built from partial isomorphisms [[rendel2010invertible](#rendel2010invertible)].
  - FliPpr derives parsers from pretty-printers [[matsuda2013flippr](#matsuda2013flippr)].
  - Zaytsev and Bagge systematize the terminology of parsing and unparsing [[zaytsev2014parsing](#zaytsev2014parsing)].
- StringBorg embeds guest languages such as SQL into host languages. It generates code that rebuilds the embedded sentences with escaping, which makes the code immune to injection by construction [[bravenboer2007stringborg](#bravenboer2007stringborg)].
- Nail derives both a parser and a generator from one grammar by setting up a semantic bijection between the data format and the object model [[bangert2014nail](#bangert2014nail)]. It is not mechanically verified.

### 4.2 Mechanically verified parsers and serializers (mostly binary formats)

| Work | Prover | Proven properties, according to the abstract |
|---|---|---|
| EverParse [[ramananandro2019everparse](#ramananandro2019everparse)] | F\* (LowParse) | memory safety; parsing is the inverse of serialization; non-malleability |
| EverParse3D [[swamy2022everparse3d](#swamy2022everparse3d)] | F\* | generated C parsers with proofs of memory and arithmetic safety, functional correctness and double-fetch freedom |
| PulseParse [[ramananandro2025pulseparse](#ramananandro2025pulseparse)] | F\* / Pulse (separation logic) | verified parser and serializer combinators for non-malleable binary formats (CBOR, CDDL, COSE) |
| Comparse [[wallez2023comparse](#wallez2023comparse)] | F\* | formats in cryptographic protocols, with properties strong enough for protocol security |
| Narcissus [[delaware2019narcissus](#delaware2019narcissus)] | Coq | decoders and encoders derived automatically with tactics |
| Vest [[cai2025vest](#cai2025vest)] | Verus (Rust) | high-performance verified binary parsers and serializers |
| VUPER [[zhou2026vuper](#zhou2026vuper)] | not named in the abstract | round-trip consistency for ASN.1 UPER; its verified parser served as a test oracle that found 20 types of inconsistencies in 11 existing parsers |

### 4.3 Verified parser generators and lexers for textual languages

- Jourdan, Pottier and Leroy check in Coq that an LR(1) automaton agrees with its grammar [[jourdan2012lr1](#jourdan2012lr1)].
- Vermillion is a verified LL(1) parser generator in Coq [[lasser2019vermillion](#lasser2019vermillion)].
- CoStar is a verified ALL(\*) parser. It is sound and complete for grammars without left recursion and detects ambiguous inputs [[lasser2021costar](#lasser2021costar)].
- Verbatim is a lexer implemented and verified in Coq. It was presented at the LangSec workshop [[egolf2021verbatim](#egolf2021verbatim)].

### 4.4 What this strand means for the project

- **The proof pattern exists.** The property we need, "parsing inverts serialization", is well established, and there are libraries for it in F\* (LowParse), Coq (Narcissus, CoStar, Verbatim) and Verus (Vest).
- **Textual languages add two new problems.**
  - Escaping and encoding have to be proven correct.
  - The lexer can be fooled across adjacent tokens, for example by a keyword split over two data tokens (see 2.4). The proof therefore has to cover the lexical level, not just the grammar.
- **A verified parser does double duty.** An executable verified parser for our SQL subset can serve as the formal model of the receiver *and* as a test oracle against SQLite (R5). VUPER already uses a verified parser this way.

## 5. Approaches that prevent injection by construction, and program analysis

### 5.1 Prevention by construction

- **Typed query construction.**
  - SQL DOM wraps SQL in a strongly typed API, so that dynamically built statements are checked at compile time [[mcclure2005sqldom](#mcclure2005sqldom)].
  - Prepared statements are the industry standard, and Bratus et al. classify them as a special case of the Unparser pattern [[bratus2017curing](#bratus2017curing)]. Their parameters bind values only, not identifiers or syntax.
- **Typed web languages.** In Ur/Web, embedded SQL and HTML are abstract syntax trees, and an inserted value is formatted as a literal of the embedded language. The paper says this rules out "code injection vulnerabilities that rely on surprising consequences of concatenating code-as-strings" [[chlipala2015urweb](#chlipala2015urweb)].
- **Templates that escape automatically.**
  - Samuel, Saxena and Song use type qualifiers to add context-sensitive automatic sanitization to templating languages [[samuel2011autosanitization](#samuel2011autosanitization)].
  - Kern reports how Google prevents script injection through API design [[kern2014tangled](#kern2014tangled)].
  - Weinberger et al. analysed XSS sanitization in web frameworks [[weinberger2011xss](#weinberger2011xss)]. According to Hermerschmidt et al., only one of 14 frameworks sanitized input in all HTML, JavaScript, CSS and URI contexts.
- **Correctness of sanitizers.**
  - ScriptGard detects and repairs sanitizers placed in the wrong spot [[saxena2011scriptgard](#saxena2011scriptgard)].
  - BEK is a language for writing sanitizers whose idempotence, commutativity and equivalence can be checked [[hooimeijer2011bek](#hooimeijer2011bek)].

### 5.2 Program analysis

- Wassermann and Su's static analysis treats a query as an attack when the input changes its intended syntactic structure. It checks this with grammar-based string analysis and is sound, precise and fully automated for PHP [[wassermann2007sound](#wassermann2007sound)].
- TAJ is a taint analysis for Java web applications [[tripp2009taj](#tripp2009taj)].
- Type systems for information flow [[sabelfeld2003ifc](#sabelfeld2003ifc)] treat injection as a violation of integrity.

### 5.3 What this strand means for the project

- **These designs trust their escaping functions instead of proving them.** They do supply the right architecture (R2, R3). This project's contribution is to prove the escaping and unparsing step, and to make it mechanically checkable that an agent's code follows the design.
- **R3 can be enforced with types instead of taint analysis.** The query type is abstract so that only the unparser can produce it, and untrusted values enter only through literal constructors.

## 6. LLMs, formal verification and intent formalization

### 6.1 Motivation: LLM-generated code is often insecure

- About 40% of 1,689 programs that Copilot generated for scenarios built around high-risk CWEs were vulnerable [[pearce2022copilot](#pearce2022copilot)].
- In a user study, participants with an AI assistant wrote significantly less secure code, and were more likely to believe it was secure [[perry2023insecure](#perry2023insecure)].
- In BaxBench, exploits succeeded on about half of the functionally correct backends that LLMs generated [[vero2025baxbench](#vero2025baxbench)].

### 6.2 LLMs that generate verified code and proofs

"Vericoding" is the term for having an LLM generate formally verified code from a formal specification.

| Work | Tool | Result, according to the abstract |
|---|---|---|
| Vericoding [[bursuc2025vericoding](#bursuc2025vericoding)] | Dafny / Verus / Lean | 82% / 44% / 27% with off-the-shelf LLMs; natural-language descriptions do not help significantly |
| AlgoVeri [[zhao2026algoveri](#zhao2026algoveri)] | Dafny / Verus / Lean | 40.3% / 24.7% / 7.8% on 77 classical algorithms with identical contracts |
| DafnyBench [[loughridge2024dafnybench](#loughridge2024dafnybench)] | Dafny | 68% success at generating verification hints for more than 750 programs |
| Clover [[sun2024clover](#sun2024clover)] | Dafny | consistency checks among code, docstrings and formal annotations; accepts up to 87% of correct instances while rejecting all incorrect ones |
| AutoVerus [[yang2025autoverus](#yang2025autoverus)] | Verus | correct proofs for more than 90% of 150 tasks |
| AlphaVerus [[aggarwal2025alphaverus](#aggarwal2025alphaverus)] | Verus | self-improving translation; filters misaligned specifications to prevent reward hacking |
| Chakraborty et al. [[chakraborty2025fstar](#chakraborty2025fstar)] | F\* | dataset of 600K lines with about 32K definitions; fine-tuned small models compare favourably with GPT-4 |
| Rango [[thompson2025rango](#thompson2025rango)] | Coq | proves 32.0% of the CoqStoq theorems |
| Baldur [[first2023baldur](#first2023baldur)] | Isabelle/HOL | generates and repairs whole proofs |
| Lemur [[wu2024lemur](#wu2024lemur)] | calculus | provably sound combination of LLMs and automated reasoners |
| VERINA [[ye2025verina](#ye2025verina)] | Lean | benchmark for generating code, specification and proof together |

### 6.3 AI agents and verified parsers

3DGen is the closest prior work [[fakhoury2025threedgen](#fakhoury2025threedgen)]. AI agents turn RFC text and sample inputs into EverParse 3D specifications. These are refined until they pass symbolically generated tests, and verified C parsers are then generated for 20 formats.

| | 3DGen | This project |
|---|---|---|
| Language class | binary formats | textual languages with quoting and escaping |
| Side | input (parsing) | output (unparsing, i.e. injection) |
| What the agent writes | a format specification; verified code is generated from it | application code plus its proof |
| What decides acceptance | tests generated symbolically from the specification | a fixed, human-approved theorem checked by a deterministic prover |

### 6.4 Other formal guarantees for LLM-generated code

- Marmaragan has an LLM write SPARK annotations for Ada programs, which GNATprove then checks [[cramer2025marmaragan](#cramer2025marmaragan)].
- Astrogator lets the user confirm their intent in a formal query language and verifies LLM-generated Ansible code against it. It verifies correct code in 83% of cases and identifies incorrect code in 92% [[councilman2025astrogator](#councilman2025astrogator)].
- TypePilot uses the Scala type system and the Stainless verifier in an agent pipeline. It substantially reduces input-validation and injection vulnerabilities, but this is measured empirically, not proven [[sternfeld2025typepilot](#sternfeld2025typepilot)].

### 6.5 Intent formalization and intent-driven development

- **Lahiri** studies how to evaluate LLM-driven formalization of user intent for verification-aware languages such as Dafny and F\*. He argues that no algorithm can establish that a specification matches the intent [[lahiri2024fmcad](#lahiri2024fmcad)]. His talk at AIware describes evaluation metrics inspired by mutation testing, and deriving data-format specifications in the 3D language from informal sources [[lahiri2024aiware](#lahiri2024aiware)].
- **nl2postcond** has LLMs turn natural-language intent into checkable postconditions [[endres2024nl2postcond](#endres2024nl2postcond)].
- **TiCoder** clarifies intent through tests, as a partial formalization, and improves pass@1 by about 46 percentage points on average [[fakhoury2024ticoder](#fakhoury2024ticoder)].
- **Intent-driven development** treats intent as a first-class artifact that agents build against [[iddweb](#iddweb)]. Spec-driven development, for example GitHub's Spec Kit, is a close relative [[speckit2025](#speckit2025)]. This project adds one more layer to that chain: a formal theorem that a machine checks.

### 6.6 Trust model

- **Proof-carrying code** [[necula1997pcc](#necula1997pcc)]: an untrusted producer supplies a proof, and the consumer checks it with a small trusted checker. In this project the LLM is the untrusted producer.
- **Guaranteed Safe AI** [[dalrymple2024gsai](#dalrymple2024gsai)] combines three components. Each maps onto this project:

  | Guaranteed Safe AI | This project |
  |---|---|
  | world model | grammar and parser model of SQLite |
  | safety specification | theorem built from R1–R3 |
  | verifier producing an auditable proof certificate | the prover's checker |

### 6.7 What this strand means for the project

- **Tool choice strongly affects agent success** (Q8).
- **We must defend against specification gaming.** Theorem statements are frozen and hash-pinned, and the checker rejects `admit`, `assume`, `sorry`, `Admitted` and added axioms (Q5).
- **Humans must review the theorem statements**, because that is where intent becomes formal (Q5, Q12).

## 7. Proof tools for this project (input for Q8)

| | F\* | Rocq (Coq) | Lean 4 | Dafny | Verus |
|---|---|---|---|---|---|
| How proofs are found | dependent types, SMT (Z3) and tactics [[swamy2016fstar](#swamy2016fstar), [demoura2008z3](#demoura2008z3)] | interactive tactics, checked by a small kernel | tactics and automation, checked by a small kernel [[demoura2021lean4](#demoura2021lean4)] | annotations plus SMT (Boogie/Z3) [[leino2010dafny](#leino2010dafny)] | annotations plus SMT, on Rust code [[lattuada2023verus](#lattuada2023verus), [lattuada2024verus](#lattuada2024verus)] |
| Running code it produces | extracts to OCaml or F#; its Low\* subset compiles to C or Rust via KaRaMeL [[protzenko2017lowstar](#protzenko2017lowstar)] | extracts to OCaml, Haskell or Scheme | native code, since Lean is also a programming language | compiles to C#, Go, Python, Java or JavaScript | the code is Rust |
| Evidence that LLMs can prove in it | dedicated corpus and synthesis results [[chakraborty2025fstar](#chakraborty2025fstar)]; in 3DGen the agents write specifications, not F\* proofs | Rango 32% | vericoding 27%, AlgoVeri 7.8% | vericoding 82%, AlgoVeri 40.3%, DafnyBench 68% | vericoding 44%, AlgoVeri 24.7%, AutoVerus >90% of 150 tasks |
| Prior work on verified parsers and serializers | EverParse, EverParse3D, PulseParse, Comparse | Narcissus, Vermillion, CoStar, Verbatim, CompCert's LR(1) validator | none found in this review | none found in this review | Vest |
| Linux arm64 (Docker on Apple Silicon) | official binaries; the release workflow builds on Ubuntu 24.04 ARM | the official Docker images we checked are x86_64 only; build from source via opam | official toolchains | no Linux arm64 release package; install as a .NET tool plus a separate Z3 | no prebuilt binaries; build from source |
| License | Apache-2.0 | LGPL-2.1 | Apache-2.0 | MIT | MIT |

**Determinism.** Rocq and Lean check proofs in a small kernel, so the result is fully deterministic. F\*, Dafny and Verus hand proof obligations to Z3. For pinned versions of the tool and Z3 the result is reproducible, but small changes to the code or the solver version can flip it. F\* and Dafny also support machine-independent resource limits instead of wall-clock timeouts. Either way, every version must be pinned in the DevContainer. Why3 [[filliatre2013why3](#filliatre2013why3)] is another SMT front end; it was not shortlisted.

**Assessment.**
- **F\*** has the closest prior work for exactly this kind of round-trip proof. Its SMT automation keeps proofs short, it can produce OCaml, C or Rust, and it ships official arm64 binaries. Its weakness is that there is no cross-tool benchmark of how well LLMs prove in F\*.
- **Dafny** has the best LLM results and the widest range of compile targets, which helps when integrating into other projects. This review found no prior work on verified parsers in Dafny, and installing it on Linux arm64 takes manual steps.
- **Rocq** has the strongest track record in verified lexing and parsing of textual grammars and a fully deterministic kernel. Proofs need more manual effort, LLM results are weaker, and on arm64 it has to be built from source.
- **Lean 4** checks deterministically and produces native code. It has the strongest ecosystem of LLMs for mathematical proofs, but the lowest vericoding numbers.
- **Verus** integrates well with Rust and has Vest as prior work. It offers no arm64 Linux binaries and sits in the middle on LLM results.

The trade-off is between prior work (F\*) and the evidence that LLMs can write the proofs, together with compile targets in mainstream languages (Dafny). Our proof about textual escaping is new in any of these tools, so F\*'s prior work on binary formats helps less than it first appears. Installing Dafny on Linux arm64 works the same way as on x86_64: .NET 8, `dotnet tool install dafny`, and the `z3` binary from the official `z3-solver` 4.16.0 wheel, which ships a Linux aarch64 build. A hybrid is also possible: prove the SQL layer once in F\* or Rocq, and let application agents work in Dafny. After a [technology experiment](../spikes/q13-dafny-vs-fstar/README.md), Q13 in [INTENT.md](../INTENT.md) chose Dafny.

## 8. Gap and positioning

As of 2026-10-08 we found no work that does any of the following:

1. mechanically prove the extended round-trip property of Hermerschmidt et al. for a textual output language with quoting and escaping, such as SQL, HTML or shell;
2. have LLM agents generate application code together with a machine-checked proof of injection-freedom against a fixed, human-approved theorem;
3. package such a check as a gate that other agents and projects can adopt.

These are the closest neighbours:

| Work | What it has | What it lacks for this project |
|---|---|---|
| McHammerCoder | the property and a generator | no proof; validated by fuzzing |
| EverParse/Vest family | proofs | only binary formats, mostly the parser side |
| 3DGen | AI agents producing verified parsers | only binary formats, input side |
| Ur/Web, SQL DOM | prevention by construction | escaping functions are trusted, not proven |
| SqlCheck, CANDID | checks against injection | at runtime only, no proof |

**Risks identified:**
- **Parser differentials (R5).** SQLite has quirks a parser model must reflect [[sqlitelangexpr](#sqlitelangexpr)]:
  - it interprets a double-quoted string as a string literal if it matches no identifier;
  - text strings may contain NUL characters.

  VUPER and Hermerschmidt et al. (2020) show how a verified parser can serve as a test oracle against the real one.
- **Whether the specification matches the intent** [[lahiri2024fmcad](#lahiri2024fmcad)].
- **Brittle SMT proofs** in F\*, Dafny and Verus.
- **Specification gaming by the agent** [[aggarwal2025alphaverus](#aggarwal2025alphaverus)].
- **Output languages that are themselves executed**, such as HTML with JavaScript, which limits what the sender can guarantee [[hermerschmidt2019dissertation](#hermerschmidt2019dissertation)].

## 9. Implications for the open questions in INTENT.md

- **Q3 (meaning of injection-free)** is confirmed by the primary sources, with one refinement. The round-trip (b) must hold for trees whose data tokens contain *arbitrary* strings, and `parse` includes decoding. Requirement (c) corresponds to McHammerCoder's condition 3.
- **Q7 (first target)**: SQL with SQLite remains the best choice.
  - SQLite's quoting is simple.
  - Su and Wassermann's grammar is a ready starting point.
  - The limit for executable output languages is a further argument against starting with XSS.
- **Q8 (proof tool)**: see section 7. Once the owner answered Q6 ("I don't care in which language"), the recommendation moved from F\* to Dafny. Q13 confirmed Dafny after a technology experiment.
- **Q11 (DevContainer host)**: F\* and Lean have official arm64 builds. Dafny, Rocq and Verus need extra steps.
- **New topics for round 2:**
  - how faithful the parser model is (R5), including SQLite's quirks;
  - checks on the encoding table;
  - nested languages such as `LIKE` (R4);
  - whether untrusted data may ever end up in identifiers.

## References

- <a id="aggarwal2025alphaverus"></a>**[aggarwal2025alphaverus]** Pranjal Aggarwal, Bryan Parno, Sean Welleck. *AlphaVerus: Bootstrapping Formally Verified Code Generation through Self-Improving Translation and Treefinement*. arXiv:2412.06176. 2024. ICML 2025. <https://arxiv.org/abs/2412.06176>
- <a id="arnoldus2011unparser"></a>**[arnoldus2011unparser]** B. J. Arnoldus, M. G.J. van den Brand, A. Serebrenik. *Less is more: unparser-completeness of metalanguages for template engines*. ACM SIGPLAN Notices. 2011. <https://doi.org/10.1145/2189751.2047887>
- <a id="bagge2013formatting"></a>**[bagge2013formatting]** Anya Helene Bagge, Tero Hasu. *A Pretty Good Formatting Pipeline*. Software Language Engineering. 2013. <https://doi.org/10.1007/978-3-319-02654-1_10>
- <a id="bangert2014nail"></a>**[bangert2014nail]** Julian Bangert, Nickolai Zeldovich. *Nail: A Practical Tool for Parsing and Generating Data Formats*. 11th USENIX Symposium on Operating Systems Design and Implementation (OSDI 14). 2014. <https://www.usenix.org/conference/osdi14/technical-sessions/presentation/bangert>
- <a id="bieschke2017mchammercoder"></a>**[bieschke2017mchammercoder]** Tobias Bieschke, Lars Hermerschmidt, Bernhard Rumpe, Peter Stanchev. *Eliminating Input-Based Attacks by Deriving Automated Encoders and Decoders from Context-Free Grammars*. 2017 IEEE Security and Privacy Workshops (SPW). 2017. <https://doi.org/10.1109/spw.2017.32>
- <a id="bisht2010candid"></a>**[bisht2010candid]** Prithvi Bisht, P. Madhusudan, V. N. Venkatakrishnan. *CANDID: Dynamic candidate evaluations for automatic prevention of SQL injection attacks*. ACM Transactions on Information and System Security. 2010. <https://doi.org/10.1145/1698750.1698754>
- <a id="bratus2014frontier"></a>**[bratus2014frontier]** Sergey Bratus, Trey Darley, Michael Locasto, Meredith L. Patterson, Rebecca Bx Shapiro, Anna Shubina. *Beyond Planted Bugs in "Trusting Trust": The Input-Processing Frontier*. IEEE Security & Privacy. 2014. <https://doi.org/10.1109/msp.2014.1>
- <a id="bratus2017curing"></a>**[bratus2017curing]** Sergey Bratus, Lars Hermerschmidt, Sven M. Hallberg, Michael E. Locasto, Falcon D. Momot, Meredith L. Patterson, et al. *Curing the Vulnerable Parser: Design Patterns for Secure Input Handling*. ;login: The USENIX Magazine. 2017. <https://www.usenix.org/publications/login/spring2017/bratus>
- <a id="bravenboer2007stringborg"></a>**[bravenboer2007stringborg]** Martin Bravenboer, Eelco Dolstra, Eelco Visser. *Preventing injection attacks with syntax embeddings*. Proceedings of the 6th international conference on Generative programming and component engineering. 2007. <https://doi.org/10.1145/1289971.1289975>
- <a id="buehrer2005sqlguard"></a>**[buehrer2005sqlguard]** Gregory Buehrer, Bruce W. Weide, Paolo A. G. Sivilotti. *Using parse tree validation to prevent SQL injection attacks*. Proceedings of the 5th international workshop on Software engineering and middleware. 2005. <https://doi.org/10.1145/1108473.1108496>
- <a id="bursuc2025vericoding"></a>**[bursuc2025vericoding]** Sergiu Bursuc, Theodore Ehrenborg, Shaowei Lin, Lacramioara Astefanoaei, Ionel Emilian Chiosa, Jure Kukovec, et al. *A benchmark for vericoding: formally verified program synthesis*. arXiv:2509.22908. 2025. <https://arxiv.org/abs/2509.22908>
- <a id="cai2025vest"></a>**[cai2025vest]** Yi Cai, Pratap Singh, Zhengyao Lin, Jay Bosamiya, Joshua Gancher, Milijana Surbatovich, et al. *Vest: Verified, Secure, High-Performance Parsing and Serialization for Rust*. 34th USENIX Security Symposium (USENIX Security 25). 2025. <https://www.usenix.org/conference/usenixsecurity25/presentation/cai-yi>
- <a id="chakraborty2025fstar"></a>**[chakraborty2025fstar]** Saikat Chakraborty, Gabriel Ebner, Siddharth Bhat, Sarah Fakhoury, Sakina Fatima, Shuvendu Lahiri, et al. *Towards Neural Synthesis for SMT-Assisted Proof-Oriented Programming*. 2025 IEEE/ACM 47th International Conference on Software Engineering (ICSE). 2025. <https://doi.org/10.1109/icse55347.2025.00002>
- <a id="chlipala2015urweb"></a>**[chlipala2015urweb]** Adam Chlipala. *Ur/Web: A Simple Model for Programming the Web*. Proceedings of the 42nd Annual ACM SIGPLAN-SIGACT Symposium on Principles of Programming Languages. 2015. <https://doi.org/10.1145/2676726.2677004>
- <a id="councilman2025astrogator"></a>**[councilman2025astrogator]** Aaron Councilman, David Jiahao Fu, Aryan Gupta, Chengxiao Wang, David Grove, Yu-Xiong Wang, et al. *Towards Formal Verification of LLM-Generated Code from Natural Language Prompts*. arXiv:2507.13290. 2025. <https://arxiv.org/abs/2507.13290>
- <a id="cramer2025marmaragan"></a>**[cramer2025marmaragan]** Marcos Cramer, Lucian McIntyre. *Verifying LLM-Generated Code in the Context of Software Verification with Ada/SPARK*. arXiv:2502.07728. 2025. <https://arxiv.org/abs/2502.07728>
- <a id="dalrymple2024gsai"></a>**[dalrymple2024gsai]** David "davidad" Dalrymple, Joar Skalse, Yoshua Bengio, Stuart Russell, Max Tegmark, Sanjit Seshia, et al. *Towards Guaranteed Safe AI: A Framework for Ensuring Robust and Reliable AI Systems*. arXiv:2405.06624. 2024. <https://arxiv.org/abs/2405.06624>
- <a id="danielsson2013pretty"></a>**[danielsson2013pretty]** Nils Anders Danielsson. *Correct-by-construction pretty-printing*. Proceedings of the 2013 ACM SIGPLAN workshop on Dependently-typed programming. 2013. <https://doi.org/10.1145/2502409.2502410>
- <a id="delaware2019narcissus"></a>**[delaware2019narcissus]** Benjamin Delaware, Sorawit Suriyakarn, Clément Pit-Claudel, Qianchuan Ye, Adam Chlipala. *Narcissus: correct-by-construction derivation of decoders and encoders from binary formats*. Proceedings of the ACM on Programming Languages. 2019. <https://doi.org/10.1145/3341686>
- <a id="demoura2008z3"></a>**[demoura2008z3]** Leonardo de Moura, Nikolaj Bjørner. *Z3: An Efficient SMT Solver*. Tools and Algorithms for the Construction and Analysis of Systems. 2008. <https://doi.org/10.1007/978-3-540-78800-3_24>
- <a id="demoura2021lean4"></a>**[demoura2021lean4]** Leonardo de Moura, Sebastian Ullrich. *The Lean 4 Theorem Prover and Programming Language*. Automated Deduction – CADE 28. 2021. <https://doi.org/10.1007/978-3-030-79876-5_37>
- <a id="egolf2021verbatim"></a>**[egolf2021verbatim]** Derek Egolf, Sam Lasser, Kathleen Fisher. *Verbatim: A Verified Lexer Generator*. 2021 IEEE Security and Privacy Workshops (SPW). 2021. <https://doi.org/10.1109/spw53761.2021.00022>
- <a id="endres2024nl2postcond"></a>**[endres2024nl2postcond]** Madeline Endres, Sarah Fakhoury, Saikat Chakraborty, Shuvendu K. Lahiri. *Can Large Language Models Transform Natural Language Intent into Formal Method Postconditions?*. Proceedings of the ACM on Software Engineering. 2024. <https://doi.org/10.1145/3660791>
- <a id="fakhoury2024ticoder"></a>**[fakhoury2024ticoder]** Sarah Fakhoury, Aaditya Naik, Georgios Sakkas, Saikat Chakraborty, Shuvendu K. Lahiri. *LLM-Based Test-Driven Interactive Code Generation: User Study and Empirical Evaluation*. IEEE Transactions on Software Engineering. 2024. <https://doi.org/10.1109/tse.2024.3428972>
- <a id="fakhoury2025threedgen"></a>**[fakhoury2025threedgen]** Sarah Fakhoury, Markus Kuppe, Shuvendu K. Lahiri, Tahina Ramananandro, Nikhil Swamy. *3DGen: AI-Assisted Generation of Provably Correct Binary Format Parsers*. 2025 IEEE/ACM 47th International Conference on Software Engineering (ICSE). 2025. <https://doi.org/10.1109/icse55347.2025.00173>
- <a id="filliatre2013why3"></a>**[filliatre2013why3]** Jean-Christophe Filliâtre, Andrei Paskevich. *Why3 – Where Programs Meet Provers*. Programming Languages and Systems. 2013. <https://doi.org/10.1007/978-3-642-37036-6_8>
- <a id="first2023baldur"></a>**[first2023baldur]** Emily First, Markus N. Rabe, Talia Ringer, Yuriy Brun. *Baldur: Whole-Proof Generation and Repair with Large Language Models*. Proceedings of the 31st ACM Joint European Software Engineering Conference and Symposium on the Foundations of Software Engineering. 2023. <https://doi.org/10.1145/3611643.3616243>
- <a id="halfond2005amnesia"></a>**[halfond2005amnesia]** William G. J. Halfond, Alessandro Orso. *AMNESIA: analysis and monitoring for NEutralizing SQL-injection attacks*. Proceedings of the 20th IEEE/ACM International Conference on Automated Software Engineering. 2005. <https://doi.org/10.1145/1101908.1101935>
- <a id="hermerschmidt2015unparsers"></a>**[hermerschmidt2015unparsers]** Lars Hermerschmidt, Stephan Kugelmann, Bernhard Rumpe. *Towards More Security in Data Exchange: Defining Unparsers with Context-Sensitive Encoders for Context-Free Grammars*. 2015 IEEE Security and Privacy Workshops. 2015. <https://doi.org/10.1109/spw.2015.29>
- <a id="hermerschmidt2019dissertation"></a>**[hermerschmidt2019dissertation]** Lars Hermerschmidt. *Agile Modellgetriebene Entwicklung von Software Security & Privacy*. RWTH Aachen University. 2019. Aachener Informatik-Berichte, Software Engineering, Band 41, Shaker Verlag, ISBN 978-3-8440-6707-1. <https://www.se-rwth.de/phdtheses/Diss-Hermerschmidt-Agile-Modellgetriebene-Entwicklung-von-Software-Security-and-Privacy.pdf>
- <a id="hermerschmidt2020detection"></a>**[hermerschmidt2020detection]** Lars Hermerschmidt, Andreas Straub, Goran Piskachev. *Language-agnostic Injection Detection*. 2020 IEEE Security and Privacy Workshops (SPW). 2020. <https://doi.org/10.1109/spw50608.2020.00060>
- <a id="hooimeijer2011bek"></a>**[hooimeijer2011bek]** Pieter Hooimeijer, Benjamin Livshits, David Molnar, Prateek Saxena, Margus Veanes. *Fast and Precise Sanitizer Analysis with BEK*. 20th USENIX Security Symposium (USENIX Security 11). 2011. <https://www.usenix.org/conference/usenix-security-11/fast-and-precise-sanitizer-analysis-bek>
- <a id="iddweb"></a>**[iddweb]** intent-driven.dev. *Intent-Driven Development*. 2026. <https://intent-driven.dev/knowledge/intent-driven-development/>
- <a id="jourdan2012lr1"></a>**[jourdan2012lr1]** Jacques-Henri Jourdan, François Pottier, Xavier Leroy. *Validating LR(1) Parsers*. Programming Languages and Systems. 2012. <https://doi.org/10.1007/978-3-642-28869-2_20>
- <a id="kern2014tangled"></a>**[kern2014tangled]** Christoph Kern. *Securing the tangled web*. Communications of the ACM. 2014. <https://doi.org/10.1145/2643134>
- <a id="lahiri2024aiware"></a>**[lahiri2024aiware]** Shuvendu K. Lahiri. *AI-Assisted User Intent Formalization for Programs: Problem and Applications (Invited Talk)*. Proceedings of the 1st ACM International Conference on AI-Powered Software. 2024. <https://doi.org/10.1145/3664646.3676274>
- <a id="lahiri2024fmcad"></a>**[lahiri2024fmcad]** Shuvendu K. Lahiri. *Evaluating LLM-driven User-Intent Formalization for Verification-Aware Languages*. arXiv:2406.09757. 2024. FMCAD 2024. <https://arxiv.org/abs/2406.09757>
- <a id="lasser2019vermillion"></a>**[lasser2019vermillion]** Sam Lasser, Chris Casinghino, Kathleen Fisher, Cody Roux. *A Verified LL(1) Parser Generator*. 10th International Conference on Interactive Theorem Proving (ITP 2019). 2019. <https://doi.org/10.4230/lipics.itp.2019.24>
- <a id="lasser2021costar"></a>**[lasser2021costar]** Sam Lasser, Chris Casinghino, Kathleen Fisher, Cody Roux. *CoStar: a verified ALL(*) parser*. Proceedings of the 42nd ACM SIGPLAN International Conference on Programming Language Design and Implementation. 2021. <https://doi.org/10.1145/3453483.3454053>
- <a id="lattuada2023verus"></a>**[lattuada2023verus]** Andrea Lattuada, Travis Hance, Chanhee Cho, Matthias Brun, Isitha Subasinghe, Yi Zhou, et al. *Verus: Verifying Rust Programs using Linear Ghost Types*. Proceedings of the ACM on Programming Languages. 2023. <https://doi.org/10.1145/3586037>
- <a id="lattuada2024verus"></a>**[lattuada2024verus]** Andrea Lattuada, Travis Hance, Jay Bosamiya, Matthias Brun, Chanhee Cho, Hayley LeBlanc, et al. *Verus: A Practical Foundation for Systems Verification*. Proceedings of the ACM SIGOPS 30th Symposium on Operating Systems Principles. 2024. <https://doi.org/10.1145/3694715.3695952>
- <a id="leino2010dafny"></a>**[leino2010dafny]** K. Rustan M. Leino. *Dafny: An Automatic Program Verifier for Functional Correctness*. Logic for Programming, Artificial Intelligence, and Reasoning. 2010. <https://doi.org/10.1007/978-3-642-17511-4_20>
- <a id="loughridge2024dafnybench"></a>**[loughridge2024dafnybench]** Chloe Loughridge, Qinyi Sun, Seth Ahrenbach, Federico Cassano, Chuyue Sun, Ying Sheng, et al. *DafnyBench: A Benchmark for Formal Software Verification*. arXiv:2406.08467. 2024. <https://arxiv.org/abs/2406.08467>
- <a id="matsuda2013flippr"></a>**[matsuda2013flippr]** Kazutaka Matsuda, Meng Wang. *FliPpr: A Prettier Invertible Printing System*. Programming Languages and Systems. 2013. <https://doi.org/10.1007/978-3-642-37036-6_6>
- <a id="mcclure2005sqldom"></a>**[mcclure2005sqldom]** R.A. McClure, I.H. Kruger. *SQL DOM: compile time checking of dynamic SQL statements*. Proceedings. 27th International Conference on Software Engineering, 2005. ICSE 2005. 2005. <https://doi.org/10.1109/icse.2005.1553551>
- <a id="mchammercoder"></a>**[mchammercoder]** McHammerCoder contributors. *McHammerCoder: (un)parser and encoding generator for textual and binary languages*. GitHub repository. 2017. <https://github.com/McHammerCoder/McHammerCoder>
- <a id="momot2016turrets"></a>**[momot2016turrets]** Falcon Momot, Sergey Bratus, Sven M. Hallberg, Meredith L. Patterson. *The Seven Turrets of Babel: A Taxonomy of LangSec Errors and How to Expunge Them*. 2016 IEEE Cybersecurity Development (SecDev). 2016. <https://doi.org/10.1109/secdev.2016.019>
- <a id="necula1997pcc"></a>**[necula1997pcc]** George C. Necula. *Proof-carrying code*. Proceedings of the 24th ACM SIGPLAN-SIGACT symposium on Principles of programming languages - POPL '97. 1997. <https://doi.org/10.1145/263699.263712>
- <a id="pearce2022copilot"></a>**[pearce2022copilot]** Hammond Pearce, Baleegh Ahmad, Benjamin Tan, Brendan Dolan-Gavitt, Ramesh Karri. *Asleep at the Keyboard? Assessing the Security of GitHub Copilot's Code Contributions*. 2022 IEEE Symposium on Security and Privacy (SP). 2022. <https://doi.org/10.1109/sp46214.2022.9833571>
- <a id="perry2023insecure"></a>**[perry2023insecure]** Neil Perry, Megha Srivastava, Deepak Kumar, Dan Boneh. *Do Users Write More Insecure Code with AI Assistants?*. Proceedings of the 2023 ACM SIGSAC Conference on Computer and Communications Security. 2023. <https://doi.org/10.1145/3576915.3623157>
- <a id="protzenko2017lowstar"></a>**[protzenko2017lowstar]** Jonathan Protzenko, Jean-Karim Zinzindohoué, Aseem Rastogi, Tahina Ramananandro, Peng Wang, Santiago Zanella-Béguelin, et al. *Verified low-level programming embedded in F**. Proceedings of the ACM on Programming Languages. 2017. <https://doi.org/10.1145/3110261>
- <a id="ramananandro2019everparse"></a>**[ramananandro2019everparse]** Tahina Ramananandro, Antoine Delignat-Lavaud, Cédric Fournet, Nikhil Swamy, Tej Chajed, Nadim Kobeissi, et al. *EverParse: Verified Secure Zero-Copy Parsers for Authenticated Message Formats*. 28th USENIX Security Symposium (USENIX Security 19). 2019. <https://www.usenix.org/conference/usenixsecurity19/presentation/delignat-lavaud>
- <a id="ramananandro2025pulseparse"></a>**[ramananandro2025pulseparse]** Tahina Ramananandro, Gabriel Ebner, Guido Martínez, Nikhil Swamy. *Secure Parsing and Serializing with Separation Logic Applied to CBOR, CDDL, and COSE*. Proceedings of the 2025 ACM SIGSAC Conference on Computer and Communications Security. 2025. <https://doi.org/10.1145/3719027.3765120>
- <a id="ray2012defining"></a>**[ray2012defining]** Donald Ray, Jay Ligatti. *Defining code-injection attacks*. ACM SIGPLAN Notices. 2012. <https://doi.org/10.1145/2103621.2103678>
- <a id="rendel2010invertible"></a>**[rendel2010invertible]** Tillmann Rendel, Klaus Ostermann. *Invertible syntax descriptions: unifying parsing and pretty printing*. Proceedings of the third ACM Haskell symposium on Haskell. 2010. <https://doi.org/10.1145/1863523.1863525>
- <a id="sabelfeld2003ifc"></a>**[sabelfeld2003ifc]** A. Sabelfeld, A.C. Myers. *Language-based information-flow security*. IEEE Journal on Selected Areas in Communications. 2003. <https://doi.org/10.1109/jsac.2002.806121>
- <a id="samuel2011autosanitization"></a>**[samuel2011autosanitization]** Mike Samuel, Prateek Saxena, Dawn Song. *Context-sensitive auto-sanitization in web templating languages using type qualifiers*. Proceedings of the 18th ACM conference on Computer and communications security. 2011. <https://doi.org/10.1145/2046707.2046775>
- <a id="sassaman2011halting"></a>**[sassaman2011halting]** Len Sassaman, Meredith L. Patterson, Sergey Bratus, Anna Shubina. *The Halting Problems of Network Stack Insecurity*. ;login: The USENIX Magazine. 2011.
- <a id="sassaman2013formal"></a>**[sassaman2013formal]** Len Sassaman, Meredith L. Patterson, Sergey Bratus, Michael E. Locasto. *Security Applications of Formal Language Theory*. IEEE Systems Journal. 2013. <https://doi.org/10.1109/jsyst.2012.2222000>
- <a id="saxena2011scriptgard"></a>**[saxena2011scriptgard]** Prateek Saxena, David Molnar, Benjamin Livshits. *SCRIPTGARD: automatic context-sensitive sanitization for large-scale legacy web applications*. Proceedings of the 18th ACM conference on Computer and communications security. 2011. <https://doi.org/10.1145/2046707.2046776>
- <a id="speckit2025"></a>**[speckit2025]** Den Delimarsky. *Spec-driven development with AI: Get started with a new open source toolkit*. The GitHub Blog. 2025. <https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/>
- <a id="sqlitelangexpr"></a>**[sqlitelangexpr]** SQLite Project. *SQL Language Expressions (literal values) and Quirks, Caveats, and Gotchas in SQLite*. 2026. <https://www.sqlite.org/lang_expr.html>
- <a id="sternfeld2025typepilot"></a>**[sternfeld2025typepilot]** Alexander Sternfeld, Andrei Kucharavy, Ljiljana Dolamic. *TypePilot: Leveraging the Scala Type System for Secure LLM-generated Code*. arXiv:2510.11151. 2025. <https://arxiv.org/abs/2510.11151>
- <a id="su2006essence"></a>**[su2006essence]** Zhendong Su, Gary Wassermann. *The essence of command injection attacks in web applications*. ACM SIGPLAN Notices. 2006. <https://doi.org/10.1145/1111320.1111070>
- <a id="sun2024clover"></a>**[sun2024clover]** Chuyue Sun, Ying Sheng, Oded Padon, Clark Barrett. *Clover: Closed-Loop Verifiable Code Generation*. AI Verification. 2024. <https://doi.org/10.1007/978-3-031-65112-0_7>
- <a id="swamy2016fstar"></a>**[swamy2016fstar]** Nikhil Swamy, Cătălin Hriţcu, Chantal Keller, Aseem Rastogi, Antoine Delignat-Lavaud, Simon Forest, et al. *Dependent types and multi-monadic effects in F**. ACM SIGPLAN Notices. 2016. <https://doi.org/10.1145/2914770.2837655>
- <a id="swamy2022everparse3d"></a>**[swamy2022everparse3d]** Nikhil Swamy, Tahina Ramananandro, Aseem Rastogi, Irina Spiridonova, Haobin Ni, Dmitry Malloy, et al. *Hardening attack surfaces with formally proven binary format parsers*. Proceedings of the 43rd ACM SIGPLAN International Conference on Programming Language Design and Implementation. 2022. <https://doi.org/10.1145/3519939.3523708>
- <a id="thompson2025rango"></a>**[thompson2025rango]** Kyle Thompson, Nuno Saavedra, Pedro Carrott, Kevin Fisher, Alex Sanchez-Stern, Yuriy Brun, et al. *Rango: Adaptive Retrieval-Augmented Proving for Automated Software Verification*. 2025 IEEE/ACM 47th International Conference on Software Engineering (ICSE). 2025. <https://doi.org/10.1109/icse55347.2025.00161>
- <a id="tripp2009taj"></a>**[tripp2009taj]** Omer Tripp, Marco Pistoia, Stephen J. Fink, Manu Sridharan, Omri Weisman. *TAJ: effective taint analysis of web applications*. Proceedings of the 30th ACM SIGPLAN Conference on Programming Language Design and Implementation. 2009. <https://doi.org/10.1145/1542476.1542486>
- <a id="vero2025baxbench"></a>**[vero2025baxbench]** Mark Vero, Niels Mündler, Victor Chibotaru, Veselin Raychev, Maximilian Baader, Nikola Jovanović, et al. *BaxBench: Can LLMs Generate Correct and Secure Backends?*. arXiv:2502.11844. 2025. ICML 2025. <https://arxiv.org/abs/2502.11844>
- <a id="wallez2023comparse"></a>**[wallez2023comparse]** Théophile Wallez, Jonathan Protzenko, Karthikeyan Bhargavan. *Comparse: Provably Secure Formats for Cryptographic Protocols*. Proceedings of the 2023 ACM SIGSAC Conference on Computer and Communications Security. 2023. <https://doi.org/10.1145/3576915.3623201>
- <a id="wassermann2007sound"></a>**[wassermann2007sound]** Gary Wassermann, Zhendong Su. *Sound and precise analysis of web applications for injection vulnerabilities*. ACM SIGPLAN Notices. 2007. <https://doi.org/10.1145/1273442.1250739>
- <a id="weinberger2011xss"></a>**[weinberger2011xss]** Joel Weinberger, Prateek Saxena, Devdatta Akhawe, Matthew Finifter, Richard Shin, Dawn Song. *A Systematic Analysis of XSS Sanitization in Web Application Frameworks*. Computer Security – ESORICS 2011. 2011. <https://doi.org/10.1007/978-3-642-23822-2_9>
- <a id="wu2024lemur"></a>**[wu2024lemur]** Haoze Wu, Clark Barrett, Nina Narodytska. *Lemur: Integrating Large Language Models in Automated Program Verification*. arXiv:2310.04870. 2023. ICLR 2024. <https://arxiv.org/abs/2310.04870>
- <a id="yang2025autoverus"></a>**[yang2025autoverus]** Chenyuan Yang, Xuheng Li, Md Rakib Hossain Misu, Jianan Yao, Weidong Cui, Yeyun Gong, et al. *AutoVerus: Automated Proof Generation for Rust Code*. Proceedings of the ACM on Programming Languages. 2025. <https://doi.org/10.1145/3763174>
- <a id="ye2025verina"></a>**[ye2025verina]** Zhe Ye, Zhengxu Yan, Jingxuan He, Timothe Kasriel, Kaiyu Yang, Dawn Song. *VERINA: Benchmarking Verifiable Code Generation*. arXiv:2505.23135. 2025. <https://arxiv.org/abs/2505.23135>
- <a id="zaytsev2014parsing"></a>**[zaytsev2014parsing]** Vadim Zaytsev, Anya Helene Bagge. *Parsing in a Broad Sense*. Model-Driven Engineering Languages and Systems. 2014. <https://doi.org/10.1007/978-3-319-11653-2_4>
- <a id="zhao2026algoveri"></a>**[zhao2026algoveri]** Haoyu Zhao, Ziran Yang, Jiawei Li, Deyuan He, Zenan Li, Chi Jin, et al. *AlgoVeri: An Aligned Benchmark for Verified Code Generation on Classical Algorithms*. arXiv:2602.09464. 2026. Accepted to ICML 2026. <https://arxiv.org/abs/2602.09464>
- <a id="zhou2026vuper"></a>**[zhou2026vuper]** Xiaotian Zhou, Kai Tu, Ali Ranjbar, Yilu Dong, Gang Tan, Syed Rafiul Hussain. *VUPER: Verified ASN.1 UPER Parser*. arXiv:2608.09094. 2026. Extended version of a paper accepted to ACM CCS 2026. <https://arxiv.org/abs/2608.09094>
