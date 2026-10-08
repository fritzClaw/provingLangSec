# Receiver-parser fidelity: options and their precision (Q17)

*2026-10-08.* This analysis supports open question Q17 in [INTENT.md](../../INTENT.md).

## The problem

The central theorem (R1) proves `parse_model(unparse(t)) = t`, where `parse_model` is *our formal model* of the receiver's parser. The guarantee carries over to the running system only if the real receiver, here SQLite, parses every text our unparser can emit the same way the model does. That is requirement R5 of the [literature review](../literature-review.md). Hermerschmidt et al. call the alternative "an idealized world, where unparsers and parsers are generated from the same grammar" [[hermerschmidt2015unparsers](#hermerschmidt2015unparsers)].

## How precise an option can be

| Level | Meaning |
|---|---|
| **A: proven** | The assumption is eliminated or itself proven. |
| **B: exact oracle** | Tests compare our model with the real parser's *own* tokens or parse trees. This is strong evidence, but limited to the inputs tested. |
| **C: indirect oracle** | Tests compare observable behaviour only, such as query results or bytecode. Both false alarms and misses are possible. |
| **D: assumed** | Nothing is checked. |

## Facts about SQLite (checked 2026-10-08)

- **Grammar.** SQLite's grammar is explicit: `src/parse.y` is a Lemon LALR(1) grammar with 417 rules [[sqliteparsey](#sqliteparsey), [sqlitedocsfidelity](#sqlitedocsfidelity)].
  - It has precedence declarations.
  - Its `%fallback ID` lets many keywords act as identifiers.
- **Tokenizer.** The tokenizer is hand-written C (`sqlite3GetToken` in `src/tokenize.c`).
  - String literals use quote doubling.
  - Tokens quoted with `"` or `` ` `` become identifiers.
  - Scanning stops at a NUL byte.
  - This is where injections happen, and it is not part of `parse.y`.
- **Double-quoted strings.** The misfeature that turns an unknown double-quoted name into a string happens *after* parsing, during name resolution (`src/resolve.c`).
  - It can be switched off per connection with `SQLITE_DBCONFIG_DQS_DML`. Python 3.12+ exposes this as `Connection.setconfig`.
  - With it switched off, `SELECT "nosuchcol" FROM users` fails with "no such column" instead of returning a string. Verified with SQLite 3.45.1.
- **NUL.** Python's `sqlite3` refuses SQL text that contains NUL, so such input fails closed (see the [Q13 spike](../../spikes/q13-dafny-vs-fstar/README.md)).
- **Debug builds** (`SQLITE_DEBUG`) offer two views into the parser:
  - `PRAGMA parser_trace` traces the steps of the generated parser;
  - the TreeView routines in `src/treeview.c` print SQLite's internal parse trees.
- **Test suites.**
  - The TCL test suite is public domain.
  - TH3, which reaches 100% branch and MC/DC coverage, is proprietary.
  - The SQL Logic Test compares SQLite's answers with other database engines.
- **Black-box comparison is unreliable.** The spike showed that `EXPLAIN` bytecode is an imprecise oracle: SQLite's optimizer merges identical `WHERE` terms, so the bytecode depends on literal values.

## Options

Options marked "owner" were named by the owner; the others were added in this analysis.

| # | Option | What it establishes | Precision | Effort | Applies to |
|---|---|---|---|---|---|
| 1 | **Keep data out of the parser**: prepared statements with parameter binding | Untrusted data never reaches SQLite's tokenizer or parser. Only the SQL text skeleton is parsed, and that skeleton does not depend on untrusted input. The remaining assumption is the binding API, which parses nothing. | **A** for injection-freedom | low | only receivers with a separate data channel (SQL drivers, process `argv`). Not HTML, shell strings or most custom languages. |
| 2 | **Receiver uses our verified parser**, generated from the same language definition | Hermerschmidt's idealized world becomes real: both sides use one definition. | **A** | low for your own or custom interpreters | custom languages. Not SQLite without replacing its parser. |
| 3 | **Validate SQLite's generated parser against `parse.y`**, as Jourdan et al. do for Menhir [[jourdan2012lr1](#jourdan2012lr1)], and run that automaton inside the model. The tokenizer is verified with a C verifier or tested exhaustively up to a bounded length. | The model's parser *is* SQLite's automaton. | **A** for the parser; **B** for the tokenizer unless it is verified | high | any receiver with a generated parser |
| 4 | **Instrument SQLite** (owner option 3): `parser_trace`, TreeView and tokenizer hooks yield SQLite's exact tokens and parse trees, which drive differential tests, including exhaustive tests of literal lexing up to a bounded length | Agreement with the real parser's own output on everything tested. | **B** | medium | any receiver whose source can be instrumented |
| 5 | **Take the grammar from `parse.y`** (owner option 1a), translating the subset mechanically | Grammar-level fidelity by construction for the subset. The tokenizer and post-parse rewrites are not covered. | **B** (needs 4 for the tokenizer) | medium | receivers with an explicit grammar |
| 6 | **Rewrite SQLite to expose a parse tree** (owner option 2) and keep its tests passing | SQLite already builds an AST and has a debug printer, so no rewrite is needed just to obtain trees. A full rewrite would be validated only by the public TCL tests, because TH3 is proprietary. | **B** (tests, not proof) | very high | — |
| 7 | **Infer the grammar** (owner option 1b), with Autogram, Mimid, Arvada or Glade [[hoschele2016autogram](#hoschele2016autogram), [gopinath2020mimid](#gopinath2020mimid), [kulkarni2021arvada](#kulkarni2021arvada), [bastani2017glade](#bastani2017glade)] | A grammar generalized from samples, which can be too broad or too narrow. | **C** | medium | languages without any grammar |
| 8 | **Hand-written model plus black-box tests** (the round-2 proposal), comparing results, literal decoding and `EXPLAIN` | Indirect agreement; `EXPLAIN` gives false alarms. | **C** | low | any |

Two further techniques strengthen options 4 and 5:
- Use a verified parser as a test oracle against the real one, as VUPER does for ASN.1 [[zhou2026vuper](#zhou2026vuper)].
- Compare parse trees across an unparser–parser round-trip, as Hermerschmidt et al. do [[hermerschmidt2020detection](#hermerschmidt2020detection)].

## Recommendation

- **SQLite in the prototype: options 5 + 4 as the main line (level B), plus option 1 as a second variant (level A).**
  - The main line uses the general unparser approach, which works for every output language.
  - The double-quote misfeature is switched off and NUL is rejected, so neither quirk is part of the trusted assumptions any more.
  - Option 1 shows, for comparison, how much stronger the guarantee becomes when the receiver offers a separate data channel.
- **Custom languages: option 2 (level A).** The interpreter embeds the verified parser generated from the same language definition, so no fidelity gap exists at all.
- **Future work: option 3.** It would lift SQLite's parser to level A.
- **Not recommended:**
  - option 6, because of very high effort for test-level assurance only;
  - option 7 for SQLite, because the explicit grammar already exists. Grammar inference stays a candidate for custom languages that have no grammar.

## References

- <a id="bastani2017glade"></a>**[bastani2017glade]** Osbert Bastani, Rahul Sharma, Alex Aiken, Percy Liang. *Synthesizing program input grammars*. ACM SIGPLAN Notices. 2017. <https://doi.org/10.1145/3140587.3062349>
- <a id="gopinath2020mimid"></a>**[gopinath2020mimid]** Rahul Gopinath, Björn Mathis, Andreas Zeller. *Mining input grammars from dynamic control flow*. Proceedings of the 28th ACM Joint Meeting on European Software Engineering Conference and Symposium on the Foundations of Software Engineering. 2020. <https://doi.org/10.1145/3368089.3409679>
- <a id="hermerschmidt2015unparsers"></a>**[hermerschmidt2015unparsers]** Lars Hermerschmidt, Stephan Kugelmann, Bernhard Rumpe. *Towards More Security in Data Exchange: Defining Unparsers with Context-Sensitive Encoders for Context-Free Grammars*. 2015 IEEE Security and Privacy Workshops. 2015. <https://doi.org/10.1109/spw.2015.29>
- <a id="hermerschmidt2020detection"></a>**[hermerschmidt2020detection]** Lars Hermerschmidt, Andreas Straub, Goran Piskachev. *Language-agnostic Injection Detection*. 2020 IEEE Security and Privacy Workshops (SPW). 2020. <https://doi.org/10.1109/spw50608.2020.00060>
- <a id="hoschele2016autogram"></a>**[hoschele2016autogram]** Matthias Höschele, Andreas Zeller. *Mining input grammars from dynamic taints*. Proceedings of the 31st IEEE/ACM International Conference on Automated Software Engineering. 2016. <https://doi.org/10.1145/2970276.2970321>
- <a id="jourdan2012lr1"></a>**[jourdan2012lr1]** Jacques-Henri Jourdan, François Pottier, Xavier Leroy. *Validating LR(1) Parsers*. Programming Languages and Systems. 2012. <https://doi.org/10.1007/978-3-642-28869-2_20>
- <a id="kulkarni2021arvada"></a>**[kulkarni2021arvada]** Neil Kulkarni, Caroline Lemieux, Koushik Sen. *Learning Highly Recursive Input Grammars*. 2021 36th IEEE/ACM International Conference on Automated Software Engineering (ASE). 2021. <https://doi.org/10.1109/ase51524.2021.9678879>
- <a id="sqlitedocsfidelity"></a>**[sqlitedocsfidelity]** SQLite Project. *PRAGMA parser\_trace; How SQLite Is Tested; TH3; The Lemon LALR(1) Parser Generator*. 2026. <https://www.sqlite.org/testing.html>
- <a id="sqliteparsey"></a>**[sqliteparsey]** SQLite Project. *SQLite source: src/parse.y (Lemon LALR(1) grammar), src/tokenize.c (tokenizer), src/resolve.c (name resolution), src/treeview.c (parse-tree printer)*. 2026. <https://sqlite.org/src/file?name=src/parse.y>
- <a id="zhou2026vuper"></a>**[zhou2026vuper]** Xiaotian Zhou, Kai Tu, Ali Ranjbar, Yilu Dong, Gang Tan, Syed Rafiul Hussain. *VUPER: Verified ASN.1 UPER Parser*. arXiv:2608.09094. 2026. Extended version of a paper accepted to ACM CCS 2026. <https://arxiv.org/abs/2608.09094>

BibTeX for all entries: [`../references.bib`](../references.bib).
