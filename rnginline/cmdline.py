from __future__ import annotations

import sys
from typing import BinaryIO, Sequence, Union, cast

import docopt
from typing_extensions import TypedDict

from rnginline import __version__, inline, uri
from rnginline.exceptions import RelaxngInlineError
from rnginline.postprocess import PostProcessor

# - Assign doc to DOC to keep it if python -OO is used (which strips docstrings)
# - We format spaces into blank lines to work around a bug in docopt-ng's usage
#   parser.
USAGE = """\
usage: rnginline [options] <rng-src> [<rng-output>]
       rnginline [options] --stdin [<rng-output>]
       rnginline --help\
"""

__doc__ = DOC = f"""
Flatten a hierachy of RELAX NG schemas into a single schema by recursively
inlining <include>/<externalRef> elements.

{USAGE}

options:
    <rng-src>
        Filesystem path or a URL of the .rng file to inline.
{" "}
    <rng-output>
        Filesystem path to write the inlined schema to. If not provided, or is
        -, stdout is written to.
{" "}
    --traceback
        Print the Python traceback on errors.
{" "}
    --no-libxml2-compat
        Don't apply a workaround to make the output compatible with versions of
        libxml2 affected by bug:
            https://bugzilla.gnome.org/show_bug.cgi?id=744146
{" "}
    --version
        Print the version and exit.
{" "}
    --help, -h
        Show this help.
{" "}
advanced options:
    --stdin
        Read the schema from stdin instead of from a URL or path.
{" "}
        Note that reading from stdin will result in the location of the schema
        being unknown to this program, so relative hrefs in the schema will
        be resolved relative to the current directory, rather than the schema's
        location. This is usually not what you want, hence this option being
        explicitly required. You should almost certainly use --base-uri along
        with this option.
{" "}
    --base-uri, -b <URI-reference>
        Replace the implicit URI of the input with the given URI. Only required
        when using stdin or something odd/advanced. Can be a relative URI.
{" "}
    --default-base-uri <URI>
        Override the default base URI, which is file:<current dir> (ending in
        a /). The schema's base URI (e.g. the location it was loaded from, or
        applicable xml:base attribute value) is resolved against the default
        base URI in order to produce an absolute base URI to resolve href
        attribute values against when fetching schemas referenced by
        <include>/<externalRef> elements. Note that <URI> must be a an absolute
        URI with a scheme, not a URI-reference.
"""

ParsedArgs = TypedDict(
    "ParsedArgs",
    {
        "<rng-src>": Union[str, None],
        "<rng-output>": Union[str, None],
        "--traceback": bool,
        "--no-libxml2-compat": bool,
        "--version": bool,
        "--help": bool,
        "-h": bool,
        "--stdin": bool,
        "--base-uri": Union[str, None],
        "--default-base-uri": Union[str, None],
    },
)


def _main(args: ParsedArgs) -> None:
    src: str | BinaryIO
    if args["--stdin"]:
        src = sys.stdin.buffer
    else:
        assert isinstance(args["<rng-src>"], str)
        src = args["<rng-src>"]

    outfile: str | BinaryIO
    outfile_name = args["<rng-output>"]

    if outfile_name is None or outfile_name == "-":
        outfile = sys.stdout.buffer
    else:
        outfile = outfile_name

    default_base_uri = None
    if args["--default-base-uri"]:
        default_base_uri = args["--default-base-uri"]
        # Need to validate this here, as it's considered a coding error to pass
        # an invalid URI to Inliner as default_base_uri, but this URI is
        # user-provided.
        if not uri.is_uri(default_base_uri):
            raise RelaxngInlineError(
                "The --default-base-uri provided is not a valid URI: "
                f"{default_base_uri}"
            )

    base_uri = None
    if args["--base-uri"]:
        base_uri = args["--base-uri"]

        if not uri.is_uri_reference(base_uri):
            raise RelaxngInlineError(
                "The --base-uri provided is not a valid " f"URI-reference: {base_uri}"
            )

    postprocessors: Sequence[PostProcessor] | None = None  # defaults
    if args["--no-libxml2-compat"]:
        postprocessors = []

    schema = inline(
        src,
        postprocessors=postprocessors,
        create_validator=False,
        base_uri=base_uri,
        default_base_uri=default_base_uri,
    )

    schema.getroottree().write(outfile)


def main(argv: list[str] | None = None) -> None:
    try:
        args = cast(ParsedArgs, docopt.docopt(DOC, version=__version__, argv=argv))
    except docopt.DocoptExit as e:
        if e.code:
            # docopt-ng produces confusing/nonsensical error messages when a
            # user provides incorrect CLI options. For example:
            # > Warning: found unmatched (duplicate?) arguments
            # > [Option(None, '--hesdfds', 0, True)]
            # To prevent this we catch docopt-ng's DocoptExit and print our own
            # error message.
            print(
                f"""\
rnginline couldn't understand the command line options it received. Run again \
with --help for more info.

{USAGE}
""",
                file=sys.stderr,
                end="",
            )
            raise SystemExit(1) from e
        raise e
    try:
        _main(args)
    except RelaxngInlineError as e:
        print(f"fatal: {e}", file=sys.stderr)

        if args["--traceback"]:
            import traceback

            print("\n--traceback on, full traceback follows:\n", file=sys.stderr)
            traceback.print_exc()

        sys.exit(1)


if __name__ == "__main__":
    main()
