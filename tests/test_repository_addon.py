import os
import zipfile

from kodirepo.repository_addon import render_addon_xml, build_zip
from kodirepo.addon_zip import read_addon

TEMPLATE = open(
    os.path.join(os.path.dirname(__file__), "..", "build", "templates", "repository.addon.xml"),
    encoding="utf-8",
).read()


def test_render_addon_xml_bakes_channel_urls():
    xml = render_addon_xml(
        TEMPLATE, id="repository.appz4fun.stable", name="Appz4Fun Repository",
        version="1.0.0", base_url="https://appz4fun.github.io/Appz4Fun-Kodi-Repo/",
        channel="stable", summary="s", description="d",
    )
    assert 'id="repository.appz4fun.stable"' in xml
    assert "https://appz4fun.github.io/Appz4Fun-Kodi-Repo/stable/addons.xml" in xml
    assert "https://appz4fun.github.io/Appz4Fun-Kodi-Repo/stable/addons.xml.md5" in xml
    assert '<datadir zip="true">https://appz4fun.github.io/Appz4Fun-Kodi-Repo/stable/</datadir>' in xml


def test_build_zip_produces_installable_addon(tmp_path):
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "icon.png").write_bytes(b"\x89PNGicon")
    (assets / "fanart.png").write_bytes(b"\x89PNGfan")
    xml = render_addon_xml(
        TEMPLATE, id="repository.appz4fun.stable", name="Appz4Fun Repository",
        version="1.0.0", base_url="https://example.com", channel="stable",
        summary="s", description="d",
    )
    dest = str(tmp_path / "repo" / "repository.appz4fun.stable-1.0.0.zip")
    build_zip("repository.appz4fun.stable", xml, str(assets), dest)
    # Round-trips through the real addon reader -> structurally valid.
    addon_id, version, _, top_dir = read_addon(dest)
    assert addon_id == "repository.appz4fun.stable"
    assert version == "1.0.0"
    with zipfile.ZipFile(dest) as zf:
        assert "repository.appz4fun.stable/icon.png" in zf.namelist()
        assert "repository.appz4fun.stable/fanart.png" in zf.namelist()
