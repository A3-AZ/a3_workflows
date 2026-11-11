"""Unit tests for scripts/validate_config.py. Run: python -m unittest discover -s validate_config/tests"""

import contextlib
import io
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'scripts'))

import validate_config as vc  # noqa: E402

FIXTURES = os.path.join(HERE, 'fixtures')


def errors(text):
    return vc.check_content(text)[0]


def warnings(text):
    return vc.check_content(text)[1]


class ErrorChecks(unittest.TestCase):
    def test_clean_config(self):
        self.assertEqual(vc.check_content('class A {\n    x[] = {1, (2)};\n};\n'), ([], []))

    def test_tab(self):
        self.assertEqual(errors('class A {\n\tx = 1;\n};\n'), [(2, 'Tab detected')])

    def test_tab_in_string_or_comment_is_ignored(self):
        self.assertEqual(errors('x = "a\tb";\n// \t\n/* \t */\n'), [])

    def test_mismatched_closing_brackets(self):
        self.assertEqual(errors('x[] = {(};\n'), [
            (1, "Possible missing curly brace '}'"),
            (None, 'A possible missing round bracket ( or ): ( = 1, ) = 0'),
        ])
        self.assertIn((1, "Possible missing round bracket ')'"), errors('x = [);'))
        self.assertIn((1, "Possible missing square bracket ']'"), errors('x = (];'))

    def test_unbalanced_counts(self):
        self.assertEqual(errors('class A {\n'),
                         [(None, 'A possible missing curly brace { or }: { = 1, } = 0')])
        self.assertEqual(errors('x[] = {1]};'),
                         [(1, "Possible missing square bracket ']'"),
                          (None, 'A possible missing square bracket [ or ]: [ = 1, ] = 2')])

    def test_brackets_in_strings_are_ignored(self):
        self.assertEqual(errors('a = "({[";\nb = \'}\';\nc = "say ""hi"" )";\n'), [])

    def test_brackets_in_comments_are_ignored(self):
        self.assertEqual(errors('// ( {\n/* [ ** ( */\nx = 1; /* } */\n'), [])

    def test_line_numbers_after_block_comment(self):
        self.assertEqual(errors('/*\n\n*/\n\tx = 1;\n'), [(4, 'Tab detected')])

    def test_crlf_line_endings(self):
        self.assertEqual(errors('class A {\r\n\tx = 1;\r\n};\r\n'), [(2, 'Tab detected')])


class WarningChecks(unittest.TestCase):
    def test_good_class_lines(self):
        self.assertEqual(warnings('class A;\nclass B: A {\n};\nclass C {};\n'), [])

    def test_space_before_colon(self):
        self.assertEqual(warnings('class B : A {};\n'), [(1, "Bad class colon (space before ':')")])

    def test_missing_space_after_colon(self):
        self.assertEqual(warnings('class B:A {};\n'), [(1, 'Bad class, missing space after colon')])

    def test_missing_space_before_curly(self):
        self.assertEqual(warnings('class B: A{};\n'), [(1, 'Bad class, missing space before curly brace')])

    def test_brace_on_next_line(self):
        self.assertEqual(warnings('class B: A\n{\n};\n'), [(1, 'Bad class braces placement')])

    def test_warnings_do_not_count_as_errors(self):
        self.assertEqual(errors('class B : A{\n};\n'), [])


class Cli(unittest.TestCase):
    def run_main(self, *args):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = vc.main(list(args) + ['--annotate'])
        return code, out.getvalue()

    def test_good_fixture_passes(self):
        code, out = self.run_main('--path', os.path.join(FIXTURES, 'good'))
        self.assertEqual(code, 0)
        self.assertIn('Checked 1 files', out)
        self.assertIn('Config validation PASSED', out)

    def test_bad_fixture_fails(self):
        code, out = self.run_main('--path', os.path.join(FIXTURES, 'bad'))
        self.assertEqual(code, 1)
        self.assertIn('Errors detected: 4', out)
        self.assertIn('::error file=', out)
        self.assertIn('::warning file=', out)

    def test_exit_code_stays_1_with_many_errors(self):
        # The original scripts exited with the error count, which wraps to 0 at 256
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, 'addons'))
            with open(os.path.join(root, 'addons', 'config.cpp'), 'w') as file:
                file.write('\t\n' * 256)
            code, out = self.run_main('--path', root)
        self.assertEqual(code, 1)
        self.assertIn('Errors detected: 256', out)

    def test_folder_and_extension_filters(self):
        code, out = self.run_main('--path', FIXTURES, '--folders', 'good/addons', '--extensions', 'hpp')
        self.assertEqual(code, 0)
        self.assertIn('Checked 0 files', out)
        self.assertIn('no files found', out)

    def test_find_files_matches_extensions_case_sensitive(self):
        files = vc.find_files(FIXTURES, ['good/addons', 'bad/addons', 'missing'], ['cpp'])
        self.assertEqual([os.path.basename(f) for f in files], ['config.cpp', 'config.cpp'])
        self.assertEqual(vc.find_files(FIXTURES, ['good'], ['CPP']), [])


if __name__ == '__main__':
    unittest.main()
