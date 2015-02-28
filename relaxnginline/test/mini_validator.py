"""
A very simple program to check if an XML file matches a RELAX NG schema.

usage: mini_validator <rngfile> <xmlfile>
"""
from __future__ import unicode_literals, print_function

import sys

import docopt
from lxml import etree


def main(argv=None):
    try:
        validate(argv)
    except Exception as e:
        print("fatal: {0}".format(e))
        sys.exit(1)


def validate(argv):
    options = docopt.docopt(__doc__, argv=argv)

    xml = etree.parse(options["<xmlfile>"])
    validator = etree.RelaxNG(etree.parse(options["<rngfile>"]))

    if not validator(xml):
        sys.exit(2)


if __name__ == "__main__":
    main()
