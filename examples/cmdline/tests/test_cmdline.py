"""Functional, exploit and model-fidelity tests for cmdline. FROZEN.

Run:  python3 -I test_cmdline.py --build DIR [--expect-leak]
  --expect-leak   only the exploit test, which must SUCCEED (vulnerable variant)
"""
import os
import random
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GLUE = os.path.join(HERE, "..", "glue")
sys.path.insert(0, GLUE)
import interp  # noqa: E402

BUILD = None
EXPECT_LEAK = False
EXPLOIT = 'x"; grant "mallory'


def run_cli(note):
    return subprocess.run([sys.executable, "-I", os.path.join(GLUE, "cmdline.py"), "--build", BUILD, "run", note],
                          capture_output=True, text=True, encoding="utf-8")


class CmdlineTest(unittest.TestCase):
    def test_plain_note(self):
        r = run_cli("hello")
        self.assertEqual((r.returncode, r.stdout.splitlines()[1:]), (0, ["get: hello", "admins: []"]))

    def test_special_characters_are_stored_literally(self):
        for note in ['say "hi"', "back\\slash", "a; b", 'q"; get "note', "é😀", "", "\\", '"', '\\"']:
            with self.subTest(note=note):
                r = run_cli(note)
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertEqual(r.stdout.splitlines()[1:], ["get: " + note, "admins: []"])

    def test_nul_is_rejected_before_the_app(self):
        sys.path.insert(0, GLUE)
        import cmdline
        self.assertIsNotNone(cmdline.check_data("a\x00b"))
        self.assertIsNone(cmdline.check_data("fine"))

    def test_exploit(self):
        r = run_cli(EXPLOIT)
        if EXPECT_LEAK:
            self.assertIn("mallory", r.stdout.splitlines()[-1], "the exploit should grant admin rights in the vulnerable variant")
        else:
            self.assertEqual((r.returncode, r.stdout.splitlines()[1:]), (0, ["get: " + EXPLOIT, "admins: []"]))


class ModelFidelityTest(unittest.TestCase):
    """The model (Dafny Parse) and the hand-written interpreter must read every text the same way."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, BUILD)
        import _dafny, CmdLang, Prelude
        cls.d, cls.L, cls.P = _dafny, CmdLang, Prelude

    def s(self, text):
        return self.d.SeqWithoutIsStrInference(map(self.d.CodePoint, text))

    def to_dafny(self, script):
        L = self.L
        return self.d.SeqWithoutIsStrInference([L.Cmd_Cmd(self.s(n), self.d.SeqWithoutIsStrInference(map(self.s, a))) for n, a in script])

    def unparse(self, script):
        return self.L.default__.Unparse(self.to_dafny(script)).VerbatimString(False)

    def model_parse(self, text):
        r = self.L.default__.Parse(self.s(text))
        if r.is_None:
            return None
        return [(c.name.VerbatimString(False), [a.VerbatimString(False) for a in c.args]) for c in r.value]

    @staticmethod
    def interp_parse(text):
        try:
            return interp.parse(text)
        except interp.ParseError:
            return None

    PIECES = ['"', "\\", ";", "; ", " ", "a", "put", 'put "', "é", "😀", "\n", "grant", '"; ']

    def rand_data(self, rng):
        return "".join(rng.choice(self.PIECES) for _ in range(rng.randint(0, 5)))

    def rand_script(self, rng):
        return [(rng.choice(["put", "get", "grant", "x_y"]), [self.rand_data(rng) for _ in range(rng.randint(0, 3))])
                for _ in range(rng.randint(1, 4))]

    def test_round_trip_in_the_interpreter(self):
        rng = random.Random(1)
        for _ in range(3000):
            script = self.rand_script(rng)
            text = self.unparse(script)
            self.assertEqual(self.interp_parse(text), script, text)
            self.assertEqual(self.model_parse(text), script, text)

    def test_model_and_interpreter_agree_on_mutated_texts(self):
        rng = random.Random(2)
        agree = 0
        for _ in range(20000):
            text = list(self.unparse(self.rand_script(rng)))
            for _ in range(rng.randint(1, 3)):
                k = rng.randrange(3)
                pos = rng.randrange(len(text) + 1)
                if k == 0:
                    text.insert(pos, rng.choice(self.PIECES))
                elif k == 1 and text:
                    del text[min(pos, len(text) - 1)]
                elif text:
                    text[min(pos, len(text) - 1)] = rng.choice(self.PIECES)
            text = "".join(text)
            self.assertEqual(self.model_parse(text), self.interp_parse(text), repr(text))
            agree += 1
        self.assertEqual(agree, 20000)


if __name__ == "__main__":
    args = sys.argv[1:]
    BUILD = os.path.abspath(args[args.index("--build") + 1])
    EXPECT_LEAK = "--expect-leak" in args
    only = ["CmdlineTest.test_exploit"] if EXPECT_LEAK else []
    unittest.main(argv=[sys.argv[0], "-v", *only])
