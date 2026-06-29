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
