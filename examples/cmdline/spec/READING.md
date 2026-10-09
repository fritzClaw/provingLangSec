# Reading of the cmdline specification (for owner approval)

**The language (`CmdLang.dfy`).** Scripts are commands separated by `; `. A command is a lowercase word and quoted arguments. Inside an argument, `\"` is a quote and `\\` is a backslash. Free text can only appear inside an argument.

**The theorem (`CmdTheorem.dfy`, proved by the agent in `src/CmdProof.dfy`).** For every script, parsing its unparsed text returns the same script, even if arguments contain quotes, backslashes or semicolons. So a receiver that parses like the model cannot be made to see an extra command.

**The application (`CmdAppSpec.dfy`).** `Store(note)` returns exactly the text of `put "note" "<note>"; get "note"` for the untrusted note.

**What it does not cover.** That the toy interpreter (`glue/interp.py`) parses like `CmdLang.Parse`: tested by `tests/test_cmdline.py` (random scripts and thousands of mutated texts compared with the model), not proven. For a custom interpreter that you control, the better fix is to compile the verified parser into it.
