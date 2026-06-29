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
