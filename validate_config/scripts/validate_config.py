#!/usr/bin/env python3
"""Check the config style of an Arma 3 mod.

Merged from tools/validate_config.py (ZRN-Mod-Template) and
tools/config_style_checker.py (andx667/arma-mod-template), which were identical
apart from dead code. The checks are unchanged:

Errors (fail the run):
  - a tab character outside strings and comments
  - a closing bracket ) ] } directly after an opening bracket of another kind
  - unequal counts of ( and ), [ and ], { and } in a file

Warnings (reported only), for lines starting with `class`:
  - a space before the inheritance colon: `class A : B`
  - no space after the inheritance colon: `class A:B`
  - no space before the opening brace: `class A{`
  - neither `{` nor `;` on the line

Strings ("..." and '...'), line comments and block comments are skipped by the
error checks. The warning checks work on raw lines.

Exit code: 0 when no errors were found, 1 otherwise.
"""

import argparse
import os
import re
import sys

RE_IS_CLASS = re.compile(r'^\s*class(.*)')
RE_IS_CLASS_INHERIT = re.compile(r'^\s*class(.*):')
RE_IS_CLASS_BODY = re.compile(r'^\s*class(.*){')
RE_BAD_COLON = re.compile(r'\s*class (.*) :')
RE_SPACE_AFTER_COLON = re.compile(r'\s*class (.*): ')
RE_SPACE_BEFORE_CURLY = re.compile(r'\s*class (.*) {')
RE_CLASS_SINGLE_LINE = re.compile(r'\s*class (.*)[{;]')

# Closing bracket -> (opening brackets it must not directly follow, name)
MISMATCH = {
    ')': (('{', '['), "round bracket ')'"),
    ']': (('{', '('), "square bracket ']'"),
    '}': (('(', '['), "curly brace '}'"),
}


def check_content(content):
    """Check config text. Returns (errors, warnings), lists of (line or None, message)."""
    errors = []
    warnings = []
    brackets = []

    in_comment_block = False
    check_if_in_comment = False   # previous character was a '/'
    in_line_comment = False
    check_if_closing_block = False  # previous character in a comment block was a '*'
    in_string = False
    string_quote = ''
    line = 1

    for c in content:
        if c == '\n':
            line += 1
        if in_string:
            if c == string_quote:
                in_string = False
        elif not in_comment_block:
            if check_if_in_comment:
                check_if_in_comment = False
                if c == '*':
                    in_comment_block = True
                elif c == '/':
                    in_line_comment = True

            if not in_comment_block:
                if in_line_comment:
                    if c == '\n':
                        in_line_comment = False
                elif c in ('"', "'"):
                    in_string = True
                    string_quote = c
                elif c == '/':
                    check_if_in_comment = True
                elif c in ('(', '[', '{'):
                    brackets.append(c)
                elif c in MISMATCH:
                    openers, name = MISMATCH[c]
                    if brackets and brackets[-1] in openers:
                        errors.append((line, f"Possible missing {name}"))
                    brackets.append(c)
                elif c == '\t':
                    errors.append((line, "Tab detected"))
        else:
            if c == '*':
                check_if_closing_block = True
            elif check_if_closing_block:
                if c == '/':
                    in_comment_block = False
                elif c != '*':
                    check_if_closing_block = False

    for opening, closing, name in (('[', ']', 'square bracket'),
                                   ('(', ')', 'round bracket'),
                                   ('{', '}', 'curly brace')):
        n_open = brackets.count(opening)
        n_close = brackets.count(closing)
        if n_open != n_close:
            errors.append((None, f"A possible missing {name} {opening} or {closing}: "
                                 f"{opening} = {n_open}, {closing} = {n_close}"))

    for number, text in enumerate(content.split('\n'), start=1):
        if not RE_IS_CLASS.match(text):
            continue
        if RE_BAD_COLON.match(text):
            warnings.append((number, "Bad class colon (space before ':')"))
        if RE_IS_CLASS_INHERIT.match(text) and not RE_SPACE_AFTER_COLON.match(text):
            warnings.append((number, "Bad class, missing space after colon"))
        if RE_IS_CLASS_BODY.match(text) and not RE_SPACE_BEFORE_CURLY.match(text):
            warnings.append((number, "Bad class, missing space before curly brace"))
        if not RE_CLASS_SINGLE_LINE.match(text):
            warnings.append((number, "Bad class braces placement"))

    return errors, warnings


def check_file(path):
    with open(path, 'r', encoding='utf-8', errors='ignore') as file:
        return check_content(file.read())


def find_files(root, folders, extensions):
    """All files below root/<folder> with one of the extensions, sorted."""
    suffixes = tuple('.' + ext.lstrip('.') for ext in extensions)
    files = []
    for folder in folders:
        for dirpath, _dirnames, filenames in os.walk(os.path.join(root, folder)):
            for filename in filenames:
                if filename.endswith(suffixes):
                    files.append(os.path.join(dirpath, filename))
    return sorted(files)


def report(level, path, line, message, annotate):
    location = f"{path} Line number: {line}" if line else path
    print(f"{level.upper()}: {message} - {location}")
    if annotate:
        props = f"file={path},line={line}" if line else f"file={path}"
        print(f"::{level} {props},title=Config style::{message}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n', 1)[0])
    parser.add_argument('--path', default='.', help='root of the mod (default: .)')
    parser.add_argument('--folders', default='addons optionals',
                        help='space-separated folders below --path to scan')
    parser.add_argument('--extensions', default='cpp hpp rvmat cfg',
                        help='space-separated file extensions to check')
    parser.add_argument('--annotate', action='store_true',
                        default=os.environ.get('GITHUB_ACTIONS') == 'true',
                        help='also print GitHub Actions annotations (default: on in GitHub Actions)')
    args = parser.parse_args(argv)

    print("Validating Config Style")
    files = find_files(args.path, args.folders.split(), args.extensions.split())

    error_count = 0
    warning_count = 0
    for path in files:
        errors, warnings = check_file(path)
        shown = os.path.relpath(path).replace(os.sep, '/')
        for line, message in errors:
            report('error', shown, line, message, args.annotate)
        for line, message in warnings:
            report('warning', shown, line, message, args.annotate)
        error_count += len(errors)
        warning_count += len(warnings)

    print(f"------\nChecked {len(files)} files\n"
          f"Errors detected: {error_count}\nWarnings: {warning_count}")
    if not files:
        print(f"WARNING: no files found in '{args.folders}' below '{args.path}'")
    print("Config validation " + ("PASSED" if error_count == 0 else "FAILED"))
    return 0 if error_count == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
