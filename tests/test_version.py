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
