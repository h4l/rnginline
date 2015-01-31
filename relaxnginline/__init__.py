"""
usage: relaxnginline [options] <rng-url> [<rng-output>]

options:
import quote
"""
from __future__ import print_function, unicode_literals
import locale

import os
import re
from os.path import abspath
import sys
from functools import partial

from lxml import etree
import docopt
import six
from six.moves.urllib import parse

__version__ = "0.0.0"


RNG_NS = "http://relaxng.org/ns/structure/1.0"
NSMAP = {"rng": RNG_NS}
RNG_GRAMMAR_TAG = "{{{}}}grammar".format(RNG_NS)

# Section 5.4 of XLink specifies that chars other than these must be escaped
# in values of href attrs before using them as URIs:
NOT_ESCAPED = "".join(chr(x) for x in
                      # ASCII are OK
                      set(range(128))
                      # But not control chars
                      - set(range(0, 31))
                      # And not these reserved chars
                      - set(ord(c) for c in " <>\"{}|\\^`"))
# Matches chars which must be escaped in href attrs
NEEDS_ESCAPE_RE = re.compile("[^{}]".format(re.escape(NOT_ESCAPED)))


class RelaxngInlineError(BaseException):
    pass


class NoAvailableHandlerError(RelaxngInlineError):
    pass


class BadXmlError(RelaxngInlineError):
    pass


class ParseError(BadXmlError):
    pass


class InvalidGrammarError(BadXmlError):
    @classmethod
    def from_bad_element(cls, el, msg):
        return cls("{} on line {} {}"
                   .format(el.tag, el.sourceline or "??", msg))


class DereferenceError(RelaxngInlineError):
    pass


class FilesystemUrlHandler(object):
    def can_handle(self, url):
        return url.scheme == "file" or url.scheme == ""

    def dereference(self, url):
        assert self.can_handle(url)
        # Paths will always be absolute due to relative paths being resolved
        # against absolute paths.
        assert url.path.startswith("/")
        try:
            # The path is URL-encoded, so it needs decoding before we hit the
            # filesystem.
            path = parse.unquote(url.path)

            with open(url.path, "rb") as f:
                return f.read()
        except IOError as e:
            err = DereferenceError(
                "Unable to dereference file url: {}".format(url.geturl()))
            six.raise_from(err, e)


class Inliner(object):
    def __init__(self, handlers=None):
        if handlers is None:
            handlers = [FilesystemUrlHandler()]
        self.handlers = handlers

    def parse_url(self, url):
        if isinstance(url, parse.ParseResult):
            return url
        return parse.urlparse(url)

    def unparse_url(self, url):
        if isinstance(url, parse.ParseResult):
            return url.geturl()
        return url

    def get_handler(self,  url):
        parsed_url = self.parse_url(url)
        handlers = (h for h in self.handlers if h.can_handle(parsed_url))
        try:
            return next(handlers)
        except StopIteration:
            raise NoAvailableHandlerError(
                "No handler can handle url: {}".format(url))

    def resolve_url(self, base, url):
        return parse.urljoin(base, url)

    def dereference_url(self, url):
        parsed_url = self.parse_url(url)
        handler = self.get_handler(url)
        return self.parse_grammar_xml(handler.dereference(parsed_url), url)

    def parse_grammar_xml(self, xml_string, base_url):
        try:
            xml = etree.fromstring(xml_string, base_url=base_url)
        except etree.ParseError as e:
            err = ParseError("Unable to parse result of dereferencing url: {}"
                             .format(base_url))
            six.raise_from(err, e)

        # Ensure the parsed XML is a relaxng grammar
        if xml.tag != RNG_GRAMMAR_TAG:
            raise InvalidGrammarError(
                "Parsed RELAX NG does not start with a grammar element in the "
                "RELAX NG namespace. got: {}, expected: {}, from url: {}"
                .format(xml.tag, RNG_GRAMMAR_TAG, base_url))
        assert xml.base == base_url
        return xml

    def inline(self, element_or_url):
        """

        """
        if isinstance(element_or_url, six.text_type):
            return self.inline(self.dereference_url(element_or_url))

        # Assume we have an etree Element
        grammar = element_or_url
        if grammar.tag != RNG_GRAMMAR_TAG:
            raise InvalidGrammarError(
                "The root element of the provided XML is not a RELAX NG "
                "grammar element. got: {}, expected: {}"
                .format(grammar.tag, RNG_GRAMMAR_TAG))

        # Find include/externalRefs and (recursively) inline them
        grammar = self._inline_includes(grammar)
        grammar = self._inline_external_refs(grammar)

        return grammar

    def _inline_includes(self, grammar):
        includes = grammar.xpath("//rng:include", namespaces=NSMAP)

        for include in includes:
            self._inline_include(include)

        return grammar

    def _inline_include(self, include):
        print("inlining include: {!r} {}".format(include, self._get_href_url(include)))
        pass

    def _inline_external_refs(self, grammar):
        refs = grammar.xpath("//rng:externalRef", namespaces=NSMAP)

        for ref in refs:
            self._inline_external_ref(ref)

        return grammar

    def _inline_external_ref(self, ref):
        url = self._get_href_url(ref)

        # datatypeLibrary: The datatypeLibrary is not inherited into an
        # included file from its parent (see note 2 in section 4.9 of the
        # relaxng spec). However, it is inherited by descendant elements.
        # As a result, including a grammar from another file inline would
        # change its semantics by making it inherit the datatypeLibrary from
        # its parent. This would be resolved transparently if we were applying
        # all of the RELAX NG simplification rules, but we're not. To prevent
        # the semantics of the inlined grammar changing we must explicitly
        # reset the datatypeLibrary attribute to the default value (""), unless
        # the root grammar element already defines a datatypeLibrary.

        # Similarly, the only way for a namespace to propagate to an included
        # file should be by setting the ns attribute alongside the href attr
        # on the include/externalRef. However, when we merge the files,
        # namespaces defined in the parent can leak into the included grammar.
        # Unlike datatypeLibrary, it's not possible to unset an XML namespace.
        #
        # The default namespace of a file which doesn't define a default
        # namespace can be changed by merging it with a file that does. We can
        # resolve this by explicitly setting xmlns="" on the root of the
        # included file if it's not already got a default namespace.
        #
        # New namespaces defined in the parent but not the included file can
        # only affect QName values which would not resolve correctly in the
        # included file if it was loaded in isolation.
        # They can't affect elements or attributes, as the XML parser would
        # raise an error if a namespace prefix is undefined for an element or
        # attribute. To ensure an undefined (erroneous) QName does not resolve
        # to a namespace from a parent, we must validate that each QName value
        # in an included file can be resolved before merging. By doing this
        # we can be sure that an unresolvable QName does not become resolvable
        # as a result of being inlined.

        pass

    _namestartchar = '[A-Z]|_|[a-z]|[\\À-\\Ö]|[\\Ø-\\ö]|[\\ø-\\˿]|[\\Ͱ-\\ͽ]|[\\\u037f-\\\u1fff]|[\\\u200c-\\\u200d]|[\\⁰-\\\u218f]|[\\Ⰰ-\\\u2fef]|[\\、-\\\ud7ff]|[\\豈-\\\ufdcf]|[\\ﷰ-\\�]|[\\𐀀-\\\U000effff]'
    _namestartchar = r"[A-Z]|_|[a-z]| [#xC0-#xD6] | [#xD8-#xF6] | [#xF8-#x2FF] | [#x370-#x37D] | [#x37F-#x1FFF] | [#x200C-#x200D] | [#x2070-#x218F] | [#x2C00-#x2FEF] | [#x3001-#xD7FF] | [#xF900-#xFDCF] | [#xFDF0-#xFFFD] | [#x10000-#xEFFFF]
    _qname_pattern = re.compile()

    def _validate_qnames_resolve(self, grammar):
        """
        Validate the QName values in grammar to ensure they resolve to a
        namespace.
        """
        # QName values occur in the following locations:
        # - <element>'s name attribute
        # - <attribute>'s name attribute
        # - <name>'s text content
        # Note that relaxng only resolves prefixed QNames to namespaces, it
        # doesn't resolve unprefixed QNames to the default namespace (as far as
        # I can see from the spec (4.10) and from experimentation with
        # validators). As a result, we can safely ignore unprefixed QNames.
        names = grammar.xpath("//rng:name", namespaces=NSMAP)
        for name in names:


    def _validate_qname(self, element, qname):
        pass

    def _get_href_url(self, el):
        if "href" not in el.attrib:
            raise InvalidGrammarError.from_bad_element(
                el, "has no href attribute")

        href = el.attrib["href"]
        if len(href) == 0:
            raise InvalidGrammarError.from_bad_element(
                el, "has empty href attribute")

        # RELAX NG / XLink permit various characters in href attrs which are
        # not permitted in URLs. These have to be escaped to make the value a
        # URL.
        url = escape_reserved_characters(href)

        base_url = el.base
        # The base url will always be set, as we require it to be present in
        # inline() and when parsing XML strings.
        assert base_url, (el, el.base)

        # make the href absolute against the element's base url
        return self.resolve_url(el.base, url)


def _escape_match(match):
    char = match.group()
    assert len(char) == 1
    assert isinstance(char, six.binary_type)
    return b"%{:X}".format(ord(char))


def escape_reserved_characters(url):
    utf8 = url.encode("utf-8")
    return NEEDS_ESCAPE_RE.sub(_escape_match, utf8).decode("ascii")


# TODO: detect href loops

def make_absolute(url):
    """
    If url appears to be a relative filesystem path, make it absolute.
    """
    parsed = parse.urlparse(url)

    path_only_url = parse.ParseResult("", "", url, "", "", "")

    if (parsed == path_only_url and not url.startswith("/")):
        # Looks like a relative filesystem path
        return abspath(url)
    return url

def get_rng_url(args):
    url = args["<rng-url>"]

    if six.PY2:
        encoding = locale.getdefaultlocale()[1] or "ascii"
        url = url.decode(encoding)

    return escape_reserved_characters(make_absolute(url))

def main():
    args = docopt.docopt(__doc__)

    rng_url = get_rng_url(args)
    outfile = args["<rng-output>"]

    if outfile is None or outfile == "-":
        if six.PY3:
            outfile = sys.stdout.buffer
        else:
            outfile = sys.stdout

    # The inliner's paths need to be absolute
    abs_rng_url = make_absolute(rng_url)

    inliner = Inliner()
    grammar = inliner.inline(abs_rng_url)

    grammar.getroottree().write(outfile)


if __name__ == "__main__":
    main()
