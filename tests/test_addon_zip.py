import os

from kodirepo.addon_zip import read_addon, extract_artwork


def test_read_addon_returns_id_version_and_topdir(sample_addon_zip):
    addon_id, version, xml_bytes, top_dir = read_addon(sample_addon_zip)
    assert addon_id == "plugin.video.sample"
    assert version == "1.0.0"
    assert top_dir == "plugin.video.sample"
    assert b"<addon" in xml_bytes


def test_extract_artwork_writes_icon_and_fanart(sample_addon_zip, tmp_path):
    addon_id, version, xml_bytes, top_dir = read_addon(sample_addon_zip)
    dest = tmp_path / "out"
    extract_artwork(sample_addon_zip, top_dir, xml_bytes, str(dest))
    assert (dest / "icon.png").read_bytes() == b"\x89PNG\r\n\x1a\nICON"
    assert (dest / "fanart.jpg").read_bytes() == b"\xff\xd8\xff\xe0FANART"


def test_read_addon_rejects_zip_without_addon_xml(tmp_path):
    import zipfile
    bad = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad, "w") as zf:
        zf.writestr("not-an-addon/readme.txt", "nope")
    try:
        read_addon(str(bad))
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_read_addon_rejects_corrupt_zip(tmp_path):
    # A truncated/garbage file is not a valid addon -> ValueError (not BadZipFile),
    # so the builder skips it instead of aborting the whole run.
    bad = tmp_path / "corrupt.zip"
    bad.write_bytes(b"PK\x03\x04 this is not actually a zip")
    try:
        read_addon(str(bad))
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_read_addon_rejects_malformed_addon_xml(tmp_path):
    import zipfile
    bad = tmp_path / "badxml.zip"
    with zipfile.ZipFile(bad, "w") as zf:
        zf.writestr("plugin.video.x/addon.xml", "<addon id='x' version='1.0.0'")  # unclosed
    try:
        read_addon(str(bad))
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_read_addon_rejects_topdir_id_mismatch(tmp_path):
    # Kodi requires the add-on folder to be named exactly <id>. A zip whose top
    # folder is versioned (plugin.video.foo-1.2.3/) must be rejected.
    import zipfile
    bad = tmp_path / "mismatch.zip"
    with zipfile.ZipFile(bad, "w") as zf:
        zf.writestr(
            "plugin.video.foo-1.2.3/addon.xml",
            '<addon id="plugin.video.foo" version="1.2.3" provider-name="t">'
            '<extension point="xbmc.python.pluginsource" library="addon.py"/></addon>',
        )
    try:
        read_addon(str(bad))
        assert False, "expected ValueError"
    except ValueError:
        pass
