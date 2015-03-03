from __future__ import unicode_literals

from copy import copy

import pytest
import six

from rnginline.regexbuilder import (Literal, Set, OneOrMore, ZeroOrMore,
                                    Choice, Capture, Sequence, Repeat,
                                    Optional, Start, End, SetRange, Whitespace)


class _TestString(object):
    def __init__(self, string, groups=None, groupdict=None, length=None,
                 should_match=True):
        self.string = string
        self.groups = groups
        self.groupdict = groupdict
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
            if self.groupdict is not None:
                assert match.groupdict() == self.groupdict, msg
        else:
            assert not match or match.end() != length, msg

    def __repr__(self):
        return ("{0}({1!r}, groups={2!r}, length={3!r}, should_match={4!r})"
                .format(type(self), self.string, self.groups, self.length,
                        self.should_match))


class _TestCase(object):
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
            _TestString(ts) if isinstance(ts, six.text_type) else ts
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
        return "{0}({1!r}{2})".format(
            type(self).__name__, self.node, test_strings)


tc = _TestCase
ts = _TestString


@pytest.mark.parametrize("test_case", [
    tc(Literal("foo"), ts("foo"), ~ts("afoo")),
    tc(Literal("".join(six.unichr(x) for x in range(256))),
       "".join(six.unichr(x) for x in range(256))),
    tc(Literal.from_codepoint(0x10155), ts("\U00010155")),
    tc(Literal.from_codepoint(ord("x")), ts("x")),

    tc(OneOrMore(Literal("a")), ~ts(""), "a", "aa", "aaa", "aaaaaaaaaaaaaaa"),
    tc(ZeroOrMore(Literal("a")), "", "a", "aa", "aaa", "aaaaaaaaaaaaaa"),

    tc(Set("a", "d", "f"), "a", "d", "f", ~ts("b"), ~ts("e"), ~ts("g")),
    tc(Set("^"), "^", ~ts("a"), ~ts("")),
    tc(Set("]"), "]", ~ts("a"), ~ts("")),
    tc(Set("\\"), "\\", ~ts("a"), ~ts("")),
    tc(Set(SetRange.create(SetRange.create(ord("x")))), "x"),

    tc(OneOrMore(Set(("a", "f"))), "abcdef", "fedcba", "aa", "fdf"),
    # Nested Sets
    tc(OneOrMore(Set(Set(("a", "f")))), "abcdef", "fedcba", "aa", "fdf"),

    tc(Choice(Literal("foo"), Literal("bar")), "foo", "bar", ~ts("foobar")),

    tc(Capture(Literal("foo")), ts("foo", groups=("foo",))),
    tc(Optional(Capture(Literal("foo"))),
       ts("foo", groups=("foo",)), ts("", groups=(None,))),
    tc(Sequence(Capture(Literal("foo")), Literal(":"),
                Capture(Literal("bar"))),
       ts("foo:bar", groups=("foo", "bar"))),
    tc(Choice(Capture(Literal("foo")), Capture(Literal("bar"))),
       ts("foo", groups=("foo", None)), ts("bar", groups=(None, "bar"))),

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
       ~ts("x")),

    tc(Sequence(
        Capture(OneOrMore(Set("a")), name="foo"),
        Capture(OneOrMore(Set("b")), name="bar")),
       ts("aaaabb", groupdict=dict(foo="aaaa", bar="bb"))),

    tc(ZeroOrMore(Whitespace()),
       "", "  ", "\t\t  \t")

])
def test_regex_builder_node(test_case):
    test_case.run()


def test_capture_name_must_by_python_name():
    with pytest.raises(ValueError):
        Capture(Literal("lol"), name="foo-bar")  # hyphen not allowed in names


def test_capture_rejects_unknown_kwargs():
    with pytest.raises(ValueError):
        Capture(Literal("lol"), foo="bar")  # unrecognised keyword arg


def test_set_cannot_be_empty():
    with pytest.raises(ValueError):
        Set()


def test_set_range_cannot_be_reversed():
    with pytest.raises(ValueError):
        SetRange(20, 10)


def test_set_range_create_rejects_unknown_args():
    with pytest.raises(ValueError):
        SetRange.create([1, 2, 3])


@pytest.mark.parametrize("a,b,intersects", [
    (SetRange(3, 3), SetRange(3, 3), True),
    (SetRange(3, 3), SetRange(4, 4), False),

    (SetRange(100, 110), SetRange(110, 120), True),
    (SetRange(110, 120), SetRange(100, 110), True),

    (SetRange(50, 100), SetRange(40, 60), True),
    (SetRange(40, 60), SetRange(50, 100), True),

    (SetRange(70, 80), SetRange(50, 100), True),
    (SetRange(50, 100), SetRange(70, 80), True)
])
def test_set_range_intersects(a, b, intersects):
    assert a.intersects(b) == intersects


def test_repr():
    expr = Choice(Literal("foo"), Repeat(Literal("bar"), min=3, max=8))
    assert "Choice" in repr(expr)
    assert "foo|(?:bar){3,8}" in repr(expr)
