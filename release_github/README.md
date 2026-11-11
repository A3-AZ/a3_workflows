# release_github

Composite action: [`action.yml`](action.yml)

## Purpose

Builds the mod with `hemtt release` on every full GitHub release and attaches HEMTT's zip to that release as `<prefix>-<tag>.zip`. It is meant for mods that do not publish to the Steam Workshop from CI, e.g. because they publish with `hemtt publish` or by hand. To build, attach the zip **and** upload to the Steam Workshop, use [`release_steam`](../release_steam/README.md) instead - do not use both in one repository.

The action:

1. reads `prefix` from `.hemtt/project.toml`
2. sets up HEMTT and runs `hemtt release`, which builds, signs and zips the mod as `releases/<prefix>-latest.zip`
3. attaches that zip to the release under `asset-name` with `gh release upload --clobber` - an existing asset of the same name is replaced, so a re-run is safe

The version inside the build comes from HEMTT's own version source (usually `addons/main/script_version.hpp`), not from the release tag.

## Triggers

The template uses `release` with `types: [released]`: full releases only, including a pre-release that is promoted to a full release. Add `prereleased` to attach zips to pre-releases as well.

On any other event the action needs the input `tag`, or `upload: 'false'` for a build-only dry run.

## Inputs

| Input | Default | Description |
|---|---|---|
| `tag` | tag of the release event | Release to attach the zip to |
| `asset-name` | `{prefix}-{tag}.zip` | File name of the zip on the release. `{prefix}` and `{tag}` are replaced |
| `upload` | `true` | `false` = build and check the zip, but do not attach it (dry run) |
| `token` | `github.token` | Token for the HEMTT setup and the upload. Needs `contents: write` |

Outputs: `prefix`, `zip` (path of the renamed zip on the runner) and `asset-name` - e.g. to pass the zip on to a later step.

## Secrets

None. The action uses the workflow's `GITHUB_TOKEN`.

## Permissions

The wrapper must grant `contents: write` (to upload the zip to the release).

## Prerequisites

- The repository is a HEMTT project, and `.hemtt/project.toml` sets `prefix` at the top level.
- The wrapper checks out the repository before the action - the action checks out nothing itself.
- If the repository or organization restricts actions, allow `A3-AZ/*` and `arma-actions/hemtt@*`.

## Installation

1. Copy [`template/release_github.yml`](template/release_github.yml) to `.github/workflows/release_github.yml` of your repository. There are no values to fill in.
2. Remove the old release workflow (e.g. `release.yml` with `svenstaro/upload-release-action`), so the zip is not built and attached twice.

## Changelog

- Initial version: `hemtt release` and `gh release upload` of `<prefix>-<tag>.zip`, prefix read from `.hemtt/project.toml`, optional `asset-name` and dry run.
