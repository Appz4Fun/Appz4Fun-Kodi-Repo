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


def test_prerelease_suffix_compares_numerically():
    # Same core, numbered prereleases: beta10 is newer than beta2 (not a string compare).
    assert parse_version("1.0.0-beta10") > parse_version("1.0.0-beta2")


def test_dotted_prerelease_suffix_compares_numerically():
    assert parse_version("1.0.0-beta.10") > parse_version("1.0.0-beta.2")
