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
