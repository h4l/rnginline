"""
This module contains URI related functions, implemented according to
`RFC 3986`_.

.. _RFC 3986: https://tools.ietf.org/html/rfc3986
"""
from __future__ import annotations

from typing import Union
from urllib.parse import SplitResult, urlsplit

from rnginline import uri_regex

__all__ = ["UriSyntaxError", "is_uri", "is_uri_reference", "resolve", "recombine"]

SplitResultInput = Union[
    SplitResult, "tuple[str | None, str | None, str | None, str | None, str | None]"
]


class UriSyntaxError(ValueError):
    pass


def is_uri(text: str) -> bool:
    """
    Checks if text matches the "URI" grammar rule from RFC 3986.

    Note the URI rule is LESS general than URI-reference - it requires an
    absolute URI with a scheme.
    """
    return _matches_uri_pattern_rule("URI", text)


def is_uri_reference(text: str) -> bool:
    """
    Checks if text matches the "URI-reference" grammar rule from RFC 3986.

    Note that the URI-reference rule is MORE general than URI - it can be
    a relative path by itself or an absolute URI with scheme.
    """
    return _matches_uri_pattern_rule("URI-reference", text)


def _matches_uri_pattern_rule(rule: uri_regex.RfcName, text: str) -> bool:
    return bool(uri_regex.get_regex(rule).match(text))


def resolve(base: str, reference: str, strict: bool = True) -> str:
    """
    Resolve a reference URI against a base URI to form a target URI.

    Implements relative URI resolution according to RFC 3986 section 5.2.
    "Relative Resolution".

    Note that urllib.urljoin does not work with non-standard schemes (like our
    pydata: scheme) hence this implementation...
    """
    if not is_uri(base):
        raise UriSyntaxError("base was not a valid URI: {0}".format(base))
    if not is_uri_reference(reference):
        raise UriSyntaxError(
            "reference was not a valid URI-reference: {0}".format(reference)
        )

    b, ref = urlsplit(base), urlsplit(reference)

    scheme, authority, path, query, fragment = None, None, None, None, None

    if not strict and ref.scheme == b.scheme:
        ref = SplitResult("", *ref[1:])

    if ref.scheme:
        scheme = ref.scheme
        authority = ref.netloc
        path = _remove_dot_segments(ref.path)
        query = ref.query
    else:
        if ref.netloc:
            authority = ref.netloc
            path = _remove_dot_segments(ref.path)
            query = ref.query
        else:
            if ref.path == "":
                path = b.path
                if ref.query:
                    query = ref.query
                else:
                    query = b.query
            else:
                if ref.path.startswith("/"):
                    path = _remove_dot_segments(ref.path)
                else:
                    path = _remove_dot_segments(_merge(b, ref.path))
                query = ref.query
            authority = b.netloc
        scheme = b.scheme
    fragment = ref.fragment

    return recombine(SplitResult(scheme, authority, path, query, fragment))


def _merge(base: SplitResult, ref_path: str) -> str:
    """
    Resolve ref_path against the base path.

    Implements 5.2.3. Merge Paths.
    """
    if base.netloc and not base.path:
        assert not ref_path.startswith("/")
        return "/" + ref_path
    base_parts = base.path.split("/")
    if len(base_parts) == 1:
        return ref_path
    return "/".join(base_parts[:-1] + ref_path.split("/"))


def _remove_dot_segments(path: str) -> str:
    """
    Remove . and .. segments from path.

    Implements 5.2.4. Remove Dot Segments.
    """
    input = path
    output: list[str] = []

    while input:
        # A
        if input.startswith("./"):
            input = input[2:]
        elif input.startswith("../"):
            input = input[3:]
        # B
        elif input.startswith("/./"):
            input = input[2:]
        elif input == "/.":
            input = "/"
        # C
        elif input.startswith("/../"):
            input = input[3:]
            if output:
                output.pop()
        elif input == "/..":
            input = "/"
            if output:
                output.pop()
        elif input == "." or input == "..":
            input = ""
        else:
            start = 1 if input.startswith("/") else 0
            i = input.find("/", start)
            if i > -1:
                output.append(input[:i])
                input = input[i:]
            else:
                output += input
                input = ""

    return "".join(output)


def recombine(spliturl: SplitResultInput) -> str:
    """
    Combine a SplitResult into a URI string.

    Implements section 5.3 Component Recomposition.
    """
    scheme, netloc, path, query, fragment = spliturl
    out = []

    # Refuse to construct a broken URI-reference
    if netloc and path and not path.startswith("/"):
        raise UriSyntaxError(
            "With a netloc present the path must be absolute or empty. "
            "path: {0}".format(path)
        )

    if scheme:
        out.append(scheme)
        out.append(":")

    if netloc:
        out.append("//")
        out.append(netloc)

    out.append(path or "")

    if query:
        out.append("?")
        out.append(query)

    if fragment:
        out.append("#")
        out.append(fragment)

    return "".join(out)
