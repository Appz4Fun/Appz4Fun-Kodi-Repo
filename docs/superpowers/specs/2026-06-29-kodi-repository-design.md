# Appz4Fun Kodi Repository — Design Spec

**Date:** 2026-06-29
**Status:** Approved (design), pending implementation plan
**Repo:** https://github.com/Appz4Fun/Appz4Fun-Kodi-Repo
**Served at:** https://appz4fun.github.io/Appz4Fun-Kodi-Repo/

## 1. Goal

A standard, self-hosting **multi-channel Kodi repository** served from GitHub Pages.
A scheduled GitHub Actions workflow rebuilds the entire repository from the source
repositories' GitHub Releases and deploys it as a Pages artifact. Two channels —
**stable** and **beta** — are each a real Kodi repository addon a user installs once
for auto-updates.

Non-goals:
- This repo does **not** build addons. Addon zips are produced by each source repo's
  own CI and attached to GitHub Releases. This repo only aggregates and serves them.
- No content is hosted beyond addon zips and repository metadata.

## 2. Key decisions (from brainstorming)

| Decision | Choice |
|---|---|
| Pages publishing | GitHub Actions artifact deploy (`actions/deploy-pages`) — **no generated files committed** |
| Version retention | Keep **all** historical zips for rollback |
| Sync cadence | Daily cron + manual dispatch + **instant** `repository_dispatch` from source CI |
| Channels | **One** site, **two** channel repository addons (`/stable`, `/beta`) |
| Beta vs stable classification | GitHub **pre-release flag**: stable = non-pre-release releases; beta = all releases |
| Builder language | Python 3 standard library only (no pip dependencies) |

## 3. This git repo's layout (hand-maintained source of truth)

```
sources.json                 # the set of source repositories to aggregate
build/
  build_repo.py              # core builder (Python 3 stdlib; no deps)
  templates/
    repository.addon.xml     # template for the repository addon's addon.xml
    index.html               # template for the landing page
assets/
  icon.png                   # artwork for the repository addons
  fanart.png
.github/workflows/sync.yml   # scheduled / triggered build + deploy
docs/superpowers/specs/      # this design doc
README.md                    # human docs: install + instant-update wiring
```

`sources.json` is a flat list so adding an addon later is a one-line edit:

```json
{ "repositories": ["Appz4Fun/nzbdavkodi"] }
```

## 4. Served Pages layout (generated each run, never committed)

```
/index.html                          # landing page: install links + version table
/stable/
  addons.xml
  addons.xml.md5
  repository.appz4fun.stable/
    repository.appz4fun.stable-1.0.0.zip
  plugin.video.nzbdav/
    plugin.video.nzbdav-1.2.3.zip     # every stable version retained
    plugin.video.nzbdav-1.2.2.zip
    ...
    icon.png                          # extracted from newest, for pre-install artwork
    fanart.jpg
/beta/
  addons.xml
  addons.xml.md5
  repository.appz4fun.beta/
    repository.appz4fun.beta-1.0.0.zip
  plugin.video.nzbdav/
    ...                               # all versions incl. pre-releases
```

Beta is a superset of stable (it includes pre-release builds). Stable zips are
duplicated into both trees; this is intentional for layout clarity and is cheap
(addon zips are small).

## 5. Builder (`build_repo.py`) — core algorithm

For each channel in `{stable, beta}`, for each source repo in `sources.json`:

1. **List releases** via the GitHub REST API using the workflow's `GITHUB_TOKEN`
   (source repos are public; token is for rate limits). Skip **drafts**.
2. **Select by channel:** stable = releases where `prerelease == false`; beta = all
   (published) releases.
3. For each selected release, find its addon `.zip` asset. Read the **authoritative**
   `id` and `version` from the `addon.xml` *inside the zip* — never trust the filename.
4. **Lay out zips:** copy each version's zip to `<channel>/<id>/<id>-<version>.zip`.
   Extract the newest version's `icon`/`fanart` assets (paths from its `addon.xml`
   `<assets>`) into `<channel>/<id>/icon.png` and `fanart.jpg`.
5. **Aggregate metadata:** select the newest version per addon (by parsed version, not
   release date), collect its full `<addon>...</addon>` element, append the channel's
   own repository addon element, and write `<channel>/addons.xml` wrapped in
   `<addons>...</addons>`. Write `<channel>/addons.xml.md5` = md5 hex digest of the
   `addons.xml` file bytes.
6. **Repository addon:** render the repository addon's `addon.xml` from the template
   with the channel's Pages URLs, bundle it with `assets/icon.png` + `fanart.png`, and
   zip it to `<channel>/repository.appz4fun.<channel>/repository.appz4fun.<channel>-<ver>.zip`.

Finally render `/index.html` from the template with a table of the addons/versions
present in each channel and the install links.

The build is **idempotent**: every run is a full rebuild from Releases (the source of
truth), so "keep all versions" requires no stored state.

### Version comparison

Parse addon versions as Kodi-style `major.minor.patch` with an optional pre-tag
suffix; compare numerically component-by-component to pick the newest per addon. The
**channel** of a build is decided by the GitHub pre-release flag, independent of the
version string.

## 6. The two repository addons

| Channel | id | name | datadir |
|---|---|---|---|
| Stable | `repository.appz4fun.stable` | Appz4Fun Repository | `…/stable/` |
| Beta | `repository.appz4fun.beta` | Appz4Fun Repository (Beta) | `…/beta/` |

Each `addon.xml` is an `xbmc.addon.repository` extension with, for its channel:

```xml
<dir>
  <info compressed="false">https://appz4fun.github.io/Appz4Fun-Kodi-Repo/<channel>/addons.xml</info>
  <checksum>https://appz4fun.github.io/Appz4Fun-Kodi-Repo/<channel>/addons.xml.md5</checksum>
  <datadir zip="true">https://appz4fun.github.io/Appz4Fun-Kodi-Repo/<channel>/</datadir>
</dir>
```

Distinct ids mean a user can install both channels side-by-side without conflict. Each
repository addon is also listed in its own channel's `addons.xml` so Kodi can
auto-update the repository addon itself. Repository addon version starts at `1.0.0` and
is bumped manually when the datadir layout or URLs change.

## 7. Workflow triggers (`sync.yml`)

- `schedule:` daily cron at a low-traffic UTC hour.
- `workflow_dispatch:` manual "Run workflow" button.
- `repository_dispatch: { types: [addon-released] }` — the **instant** trigger.
- `push:` to `main` touching `sources.json`, `build/`, or `assets/` — redeploy on
  config/code change.

Permissions: `pages: write`, `id-token: write`, `contents: read`. Standard
`actions/configure-pages` → build → `actions/upload-pages-artifact` →
`actions/deploy-pages` flow. Concurrency group `pages` with cancel-in-progress so
overlapping triggers don't race.

### Instant-update wiring (per source repo)

GitHub's default `GITHUB_TOKEN` cannot reach across repositories, so each source repo
stores a fine-grained PAT secret `REPO_DISPATCH_TOKEN` (Contents: read+write scoped to
this repo only) and, after publishing a release, runs:

```yaml
- name: Notify Kodi repository
  run: |
    curl -sf -X POST \
      -H "Authorization: Bearer ${{ secrets.REPO_DISPATCH_TOKEN }}" \
      -H "Accept: application/vnd.github+json" \
      https://api.github.com/repos/Appz4Fun/Appz4Fun-Kodi-Repo/dispatches \
      -d '{"event_type":"addon-released"}'
```

This is optional polish documented in the README; the daily schedule guarantees
updates regardless.

## 8. Caching, errors, edge cases

- **Cache:** `actions/cache` stores downloaded release zips keyed on a manifest of
  release asset sha256 digests (returned by the API). Unchanged assets are not
  re-downloaded.
- **Release with no usable `.zip` asset** → skip with a logged warning; do not fail the
  build.
- **Addon with only pre-releases** → present in beta, absent from stable (correct).
- **Build failure or empty `addons.xml`** → the workflow fails loudly and the previous
  Pages deployment stays live; never publish a partial/empty repo.
- **Multiple `.zip` assets on one release** → prefer the asset whose name matches
  `<id>-<version>.zip`; if ambiguous, log and skip that release.

## 9. Testing

`build_repo.py` is plain stdlib and unit-testable offline. Built test-first against
fixtures (fake release JSON + a sample addon zip):

- zip layout: each version lands at `<channel>/<id>/<id>-<version>.zip`.
- `addons.xml` aggregation: newest `<addon>` per addon + the repository addon element.
- `addons.xml.md5` matches the md5 of the generated `addons.xml` bytes.
- channel split: pre-release builds appear in beta only.
- version pick: newest version chosen by parsed version, not date.
- artwork extraction from the newest zip.
- edge cases: no-zip release skipped, prerelease-only addon absent from stable.

## 10. What a user does to install

1. Settings → System → Add-ons → enable **Unknown sources**.
2. Add-ons → Install from zip file → the channel's `repository.appz4fun.<channel>-x.y.z.zip`
   (linked from the landing page).
3. Add-ons → Install from repository → Appz4Fun Repository → Video add-ons → install.
4. Kodi auto-updates from then on along the chosen channel.
