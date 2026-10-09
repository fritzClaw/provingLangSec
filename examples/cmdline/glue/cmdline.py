"""Command-line glue for the cmdline example. FROZEN; part of the trusted computing base.

Usage:  cmdline.py --build DIR run NOTE
Builds the script with the Dafny-compiled `CmdApp.Store`, runs it in the toy interpreter and
prints the script, the output and the list of users that were granted admin rights.
Rejects input that is not valid Unicode or contains NUL (the proof's `Data` type excludes NUL).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import interp  # noqa: E402


def check_data(text):
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return "input rejected: not valid Unicode text"
    if "\x00" in text:
        return "input rejected: NUL character"
    return None


def main(argv):
    ap = argparse.ArgumentParser(prog="cmdline")
    ap.add_argument("--build", required=True)
    ap.add_argument("cmd", choices=["run"])
    ap.add_argument("note")
    a = ap.parse_args(argv)
    problem = check_data(a.note)
    if problem:
        print(problem, file=sys.stderr)
        return 2
    sys.path.insert(0, os.path.abspath(a.build))
    import _dafny
    import CmdApp
    script = CmdApp.default__.Store(_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, a.note))).VerbatimString(False)
    it = interp.Interpreter()
    it.run(script)
    print("script:", script)
    for line in it.output:
        print("get:", line)
    print("admins:", it.admins)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
