"""Render a per-add-on page listing every retained version with download links."""

import html as _html

from .version import parse_version


def render_addon_page(template, *, name, addon_id, channel, versions):
    """Render one add-on's <channel>/<id>/index.html.

    versions: an iterable of version strings (duplicates allowed). They are
    de-duplicated and listed newest-first; each links to the sibling
    <id>-<version>.zip in the same directory. GitHub Pages has no directory
    listing, so this page is what makes every retained version browsable.
    """
    ordered = sorted(set(versions), key=parse_version, reverse=True)
    rows = []
    for i, ver in enumerate(ordered):
        zip_name = f"{addon_id}-{ver}.zip"
        label = _html.escape(ver) + (' <span class="new">(newest)</span>' if i == 0 else "")
        rows.append(
            f"<tr><td>{label}</td>"
            f'<td><a class="dl" href="{_html.escape(zip_name)}">{_html.escape(zip_name)}</a></td></tr>'
        )
    return template.format(
        name=_html.escape(name),
        id=_html.escape(addon_id),
        channel=_html.escape(channel.title()),
        count=len(ordered),
        rows="\n".join(rows),
    )
