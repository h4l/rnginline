from __future__ import unicode_literals

from copy import copy

from six.moves import urllib

import pytest
import six

from relaxnginline.regexbuilder import (Literal, Set, OneOrMore, ZeroOrMore,
                                        Choice, Capture, Sequence, Repeat,
                                        Optional, Start, End)


class TestString(object):
    def __init__(self, string, groups=None, length=None, should_match=True):
        self.string = string
        self.groups = groups
        self.length = length
        self.should_match = should_match

    def __invert__(self):
        inverted = copy(self)
        inverted.should_match = not self.should_match
        return inverted

    def run(self, regex):
        match = regex.match(self.string)

        # For debugging
        msg = (match, regex, self.string)

        length = self.length or len(self.string)

        if self.should_match:
            assert match, msg
            assert match.end() == length, msg
            if self.groups is not None:
                assert match.groups() == self.groups, msg
        else:
            assert not match or match.end() != length, msg

    def __repr__(self):
        return ("{}({!r}, groups={!r}, length={!r}, should_match={!r})"
                .format(type(self), self.string, self.groups, self.length,
                        self.should_match))


class TestCase(object):
    def __init__(self, node, *test_strings, **kwargs):
        if len(test_strings) == 0:
            raise ValueError("no test strings provided")

        wrap = kwargs.get("wrap", True)

        if wrap is True:
            # We generally want to match with ^<pattern>$, otherwise patterns
            # like this won't match the entire input, even though they could:
            # re.match("(/[a-z]+)*|([a-z]+)", "foo")  # 0 length match
            self.node = Sequence(Start(), node, End())
        else:
            self.node = node
        self.test_strings = [
            TestString(ts) if isinstance(ts, six.text_type) else ts
            for ts in test_strings
        ]

    def run(self):
        regex = self.node.compile()

        for test_string in self.test_strings:
            test_string.run(regex)

    def __repr__(self):
        test_strings = ""
        if self.test_strings:
            test_strings = ", " + ", ".join(
                repr(ts) for ts in self.test_strings)
        return "{}({!r}{})".format(type(self).__name__, self.node, test_strings)


tc = TestCase
ts = TestString


@pytest.mark.parametrize("test_case", [
    tc(Literal("foo"), ts("foo"), ~ts("afoo")),
    tc(Literal("".join(unichr(x) for x in range(256))),
       "".join(unichr(x) for x in range(256))),

    tc(OneOrMore(Literal("a")), ~ts(""), "a", "aa", "aaa", "aaaaaaaaaaaaaaa"),
    tc(ZeroOrMore(Literal("a")), "", "a", "aa", "aaa", "aaaaaaaaaaaaaa"),

    tc(Set("a", "d", "f"), "a", "d", "f", ~ts("b"), ~ts("e"), ~ts("g")),
    tc(Set("^"), "^", ~ts("a"), ~ts("")),
    tc(Set("]"), "]", ~ts("a"), ~ts("")),
    tc(Set("\\"), "\\", ~ts("a"), ~ts("")),

    tc(OneOrMore(Set(("a", "f"))), "abcdef", "fedcba", "aa", "fdf"),
    # Nested Sets
    tc(OneOrMore(Set(Set(("a", "f")))), "abcdef", "fedcba", "aa", "fdf"),

    tc(Choice(Literal("foo"), Literal("bar")), "foo", "bar", ~ts("foobar")),

    tc(Capture(Literal("foo")), ts("foo", groups=("foo",))),
    tc(Sequence(Capture(Literal("foo")), Literal(":"),
                Capture(Literal("bar"))),
       ts("foo:bar", groups=("foo", "bar"))),

    tc(Repeat(Literal("abc"), count=3), "abcabcabc", ~ts("abcabc"),
       ~ts("abcabcabcabc")),
    tc(Repeat(Literal("ab"), min=2, max=4), "abab", "ababab", "abababab",
       ~ts("ab"), ~ts("ababababab")),

    tc(Repeat(Literal("ab"), min=2, max=None), "abab", "ababab",
       "ababababab" * 100, ~ts("ab")),

    tc(Repeat(Literal("ab"), min=None, max=10), ~ts("ab" * 11),
       *["ab" * n for n in range(1, 11)]),

    tc(Sequence(Literal("foo"), Optional(Literal("bar")), Literal("baz")),
       "foobaz", "foobarbaz"),

    tc(Optional(Repeat(Literal("x"), min=2, max=4)), "", "xx", "xxx", "xxxx",
       ~ts("x"))
])
def test_regex_builder_node(test_case):
    test_case.run()
