# validate_config

Composite action: [`action.yml`](action.yml) · Checker: [`scripts/validate_config.py`](scripts/validate_config.py)

## Purpose

Checks the config style of an Arma 3 mod - every `.cpp`, `.hpp`, `.rvmat` and `.cfg` file below `addons/` and `optionals/` - and fails the run on errors. The checker ships with the action, so the mod repository no longer needs `tools/validate_config.py` or `tools/config_style_checker.py`.

| Check | Result |
|---|---|
| Tab character | error |
| Closing bracket `)` `]` `}` directly after an opening bracket of another kind, e.g. `{(}` | error |
| Unequal number of `(` and `)`, `[` and `]`, or `{` and `}` in a file | error |
| `class A : B` - space before the inheritance colon | warning |
| `class A:B` - no space after the colon | warning |
| `class A{` - no space before the opening brace | warning |
| `class` line without `{` or `;` - brace on the next line | warning |

Strings (`"..."`, `'...'`) and comments (`//`, `/* */`) are skipped by the error checks. The warning checks look at raw lines.

Errors and warnings are printed to the log and shown as annotations on the changed files of a pull request. Only errors fail the run.

## Triggers

The template runs on `push` to `main` and on `pull_request` against `main`. Any event with the source checked out works.

## Inputs

| Input | Default | Description |
|---|---|---|
| `path` | `.` | Root of the mod, relative to the workspace. Set it if the mod is checked out into a subfolder |
| `folders` | `addons optionals` | Space-separated folders below `path` to scan. Folders that do not exist are skipped |
| `extensions` | `cpp hpp rvmat cfg` | Space-separated file extensions to check (case-sensitive) |

## Secrets

None.

## Permissions

The wrapper must grant `contents: read`.

## Prerequisites

- The repository is checked out before the action runs (`actions/checkout`).
- The runner has `python3` - all GitHub-hosted Linux runners do. Only the Python standard library is used.
- If the repository or organization restricts actions, allow `A3-AZ/*`.

## Installation

1. Copy [`template/validate_config.yml`](template/validate_config.yml) to `.github/workflows/validate_config.yml` of your repository.
2. Remove the old workflow that called `tools/validate_config.py` or `tools/config_style_checker.py` (in andx667's template this is the *Validate Config* step of `validate.yml`; keep its stringtable step or replace it with `validate_stringtable`).
3. Delete `tools/validate_config.py` / `tools/config_style_checker.py` unless you still run it locally.

To run the checker locally: `python3 validate_config/scripts/validate_config.py --path <mod-root>` from a checkout of this repository.

## Changelog

- Initial version: merged `tools/validate_config.py` (ZRN-Mod-Template) and `tools/config_style_checker.py` (andx667/arma-mod-template), which ran the same checks. Results are unchanged; the exit code is now always 1 on errors (the old scripts returned the error count, which wrapped to 0 at 256 errors). New: GitHub annotations, a warning count, and the `path`, `folders` and `extensions` inputs.
