# validate_pr_label

Composite action: [`action.yml`](action.yml)

## Purpose

Fails a pull request that has no label - or, with `label-pattern`, no label matching that pattern. Made a required status check, it blocks merging unlabelled pull requests, so release notes drafted from labels stay complete.

The check reads the **current** labels of the pull request through the GitHub API, not the labels in the event payload. On `opened` and `reopened` it first waits `wait-seconds` (15 s by default), because labels are often added a moment after the pull request is opened - by hand or by another workflow.

## Triggers

`pull_request` with `types: [opened, labeled, unlabeled, synchronize, reopened]`:

| Type | Why |
|---|---|
| `opened`, `reopened` | Check a new pull request, after waiting for labels to arrive |
| `labeled`, `unlabeled` | Re-check when the labels change |
| `synchronize` | A new commit needs its own check result, otherwise a required check blocks the new head commit |

The wrapper also sets a `concurrency` group per pull request with `cancel-in-progress: true`. When a label is added while a run is still waiting after `opened`, the `labeled` event starts a new run and cancels the waiting one, so the newest state decides and no stale red run stays behind. This lives in the wrapper because a composite action cannot set concurrency for its job.

Other events work only with the input `pr-number` set, e.g. `workflow_dispatch` to check one pull request by hand. Pull requests from forks work with `pull_request`; the read-only token they get is enough.

## Inputs

| Input | Default | Description |
|---|---|---|
| `wait-seconds` | `15` | Seconds to wait on `opened` and `reopened` before reading the labels. `0` = no wait |
| `label-pattern` | `''` | Glob pattern a label must match to count, e.g. `pr/*`. Several patterns separated by commas or newlines (`bug, type:*`). Case is ignored. Empty = any label counts |
| `pr-number` | the event's pull request | Number of the pull request to check |
| `github-token` | `${{ github.token }}` | Token used to read the pull request |

Patterns use shell glob syntax: `*` any text, `?` one character, `[0-9]` one character from a set.

### Outputs

| Output | Description |
|---|---|
| `labels` | Comma-separated labels that matched (all labels if no pattern is set) |

## Secrets

None. The workflow uses the automatic `GITHUB_TOKEN`.

## Permissions

The wrapper must grant `pull-requests: read`.

## Prerequisites

- The repository has labels for pull requests, e.g. managed with `sync_labels` and `.github/labels.yml`.
- If the repository or organization restricts actions, allow `A3-AZ/*`.
- To block merging, make the `Validate PR label` job a required status check (*Settings → Branches* or *Settings → Rules*).

## Installation

1. Copy [`template/validate_pr_label.yml`](template/validate_pr_label.yml) to `.github/workflows/validate_pr_label.yml` of your repository.
2. Optionally set `label-pattern` if only some labels should count.
3. Remove the old label check workflow (e.g. `require_label.yml`), so pull requests are not checked twice.
4. Optionally make `Validate PR label` a required status check.

## Changelog

- Initial version, based on `require_label.yml` of ZRN-Mod-Template: English messages, new inputs `wait-seconds`, `label-pattern`, `pr-number` and `github-token`, output `labels`.
