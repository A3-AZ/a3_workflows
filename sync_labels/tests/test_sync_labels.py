"""Unit tests for sync_labels/scripts/sync_labels.py. The gh cli is mocked - no GitHub calls are made.

Run from the repository root: python3 -m unittest discover -s sync_labels/tests -v
"""

import io
import json
import os
import sys
import tempfile
import textwrap
import unittest
from contextlib import redirect_stdout
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

import sync_labels  # noqa: E402

EXAMPLE = os.path.join(HERE, "..", "example", "labels.yml")


def write_config(text):
    f = tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False, encoding="utf-8")
    f.write(textwrap.dedent(text))
    f.close()
    return f.name


class FakeGh:
    """Stands in for sync_labels.gh: answers 'label list' with the given labels and records every other call."""

    def __init__(self, labels):
        self.labels = labels
        self.calls = []

    def __call__(self, *args):
        if args[:2] == ("label", "list"):
            return json.dumps(self.labels)
        self.calls.append(args)
        return ""


class LoadConfigTest(unittest.TestCase):
    def tearDown(self):
        for path in getattr(self, "paths", []):
            os.unlink(path)

    def config(self, text):
        path = write_config(text)
        self.paths = getattr(self, "paths", []) + [path]
        return path

    def test_example_file_is_valid(self):
        labels, remove_unlisted = sync_labels.load_config(EXAMPLE)
        self.assertTrue(remove_unlisted)
        self.assertEqual(len(labels), 10)
        self.assertTrue(all(label["name"].startswith("pr/") for label in labels))

    def test_normalizes_color_and_description(self):
        labels, remove_unlisted = sync_labels.load_config(self.config("""
            labels:
              - name: "a"
                color: "#ABCDEF"
        """))
        self.assertFalse(remove_unlisted)
        self.assertEqual(labels, [{"name": "a", "color": "abcdef", "description": ""}])

    def test_empty_file(self):
        self.assertEqual(sync_labels.load_config(self.config("")), ([], False))

    def test_missing_file(self):
        with self.assertRaisesRegex(sync_labels.ConfigError, "does not exist"):
            sync_labels.load_config("does/not/exist.yml")

    def test_unquoted_color(self):
        with self.assertRaisesRegex(sync_labels.ConfigError, "quoted 6 digit hex"):
            sync_labels.load_config(self.config("""
                labels:
                  - name: "a"
                    color: 000000
            """))

    def test_invalid_color(self):
        with self.assertRaisesRegex(sync_labels.ConfigError, "quoted 6 digit hex"):
            sync_labels.load_config(self.config("""
                labels:
                  - name: "a"
                    color: "red"
            """))

    def test_missing_name(self):
        with self.assertRaisesRegex(sync_labels.ConfigError, "without name"):
            sync_labels.load_config(self.config("""
                labels:
                  - color: "ffffff"
            """))

    def test_duplicate_name(self):
        with self.assertRaisesRegex(sync_labels.ConfigError, "listed twice"):
            sync_labels.load_config(self.config("""
                labels:
                  - name: "Bug"
                    color: "ffffff"
                  - name: "bug"
                    color: "000000"
            """))

    def test_remove_unlisted_must_be_bool(self):
        with self.assertRaisesRegex(sync_labels.ConfigError, "true or false"):
            sync_labels.load_config(self.config("""
                settings:
                  remove_unlisted: "yes please"
            """))

    def test_invalid_yaml(self):
        with self.assertRaisesRegex(sync_labels.ConfigError, "not valid YAML"):
            sync_labels.load_config(self.config("labels: [unclosed"))


class PlanTest(unittest.TestCase):
    LABELS = [
        {"name": "pr/fix", "color": "d73a4a", "description": "Fix"},
        {"name": "pr/new", "color": "0e8a16", "description": "New"},
        {"name": "pr/docs", "color": "0075ca", "description": "Docs"},
        {"name": "pr/ignore", "color": "e1e4e8", "description": ""},
    ]
    EXISTING = {
        "pr/fix": {"name": "pr/fix", "color": "D73A4A", "description": "Fix"},     # unchanged, color case ignored
        "pr/new": {"name": "pr/new", "color": "ffffff", "description": "New"},     # color differs
        "pr/docs": {"name": "PR/Docs", "color": "0075ca", "description": "Docs"},  # name case differs
        "bug": {"name": "bug", "color": "d73a4a", "description": "Something"},     # unlisted
    }

    def actions(self, remove_unlisted):
        return {(action, label["name"]) for action, label, _ in
                sync_labels.plan(self.LABELS, self.EXISTING, remove_unlisted)}

    def test_plan_keeps_unlisted(self):
        self.assertEqual(self.actions(False), {
            ("unchanged", "pr/fix"), ("update", "pr/new"), ("update", "pr/docs"), ("create", "pr/ignore"),
        })

    def test_plan_removes_unlisted(self):
        self.assertIn(("delete", "bug"), self.actions(True))

    def test_none_description_equals_empty(self):
        existing = {"pr/ignore": {"name": "pr/ignore", "color": "e1e4e8", "description": None}}
        changes = sync_labels.plan(self.LABELS[3:], existing, False)
        self.assertEqual(changes[0][0], "unchanged")


class MainTest(unittest.TestCase):
    EXISTING = [
        {"name": "pr/fix", "color": "d73a4a", "description": "Fixes a bug - Changelog: Bug Fixes"},
        {"name": "PR/New", "color": "000000", "description": "old"},
        {"name": "bug", "color": "d73a4a", "description": "Something isn't working"},
    ]

    def run_main(self, *args):
        fake = FakeGh(self.EXISTING)
        out = io.StringIO()
        with mock.patch.object(sync_labels, "gh", fake), mock.patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": ""}), \
                redirect_stdout(out):
            code = sync_labels.main(["--config", EXAMPLE, *args])
        return code, fake.calls, out.getvalue()

    def test_dry_run_changes_nothing(self):
        code, calls, out = self.run_main("--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(calls, [])
        self.assertIn("[DRY RUN] Create: pr/improvement", out)
        self.assertIn("[DRY RUN] Update: pr/new (was 'PR/New')", out)
        self.assertIn("[DRY RUN] Delete: bug", out)
        self.assertIn("Unchanged: pr/fix", out)
        self.assertIn("8 created, 1 updated, 1 deleted, 1 unchanged", out)

    def test_apply_calls_gh(self):
        code, calls, _ = self.run_main()
        self.assertEqual(code, 0)
        self.assertIn(("label", "edit", "PR/New", "--name", "pr/new", "--color", "0e8a16",
                       "--description", "New feature - Changelog: Features"), calls)
        self.assertIn(("label", "delete", "bug", "--yes"), calls)
        self.assertEqual(sum(1 for c in calls if c[1] == "create"), 8)
        self.assertFalse(any(c[1] == "edit" and c[2] == "pr/fix" for c in calls))

    def test_invalid_config_makes_no_calls(self):
        path = write_config("""
            labels:
              - name: "a"
                color: 123456
        """)
        fake = FakeGh(self.EXISTING)
        out = io.StringIO()
        try:
            with mock.patch.object(sync_labels, "gh", fake), redirect_stdout(out):
                code = sync_labels.main(["--config", path])
        finally:
            os.unlink(path)
        self.assertEqual(code, 1)
        self.assertEqual(fake.calls, [])
        self.assertIn("::error title=sync_labels::", out.getvalue())

    def test_gh_failure_is_reported(self):
        def failing_gh(*args):
            raise RuntimeError("gh label list failed: HTTP 403")
        out = io.StringIO()
        with mock.patch.object(sync_labels, "gh", failing_gh), redirect_stdout(out):
            code = sync_labels.main(["--config", EXAMPLE, "--dry-run"])
        self.assertEqual(code, 1)
        self.assertIn("::error title=sync_labels::gh label list failed: HTTP 403", out.getvalue())

    def test_job_summary(self):
        fake = FakeGh(self.EXISTING)
        with tempfile.TemporaryDirectory() as tmp:
            summary = os.path.join(tmp, "summary.md")
            with mock.patch.object(sync_labels, "gh", fake), \
                    mock.patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": summary}), redirect_stdout(io.StringIO()):
                sync_labels.main(["--config", EXAMPLE, "--dry-run"])
            with open(summary, encoding="utf-8") as f:
                text = f.read()
        self.assertIn("dry run", text)
        self.assertIn("| 8 | 1 | 1 | 1 |", text)


class GhTest(unittest.TestCase):
    def test_gh_error_message(self):
        failed = mock.Mock(returncode=1, stdout="", stderr="HTTP 404: Not Found")
        with mock.patch.object(sync_labels.subprocess, "run", return_value=failed):
            with self.assertRaisesRegex(RuntimeError, "gh label list failed: HTTP 404"):
                sync_labels.gh("label", "list")


if __name__ == "__main__":
    unittest.main()
