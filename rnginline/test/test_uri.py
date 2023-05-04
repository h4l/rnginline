from __future__ import annotations

import urllib

import pytest

from rnginline import uri


def test_urllib_urljoin_does_not_work_for_us() -> None:
    """The reason for the uri module to exist."""

    # bad
    assert (
        urllib.parse.urljoin("custom://a/b/c/foo.txt", "bar.txt") == "bar.txt"
    )  # Not what I'd expect

    # good!
    assert (
        uri.resolve("custom://a/b/c/foo.txt", "bar.txt") == "custom://a/b/c/bar.txt"
    )  # What I'd expect


def test_urllib_parsing_is_not_that_great() -> None:
    assert urllib.parse.unquote("f%69le:///foo") == "file:///foo"
    assert urllib.parse.urlsplit("f%69le:///foo") == (
        "",
        "",
        "f%69le:///foo",
        "",
        "",
    )  # WTF...


def test_urllib_urlunsplit_adds_empty_netloc_on_file_urls() -> None:
    parts = ("file", "", "/foo/bar", "", "")
    assert urllib.parse.urlunsplit(parts) == "file:///foo/bar"

    assert uri.recombine(parts) == "file:/foo/bar"


# Test here are from RFC 3986 section 5.4:
# http://tools.ietf.org/html/rfc3986#section-5.4

# The test cases all resolve against this base
BASE = ("http://a/b/c/d;p?q",)


# a relative reference is transformed to its target URI as follows.
@pytest.mark.parametrize(
    "base,reference,target",
    [
        # Normal Examples from: http://tools.ietf.org/html/rfc3986#section-5.4.1
        BASE + ("g:h", "g:h"),
        BASE + ("g", "http://a/b/c/g"),
        BASE + ("./g", "http://a/b/c/g"),
        BASE + ("g/", "http://a/b/c/g/"),
        BASE + ("/g", "http://a/g"),
        BASE + ("//g", "http://g"),
        BASE + ("?y", "http://a/b/c/d;p?y"),
        BASE + ("g?y", "http://a/b/c/g?y"),
        BASE + ("#s", "http://a/b/c/d;p?q#s"),
        BASE + ("g#s", "http://a/b/c/g#s"),
        BASE + ("g?y#s", "http://a/b/c/g?y#s"),
        BASE + (";x", "http://a/b/c/;x"),
        BASE + ("g;x", "http://a/b/c/g;x"),
        BASE + ("g;x?y#s", "http://a/b/c/g;x?y#s"),
        BASE + ("", "http://a/b/c/d;p?q"),
        BASE + (".", "http://a/b/c/"),
        BASE + ("./", "http://a/b/c/"),
        BASE + ("..", "http://a/b/"),
        BASE + ("../", "http://a/b/"),
        BASE + ("../g", "http://a/b/g"),
        BASE + ("../..", "http://a/"),
        BASE + ("../../", "http://a/"),
        BASE + ("../../g", "http://a/g"),
        # Abnormal examples from: http://tools.ietf.org/html/rfc3986#section-5.4.2
        BASE + ("../../../g", "http://a/g"),
        BASE + ("../../../../g", "http://a/g"),
        BASE + ("/./g", "http://a/g"),
        BASE + ("/../g", "http://a/g"),
        BASE + ("g.", "http://a/b/c/g."),
        BASE + (".g", "http://a/b/c/.g"),
        BASE + ("g..", "http://a/b/c/g.."),
        BASE + ("..g", "http://a/b/c/..g"),
        BASE + ("./../g", "http://a/b/g"),
        BASE + ("./g/.", "http://a/b/c/g/"),
        BASE + ("g/./h", "http://a/b/c/g/h"),
        BASE + ("g/../h", "http://a/b/c/h"),
        BASE + ("g;x=1/./y", "http://a/b/c/g;x=1/y"),
        BASE + ("g;x=1/../y", "http://a/b/c/y"),
        BASE + ("g?y/./x", "http://a/b/c/g?y/./x"),
        BASE + ("g?y/../x", "http://a/b/c/g?y/../x"),
        BASE + ("g#s/./x", "http://a/b/c/g#s/./x"),
        BASE + ("g#s/../x", "http://a/b/c/g#s/../x"),
        # Extras not from the RFC:
        # Resolving relative path against abs URI w/ no path
        ("x://blah", "rel/path", "x://blah/rel/path"),
        ("x://blah", "./rel/path", "x://blah/rel/path"),
        ("x://blah", ".", "x://blah/"),
        ("x://blah", "..", "x://blah/"),
        ("z:relpath", ".", "z:"),
        ("z:relpath", "..", "z:"),
        ("x://blah", "y:../rel/path", "y:rel/path"),
        ("x://blah", "y:./rel/path", "y:rel/path"),
    ],
)
def test_resolve(base: str, reference: str, target: str) -> None:
    assert uri.resolve(base, reference) == target


@pytest.mark.parametrize(
    "base,reference,target,strict",
    [
        # Final 2 examples from 5.4.2.
        BASE + ("http:g", "http:g", True),  # for strict/modern parsers
        BASE + ("http:g", "http://a/b/c/g", False),  # for backward compatibility
    ],
)
def test_strict_resolve(base: str, reference: str, target: str, strict: bool) -> None:
    assert uri.resolve(base, reference, strict=strict) == target


@pytest.mark.parametrize(
    "base,raises",
    [
        ("x:/blah", False),
        ("x:/blah blah", True),  # contains space
        ("", True),
        ("/a/path", True),
        ("//host/a/path", True),
    ],
)
def test_resolve_base_must_be_uri(base: str, raises: bool) -> None:
    if raises is True:
        with pytest.raises(ValueError):
            uri.resolve(base, "")
    else:
        uri.resolve(base, "")


@pytest.mark.parametrize(
    "ref,raises",
    [
        ("x:/blah", False),
        ("x:/blah blah", True),  # contains space
        ("", False),
        ("/a/path", False),
        ("//host/a/path", False),
    ],
)
def test_resolve_reference_must_be_uri_ref(ref: str, raises: bool) -> None:
    if raises is True:
        with pytest.raises(ValueError):
            uri.resolve("x:/foo", ref)
    else:
        uri.resolve("x:/foo", ref)


@pytest.mark.parametrize(
    "parts,expected",
    [
        # testcases are cartesian product of:
        # [("", "a"), ("", "b"), ("", "c", "/c"), ("", "d=d"), ("", "e")]
        (("", "", "", "", ""), ""),
        (("", "", "", "", "e"), "#e"),
        (("", "", "", "d=d", ""), "?d=d"),
        (("", "", "", "d=d", "e"), "?d=d#e"),
        (("", "", "c", "", ""), "c"),
        (("", "", "c", "", "e"), "c#e"),
        (("", "", "c", "d=d", ""), "c?d=d"),
        (("", "", "c", "d=d", "e"), "c?d=d#e"),
        (("", "", "/c", "", ""), "/c"),
        (("", "", "/c", "", "e"), "/c#e"),
        (("", "", "/c", "d=d", ""), "/c?d=d"),
        (("", "", "/c", "d=d", "e"), "/c?d=d#e"),
        (("", "b", "", "", ""), "//b"),
        (("", "b", "", "", "e"), "//b#e"),
        (("", "b", "", "d=d", ""), "//b?d=d"),
        (("", "b", "", "d=d", "e"), "//b?d=d#e"),
        (("", "b", "c", "", ""), None),  # syntax error
        (("", "b", "c", "", "e"), None),
        (("", "b", "c", "d=d", ""), None),
        (("", "b", "c", "d=d", "e"), None),
        (("", "b", "/c", "", ""), "//b/c"),
        (("", "b", "/c", "", "e"), "//b/c#e"),
        (("", "b", "/c", "d=d", ""), "//b/c?d=d"),
        (("", "b", "/c", "d=d", "e"), "//b/c?d=d#e"),
        (("a", "", "", "", ""), "a:"),
        (("a", "", "", "", "e"), "a:#e"),
        (("a", "", "", "d=d", ""), "a:?d=d"),
        (("a", "", "", "d=d", "e"), "a:?d=d#e"),
        (("a", "", "c", "", ""), "a:c"),
        (("a", "", "c", "", "e"), "a:c#e"),
        (("a", "", "c", "d=d", ""), "a:c?d=d"),
        (("a", "", "c", "d=d", "e"), "a:c?d=d#e"),
        (("a", "", "/c", "", ""), "a:/c"),
        (("a", "", "/c", "", "e"), "a:/c#e"),
        (("a", "", "/c", "d=d", ""), "a:/c?d=d"),
        (("a", "", "/c", "d=d", "e"), "a:/c?d=d#e"),
        (("a", "b", "", "", ""), "a://b"),
        (("a", "b", "", "", "e"), "a://b#e"),
        (("a", "b", "", "d=d", ""), "a://b?d=d"),
        (("a", "b", "", "d=d", "e"), "a://b?d=d#e"),
        (("a", "b", "c", "", ""), None),
        (("a", "b", "c", "", "e"), None),
        (("a", "b", "c", "d=d", ""), None),
        (("a", "b", "c", "d=d", "e"), None),
        (("a", "b", "/c", "", ""), "a://b/c"),
        (("a", "b", "/c", "", "e"), "a://b/c#e"),
        (("a", "b", "/c", "d=d", ""), "a://b/c?d=d"),
        (("a", "b", "/c", "d=d", "e"), "a://b/c?d=d#e"),
    ],
)
def test_recombine(parts: tuple[str, str, str, str, str], expected: str | None) -> None:
    if expected is None:
        assert parts[1] and not parts[2].startswith("/")
        with pytest.raises(uri.UriSyntaxError):
            # This would produce "bc" if an error was not raised.
            # We could do what urllib does and insert a leading /, but this
            # doesn't sit well with PEP 20 IMO.
            uri.recombine(parts)
    else:
        assert uri.recombine(parts) == expected
