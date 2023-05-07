from __future__ import annotations

import io
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence
from unittest import mock
from urllib.parse import urlsplit

import importlib_resources
import pytest
from importlib_resources.abc import Traversable
from lxml import etree

import rnginline
from rnginline import DeferredXmlInsertion, InlineContextToken, uri, urlhandlers
from rnginline.exceptions import (
    InvalidGrammarError,
    NoAvailableHandlerError,
    ParseError,
    SchemaIncludesSelfError,
)

TESTPKG = "rnginline.test"

DATA_URI = urlhandlers.pydata.makeurl(TESTPKG, "data/")


@dataclass(frozen=True)
class SchemaTestCase:
    base_url: str
    schema_file: Traversable
    xml_file: Traversable
    should_match: bool

    @property
    def name(self) -> str:
        return Path(urlsplit(self.base_url).path).name

    @property
    def schema_url(self) -> str:
        return uri.resolve(self.base_url, self.schema_file.name)


def _load_testcases() -> "Sequence[SchemaTestCase]":
    testcases_dir = importlib_resources.files(TESTPKG) / "data/testcases"
    testcases_url = urlhandlers.pydata.makeurl(TESTPKG, "data/testcases/")
    assert testcases_dir.is_dir()

    testcases: list[SchemaTestCase] = []

    for tc_dir in testcases_dir.iterdir():
        tc_dir_url = uri.resolve(testcases_url, f"{tc_dir.name}/")

        schema = tc_dir / "schema.rng"
        positive_cases = [
            f for f in tc_dir.iterdir() if re.match(r"^positive.*\.xml$", f.name)
        ]
        negative_cases = [
            f for f in tc_dir.iterdir() if re.match(r"^negative.*\.xml$", f.name)
        ]

        assert len(positive_cases) > 0

        testcases.extend(
            SchemaTestCase(
                base_url=tc_dir_url,
                schema_file=schema,
                xml_file=file,
                should_match=should_match,
            )
            for (files, should_match) in [
                (positive_cases, True),
                (negative_cases, False),
            ]
            for file in files
        )

    assert len(testcases) > 0
    return testcases


@pytest.mark.parametrize(
    "href_text,encoded_url",
    [
        # Spaces are escaped
        ("/foo/bar baz.txt", "/foo/bar%20baz.txt"),
        ("file:///foo/bar baz.txt", "file:///foo/bar%20baz.txt"),
        (
            "http://example.com/Heizölrückstoßabdämpfung",
            "http://example.com/Heiz%C3%B6lr%C3%BCcksto%C3%9Fabd%C3%A4mpfung",
        ),
        # urls which are already escaped are not double escaped
        ("/foo/bar%20baz.txt", "/foo/bar%20baz.txt"),
    ],
)
def test_escape_reserved(href_text: str, encoded_url: str) -> None:
    assert rnginline.escape_reserved_characters(href_text) == encoded_url


def test_include_cant_inline_non_grammar_elements() -> None:
    """
    Verify that <include>s can't pull in a RNG file that doesn't start with a
    <grammar>.
    """
    illegal_url = urlhandlers.pydata.makeurl(
        TESTPKG, "data/inline-non-grammar-els/illegal.rng"
    )

    with pytest.raises(InvalidGrammarError):
        rnginline.inline(url=illegal_url)

    legal_url = urlhandlers.pydata.makeurl(
        TESTPKG, "data/inline-non-grammar-els/legal.rng"
    )
    schema = rnginline.inline(url=legal_url)

    assert schema(etree.XML("<foo/>"))


@pytest.mark.parametrize(
    "schema_path",
    [
        "data/datatype-library-inheritance/base-included.rng",
        "data/datatype-library-inheritance/base-external.rng",
    ],
)
def test_inlined_files_dont_inherit_datatype(schema_path: str) -> None:
    illegal_url = urlhandlers.pydata.makeurl(TESTPKG, schema_path)

    # Inlining will succeed
    grammar = rnginline.inline(url=illegal_url, create_validator=False)

    # But constructing a validator from the grammar XML will fail
    with pytest.raises(etree.RelaxNGError):
        etree.RelaxNG(grammar)


def _testcase_id(tc: SchemaTestCase) -> str:
    return (
        f"name:{tc.name},schema:{tc.schema_file.name},xml:{tc.xml_file.name},"
        f"should_match:{tc.should_match}"
    )


test_testcases_testcases = _load_testcases()
ttt_ids = [_testcase_id(tc) for tc in test_testcases_testcases]


@pytest.mark.parametrize("example", test_testcases_testcases, ids=ttt_ids)
def test_testcases(example: SchemaTestCase) -> None:
    schema = rnginline.inline(example.schema_url)

    with importlib_resources.as_file(example.xml_file) as xml_path:
        with xml_path.open("rb") as xml_file:
            xml = etree.parse(xml_file)

    if example.should_match:
        try:
            # Should match
            schema.assertValid(xml)
        except etree.DocumentInvalid:
            pytest.fail(
                f"{example.xml_file.name} should match {example.schema_file.name} "
                f"but didn't: {schema.error_log}"
            )
    else:
        with pytest.raises(etree.DocumentInvalid):
            # Shouldn't match
            schema.assertValid(xml)
            pytest.fail(
                f"{example.xml_file.name} shouldn't match "
                f"{example.schema_file.name} but did"
            )


def test_lxml_doesnt_honour_namespace_prefixes() -> None:
    a = etree.XML("""<a xmlns="foo" xmlns:f1="foo"><f1:b/></a>""")
    b = list(a)[0]
    c = etree.XML("""<f2:c xmlns:f2="foo" xmlns:f3="foo"><f3:d/></f2:c>""")
    d = list(c)[0]

    assert a.prefix is None
    assert b.prefix == "f1"
    assert c.prefix == "f2"
    assert d.prefix == "f3"

    # Now merge them, we'll lose the prefixes
    b.insert(0, c)
    assert a.prefix is None
    assert b.prefix == "f1"  # This won't change as we've not reinserted it
    assert c.prefix is None  # These get nuked though
    assert d.prefix is None  # type: ignore[unreachable]


def test_deferred_xml_insertion__replace() -> None:
    a = etree.XML("""<a xmlns="foo" xmlns:f1="foo"><f1:b/></a>""")
    b = list(a)[0]
    c = etree.XML("""<f2:c xmlns:f2="foo" xmlns:f3="foo"><f3:d/></f2:c>""")
    d = list(c)[0]

    assert a.prefix is None
    assert c.prefix == "f2"
    assert d.prefix == "f3"

    dxi = DeferredXmlInsertion(a)
    dxi.register_replace(b, c)
    new_a = dxi.perform_insertions()
    new_c = list(new_a)[0]
    new_d = list(new_c)[0]

    # They're now in the same root element
    assert new_a.getroottree().getroot() == new_c.getroottree().getroot()

    # The prefixes are not nuked though
    assert new_a.prefix is None and new_a.tag == "{foo}a"
    assert new_c.prefix == "f2" and new_c.tag == "{foo}c"
    assert new_d.prefix == "f3" and new_d.tag == "{foo}d"


def test_deferred_xml_insertion__replace_root_can_only_happen_once() -> None:
    a = etree.XML("""<a><b/></a>""")
    c = etree.XML("""<c><d/></c>""")
    d = list(c)[0]

    dxi = DeferredXmlInsertion(a)
    dxi.register_replace(a, c)

    # We don't allow the root to be replaced twice. Mainly because we never
    # need to, so it would indicate an error.
    with pytest.raises(ValueError):
        dxi.register_replace(a, d)


def test_deferred_xml_insertion__perform_insertions_can_only_happen_once() -> None:
    a = etree.XML("""<a><b/></a>""")
    b = list(a)[0]
    c = etree.XML("""<c><d/></c>""")

    dxi = DeferredXmlInsertion(a)
    dxi.register_replace(b, c)

    dxi.perform_insertions()  # first time
    # We don't allow insertions to be performed twice, as it's never necessary
    with pytest.raises(AssertionError):
        dxi.perform_insertions()  # second time


def test_deferred_xml_insertion__iter_root_elements() -> None:
    level0 = etree.XML("""<level0><thing/></level0>""")
    level1a = etree.XML("""<level1a><thing/></level1a>""")
    level1b = etree.XML("""<level1b/>""")
    level2a = etree.XML("""<level2a/>""")
    level2b = etree.XML("""<level2b/>""")
    other = etree.XML("""<foo/>""")

    dxi_l1a = DeferredXmlInsertion(level1a)
    dxi_l1a.register_replace(
        old_el=list(level1a)[0], new_el=DeferredXmlInsertion(level2a)
    )
    dxi_l1b = DeferredXmlInsertion(level1b)
    dxi_l1b.register_insert(parent=level1b, index=0, el=DeferredXmlInsertion(level2b))

    dxi = DeferredXmlInsertion(level0)
    dxi.register_replace(old_el=list(level0)[0], new_el=dxi_l1a)
    dxi.register_insert(parent=level0, index=1, el=dxi_l1b)
    dxi.register_insert(parent=level0, index=2, el=other)

    roots = [root for root in dxi.iter_root_elements()]
    assert roots == [level0, level1a, level2a, level1b, level2b, other]


def test_foreign_attrs_cant_be_in_default_ns() -> None:
    xml = """\
    <grammar xmlns="http://relaxng.org/ns/structure/1.0">
        <start {0}>
            <element name="foo">
                <empty/>
            </element>
        </start>
    </grammar>
    """
    rnginline.inline(etree=etree.XML(xml.format("")))

    with pytest.raises(InvalidGrammarError):
        rnginline.inline(etree=etree.XML(xml.format('illegal-attr="abc"')))


def test_include_loops_trigger_error() -> None:
    with pytest.raises(SchemaIncludesSelfError):
        rnginline.inline(
            url=urlhandlers.pydata.makeurl(TESTPKG, "data/loops/start.rng")
        )


def test_include_cant_override_start_if_no_start_in_included_file() -> None:
    with pytest.raises(InvalidGrammarError):
        rnginline.inline(
            url=urlhandlers.pydata.makeurl(
                TESTPKG, "data/include-override-start/start.rng"
            )
        )


def test_include_cant_override_define_if_no_matching_define_in_included_file() -> None:
    with pytest.raises(InvalidGrammarError):
        rnginline.inline(
            url=urlhandlers.pydata.makeurl(
                TESTPKG, "data/include-override-define/start.rng"
            )
        )


@pytest.mark.parametrize(
    "xml,index,expected",
    [
        ("""<a xmlns="foo" xmlns:f1="foo"/>""", 0, 0),
        ("""<a xmlns="foo" xmlns:f1="foo"/>""", -2, 0),
        ("""<a xmlns="foo" xmlns:f1="foo"/>""", 2, 0),
        ("""<a xmlns="foo" xmlns:f1="foo"><b/></a>""", 0, 0),
        ("""<a xmlns="foo" xmlns:f1="foo"><b/></a>""", 1, 1),
        ("""<a xmlns="foo" xmlns:f1="foo"><b/></a>""", 4, 1),
        ("""<a xmlns="foo" xmlns:f1="foo"><b/></a>""", -1, 0),
        ("""<a xmlns="foo" xmlns:f1="foo"><b/><b/><b/></a>""", -1, 2),
        ("""<a xmlns="foo" xmlns:f1="foo"><b/><b/><b/></a>""", -2, 1),
        ("""<a xmlns="foo" xmlns:f1="foo"><b/><b/><b/></a>""", -3, 0),
        ("""<a xmlns="foo" xmlns:f1="foo"><b/><b/><b/></a>""", 3, 3),
        ("""<a xmlns="foo" xmlns:f1="foo"><b/><b/><b/></a>""", 5, 3),
    ],
)
def test_deferred_xml_insertion__insert(xml: str, index: int, expected: int) -> None:
    a = etree.XML(xml)
    c = etree.XML("""<f2:c xmlns:f2="foo" xmlns:f3="foo"><f3:d/></f2:c>""")
    d = list(c)[0]

    assert a.prefix is None
    assert c.prefix == "f2"
    assert d.prefix == "f3"

    dxi = DeferredXmlInsertion(a)
    dxi.register_insert(a, index, c)
    new_a = dxi.perform_insertions()
    new_c = new_a.find("{foo}c")
    assert new_c is not None
    new_d = list(new_c)[0]

    assert new_a.prefix is None
    assert new_c.prefix == "f2"
    assert new_d.prefix == "f3"

    assert new_a.index(new_c) == expected


def test_multiple_references_to_same_uri_results_in_1_fetch() -> None:
    handler = urlhandlers.PackageDataUrlHandler()
    # Mock the dereference method to allow calls to be observed
    handler.dereference = mock.Mock(  # type: ignore[method-assign]
        side_effect=handler.dereference
    )

    url = urlhandlers.pydata.makeurl(TESTPKG, "data/multiple-ref-1-fetch/schema.rng")

    rnginline.inline(url=url, handlers=[handler])

    # schema.rng, indrect.rng & 5x popular.rng = 3 fetches total
    assert len(handler.dereference.mock_calls) == 3


def test_inline_url_arguments_are_resolved_against_default_base_uri() -> None:
    class Stop(Exception):
        pass

    # Mock the dereference method to allow calls to be observed
    handler = mock.MagicMock()
    handler.can_handle.return_value = True
    handler.dereference.side_effect = Stop

    url = "somefile.txt"

    with pytest.raises(Stop):
        rnginline.inline(url=url, handlers=[handler])

    # The default base URL is the cwd
    expected_base = urlhandlers.file.makeurl(rnginline._get_cwd(), abs=True)
    # The url we provide should be resolved against the default base:
    expected_url = uri.resolve(expected_base, url)
    assert expected_url.startswith(expected_base)
    assert expected_url.endswith("somefile.txt")

    handler.dereference.assert_called_once_with(expected_url)


def test_override_default_base_uri() -> None:
    default_base_uri = urlhandlers.pydata.makeurl(TESTPKG, "data/testcases/xml-base/")
    schema = rnginline.inline(url="schema.rng", default_base_uri=default_base_uri)

    xml_url = uri.resolve(default_base_uri, "positive-1.xml")
    xml = etree.fromstring(urlhandlers.pydata.dereference(xml_url))

    assert schema(xml)


def test_overridden_default_base_uri_must_be_absolute() -> None:
    """
    The default base URI must be an absolute URI. i.e. matches the URI grammar,
    not the URI-reference grammar.
    """
    relative_uri = "/some/path/blah"
    assert uri.is_uri_reference(relative_uri)
    assert not uri.is_uri(relative_uri)

    with pytest.raises(ValueError):
        rnginline.Inliner(default_base_uri=relative_uri)


def test_provide_base_uri() -> None:
    """
    This tests manually specifying a base URI to use for the source.
    """
    base_uri = urlhandlers.pydata.makeurl(TESTPKG, "data/testcases/xml-base/schema.rng")
    # Use a file object so that the inliner won't know the URI of the src
    fileobj = io.BytesIO(urlhandlers.pydata.dereference(base_uri))

    schema = rnginline.inline(
        fileobj,
        base_uri=base_uri,
        # our base URI is absolute, so the default
        # base won't have any effect.
        default_base_uri="x:/blah",
    )

    xml_url = uri.resolve(base_uri, "positive-1.xml")
    xml = etree.fromstring(urlhandlers.pydata.dereference(xml_url))

    assert schema(xml)


def test_overridden_base_uri_must_be_uri_ref() -> None:
    """
    The base URI, if specified, must match the URI-reference grammar. i.e. it
    is a relative or absolute URI.
    """
    bad_uri = "x:/some/path/spaces not allowed/oops"
    assert not uri.is_uri_reference(bad_uri)

    with pytest.raises(ValueError):
        rnginline.inline(
            # some random schema, not of any significance
            uri.resolve(DATA_URI, "testcases/include-1/schema.rng"),
            base_uri=bad_uri,
        )


def test_unhandleable_url_raises_error() -> None:
    with pytest.raises(NoAvailableHandlerError):
        rnginline.inline(url="my-fancy-url-scheme:/foo")


def test_context_pushes_must_have_parents_except_first() -> None:
    context = rnginline.InlineContext()

    with context.track("x:/some/url"):
        with pytest.raises(ValueError):
            # Tracking second URL without passing context el: not allowed
            with context.track("x:/other/url"):
                pass


def test_including_invalid_xml_file_raises_parse_error() -> None:
    url = urlhandlers.pydata.makeurl(TESTPKG, "data/include-invalid-xml/ok.rng")
    with pytest.raises(ParseError):
        rnginline.inline(url=url)


def test_including_non_rng_xml_file_raises_invalid_grammar_error() -> None:
    url = urlhandlers.pydata.makeurl(TESTPKG, "data/include-non-rng-xml/ok.rng")
    with pytest.raises(InvalidGrammarError):
        rnginline.inline(url=url)


def test_calling_inline_with_0_args_raises_value_error() -> None:
    with pytest.raises(ValueError):
        rnginline.inline()


def test_inline_etree_el_with_no_base_uri_uses_default_base_uri() -> None:
    base_url = urlhandlers.pydata.makeurl(TESTPKG, "data/testcases/xml-base/")
    schema_bytes = urlhandlers.pydata.dereference(uri.resolve(base_url, "schema.rng"))

    schema_el = etree.fromstring(schema_bytes)
    assert schema_el.getroottree().docinfo.URL is None

    # The default-default base URI is the pwd, so let's use something else
    # to demonstrate this. An unhandlable URI will result in a
    # NoAvailableHandlerError when the first href is dereferenced.
    with pytest.raises(NoAvailableHandlerError):
        rnginline.inline(etree=schema_el, default_base_uri="x:")

    # If we use a sensible default base URI the references will be resolved OK,
    # even though the XML document itself has no base URI
    schema = rnginline.inline(etree=schema_el, default_base_uri=base_url)

    assert schema(
        etree.fromstring(
            urlhandlers.pydata.dereference(uri.resolve(base_url, "positive-1.xml"))
        )
    )


def test_inline_args_etree_as_src() -> None:
    url = uri.resolve(DATA_URI, "testcases/xml-base/schema.rng")
    schema_el = etree.fromstring(
        urlhandlers.pydata.dereference(
            uri.resolve(DATA_URI, "testcases/xml-base/schema.rng")
        ),
        base_url=url,
    )

    assert etree.iselement(schema_el)

    # pass schema_el as src, should be detected as an Element
    schema = rnginline.inline(schema_el)

    assert schema(
        etree.fromstring(
            urlhandlers.pydata.dereference(uri.resolve(url, "positive-1.xml"))
        )
    )


def test_inline_args_etree_doc_as_src() -> None:
    url = uri.resolve(DATA_URI, "testcases/xml-base/schema.rng")
    schema_el = etree.fromstring(
        urlhandlers.pydata.dereference(
            uri.resolve(DATA_URI, "testcases/xml-base/schema.rng")
        ),
        base_url=url,
    )

    schema_root = schema_el.getroottree()
    assert not etree.iselement(schema_root)

    # pass etree document (not el) as src, should pull out root el and use it
    schema = rnginline.inline(schema_root)

    assert schema(
        etree.fromstring(
            urlhandlers.pydata.dereference(uri.resolve(url, "positive-1.xml"))
        )
    )


def test_inline_args_url_refs_must_be_valid() -> None:
    bad_url = "/tmp/File Name With Spaces"
    assert not uri.is_uri_reference(bad_url)

    with pytest.raises(ValueError):
        rnginline.inline(url=bad_url)


def test_inline_args_fs_path_as_src() -> None:
    grammar_xml = b"""
    <element name="start" xmlns="http://relaxng.org/ns/structure/1.0">
        <empty/>
    </element>
    """
    path = "/some/dir/Filename with spaces.rng"
    handler = urlhandlers.FilesystemUrlHandler()
    handler.dereference = mock.Mock(  # type: ignore[method-assign]
        side_effect=[grammar_xml]
    )

    rnginline.inline(path, handlers=[handler])

    handler.dereference.assert_called_once_with(
        urlhandlers.file.makeurl(path, abs=True)
    )


def test_inline_args_passing_garbage() -> None:
    with pytest.raises(ValueError):
        # pass a useless arg as src
        rnginline.inline(1234)  # type: ignore[call-overload]


def test_context_pop_with_no_context_raises_error() -> None:
    context = rnginline.InlineContext()

    with pytest.raises(ValueError):
        context._pop_context("x:/url", None)  # type: ignore[arg-type]


def test_context_pop_with_mismatching_url_raises_error() -> None:
    context = rnginline.InlineContext()
    token = context._push_context("x:/foo", None)

    with pytest.raises(ValueError):
        # different URL to push call
        context._pop_context("x:/bar", token)


def test_context_pop_with_mismatching_token_raises_error() -> None:
    context = rnginline.InlineContext()
    url = "x:/foo"
    context._push_context(url, None)  # Ignore the returned token

    with pytest.raises(ValueError):
        # different token to push call
        context._pop_context(url, InlineContextToken())
