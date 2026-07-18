"""Minimal GitHub REST client + asset download cache (stdlib only)."""

import json
import os
import urllib.parse
import urllib.request

API = "https://api.github.com"


class _AuthStrippingRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Drop Authorization when a download redirects to another host.

    GitHub serves asset binaries via a 302 to its storage backend, whose
    signed URL is the only credential it accepts — forwarding the API
    Authorization header there gets the request rejected. urllib forwards
    all headers on redirect, so strip it whenever the host changes.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None and (urllib.parse.urlsplit(newurl).netloc
                                != urllib.parse.urlsplit(req.full_url).netloc):
            new.remove_header("Authorization")
        return new


def _request(url, token=None):
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "appz4fun-kodi-repo")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def list_releases(repo, token=None):
    """Return ALL published+draft releases for owner/repo (newest first).

    Pages through the GitHub API (100 per page) until a short or empty page is
    returned, so a source repo with more than 100 releases still contributes
    every historical version — the repository promises to retain them all.
    """
    releases = []
    page = 1
    while True:
        batch = json.loads(_request(
            f"{API}/repos/{repo}/releases?per_page=100&page={page}", token))
        releases.extend(batch)
        if len(batch) < 100:
            return releases
        page += 1


def download_asset(url, dest, token=None):
    """Download a release asset binary to dest.

    The octet-stream Accept header asks the API asset URL for the binary
    instead of its JSON metadata; it is ignored by browser_download_url,
    so the header is safe for both URL styles.
    """
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/octet-stream")
    req.add_header("User-Agent", "appz4fun-kodi-repo")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    opener = urllib.request.build_opener(_AuthStrippingRedirectHandler())
    with opener.open(req, timeout=300) as resp, open(dest, "wb") as fh:
        fh.write(resp.read())
    return dest


def download_asset_cached(asset, cache_dir, token=None):
    """Return a local path to the asset zip, downloading only on cache miss.

    Cache key is the immutable asset id; an existing non-empty file is reused.
    With a token the API asset URL is used — the only URL that can serve
    assets from private source repos (browser_download_url is anonymous-only).
    """
    os.makedirs(cache_dir, exist_ok=True)
    dest = os.path.join(cache_dir, f"{asset['id']}.zip")
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest
    url = asset["url"] if token else asset["browser_download_url"]
    return download_asset(url, dest, token)
