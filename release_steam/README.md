# release_steam

Reusable workflow: [`.github/workflows/release_steam.yml`](../.github/workflows/release_steam.yml)

## Purpose

Builds the mod with HEMTT on every GitHub release and publishes it to the Steam Workshop: a stable item and, optionally, a dev item. It attaches the build as a zip to the GitHub release, keeps the Workshop title, description and preview image in sync with the repository, and announces the release on Discord.

| Release event | Stable item | Dev item | Zip on the GitHub release | Discord |
|---|---|---|---|---|
| Pre-release | - | updated, if `workshop-id-dev` is set | dev build | "Dev Release!" |
| Full release | updated | updated as well, if `workshop-id-dev` is set - so dev never falls behind stable | stable build | "Stable Release!" |

A pre-release that is later promoted to a full release triggers the full release as well. Without `workshop-id-dev`, a pre-release does nothing.

For each item the workflow:

1. writes the version from the release tag (`v1.2.3` → `1.2.3`) into the `MAJOR`, `MINOR` and `PATCH` defines of `version-file`
2. creates `meta.cpp` with the item's Workshop ID and name
3. runs the HEMTT script `hemtt-script-stable` / `hemtt-script-dev`, if `.hemtt/scripts/<name>.rhai` exists (e.g. to set a dev flag)
4. builds with `hemtt release` and zips the result as `<mod-folder>-<version>.zip`
5. uploads it with [workshop-upload-extended](https://github.com/A3-AZ/workshop-upload-extended): the change note is a link to the GitHub release plus the release notes

## Triggers

`release` with `types: [prereleased, released]`. Any other event fails with an error.

## Inputs

| Input | Default | Description |
|---|---|---|
| `mod-folder` | **required** | Mod folder name, e.g. `@example_mod` |
| `mod-name` | **required** | Name of the stable mod - `meta.cpp` and Workshop title |
| `workshop-id` | **required** | Workshop item ID of the stable item |
| `workshop-id-dev` | `''` | Workshop item ID of the dev item. Empty = no dev item |
| `mod-name-dev` | `<mod-name> [DEV]` | Name of the dev mod |
| `mod-folder-dev` | `<mod-folder>_dev` | Mod folder of the dev build |
| `version-file` | `addons/main/script_version.hpp` | File with the `MAJOR`/`MINOR`/`PATCH` defines. Empty = skip |
| `hemtt-script-stable` | `set_RELEASE_VERSION_STABLE` | HEMTT script before the stable build, skipped if it does not exist |
| `hemtt-script-dev` | `set_RELEASE_VERSION_DEV` | HEMTT script before the dev build, skipped if it does not exist |
| `steam-dir` | `.steam` | Folder with the Workshop page files, see below |
| `discord-content-stable` | `Stable Release!` | Message text above the release notes for a full release, e.g. with a role ping |
| `discord-content-dev` | `Dev Release!` | Message text above the release notes for a pre-release |
| `discord-username` | `<mod-name>` | Name of the Discord bot |
| `discord-avatar-url` | `''` | Avatar of the Discord bot |
| `discord-footer-title` | `<mod-name>` | Footer text of the Discord message |
| `discord-footer-icon-url` | `''` | Footer icon of the Discord message |
| `runs-on` | `ubuntu-24.04` | Runner of the build jobs. steamcmd currently fails to update on `ubuntu-26.04` |

### Workshop page files

```
.steam/
├─ description.md     Workshop description (Markdown, converted to Steam BBCode)
├─ preview.png        preview image, max. 1 MB
└─ dev/               optional overrides for the dev item
   ├─ description.md
   └─ preview.png
```

A file that does not exist leaves that field unchanged on Steam. Once a file exists, every release overwrites manual edits of that field on the Steam page - the repository is the source of truth. The same applies to the title, which is always set from `mod-name` / `mod-name-dev`.

## Secrets

| Secret | Required | Description |
|---|---|---|
| `steam-username` | yes | Steam account that is a contributor of the Workshop items |
| `steam-password` | yes | Its password |
| `discord-webhook` | no | Discord webhook URL. Not passed = no announcement |

The Steam account must have **Steam Guard disabled** - use a dedicated account. Secrets are passed explicitly in the wrapper; organization secrets work too, except for private repositories of an organization on the GitHub Free plan, where they arrive empty. The workflow checks the Steam secrets before it builds.

## Permissions

The wrapper must grant `contents: write` (to upload the zip to the release).

## Prerequisites

- The Workshop items exist already, and the Steam account is a contributor of each.
- The repository is a HEMTT project.
- If the repository or organization restricts actions, allow `A3-AZ/*`, `arma-actions/hemtt@*` and `SethCohen/github-releases-to-discord@*`.
- Release tags start with `MAJOR.MINOR.PATCH`, optionally with a leading `v` and a suffix: `v1.2.3`, `1.2.3-rc1`.

## Installation

1. Copy [`template/release_steam.yml`](template/release_steam.yml) to `.github/workflows/release_steam.yml` of your repository.
2. Fill in `mod-folder`, `mod-name`, `workshop-id` and, if you have a dev item, `workshop-id-dev`.
3. Create the secrets `STEAM_USERNAME`, `STEAM_PASSWORD` and, optionally, `DISCORD_WEBHOOK_URL`.
4. Optionally add `.steam/description.md` and `.steam/preview.png`.
5. Remove the old release and Discord notice workflows, so a release is not published or announced twice.

## Changelog

- Initial version: stable and dev item in one workflow, Workshop title/description/preview from the repository, Discord announcement with separate texts for stable and dev.
