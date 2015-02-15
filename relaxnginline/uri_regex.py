"""
This module provides regular expressions matching the ABNF rules for URIs
specified in Appendix A of rfc 3986:

    https://tools.ietf.org/html/rfc3986#appendix-A
"""
from __future__ import unicode_literals

from relaxnginline.regexbuilder import (Set, Sequence, Literal, Optional,
                                        Choice, ZeroOrMore, OneOrMore, Repeat,
                                        Regex, Start, End)

# The rules here are named according to those in RFC 3986, but transformed to
# make them valid Python identifiers. Mixed case rules are lower cased and,
# hyphens are replaced with underscores.

ALPHA = Set(("a", "z"), ("A", "Z"))
DIGIT = Set(("0", "9"))
HEXDIG = Set(("a", "f"), ("A", "F"), DIGIT)

sub_delims = Set(*list("!$&'()*+,;="))

gen_delims = Set(*list(":/?#[]@"))

reserved = Set(gen_delims, sub_delims)

unreserved = Set(ALPHA, DIGIT, *list("-._~"))

pct_encoded = Sequence(Literal("%"), Repeat(HEXDIG, count=2))

pchar = Choice(pct_encoded, Set(unreserved, sub_delims, *list(":@")))

query = ZeroOrMore(Choice(pchar, Set(*list("/?"))))

fragment = query

segment_nz_nc = OneOrMore(Choice(pct_encoded,
                                 Set(unreserved, sub_delims, "@")))

segment_nz = OneOrMore(pchar)

segment = ZeroOrMore(pchar)

path_empty = Literal("")

_zom_segments = ZeroOrMore(Sequence(Literal("/"), segment))

path_rootless = Sequence(segment_nz, _zom_segments)

path_noscheme = Sequence(segment_nz_nc, _zom_segments)

path_absolute = Sequence(
    Literal("/"), Optional(Sequence(segment_nz, _zom_segments)))

path_abempty = _zom_segments

path = Choice(path_abempty,
              path_absolute,
              path_noscheme,
              path_rootless,
              path_empty)

reg_name = ZeroOrMore(Choice(pct_encoded, Set(unreserved, sub_delims)))

dec_octet = Choice(
    DIGIT,
    Sequence(Set((0x31, 0x39)), DIGIT),
    Sequence(Literal("1"), Repeat(DIGIT, count=2)),
    Sequence(Literal("2"), Set((0x30, 0x34)), DIGIT),
    Sequence(Literal("25"), Set((0x30, 0x35))))

ipv4address = Sequence(dec_octet, Literal("."),
                       dec_octet, Literal("."),
                       dec_octet, Literal("."), dec_octet)

h16 = Repeat(HEXDIG, min=1, max=4)

ls32 = Choice(Sequence(h16, Literal(":"), h16), ipv4address)

ipv6address = Choice(
    Sequence(Repeat(Sequence(h16, Literal(":")), count=6), ls32),

    Sequence(Literal("::"),
             Repeat(Sequence(h16, Literal(":")), count=5), ls32),

    Sequence(Optional(h16),
             Literal("::"),
             Repeat(Sequence(h16, Literal(":")), count=4), ls32),

    Sequence(Optional(Sequence(Repeat(Sequence(h16, Literal(":")),
                                      max=1), h16)),
             Literal("::"),
             Repeat(Sequence(h16, Literal(":")), count=3), ls32),

    Sequence(Optional(Sequence(Repeat(Sequence(h16, Literal(":")),
                                      max=2), h16)),
             Literal("::"),
             Repeat(Sequence(h16, Literal(":")), count=2), ls32),

    Sequence(Optional(Sequence(Repeat(Sequence(h16, Literal(":")),
                                      max=3), h16)),
             Literal("::"), h16, Literal(":"), ls32),

    Sequence(Optional(Sequence(Repeat(Sequence(h16, Literal(":")),
                                      max=4), h16)),
             Literal("::"), ls32),

    Sequence(Optional(Sequence(Repeat(Sequence(h16, Literal(":")),
                                      max=5), h16)),
             Literal("::"), h16),

    Sequence(Optional(Sequence(Repeat(Sequence(h16, Literal(":")),
                                      max=6), h16)),
             Literal("::")),
)

ipvfuture = Sequence(Literal("v"), OneOrMore(HEXDIG), Literal("."),
                     OneOrMore(Set(unreserved, sub_delims, ":")))

ip_literal = Sequence(Literal("["),
                      Choice(ipv6address, ipvfuture),
                      Literal("]"))

port = ZeroOrMore(DIGIT)

host = Choice(ip_literal, ipv4address, reg_name)

userinfo = ZeroOrMore(Choice(pct_encoded,
                      Set(unreserved, sub_delims, ":")))

authority = Sequence(Optional(Sequence(userinfo, Literal("@"))),
                     host,
                     Optional(Sequence(Literal(":"), port)))

scheme = Sequence(ALPHA,
                  ZeroOrMore(Set(ALPHA, DIGIT, *list("+-."))))

relative_part = Choice(
    Sequence(Literal("//"), authority, path_abempty),
    path_absolute,
    path_noscheme,
    path_empty
)

relative_ref = Sequence(relative_part,
                        Optional(Sequence(Literal("?"), query)),
                        Optional(Sequence(Literal("#"), fragment))
)

hier_part = Choice(
    Sequence(Literal("//"), authority, path_abempty),
    path_absolute,
    path_rootless,
    path_empty
)

absolute_uri = Sequence(scheme, Literal(":"), hier_part,
                        Optional(Sequence(Literal("?"), query)))

uri = Sequence(scheme, Literal(":"), hier_part,
               Optional(Sequence(Literal("?"), query)),
               Optional(Sequence(Literal("#"), fragment)))

uri_reference = Choice(uri, relative_ref)
