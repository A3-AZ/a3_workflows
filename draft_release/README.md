# draft_release

Composite action: [`action.yml`](action.yml)

## Purpose

Keeps a draft GitHub release up to date with release notes built from the pull requests merged since the last release, sorted into sections by their labels. It wraps [release-drafter](https://github.com/release-drafter/release-drafter) (`@v7`). Publishing the draft is up to you - `release_steam` or `release_github` take over from there.

The release notes format lives in the mod repository (`.github/release-drafter.yml`), not here. This folder ships [`example/release-drafter.yml`](example/release-drafter.yml), which sorts pull requests by the `pr/*` labels:

| Changelog section | Labels |
|---|---|
| Features 🚀 | `pr/new`, `pr/improvement` |
| Bug Fixes 🐛 | `pr/fix` |
| Settings ⚙️ | `pr/settings` |
| Translation 📚 | `pr/translation` |
| Documentation 📚 | `pr/docs` |
| Maintenance 🛠️ | `pr/maintenance`, `pr/cleanup` |
| Breaking Changes ⚠️ | `pr/breaking` |
| *left out* | `pr/ignore` |

These are the labels of the `sync_labels` example `labels.yml`; `validate_pr_label` with `label-pattern: 'pr/*'` makes sure every pull request has one. A pull request with labels of several sections is listed in each. If you rename or add labels, change both `labels.yml` and `release-drafter.yml`.

The example names the draft `v$NEXT_PATCH_VERSION` (last release `v1.2.3` → `v1.2.4`). To bump the version from the labels instead, add `semver-increment: major` / `minor` to a category and use `v$RESOLVED_VERSION` - see [Version resolver](https://github.com/release-drafter/release-drafter#version-resolver).

### Sharing one config across repositories

Instead of copying the example, a repository can extend it. Put this into `.github/release-drafter.yml`:

```yaml
_extends: A3-AZ/a3_workflows:/draft_release/example/release-drafter.yml@v1
```

release-drafter loads the file through the GitHub API with the workflow's own token - this works because `A3-AZ/a3_workflows` is public, no extra token or secret is needed. Keys you set in your own file replace the inherited ones; to add categories instead of replacing them, use the mapping form:

```yaml
_extends:
  from: A3-AZ/a3_workflows:/draft_release/example/release-drafter.yml@v1
  strategy:
    categories: append
categories:
  - title: 'Compatibility 🔗'
    when:
      label: pr/compat
```

Keep the `@v1` (or pin a release tag): without a ref the file is read from `main` and changes with every merge here. The leading `/` matters - without it the path is relative to `.github/`. Copying the example is still the default: the release notes format is repository data, and extending ties your changelog layout to this repository.

## Triggers

The template uses `push` to `main` - every merge updates the draft - and `workflow_dispatch` to rebuild it by hand. A `concurrency` group lets only the newest run finish.

Other events work too: on `pull_request` release-drafter only logs the result (dry-run), since a pull request merge ref is temporary. For a release branch, add it to `push.branches` and set `commitish`.

### Forks

With `skip-forks: 'true'` (default) the action skips with a notice when `github.event.repository.fork` is true, so a fork that has Actions enabled does not draft releases of its own. This replaces the hardcoded `if: github.repository == 'owner/repo'` of the old templates, which had to be edited in every new repository. Repositories created with *Use this template* are not forks and draft normally.

## Inputs

| Input | Default | Description |
|---|---|---|
| `config-name` | `release-drafter.yml` | Config target. A relative path starts in `.github/`; `/path` starts at the repository root; `owner/repo:/path@ref` reads another repository; `file:path` reads a file from the runner (needs `actions/checkout`) |
| `skip-forks` | `'true'` | Skip the run when the repository is a fork |
| `token` | `github.token` | Token for the GitHub API |
| `commitish` | `''` | Release target. Empty = the branch that triggered the run |
| `from` | `''` | Baseline for the change list. Empty = the last published release |
| `name` | `''` | Release name, overrides `name-template` |
| `tag` | `''` | Release tag, overrides `tag-template` |
| `version` | `''` | Overrides the calculated version |
| `prerelease` | `''` | `'true'` = draft a prerelease |
| `prerelease-identifier` | `''` | e.g. `rc`, `beta`. Enables `prerelease` |
| `include-pre-releases` | `''` | `'true'` = prereleases count as the last release |
| `filter-by-range` | `''` | Only consider previous releases whose tag satisfies this SemVer range |
| `header` | `''` | Text before the release notes |
| `footer` | `''` | Text after the release notes |
| `dry-run` | `''` | `'true'` = only log the draft, write nothing |

Empty inputs fall back to the value in the config file, then to release-drafter's default. Outputs: `skipped`, `id`, `name`, `tag_name`, `body`, `labels`, `html_url`, `resolved_version`.

## Secrets

None. The workflow's own `GITHUB_TOKEN` is enough, also for `_extends` from this public repository.

## Permissions

The job must grant `contents: write` (create and update the draft release) and `pull-requests: read` (read the merged pull requests and their labels).

## Prerequisites

- `.github/release-drafter.yml` in the repository - copy [`example/release-drafter.yml`](example/release-drafter.yml) or extend it, see above. Without it, release-drafter also looks in the organization's `.github` repository before it fails.
- The labels the config uses exist in the repository - see `sync_labels`.
- If the repository or organization restricts actions, allow `A3-AZ/*` and `release-drafter/release-drafter@*`.

Configs written for release-drafter v6 still load, but category `labels:` and `exclude-labels` are deprecated in v7 and log a warning. The example uses the v7 form (`when:` and a `type: pre-exclude` category).

## Installation

1. Copy [`example/release-drafter.yml`](example/release-drafter.yml) to `.github/release-drafter.yml` of your repository and adjust the sections - or extend it, see *Sharing one config across repositories*.
2. Copy [`template/draft_release.yml`](template/draft_release.yml) to `.github/workflows/draft_release.yml`.
3. Remove the old `release-drafter.yml` workflow, so the draft is not written twice.
4. Merge a labelled pull request, or run the workflow by hand, and check the draft under *Releases*.

## Changelog

- Initial version: release-drafter v7, config from the mod repository, `pr/*` example config, fork skip via `github.event.repository.fork`.
