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
