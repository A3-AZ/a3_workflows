# validate_stringtable

Composite action: [`action.yml`](action.yml)

## Purpose

Checks every `stringtable.xml` of the mod and fails the run if one breaks a rule. Each problem shows up as an annotation on the file and line in the pull request.

| Check | Can be skipped | Rule |
|---|---|---|
| structure | no | Well-formed XML, `<Project>` as root, a `<Package>` in it, every `<Key>` has an `ID` and at least one translation |
| duplicates | no | No key ID defined twice in a file, no language twice in one key |
| `project-name` | yes | `<Project name>` equals the project prefix |
| `package-name` | yes | `<Package name>` equals the addon folder name (case does not matter) |
| `key-prefix` | yes | Key IDs start with `STR_<prefix>_<package>_`, also inside `<Container>` |
| `english-first` | yes | `English` is the first translation of every key |
| `no-original` | yes | No `<Original>` translation - English replaces it |
| `whitespace` | yes | No tabs, 4 spaces per level of `Project`, `Package`, `Container` and `Key`. Blank lines are not checked |

The project prefix comes from `prefix` in `.hemtt/project.toml`. `.git` and `.hemttout` are never searched.

The checks are a port of `tools/stringtable_validator.py` from [andx667/arma-mod-template](https://github.com/andx667/arma-mod-template) (originally from ACE3). The script ships in [`scripts/`](scripts/stringtable_validator.py), so the mod does not need a copy. It runs locally as well:

```
python3 stringtable_validator.py --root path/to/mod [--prefix mod] [--skip project-name] [--case-insensitive] [--exclude 'include/*']
```

## Triggers

The template runs on `push` to `main` and on every `pull_request`. The action only reads files, so any event with a checkout works.

## Inputs

| Input | Default | Description |
|---|---|---|
| `path` | `.` | Directory searched for `stringtable.xml` files, relative to the workspace. `.hemtt/project.toml` is read from here as well |
| `prefix` | `''` | Project prefix for the `project-name` and `key-prefix` checks. Empty = `prefix` from `.hemtt/project.toml` |
| `exclude` | `''` | Paths to skip, one glob per line, relative to `path`, e.g. `include/*`. A matching folder is skipped completely |
| `skip-checks` | `''` | Checks to turn off, comma- or space-separated: `project-name`, `package-name`, `key-prefix`, `english-first`, `no-original`, `whitespace` |
| `case-sensitive` | `true` | Compare key IDs case-sensitively, against `STR_<prefix>_<package>_` and against each other. `false` accepts e.g. `<Package name="Main">` with keys `STR_mod_main_...` - Arma looks up stringtable keys case-insensitively |

Example for the ZRN mod template (`<Package name="Main">`, keys in lowercase):

```yaml
      - uses: A3-AZ/a3_workflows/validate_stringtable@v1
        with:
          case-sensitive: 'false'
```

## Secrets

None.

## Permissions

The wrapper must grant `contents: read` (to check out the repository).

## Prerequisites

- The wrapper checks out the repository before the action runs.
- `.hemtt/project.toml` with a top-level `prefix`, or the `prefix` input. Without a prefix, the run fails - unless `project-name` and `key-prefix` are both skipped.
- The runner has `python3` 3.8 or newer. GitHub-hosted Ubuntu runners have it.
- If the repository or organization restricts actions, allow `A3-AZ/*`.

## Installation

1. Copy [`template/validate_stringtable.yml`](template/validate_stringtable.yml) to `.github/workflows/validate_stringtable.yml` of your repository.
2. Run it once. If a check fails for a convention your mod uses on purpose, set `skip-checks`, `case-sensitive` or `exclude` in the wrapper.
3. Remove the old stringtable step (e.g. `python3 tools/stringtable_validator.py` in `validate.yml`) and, once no other step uses it, `tools/stringtable_validator.py`.

## Changelog

- Initial version: port of the arma-mod-template stringtable validator with the prefix read from `.hemtt/project.toml`, switchable checks, `case-sensitive` and `exclude` inputs, and annotations with line numbers.
