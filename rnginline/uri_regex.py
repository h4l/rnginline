"""
This module provides regular expressions matching the ABNF rules for URIs
specified in Appendix A of rfc 3986:

    https://tools.ietf.org/html/rfc3986#appendix-A
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Mapping

from typing_extensions import Literal as TypingLiteral

from rnginline.regexbuilder import (
    Choice,
    End,
    Literal,
    OneOrMore,
    Optional,
    Regex,
    Repeat,
    Sequence,
    Set,
    Start,
    ZeroOrMore,
)

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

segment_nz_nc = OneOrMore(Choice(pct_encoded, Set(unreserved, sub_delims, "@")))

segment_nz = OneOrMore(pchar)

segment = ZeroOrMore(pchar)

path_empty = Literal("")

_zom_segments = ZeroOrMore(Sequence(Literal("/"), segment))

path_rootless = Sequence(segment_nz, _zom_segments)

path_noscheme = Sequence(segment_nz_nc, _zom_segments)

path_absolute = Sequence(Literal("/"), Optional(Sequence(segment_nz, _zom_segments)))

path_abempty = _zom_segments

path = Choice(path_abempty, path_absolute, path_noscheme, path_rootless, path_empty)

reg_name = ZeroOrMore(Choice(pct_encoded, Set(unreserved, sub_delims)))

dec_octet = Choice(
    DIGIT,
    Sequence(Set((0x31, 0x39)), DIGIT),
    Sequence(Literal("1"), Repeat(DIGIT, count=2)),
    Sequence(Literal("2"), Set((0x30, 0x34)), DIGIT),
    Sequence(Literal("25"), Set((0x30, 0x35))),
)

ipv4address = Sequence(
    dec_octet, Literal("."), dec_octet, Literal("."), dec_octet, Literal("."), dec_octet
)

h16 = Repeat(HEXDIG, min=1, max=4)

ls32 = Choice(Sequence(h16, Literal(":"), h16), ipv4address)

ipv6address = Choice(
    Sequence(Repeat(Sequence(h16, Literal(":")), count=6), ls32),
    Sequence(Literal("::"), Repeat(Sequence(h16, Literal(":")), count=5), ls32),
    Sequence(
        Optional(h16), Literal("::"), Repeat(Sequence(h16, Literal(":")), count=4), ls32
    ),
    Sequence(
        Optional(Sequence(Repeat(Sequence(h16, Literal(":")), max=1), h16)),
        Literal("::"),
        Repeat(Sequence(h16, Literal(":")), count=3),
        ls32,
    ),
    Sequence(
        Optional(Sequence(Repeat(Sequence(h16, Literal(":")), max=2), h16)),
        Literal("::"),
        Repeat(Sequence(h16, Literal(":")), count=2),
        ls32,
    ),
    Sequence(
        Optional(Sequence(Repeat(Sequence(h16, Literal(":")), max=3), h16)),
        Literal("::"),
        h16,
        Literal(":"),
        ls32,
    ),
    Sequence(
        Optional(Sequence(Repeat(Sequence(h16, Literal(":")), max=4), h16)),
        Literal("::"),
        ls32,
    ),
    Sequence(
        Optional(Sequence(Repeat(Sequence(h16, Literal(":")), max=5), h16)),
        Literal("::"),
        h16,
    ),
    Sequence(
        Optional(Sequence(Repeat(Sequence(h16, Literal(":")), max=6), h16)),
        Literal("::"),
    ),
)

ipvfuture = Sequence(
    Literal("v"),
    OneOrMore(HEXDIG),
    Literal("."),
    OneOrMore(Set(unreserved, sub_delims, ":")),
)

ip_literal = Sequence(Literal("["), Choice(ipv6address, ipvfuture), Literal("]"))

port = ZeroOrMore(DIGIT)

host = Choice(ip_literal, ipv4address, reg_name)

userinfo = ZeroOrMore(Choice(pct_encoded, Set(unreserved, sub_delims, ":")))

authority = Sequence(
    Optional(Sequence(userinfo, Literal("@"))),
    host,
    Optional(Sequence(Literal(":"), port)),
)

scheme = Sequence(ALPHA, ZeroOrMore(Set(ALPHA, DIGIT, *list("+-."))))

relative_part = Choice(
    Sequence(Literal("//"), authority, path_abempty),
    path_absolute,
    path_noscheme,
    path_empty,
)

relative_ref = Sequence(
    relative_part,
    Optional(Sequence(Literal("?"), query)),
    Optional(Sequence(Literal("#"), fragment)),
)

hier_part = Choice(
    Sequence(Literal("//"), authority, path_abempty),
    path_absolute,
    path_rootless,
    path_empty,
)

absolute_uri = Sequence(
    scheme, Literal(":"), hier_part, Optional(Sequence(Literal("?"), query))
)

uri = Sequence(
    scheme,
    Literal(":"),
    hier_part,
    Optional(Sequence(Literal("?"), query)),
    Optional(Sequence(Literal("#"), fragment)),
)

uri_reference = Choice(uri, relative_ref)

RfcName = TypingLiteral[
    "URI",
    "hier-part",
    "URI-reference",
    "absolute-URI",
    "relative-ref",
    "relative-part",
    "scheme",
    "authority",
    "userinfo",
    "host",
    "port",
    "IP-literal",
    "IPvFuture",
    "IPv6address",
    "h16",
    "ls32",
    "IPv4address",
    "dec-octet",
    "reg-name",
    "path",
    "path-abempty",
    "path-absolute",
    "path-noscheme",
    "path-rootless",
    "path-empty",
    "segment",
    "segment-nz",
    "segment-nz-nc",
    "pchar",
    "query",
    "fragment",
    "pct-encoded",
    "unreserved",
    "reserved",
    "gen-delims",
    "sub-delims",
    "HEXDIG",
    "ALPHA",
    "DIGIT",
]

_rfc_names: Mapping[RfcName, Regex] = {
    "URI": uri,
    "hier-part": hier_part,
    "URI-reference": uri_reference,
    "absolute-URI": absolute_uri,
    "relative-ref": relative_ref,
    "relative-part": relative_part,
    "scheme": scheme,
    "authority": authority,
    "userinfo": userinfo,
    "host": host,
    "port": port,
    "IP-literal": ip_literal,
    "IPvFuture": ipvfuture,
    "IPv6address": ipv6address,
    "h16": h16,
    "ls32": ls32,
    "IPv4address": ipv4address,
    "dec-octet": dec_octet,
    "reg-name": reg_name,
    "path": path,
    "path-abempty": path_abempty,
    "path-absolute": path_absolute,
    "path-noscheme": path_noscheme,
    "path-rootless": path_rootless,
    "path-empty": path_empty,
    "segment": segment,
    "segment-nz": segment_nz,
    "segment-nz-nc": segment_nz_nc,
    "pchar": pchar,
    "query": query,
    "fragment": fragment,
    "pct-encoded": pct_encoded,
    "unreserved": unreserved,
    "reserved": reserved,
    "gen-delims": gen_delims,
    "sub-delims": sub_delims,
    "HEXDIG": HEXDIG,
    "ALPHA": ALPHA,
    "DIGIT": DIGIT,
}


@lru_cache(maxsize=len(_rfc_names))
def get_regex(rule_name: RfcName) -> re.Pattern[str]:
    """
    Get a compiled regex which matches an entire string against the named rule
    from RFC 3986.
    """
    if rule_name not in _rfc_names:
        raise ValueError("Unknown rule name: {0}".format(rule_name))
    rule = _rfc_names[rule_name]
    # Need to place the rule between ^ and $ anchors, as the rules can't
    # include them by default.
    wrapped = Sequence(Start(), rule, End())
    return wrapped.compile()


__all__ = ["get_regex"] + (
    [n for (n, v) in locals().items() if not n.startswith("_") and isinstance(v, Regex)]
)
