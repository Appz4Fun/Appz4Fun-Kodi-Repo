#!/usr/bin/env python3
"""Build the Appz4Fun Kodi repository tree into out/ from source releases."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kodirepo import github
from kodirepo.addon_zip import read_addon
from kodirepo.builder import build_channel
from kodirepo.landing import render_index
from kodirepo.select import releases_for_channel, pick_zip_asset

CHANNELS = ("stable", "beta")

REPO_ADDONS = {
    "stable": {
        "id": "repository.appz4fun.stable",
        "name": "Appz4Fun Repository",
        "version": "1.0.0",
        "summary": "Appz4Fun Kodi add-ons (stable)",
        "description": "Stable channel for Appz4Fun Kodi add-ons. Auto-updates.",
    },
    "beta": {
        "id": "repository.appz4fun.beta",
        "name": "Appz4Fun Repository (Beta)",
        "version": "1.0.0",
        "summary": "Appz4Fun Kodi add-ons (beta)",
        "description": "Beta channel for Appz4Fun Kodi add-ons, including pre-releases.",
    },
}

HERE = os.path.dirname(os.path.abspath(__file__))


def _resolve(sources, cache_dir, token, list_releases, download):
    """Download each repo's release zips and read authoritative addon metadata."""
    resolved = []
    for repo in sources["repositories"]:
        for rel in list_releases(repo, token):
            if rel.get("draft"):
                continue
            asset = pick_zip_asset(rel)
            if asset is None:
                print(f"WARN {repo} {rel.get('tag_name')}: no usable .zip asset; skipping")
                continue
            zip_path = download(asset, cache_dir, token)
            try:
                addon_id, version, xml, top = read_addon(zip_path)
            except ValueError as exc:
                print(f"WARN {repo} {rel.get('tag_name')}: {exc}; skipping")
                continue
            resolved.append({
                "prerelease": bool(rel.get("prerelease")),
                "id": addon_id, "version": version,
                "zip_path": zip_path, "addon_xml": xml, "top_dir": top,
            })
    return resolved


def build(sources, out_root, cache_dir, assets_dir, token,
          list_releases=github.list_releases, download=github.download_asset_cached):
    """Build both channels into out_root and write the landing page."""
    repo_template = open(os.path.join(HERE, "templates", "repository.addon.xml"), encoding="utf-8").read()
    index_template = open(os.path.join(HERE, "templates", "index.html"), encoding="utf-8").read()
    base_url = sources["base_url"]

    resolved = _resolve(sources, cache_dir, token, list_releases, download)
    if not resolved:
        raise SystemExit("ERROR: no addons resolved from any source repo; refusing to publish empty repo")

    channels_summary = {}
    for channel in CHANNELS:
        addons = [r for r in resolved if channel == "beta" or not r["prerelease"]]
        cfg = REPO_ADDONS[channel]
        summary = build_channel(
            channel=channel, base_url=base_url, addons=addons,
            repo_addon_cfg=cfg, assets_dir=assets_dir,
            repo_template=repo_template, out_root=out_root,
        )
        channels_summary[channel] = {
            "repo_id": cfg["id"], "repo_version": cfg["version"], "addons": summary,
        }

    with open(os.path.join(out_root, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(render_index(index_template, base_url=base_url, channels=channels_summary))
    return channels_summary


def main():
    root = os.path.dirname(HERE)  # repo root
    sources = json.load(open(os.path.join(root, "sources.json"), encoding="utf-8"))
    build(
        sources=sources,
        out_root=os.path.join(root, "out"),
        cache_dir=os.path.join(root, ".cache", "assets"),
        assets_dir=os.path.join(root, "assets"),
        token=os.environ.get("GITHUB_TOKEN"),
    )
    print("Built repository into out/")


if __name__ == "__main__":
    main()
