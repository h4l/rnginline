"""
usage: relaxnginline [options] <rng-url> [<rng-output>]

options:

   --propagate-datatypelibrary -p    Propagate datatypeLibrary attributes to
                                     data and value elements. This can be used
                                     to work around a bug in libxml2: it
                                     doesn't find datatypeLibrary attributes on
                                     div elements.
"""
from __future__ import unicode_literals

import sys
import locale
from os.path import abspath

import docopt
import six
from six.moves.urllib import parse

from relaxnginline import (__version__, Inliner, escape_reserved_characters,
                           urlhandlers, postprocess)


def get_rng_url(args):
    url = args["<rng-url>"]

    if six.PY2:
        encoding = locale.getdefaultlocale()[1] or "ascii"
        url = url.decode(encoding)

    parsed = parse.urlparse(url)
    path_only_url = parse.ParseResult("", "", url, "", "", "")

    if path_only_url == parsed:
        # Looks like a filesystem path. Turn it into a file URL
        return urlhandlers.FilesystemUrlHandler.make_url(abspath(url))
    else:
        # Already a url, assume one of the handlers supports it
        return escape_reserved_characters(url)


def main():
    args = docopt.docopt(__doc__, version=__version__)

    rng_url = get_rng_url(args)
    outfile = args["<rng-output>"]

    if outfile is None or outfile == "-":
        if six.PY3:
            outfile = sys.stdout.buffer
        else:
            outfile = sys.stdout

    postprocessors = []
    if args["--propagate-datatypelibrary"]:
        postprocessors.append(postprocess.datatypelibrary)

    inliner = Inliner.with_default_handlers(postprocessors=postprocessors)
    grammar = inliner.load(rng_url)

    grammar.getroottree().write(outfile)


if __name__ == "__main__":
    main()
