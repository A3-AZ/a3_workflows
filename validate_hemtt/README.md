# validate_hemtt

Composite action: [`action.yml`](action.yml)

## Purpose

Runs [`hemtt check`](https://hemtt.dev/commands/check.html) on the mod, so config, preprocessor and SQF errors fail the push or pull request before anything is built or released.

The action does **not** check out the code. The wrapper does that with `actions/checkout` and then calls the action. This keeps the action composable: it checks whatever tree the job prepared, whether that is the repository root, a sub folder or a modified copy. If the project is missing, the action stops with a clear error instead of failing inside HEMTT.

Steps:

1. checks that `working-directory` holds a HEMTT project (`.hemtt/project.toml`)
2. installs HEMTT with [`arma-actions/hemtt`](https://github.com/arma-actions/hemtt), authenticated with `github-token` to avoid API rate limits
3. runs `hemtt check` with `check-args`

A mod template with raw placeholders (e.g. `~PREFIX~`) can't pass `hemtt check`. Skip the job in the template repository itself with `if: github.repository != '<owner>/<template>'` - mods created from the template then run it as usual.

## Triggers

The template runs on `push` to `main` and on `pull_request` against `main`. Any event that checks out a HEMTT project works, e.g. add `workflow_dispatch` for manual runs or extra branches for long-lived development branches.

## Inputs

| Input | Default | Description |
|---|---|---|
| `working-directory` | `.` | Folder of the HEMTT project (holds `.hemtt/project.toml`), relative to the workspace |
| `hemtt-version` | `latest` | HEMTT version to install, e.g. `v1.15.0` to pin one |
| `check-args` | `''` | Extra arguments for `hemtt check`, split on spaces, e.g. `--pedantic` |
| `github-token` | `${{ github.token }}` | Token for the HEMTT download. The default is fine; it only raises the GitHub API rate limit |

## Secrets

None. The default `github-token` is the job's own token.

## Permissions

The wrapper should grant `contents: read`, which `actions/checkout` needs. The action itself needs no further permission.

## Prerequisites

- The repository is a HEMTT project: `.hemtt/project.toml` exists in `working-directory`.
- The job checks out the code before calling the action.
- If the repository or organization restricts actions, allow `A3-AZ/*`, `actions/checkout@*` and `arma-actions/hemtt@*`.

## Installation

1. Copy [`template/validate_hemtt.yml`](template/validate_hemtt.yml) to `.github/workflows/validate_hemtt.yml` of your repository.
2. Optionally set `check-args` or pin `hemtt-version`.
3. Remove the old HEMTT check workflow (e.g. `check.yml` or the old `validate_hemtt.yml`), so the check does not run twice.
4. Optionally make the `check` job a required status check in the branch protection of `main`.

## Changelog

- v1.0.1: removed `fill-template-placeholders` - template repositories skip the job instead (see Purpose). Nothing used the input yet.
- Initial version: `hemtt check` with configurable project folder, HEMTT version and extra arguments; opt-in placeholder fill for the mod template repository; authenticated HEMTT download.
