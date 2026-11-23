# release_steam

Reusable workflow: [`.github/workflows/release_steam.yml`](../.github/workflows/release_steam.yml)

## Purpose

Builds the mod with HEMTT on every GitHub release and publishes it to the Steam Workshop: a stable item and, optionally, a dev item. It attaches the build as a zip to the GitHub release, keeps the Workshop title, description and preview image in sync with the repository, and announces the release on Discord.

| Release event | Stable item | Dev item | Zip on the GitHub release | Discord |
|---|---|---|---|---|
| Pre-release | - | updated, if `workshop-id-dev` is set | dev build | "<mod-name> Dev got updated - Version 1.2.3." |
| Full release | updated | updated as well, if `workshop-id-dev` is set - so dev never falls behind stable | stable build | "<mod-name> Stable got updated - Version 1.2.3." |

A pre-release that is later promoted to a full release triggers the full release as well. Without `workshop-id-dev`, a pre-release does nothing.

For each item the workflow:

1. writes the version from the release tag (`v1.2.3` → `1.2.3`) into the `MAJOR`, `MINOR` and `PATCH` defines of `version-file`
2. creates `meta.cpp` with the item's Workshop ID and name
3. runs the HEMTT script `hemtt-script-stable` / `hemtt-script-dev`, if `.hemtt/scripts/<name>.rhai` exists (e.g. to set a dev flag)
4. builds with `hemtt release` and zips the result as `<mod-folder>-<version>.zip`
5. uploads it with [workshop-upload-extended](https://github.com/A3-AZ/workshop-upload-extended): the change note is a link to the GitHub release plus the release notes
6. attaches the zip to the GitHub release (stable build on a full release, dev build on a pre-release) - only after a successful upload, so a failed upload leaves the release without a zip. Re-running the job replaces the zip.

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
| `discord-message-stable` | `<mod-name> Stable got updated - Version <version>.` | Message text above the release notes for a full release, e.g. with a role ping |
| `discord-message-dev` | `<mod-name> Dev got updated - Version <version>.` | Message text above the release notes for a pre-release |
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
| `discord-webhook` | no | Discord webhook URL, or up to 5 URLs separated by spaces, commas or newlines. Not passed = no announcement |
| `arma3-tools-url` | no | Direct download URL of a zip with Arma 3 Tools, so HEMTT binarizes p3d/rtm/wrp files. Not passed = packed unbinarized, see [Binarization](#binarization) |

### Several Discord webhooks

The template passes two secrets, so that one can be set on the organization and the other on the repository:

```yaml
discord-webhook: ${{ secrets.DISCORD_WEBHOOK_URL }} ${{ secrets.DISCORD_WEBHOOK_URL_EXTENDED }}
```

The workflow splits the value into separate URLs, drops empty and duplicate ones and posts to the first 5 (more give a warning). A secret that is not set arrives empty and is skipped. A single secret may also hold several URLs separated by spaces. Every webhook gets the same message, so a role ping in `discord-message-stable` / `discord-message-dev` only works on the server the role belongs to.

The Steam account must have **Steam Guard disabled** - use a dedicated account. Secrets are passed explicitly in the wrapper; organization secrets work too, except for private repositories of an organization on the GitHub Free plan, where they arrive empty. The workflow checks the Steam secrets before it builds.

### Binarization

Without Arma 3 Tools on the runner, HEMTT packs `.p3d` models unbinarized (MLOD), without an error. The game then converts every model when it loads it: slower loading, and conversion warnings in the RPT (e.g. "Subskeleton index out of range" for skinned facewear) that a binarized model doesn't produce.

With `arma3-tools-url`, the workflow installs the tools with [arma-actions/arma3-tools](https://github.com/arma-actions/arma3-tools) before the build. On the default Linux runner, HEMTT runs binarize through Wine. After the build, every `.p3d` in the PBOs is checked: with the tools set, a single unbinarized model fails the build before anything is uploaded; without them, unbinarized models only give a warning.

The zip needs the folders `Binarize` and `BinMake` of an Arma 3 Tools installation at its root, with forward slashes in the paths (`tar -a -cf` on Windows, not PowerShell 5.1's `Compress-Archive`). `binarize_x64.exe` with its 64-bit DLLs is enough; leaving out `binarize.exe`, the `*_32.dll` files and `PhysXGpu_*.dll` brings the zip to about 18 MB.

Host it where a plain HTTP GET returns the file: a Nextcloud share link with `/download` appended, a webspace folder, a storage bucket. Not a private GitHub release (needs a token), Google Drive or OneDrive (confirmation pages). The Arma 3 Tools are Bohemia Interactive's software, so keep the URL in a secret and the link unlisted.

## Permissions

The wrapper must grant `contents: write` (to upload the zip to the release).

## Prerequisites

- The Workshop items exist already, and the Steam account is a contributor of each.
- The repository is a HEMTT project.
- If the repository or organization restricts actions, allow `A3-AZ/*`, `arma-actions/hemtt@*`, `arma-actions/arma3-tools@*` and `SethCohen/github-releases-to-discord@*`.
- Release tags start with `MAJOR.MINOR.PATCH`, optionally with a leading `v` and a suffix: `v1.2.3`, `1.2.3-rc1`.

## Installation

1. Copy [`template/release_steam.yml`](template/release_steam.yml) to `.github/workflows/release_steam.yml` of your repository.
2. Fill in `mod-folder`, `mod-name`, `workshop-id` and, if you have a dev item, `workshop-id-dev`.
3. Create the secrets `STEAM_USERNAME`, `STEAM_PASSWORD` and, optionally, `DISCORD_WEBHOOK_URL` and/or `DISCORD_WEBHOOK_URL_EXTENDED` and `ARMA3_TOOLS_URL` (see [Binarization](#binarization)).
4. Optionally add `.steam/description.md` and `.steam/preview.png`.
5. Remove the old release and Discord notice workflows, so a release is not published or announced twice.

## Changelog

- Initial version: stable and dev item in one workflow, Workshop title/description/preview from the repository, Discord announcement with separate texts for stable and dev.
- The zip is attached to the GitHub release only after the Workshop upload succeeded, no longer before it.
- `discord-webhook` accepts up to 5 URLs; the template passes `DISCORD_WEBHOOK_URL` and `DISCORD_WEBHOOK_URL_EXTENDED`.
- The default Discord message text is now `<mod-name> Stable/Dev got updated - Version <version>.`, instead of `Stable Release!` / `Dev Release!`.
- **Breaking:** `discord-content-stable` / `discord-content-dev` are renamed to `discord-message-stable` / `discord-message-dev`. A wrapper that still passes the old names fails.
- Optional secret `arma3-tools-url`: installs Arma 3 Tools so HEMTT binarizes the models. Every build now checks its `.p3d` files: unbinarized ones fail the build when the tools are set, and only give a warning otherwise.
