"""Read addon metadata and artwork out of a Kodi addon zip."""

import os
import zipfile
import xml.etree.ElementTree as ET


def read_addon(zip_path):
    """Return (addon_id, version, addon_xml_bytes, top_dir) for a Kodi addon zip.

    The id and version are taken from the addon.xml inside the zip — never
    the filename. Raises ValueError if the zip is not a valid Kodi addon: a
    corrupt archive, a missing or malformed addon.xml, a missing id/version,
    or a top-level folder whose name does not match the addon id (Kodi
    requires the add-on folder to be named exactly <id>). Callers treat every
    ValueError as "skip this release", so all of these are reported as one.
    """
    try:
        with zipfile.ZipFile(zip_path) as zf:
            candidates = [n for n in zf.namelist()
                          if n.count("/") == 1 and n.endswith("/addon.xml")]
            if not candidates:
                raise ValueError(f"{zip_path}: no top-level <dir>/addon.xml")
            entry = sorted(candidates)[0]
            data = zf.read(entry)
    except zipfile.BadZipFile as exc:
        raise ValueError(f"{zip_path}: not a readable zip ({exc})") from exc
    top_dir = entry.split("/", 1)[0]
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise ValueError(f"{zip_path}: malformed addon.xml ({exc})") from exc
    addon_id = root.get("id")
    version = root.get("version")
    if not addon_id or not version:
        raise ValueError(f"{zip_path}: addon.xml missing id/version")
    if top_dir != addon_id:
        raise ValueError(
            f"{zip_path}: top folder {top_dir!r} does not match addon id {addon_id!r}")
    return addon_id, version, data, top_dir


def _find_assets(root):
    for ext in root.findall("extension"):
        if ext.get("point") == "xbmc.addon.metadata":
            assets = ext.find("assets")
            if assets is not None:
                return assets
    return None


def extract_artwork(zip_path, top_dir, addon_xml_bytes, dest_dir):
    """Extract icon/fanart referenced in addon.xml <assets> into dest_dir,
    keeping each asset's declared relative path.

    Kodi resolves a repository add-on's pre-install artwork via the <assets>
    paths under <datadir>/<id>/, so an asset declared as resources/icon.png is
    written to dest_dir/resources/icon.png (not flattened to icon.png) — the
    served catalog advertises that same relative path. Missing assets are
    skipped silently; artwork is best-effort, not required.
    """
    assets = _find_assets(ET.fromstring(addon_xml_bytes))
    if assets is None:
        return
    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())
        for tag in ("icon", "fanart"):
            el = assets.find(tag)
            rel = (el.text or "").strip() if el is not None else ""
            if not rel:
                continue
            src = f"{top_dir}/{rel}"
            if src not in names:
                continue
            # The declared path becomes a write destination, so refuse anything
            # that would escape dest_dir (hostile addon.xml).
            dest = os.path.normpath(os.path.join(dest_dir, rel))
            if os.path.relpath(dest, dest_dir).startswith(os.pardir):
                continue
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as fh:
                fh.write(zf.read(src))
