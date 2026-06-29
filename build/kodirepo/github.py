"""Minimal GitHub REST client + asset download cache (stdlib only)."""

import json
import os
import urllib.request

API = "https://api.github.com"


def _request(url, token=None):
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "appz4fun-kodi-repo")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def list_releases(repo, token=None):
    """Return the published+draft releases for owner/repo (newest first)."""
    return json.loads(_request(f"{API}/repos/{repo}/releases?per_page=100", token))


def download_asset(url, dest, token=None):
    """Download a release asset to dest (browser_download_url, public, no auth)."""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "appz4fun-kodi-repo")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=300) as resp, open(dest, "wb") as fh:
        fh.write(resp.read())
    return dest


def download_asset_cached(asset, cache_dir, token=None):
    """Return a local path to the asset zip, downloading only on cache miss.

    Cache key is the immutable asset id; an existing non-empty file is reused.
    """
    os.makedirs(cache_dir, exist_ok=True)
    dest = os.path.join(cache_dir, f"{asset['id']}.zip")
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest
    return download_asset(asset["browser_download_url"], dest, token)
