"""Toy interpreter for the command language. FROZEN; part of the trusted computing base.

This is the RECEIVER: a hand-written parser, deliberately not generated from the Dafny
model. tests/test_cmdline.py checks that it agrees with the model on thousands of scripts
and mutated texts. For a custom interpreter you control, a stronger option is to compile the
verified parser into it, which removes this gap.

Commands:  put "key" "value"   stores a value
           get "key"           prints the stored value
           grant "user"        gives the user admin rights   (the command an attacker wants)
"""


class ParseError(ValueError):
    pass


def parse(text):
    """Return [(name, [args])]. Strict: accepts exactly the canonical text of the grammar."""
    n, i, cmds = len(text), 0, []
    while True:
        j = i
        while j < n and ("a" <= text[j] <= "z" or text[j] == "_"):
            j += 1
        if j == i:
            raise ParseError(f"command word expected at {i}")
        name, args, i = text[i:j], [], j
        while text.startswith(' "', i):
            i += 2
            buf = []
            while True:
                if i >= n:
                    raise ParseError("unterminated argument")
                c = text[i]
                if c == '"':
                    i += 1
                    break
                if c == "\\":
                    if i + 1 < n and text[i + 1] in '"\\':
                        buf.append(text[i + 1]); i += 2; continue
                    raise ParseError("bad escape")
                buf.append(c); i += 1
            arg = "".join(buf)
            if "\x00" in arg:
                raise ParseError("NUL in argument")
            args.append(arg)
        cmds.append((name, args))
        if text.startswith("; ", i):
            i += 2
            continue
        if i == n:
            return cmds
        raise ParseError(f"unexpected text at {i}")


class Interpreter:
    def __init__(self):
        self.notes, self.admins, self.output = {}, [], []

    def run(self, text):
        for name, args in parse(text):
            if name == "put" and len(args) == 2:
                self.notes[args[0]] = args[1]
            elif name == "get" and len(args) == 1:
                self.output.append(self.notes.get(args[0], ""))
            elif name == "grant" and len(args) == 1:
                self.admins.append(args[0])
            else:
                raise ParseError(f"unknown command {name!r} with {len(args)} argument(s)")
