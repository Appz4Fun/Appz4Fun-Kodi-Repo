import os

from kodirepo.builder import build_channel
from kodirepo.addon_zip import read_addon
from kodirepo.aggregate import md5_hex
from conftest import make_addon_zip

TEMPLATE = open(
    os.path.join(os.path.dirname(__file__), "..", "build", "templates", "repository.addon.xml"),
    encoding="utf-8",
).read()

REPO_CFG = {
    "id": "repository.appz4fun.stable",
    "name": "Appz4Fun Repository",
    "version": "1.0.0",
    "summary": "Appz4Fun add-ons",
    "description": "Stable channel.",
}


def _record(zip_path):
    aid, ver, xml, top = read_addon(zip_path)
    return {"id": aid, "version": ver, "zip_path": zip_path, "addon_xml": xml, "top_dir": top}


def test_build_channel_lays_out_tree_and_catalog(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    old = _record(make_addon_zip(str(src), version="1.0.0"))
    new = _record(make_addon_zip(str(src), version="1.1.0"))
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "icon.png").write_bytes(b"\x89PNGicon")
    (assets / "fanart.png").write_bytes(b"\x89PNGfan")
    out = tmp_path / "out"

    summary = build_channel(
        channel="stable",
        base_url="https://appz4fun.github.io/Appz4Fun-Kodi-Repo",
        addons=[old, new],
        repo_addon_cfg=REPO_CFG,
        assets_dir=str(assets),
        repo_template=TEMPLATE,
        out_root=str(out),
    )

    chan = out / "stable"
    # Every version retained.
    assert (chan / "plugin.video.sample" / "plugin.video.sample-1.0.0.zip").exists()
    assert (chan / "plugin.video.sample" / "plugin.video.sample-1.1.0.zip").exists()
    # Repository addon zip emitted.
    assert (chan / "repository.appz4fun.stable" / "repository.appz4fun.stable-1.0.0.zip").exists()
    # Artwork from the newest version extracted, keeping its declared path.
    assert (chan / "plugin.video.sample" / "resources" / "icon.png").exists()
    # Catalog advertises the NEWEST member version + the repo addon.
    catalog = (chan / "addons.xml").read_text(encoding="utf-8")
    assert 'version="1.1.0"' in catalog
    assert 'version="1.0.0"' not in catalog.split('id="plugin.video.sample"')[1].split("</addon>")[0]
    assert 'id="repository.appz4fun.stable"' in catalog
    # md5 matches.
    assert (chan / "addons.xml.md5").read_text(encoding="utf-8") == md5_hex(catalog)
    # Summary reports newest member versions only.
    assert summary == {"plugin.video.sample": "1.1.0"}
