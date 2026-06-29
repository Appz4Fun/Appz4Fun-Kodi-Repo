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
