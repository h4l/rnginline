from __future__ import unicode_literals

from relaxnginline.regexbuilder import (Set, Sequence, Literal, Optional,
                                        Choice, ZeroOrMore, OneOrMore, Repeat)


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


HEXDIG = lambda: Set(("a", "f"), ("A", "F"), DIGIT())
ALPHA = lambda: Set(("a", "z"), ("A", "Z"))
DIGIT = lambda: Set(("0", "9"))
