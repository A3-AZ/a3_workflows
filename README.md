# a3_workflows

Shared GitHub Actions workflows for Arma 3 mod projects - maintained in one place, used by many repositories.

## Why this exists

Arma 3 mod repositories tend to carry the same CI: run `hemtt check`, validate configs and stringtables, require PR labels, draft release notes, publish to the Steam Workshop, announce releases on Discord.

When every repository holds its own copy of those workflows and their helper scripts, the copies drift apart, and every fix or improvement has to be ported into each repository by hand.

This repository solves that:

- **Each workflow lives here once** - logic, scripts and documentation.
- **Target repositories only hold a small wrapper** that decides *when* the workflow runs and passes in the repository-specific values.
- **Changes reach every repository automatically** - fix it here, release it, and the next run in every repository uses the fixed version. No pull requests in the target repositories.

Everything here is public and meant for community use. You are welcome to use these workflows in your own mods.

## How it works

```
 your-mod/.github/workflows/validate_hemtt.yml          a3_workflows
 ┌─────────────────────────────────────────────┐         ┌────────────────────────────┐
 │ on: push / pull_request          (trigger)  │         │ validate_hemtt/action.yml  │
 │ permissions: ...                 (access)   │  ─────► │   the actual steps         │
 │ uses: A3-AZ/a3_workflows/validate_hemtt@v1  │         │   + bundled scripts        │
 │ with: <repo-specific inputs and secrets>    │         └────────────────────────────┘
 └─────────────────────────────────────────────┘
           the wrapper - set up once                    maintained here, updated centrally
```

Most workflows are [composite actions](https://docs.github.com/en/actions/sharing-automations/creating-actions/creating-a-composite-action): the wrapper keeps the triggers, permissions and job layout, the action provides the steps. Scripts the action needs ship inside its folder, so target repositories do not need a `tools/` copy of them.

Where a workflow needs several jobs, it can instead be a [reusable workflow](https://docs.github.com/en/actions/sharing-automations/reusing-workflows). GitHub requires those files to sit in `.github/workflows/` of this repository - the workflow's folder still holds its README, scripts and template.

These workflows build on the generic actions from [arma-actions](https://github.com/arma-actions) (e.g. `arma-actions/hemtt`). Fixes that belong to such a building block go upstream there, not into a workaround here.

## Repository layout

```
a3_workflows/
├─ README.md                  this file
├─ CONTRIBUTING.md            how to add or change a workflow
├─ CHANGELOG.md               release history
├─ _template/                 skeleton for a new workflow folder
├─ <workflow-name>/           one folder per workflow, e.g. validate_hemtt/
│  ├─ action.yml              the workflow logic (composite action)
│  ├─ scripts/                helper scripts used by action.yml (optional)
│  ├─ template/
│  │  └─ <workflow-name>.yml  wrapper - copy to .github/workflows/ of the target repo
│  └─ README.md               documentation, see below
└─ .github/workflows/         CI of this repository + reusable workflows
```

Rules for a workflow folder:

- **Self-contained.** A folder never depends on files of another folder. This keeps every workflow independently understandable - and lets one be moved into a standalone repository later if it becomes useful beyond this collection.
- **The name says what it does.** Every workflow is named `<verb>_<object>` in lowercase snake_case: `validate_hemtt`, `sync_labels`, `release_steam`. Workflows doing the same kind of job share the verb, so they sort next to each other. Variants of one job differ only in the object: `release_steam` vs. `release_github`.

### Workflow README

Every workflow folder has a README with these sections, in this order:

1. **Purpose** - what it does, in one or two sentences
2. **Triggers** - which events the template uses, and which ones make sense
3. **Inputs** - name, description, default, required
4. **Secrets** - which secrets to create and how to pass them
5. **Permissions** - what the wrapper must grant
6. **Prerequisites** - what the target repository needs (config files, HEMTT scripts, labels, repository settings)
7. **Installation** - step by step
8. **Changelog** - notable changes of this workflow

## Using a workflow

1. **Allow the actions.** If your repository or organization restricts which actions may run (*Settings → Actions → General*), add `A3-AZ/a3_workflows/*` plus the third-party actions the workflow's README lists under *Prerequisites*.
2. **Copy the wrapper.** Copy `<workflow-name>/template/<workflow-name>.yml` into `.github/workflows/` of your repository.
3. **Fill in the values.** Set the inputs marked as required in the wrapper.
4. **Create the secrets** the workflow needs (*Settings → Secrets and variables → Actions*).
5. **Add repository data files** if the workflow needs them, e.g. `.github/labels.yml`.

Secrets are always passed explicitly from the wrapper (`with: steam-password: ${{ secrets.STEAM_PASSWORD }}`). `secrets: inherit` does not work across organizations, and explicit secrets make clear which workflow receives what.

## Versioning

Releases follow [semantic versioning](https://semver.org) for the repository as a whole: `v1.0.0`, `v1.1.0`, `v1.1.1`, ...

In addition there is a **moving major tag** - `v1`, later `v2` - that always points to the latest release of that major version. This is the reference wrappers should use:

| Reference in the wrapper | Changes arrive | Recommended |
|---|---|---|
| `@v1` | automatically, each time a new `v1.x.y` is released | **yes** |
| `@v1.2.0` or a commit SHA | never automatically - update by hand or via Dependabot | if you want full control |
| `@main` | immediately on every merge, without a release | no |

What counts as a **breaking change** (new major version):

- a new **required** input or secret
- a removed or renamed input or output
- a changed default that alters behaviour in existing repositories
- a new permission the wrapper has to grant

Anything else - bug fixes, new optional inputs with a sensible default, improved steps or scripts - is released within the current major version and reaches all repositories automatically.

## Design rules

- **English only** - code, comments, log output and documentation.
- **New inputs get a default.** Then adding them is not a breaking change.
- **Repository data stays in the repository.** Files such as `labels.yml` or `release-drafter.yml` describe a project, not the pipeline. Workflows read them; this repository documents their format and ships an example.
- **Fail early and clearly.** Check secrets and inputs at the start of a run and stop with a readable error, instead of failing deep inside a third-party tool.
- **No hidden special cases.** Behaviour that only one repository needs is an opt-in input, documented in the README.

## Workflows

| Workflow | Purpose | Status |
|---|---|---|
| `validate_hemtt` | Run `hemtt check` | planned |
| `validate_config` | Check config style | planned |
| `validate_stringtable` | Check stringtable files | planned |
| `validate_pr_label` | Fail pull requests without a label | planned |
| `sync_labels` | Apply `.github/labels.yml` to the repository | planned |
| `update_translation_issue` | Keep a GitHub issue updated with `hemtt localization coverage` | planned |
| `draft_release` | Draft release notes from labelled pull requests | planned |
| `release_github` | Build with HEMTT and attach the zip to the GitHub release | planned |
| `release_steam` | Build with HEMTT, attach the zip to the GitHub release and upload to the Steam Workshop - stable and optional dev item in one workflow, optional description and preview image from `.steam/` | planned |
| `announce_discord` | Announce a release on Discord | planned |

## Contributing

Changes go through pull requests and need a review by a maintainer. Before a change is released it is tested against a real mod repository. See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## Maintainers

- [OverlordZorn](https://github.com/OverlordZorn)
- [Andx667](https://github.com/Andx667)
