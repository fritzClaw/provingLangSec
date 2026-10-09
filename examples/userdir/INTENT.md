# Intent: `userdir`, a command-line user directory

*Application intent, written in plain English. It is the input of `make agent`.*

## What the app does

`userdir search <name>` prints the name and email address of every user whose name is exactly `<name>`, one per line, separated by a tab. It reads a small SQLite database that also holds a `secret` column for each user. The secret must never be shown.

## Untrusted input

The `<name>` argument comes from an untrusted user. It may contain any characters, including quotes, SQL keywords and comment markers. NUL characters are rejected before the app sees them.

## The query the app may issue

Exactly one query shape, with the untrusted name appearing only as a text literal:

```sql
SELECT "name", "email" FROM "users" WHERE ("name" = '<name>')
```

The app may not select the `secret` column, may not use another table, and may not let the name change anything but the literal. The formal version of this paragraph is `spec/UserdirSpec.dfy`; the owner approves it before any implementation is written.

## Examples

| Command | Output |
|---|---|
| `userdir search alice` | `alice<TAB>alice@example.org` |
| `userdir search "o'brien"` | `o'brien<TAB>obrien@example.org` |
| `userdir search nobody` | *(nothing)* |
| `userdir search "x') UNION SELECT secret, email FROM users --"` | *(nothing)*: the whole argument is just a name that matches nobody |
