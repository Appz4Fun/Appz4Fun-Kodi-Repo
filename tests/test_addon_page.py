import os

from kodirepo.addon_page import render_addon_page

TEMPLATE = open(
    os.path.join(os.path.dirname(__file__), "..", "build", "templates", "addon.html"),
    encoding="utf-8",
).read()


def test_render_addon_page_lists_all_versions_newest_first():
    html = render_addon_page(
        TEMPLATE, name="NZB-DAV", addon_id="plugin.video.nzbdav",
        channel="stable", versions=["1.0.0", "1.10.0", "1.2.0", "1.0.0-pre-alpha"],
    )
    assert "NZB-DAV" in html
    assert "plugin.video.nzbdav" in html
    assert "Stable" in html  # channel title-cased
    # every version is a download link to the sibling zip (relative path)
    for v in ("1.10.0", "1.2.0", "1.0.0", "1.0.0-pre-alpha"):
        assert f'href="plugin.video.nzbdav-{v}.zip"' in html
    # newest-first ordering (numeric, not lexical): 1.10.0 > 1.2.0 > 1.0.0
    assert (html.index("plugin.video.nzbdav-1.10.0.zip")
            < html.index("plugin.video.nzbdav-1.2.0.zip")
            < html.index("plugin.video.nzbdav-1.0.0.zip"))
    # release sorts above its own pre-release
    assert (html.index("plugin.video.nzbdav-1.0.0.zip")
            < html.index("plugin.video.nzbdav-1.0.0-pre-alpha.zip"))
    # back-link to the repo home page
    assert 'href="../../"' in html
    # template CSS braces consumed by str.format
    assert "{{" not in html and "}}" not in html


def test_render_addon_page_dedupes_and_counts():
    html = render_addon_page(
        TEMPLATE, name="X", addon_id="plugin.x", channel="beta",
        versions=["1.0.0", "1.0.0", "0.9.0"],
    )
    assert "2 version(s)" in html  # deduped
    assert html.count('href="plugin.x-1.0.0.zip"') == 1
