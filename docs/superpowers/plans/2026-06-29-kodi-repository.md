# Appz4Fun Kodi Repository Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a multi-channel (stable/beta) self-hosting Kodi repository that a scheduled GitHub Actions workflow rebuilds from source repos' GitHub Releases and deploys to GitHub Pages.

**Architecture:** A dependency-free Python 3 package (`build/kodirepo/`) of small, pure, unit-tested units does the work: read addon metadata from each release zip, select releases per channel, aggregate `addons.xml` + `.md5`, generate per-channel repository addons, and render a landing page. A thin CLI (`build/build_repo.py`) wires in the GitHub API (network) and writes the full served tree to `out/`. A workflow runs the tests, rebuilds from scratch each run, and deploys `out/` as a Pages artifact.

**Tech Stack:** Python 3.12 standard library only (`zipfile`, `xml.etree`, `hashlib`, `urllib`), `pytest` for tests, GitHub Actions + GitHub Pages.

---

## File Structure

```
sources.json                      # list of source repos + base_url
build/
  build_repo.py                   # CLI entry; wires GitHub API + writes out/
  kodirepo/
    __init__.py
    version.py                    # parse_version() for newest-version comparison
    addon_zip.py                  # read_addon(), extract_artwork()
    aggregate.py                  # addon_element(), build_addons_xml(), md5_hex()
    select.py                     # releases_for_channel(), newest_per_addon(), pick_zip_asset()
    repository_addon.py           # render_addon_xml(), build_zip()
    landing.py                    # render_index()
    builder.py                    # build_channel() — per-channel orchestration, offline-testable
    github.py                     # list_releases(), download_asset(), download_asset_cached()
  templates/
    repository.addon.xml
    index.html
assets/
  icon.png                        # repository addon artwork (placeholder, replaceable)
  fanart.png
tests/
  conftest.py                     # puts build/ on sys.path; sample-addon-zip fixture
  test_version.py
  test_addon_zip.py
  test_aggregate.py
  test_select.py
  test_repository_addon.py
  test_landing.py
  test_builder.py
  test_github.py
  test_build_repo.py
.github/workflows/sync.yml
.gitignore
README.md
```

**Module contract summary** (used consistently across tasks):

- `parse_version(s: str) -> tuple` — comparable key; release sorts above same-core pre-release.
- `read_addon(zip_path) -> (addon_id: str, version: str, addon_xml_bytes: bytes, top_dir: str)`
- `extract_artwork(zip_path, top_dir, addon_xml_bytes, dest_dir) -> None`
- `addon_element(addon_xml_bytes: bytes) -> str` — the `<addon>` element, no XML prolog.
- `build_addons_xml(elements: list[str]) -> str`
- `md5_hex(text: str | bytes) -> str`
- `releases_for_channel(releases: list[dict], channel: str) -> list[dict]`
- `pick_zip_asset(release: dict) -> dict | None`
- `newest_per_addon(records: list[dict]) -> dict[str, dict]` — records have keys `id`, `version`.
- `render_addon_xml(template, *, id, name, version, base_url, channel, summary, description) -> str`
- `build_zip(addon_id, addon_xml_str, assets_dir, dest_zip) -> str`
- `build_channel(*, channel, base_url, addons, repo_addon_cfg, assets_dir, repo_template, out_root) -> dict[str, str]`
  - `addons` records have keys: `id`, `version`, `zip_path`, `addon_xml` (bytes), `top_dir`.
  - `repo_addon_cfg` keys: `id`, `name`, `version`, `summary`, `description`.
  - returns `{addon_id: version}` of the newest member addons (excludes the repo addon).
- `render_index(template, *, base_url, channels: dict) -> str`
- `list_releases(repo, token=None) -> list[dict]`, `download_asset_cached(asset, cache_dir, token=None) -> str`

---

## Task 1: Project scaffold, config, and test harness

**Files:**
- Create: `sources.json`
- Create: `build/kodirepo/__init__.py`
- Create: `tests/conftest.py`
- Create: `.gitignore`
- Create: `requirements-dev.txt`

- [ ] **Step 1: Create `sources.json`**

```json
{
  "base_url": "https://appz4fun.github.io/Appz4Fun-Kodi-Repo",
  "repositories": [
    "Appz4Fun/nzbdavkodi"
  ]
}
```

- [ ] **Step 2: Create the empty package marker `build/kodirepo/__init__.py`**

```python
"""Kodi repository builder (standard library only)."""
```

- [ ] **Step 3: Create `requirements-dev.txt`**

```
pytest>=8
```

- [ ] **Step 4: Create `.gitignore`**

```
__pycache__/
*.pyc
.pytest_cache/
out/
.cache/
```

- [ ] **Step 5: Create `tests/conftest.py` with the sys.path shim and a sample-addon-zip fixture**

```python
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
```

- [ ] **Step 6: Verify pytest collects with no tests yet**

Run: `cd /Users/allen/git/Appz4Fun-Kodi-Repo && python3 -m pytest -q`
Expected: `no tests ran` (exit code 5) — confirms conftest imports cleanly.

- [ ] **Step 7: Commit**

```bash
git add sources.json build/kodirepo/__init__.py tests/conftest.py .gitignore requirements-dev.txt
git commit -m "chore: scaffold kodi repo builder package and test harness"
```

---

## Task 2: Version parsing (`version.py`)

**Files:**
- Create: `build/kodirepo/version.py`
- Test: `tests/test_version.py`

- [ ] **Step 1: Write the failing test**

```python
from kodirepo.version import parse_version


def test_patch_ordering():
    assert parse_version("1.2.3") > parse_version("1.2.2")


def test_numeric_not_lexical_ordering():
    assert parse_version("1.10.0") > parse_version("1.9.9")


def test_release_beats_prerelease_same_core():
    assert parse_version("1.2.3") > parse_version("1.2.3-pre-alpha")


def test_handles_v_prefix_stripped_by_caller_only():
    # parse_version expects a clean version string (no leading 'v').
    assert parse_version("0.6.21") > parse_version("0.6.20")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_version.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'kodirepo.version'`

- [ ] **Step 3: Write the implementation**

```python
"""Parse Kodi-style addon version strings into comparable keys."""

import re

_CORE_RE = re.compile(r"^([0-9][0-9.]*)(?:[-~](.*))?$")


def parse_version(value):
    """Return a tuple key for comparing addon versions.

    Key shape: (epoch, core_ints, is_release, pre_tag_parts).
    A version with no pre-release tag sorts above the same numeric core
    that has one (so 1.2.3 > 1.2.3-beta). Channel membership is decided
    elsewhere by the GitHub pre-release flag, not by this string.
    """
    v = value.strip()
    epoch = 0
    if ":" in v:
        head, _, rest = v.partition(":")
        if head.isdigit():
            epoch, v = int(head), rest
    m = _CORE_RE.match(v)
    if not m:
        return (epoch, (), 0, (v,))
    core = tuple(int(p) for p in m.group(1).split(".") if p != "")
    tag = m.group(2) or ""
    is_release = 1 if tag == "" else 0
    tag_parts = tuple(tag.split(".")) if tag else ()
    return (epoch, core, is_release, tag_parts)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_version.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add build/kodirepo/version.py tests/test_version.py
git commit -m "feat: add Kodi version parsing/comparison"
```

---

## Task 3: Read addon metadata and artwork from a zip (`addon_zip.py`)

**Files:**
- Create: `build/kodirepo/addon_zip.py`
- Test: `tests/test_addon_zip.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_addon_zip.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'kodirepo.addon_zip'`

- [ ] **Step 3: Write the implementation**

```python
"""Read addon metadata and artwork out of a Kodi addon zip."""

import os
import zipfile
import xml.etree.ElementTree as ET


def read_addon(zip_path):
    """Return (addon_id, version, addon_xml_bytes, top_dir) for a Kodi addon zip.

    The id and version are taken from the addon.xml inside the zip — never
    the filename. Raises ValueError if the zip is not a valid addon.
    """
    with zipfile.ZipFile(zip_path) as zf:
        candidates = [n for n in zf.namelist()
                      if n.count("/") == 1 and n.endswith("/addon.xml")]
        if not candidates:
            raise ValueError(f"{zip_path}: no top-level <dir>/addon.xml")
        entry = sorted(candidates)[0]
        data = zf.read(entry)
    top_dir = entry.split("/", 1)[0]
    root = ET.fromstring(data)
    addon_id = root.get("id")
    version = root.get("version")
    if not addon_id or not version:
        raise ValueError(f"{zip_path}: addon.xml missing id/version")
    return addon_id, version, data, top_dir


def _find_assets(root):
    for ext in root.findall("extension"):
        if ext.get("point") == "xbmc.addon.metadata":
            assets = ext.find("assets")
            if assets is not None:
                return assets
    return None


def extract_artwork(zip_path, top_dir, addon_xml_bytes, dest_dir):
    """Extract icon/fanart referenced in addon.xml <assets> into dest_dir.

    Writes dest_dir/icon.png and dest_dir/fanart.jpg when present. Missing
    assets are skipped silently — artwork is best-effort, not required.
    """
    assets = _find_assets(ET.fromstring(addon_xml_bytes))
    if assets is None:
        return
    os.makedirs(dest_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())
        for tag, out_name in (("icon", "icon.png"), ("fanart", "fanart.jpg")):
            el = assets.find(tag)
            if el is None or not (el.text or "").strip():
                continue
            src = f"{top_dir}/{el.text.strip()}"
            if src not in names:
                continue
            with open(os.path.join(dest_dir, out_name), "wb") as fh:
                fh.write(zf.read(src))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_addon_zip.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add build/kodirepo/addon_zip.py tests/test_addon_zip.py
git commit -m "feat: read addon id/version and extract artwork from zips"
```

---

## Task 4: Aggregate addons.xml + md5 (`aggregate.py`)

**Files:**
- Create: `build/kodirepo/aggregate.py`
- Test: `tests/test_aggregate.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_aggregate.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'kodirepo.aggregate'`

- [ ] **Step 3: Write the implementation**

```python
"""Build the repository addons.xml catalog and its md5 checksum."""

import hashlib
import xml.etree.ElementTree as ET


def addon_element(addon_xml_bytes):
    """Return the <addon> element of an addon.xml as a string, no XML prolog."""
    root = ET.fromstring(addon_xml_bytes)
    return ET.tostring(root, encoding="unicode").strip()


def build_addons_xml(elements):
    """Wrap a list of <addon> element strings into a full addons.xml document."""
    parts = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>', "<addons>"]
    parts.extend(e.strip() for e in elements)
    parts.append("</addons>")
    return "\n".join(parts) + "\n"


def md5_hex(text):
    """Return the hex md5 digest of text (str or bytes)."""
    if isinstance(text, str):
        text = text.encode("utf-8")
    return hashlib.md5(text).hexdigest()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_aggregate.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add build/kodirepo/aggregate.py tests/test_aggregate.py
git commit -m "feat: aggregate addons.xml and compute md5"
```

---

## Task 5: Release selection (`select.py`)

**Files:**
- Create: `build/kodirepo/select.py`
- Test: `tests/test_select.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_select.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'kodirepo.select'`

- [ ] **Step 3: Write the implementation**

```python
"""Select which releases and assets feed each channel."""

from .version import parse_version


def releases_for_channel(releases, channel):
    """Return published releases for a channel.

    'stable' excludes pre-releases; 'beta' includes them. Drafts are always
    excluded.
    """
    out = []
    for r in releases:
        if r.get("draft"):
            continue
        if channel == "stable" and r.get("prerelease"):
            continue
        out.append(r)
    return out


def newest_per_addon(records):
    """Reduce records (each with 'id' and 'version') to the newest per id."""
    best = {}
    for rec in records:
        rid = rec["id"]
        if rid not in best or parse_version(rec["version"]) > parse_version(best[rid]["version"]):
            best[rid] = rec
    return best


def pick_zip_asset(release):
    """Choose the addon .zip asset of a release, or None if absent/ambiguous."""
    zips = [a for a in release.get("assets", []) if a.get("name", "").endswith(".zip")]
    if not zips:
        return None
    if len(zips) == 1:
        return zips[0]
    tag = release.get("tag_name", "").lstrip("v")
    for a in zips:
        if tag and tag in a["name"]:
            return a
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_select.py -q`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add build/kodirepo/select.py tests/test_select.py
git commit -m "feat: select releases/assets per channel"
```

---

## Task 6: Repository addon template + builder (`repository_addon.py`)

**Files:**
- Create: `build/templates/repository.addon.xml`
- Create: `build/kodirepo/repository_addon.py`
- Test: `tests/test_repository_addon.py`

- [ ] **Step 1: Create the template `build/templates/repository.addon.xml`**

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<addon id="{id}" name="{name}" version="{version}" provider-name="Appz4Fun">
    <extension point="xbmc.addon.repository" name="{name}">
        <dir>
            <info compressed="false">{base_url}/{channel}/addons.xml</info>
            <checksum>{base_url}/{channel}/addons.xml.md5</checksum>
            <datadir zip="true">{base_url}/{channel}/</datadir>
        </dir>
    </extension>
    <extension point="xbmc.addon.metadata">
        <summary lang="en">{summary}</summary>
        <description lang="en">{description}</description>
        <platform>all</platform>
        <assets>
            <icon>icon.png</icon>
            <fanart>fanart.png</fanart>
        </assets>
    </extension>
</addon>
```

- [ ] **Step 2: Write the failing test**

```python
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 -m pytest tests/test_repository_addon.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'kodirepo.repository_addon'`

- [ ] **Step 4: Write the implementation**

```python
"""Render and package the per-channel repository addon."""

import os
import zipfile


def render_addon_xml(template, *, id, name, version, base_url, channel,
                     summary, description):
    """Fill the repository addon.xml template for one channel."""
    return template.format(
        id=id, name=name, version=version,
        base_url=base_url.rstrip("/"), channel=channel,
        summary=summary, description=description,
    )


def build_zip(addon_id, addon_xml_str, assets_dir, dest_zip):
    """Zip the repository addon (addon.xml + icon/fanart) under a top-level dir."""
    os.makedirs(os.path.dirname(dest_zip), exist_ok=True)
    with zipfile.ZipFile(dest_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{addon_id}/addon.xml", addon_xml_str)
        for fname in ("icon.png", "fanart.png"):
            src = os.path.join(assets_dir, fname)
            if os.path.exists(src):
                zf.write(src, f"{addon_id}/{fname}")
    return dest_zip
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m pytest tests/test_repository_addon.py -q`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add build/templates/repository.addon.xml build/kodirepo/repository_addon.py tests/test_repository_addon.py
git commit -m "feat: render and package per-channel repository addon"
```

---

## Task 7: Landing page (`landing.py`)

**Files:**
- Create: `build/templates/index.html`
- Create: `build/kodirepo/landing.py`
- Test: `tests/test_landing.py`

- [ ] **Step 1: Create the template `build/templates/index.html`**

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Appz4Fun Kodi Repository</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 720px; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; }}
  table {{ border-collapse: collapse; width: 100%; margin: 0.5rem 0 1.5rem; }}
  th, td {{ border: 1px solid #ccc; padding: 0.35rem 0.6rem; text-align: left; }}
  code {{ background: #f2f2f2; padding: 0.1rem 0.3rem; border-radius: 3px; }}
  a.dl {{ font-weight: 600; }}
</style>
</head>
<body>
<h1>Appz4Fun Kodi Repository</h1>
<p>Pick a channel, download its repository add-on, and install it in Kodi via
<em>Add-ons &rarr; Install from zip file</em>. Kodi will then auto-update along that channel.</p>
{channels}
<h2>How to install</h2>
<ol>
  <li>Settings &rarr; System &rarr; Add-ons &rarr; enable <strong>Unknown sources</strong>.</li>
  <li>Add-ons &rarr; <em>Install from zip file</em> &rarr; choose the channel zip above.</li>
  <li>Add-ons &rarr; <em>Install from repository</em> &rarr; Appz4Fun Repository &rarr; install add-ons.</li>
</ol>
</body>
</html>
```

- [ ] **Step 2: Write the failing test**

```python
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 -m pytest tests/test_landing.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'kodirepo.landing'`

- [ ] **Step 4: Write the implementation**

```python
"""Render the human-facing landing page (index.html)."""

import html as _html


def render_index(template, *, base_url, channels):
    """Render index.html.

    channels: {channel_name: {"repo_id", "repo_version", "addons": {id: version}}}
    The template uses Python str.format, so its literal CSS braces are doubled
    ({{ }}); only the {channels} placeholder is substituted here.
    """
    base = base_url.rstrip("/")
    blocks = []
    for channel, info in channels.items():
        repo_id = info["repo_id"]
        repo_ver = info["repo_version"]
        link = f"{base}/{channel}/{repo_id}/{repo_id}-{repo_ver}.zip"
        rows = "\n".join(
            f"<tr><td>{_html.escape(aid)}</td><td>{_html.escape(ver)}</td></tr>"
            for aid, ver in sorted(info["addons"].items())
        )
        blocks.append(
            f'<section><h2>{channel.title()} channel</h2>'
            f'<p><a class="dl" href="{link}">Download {repo_id}-{repo_ver}.zip</a></p>'
            f"<table><thead><tr><th>Add-on</th><th>Version</th></tr></thead>"
            f"<tbody>{rows}</tbody></table></section>"
        )
    return template.format(channels="\n".join(blocks))
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m pytest tests/test_landing.py -q`
Expected: PASS (1 passed)

- [ ] **Step 6: Commit**

```bash
git add build/templates/index.html build/kodirepo/landing.py tests/test_landing.py
git commit -m "feat: render landing page with channel install links"
```

---

## Task 8: Per-channel orchestration (`builder.py`)

**Files:**
- Create: `build/kodirepo/builder.py`
- Test: `tests/test_builder.py`

- [ ] **Step 1: Write the failing test**

```python
import os

from kodirepo.builder import build_channel
from kodirepo.addon_zip import read_addon
from kodirepo.aggregate import md5_hex
from conftest import make_addon_zip

TEMPLATE = open(
    os.path.join(os.path.dirname(__file__), "..", "build", "templates", "repository.addon.xml"),
    encoding="utf-8",
).read()

REPO_CFG = {
    "id": "repository.appz4fun.stable",
    "name": "Appz4Fun Repository",
    "version": "1.0.0",
    "summary": "Appz4Fun add-ons",
    "description": "Stable channel.",
}


def _record(zip_path):
    aid, ver, xml, top = read_addon(zip_path)
    return {"id": aid, "version": ver, "zip_path": zip_path, "addon_xml": xml, "top_dir": top}


def test_build_channel_lays_out_tree_and_catalog(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    old = _record(make_addon_zip(str(src), version="1.0.0"))
    new = _record(make_addon_zip(str(src), version="1.1.0"))
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "icon.png").write_bytes(b"\x89PNGicon")
    (assets / "fanart.png").write_bytes(b"\x89PNGfan")
    out = tmp_path / "out"

    summary = build_channel(
        channel="stable",
        base_url="https://appz4fun.github.io/Appz4Fun-Kodi-Repo",
        addons=[old, new],
        repo_addon_cfg=REPO_CFG,
        assets_dir=str(assets),
        repo_template=TEMPLATE,
        out_root=str(out),
    )

    chan = out / "stable"
    # Every version retained.
    assert (chan / "plugin.video.sample" / "plugin.video.sample-1.0.0.zip").exists()
    assert (chan / "plugin.video.sample" / "plugin.video.sample-1.1.0.zip").exists()
    # Repository addon zip emitted.
    assert (chan / "repository.appz4fun.stable" / "repository.appz4fun.stable-1.0.0.zip").exists()
    # Artwork from the newest version extracted.
    assert (chan / "plugin.video.sample" / "icon.png").exists()
    # Catalog advertises the NEWEST member version + the repo addon.
    catalog = (chan / "addons.xml").read_text(encoding="utf-8")
    assert 'version="1.1.0"' in catalog
    assert 'version="1.0.0"' not in catalog.split('id="plugin.video.sample"')[1].split("</addon>")[0]
    assert 'id="repository.appz4fun.stable"' in catalog
    # md5 matches.
    assert (chan / "addons.xml.md5").read_text(encoding="utf-8") == md5_hex(catalog)
    # Summary reports newest member versions only.
    assert summary == {"plugin.video.sample": "1.1.0"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_builder.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'kodirepo.builder'`

- [ ] **Step 3: Write the implementation**

```python
"""Assemble one channel's served tree from resolved addon records."""

import os
import shutil

from .addon_zip import extract_artwork
from .aggregate import addon_element, build_addons_xml, md5_hex
from .repository_addon import render_addon_xml, build_zip
from .select import newest_per_addon


def build_channel(*, channel, base_url, addons, repo_addon_cfg,
                  assets_dir, repo_template, out_root):
    """Write <out_root>/<channel>/ and return {addon_id: newest_version}.

    `addons` is one record per selected release/version, each with keys
    id, version, zip_path, addon_xml (bytes), top_dir. Every version's zip is
    retained; the catalog advertises the newest per addon plus the channel's
    own repository addon.
    """
    chan_dir = os.path.join(out_root, channel)

    # 1. Retain every version's zip under <channel>/<id>/.
    for rec in addons:
        dst = os.path.join(chan_dir, rec["id"], f"{rec['id']}-{rec['version']}.zip")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(rec["zip_path"], dst)

    # 2. Newest per addon (for catalog + artwork).
    newest = newest_per_addon(addons)
    for addon_id, rec in newest.items():
        extract_artwork(rec["zip_path"], rec["top_dir"], rec["addon_xml"],
                        os.path.join(chan_dir, addon_id))

    # 3. Channel repository addon.
    repo_xml = render_addon_xml(
        repo_template, id=repo_addon_cfg["id"], name=repo_addon_cfg["name"],
        version=repo_addon_cfg["version"], base_url=base_url, channel=channel,
        summary=repo_addon_cfg["summary"], description=repo_addon_cfg["description"],
    )
    repo_zip = os.path.join(
        chan_dir, repo_addon_cfg["id"],
        f"{repo_addon_cfg['id']}-{repo_addon_cfg['version']}.zip",
    )
    build_zip(repo_addon_cfg["id"], repo_xml, assets_dir, repo_zip)

    # 4. Catalog = newest member elements + repo addon element.
    elements = [addon_element(rec["addon_xml"]) for rec in newest.values()]
    elements.append(addon_element(repo_xml.encode("utf-8")))
    doc = build_addons_xml(elements)
    with open(os.path.join(chan_dir, "addons.xml"), "w", encoding="utf-8") as fh:
        fh.write(doc)
    with open(os.path.join(chan_dir, "addons.xml.md5"), "w", encoding="utf-8") as fh:
        fh.write(md5_hex(doc))

    return {addon_id: rec["version"] for addon_id, rec in newest.items()}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_builder.py -q`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add build/kodirepo/builder.py tests/test_builder.py
git commit -m "feat: assemble per-channel served tree and catalog"
```

---

## Task 9: GitHub API client + asset cache (`github.py`)

**Files:**
- Create: `build/kodirepo/github.py`
- Test: `tests/test_github.py`

- [ ] **Step 1: Write the failing test** (offline — exercises the cache short-circuit and URL building, no network)

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_github.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'kodirepo.github'`

- [ ] **Step 3: Write the implementation**

```python
"""Minimal GitHub REST client + asset download cache (stdlib only)."""

import json
import os
import urllib.request

API = "https://api.github.com"


def _request(url, token=None):
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "appz4fun-kodi-repo")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def list_releases(repo, token=None):
    """Return the published+draft releases for owner/repo (newest first)."""
    return json.loads(_request(f"{API}/repos/{repo}/releases?per_page=100", token))


def download_asset(url, dest, token=None):
    """Download a release asset to dest (browser_download_url, public, no auth)."""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "appz4fun-kodi-repo")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=300) as resp, open(dest, "wb") as fh:
        fh.write(resp.read())
    return dest


def download_asset_cached(asset, cache_dir, token=None):
    """Return a local path to the asset zip, downloading only on cache miss.

    Cache key is the immutable asset id; an existing non-empty file is reused.
    """
    os.makedirs(cache_dir, exist_ok=True)
    dest = os.path.join(cache_dir, f"{asset['id']}.zip")
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest
    return download_asset(asset["browser_download_url"], dest, token)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_github.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add build/kodirepo/github.py tests/test_github.py
git commit -m "feat: add GitHub releases client with asset cache"
```

---

## Task 10: CLI wiring (`build_repo.py`)

**Files:**
- Create: `build/build_repo.py`
- Test: `tests/test_build_repo.py`

- [ ] **Step 1: Write the failing test** (drives the full build offline via injected fakes)

```python
import os
import sys

BUILD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build")
if BUILD_DIR not in sys.path:
    sys.path.insert(0, BUILD_DIR)

import build_repo
from kodirepo.addon_zip import read_addon
from conftest import make_addon_zip


def test_build_produces_both_channels(tmp_path):
    # One stable release (1.0.0) and one pre-release (1.1.0-beta).
    src = tmp_path / "src"
    src.mkdir()
    stable_zip = make_addon_zip(str(src), version="1.0.0")
    beta_zip = make_addon_zip(str(src), version="1.1.0-beta")

    releases = [
        {"tag_name": "v1.1.0-beta", "prerelease": True, "draft": False,
         "assets": [{"id": 2, "name": "plugin.video.sample-1.1.0-beta.zip",
                     "browser_download_url": "https://x/2"}]},
        {"tag_name": "v1.0.0", "prerelease": False, "draft": False,
         "assets": [{"id": 1, "name": "plugin.video.sample-1.0.0.zip",
                     "browser_download_url": "https://x/1"}]},
    ]
    asset_files = {1: stable_zip, 2: beta_zip}

    def fake_list_releases(repo, token=None):
        return releases

    def fake_download(asset, cache_dir, token=None):
        return asset_files[asset["id"]]

    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "icon.png").write_bytes(b"\x89PNGicon")
    (assets / "fanart.png").write_bytes(b"\x89PNGfan")
    out = tmp_path / "out"

    build_repo.build(
        sources={"base_url": "https://appz4fun.github.io/Appz4Fun-Kodi-Repo",
                 "repositories": ["Appz4Fun/sample"]},
        out_root=str(out),
        cache_dir=str(tmp_path / "cache"),
        assets_dir=str(assets),
        token=None,
        list_releases=fake_list_releases,
        download=fake_download,
    )

    # Stable: only 1.0.0; Beta: newest is 1.1.0-beta.
    stable_catalog = (out / "stable" / "addons.xml").read_text(encoding="utf-8")
    beta_catalog = (out / "beta" / "addons.xml").read_text(encoding="utf-8")
    assert 'version="1.0.0"' in stable_catalog
    assert "1.1.0-beta" not in stable_catalog
    assert "1.1.0-beta" in beta_catalog
    # Stable advertises its own repo addon; beta advertises the beta one.
    assert 'id="repository.appz4fun.stable"' in stable_catalog
    assert 'id="repository.appz4fun.beta"' in beta_catalog
    # Landing page exists and links both channels.
    index = (out / "index.html").read_text(encoding="utf-8")
    assert "Stable channel" in index and "Beta channel" in index
    # Beta retained both versions; stable retained only the stable one.
    assert (out / "beta" / "plugin.video.sample" / "plugin.video.sample-1.1.0-beta.zip").exists()
    assert (out / "stable" / "plugin.video.sample" / "plugin.video.sample-1.0.0.zip").exists()
    assert not (out / "stable" / "plugin.video.sample" / "plugin.video.sample-1.1.0-beta.zip").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_build_repo.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'build_repo'`

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/env python3
"""Build the Appz4Fun Kodi repository tree into out/ from source releases."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kodirepo import github
from kodirepo.addon_zip import read_addon
from kodirepo.builder import build_channel
from kodirepo.landing import render_index
from kodirepo.select import releases_for_channel, pick_zip_asset

CHANNELS = ("stable", "beta")

REPO_ADDONS = {
    "stable": {
        "id": "repository.appz4fun.stable",
        "name": "Appz4Fun Repository",
        "version": "1.0.0",
        "summary": "Appz4Fun Kodi add-ons (stable)",
        "description": "Stable channel for Appz4Fun Kodi add-ons. Auto-updates.",
    },
    "beta": {
        "id": "repository.appz4fun.beta",
        "name": "Appz4Fun Repository (Beta)",
        "version": "1.0.0",
        "summary": "Appz4Fun Kodi add-ons (beta)",
        "description": "Beta channel for Appz4Fun Kodi add-ons, including pre-releases.",
    },
}

HERE = os.path.dirname(os.path.abspath(__file__))


def _resolve(sources, cache_dir, token, list_releases, download):
    """Download each repo's release zips and read authoritative addon metadata."""
    resolved = []
    for repo in sources["repositories"]:
        for rel in list_releases(repo, token):
            if rel.get("draft"):
                continue
            asset = pick_zip_asset(rel)
            if asset is None:
                print(f"WARN {repo} {rel.get('tag_name')}: no usable .zip asset; skipping")
                continue
            zip_path = download(asset, cache_dir, token)
            try:
                addon_id, version, xml, top = read_addon(zip_path)
            except ValueError as exc:
                print(f"WARN {repo} {rel.get('tag_name')}: {exc}; skipping")
                continue
            resolved.append({
                "prerelease": bool(rel.get("prerelease")),
                "id": addon_id, "version": version,
                "zip_path": zip_path, "addon_xml": xml, "top_dir": top,
            })
    return resolved


def build(sources, out_root, cache_dir, assets_dir, token,
          list_releases=github.list_releases, download=github.download_asset_cached):
    """Build both channels into out_root and write the landing page."""
    repo_template = open(os.path.join(HERE, "templates", "repository.addon.xml"), encoding="utf-8").read()
    index_template = open(os.path.join(HERE, "templates", "index.html"), encoding="utf-8").read()
    base_url = sources["base_url"]

    resolved = _resolve(sources, cache_dir, token, list_releases, download)
    if not resolved:
        raise SystemExit("ERROR: no addons resolved from any source repo; refusing to publish empty repo")

    channels_summary = {}
    for channel in CHANNELS:
        addons = [r for r in resolved if channel == "beta" or not r["prerelease"]]
        cfg = REPO_ADDONS[channel]
        summary = build_channel(
            channel=channel, base_url=base_url, addons=addons,
            repo_addon_cfg=cfg, assets_dir=assets_dir,
            repo_template=repo_template, out_root=out_root,
        )
        channels_summary[channel] = {
            "repo_id": cfg["id"], "repo_version": cfg["version"], "addons": summary,
        }

    with open(os.path.join(out_root, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(render_index(index_template, base_url=base_url, channels=channels_summary))
    return channels_summary


def main():
    root = os.path.dirname(HERE)  # repo root
    sources = json.load(open(os.path.join(root, "sources.json"), encoding="utf-8"))
    build(
        sources=sources,
        out_root=os.path.join(root, "out"),
        cache_dir=os.path.join(root, ".cache", "assets"),
        assets_dir=os.path.join(root, "assets"),
        token=os.environ.get("GITHUB_TOKEN"),
    )
    print("Built repository into out/")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_build_repo.py -q`
Expected: PASS (1 passed)

- [ ] **Step 5: Run the full suite**

Run: `python3 -m pytest -q`
Expected: PASS (all tasks' tests green)

- [ ] **Step 6: Commit**

```bash
git add build/build_repo.py tests/test_build_repo.py
git commit -m "feat: wire CLI that builds both channels from source releases"
```

---

## Task 11: Repository artwork placeholders (`assets/`)

**Files:**
- Create: `assets/icon.png`
- Create: `assets/fanart.png`

- [ ] **Step 1: Generate simple placeholder PNGs with stdlib (no Pillow)**

Run from repo root:

```bash
python3 - <<'PY'
import os, struct, zlib

def write_png(path, width, height, rgb):
    def chunk(typ, data):
        c = typ + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xffffffff)
    raw = bytearray()
    row = bytes(rgb) * width
    for _ in range(height):
        raw += b"\x00" + row
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(png)

write_png("assets/icon.png", 256, 256, (32, 80, 160))      # solid blue 256x256
write_png("assets/fanart.png", 1280, 720, (16, 24, 40))    # dark 16:9 fanart
print("wrote assets/icon.png and assets/fanart.png")
PY
```

- [ ] **Step 2: Verify the PNGs are valid**

Run: `python3 -c "import struct;
for p in ('assets/icon.png','assets/fanart.png'):
    d=open(p,'rb').read(); assert d[:8]==b'\x89PNG\r\n\x1a\n', p; print(p, len(d), 'bytes OK')"`
Expected: both files report `OK`

- [ ] **Step 3: Commit**

```bash
git add assets/icon.png assets/fanart.png
git commit -m "chore: add placeholder repository artwork"
```

> Note: these are plain-color placeholders. Replace `assets/icon.png` (square, ≥256×256) and `assets/fanart.png` (16:9) with real branding anytime — the next build picks them up automatically.

---

## Task 12: GitHub Actions workflow (`sync.yml`)

**Files:**
- Create: `.github/workflows/sync.yml`

- [ ] **Step 1: Create the workflow**

```yaml
name: Build & Deploy Kodi Repository

on:
  schedule:
    - cron: "17 4 * * *"        # daily at 04:17 UTC
  workflow_dispatch: {}
  repository_dispatch:
    types: [addon-released]      # instant trigger from source repo CI
  push:
    branches: [main]
    paths:
      - "sources.json"
      - "build/**"
      - "assets/**"
      - ".github/workflows/sync.yml"

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements-dev.txt
      - run: python -m pytest -q

  build-deploy:
    needs: test
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deploy.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Configure Pages
        uses: actions/configure-pages@v5
      - name: Restore asset cache
        uses: actions/cache@v4
        with:
          path: .cache/assets
          key: kodi-assets-${{ github.run_id }}
          restore-keys: |
            kodi-assets-
      - name: Build repository
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: python build/build_repo.py
      - name: Upload Pages artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: out
      - name: Deploy to GitHub Pages
        id: deploy
        uses: actions/deploy-pages@v4
```

- [ ] **Step 2: Validate the YAML parses**

Run: `python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/sync.yml')); print('workflow YAML OK')"`
Expected: `workflow YAML OK` (if PyYAML is missing, run `pip install pyyaml` first; it is not a project dependency)

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/sync.yml
git commit -m "ci: add scheduled build-and-deploy workflow for GitHub Pages"
```

---

## Task 13: README and operator docs

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`**

````markdown
# Appz4Fun Kodi Repository

A self-hosting, multi-channel [Kodi](https://kodi.tv) add-on repository served from
GitHub Pages. A scheduled GitHub Actions workflow rebuilds the whole repository from
the source repos' GitHub Releases and deploys it — no built artifacts are committed.

**Repository home:** https://appz4fun.github.io/Appz4Fun-Kodi-Repo/

## Channels

| Channel | Install zip | Contents |
|---|---|---|
| Stable | `repository.appz4fun.stable` | Releases not marked pre-release |
| Beta | `repository.appz4fun.beta` | All releases, including pre-releases |

Install a channel's repository zip once (see the landing page), then install add-ons
from it; Kodi auto-updates along that channel.

## Adding an add-on

1. Make sure the add-on's repo publishes a GitHub Release whose asset is a proper
   Kodi add-on zip (unzipping yields a top-level `<id>/` folder containing `addon.xml`).
2. Add `"owner/repo"` to `repositories` in [`sources.json`](sources.json).
3. Push to `main` — the workflow rebuilds and redeploys automatically.

Stable vs. beta is decided per release by the GitHub **pre-release** checkbox.

## Local build

```bash
python3 build/build_repo.py        # writes ./out
python3 -m pytest -q                # run the test suite (needs: pip install -r requirements-dev.txt)
```

## One-time GitHub setup

- **Settings → Pages → Build and deployment → Source: GitHub Actions.**
- The default `GITHUB_TOKEN` is sufficient for the build (source repos are public).

## Optional: instant updates from source CI

The daily schedule guarantees updates within ~24h. For near-instant updates, have each
source repo notify this repo when it publishes a release:

1. Create a fine-grained PAT with **Contents: read and write** scoped to
   `Appz4Fun/Appz4Fun-Kodi-Repo` only. Store it in the **source** repo as the secret
   `REPO_DISPATCH_TOKEN`.
2. Add this step to the source repo's release workflow (after the release is published):

```yaml
- name: Notify Kodi repository
  run: |
    curl -sf -X POST \
      -H "Authorization: Bearer ${{ secrets.REPO_DISPATCH_TOKEN }}" \
      -H "Accept: application/vnd.github+json" \
      https://api.github.com/repos/Appz4Fun/Appz4Fun-Kodi-Repo/dispatches \
      -d '{"event_type":"addon-released"}'
```

## How it works

`build/build_repo.py` lists each source repo's releases, downloads each release's
add-on zip (cached by asset id), reads the authoritative `id`/`version` from the
`addon.xml` inside each zip, and for both channels lays out every version under
`<channel>/<id>/<id>-<version>.zip`, extracts the newest version's artwork, writes
`<channel>/addons.xml` (+ `.md5`) advertising the newest version of each add-on plus
the channel's own repository add-on, and renders `index.html`. The whole tree is
deployed to GitHub Pages as an artifact. See
[`docs/superpowers/specs/2026-06-29-kodi-repository-design.md`](docs/superpowers/specs/2026-06-29-kodi-repository-design.md).
````

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with install, config, and operator instructions"
```

---

## Task 14: Full verification

- [ ] **Step 1: Run the entire test suite**

Run: `cd /Users/allen/git/Appz4Fun-Kodi-Repo && python3 -m pytest -q`
Expected: all tests pass.

- [ ] **Step 2: Run a real end-to-end local build against the live `Appz4Fun/nzbdavkodi` releases**

Run: `cd /Users/allen/git/Appz4Fun-Kodi-Repo && python3 build/build_repo.py && find out -maxdepth 3 -type f | sort`
Expected: `out/index.html`, `out/stable/addons.xml`, `out/stable/addons.xml.md5`,
`out/stable/repository.appz4fun.stable/repository.appz4fun.stable-1.0.0.zip`,
`out/stable/plugin.video.nzbdav/plugin.video.nzbdav-*.zip` (multiple versions), and the
matching `out/beta/...` tree including the `v1.0.0-pre-alpha` build under beta only.

- [ ] **Step 3: Sanity-check the generated stable catalog**

Run: `python3 -c "import re;
d=open('out/stable/addons.xml').read();
import hashlib;
m=open('out/stable/addons.xml.md5').read().strip();
assert hashlib.md5(d.encode()).hexdigest()==m, 'md5 mismatch';
assert 'plugin.video.nzbdav' in d and 'repository.appz4fun.stable' in d;
assert 'pre-alpha' not in d, 'prerelease leaked into stable';
print('stable catalog OK')"`
Expected: `stable catalog OK`

- [ ] **Step 4: Confirm `out/` is git-ignored (not staged)**

Run: `git status --porcelain out/ .cache/`
Expected: empty output (both ignored).

- [ ] **Step 5: Final commit if anything remains**

```bash
git status
# Only docs/specs/plan and source files should be tracked; out/ and .cache/ ignored.
```

---

## Self-Review (completed during planning)

- **Spec coverage:** no-commit Pages deploy → Task 12 (`upload-pages-artifact`/`deploy-pages`, `out/` git-ignored in Task 1). Keep-all-versions → Task 8 (copies every record's zip). Daily + manual + dispatch + push triggers → Task 12. Two channels / two repository addons → Tasks 6, 8, 10. Pre-release classification → Task 5 + Task 10 channel split. Stdlib-only builder → Tasks 2–10 (no third-party imports; `pytest`/`pyyaml` are dev/CI only). Caching → Tasks 9 + 12. Error/edge handling (no-zip skip, empty-repo refusal, prerelease-only addon) → Tasks 5, 10, plus verification in Task 14. Landing page → Task 7. Install docs + dispatch wiring + Pages source setting → Task 13.
- **Placeholder scan:** every code/test/template step contains complete content; no TBD/TODO.
- **Type/name consistency:** function names and record keys (`id`, `version`, `zip_path`, `addon_xml`, `top_dir`; `repo_id`/`repo_version`/`addons`) match across Tasks 3–10 and the contract summary.
