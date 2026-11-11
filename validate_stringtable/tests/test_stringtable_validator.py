"""Unit tests for scripts/stringtable_validator.py. Run: python3 -m unittest discover -s validate_stringtable/tests"""

import contextlib
import io
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

import stringtable_validator as sv  # noqa: E402

FIXTURES = os.path.join(HERE, "fixtures")
ALL = set(sv.OPTIONAL_CHECKS)


def run_main(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = sv.main(list(argv))
    return code, out.getvalue()


class TempMod:
    """Creates a mod folder with one addon stringtable."""

    def __init__(self, xml, addon="main", project_toml='prefix = "tst"\n'):
        self.dir = tempfile.TemporaryDirectory()
        self.root = self.dir.name
        os.makedirs(os.path.join(self.root, "addons", addon))
        self.path = os.path.join(self.root, "addons", addon, "stringtable.xml")
        with open(self.path, "w", encoding="utf-8", newline="") as f:
            f.write(xml)
        if project_toml is not None:
            os.makedirs(os.path.join(self.root, ".hemtt"))
            with open(os.path.join(self.root, ".hemtt", "project.toml"), "w", encoding="utf-8") as f:
                f.write(project_toml)

    def check(self, checks=ALL, case_sensitive=True, prefix="tst"):
        return [m for _, m in sv.check_stringtable(self.path, prefix, checks, case_sensitive)]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.dir.cleanup()


def table(body, project="tst", package="main"):
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Project name="{}">\n'
        '    <Package name="{}">\n'
        "{}"
        "    </Package>\n"
        "</Project>\n"
    ).format(project, package, body)


def key(key_id, *entries):
    lines = ['        <Key ID="{}">\n'.format(key_id)]
    lines += ["            <{0}>{1}</{0}>\n".format(tag, text) for tag, text in entries]
    lines.append("        </Key>\n")
    return "".join(lines)


GOOD_KEY = key("STR_tst_main_a", ("English", "A"), ("German", "A"))


class CheckTests(unittest.TestCase):
    def test_valid(self):
        with TempMod(table(GOOD_KEY)) as mod:
            self.assertEqual(mod.check(), [])

    def test_parse_error(self):
        with TempMod("<Project><Package></Project>") as mod:
            errors = mod.check()
            self.assertEqual(len(errors), 1)
            self.assertIn("Failed to parse", errors[0])

    def test_root_tag(self):
        with TempMod('<Stringtable name="tst"><Package name="main"/></Stringtable>\n') as mod:
            self.assertTrue(any("root tag" in e for e in mod.check(checks=set())))

    def test_missing_package(self):
        with TempMod('<Project name="tst">\n</Project>\n') as mod:
            self.assertTrue(any("No 'Package'" in e for e in mod.check()))

    def test_project_name(self):
        with TempMod(table(GOOD_KEY, project="other")) as mod:
            self.assertTrue(any("Project name" in e for e in mod.check()))
            self.assertEqual(mod.check(checks=ALL - {"project-name"}), [])

    def test_package_name(self):
        with TempMod(table(key("STR_tst_other_a", ("English", "A")), package="other")) as mod:
            self.assertTrue(any("Package name" in e for e in mod.check()))
            self.assertEqual(mod.check(checks=ALL - {"package-name"}), [])

    def test_package_name_case_insensitive(self):
        with TempMod(table(key("STR_tst_Main_a", ("English", "A")), package="Main")) as mod:
            self.assertEqual(mod.check(), [])

    def test_key_prefix(self):
        with TempMod(table(key("STR_xyz_main_a", ("English", "A")))) as mod:
            self.assertTrue(any("must start with 'STR_tst_main_'" in e for e in mod.check()))
            self.assertEqual(mod.check(checks=ALL - {"key-prefix"}), [])

    def test_key_prefix_case(self):
        # Zorn's templates: Package 'Main', keys 'STR_<prefix>_main_...'
        with TempMod(table(key("STR_tst_main_a", ("English", "A")), package="Main")) as mod:
            self.assertTrue(any("must start with" in e for e in mod.check()))
            self.assertEqual(mod.check(case_sensitive=False), [])

    def test_key_in_container(self):
        body = '        <Container name="c">\n' + key("STR_xyz_main_a", ("English", "A")).replace("\n        ", "\n            ").replace("        <Key", "            <Key", 1) + "        </Container>\n"
        with TempMod(table(body)) as mod:
            errors = mod.check()
            self.assertEqual(len(errors), 1, errors)
            self.assertIn("must start with", errors[0])

    def test_key_without_id(self):
        with TempMod(table(key("X", ("English", "A")).replace(' ID="X"', ""))) as mod:
            self.assertTrue(any("no ID" in e for e in mod.check()))

    def test_no_translations(self):
        with TempMod(table('        <Key ID="STR_tst_main_a">\n        </Key>\n')) as mod:
            self.assertTrue(any("no translations" in e for e in mod.check()))

    def test_english_first(self):
        with TempMod(table(key("STR_tst_main_a", ("German", "A"), ("English", "A")))) as mod:
            self.assertTrue(any("English translation listed first" in e for e in mod.check()))
            self.assertEqual(mod.check(checks=ALL - {"english-first"}), [])

    def test_original(self):
        with TempMod(table(key("STR_tst_main_a", ("English", "A"), ("Original", "A")))) as mod:
            self.assertTrue(any("Original" in e for e in mod.check()))
            self.assertEqual(mod.check(checks=ALL - {"no-original"}), [])

    def test_duplicate_language(self):
        with TempMod(table(key("STR_tst_main_a", ("English", "A"), ("English", "B")))) as mod:
            self.assertTrue(any("2 English translations" in e for e in mod.check()))

    def test_duplicate_key(self):
        with TempMod(table(GOOD_KEY + GOOD_KEY)) as mod:
            self.assertTrue(any("defined 2 times" in e for e in mod.check()))

    def test_duplicate_key_case(self):
        with TempMod(table(GOOD_KEY + key("STR_TST_main_a", ("English", "A")))) as mod:
            self.assertFalse(any("defined" in e for e in mod.check(checks=set())))
            self.assertTrue(any("defined 2 times" in e for e in mod.check(checks=set(), case_sensitive=False)))

    def test_tab(self):
        with TempMod(table(GOOD_KEY.replace("            <English>", "\t\t\t<English>"))) as mod:
            self.assertTrue(any("Tab" in e for e in mod.check()))
            self.assertEqual(mod.check(checks=ALL - {"whitespace"}), [])

    def test_indentation(self):
        with TempMod(table(GOOD_KEY.replace("        <Key", "      <Key"))) as mod:
            self.assertTrue(any("Indented with 6 spaces, should be 8" in e for e in mod.check()))

    def test_tab_line_keeps_depth(self):
        # A tab-indented <Key> line still opens a block: only that line is reported
        with TempMod(table(GOOD_KEY.replace("        <Key", "\t\t<Key"))) as mod:
            self.assertEqual(mod.check(), ["Tab found, indent with spaces."])

    def test_crlf_and_blank_lines(self):
        with TempMod(table(GOOD_KEY + "\n" + key("STR_tst_main_b", ("English", "B"))).replace("\n", "\r\n")) as mod:
            self.assertEqual(mod.check(), [])

    def test_line_numbers(self):
        with TempMod(table(GOOD_KEY + key("STR_xyz_main_b", ("English", "B")))) as mod:
            errors = sv.check_stringtable(mod.path, "tst", ALL)
            self.assertEqual(errors, [(8, "Key 'STR_xyz_main_b' must start with 'STR_tst_main_'.")])


class PrefixTests(unittest.TestCase):
    def test_reads_top_level_prefix(self):
        self.assertEqual(sv.read_prefix(os.path.join(FIXTURES, "valid")), "tst")

    def test_fallback_parser(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, ".hemtt"))
            with open(os.path.join(root, ".hemtt", "project.toml"), "w") as f:
                f.write('name = "x"\nprefix = "abc"   # comment\n[version]\nprefix = "no"\n')
            saved, sv.tomllib = sv.tomllib, None
            try:
                self.assertEqual(sv.read_prefix(root), "abc")
            finally:
                sv.tomllib = saved

    def test_no_project_toml(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertIsNone(sv.read_prefix(root))


class MainTests(unittest.TestCase):
    def test_valid_fixture(self):
        code, out = run_main("--root", os.path.join(FIXTURES, "valid"))
        self.assertEqual(code, 0, out)
        self.assertIn("PASSED: 2 file(s)", out)

    def test_broken_fixture(self):
        code, out = run_main("--root", os.path.join(FIXTURES, "broken"))
        self.assertEqual(code, 1, out)
        self.assertIn("10 error(s)", out)

    def test_broken_fixture_with_all_checks_skipped(self):
        code, out = run_main("--root", os.path.join(FIXTURES, "broken"), "--skip", ",".join(sv.OPTIONAL_CHECKS))
        self.assertEqual(code, 1, out)
        self.assertIn("3 error(s)", out)  # duplicate language, duplicate key, no translations

    def test_prefix_input_overrides_project_toml(self):
        code, out = run_main("--root", os.path.join(FIXTURES, "valid"), "--prefix", "abc")
        self.assertEqual(code, 2, out)

    def test_unknown_skip(self):
        code, out = run_main("--root", os.path.join(FIXTURES, "valid"), "--skip", "project-name typo")
        self.assertEqual(code, 1)
        self.assertIn("Unknown check(s) to skip: typo", out)

    def test_no_prefix(self):
        with tempfile.TemporaryDirectory() as root:
            code, out = run_main("--root", root)
            self.assertEqual(code, 1)
            self.assertIn("No project prefix", out)
            code, out = run_main("--root", root, "--skip", "project-name,key-prefix")
            self.assertEqual(code, 0, out)

    def test_exclude_and_hemttout(self):
        with TempMod(table(GOOD_KEY)) as mod:
            for folder in (".hemttout/build/addons/x", "include/x", "addons/other/sub"):
                os.makedirs(os.path.join(mod.root, folder))
                with open(os.path.join(mod.root, folder, "stringtable.xml"), "w") as f:
                    f.write("broken")
            self.assertEqual(
                sv.find_stringtables(mod.root, ["include/*"]),
                ["addons/main/stringtable.xml", "addons/other/sub/stringtable.xml"],
            )
            self.assertEqual(sv.find_stringtables(mod.root, ["include", "addons/other/*"]), ["addons/main/stringtable.xml"])

    def test_no_files(self):
        with tempfile.TemporaryDirectory() as root:
            code, out = run_main("--root", root, "--prefix", "x")
            self.assertEqual(code, 0)
            self.assertIn("No stringtable.xml", out)

    def test_annotations(self):
        saved = os.environ.get("GITHUB_ACTIONS")
        os.environ["GITHUB_ACTIONS"] = "true"
        try:
            code, out = run_main("--root", os.path.join(FIXTURES, "broken"))
        finally:
            if saved is None:
                del os.environ["GITHUB_ACTIONS"]
            else:
                os.environ["GITHUB_ACTIONS"] = saved
        self.assertIn("::error file=", out)
        self.assertIn("broken/addons/main/stringtable.xml,line=2,title=Stringtable::Project name", out)


if __name__ == "__main__":
    unittest.main()
