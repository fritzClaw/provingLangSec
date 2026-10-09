"""Fast unit tests for the gate's scanner and manifest logic (no Dafny needed)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate  # noqa: E402


class ScanTests(unittest.TestCase):
    def found(self, code):
        return gate.scan_text(code, "t.dfy")

    def test_clean(self):
        self.assertEqual(self.found("method M() { assert 1 + 1 == 2; }"), [])

    def test_assume(self):
        self.assertTrue(self.found("method M() { assume false; }"))

    def test_attributes(self):
        for attr in ("axiom", "verify false", "extern \"x\"", "rlimit 0", "timeLimit 0", "vcs_max_cost 0", "nowarn"):
            with self.subTest(attr):
                self.assertTrue(self.found("lemma {:%s} L() ensures false" % attr))

    def test_decreases_star(self):
        self.assertTrue(self.found("method M() decreases * { }"))

    def test_allowed_proof_hints(self):
        self.assertEqual(self.found("lemma {:induction n} L(n: nat) {}\nfunction {:opaque} f(): int { 1 }"), [])

    def test_comments_and_strings_are_not_code(self):
        self.assertEqual(self.found('// assume x\n/* {:axiom} */ method M() { var s := "assume {:axiom}"; }'), [])

    def test_nested_block_comment(self):
        self.assertEqual(self.found("/* outer /* inner */ assume still-comment */ method M() {}"), [])

    def test_code_after_char_literal_quote_is_still_scanned(self):
        # A scanner that mistakes '"' for the start of a string would hide the assume below.
        self.assertTrue(self.found("method M() { var c := '\"'; assume false; var d := '\"'; }"))

    def test_prime_in_identifier_is_not_a_char_literal(self):
        self.assertTrue(self.found("method M(rest': int) { assume rest' > 0; }"))

    def test_escaped_quote_char(self):
        self.assertTrue(self.found("method M() { var c := '\\''; assume false; }"))

    def test_string_with_escaped_quote(self):
        self.assertTrue(self.found('method M() { var s := "a\\"b"; assume false; }'))

    def test_unterminated_string_fails_closed(self):
        self.assertTrue(self.found('method M() { var s := "oops; assume false; }'))

    def test_unterminated_comment_fails_closed(self):
        self.assertTrue(self.found("method M() {} /* never closed assume"))


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "spec").mkdir()
        (self.root / "gate").mkdir()
        (self.root / "spec" / "a.dfy").write_text("module A {}")
        self._old = (gate.ROOT, gate.MANIFEST)
        gate.ROOT, gate.MANIFEST = self.root, self.root / "gate" / "manifest.json"

    def tearDown(self):
        gate.ROOT, gate.MANIFEST = self._old
        self.tmp.cleanup()

    def write_manifest(self, status="approved"):
        gate.MANIFEST.write_text(json.dumps({
            "version": 1, "approval": {"status": status}, "frozen_roots": ["spec"],
            "files": {"spec/a.dfy": gate.sha256(self.root / "spec" / "a.dfy")}}))

    def check(self, allow=False):
        rep = gate.Report()
        gate.check_manifest(rep, allow)
        return rep

    def test_matching_manifest_passes(self):
        self.write_manifest()
        self.assertTrue(self.check().ok)

    def test_changed_file_fails(self):
        self.write_manifest()
        (self.root / "spec" / "a.dfy").write_text("module A { /* weakened */ }")
        self.assertFalse(self.check().ok)

    def test_new_file_in_frozen_dir_fails(self):
        self.write_manifest()
        (self.root / "spec" / "b.dfy").write_text("module B {}")
        self.assertFalse(self.check().ok)

    def test_missing_file_fails(self):
        self.write_manifest()
        (self.root / "spec" / "a.dfy").unlink()
        self.assertFalse(self.check().ok)

    def test_proposed_manifest_needs_flag(self):
        self.write_manifest("proposed")
        self.assertFalse(self.check().ok)
        self.assertTrue(self.check(allow=True).ok)

    def test_missing_manifest_fails(self):
        self.assertFalse(self.check().ok)


if __name__ == "__main__":
    unittest.main(verbosity=2)
