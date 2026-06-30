# Appz4Fun Kodi Repository

A self-hosting, multi-channel [Kodi](https://kodi.tv) add-on repository served from
GitHub Pages. A scheduled GitHub Actions workflow rebuilds the whole repository from
the source repos' GitHub Releases and deploys it — no built artifacts are committed.

**Repository home:** https://appz4fun.github.io/Appz4Fun-Kodi-Repo/

## Channels

| Channel | Install zip | Contents |
|---|---|---|
| Stable | `repository.appz4fun.stable` | Releases not marked pre-release |
| Beta | `repository.appz4fun.beta` | All releases, including pre-releases |

Install a channel's repository zip once (see the landing page), then install add-ons
from it; Kodi auto-updates along that channel.

## Adding an add-on

1. Make sure the add-on's repo publishes a GitHub Release whose asset is a proper
   Kodi add-on zip (unzipping yields a top-level `<id>/` folder containing `addon.xml`).
2. Add `"owner/repo"` to `repositories` in [`sources.json`](sources.json).
3. Push to `main` — the workflow rebuilds and redeploys automatically.

Stable vs. beta is decided per release by the GitHub **pre-release** checkbox.

## Local build

```bash
python3 build/build_repo.py        # writes ./out
python3 -m pytest -q                # run the test suite (needs: pip install -r requirements-dev.txt)
```

## One-time GitHub setup

- **Settings → Pages → Build and deployment → Source: GitHub Actions.**
- The default `GITHUB_TOKEN` is sufficient for the build (source repos are public).

## Optional: instant updates from source CI

The daily schedule guarantees updates within ~24h. For near-instant updates, have each
source repo notify this repo when it publishes a release:

1. Create a fine-grained PAT with **Contents: read and write** scoped to
   `Appz4Fun/Appz4Fun-Kodi-Repo` only. Store it in the **source** repo as the secret
   `REPO_DISPATCH_TOKEN`.
2. Add this step to the source repo's release workflow (after the release is published):

```yaml
- name: Notify Kodi repository
  run: |
    curl -sf -X POST \
      -H "Authorization: Bearer ${{ secrets.REPO_DISPATCH_TOKEN }}" \
      -H "Accept: application/vnd.github+json" \
      https://api.github.com/repos/Appz4Fun/Appz4Fun-Kodi-Repo/dispatches \
      -d '{"event_type":"addon-released"}'
```

## How it works

`build/build_repo.py` lists each source repo's releases, downloads each release's
add-on zip (cached by asset id), reads the authoritative `id`/`version` from the
`addon.xml` inside each zip, and for both channels lays out every version under
`<channel>/<id>/<id>-<version>.zip`, extracts the newest version's artwork, writes
`<channel>/addons.xml` (+ `.md5`) advertising the newest version of each add-on plus
the channel's own repository add-on, and renders `index.html`. The whole tree is
deployed to GitHub Pages as an artifact. See
[`docs/superpowers/specs/2026-06-29-kodi-repository-design.md`](docs/superpowers/specs/2026-06-29-kodi-repository-design.md).
