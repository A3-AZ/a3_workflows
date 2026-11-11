#!/usr/bin/env python3
"""
Syncs the labels of a GitHub repository with a labels file (default: .github/labels.yml).
Used by sync_labels/action.yml - see sync_labels/README.md for the file format.

- creates missing labels, updates name case / color / description of existing ones
- if settings.remove_unlisted is true, deletes every label that is not listed
- --dry-run only prints what would change

Requires the gh cli (preinstalled on GitHub runners, auth via GH_TOKEN, repository via GH_REPO) and PyYAML.
"""

import argparse
import json
import os
import re
import subprocess
import sys

import yaml

DEFAULT_CONFIG = ".github/labels.yml"
COLOR_PATTERN = re.compile(r"#?[0-9a-fA-F]{6}")


class ConfigError(Exception):
    """The labels file is missing or invalid."""


def gh(*args):
    """Runs a gh cli command and returns its stdout. Raises RuntimeError with gh's error message on failure."""
    result = subprocess.run(["gh", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:2])} failed: {result.stderr.strip() or result.stdout.strip()}")
    return result.stdout


def load_config(path):
    """Reads the labels file. Returns (labels, remove_unlisted); labels is a list of {name, color, description}."""
    try:
        with open(path, encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        raise ConfigError(f"Labels file '{path}' does not exist. Check the labels-file input and that the repository is checked out.")
    except yaml.YAMLError as e:
        raise ConfigError(f"Labels file '{path}' is not valid YAML: {e}")

    if config is None:
        config = {}
    if not isinstance(config, dict):
        raise ConfigError(f"Labels file '{path}' must be a mapping with 'settings' and 'labels'.")

    settings = config.get("settings") or {}
    if not isinstance(settings, dict):
        raise ConfigError("'settings' must be a mapping.")
    remove_unlisted = settings.get("remove_unlisted", False)
    if not isinstance(remove_unlisted, bool):
        raise ConfigError(f"settings.remove_unlisted must be true or false, got: {remove_unlisted!r}")

    entries = config.get("labels") or []
    if not isinstance(entries, list):
        raise ConfigError("'labels' must be a list.")

    labels = []
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ConfigError(f"Label entry must be a mapping with name/color/description, got: {entry!r}")
        name = entry.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ConfigError(f"Label without name: {entry!r}")
        color = entry.get("color")
        if not isinstance(color, str) or not COLOR_PATTERN.fullmatch(color):
            raise ConfigError(f"Label '{name}' needs a quoted 6 digit hex color, got: {color!r}")
        description = entry.get("description") or ""
        if not isinstance(description, str):
            raise ConfigError(f"Label '{name}' has a description that is not text: {description!r}")
        if name.lower() in seen:
            raise ConfigError(f"Label '{name}' is listed twice (names are case-insensitive).")
        seen.add(name.lower())
        labels.append({"name": name, "color": color.lstrip("#").lower(), "description": description})

    return labels, remove_unlisted


def fetch_labels():
    """Returns the repository's labels as {lowercase name: {name, color, description}}."""
    labels = json.loads(gh("label", "list", "--limit", "1000", "--json", "name,color,description"))
    return {label["name"].lower(): label for label in labels}


def plan(labels, existing, remove_unlisted):
    """Works out the changes. Returns a list of (action, label, current_name) with action create/update/unchanged/delete."""
    changes = []
    for label in labels:
        current = existing.get(label["name"].lower())
        if current is None:
            changes.append(("create", label, None))
        elif (current["name"], current["color"].lower(), current.get("description") or "") == (
            label["name"], label["color"], label["description"]
        ):
            changes.append(("unchanged", label, current["name"]))
        else:
            changes.append(("update", label, current["name"]))

    if remove_unlisted:
        listed = {label["name"].lower() for label in labels}
        for key, current in existing.items():
            if key not in listed:
                changes.append(("delete", current, current["name"]))

    return changes


def apply(changes, dry_run):
    """Prints and (unless dry_run) applies the changes. Returns a count per action."""
    prefix = "[DRY RUN] " if dry_run else ""
    counts = {"create": 0, "update": 0, "unchanged": 0, "delete": 0}
    for action, label, current_name in changes:
        counts[action] += 1
        if action == "unchanged":
            print(f"Unchanged: {label['name']}")
        elif action == "create":
            print(f"{prefix}Create: {label['name']} (#{label['color']})")
            if not dry_run:
                gh("label", "create", label["name"], "--color", label["color"], "--description", label["description"])
        elif action == "update":
            rename = f" (was '{current_name}')" if current_name != label["name"] else ""
            print(f"{prefix}Update: {label['name']}{rename}")
            if not dry_run:
                gh("label", "edit", current_name, "--name", label["name"], "--color", label["color"],
                   "--description", label["description"])
        elif action == "delete":
            print(f"{prefix}Delete: {current_name}")
            if not dry_run:
                gh("label", "delete", current_name, "--yes")
    return counts


def write_summary(counts, dry_run, path):
    """Appends a short result table to the GitHub job summary, if available."""
    if not path:
        return
    title = "Label sync (dry run - nothing changed)" if dry_run else "Label sync"
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"### {title}\n\n| Create | Update | Delete | Unchanged |\n|---|---|---|---|\n")
        f.write(f"| {counts['create']} | {counts['update']} | {counts['delete']} | {counts['unchanged']} |\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Sync repository labels with a labels file.")
    parser.add_argument("--config", default=DEFAULT_CONFIG, help=f"path to the labels file (default: {DEFAULT_CONFIG})")
    parser.add_argument("--dry-run", action="store_true", help="only print what would change")
    args = parser.parse_args(argv)

    try:
        labels, remove_unlisted = load_config(args.config)
        existing = fetch_labels()
        print(f"{len(labels)} labels listed in {args.config}, {len(existing)} labels in the repository, "
              f"remove_unlisted: {str(remove_unlisted).lower()}")
        counts = apply(plan(labels, existing, remove_unlisted), args.dry_run)
    except (ConfigError, RuntimeError) as e:
        print(f"::error title=sync_labels::{e}")
        return 1

    print(f"Done: {counts['create']} created, {counts['update']} updated, {counts['delete']} deleted, "
          f"{counts['unchanged']} unchanged" + (" (dry run - nothing was changed)" if args.dry_run else ""))
    write_summary(counts, args.dry_run, os.environ.get("GITHUB_STEP_SUMMARY"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
