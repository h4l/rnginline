from __future__ import unicode_literals

import re

import six


@six.python_2_unicode_compatible
class Regex(object):
    def compile(self):
        return re.compile(self.render())

    def is_singular(self):
        return False

    def is_expansive(self):
        """
        If this expression B was placed between expressions A and C,
        is_expansive() returns True if the meaning of A or C could be changed.
        """
        return False

    def render_singular(self):
        """
        Render this regex for placement in a context which requires a single
        expression rather than multiple expressions. e.g. in x? <x> must be
        a single expression as ? applies to a single expression.
        """
        rendered = self.render()
        if self.is_singular():
            return rendered
        # Wrap the expressions in an anonymous group to make 1 expression
        return "(?:{0})".format(rendered)

    def render_non_expansive(self):
        """
        Render this expression, allowing it not to be singular as long as it's
        not an expansive expression.
        """
        if self.is_expansive():
            return self.render_singular()
        return self.render()

    def __str__(self):
        return self.render()

    def __repr__(self):
        return "<{0} -> ur\"{1}\">".format(
            type(self).__name__,
            six.text_type(self).encode("raw_unicode_escape"))


class BaseSequence(Regex):
    def __init__(self, *expressions):
        assert isinstance(expressions, tuple)
        assert all(isinstance(e, Regex) for e in expressions), expressions
        self.expressions = expressions

    def is_singular(self):
        return len(self.expressions) == 1 and self.expressions[0].is_singular()

    def get_operator(self):
        return ""

    def render_expression(self, e):
        # In a sequence of expressions, each expression doesn't need to be
        # singular to maintain its semantics, but the expression can't affect
        # the semantics of its neighbors.
        return e.render_non_expansive()

    def render(self):
        return self.get_operator().join(
            self.render_expression(e) for e in self.expressions)


class Sequence(BaseSequence):
    pass


class Literal(Regex):
    _reserved_chars = set("\\.^$*+?{}[]|()")

    def __init__(self, text):
        self.text = text

    def is_singular(self):
        return len(self.text) == 1

    def needs_escape(self, char):
        return char in self._reserved_chars

    def render(self):
        return "".join(
            re.escape(char) if self.needs_escape(char) else char
            for char in self.text)

    @classmethod
    def from_codepoint(cls, code_point):
        """
        Create a Literal matching the specified unicode code point. In
        interpreters using UTF-16 as their string representation (< 3.3)
        this will create (and match) surrogate pairs for code points above the
        BMP.
        """
        return cls("\\U{0:08X}".format(code_point)
                   .encode("ascii").decode("unicode_escape"))


class Choice(BaseSequence):
    def get_operator(self):
        return "|"

    def is_expansive(self):
        # The choice operator is greedy, it includes as much as possible either
        # side, so if one is present in the expression, it's "expansive" (will
        # change the meaning of expressions next to it).
        return not self.is_singular()


class Capture(Sequence):
    def __init__(self, *expressions, **kwargs):
        """
        Create a capturing regex group, optionally with a name.
        Args:
            name: If provided, create a named group with this name.
        """
        super(Capture, self).__init__(*expressions)

        name = kwargs.pop("name", None)
        if name is not None and not is_name(name):
            raise ValueError("Invalid capture group name: {0}".format(name))
        self.name = name

        if kwargs:
            raise ValueError("Got unexpected kwargs: {0}".format(kwargs))

    def render(self):
        expressions = super(Capture, self).render()

        if self.name is not None:
            return "(?P<{0}>{1})".format(self.name, expressions)
        return "({0})".format(expressions)

    def is_singular(self):
        # A capture group always renders as a group, so it's always singular
        return True


class Set(Regex):
    def __init__(self, *items):
        if len(items) == 0:
            raise ValueError("empty Set()")
        self.ranges = [SetRange.create(i)
                       for i in items if not isinstance(i, Set)]
        # Merge sub set items
        self.ranges += [range
                        for set in items if isinstance(set, Set)
                        for range in set.ranges]

    def render(self):
        contents = "".join(i.render(pos == 0)
                           for pos, i in enumerate(self.ranges))
        return "[{0}]".format(contents)

    def is_singular(self):
        # Sets are always singular (1 expression)
        return True


class SetRange(object):
    def __init__(self, start, end):
        if end < start:
            raise ValueError("end < start. start: {0}, end: {1}"
                             .format(start, end))
        self.start = start
        self.end = end

    def is_single(self):
        return self.start == self.end

    @classmethod
    def create(cls, item):
        if isinstance(item, SetRange):
            return item
        if isinstance(item, (int, six.text_type)):
            codepoint = cls.get_codepoint(item)
            return SetRange(codepoint, codepoint)
        if len(item) == 2:
            start, end = item
            return SetRange(cls.get_codepoint(start), cls.get_codepoint(end))
        raise ValueError("Don't know how to create a SetItem from: {0!r}"
                         .format(item))

    @staticmethod
    def get_codepoint(item):
        if isinstance(item, int):
            return item
        return ord(item)

    def needs_escape(self, char, is_first):
        # The ^ must be escaped if it's the first char in the set
        return (is_first and char == "^") or char in "\\]-"

    def render_char(self, code_point, is_first):
        char = six.unichr(code_point)
        if self.needs_escape(char, is_first):
            return re.escape(char)
        return char

    def render(self, is_first):
        """
        Args:
            is_first: True if this is the first range in the set
        """
        if self.is_single():
            return self.render_char(self.start, is_first)
        else:
            return "{0}-{1}".format(self.render_char(self.start, is_first),
                                    self.render_char(self.end, False))

    def intersects(self, range):
        start, end = range.start, range.end
        ends_before = self.end < start
        starts_after = self.start > end
        return (not ends_before) and (not starts_after)


class UnaryOperator(Regex):
    def __init__(self, expression):
        assert isinstance(expression, Regex), expression
        self.expression = expression

    # Note that instances are not singular by default

    def render(self):
        # The subexpression must be singular
        return "{0}{1}".format(
            self.expression.render_singular(), self.operator)


class Repeat(UnaryOperator):
    def __init__(self, expression, min=None, max=None, count=None):
        super(Repeat, self).__init__(expression)

        if count is not None:
            assert min is None and max is None
            min = count
            max = count

        assert min is None or min >= 0
        assert max is None or max >= 0
        assert ((min is None and max is None) or
                (min is None or max is None) or
                min <= max), (min, max)

        self.min = min
        self.max = max

    @property
    def operator(self):
        if self.min is None and self.max is None:
            return "*"
        elif self.min == 1 and self.max is None:
            return "+"
        elif self.min == 0 and self.max == 1:
            return "?"
        elif self.min == self.max:
            return "{{{0:d}}}".format(self.min)
        elif self.min is None:
            return "{{,{0:d}}}".format(self.max)
        elif self.max is None:
            return "{{{0:d},}}".format(self.min)
        else:
            return "{{{0:d},{1:d}}}".format(self.min, self.max)


class ZeroOrMore(Repeat):
    def __init__(self, expresion):
        super(ZeroOrMore, self).__init__(expresion)


class OneOrMore(Repeat):
    def __init__(self, expresion):
        super(OneOrMore, self).__init__(expresion, min=1)


class Optional(Repeat):
    def __init__(self, expresion):
        super(Optional, self).__init__(expresion, min=0, max=1)


class StandAlone(Regex):
    """
    Base class for stand alone expressions like ^, $, \w, etc.
    """

    def render(self):
        return self.representation

    def is_singular(self):
        # These are always singular as they're stand alone expressions
        return True


class Start(StandAlone):
    representation = "^"


class End(StandAlone):
    representation = "$"


class Whitespace(StandAlone):
    representation = r"\s"


NAME = re.compile(r"^[a-zA-Z_]\w*$")


def is_name(string):
    """Returns: True if string is a Python name/identifier."""
    return bool(NAME.match(string))
