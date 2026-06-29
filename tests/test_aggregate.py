import hashlib

from kodirepo.aggregate import addon_element, build_addons_xml, md5_hex

ADDON_A = b"""<?xml version="1.0" encoding="UTF-8"?>
<addon id="plugin.video.a" name="A" version="1.0.0" provider-name="t">
  <extension point="xbmc.addon.metadata"><platform>all</platform></extension>
</addon>"""


def test_addon_element_strips_prolog_and_keeps_root():
    el = addon_element(ADDON_A)
    assert el.startswith("<addon")
    assert "<?xml" not in el
    assert 'id="plugin.video.a"' in el


def test_build_addons_xml_wraps_elements():
    doc = build_addons_xml([addon_element(ADDON_A)])
    assert doc.startswith('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>')
    assert "<addons>" in doc and "</addons>" in doc
    assert 'id="plugin.video.a"' in doc


def test_md5_hex_matches_hashlib():
    doc = build_addons_xml([addon_element(ADDON_A)])
    assert md5_hex(doc) == hashlib.md5(doc.encode("utf-8")).hexdigest()
