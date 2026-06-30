from kodirepo.select import releases_for_channel, newest_per_addon, pick_zip_asset

RELEASES = [
    {"tag_name": "v1.2.0", "prerelease": False, "draft": False},
    {"tag_name": "v1.3.0-beta", "prerelease": True, "draft": False},
    {"tag_name": "v1.1.0", "prerelease": False, "draft": True},
]


def test_stable_excludes_prerelease_and_draft():
    out = releases_for_channel(RELEASES, "stable")
    assert [r["tag_name"] for r in out] == ["v1.2.0"]


def test_beta_includes_prerelease_but_not_draft():
    out = releases_for_channel(RELEASES, "beta")
    assert [r["tag_name"] for r in out] == ["v1.2.0", "v1.3.0-beta"]


def test_newest_per_addon_picks_highest_version():
    records = [
        {"id": "plugin.video.a", "version": "1.2.0"},
        {"id": "plugin.video.a", "version": "1.10.0"},
        {"id": "plugin.video.b", "version": "0.1.0"},
    ]
    best = newest_per_addon(records)
    assert best["plugin.video.a"]["version"] == "1.10.0"
    assert best["plugin.video.b"]["version"] == "0.1.0"


def test_pick_zip_asset_single():
    rel = {"tag_name": "v1.2.0", "assets": [{"name": "plugin.video.a-1.2.0.zip"}]}
    assert pick_zip_asset(rel)["name"] == "plugin.video.a-1.2.0.zip"


def test_pick_zip_asset_prefers_tag_match_when_multiple():
    rel = {"tag_name": "v1.2.0", "assets": [
        {"name": "extra.zip"},
        {"name": "plugin.video.a-1.2.0.zip"},
    ]}
    assert pick_zip_asset(rel)["name"] == "plugin.video.a-1.2.0.zip"


def test_pick_zip_asset_none_when_no_zip():
    assert pick_zip_asset({"tag_name": "v1", "assets": [{"name": "notes.txt"}]}) is None
