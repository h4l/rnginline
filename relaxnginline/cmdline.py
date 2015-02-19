"""
Flatten a hierachy of RELAX NG schemas into a single schema by recursively
inlining <include>/<externalRef> elements.

usage: relaxnginline [options] (<rng-src> | --stdin) [<rng-output>]

options:
    <rng-src>
        Filesystem path or a URL of the .rng file to inline.

    <rng-output>
        Filesystem path to write the inlined schema to. If not provided, or is
        -, stdout is written to.

    --default-base-uri <URI>
        Override the default base URI, which is file:<current dir>. The
        schema's base URI (e.g. the location it was loaded from, or applicable
        xml:base attribute value) is resolved against the default base URI in
        order to produce an absolute base URI to resolve href attribute values
        against when fetching schemas referenced by <include>/<externalRef>
        elements. Note that <URI> must be a an absolute URI with a scheme, not
        a URI-reference.

    --no-libxml2-compat
        Don't apply a workaround to make the output compatible with versions of
        libxml2 affected by bug:
            https://bugzilla.gnome.org/show_bug.cgi?id=744146

    --stdin
        Read the schema from stdin instead of from a URL or path.

        Note that reading from stdin will result in the location of the schema
        being unknown to this program, so relative hrefs in the schema will
        be resolved relative to the current directory, rather than the schema's
        location. This is usually not what you want, hence this option being
        explicitly required.

    --traceback
        Print the Python traceback on errors.

    --version
        Print the version and exit.

    --help, -h
        Show this help.
"""
from __future__ import unicode_literals, print_function

import sys
import locale

import docopt
import six
from lxml import etree

from relaxnginline import (__version__, inline, uri)
from relaxnginline.exceptions import ParseError, RelaxngInlineError


def py2_decode_bytes(cmdline_argument):
    # Python 2 provides command line args as bytes rather than text
    if six.PY2:
        assert isinstance(cmdline_argument, six.binary_type), (cmdline_argument, type(cmdline_argument))
        encoding = locale.getdefaultlocale()[1] or "ascii"
        return cmdline_argument.decode(encoding)

    assert isinstance(cmdline_argument, six.text_type)
    return cmdline_argument


def parse_stdin():
    stdin = sys.stdin.buffer if six.PY3 else sys.stdin
    try:
        xml = etree.parse(stdin, base_url=None)
    except etree.ParseError as cause:
            err = ParseError("Unable to parse <stdin> as XML. error: {0}"
                             .format(cause))
            six.raise_from(err, cause)
    assert xml.base is None
    return xml


def _main(args):
    if args["--stdin"]:
        src = parse_stdin()
    else:
        src = py2_decode_bytes(args["<rng-src>"])

    outfile = args["<rng-output>"]

    if outfile is None or outfile == "-":
        outfile = sys.stdin.buffer if six.PY3 else sys.stdout

    default_base_uri = None
    if args["--default-base-uri"]:
        default_base_uri = args["--default-base-uri"]
        # Need to validate this here, as it's considered a coding error to pass
        # an invalid URI to Inliner as default_base_uri, but this URI is
        # user-provided.
        if not uri.is_uri(default_base_uri):
            raise RelaxngInlineError(
                "The --default-base-uri provided is not a valid URI: {0}"
                .format(default_base_uri))

    postprocessors = None  # defaults
    if args["--no-libxml2-compat"]:
        postprocessors = []

    schema = inline(src, postprocessors=postprocessors, create_validator=False,
                    default_base_uri=default_base_uri)

    schema.getroottree().write(outfile)


def main():
    args = docopt.docopt(__doc__, version=__version__)
    try:
        _main(args)
    except RelaxngInlineError as e:
        print("fatal: {0}".format(e), file=sys.stderr)

        if args["--traceback"]:
            import traceback

            print("\n--traceback on, full traceback follows:\n",
                  file=sys.stderr)
            traceback.print_exc()

        sys.exit(1)


if __name__ == "__main__":
    main()
