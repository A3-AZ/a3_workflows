# publish_draft

Composite action: [`action.yml`](action.yml)

## Purpose

Publishes the draft GitHub release, normally the one kept up to date by [`draft_changelog`](../draft_changelog/README.md), from a manual run. You choose two things when you start it:

| Choice | Options | Result for a draft `v1.2.4` |
|---|---|---|
| `type` | `pre-release` | `v1.2.4-rc.1`, then `v1.2.4-rc.2`, ... |
| | `release` | `v1.2.4` |
| `bump` | `keep` | the draft's version, as above |
| | `minor` | `v1.3.0` / `v1.3.0-rc.N` |
| | `major` | `v2.0.0` / `v2.0.0-rc.N` |

The action:

1. finds the draft: the one named by `draft-tag`, or the only draft of the repository
2. calculates the tag from the draft's `MAJOR.MINOR.PATCH` (a suffix on the draft tag is ignored), the bump and the type. A pre-release gets the next free number `N` of `<version>-rc.N`; the count restarts for every version
3. refuses a version that already has a tag or a published release, e.g. a pre-release of `v1.2.4` after `v1.2.4` was released
4. publishes the draft under the new tag in one API request. GitHub creates the tag on the draft's target branch at that moment. A release name that contains the draft tag gets the new tag in its place; any other custom name is kept

Publishing then starts the release workflows of the repository: [`release_steam`](../release_steam/README.md) uploads a pre-release to the dev item and a release to the stable item, [`release_github`](../release_github/README.md) attaches the zip to full releases. This only happens with a token other than `GITHUB_TOKEN`, see *Secrets*.

### Pre-releases and the changelog

After a pre-release there is no draft until the next merge. The template runs `draft_changelog` first, so the draft is recreated with the same version and the changelog since the last **full** release (release-drafter ignores pre-releases by default) - a release after `v1.2.4-rc.2` is still `v1.2.4` with all changes since `v1.2.3`.

The bump is relative to the draft. If the draft already resolves a higher version (`$RESOLVED_VERSION` with `semver-increment` labels), `minor` bumps from there.

## Triggers

`workflow_dispatch` only - publishing is a decision, not a reaction to an event. The template offers `type`, `bump` and `dry-run` as inputs of the *Run workflow* form, and runs only on the default branch, since `draft_changelog` would otherwise retarget the draft to the branch the run was started on.

## Inputs

| Input | Default | Description |
|---|---|---|
| `type` | - | **Required.** `release` or `pre-release` |
| `bump` | `keep` | `keep`, `minor` (x.Y+1.0) or `major` (X+1.0.0) |
| `prerelease-identifier` | `rc` | Identifier of pre-release tags: `rc` → `v1.2.4-rc.1`, `beta` → `v1.2.4-beta.1` |
| `draft-tag` | `''` | Tag of the draft to publish. Empty = the only draft; fails if there are several |
| `dry-run` | `false` | `true` = log the tag and name, publish nothing |
| `token` | `github.token` | Token for the GitHub API, see *Secrets* |

Outputs: `id`, `tag`, `name`, `prerelease` and `html_url` (empty on a dry run).

## Secrets

GitHub does not start workflows from events caused by `GITHUB_TOKEN`. A release published with it stays silent: `release_steam` and `release_github` do not run. The action warns when it uses the default token.

To start them, create a token and store it as the secret `RELEASE_TOKEN` (*Settings → Secrets and variables → Actions*):

- **Fine-grained personal access token** (*GitHub Settings → Developer settings*): only this repository, permission *Contents: Read and write*. Releases appear as published by the token's owner. Set an expiry and renew it.
- **GitHub App** with *Contents: Read and write*, installed on the repository, and a token from [`actions/create-github-app-token`](https://github.com/actions/create-github-app-token) in a step before - better for organizations, does not expire or depend on a person.

If the repository has no release workflows, `token` can be left out.

## Permissions

The job must grant `contents: write` (publish the draft), plus `pull-requests: read` for the `draft_changelog` step of the template. A personal access token or App token brings its own permissions; the job permissions apply to `GITHUB_TOKEN` only.

## Prerequisites

- A draft release whose tag starts with `MAJOR.MINOR.PATCH`, optionally with a leading `v` - as `draft_changelog` creates it with the example config.
- The secret `RELEASE_TOKEN` if release workflows should start, see *Secrets*.
- If the repository or organization restricts actions, allow `A3-AZ/*` (plus `release-drafter/release-drafter@*` for the `draft_changelog` step).

## Installation

1. Set up [`draft_changelog`](../draft_changelog/README.md), or remove the *Update the draft* step from the template and its `draft-tag` line.
2. Create the secret `RELEASE_TOKEN`, see *Secrets*.
3. Copy [`template/publish_draft.yml`](template/publish_draft.yml) to `.github/workflows/publish_draft.yml`.
4. Run it once with *dry-run* ticked (*Actions → Release: Publish Draft → Run workflow*) and check the tag in the run summary.

## Changelog

- Initial version: publish the draft as `release` or numbered `pre-release` (`-rc.N`), optional `minor` / `major` bump for both, dry run, warning for `GITHUB_TOKEN`.
