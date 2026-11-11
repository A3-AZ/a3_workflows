# update_translation_issue

Composite action: [`action.yml`](action.yml)

## Purpose

Runs `hemtt localization coverage` and keeps one open GitHub issue updated with the coverage table, so translators can see at a glance which languages are missing strings.

The issue body looks like this:

```markdown
Translation completeness per language.

**[Translation guide](https://ace3.acemod.org/wiki/development/how-to-translate-ace3.html)**

| Language | Coverage % | Addons                    |
|----------|------------|---------------------------|
| English  | 100.00%    | None                      |
| German   | 5.88%      | addons/main and 15 more   |

_Coverage last changed in 8191a428489fc997f224fe373aa49e8d2ab2f013_
```

On each run the action:

1. generates the body above (header and guide link are optional)
2. looks for an **open** issue whose title equals `title`, ignoring case. If there are several, the oldest one is used
3. creates the issue if there is none, edits it if the body differs, and does nothing otherwise

The last line names the commit that last changed the coverage. It is ignored when comparing, so a push that does not change the coverage (e.g. a reworded English string) leaves the issue untouched. Closing the issue makes the next run create a new one.

## Triggers

The template uses `push` to `main` with `paths: '**/stringtable.xml'`, so it only runs when a stringtable changes, plus `workflow_dispatch` to run it by hand, e.g. after installing it. Running it on pull requests makes little sense - the issue should show the state of `main`; use `dry-run: 'true'` if you do.

The wrapper must check out the repository before the action runs.

## Inputs

| Input | Default | Description |
|---|---|---|
| `title` | `Translations` | Title of the issue. Matched against open issues, ignoring case |
| `header` | `Translation completeness per language.` | Text above the table. Empty = no header |
| `guide-url` | [ACE3 translation guide](https://ace3.acemod.org/wiki/development/how-to-translate-ace3.html) | URL of a translation guide, linked above the table. The ACE3 guide is a good community baseline; point it to your own guide if you have one. `''` = no link |
| `path` | `.` | Folder of the HEMTT project, relative to the workspace |
| `dry-run` | `'false'` | `'true'` = generate the report and look up the issue, but never create or edit it |
| `token` | `${{ github.token }}` | Token for the HEMTT download and the GitHub CLI |

Outputs: `result` (`created`, `updated` or `unchanged` - in dry-run what would be done), `issue-number` (empty if a dry-run would create it) and `body-file` (path of the generated body). The body is also written to the job summary.

## Secrets

None. The action uses the workflow's `GITHUB_TOKEN`.

## Permissions

The wrapper must grant `contents: read` and `issues: write`. With `dry-run: 'true'`, `issues: read` is enough.

## Prerequisites

- The repository is a HEMTT project (`.hemtt/project.toml`) with `stringtable.xml` files.
- Issues are enabled for the repository.
- If the repository or organization restricts actions, allow `A3-AZ/*`, `actions/checkout@*` and `arma-actions/hemtt@*`.

## Installation

1. Copy [`template/update_translation_issue.yml`](template/update_translation_issue.yml) to `.github/workflows/update_translation_issue.yml` of your repository.
2. Optionally set `title`, `header` and `guide-url`. To keep an existing issue, set `title` to its title (e.g. `Localization coverage`).
3. Remove the old translation or localization coverage workflow, so two workflows do not fight over the issue.
4. Run the workflow once by hand (*Actions → Update: Translation Issue → Run workflow*) to create the issue.

## Changelog

- Initial version: merged from ZRN-Mod-Template's `stringtable.yml` and andx667/hemtt-localization-issue. Configurable title, header and guide link, case-insensitive exact title match, no edit if the coverage is unchanged, dry-run mode.
