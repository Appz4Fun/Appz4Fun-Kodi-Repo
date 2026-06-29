import os

from kodirepo.landing import render_index

TEMPLATE = open(
    os.path.join(os.path.dirname(__file__), "..", "build", "templates", "index.html"),
    encoding="utf-8",
).read()


def test_render_index_lists_channels_and_links():
    html = render_index(
        TEMPLATE,
        base_url="https://appz4fun.github.io/Appz4Fun-Kodi-Repo/",
        channels={
            "stable": {
                "repo_id": "repository.appz4fun.stable",
                "repo_version": "1.0.0",
                "addons": {"plugin.video.nzbdav": "1.2.3"},
            },
            "beta": {
                "repo_id": "repository.appz4fun.beta",
                "repo_version": "1.0.0",
                "addons": {"plugin.video.nzbdav": "1.3.0-beta"},
            },
        },
    )
    assert "Stable channel" in html
    assert "Beta channel" in html
    assert "stable/repository.appz4fun.stable/repository.appz4fun.stable-1.0.0.zip" in html
    assert "plugin.video.nzbdav" in html
    assert "1.2.3" in html and "1.3.0-beta" in html
    # Template's literal CSS braces must not survive as {{ }}.
    assert "{{" not in html and "}}" not in html
