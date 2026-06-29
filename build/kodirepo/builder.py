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
