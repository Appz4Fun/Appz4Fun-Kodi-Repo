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


def test_releases_url_built_correctly(monkeypatch):
    captured = {}

    def fake_request(url, token=None):
        captured["url"] = url
        return b"[]"

    monkeypatch.setattr(gh, "_request", fake_request)
    assert gh.list_releases("Owner/Repo") == []
    assert captured["url"] == "https://api.github.com/repos/Owner/Repo/releases?per_page=100"
