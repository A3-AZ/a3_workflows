#!/usr/bin/env python3
"""Validate the stringtable.xml files of an Arma 3 mod.

Ported from the stringtable validator of andx667/arma-mod-template
(originally by mharis001, ACE3). Checks every stringtable.xml below the
root directory for:

  structure      well-formed XML, <Project> root, a <Package>, keys with an ID
                 and at least one translation (always on)
  duplicates     no key ID defined twice, no language twice in a key (always on)
  project-name   <Project name> equals the project prefix
  package-name   <Package name> equals the addon folder name (case-insensitive)
  key-prefix     key IDs start with STR_<prefix>_<package>_
  english-first  English is the first translation of every key
  no-original    no <Original> translation (English replaces it)
  whitespace     no tabs, indented with 4 spaces per level

Exit code: number of files with errors (0 = all good).
Errors are printed as GitHub Actions annotations when running in Actions.
"""

import argparse
import fnmatch
import os
import sys
import xml.parsers.expat

try:
    import tomllib
except ImportError:  # Python < 3.11
    tomllib = None

OPTIONAL_CHECKS = ("project-name", "package-name", "key-prefix", "english-first", "no-original", "whitespace")
ALWAYS_EXCLUDED = (".git", ".hemttout")
INDENT = 4
BLOCK_TAGS = ("key", "package", "project", "container")


class Node:
    """Minimal XML element with the line it starts on."""

    def __init__(self, tag, attrib, line):
        self.tag = tag
        self.attrib = attrib
        self.line = line
        self.children = []

    def get(self, name):
        return self.attrib.get(name)

    def findall(self, tag):
        return [c for c in self.children if c.tag == tag]

    def find(self, tag):
        found = self.findall(tag)
        return found[0] if found else None


def parse_xml(data):
    """Parse XML bytes into a Node tree. Raises ValueError with the expat message."""
    parser = xml.parsers.expat.ParserCreate()
    stack = []
    result = []

    def start(tag, attrib):
        node = Node(tag, attrib, parser.CurrentLineNumber)
        if stack:
            stack[-1].children.append(node)
        else:
            result.append(node)
        stack.append(node)

    def end(_tag):
        stack.pop()

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    try:
        parser.Parse(data, True)
    except xml.parsers.expat.ExpatError as e:
        raise ValueError("line {}: {}".format(e.lineno, xml.parsers.expat.ErrorString(e.code))) from e
    return result[0]


class Report:
    def __init__(self, path, display_path):
        self.path = path
        self.display_path = display_path
        self.errors = []

    def error(self, message, line=None):
        self.errors.append((line, message))


def check_stringtable(path, prefix, checks, case_sensitive=True, display_path=None):
    """Check one stringtable file. Returns a list of (line, message) errors."""
    report = Report(path, display_path or path)
    with open(path, "rb") as f:
        data = f.read()

    try:
        root = parse_xml(data)
    except ValueError as e:
        report.error("Failed to parse file: {}".format(e))
        return report.errors

    def same(a, b):
        return a == b if case_sensitive else a.lower() == b.lower()

    if root.tag != "Project":
        report.error("Invalid root tag '{}', must be 'Project'.".format(root.tag), root.line)

    if "project-name" in checks and root.get("name") != prefix:
        report.error("Project name '{}' must be the project prefix '{}'.".format(root.get("name"), prefix), root.line)

    package = root.find("Package")
    if package is None:
        report.error("No 'Package' tag under the 'Project' tag.", root.line)
    else:
        package_name = package.get("name") or ""
        component_folder = os.path.basename(os.path.dirname(os.path.abspath(path)))
        if "package-name" in checks and package_name.lower() != component_folder.lower():
            report.error(
                "Package name '{}' does not match the addon folder name '{}'.".format(package_name, component_folder),
                package.line,
            )

        keys = package.findall("Key")
        for container in package.findall("Container"):
            keys.extend(container.findall("Key"))

        key_prefix = "STR_{}_{}_".format(prefix, package_name)
        seen_ids = {}

        for key in keys:
            key_id = key.get("ID")
            if key_id is None:
                report.error("Key has no ID attribute.", key.line)
            else:
                if "key-prefix" in checks and not same(key_id[: len(key_prefix)], key_prefix):
                    report.error("Key '{}' must start with '{}'.".format(key_id, key_prefix), key.line)
                seen_ids.setdefault(key_id if case_sensitive else key_id.lower(), []).append(key)

            entries = key.children
            if not entries:
                report.error("Key '{}' has no translations.".format(key_id), key.line)
                continue

            if "no-original" in checks and key.find("Original") is not None:
                report.error("Key '{}' has an Original translation, unnecessary with English as first.".format(key_id), key.find("Original").line)

            if "english-first" in checks and entries[0].tag != "English":
                report.error("Key '{}' does not have its English translation listed first.".format(key_id), entries[0].line)

            languages = {}
            for entry in entries:
                languages.setdefault(entry.tag, []).append(entry)
            for language, items in languages.items():
                if len(items) > 1:
                    report.error("Key '{}' has {} {} translations.".format(key_id, len(items), language), items[1].line)

        for items in seen_ids.values():
            if len(items) > 1:
                report.error("Key '{}' is defined {} times.".format(items[0].get("ID"), len(items)), items[1].line)

    if "whitespace" in checks:
        check_whitespace(data.decode("utf-8", errors="replace"), report)

    report.errors.sort(key=lambda e: (e[0] or 0))
    return report.errors


def check_whitespace(text, report):
    depth = 0
    for line_number, line in enumerate(text.splitlines(), 1):
        stripped = line.lstrip()
        lowered = stripped.lower()
        if any(lowered.startswith("</" + t) for t in BLOCK_TAGS):
            depth -= INDENT
        if "\t" in line:
            report.error("Tab found, indent with spaces.", line_number)
        elif stripped:
            indent = len(line) - len(stripped)
            if indent != depth:
                report.error("Indented with {} spaces, should be {}.".format(indent, depth), line_number)
        if any(lowered.startswith("<" + t) for t in BLOCK_TAGS) and not lowered.rstrip().endswith("/>"):
            # A block opened and closed on the same line does not change the depth
            if not any("</" + t in lowered for t in BLOCK_TAGS):
                depth += INDENT


def read_prefix(root):
    """Read `prefix` from .hemtt/project.toml. Returns None if not available."""
    path = os.path.join(root, ".hemtt", "project.toml")
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as f:
        raw = f.read()
    if tomllib is not None:
        try:
            return tomllib.loads(raw.decode("utf-8")).get("prefix")
        except (tomllib.TOMLDecodeError, UnicodeDecodeError):
            pass
    # Fallback for old Python or broken TOML: top-level `prefix = "..."`
    for line in raw.decode("utf-8", errors="replace").splitlines():
        if line.startswith("["):
            break
        name, sep, value = line.partition("=")
        if sep and name.strip() == "prefix":
            value = value.split("#", 1)[0].strip()
            return value.strip("\"'")
    return None


def find_stringtables(root, exclude):
    patterns = list(exclude)
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root).replace(os.sep, "/")
        rel_dir = "" if rel_dir == "." else rel_dir + "/"
        dirnames[:] = sorted(
            d for d in dirnames
            if d not in ALWAYS_EXCLUDED and not any(fnmatch.fnmatch(rel_dir + d, p) for p in patterns)
        )
        for name in filenames:
            rel = rel_dir + name
            if name.lower() == "stringtable.xml" and not any(fnmatch.fnmatch(rel, p) for p in patterns):
                found.append(rel)
    return sorted(found)


def annotate(path, line, message):
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return
    location = "file={}".format(path) + (",line={}".format(line) if line else "")
    message = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    print("::error {},title=Stringtable::{}".format(location, message))


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=".", help="Directory to search for stringtable.xml files (default: .)")
    parser.add_argument("--prefix", default="", help="Project prefix. Empty = 'prefix' from .hemtt/project.toml")
    parser.add_argument("--exclude", action="append", default=[], help="Glob of paths to skip, relative to --root. Repeatable.")
    parser.add_argument("--skip", action="append", default=[], help="Checks to turn off, comma- or space-separated. Repeatable. One of: " + ", ".join(OPTIONAL_CHECKS))
    parser.add_argument("--case-insensitive", action="store_true", help="Compare key IDs and key prefixes case-insensitively.")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    root = args.root
    skip = {c for value in args.skip for c in value.replace(",", " ").split()}
    unknown = sorted(skip - set(OPTIONAL_CHECKS))
    if unknown:
        print("ERROR: Unknown check(s) to skip: {}. Valid: {}.".format(", ".join(unknown), ", ".join(OPTIONAL_CHECKS)))
        return 1
    checks = set(OPTIONAL_CHECKS) - skip
    exclude = [p.strip().strip("/") for p in args.exclude if p.strip()]

    prefix = args.prefix or read_prefix(root)
    if not prefix and checks & {"project-name", "key-prefix"}:
        print("ERROR: No project prefix. Set it, or add 'prefix' to .hemtt/project.toml.")
        return 1

    print("Validating stringtables in '{}' (prefix '{}')".format(root, prefix or "-"))
    print("Checks: structure, duplicates, {}".format(", ".join(c for c in OPTIONAL_CHECKS if c in checks)))
    print()

    files = find_stringtables(root, exclude)
    if not files:
        print("No stringtable.xml files found.")
        return 0

    bad = 0
    total_errors = 0
    for rel in files:
        errors = check_stringtable(os.path.join(root, rel), prefix, checks, not args.case_insensitive, rel)
        status = "OK" if not errors else "{} error(s)".format(len(errors))
        print("{}: {}".format(rel, status))
        for line, message in errors:
            print("  {}{}".format("line {}: ".format(line) if line else "", message))
            annotate(os.path.relpath(os.path.join(root, rel)).replace(os.sep, "/"), line, message)
        if errors:
            bad += 1
            total_errors += len(errors)

    print()
    if bad:
        print("Stringtable validation FAILED: {} error(s) in {} of {} file(s).".format(total_errors, bad, len(files)))
    else:
        print("Stringtable validation PASSED: {} file(s).".format(len(files)))
    return min(bad, 255)


if __name__ == "__main__":
    sys.exit(main())
