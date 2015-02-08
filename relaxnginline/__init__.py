"""
usage: relaxnginline [options] <rng-url> [<rng-output>]

options:

   --propagate-datatypelibrary -p    Propagate datatypeLibrary attributes to
                                     data and value elements. This can be used
                                     to work around a bug in libxml2: it
                                     doesn't find datatypeLibrary attributes on
                                     div elements.
"""
from __future__ import print_function, unicode_literals

import contextlib
import locale
import re
from os.path import abspath
import sys
import collections
import pkg_resources
import copy

from lxml import etree
import docopt
import six
from six.moves.urllib import parse
from relaxnginline import postprocess

from relaxnginline.constants import (NSMAP, RNG_DIV_TAG, RNG_START_TAG,
                                     RNG_DEFINE_TAG, RNG_INCLUDE_TAG)

__version__ = "0.0.0"

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
NEEDS_ESCAPE_RE = re.compile("[^{}]"
                             .format(re.escape(NOT_ESCAPED)).encode("ascii"))


RELAXNG_SCHEMA = etree.RelaxNG(etree.parse(
    pkg_resources.resource_stream("relaxnginline", "relaxng.rng")))


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


class SchemaIncludesSelfError(InvalidGrammarError, DereferenceError):
    @classmethod
    def from_context_stack(cls, url, trigger_el, stack):
        # Drop tokens from the stack and append the loop-creating el & url
        url_triggers = [(u, t) for (u, _, t) in stack] + [(url, trigger_el)]

        loop = "".join(cls._format_url_trigger(u, t)
                       for (u, t) in url_triggers)

        return cls("A schema referenced itself, creating a loop:\n{}"
                   .format(loop))

    @classmethod
    def _format_url_trigger(cls, url, trigger_el):
        if trigger_el is None:
            return url
        return ":{} <{}> -> \n{}".format(
            trigger_el.sourceline, etree.QName(trigger_el).localname, url)


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
            # filesystem. In addition, it's a UTF-8 byte string rather than
            # characters, so needs decoding as UTF-8
            path = parse.unquote(url.path).decode("utf-8")

            with open(path, "rb") as f:
                return f.read()
        except IOError as e:
            err = DereferenceError(
                "Unable to dereference file url: {}".format(url.geturl()))
            six.raise_from(err, e)


class InlineContext(object):
    """
    Maintains state through an inlining operation to prevent infinite loops,
    and allow each unique URL to be dereferenced only once.
    """
    def __init__(self, dereferenced_urls={}, stack=[]):
        self.dereferenced_urls = dereferenced_urls
        self.url_context_stack = stack

    def has_been_dereferenced(self, url):
        return url in self.dereferenced_urls

    def get_previous_dereference(self, url):
        return copy.deepcopy(self.dereferenced_urls[url])

    def url_in_context(self, url):
        return any(u == url for (u, _, _) in self.url_context_stack)

    def _push_context(self, url, trigger_el):
        if trigger_el is None and len(self.url_context_stack) != 0:
            raise ValueError("Only the first url can omit a trigger element")
        if self.url_in_context(url):
            raise SchemaIncludesSelfError.from_context_stack(
                url, trigger_el, self.url_context_stack)

        token = object()
        self.url_context_stack.append((url, token, trigger_el))
        return token

    def _pop_context(self, url, token):
        if len(self.url_context_stack) == 0:
            raise ValueError("Context stack is empty")
        head = self.url_context_stack.pop()
        if head[:2] != (url, token):
            raise ValueError("Context stack head is different from expectation"
                             ". expected: {}, actual: {}"
                             .format((url, token), head[:2]))

    def track(self, url, trigger_el=None):
        """
        A context manager which keeps track of inlining under the specified
        url. If an attempt is made to inline a url which is already being
        inlined, an error will be raised (as it indicates a direct or indirect
        self reference).
        """
        @contextlib.contextmanager
        def tracker(url):
            token = self._push_context(url, trigger_el)
            yield
            self._pop_context(url, token)
        return tracker(url)


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

    def dereference_url(self, url, context):
        if context.has_been_dereferenced(url):
            return context.get_previous_dereference(url)

        parsed_url = self.parse_url(url)
        handler = self.get_handler(url)
        return self.parse_grammar_xml(handler.dereference(parsed_url), url)

    def parse_grammar_xml(self, xml_string, base_url):
        try:
            xml = etree.fromstring(xml_string, base_url=base_url)
        except etree.ParseError as cause:
            err = ParseError("Unable to parse result of dereferencing url: {}."
                             " error: {}".format(base_url, cause))
            six.raise_from(err, cause)

        assert xml.base == base_url

        # Ensure the parsed XML is a relaxng grammar
        self.validate_grammar_xml(xml)

        return xml

    def validate_grammar_xml(self, grammar):
        """
        Checks that grammar is an XML document matching the RELAX NG schema.
        """
        try:
            RELAXNG_SCHEMA.assertValid(grammar)
        except etree.DocumentInvalid as cause:
            url = self.get_source_url(grammar) or "??"
            err = InvalidGrammarError(
                "The XML document from url: {} was not a valid RELAX NG "
                "schema: {}".format(url, cause))
            six.raise_from(err, cause)

    def get_source_url(self, xml):
        return xml.getroottree().docinfo.URL

    def inline(self, element_or_url):
        """

        """
        context = InlineContext()
        if isinstance(element_or_url, six.text_type):
            grammar = self.dereference_url(element_or_url, context)
        else:
            # Assume we have an etree Element
            grammar = element_or_url
            self.validate_grammar_xml(grammar)

        return self._inline(grammar, context)

    def _inline(self, grammar, context, trigger_el=None):

        # Track the URLs we're inlining from to detect cycles
        with context.track(self.get_source_url(grammar), trigger_el):
            # Find include/externalRefs and (recursively) inline them
            grammar = self._inline_includes(grammar, context)
            grammar = self._inline_external_refs(grammar, context)

        return grammar

    def _inline_includes(self, grammar, context):
        includes = grammar.xpath("//rng:include", namespaces=NSMAP)

        for include in includes:
            self._inline_include(include, context)

        return grammar

    def _inline_include(self, include, context):
        url = self._get_href_url(include)

        grammar = self._inline(self.dereference_url(url, context), context,
                               trigger_el=include)

        # To process an include the RNG spec (4.7) says we need to:
        # - recursively process includes in included grammar
        # - override starts and defines with any provided in the include el
        # - rename include to div, removing href attr
        # - insert the referenced grammar before any start/define elements in
        #   the include
        # - rename the grammar el to div
        #
        # In addition, we need to prevent datatypeLibrary from leaking into
        # the included grammar. See explanation in _inline_external_ref()

        if "datatypeLibrary" not in grammar.attrib:
            grammar.attrib["datatypeLibrary"] = ""

        self._remove_overridden_components(include, grammar)

        include.tag = RNG_DIV_TAG
        del include.attrib["href"]

        include.insert(0, grammar)
        grammar.tag = RNG_DIV_TAG

    def _remove_overridden_components(self, include, grammar):
        override_starts, override_defines = self._grouped_components(include)

        if not (override_starts or override_defines):
            return

        starts, defines = self._grouped_components(grammar)

        if override_starts:
            if len(starts) == 0:
                raise InvalidGrammarError.from_bad_element(
                    override_starts[0], "Included grammar contains no start "
                                        "element(s) to replace.")
            self._remove_all(starts)

        for name, els in override_defines:
            overridden = defines[name]
            if len(overridden) == 0:
                raise InvalidGrammarError.from_bad_element(
                    els[0], "Included grammar contains no define(s) named {} "
                            "to replace.".format(name))
            self._remove_all(overridden)

    def _remove_all(self, elements):
        for el in elements:
            el.getparent().remove(el)

    def _grouped_components(self, el):
        starts = []
        defines = collections.defaultdict(list)

        for c in self._raw_components(el):
            if c.tag == RNG_START_TAG:
                starts.append(c)
            else:
                assert c.tag == RNG_DEFINE_TAG
                assert c.attrib.get("name")

                defines[c.attrib["name"]].append(c)

        return (starts, defines)

    def _raw_components(self, el):
        """
        Yields the components of an element, as defined in the RELAX NG spec.

        For our purposes, we only care about start elements and define
        elements.
        """
        assert el.tag in [RNG_START_TAG, RNG_DEFINE_TAG, RNG_INCLUDE_TAG]
        components = el.xpath("rng:start|rng:define", namespaces=NSMAP)

        for component in components:
            yield component

        # Recursively yield the components of child divs
        div_children = el.xpath("rng:div", namespaces=NSMAP)
        for div in div_children:
            for components in self._components(div):
                yield component

    def _inline_external_refs(self, grammar, context):
        refs = grammar.xpath("//rng:externalRef", namespaces=NSMAP)

        for ref in refs:
            self._inline_external_ref(ref, context)

        return grammar

    def _inline_external_ref(self, ref, context):
        url = self._get_href_url(ref)

        grammar = self.inline(self.dereference_url(url, context), context,
                              trigger_el=ref)

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
        #
        # Namespaces are inherited into included files, so no special handling
        # is needed, other than copying over of any ns attribute on the
        # externalRef element.

        if "datatypeLibrary" not in grammar.attrib:
            grammar.attrib["datatypeLibrary"] = ""

        if "ns" in ref.attrib and "ns" not in grammar.attrib:
            grammar.attrib["ns"] = ref.attrib["ns"]

        ref.getparent().replace(ref, grammar)

    def _get_href_url(self, el):
        if "href" not in el.attrib:
            raise InvalidGrammarError.from_bad_element(
                el, "has no href attribute")

        href = el.attrib["href"]
        if len(href) == 0:
            raise InvalidGrammarError.from_bad_element(
                el, "has empty href attribute")

        # RELAX NG / XLink 1.0 permit various characters in href attrs which
        # are not permitted in URLs. These have to be escaped to make the value
        # a URL.
        # TODO: The spec references XLINK 1.0, but 1.1 is available which uses
        #       IRIs for href values. Consider supporting these.
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
    return "%{:X}".format(ord(char)).encode("ascii")


def escape_reserved_characters(url):
    utf8 = url.encode("utf-8")
    return NEEDS_ESCAPE_RE.sub(_escape_match, utf8).decode("ascii")


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

    if args["--propagate-datatypelibrary"]:
        grammar = postprocess.datatypelibrary(grammar)

    grammar.getroottree().write(outfile)


if __name__ == "__main__":
    main()
