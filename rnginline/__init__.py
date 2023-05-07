from __future__ import annotations

import collections
import contextlib
import copy
import operator
import os
import re
import uuid
from dataclasses import dataclass, field
from functools import reduce
from os import path
from typing import (
    BinaryIO,
    ContextManager,
    Generator,
    Iterable,
    Mapping,
    Sequence,
    TextIO,
    Union,
    cast,
    overload,
)

from importlib_metadata import version
from lxml import etree
from typing_extensions import Final, Literal, Protocol

from rnginline import postprocess, uri, urlhandlers
from rnginline.constants import (
    NSMAP,
    RNG_DEFINE_TAG,
    RNG_DIV_TAG,
    RNG_GRAMMAR_TAG,
    RNG_INCLUDE_TAG,
    RNG_NS,
    RNG_START_TAG,
)
from rnginline.exceptions import (
    InvalidGrammarError,
    NoAvailableHandlerError,
    ParseError,
    SchemaIncludesSelfError,
)

__version__ = version("rnginline")

__all__ = ["inline", "Inliner"]

# Section 5.4 of XLink specifies that chars other than these must be escaped
# in values of href attrs before using them as URIs:
NOT_ESCAPED = "".join(
    chr(x)
    for x in
    # ASCII are OK
    set(range(128)) -
    # But not control chars
    set(range(0, 31)) -
    # And not these reserved chars
    set(ord(c) for c in ' <>"{}|\\^`')
)
# Matches chars which must be escaped in href attrs
NEEDS_ESCAPE_RE = re.compile("[^{0}]".format(re.escape(NOT_ESCAPED)).encode("ascii"))

RELAXNG_SCHEMA = etree.RelaxNG(
    etree.fromstring(urlhandlers.pydata.dereference("pydata://rnginline/relaxng.rng"))
)

_etree = etree  # maintain access to etree in methods w/ etree param.


AnyInlineSrc = Union[
    str,
    "os.PathLike[str]",
    TextIO,
    BinaryIO,
    etree._Element,
    "etree._ElementTree[etree._Element]",
    None,
]


@overload
def inline(
    src: AnyInlineSrc = ...,
    *,
    etree: etree._Element | etree._ElementTree[etree._Element] | None = ...,
    url: str | None = ...,
    path: str | os.PathLike[str] | None = ...,
    file: TextIO | BinaryIO | None = ...,
    handlers: Iterable[urlhandlers.UrlHandler] | None = ...,
    postprocessors: Iterable[postprocess.PostProcessor] | None = ...,
    create_validator: Literal[False],
    base_uri: str | None = ...,
    default_base_uri: str | None = ...,
    inliner: type[Inliner] | None = ...,
) -> etree._Element:
    ...


@overload
def inline(
    src: AnyInlineSrc = ...,
    *,
    etree: etree._Element | etree._ElementTree[etree._Element] | None = ...,
    url: str | None = ...,
    path: str | os.PathLike[str] | None = ...,
    file: TextIO | BinaryIO | None = ...,
    handlers: Iterable[urlhandlers.UrlHandler] | None = ...,
    postprocessors: Iterable[postprocess.PostProcessor] | None = ...,
    create_validator: Literal[True] = ...,
    base_uri: str | None = ...,
    default_base_uri: str | None = ...,
    inliner: type[Inliner] | None = ...,
) -> etree.RelaxNG:
    ...


def inline(
    src: AnyInlineSrc = None,
    *,
    etree: etree._Element | etree._ElementTree[etree._Element] | None = None,
    url: str | None = None,
    path: str | os.PathLike[str] | None = None,
    file: TextIO | BinaryIO | None = None,
    handlers: Iterable[urlhandlers.UrlHandler] | None = None,
    postprocessors: Iterable[postprocess.PostProcessor] | None = None,
    # mypy treats Literal[True, False] differently to bool 😳
    create_validator: Literal[True, False] = True,
    base_uri: str | None = None,
    default_base_uri: str | None = None,
    inliner: CreateInlinerFn | None = None,
) -> etree.RelaxNG | etree._Element:
    """
    Load an XML document containing a RELAX NG schema, recursively loading and
    inlining any ``<include href="...">``/``<externalRef href="...">``
    elements to form a complete schema in a single XML document.

    URLs in ``href`` attributes are dereferenced to obtain the RELAX NG schemas
    they point to using one or more URL Handlers. By default, handlers for
    ``file:`` and ``pydata:`` URLs are registered.

    Keyword Args:
        src: The source to load the schema from. Either an ``lxml.etree``
            ``Element``, a URL, filesystem path or file-like object
        etree: Explicitly provide an ``lxml.etree`` ``Element`` as the source
        url: Explicitly provide a URL as the source
        path: Explicitly provide a filesystem path as the source
        file: Explicitly provide a file-like object as the source
        handlers: An iterable of ``UrlHandler`` objects which are, in turn,
            requested to fetch each ``href`` attribute's URL. Defaults to
            the :obj:`rnginline.urlhandlers.file` and
            :py:obj:`rnginline.urlhandlers.pydata` in that order.
        base_uri: A URI to override the base URI of the schema with. Useful
            when the source doesn't have a sensible base URI, e.g. passing a
            file object like ``sys.stdin``
        postprocessors: An iterable of ``PostProcess`` objects which perform
            arbitary transformations on the inlined XML before it's returned/
            loaded as a schema. Defaults to the result of calling
            :func:`rnginline.postprocess.get_default_postprocessors`
        create_validator: If True, a validator created via
            ``lxml.etree.RelaxNG()`` is returned instead of an lxml ``Element``
        default_base_uri: The root URI which all others are resolved against.
            Defaults to ``file:<current directory>`` which relative file URLs
            such as ``'external.rng'`` to be found relative to the current
            working directory.
        inliner: The class to create the ``Inliner`` instance from. Defaults to
            :class:`rnginline.Inliner`.
        create_validator: If True, an lxml RelaxNG validator is created
            from the loaded XML document and returned. If False then the
            loaded XML is returned.
    Returns:
        A ``lxml.etree.RelaxNG`` validator from the fully loaded and inlined
        XML, or the XML itself, depending on the ``create_validator`` argument.
    Raises:
        RelaxngInlineError: (or subclass) is raised if the schema can't be
            loaded.
    """

    inliner_cls: CreateInlinerFn = Inliner if inliner is None else inliner

    inliner_obj: InlinerLike = inliner_cls(
        handlers=handlers,
        postprocessors=postprocessors,
        default_base_uri=default_base_uri,
    )

    # mypy can't infer the return type if we pass create_validator directly... 😟
    if create_validator:
        return inliner_obj.inline(
            src=src,
            etree=etree,
            url=url,
            path=path,
            file=file,
            base_uri=base_uri,
            create_validator=True,
        )
    else:
        return inliner_obj.inline(
            src=src,
            etree=etree,
            url=url,
            path=path,
            file=file,
            base_uri=base_uri,
            create_validator=False,
        )


class InlineContextToken:
    """An opaque marker object used to distinguish InlineContext's contexts."""

    pass


@dataclass
class InlineContext:
    """
    Maintains state through an inlining operation to prevent infinite loops,
    and allow each unique URL to be dereferenced only once.
    """

    dereferenced_urls: dict[str, bytes] = field(default_factory=dict)
    url_context_stack: list[
        tuple[str | None, InlineContextToken, etree._Element | None]
    ] = field(default_factory=list)

    def has_been_dereferenced(self, url: str) -> bool:
        return url in self.dereferenced_urls

    def get_previous_dereference(self, url: str) -> bytes:
        return self.dereferenced_urls[url]

    def store_dereference_result(self, url: str, content: bytes) -> None:
        assert url not in self.dereferenced_urls
        assert isinstance(content, bytes)
        self.dereferenced_urls[url] = content

    def url_in_context(self, url: str | None) -> bool:
        return any(u == url for (u, _, _) in self.url_context_stack)

    def _push_context(
        self, url: str | None, trigger_el: etree._Element | None
    ) -> InlineContextToken:
        if trigger_el is None and len(self.url_context_stack) != 0:
            raise ValueError("Only the first url can omit a trigger element")
        if self.url_in_context(url):
            raise SchemaIncludesSelfError.from_context_stack(
                url, trigger_el, self.url_context_stack
            )

        token = InlineContextToken()
        self.url_context_stack.append((url, token, trigger_el))
        return token

    def _pop_context(self, url: str | None, token: InlineContextToken) -> None:
        if len(self.url_context_stack) == 0:
            raise ValueError("Context stack is empty")
        head = self.url_context_stack.pop()
        if head[:2] != (url, token):
            raise ValueError(
                "Context stack head is different from expectation"
                ". expected: {0}, actual: {1}".format((url, token), head[:2])
            )

    def track(
        self, url: str | None, trigger_el: etree._Element | None = None
    ) -> ContextManager[None]:
        """
        A context manager which keeps track of inlining under the specified
        url. If an attempt is made to inline a url which is already being
        inlined, an error will be raised (as it indicates a direct or indirect
        self reference).

        """

        @contextlib.contextmanager
        def tracker(url: str | None) -> Generator[None, None, None]:
            token = self._push_context(url, trigger_el)
            yield
            self._pop_context(url, token)

        return tracker(url)


class InlinerLike(Protocol):
    @overload
    def inline(
        self,
        src: AnyInlineSrc = ...,
        *,
        etree: etree._Element | etree._ElementTree[etree._Element] | None = ...,
        url: str | None = ...,
        path: str | os.PathLike[str] | None = ...,
        file: TextIO | BinaryIO | None = ...,
        create_validator: Literal[False],
        base_uri: str | None = ...,
    ) -> etree._Element:
        ...

    @overload
    def inline(
        self,
        src: AnyInlineSrc = ...,
        *,
        etree: etree._Element | etree._ElementTree[etree._Element] | None = ...,
        url: str | None = ...,
        path: str | os.PathLike[str] | None = ...,
        file: TextIO | BinaryIO | None = ...,
        create_validator: Literal[True] = ...,
        base_uri: str | None = ...,
    ) -> etree.RelaxNG:
        ...

    @property
    def handlers(self) -> Sequence[urlhandlers.UrlHandler]:
        ...

    @property
    def postprocessors(self) -> Sequence[postprocess.PostProcessor]:
        ...

    @property
    def default_base_uri(self) -> str:
        ...


class CreateInlinerFn(Protocol):
    def __call__(
        self,
        *,
        handlers: Iterable[urlhandlers.UrlHandler] | None = None,
        postprocessors: Iterable[postprocess.PostProcessor] | None = None,
        default_base_uri: str | None = None,
    ) -> InlinerLike:
        ...


class Inliner:
    """
    Inliners merge references to external schemas into an input schema via
    their ``inline()`` method.

    Typically you can ignore this class and just use
    :py:func:`rnginline.inline` which handles instantiating an ``Inliner`` and
    calling its ``inline()`` method.
    """

    handlers: Final[Sequence[urlhandlers.UrlHandler]]
    postprocessors: Final[Sequence[postprocess.PostProcessor]]
    default_base_uri: Final[str]

    def __init__(
        self,
        *,
        handlers: Iterable[urlhandlers.UrlHandler] | None = None,
        postprocessors: Iterable[postprocess.PostProcessor] | None = None,
        default_base_uri: str | None = None,
    ):
        """
        Create an Inliner with the specified Handlers, PostProcessors and
        default base URI.

        Args:
            handlers: A list of URL Handler objects to handle URLs encountered
                by ``inline()``. Defaults to the
                :obj:`rnginline.urlhandlers.file` and
                :py:obj:`rnginline.urlhandlers.pydata` in that order.
            postprocessors: A list of PostProcess objects to apply to the fully
                inlined schema XML before it's returned by ``inline()``.
                Defaults to the result of calling
                :func:`rnginline.postprocess.get_default_postprocessors`
            default_base_uri: The root URI which all others are resolved
                against. Defaults to ``file:<current directory>``

        """
        self.handlers = list(
            self.get_default_handlers() if handlers is None else handlers
        )

        self.postprocessors = list(
            self.get_default_postprocessors()
            if postprocessors is None
            else postprocessors
        )

        if default_base_uri is None:
            default_base_uri = self.get_default_default_base_uri()
        else:
            if not uri.is_uri(default_base_uri):
                raise ValueError(
                    "default_base_uri is not a valid URI: {0}".format(default_base_uri)
                )
        self.default_base_uri = default_base_uri

    # Yes, this is the default's default.
    def get_default_default_base_uri(self) -> str:
        """
        Get the URI to use as the default_base_uri if none is provided.
        """
        dir = _get_cwd()
        assert dir.endswith("/")
        return urlhandlers.file.makeurl(dir, abs=True)

    def get_default_postprocessors(self) -> Sequence[postprocess.PostProcessor]:
        return postprocess.get_default_postprocessors()

    def get_default_handlers(self) -> Sequence[urlhandlers.UrlHandler]:
        return urlhandlers.get_default_handlers()

    def postprocess(self, grammar: etree._Element) -> etree._Element:
        for pp in self.postprocessors:
            grammar = pp.postprocess(grammar)
        return grammar

    def get_handler(self, url: str) -> urlhandlers.UrlHandler:
        handlers = (h for h in self.handlers if h.can_handle(url))
        try:
            return next(handlers)
        except StopIteration:
            raise NoAvailableHandlerError("No handler can handle url: {0}".format(url))

    def dereference_url(self, url: str, context: InlineContext) -> etree._Element:
        if context.has_been_dereferenced(url):
            content = context.get_previous_dereference(url)
        else:
            handler = self.get_handler(url)
            content = handler.dereference(url)
            context.store_dereference_result(url, content)

        return self.parse_grammar_xml(content, url)

    def parse_grammar_xml(
        self, xml_string: str | bytes, base_url: str | None
    ) -> etree._Element:
        try:
            xml = etree.fromstring(xml_string, base_url=base_url)
        except etree.ParseError as cause:
            raise ParseError(
                "Unable to parse result of dereferencing "
                f"url: {base_url}. error: {cause}"
            ) from cause

        assert xml.getroottree().docinfo.URL == base_url

        # Ensure the parsed XML is a relaxng grammar
        self.validate_grammar_xml(xml)

        return xml

    @classmethod
    def _strip_non_rng(cls, tree: etree._Element) -> etree._Element | None:
        if etree.QName(tree).namespace != RNG_NS:
            parent = tree.getparent()
            if parent is not None:
                parent.remove(tree)
            return None

        non_rng_attrs = [
            key
            for key in tree.attrib.keys()
            if etree.QName(key).namespace not in [None, RNG_NS]
        ]
        for key in non_rng_attrs:
            del tree.attrib[key]

        for child in tree.iterchildren(etree.Element):
            cls._strip_non_rng(child)

        return tree

    def validate_grammar_xml(self, grammar: etree._Element) -> None:
        """
        Checks that grammar is an XML document matching the RELAX NG schema.
        """
        url = self.get_source_url(grammar) or "??"
        msg = "The XML document from url: {0} was not a valid RELAX NG " "schema: {1}"

        # libxml2's RELAX NG validator does not implement <except>, so we can't
        # validate with the RELAX NG schema which permits foreign
        # elements/attributes. We can validate against the schema provided in
        # the RELAX NG spec, which does not permit foreign elements. To do this
        # we have to manually strip foreign elements from a copy of the XML and
        # validate that...

        stripped = self._strip_non_rng(copy.deepcopy(grammar))
        if stripped is None:
            reason = "The root element is not a RELAX NG schema element."
            raise InvalidGrammarError(msg.format(url, reason))

        try:
            RELAXNG_SCHEMA.assertValid(stripped)
        except etree.DocumentInvalid as cause:
            raise InvalidGrammarError(msg.format(url, cause)) from cause

    def get_source_url(self, xml: etree._Element) -> str | None:
        return xml.getroottree().docinfo.URL

    def create_validator(self, schema: etree._Element) -> etree.RelaxNG:
        # This should not fail under normal circumstances as we've validated
        # our input RELAX NG schemas. However, if the libxml2 compat is
        # disabled and a buggy libxml2 version is used then this could fail.
        # It seems inappropriate to catch and rethrow such an error as our own,
        # as it's lxml (via libxml2)'s problem and the user will have
        # explicitly disabled our workaround to protect them from it.
        return etree.RelaxNG(schema)

    @overload
    def inline(
        self,
        src: AnyInlineSrc = ...,
        *,
        etree: etree._Element | etree._ElementTree[etree._Element] | None = ...,
        url: str | None = ...,
        path: str | os.PathLike[str] | None = ...,
        file: TextIO | BinaryIO | None = ...,
        create_validator: Literal[False],
        base_uri: str | None = ...,
    ) -> etree._Element:
        ...

    @overload
    def inline(
        self,
        src: AnyInlineSrc = ...,
        *,
        etree: etree._Element | etree._ElementTree[etree._Element] | None = ...,
        url: str | None = ...,
        path: str | os.PathLike[str] | None = ...,
        file: TextIO | BinaryIO | None = ...,
        create_validator: Literal[True] = ...,
        base_uri: str | None = ...,
    ) -> etree.RelaxNG:
        ...

    def inline(
        self,
        src: AnyInlineSrc = None,
        *,
        etree: etree._Element | etree._ElementTree[etree._Element] | None = None,
        url: str | None = None,
        path: str | os.PathLike[str] | None = None,
        file: TextIO | BinaryIO | None = None,
        create_validator: Literal[True, False] = True,
        base_uri: str | None = None,
    ) -> etree.RelaxNG | etree._Element:
        """
        Load an XML document containing a RELAX NG schema, recursively loading
        and inlining any ``<include>``/``<externalRef>`` elements to form a
        complete schema.

        URLs in <include>/<externalRef> elements are resolved against the base
        URL of their containing document, and fetched using one of this
        Inliner's urlhandlers.

        Args:
            src: The source to load the schema from. Either an lxml.etree
                Element, a URL, filesystem path or file-like object.
            etree: Explicitly provide an lxml.etree Element as the source
            url: Explicitly provide a URL as the source
            path: Explicitly provide a path as the source
            file: Explicitly provide a file-like as the source
            base_uri: A URI to override the base URI of the grammar with.
                      Useful when the source doesn't have a sensible base URI,
                      e.g. passing sys.stdin as a file.
            create_validator: If True, an lxml RelaxNG validator is created
                from the loaded XML document and returned. If False then the
                loaded XML is returned.
        Returns:
            A ``lxml.etree.RelaxNG`` validator from the fully loaded and
            inlined XML, or the XML itself, depending on the
            ``create_validator`` argument.
        Raises:
            RelaxngInlineError: (or subclass) is raised if the schema can't be
                loaded.
        """
        arg_count = reduce(
            operator.add, (arg is not None for arg in [src, etree, url, path, file])
        )
        if arg_count != 1:
            raise ValueError(
                "A single argument must be provided from src, "
                "etree, url, path or file. got {0:d}".format(arg_count)
            )

        if src is not None:
            # lxml.etree Element
            if _etree.iselement(src):
                etree = src
            # lxml.etree ElementTree
            elif hasattr(src, "getroot"):
                etree = src.getroot()
                assert _etree.iselement(etree)
            elif isinstance(src, str):
                if uri.is_uri_reference(src):
                    url = src
                else:
                    path = src
            elif hasattr(src, "read"):
                file = cast("TextIO | BinaryIO", src)
            else:
                raise ValueError("Don't know how to use src: {0!r}".format(src))

        grammar_provided_directly = etree is not None

        if path is not None:
            assert url is None and etree is None
            url = urlhandlers.file.makeurl(path)

        if file is not None:
            assert etree is None
            # Note that the file.name attr is purposefully ignored as it's not
            # possible in the general case to know whether it's a filename/path
            # or some other indicator like <stdin> or a file descriptor number.
            # base_uri can be used to safely provide a base URI.
            etree = self.parse_grammar_xml(file.read(), None)

        context = InlineContext()

        if url is not None:
            assert etree is None
            if not uri.is_uri_reference(url):
                raise ValueError("url was not a valid URL-reference: {0}".format(url))
            # IMPORTANT: resolving the input URL against the default base URI
            # is what allows the url to be a relative URI like foo/bar.rng
            # and still get handled by the filesystem handler, which requires
            # a file: URI scheme. Note also that if url is already absolute
            # with its own scheme then the default base is ignored in the
            # resolution process.
            absolute_url = uri.resolve(self.default_base_uri, url)
            etree = self.dereference_url(absolute_url, context)

        assert etree is not None
        assert _etree.iselement(etree)

        if base_uri is not None:
            if not uri.is_uri_reference(base_uri):
                raise ValueError(
                    "base_uri is not a valid URI-reference: {0}".format(base_uri)
                )
            etree.getroottree().docinfo.URL = base_uri

        if grammar_provided_directly:
            # The XML to inline was directly provided, so we'll need to
            # validate it:
            self.validate_grammar_xml(etree)
            # Note that we don't need to validate that the element has a base
            # URI, as if it only includes absolute URLs it's not needed.

        dxi = self._inline(etree, context)
        inlined = dxi.perform_insertions()
        schema = self.postprocess(inlined)

        if create_validator is True:
            return self.create_validator(schema)
        return schema

    def _inline(
        self,
        grammar: etree._Element,
        context: InlineContext,
        trigger_el: etree._Element | None = None,
    ) -> DeferredXmlInsertion:
        dxi = DeferredXmlInsertion(grammar)

        # Track the URLs we're inlining from to detect cycles
        with context.track(self.get_source_url(grammar), trigger_el):
            # Find include/externalRefs and (recursively) inline them
            self._inline_includes(dxi, grammar, context)
            self._inline_external_refs(dxi, grammar, context)

        return dxi

    def _inline_includes(
        self, dxi: DeferredXmlInsertion, grammar: etree._Element, context: InlineContext
    ) -> None:
        assert dxi.get_root_el() == grammar
        includes = grammar.xpath("//rng:include", namespaces=NSMAP)

        for include in includes:
            self._inline_include(dxi, include, context)

    def _inline_include(
        self, dxi: DeferredXmlInsertion, include: etree._Element, context: InlineContext
    ) -> None:
        url = self._get_href_url(include)

        grammar_dxi = self._inline(
            self.dereference_url(url, context), context, trigger_el=include
        )
        grammar = grammar_dxi.get_root_el()

        # The included grammar's root element must be a grammar (unlike
        # externalRef, which can be any pattern).
        if grammar.tag != RNG_GRAMMAR_TAG:
            raise InvalidGrammarError.from_bad_element(
                include,
                "referenced a RELAX NG schema which doesn't start "
                "with a grammar element.",
            )

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

        self._remove_overridden_components(include, grammar_dxi)

        include.tag = RNG_DIV_TAG
        del include.attrib["href"]

        # TODO: Changing the tag doesn't seem to cause lxml to change ns
        # prefixes, but should probably do more testing to verify.
        grammar.tag = RNG_DIV_TAG

        # The grammar_dxi holds the pending merges for the grammar we're
        # inlining.
        dxi.register_insert(include, 0, grammar_dxi)

    def _remove_overridden_components(
        self, include: etree._Element, grammar_dxi: DeferredXmlInsertion
    ) -> None:
        # grammar_dxi is being included into the include element. include can
        # contain <start> or <define name="..."> ""component"" elements that
        # override equivalently-named elements inside grammar_dxi. These
        # override components *must* pair with exist in grammar_dxi. And they can be
        # indirectly included into grammar_dxi, so they may be in a child DXI of
        # grammar_dxi that's yet to be merged.
        override_starts, override_defines = self._grouped_components(include)

        if not (override_starts or override_defines):
            return

        starts, defines = self._grouped_components(grammar_dxi)

        if override_starts:
            if len(starts) == 0:
                raise InvalidGrammarError.from_bad_element(
                    override_starts[0],
                    "Included grammar contains no start " "element(s) to replace.",
                )
            self._remove_all(starts)

        for name, els in override_defines.items():
            overridden = defines[name]
            if len(overridden) == 0:
                raise InvalidGrammarError.from_bad_element(
                    els[0],
                    "Included grammar contains no define(s) named {0} "
                    "to replace.".format(name),
                )
            self._remove_all(overridden)

    def _remove_all(self, elements: Iterable[etree._Element]) -> None:
        for el in elements:
            parent = el.getparent()
            assert parent is not None, "attempted to remove the XML root"
            parent.remove(el)

    def _grouped_components(
        self, start: etree._Element | DeferredXmlInsertion
    ) -> tuple[Sequence[etree._Element], Mapping[str, Sequence[etree._Element]]]:
        starts: list[etree._Element] = []
        defines: dict[str, list[etree._Element]] = collections.defaultdict(list)

        for c in self._raw_components(start):
            if c.tag == RNG_START_TAG:
                starts.append(c)
            else:
                assert c.tag == RNG_DEFINE_TAG
                assert c.attrib.get("name")

                defines[c.attrib["name"]].append(c)

        return (starts, defines)

    def _raw_components(
        self, start: etree._Element | DeferredXmlInsertion
    ) -> Generator[etree._Element, None, None]:
        if isinstance(start, DeferredXmlInsertion):
            assert start.get_root_el().tag == RNG_GRAMMAR_TAG
            for el in start.iter_root_elements():
                yield from self._raw_components_under_element(el)
        else:
            yield from self._raw_components_under_element(start)

    def _raw_components_under_element(
        self, el: etree._Element
    ) -> Generator[etree._Element, None, None]:
        """
        Yields the components of an element, as defined in the RELAX NG spec.

        For our purposes, we only care about start elements and define
        elements.
        """
        assert el.tag in [RNG_DIV_TAG, RNG_GRAMMAR_TAG, RNG_INCLUDE_TAG]
        components = el.xpath("rng:start|rng:define", namespaces=NSMAP)

        for component in components:
            yield component

        # Recursively yield the components of child divs
        div_children = el.xpath("rng:div", namespaces=NSMAP)
        for div in div_children:
            for component in self._raw_components_under_element(div):
                yield component

    def _inline_external_refs(
        self, dxi: DeferredXmlInsertion, grammar: etree._Element, context: InlineContext
    ) -> None:
        assert dxi.get_root_el() == grammar
        refs = grammar.xpath("//rng:externalRef", namespaces=NSMAP)

        for ref in refs:
            self._inline_external_ref(dxi, ref, context)

    def _inline_external_ref(
        self, dxi: DeferredXmlInsertion, ref: etree._Element, context: InlineContext
    ) -> None:
        url = self._get_href_url(ref)

        grammar_dxi = self._inline(
            self.dereference_url(url, context), context, trigger_el=ref
        )
        grammar = grammar_dxi.get_root_el()

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

        dxi.register_replace(ref, grammar_dxi)

    def _get_base_uri(self, el: etree._Element) -> str:
        base = "" if el.base is None else el.base
        return uri.resolve(self.default_base_uri, base)

    def _get_href_url(self, el: etree._Element) -> str:
        # validate_grammar_xml() ensures we have an href attr
        assert "href" in el.attrib

        href = el.attrib["href"]

        # RELAX NG / XLink 1.0 permit various characters in href attrs which
        # are not permitted in URLs. These have to be escaped to make the value
        # a URL.
        # TODO: The spec references XLINK 1.0, but 1.1 is available which uses
        #       IRIs for href values. Consider supporting these.
        url = escape_reserved_characters(href)

        base = self._get_base_uri(el)
        # The base url will always be set, as even if the element has no base,
        # we have a default base URI.
        assert uri.is_uri(base), (el, el.base)

        # make the href absolute against the element's base url
        return uri.resolve(base, url)


# Sigh...
class DeferredXmlInsertion:
    """
    A ridiculous hack to merge together lxml XML trees while preserving the
    namespace prefixes used in the tree being merged in.

    When using parent.replace(child, new_el) or parent.insert(0, new_el),
    lxml tries to simplify the namespaces defined in new_el, which can result
    in the defined namespace prefixes changing. e.g. if new_el has
    xmlns:foo="bar" and "bar" is already defined higher up the tree, the
    mapping from the foo prefix -> bar may be removed. For most applications
    this doesn't matter, but QName attribute values in RELAX NG documents
    depend on the defined ns prefixes in their context, so this behaviour has
    the potential to break RELAX NG documents.
    See: http://relaxng.org/spec-20011203.html#IDA4CZR

    So, namespace prefixes are not maintained if we construct trees in code.
    They ARE maintained when parsing a serialised document. So, we can
    maintain our ns prefixes by serialising both trees, joining them together
    and parsing the result. Absolutely stupid, but there doesn't seem to be
    any other way to do this with lxml. To make this more efficient, this class
    supports batching up the merges, so we only have to perform the dump and
    parse once for any given XML element in the tree.
    """

    root_el: etree._Element
    root_replacement: etree._Element | DeferredXmlInsertion | None
    pending_insertions: list[tuple[str, etree._Element | DeferredXmlInsertion]]
    insertions_performed: bool

    def __init__(self, root_el: etree._Element) -> None:
        assert etree.iselement(root_el)
        # root_el is the root el of its tree
        assert root_el.getroottree().getroot() == root_el
        self.root_el = root_el
        self.root_replacement = None
        self.pending_insertions = []
        self.insertions_performed = False

    def get_root_el(self) -> etree._Element:
        return self.root_el

    def iter_root_elements(self) -> Generator[etree._Element, None, None]:
        """
        Generate the root elements of all XML trees that will be included in the
        merged tree returned by perform_insertions().
        """
        yield self.root_el
        for _, root in self.pending_insertions:
            if isinstance(root, DeferredXmlInsertion):
                yield from root.iter_root_elements()
            else:
                yield root

    def register_insert(
        self,
        parent: etree._Element,
        index: int,
        el: etree._Element | DeferredXmlInsertion,
    ) -> None:
        children = list(parent)
        if len(children) == 0:
            target = parent
            insert_after = False
        elif index >= len(parent):
            target = children[-1]
            insert_after = True
        else:
            el_at_pos = children[index]
            prev = el_at_pos.getprevious()
            if prev is None:
                target = parent
                insert_after = False
            else:
                target = prev
                insert_after = True

        self._register_insertion(target, insert_after, el)

    def register_replace(
        self, old_el: etree._Element, new_el: etree._Element | DeferredXmlInsertion
    ) -> None:
        """
        Replace old_el with new_el. This works like:
            el.parent.replace(el, replacement)
        except care is taken to maintain whatever namespaces prefixes are
        defined in the new_eltree.

        Note that old_el is removed immediately, but new_el is not merged in
        until perform_insertions() is called.
        """
        prev = old_el.getprevious()
        insert_after = True

        if prev is None:
            prev = old_el.getparent()
            insert_after = False

        if prev is None:
            # Nothing to maintain in old_el's tree, old_el must be the root.
            assert self.root_el == old_el
            if self.root_replacement is not None:
                raise ValueError(
                    "Root already replaced, refusing to replace "
                    "again as this call must be a coding error."
                )
            self.root_replacement = new_el
            return

        # Remove old_el immediately, and register the insertion
        self._register_insertion(prev, insert_after, new_el)
        old_el_parent = old_el.getparent()
        assert old_el_parent is not None  # cannot be None since root case is above
        old_el_parent.remove(old_el)

    def _register_insertion(
        self,
        target_el: etree._Element,
        insert_after: bool,
        el: etree._Element | DeferredXmlInsertion,
    ) -> None:
        """
        Register an element to be inserted into this object's root_el. The
        insertion is not performed immediately, but at a later time.

        Args:
            target_el: The element which marks the position to insert el into
            insert_after: If True, el will end up immediately after tail text
                of target_el (outside the tag). If False, el will end up after
                the text inside target_el (before any existing children).
            el: The element to insert. Can be an etree Element or a
                DeferredXmlInsertion instance.
        """
        # We need a way to find the insertion point in the serialised tree. A
        # UUID provides us with a string which is all but guaranteed not to
        # exist in the root_el tree.
        marker = uuid.uuid4().hex

        if insert_after:
            target_el.tail = (target_el.tail or "") + marker
        else:
            target_el.text = (target_el.text or "") + marker

        # Record the marker against the el for later bulk insertion
        self.pending_insertions.append((marker, el))

    def _prevent_repeated_insertions(self) -> None:
        if self.insertions_performed is not False:
            raise AssertionError("insertions have already performed")
        self.insertions_performed = True

    def perform_insertions(self) -> etree._Element:
        if len(self.pending_insertions) == 0:
            self._prevent_repeated_insertions()
            return self.root_el

        merged_xml = self._perform_insertions_internal()

        # Parse the merged string, maintaining the base URL of the previous doc
        return etree.fromstring(
            merged_xml, base_url=self.root_el.getroottree().docinfo.URL
        )

    def _get_xml_string(self, el: etree._Element | DeferredXmlInsertion) -> str:
        if isinstance(el, DeferredXmlInsertion):
            return el._perform_insertions_internal()
        return etree.tostring(el, encoding="unicode")

    def _perform_insertions_internal(self) -> str:
        self._prevent_repeated_insertions()

        # We never have a situation where the root is replaced, and insertions
        # are registered.
        assert self.root_replacement is None or len(self.pending_insertions) == 0

        # root_replacement will be an Element/DXI only if if the root was
        # registered for replacement.
        if self.root_replacement is not None:
            return self._get_xml_string(self.root_replacement)

        root_xml = etree.tostring(self.root_el, encoding="unicode")

        for marker, el in self.pending_insertions:
            el_xml = self._get_xml_string(el)
            merged_xml = root_xml.replace(marker, el_xml, 1)

            # There has to be a match
            assert root_xml is not merged_xml
            root_xml = merged_xml

        return root_xml


def _escape_match(match: re.Match[bytes]) -> bytes:
    char = match.group()
    assert len(char) == 1
    assert isinstance(char, bytes)
    return "%{0:X}".format(ord(char)).encode("ascii")


def escape_reserved_characters(url: str) -> str:
    utf8 = url.encode("utf-8")
    return NEEDS_ESCAPE_RE.sub(_escape_match, utf8).decode("ascii")


def _get_cwd() -> str:
    cwd_path = os.getcwd()
    # Directory paths used as URLs need to end with a slash, otherwise the last
    # path segment will be dropped when resolve()ing.
    cwd_path = path.join(cwd_path, "")
    assert cwd_path.endswith("/")
    return cwd_path
