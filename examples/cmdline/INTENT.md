# Intent: `cmdline`, a custom command language (generality check)

*Generality check for the approach (decision Q24): a non-SQL, non-standard output language with a different escaping style, an interpreter that is not SQLite, and its own exploit.*

## What the app does

A program stores a note given by an untrusted user and reads it back. It does so by sending a small script, written in a custom command language, to a toy interpreter:

    put "note" "<the user's text>"; get "note"

The interpreter has three commands: `put "key" "value"` stores a value, `get "key"` prints it, and `grant "user"` gives that user admin rights. The application must never be able to send `grant`.

## The language

A script is one or more commands separated by `; `. A command is a lowercase word followed by zero or more quoted arguments, each preceded by a space. Inside an argument, a backslash escapes the next character: `\"` is a quote and `\\` is a backslash.

## Untrusted input

The note text. It may contain quotes, backslashes, semicolons and anything else (except NUL).

## What the application may send

Exactly `put "note" "<text>"; get "note"`, with the untrusted text appearing only as the content of the second argument of `put`.

## The exploit to defeat

The text `x"; grant "mallory` must be stored as a note, not run as a command.
