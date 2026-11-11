# sync_labels

Composite action: [`action.yml`](action.yml)

## Purpose

Applies the labels file of the repository (default `.github/labels.yml`) to its GitHub labels: creates missing labels, updates color, description and name case of existing ones and, if the file says so, deletes every label that is not listed. The labels file stays in the repository and is the source of truth; this folder ships an [example](example/labels.yml).

The run log lists every change (`Create`, `Update`, `Delete`, `Unchanged`), and the job summary shows the totals. A dry run only prints what would change.

## Triggers

`workflow_dispatch` with a boolean `dry_run` input that defaults to `true`, so a sync is always started by hand and a click on *Run workflow* without changing anything only previews the changes.

A `push` trigger with `paths: [.github/labels.yml]` on the default branch also works if you want the labels to follow every change of the file. In that case pass `dry-run: 'false'` explicitly, and mind `remove_unlisted`.

## Inputs

| Input | Default | Description |
|---|---|---|
| `labels-file` | `.github/labels.yml` | Path to the labels file, relative to the repository root |
| `dry-run` | `'true'` | `'true'` = only print what would change, `'false'` = apply the changes |
| `token` | `${{ github.token }}` | Token used to read and change the labels |
| `repository` | `${{ github.repository }}` | Repository whose labels are synced, as `owner/name` |

### Labels file

```yaml
settings:
  # false: only create/update the listed labels
  # true:  also DELETE every label of the repository that is not listed (e.g. GitHub's default labels)
  remove_unlisted: true

labels:
  - name: "pr/fix"
    color: "d73a4a"           # 6 digit hex, with or without "#" - MUST be quoted
    description: "Fixes a bug - Changelog: Bug Fixes"
```

- Names are matched case-insensitively. A label that differs only in case is renamed to the case in the file, so its pull requests and issues keep it.
- Colors must be quoted, otherwise YAML reads e.g. `000000` as the number `0` - the workflow stops with an error instead of guessing.
- `remove_unlisted` defaults to `false` when it is missing. Deleting a label removes it from every issue and pull request - run a dry run first.
- The file is checked completely before any change is made: an invalid color, a missing name or a duplicate name stops the run without touching any label.

[`example/labels.yml`](example/labels.yml) is the standard `pr/*` label set that `release-drafter` sorts into changelog categories.

## Secrets

None. The workflow uses the job's `GITHUB_TOKEN`.

## Permissions

The wrapper must grant `issues: write` (labels are managed through the issues permission) and `contents: read` (to check out the labels file). A dry run only needs `issues: read`.

## Prerequisites

- The repository is checked out before the action runs (`actions/checkout`), and the labels file exists.
- If the repository or organization restricts actions, allow `A3-AZ/*` and `actions/checkout@*`.
- The runner has Python 3 and the `gh` CLI, as GitHub-hosted Ubuntu runners do. PyYAML is installed if it is missing.

## Installation

1. Copy [`template/sync_labels.yml`](template/sync_labels.yml) to `.github/workflows/sync_labels.yml` of your repository.
2. Add `.github/labels.yml` - start from [`example/labels.yml`](example/labels.yml) and decide on `remove_unlisted`.
3. Run the workflow from the Actions tab with *Dry run* ticked and check the log.
4. Run it again with *Dry run* unticked to apply the changes.
5. Remove the old `.github/workflows/sync_labels.yml` copy and `tools/sync_labels.py`, if your repository has them.

## Changelog

- Initial version: based on the `sync_labels` workflow and `tools/sync_labels.py` of ZRN-Mod-Template. The script now ships with the action, the labels file path is an input, the whole file is validated before any change, and the result is written to the job summary.
