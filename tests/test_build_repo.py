import os
import sys

BUILD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build")
if BUILD_DIR not in sys.path:
    sys.path.insert(0, BUILD_DIR)

import build_repo
from kodirepo.addon_zip import read_addon
from conftest import make_addon_zip


def test_build_produces_both_channels(tmp_path):
    # One stable release (1.0.0) and one pre-release (1.1.0-beta).
    src = tmp_path / "src"
    src.mkdir()
    stable_zip = make_addon_zip(str(src), version="1.0.0")
    beta_zip = make_addon_zip(str(src), version="1.1.0-beta")

    releases = [
        {"tag_name": "v1.1.0-beta", "prerelease": True, "draft": False,
         "assets": [{"id": 2, "name": "plugin.video.sample-1.1.0-beta.zip",
                     "browser_download_url": "https://x/2"}]},
        {"tag_name": "v1.0.0", "prerelease": False, "draft": False,
         "assets": [{"id": 1, "name": "plugin.video.sample-1.0.0.zip",
                     "browser_download_url": "https://x/1"}]},
    ]
    asset_files = {1: stable_zip, 2: beta_zip}

    def fake_list_releases(repo, token=None):
        return releases

    def fake_download(asset, cache_dir, token=None):
        return asset_files[asset["id"]]

    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "icon.png").write_bytes(b"\x89PNGicon")
    (assets / "fanart.png").write_bytes(b"\x89PNGfan")
    out = tmp_path / "out"

    build_repo.build(
        sources={"base_url": "https://appz4fun.github.io/Appz4Fun-Kodi-Repo",
                 "repositories": ["Appz4Fun/sample"]},
        out_root=str(out),
        cache_dir=str(tmp_path / "cache"),
        assets_dir=str(assets),
        token=None,
        list_releases=fake_list_releases,
        download=fake_download,
    )

    # Stable: only 1.0.0; Beta: newest is 1.1.0-beta.
    stable_catalog = (out / "stable" / "addons.xml").read_text(encoding="utf-8")
    beta_catalog = (out / "beta" / "addons.xml").read_text(encoding="utf-8")
    assert 'version="1.0.0"' in stable_catalog
    assert "1.1.0-beta" not in stable_catalog
    assert "1.1.0-beta" in beta_catalog
    # Stable advertises its own repo addon; beta advertises the beta one.
    assert 'id="repository.appz4fun.stable"' in stable_catalog
    assert 'id="repository.appz4fun.beta"' in beta_catalog
    # Landing page exists and links both channels.
    index = (out / "index.html").read_text(encoding="utf-8")
    assert "Stable channel" in index and "Beta channel" in index
    # Beta retained both versions; stable retained only the stable one.
    assert (out / "beta" / "plugin.video.sample" / "plugin.video.sample-1.1.0-beta.zip").exists()
    assert (out / "stable" / "plugin.video.sample" / "plugin.video.sample-1.0.0.zip").exists()
    assert not (out / "stable" / "plugin.video.sample" / "plugin.video.sample-1.1.0-beta.zip").exists()
    # Landing links to each add-on's page, and the per-addon page lists all versions.
    assert 'href="stable/plugin.video.sample/"' in index
    beta_page = (out / "beta" / "plugin.video.sample" / "index.html").read_text(encoding="utf-8")
    assert 'href="plugin.video.sample-1.1.0-beta.zip"' in beta_page
    assert 'href="plugin.video.sample-1.0.0.zip"' in beta_page
