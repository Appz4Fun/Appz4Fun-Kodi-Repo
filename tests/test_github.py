import os

import kodirepo.github as gh


def test_download_asset_cached_returns_existing_without_network(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    cache.mkdir()
    asset = {"id": 999, "name": "x.zip", "browser_download_url": "https://example/x.zip"}
    cached = cache / "999.zip"
    cached.write_bytes(b"already-here")

    def explode(*a, **k):
        raise AssertionError("network must not be called on cache hit")

    monkeypatch.setattr(gh, "download_asset", explode)
    out = gh.download_asset_cached(asset, str(cache))
    assert out == str(cached)
    assert open(out, "rb").read() == b"already-here"


def test_download_asset_cached_downloads_on_miss(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    asset = {"id": 7, "name": "x.zip", "browser_download_url": "https://example/x.zip"}
    calls = {}

    def fake_download(url, dest, token=None):
        calls["url"] = url
        with open(dest, "wb") as fh:
            fh.write(b"downloaded")
        return dest

    monkeypatch.setattr(gh, "download_asset", fake_download)
    out = gh.download_asset_cached(asset, str(cache))
    assert calls["url"] == "https://example/x.zip"
    assert open(out, "rb").read() == b"downloaded"
    assert os.path.basename(out) == "7.zip"


def test_releases_first_page_url_and_empty(monkeypatch):
    captured = {}

    def fake_request(url, token=None):
        captured["url"] = url
        return b"[]"

    monkeypatch.setattr(gh, "_request", fake_request)
    assert gh.list_releases("Owner/Repo") == []
    assert captured["url"] == "https://api.github.com/repos/Owner/Repo/releases?per_page=100&page=1"


def test_list_releases_pages_until_short_page(monkeypatch):
    # Page 1 is full (100) so a second page is fetched; page 2 is short (2) so
    # pagination stops there (no page 3 request). Results are concatenated.
    import json as _json
    urls = []

    def fake_request(url, token=None):
        urls.append(url)
        if url.endswith("&page=1"):
            return _json.dumps([{"tag_name": f"v{i}"} for i in range(100)]).encode()
        if url.endswith("&page=2"):
            return _json.dumps([{"tag_name": "v100"}, {"tag_name": "v101"}]).encode()
        raise AssertionError(f"unexpected extra page request: {url}")

    monkeypatch.setattr(gh, "_request", fake_request)
    out = gh.list_releases("Owner/Repo")
    assert len(out) == 102
    assert out[0]["tag_name"] == "v0" and out[-1]["tag_name"] == "v101"
    assert urls == [
        "https://api.github.com/repos/Owner/Repo/releases?per_page=100&page=1",
        "https://api.github.com/repos/Owner/Repo/releases?per_page=100&page=2",
    ]
