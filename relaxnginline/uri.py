from __future__ import unicode_literals

from six.moves.urllib.parse import urlsplit, SplitResult


def resolve(base, reference, strict=True):
    """
    Resolve a reference URI against a base URI to form a target URI.

    Implements relative URI resolution according to RFC 3986 section 5.2.
    "Relative Resolution".

    Note that urllib.urljoin does not work with non-standard schemes (like our
    pypkgdata: scheme) hence this implementation...
    """
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

    return _recombine(SplitResult(scheme, authority, path, query, fragment))


def _merge(base, ref_path):
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


def _remove_dot_segments(path):
    """
    Remove . and .. segments from path.

    Implements 5.2.4. Remove Dot Segments.
    """
    input = path
    output = []

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


def _recombine(spliturl):
    """
    Combine a SplitResult into a URI string.

    Implements section 5.3 Component Recomposition.
    """
    out = []

    if spliturl.scheme:
        out.append(spliturl.scheme)
        out.append(":")

    if spliturl.netloc:
        out.append("//")
        out.append(spliturl.netloc)

    out.append(spliturl.path)

    if spliturl.query:
        out.append("?")
        out.append(spliturl.query)

    if spliturl.fragment:
        out.append("#")
        out.append(spliturl.fragment)

    return "".join(out)
