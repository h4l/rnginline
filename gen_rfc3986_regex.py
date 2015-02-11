from __future__ import unicode_literals

import re

import six


@six.python_2_unicode_compatible
class Regex(object):
    def compile(self):
        return re.compile(self.render())

    def template(self, group=True):
        return "(?:{})" if group is True else "{}"

    def __str__(self):
        return self.render()


class BaseSequence(Regex):
    def __init__(self, *expressions):
        assert isinstance(expressions, tuple)
        assert all(isinstance(e, Regex) for e in expressions), expressions
        self.expressions = expressions

    def get_template(self, group):
        group = group is True and len(self.expressions) != 1
        return "(?:{})" if group is True else "{}"

    def get_operator(self):
        return ""

    def render_expression(self, e):
        return six.text_type(e)

    def render(self, group=True):
        expression = self.get_operator().join(
            self.render_expression(e) for e in self.expressions)
        return self.get_template(group).format(expression)


class Sequence(BaseSequence):
    pass


class Literal(BaseSequence):
    def __init__(self, text):
        self.expressions = text

    def render_expression(self, e):
        # Escape each character before inserting into the regex
        return re.escape(e)

    @classmethod
    def from_codepoint(cls, code_point):
        """
        Create a Literal matching the specified unicode code point. In
        interpreters using UTF-16 as their string representation (< 3.3)
        this will create (and match) surrogate pairs for code points above the
        BMP.
        """
        return cls("\\U{:08X}".format(code_point).decode("unicode_escape"))


class Choice(BaseSequence):
    def get_operator(self):
        return "|"


class Capture(Sequence):
    def render(self, group=True):
        return "({})".format(super(Capture, self).render(group=False))


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

    def render(self, group=False):
        contents = "".join(i.render() for i in self.ranges)
        return "[{}]".format(contents)


class SetRange(object):
    def __init__(self, start, end):
        if end < start:
            raise ValueError("end < start. start: {}, end: {}"
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
        raise ValueError("Don't know how to create a SetItem from: {!r}"
                         .format(item))


    @staticmethod
    def get_codepoint(item):
        if isinstance(item, int):
            return item
        return ord(item)

    def render(self):
        if self.start == self.end:
            return re.escape(six.unichr(self.start))
        else:
            return "{}-{}".format(re.escape(six.unichr(self.start)),
                                  re.escape(six.unichr(self.end)))

    def intersects(self, range):
        start, end = range
        ends_before = self.end < start
        starts_after = self.start > end
        return (not ends_before) and (not starts_after)


class UnaryOperator(Regex):
    def __init__(self, expression):
        assert isinstance(expression, Regex), expression
        self.expression = expression

    def render(self, group=False):
        return "{}{}".format(self.expression.render(), self.operator)


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
                min <= max or
                (min is None or max is None)), (min, max)

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
            return "{{{:d}}}".format(self.min)
        elif self.min is None:
            return "{{,{:d}}}".format(self.max)
        elif self.max is None:
            return "{{{:d},}}".format(self.min)
        else:
            return "{{{:d},{:d}}}".format(self.min, self.max)


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

    def render(self, group=False):
        return self.representation


class Start(StandAlone):
    representation = "^"


class End(StandAlone):
    representation = "$"


#    URI           = scheme ":" hier-part [ "?" query ] [ "#" fragment ]
uri = lambda: Sequence(scheme(), Literal(":"), hier_part(),
                       Optional(Sequence(Literal("?"), query())),
                       Optional(Sequence(Literal("#"), fragment())))

#    hier-part     = "//" authority path-abempty
#                  / path-absolute
#                  / path-rootless
#                  / path-empty
hier_part = lambda: Choice(
    Sequence(Literal("//"), authority(), path_abempty()),
    path_absolute(),
    path_rootless(),
    path_empty()
)

#    URI-reference = URI / relative-ref
uri_reference = lambda: Choice(uri(), relative_ref())

#    absolute-URI  = scheme ":" hier-part [ "?" query ]
absolute_uri = lambda: Sequence(scheme(), Literal(":"), hier_part(),
                                Optional(Literal("?", query)))

#    relative-ref  = relative-part [ "?" query ] [ "#" fragment ]
relative_ref = lambda: Sequence(relative_part(),
                                Optional(Sequence(Literal("?"), query())),
                                Optional(Sequence(Literal("#"), fragment()))
)

#    relative-part = "//" authority path-abempty
#                  / path-absolute
#                  / path-noscheme
#                  / path-empty
relative_part = lambda: Choice(
    Sequence(Literal("//"), authority(), path_abempty()),
    path_absolute(),
    path_noscheme(),
    path_empty()
)

#    scheme        = ALPHA *( ALPHA / DIGIT / "+" / "-" / "." )
scheme = lambda: Sequence(ALPHA(),
                          ZeroOrMore(Set(ALPHA(), DIGIT(), *list("+-."))))

#    authority     = [ userinfo "@" ] host [ ":" port ]
authority = lambda: Sequence(Optional(Sequence(userinfo(), Literal("@"))),
                             host(),
                             Optional(Sequence(Literal(":"), port())))

#    userinfo      = *( unreserved / pct-encoded / sub-delims / ":" )
userinfo = lambda: ZeroOrMore(Choice(pct_encoded(),
                                     Set(unreserved(), sub_delims(), ":")))

#    host          = IP-literal / IPv4address / reg-name
host = lambda: Choice(ip_literal(), ipv4address(), reg_name())

#    port          = *DIGIT
port = lambda: ZeroOrMore(DIGIT())

#    IP-literal    = "[" ( IPv6address / IPvFuture  ) "]"
ip_literal = lambda: Sequence(Literal("["),
                              Choice(ipv6address(), ipvfuture()),
                              Literal("]"))

#    IPvFuture     = "v" 1*HEXDIG "." 1*( unreserved / sub-delims / ":" )
ipvfuture = lambda: Sequence(Literal("v"), OneOrMore(HEXDIG()), Literal("."),
                             OneOrMore(Set(unreserved(), sub_delims(), ":")))

#    IPv6address   =                            6( h16 ":" ) ls32
#                  /                       "::" 5( h16 ":" ) ls32
#                  / [               h16 ] "::" 4( h16 ":" ) ls32
#                  / [ *1( h16 ":" ) h16 ] "::" 3( h16 ":" ) ls32
#                  / [ *2( h16 ":" ) h16 ] "::" 2( h16 ":" ) ls32
#                  / [ *3( h16 ":" ) h16 ] "::"    h16 ":"   ls32
#                  / [ *4( h16 ":" ) h16 ] "::"              ls32
#                  / [ *5( h16 ":" ) h16 ] "::"              h16
#                  / [ *6( h16 ":" ) h16 ] "::"
ipv6address = lambda: Choice(
    Sequence(Repeat(Sequence(h16(), Literal(":")), count=6), ls32()),

    Sequence(Literal("::"),
             Repeat(Sequence(h16(), Literal(":")), count=5), ls32()),

    Sequence(Optional(h16()),
             Literal("::"),
             Repeat(Sequence(h16(), Literal(":")), count=4), ls32()),

    Sequence(Optional(Sequence(Repeat(Sequence(h16(), Literal(":")), max=1), h16())),
             Literal("::"),
             Repeat(Sequence(h16(), Literal(":")), count=3), ls32()),

    Sequence(Optional(Sequence(Repeat(Sequence(h16(), Literal(":")), max=2), h16())),
             Literal("::"),
             Repeat(Sequence(h16(), Literal(":")), count=2), ls32()),

    Sequence(Optional(Sequence(Repeat(Sequence(h16(), Literal(":")), max=3), h16())),
             Literal("::"), h16(), Literal(":"), ls32()),

    Sequence(Optional(Sequence(Repeat(Sequence(h16(), Literal(":")), max=4), h16())),
             Literal("::"), ls32()),

    Sequence(Optional(Sequence(Repeat(Sequence(h16(), Literal(":")), max=5), h16())),
             Literal("::"), h16()),

    Sequence(Optional(Sequence(Repeat(Sequence(h16(), Literal(":")), max=6), h16())),
             Literal("::")),
)

#
#    h16           = 1*4HEXDIG
h16 = lambda: Repeat(HEXDIG(), min=1, max=4)

#    ls32          = ( h16 ":" h16 ) / IPv4address
ls32 = lambda: Choice(Sequence(h16(), Literal(":"), h16()), ipv4address())

#    IPv4address   = dec-octet "." dec-octet "." dec-octet "." dec-octet
ipv4address = lambda: Sequence(dec_octet(), Literal("."),
                               dec_octet(), Literal("."),
                               dec_octet(), Literal("."), dec_octet())

#
#    dec-octet     = DIGIT                 ; 0-9
#                  / %x31-39 DIGIT         ; 10-99
#                  / "1" 2DIGIT            ; 100-199
#                  / "2" %x30-34 DIGIT     ; 200-249
#                  / "25" %x30-35          ; 250-255
dec_octet = lambda: Choice(
    DIGIT(),
    Sequence(Set((0x31, 0x39)), DIGIT()),
    Sequence(Literal("1"), Repeat(DIGIT(), count=2)),
    Sequence(Literal("2"), Set((0x30, 0x34)), DIGIT()),
    Sequence(Literal("25"), Set((0x30, 0x35)))
)

#    reg-name      = *( unreserved / pct-encoded / sub-delims )
reg_name = lambda: ZeroOrMore(Choice(pct_encoded(),
                                     Set(unreserved(), sub_delims())))

#    path          = path-abempty    ; begins with "/" or is empty
#                  / path-absolute   ; begins with "/" but not "//"
#                  / path-noscheme   ; begins with a non-colon segment
#                  / path-rootless   ; begins with a segment
#                  / path-empty      ; zero characters
path = lambda: Choice(path_abempty(),
                      path_absolute(),
                      path_noscheme(),
                      path_rootless(),
                      path_empty())

#    path-abempty  = *( "/" segment )
path_abempty = lambda: _zom_segments()

#    path-absolute = "/" [ segment-nz *( "/" segment ) ]
path_absolute = lambda: Sequence(
    Literal("/"), Optional(Sequence(segment_nz(), _zom_segments())))

#    path-noscheme = segment-nz-nc *( "/" segment )
path_noscheme = lambda: Sequence(segment_nz_nc(), _zom_segments())

#    path-rootless = segment-nz *( "/" segment )
path_rootless = lambda: Sequence(segment_nz(), _zom_segments())

_zom_segments = lambda: ZeroOrMore(Sequence(Literal("/"), segment()))

#    path-empty    = 0<pchar>
path_empty = lambda: Literal("")

#    segment       = *pchar
segment = lambda: ZeroOrMore(pchar())

#    segment-nz    = 1*pchar
segment_nz = lambda: OneOrMore(pchar())

#    segment-nz-nc = 1*( unreserved / pct-encoded / sub-delims / "@" )
#                  ; non-zero-length segment without any colon ":"
segment_nz_nc = lambda: OneOrMore(Choice(pct_encoded(),
                                         Set(unreserved(), sub_delims(), "@")))

#    pchar         = unreserved / pct-encoded / sub-delims / ":" / "@"
pchar = lambda: Choice(pct_encoded(), Set(unreserved(), sub_delims(), *list(":@")))

#    query         = *( pchar / "/" / "?" )
query = lambda: ZeroOrMore(Choice(pchar(), Set(*list("/?"))))

#    fragment      = *( pchar / "/" / "?" )
fragment = query

#    pct-encoded   = "%" HEXDIG HEXDIG
pct_encoded = lambda: Sequence(Literal("%"), Repeat(HEXDIG(), count=2))

#    unreserved    = ALPHA / DIGIT / "-" / "." / "_" / "~"
unreserved = lambda: Set(ALPHA(), DIGIT(), *list("-._~"))

#    reserved      = gen-delims / sub-delims
reserved = lambda: Set(gen_delims(), sub_delims())

#    gen-delims    = ":" / "/" / "?" / "#" / "[" / "]" / "@"
gen_delims = lambda: Set(*list(":/?#[]@"))

#    sub-delims    = "!" / "$" / "&" / "'" / "(" / ")"
#                  / "*" / "+" / "," / ";" / "="
sub_delims = lambda: Set(*list("!$&'()*+,;="))

sub_delims = lambda: Set(*list("!$&'()*+,;="))

HEXDIG = lambda: Set(("a", "f"), ("A", "F"), DIGIT())
ALPHA = lambda: Set(("a", "f"), ("A", "F"))
DIGIT = lambda: Set(("0", "9"))


def main():
    print("URI regex:")
    print(uri_reference().render())


if __name__ == "__main__":
    main()
