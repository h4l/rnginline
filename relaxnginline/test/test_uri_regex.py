from __future__ import unicode_literals

import pytest

from relaxnginline.test.test_regexbuilder import (tc, ts)
from relaxnginline import uri_regex as ur


@pytest.mark.parametrize("test_case", [
    tc(ur.DIGIT(), ~ts("a"), ~ts("x"), *list("0123456789")),
    tc(ur.ALPHA(), ~ts("9"), ~ts("0"), *list("abcdefghijklmnopqrstuvwxyz"
                                             "ABCDEFGHIJKLMNOPQRSTUVWXYZ")),
    tc(ur.HEXDIG(), ~ts("g"), ~ts("z"), *list("abcdefABCDEF0123456789")),

    tc(ur.sub_delims(), ~ts("g"), ~ts("z"), *list("!$&'()*+,;=")),
    tc(ur.gen_delims(), ~ts("g"), ~ts("z"), *list(":/?#[]@")),
    tc(ur.reserved(), ~ts("g"), ~ts("z"), *list("!$&'()*+,;=:/?#[]@")),
    tc(ur.unreserved(), ~ts("%"), ~ts("!"), *list("azAZhIjK0956-._~")),

    tc(ur.pct_encoded(), ~ts("%3"), ~ts("%434"), "%FF", "%00", "%f8"),

    tc(ur.pchar(), ~ts("?"), ~ts("#"), ~ts("/"), "%12",
       *list("abc:@foo-._~!$&'()*+,;=")),


    tc(ur.ipv6address(), "2001:0db8:0000:0000:0000:ff00:0042:8329"),
    tc(ur.ipv6address(), "2001:db8:0:0:0:ff00:42:8329"),
    tc(ur.ipv6address(), "2001:db8::ff00:42:8329"),
    tc(ur.ipv6address(), "0000:0000:0000:0000:0000:0000:0000:0001"),
    tc(ur.ipv6address(), "::1"),

    tc(ur.uri(), "foo://bar/a/b/c;d=1?foo=bar#xyz"),
])
def test_uri_regex(test_case):
    test_case.run()
