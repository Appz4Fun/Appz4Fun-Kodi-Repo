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
