import os
import sys
import zipfile

import pytest

# Make `from kodirepo import ...` work without installation.
BUILD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build")
if BUILD_DIR not in sys.path:
    sys.path.insert(0, BUILD_DIR)

ADDON_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<addon id="{id}" name="{name}" version="{version}" provider-name="tester">
    <extension point="xbmc.python.pluginsource" library="addon.py">
        <provides>video</provides>
    </extension>
    <extension point="xbmc.addon.metadata">
        <summary lang="en">Sample addon</summary>
        <description lang="en">Sample addon for tests</description>
        <platform>all</platform>
        <assets>
            <icon>resources/icon.png</icon>
            <fanart>resources/fanart.jpg</fanart>
        </assets>
    </extension>
</addon>
"""


def make_addon_zip(dest_dir, addon_id="plugin.video.sample", version="1.0.0", name="Sample"):
    """Write a minimal but structurally-correct Kodi addon zip; return its path."""
    path = os.path.join(dest_dir, f"{addon_id}-{version}.zip")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{addon_id}/addon.xml", ADDON_XML.format(id=addon_id, name=name, version=version))
        zf.writestr(f"{addon_id}/addon.py", "# entry point\n")
        zf.writestr(f"{addon_id}/resources/icon.png", b"\x89PNG\r\n\x1a\nICON")
        zf.writestr(f"{addon_id}/resources/fanart.jpg", b"\xff\xd8\xff\xe0FANART")
    return path


@pytest.fixture
def sample_addon_zip(tmp_path):
    return make_addon_zip(str(tmp_path))
