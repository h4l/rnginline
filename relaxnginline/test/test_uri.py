from __future__ import unicode_literals

from six.moves import urllib

import pytest

from relaxnginline import uri


def test_urllib_urljoin_does_not_work_for_us():
    """The reason for the uri module to exist."""

    # bad
    assert (urllib.parse.urljoin("custom://a/b/c/foo.txt", "bar.txt")
            == "bar.txt")  # Not what I'd expect

    # good!
    assert (uri.resolve("custom://a/b/c/foo.txt", "bar.txt")
            == "custom://a/b/c/bar.txt")  # What I'd expect


def test_urllib_parsing_is_not_that_great():
    assert urllib.parse.unquote("f%69le:///foo") == "file:///foo"
    assert urllib.parse.urlsplit("f%69le:///foo") == (
        "", "", "f%69le:///foo", "", "")  # WTF...


# Test here are from RFC 3986 section 5.4:
# http://tools.ietf.org/html/rfc3986#section-5.4

# The test cases all resolve against this base
BASE = ("http://a/b/c/d;p?q",)

# a relative reference is transformed to its target URI as follows.
@pytest.mark.parametrize("base,reference,target", [
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
    BASE + ("g#s/../x", "http://a/b/c/g#s/../x")
])
def test_resolve(base, reference, target):
    assert uri.resolve(base, reference) == target


@pytest.mark.parametrize("base,reference,target,strict", [
    # Final 2 examples from 5.4.2.
    BASE + ("http:g", "http:g", True),  # for strict/modern parsers
    BASE + ("http:g", "http://a/b/c/g", False)  # for backward compatibility
])
def test_strict_resolve(base, reference, target, strict):
    assert uri.resolve(base, reference, strict=strict) == target


def test_recombine_rejects_relative_paths_with_netloc():
    with pytest.raises(uri.UriSyntaxError):
        # This would produce "foorel/path" if an error was not raised.
        # We could do what urllib does and insert a leading /, but this doesn't
        # sit well with PEP 20 IMO.
        uri.recombine(("", "foo", "rel/path", "", ""))
