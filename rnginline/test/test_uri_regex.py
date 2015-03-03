from __future__ import unicode_literals

import pytest

from rnginline.test.test_regexbuilder import (
    _TestCase as tc, _TestString as ts)
from rnginline import uri_regex as ur


@pytest.mark.parametrize("test_case", [
    tc(ur.DIGIT, ~ts("a"), ~ts("x"), *list("0123456789")),
    tc(ur.ALPHA, ~ts("9"), ~ts("0"), *list("abcdefghijklmnopqrstuvwxyz"
                                           "ABCDEFGHIJKLMNOPQRSTUVWXYZ")),
    tc(ur.HEXDIG, ~ts("g"), ~ts("z"), *list("abcdefABCDEF0123456789")),

    tc(ur.sub_delims, ~ts("g"), ~ts("z"), *list("!$&'()*+,;=")),
    tc(ur.gen_delims, ~ts("g"), ~ts("z"), *list(":/?#[]@")),
    tc(ur.reserved, ~ts("g"), ~ts("z"), *list("!$&'()*+,;=:/?#[]@")),
    tc(ur.unreserved, ~ts("%"), ~ts("!"), *list("azAZhIjK0956-._~")),

    tc(ur.pct_encoded, ~ts("%3"), ~ts("%434"), "%FF", "%00", "%f8"),

    tc(ur.pchar, ~ts("?"), ~ts("#"), ~ts("/"), "%12",
       *list("abc:@foo-._~!$&'()*+,;=")),

    tc(ur.query,   "", "???", "?abcDef-._~123/?:@!$&'()*+,;=%27",
       *[~ts(x) for x in "#[]"]),
    tc(ur.fragment, "", "???", "?abcDef-._~123/?:@!$&'()*+,;=%27",
       *[~ts(x) for x in "#[]"]),

    tc(ur.segment_nz_nc, ~ts(""), ~ts(":"), ~ts("foo:bar"),
       "!$&'()*+,;=az09AZ@%dd-._~"),

    tc(ur.segment_nz, ~ts(""), "a", "ab", "abc:@foo-._~!$&'()*+,;="),
    tc(ur.segment, "", "a", "ab", "abc:@foo-._~!$&'()*+,;="),

    tc(ur.path_empty, "", ~ts("a"), ~ts("ab")),

    tc(ur.path_rootless, ~ts("/"), ~ts("/foo"), "foo", "foo/bar", "foo/",
       "!/!", "ab;cd/e/f/g/;", "notascheme:foo/bar/baz"),

    tc(ur.path_noscheme, ~ts("/"), ~ts("/foo"), "foo", "foo/bar", "foo/",
       "!/!", "ab;cd/e/f/g/;", ~ts("couldbescheme:foo/bar/baz")),

    tc(ur.path_absolute, ~ts(""), ~ts("a/b/c"), ~ts("//foo"), "/a//foo", "/",
       "/a/b/c", "/aa/bb/"),

    tc(ur.path_abempty, ~ts("foo/bar"), ~ts("a"), "", "/", "//", "/foo",
       "/foo/bar//baz"),

    tc(ur.path, "", "/", "//", "/foo", "/foo/b/a/r", "foo:bar",
       "foo:bar/baz", "foo", "foo/b/a/r/", "foo/b/a/r"),

    tc(ur.reg_name, "", "abcDEF%ab-._~!$&'()*+,;=",
       *[~ts(x) for x in ":/?#[]@"]),

    tc(ur.dec_octet, "0", "9", "10", "99", "100", "199", "200", "249", "250",
       "255", ~ts("256"), ~ts("-1"), ~ts("foo"), ~ts(""), ~ts("01"),
       ~ts("001")),

    tc(ur.ipv4address, "0.0.0.0", "255.255.255.255", "1.22.33.44",
       ~ts("0a0a0a0"), ~ts("123..123.123.123"), ~ts("")),

    tc(ur.h16, "f", "F", "1a", "fa3", "aBcd", "01", "001", "0001",
       ~ts("abcd0"), ~ts("")),

    tc(ur.ls32, "ffff:ffff", "1.1.1.1", "ab:1", ~ts(""), ~ts("1::2")),

    tc(ur.ipv6address,
       # 1st alternative
       "1:2:3:4:5:6:7:8", "1:2:3:4:5:6:77.77.88.88",
       # 2
       "::2:3:4:5:6:7:8", "::2:3:4:5:6:77.77.88.88",

       # 3
       "::3:4:5:6:7:8", "::3:4:5:6:77.77.88.88",
       "1::3:4:5:6:7:8", "1::3:4:5:6:77.77.88.88",


       # 4
       "::4:5:6:7:8", "::4:5:6:77.77.88.88",
       "1::4:5:6:7:8", "1::4:5:6:77.77.88.88",
       "1:2::4:5:6:7:8", "1:2::4:5:6:77.77.88.88",

       # 5
       "::5:6:7:8", "::5:6:77.77.88.88",
       "1::5:6:7:8", "1::5:6:77.77.88.88",
       "1:2::5:6:7:8", "1:2::5:6:77.77.88.88",
       "1:2:3::5:6:7:8", "1:2:3::5:6:77.77.88.88",

       # 6
       "::6:7:8", "::6:77.77.88.88",
       "1::6:7:8", "1::6:77.77.88.88",
       "1:2::6:7:8", "1:2::6:77.77.88.88",
       "1:2:3::6:7:8", "1:2:3::6:77.77.88.88",
       "1:2:3:4::6:7:8", "1:2:3:4::6:77.77.88.88",

       # 7
       "::7:8", "::77.77.88.88",
       "1::7:8", "1::77.77.88.88",
       "1:2::7:8", "1:2::77.77.88.88",
       "1:2:3::7:8", "1:2:3::77.77.88.88",
       "1:2:3:4::7:8", "1:2:3:4::77.77.88.88",
       "1:2:3:4:5::7:8", "1:2:3:4:5::77.77.88.88",

       # 8
       "::8",
       "1::8",
       "1:2::8",
       "1:2:3::8",
       "1:2:3:4::8",
       "1:2:3:4:5::8",
       "1:2:3:4:5:6::8",

       # 9
       "::",
       "1::",
       "1:2::",
       "1:2:3::",
       "1:2:3:4::",
       "1:2:3:4:5::",
       "1:2:3:4:5:6::",
       "1:2:3:4:5:6:7::"),

    tc(ur.ipv6address,
       "2001:0db8:0000:0000:0000:ff00:0042:8329",
       "2001:db8:0:0:0:ff00:42:8329",
       "2001:db8::ff00:42:8329",
       "0000:0000:0000:0000:0000:0000:0000:0001"),

    tc(ur.ipvfuture, "vB33F.Is:A:Tasty:Food!$&'()*+,;="),

    tc(ur.ip_literal, "[1::2]", "[v1000.1234]"),

    tc(ur.port, "", "1", "9999", ~ts("FF")),

    tc(ur.host, "123.123.123.123", "[ffff::]", "[v1.1]", "", "example.com",
       *[~ts(x) for x in ":/?#[]@"]),

    tc(ur.userinfo, "", "-._~!$&'()*+,;=:abc123ABC",
       *[~ts(x) for x in "/?#[]@"]),

    tc(ur.authority, "", "foo@bar.baz:123", "bar.baz:123", "foo@bar.baz",
       "foo@:123", "bar.baz"),

    tc(ur.scheme, ~ts(""), "A", "abc+foo-bar.baz"),

    tc(ur.relative_part,
       "//", "//auth", "///a/b/c", "//auth/a/b/c",
       "", "/", "a", "a/b/c",
       # Can't have relative paths which start looking like a scheme
       ~ts("foo:bar"),
       # This is ok though
       "/foo:bar", "a/foo:bar",
       ~ts("foo?bar"), ~ts("foo#bar")),

    tc(ur.relative_ref, "foo?bar", "foo#baz", "foo?bar#baz"),

    # Same as relative_part except we can have scheme-like initial segments in
    # relative paths
    tc(ur.hier_part,
       "//", "//auth", "///a/b/c", "//auth/a/b/c",
       "", "/", "a", "a/b/c",
       # CAN have relative paths which start looking like a scheme
       "foo:bar",
       "/foo:bar", "a/foo:bar",
       ~ts("foo?bar"), ~ts("foo#bar")),

    tc(ur.absolute_uri, ~ts(":foo"), "a:b/c?d", ~ts("a:b/c?d#e")),

    tc(ur.uri,
       "foo://bar/a/b/c;d=1?foo=bar#xyz", "scheme:path", "scheme://auth/path",
       "scheme://auth", "scheme:?query", "scheme:#frag",
       "scheme:path?query#frag", "scheme://auth/path?query#frag"),

    tc(ur.uri_reference, "", "a/b", "a/b?q#f", "/a/b", "s://a",
       "s://", "s:", "//auth/path", "path//a/b",
       "s:a/b/c")
])
def test_uri_regex(test_case):
    test_case.run()


def test_get_regex_raises_on_unknown_name():
    with pytest.raises(ValueError):
        ur.get_regex("fjalksdjflas")
