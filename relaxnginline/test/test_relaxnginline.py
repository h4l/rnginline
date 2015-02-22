# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

from lxml import etree
import pytest
import pkg_resources as pr  # setuptools, but only used in tests

import relaxnginline
from relaxnginline import DeferredXmlInsertion
from relaxnginline.urlhandlers import construct_py_pkg_data_url
from relaxnginline.exceptions import InvalidGrammarError


TESTPKG = "relaxnginline.test"


def _load_testcases():
    root_dir = "data/testcases"
    assert pr.resource_isdir(TESTPKG, root_dir)

    testcases = []
    for tc_dir in pr.resource_listdir(TESTPKG, root_dir):
        files = pr.resource_listdir(TESTPKG, "/".join([root_dir, tc_dir]))

        schema = "/".join((root_dir, tc_dir, "schema.rng"))
        positive_cases = ["/".join([root_dir, tc_dir, f]) for f in files
                          if re.match("^positive.*\.xml$", f)]
        negative_cases = ["/".join([root_dir, tc_dir, f]) for f in files
                          if re.match("^negative.*\.xml$", f)]

        assert positive_cases
        assert not [f for files in [[schema], positive_cases, negative_cases]
                    for f in files if not pr.resource_exists(__name__, f)]

        for file in positive_cases:
            testcases.append((schema, file, True))
        for file in negative_cases:
            testcases.append((schema, file, False))

    assert testcases
    return testcases


@pytest.mark.parametrize("href_text,encoded_url", [
    # Spaces are escaped
    ("/foo/bar baz.txt", "/foo/bar%20baz.txt"),
    ("file:///foo/bar baz.txt", "file:///foo/bar%20baz.txt"),

    ("http://example.com/Heizölrückstoßabdämpfung",
     "http://example.com/Heiz%C3%B6lr%C3%BCcksto%C3%9Fabd%C3%A4mpfung"),

    # urls which are already escaped are not double escaped
    ("/foo/bar%20baz.txt", "/foo/bar%20baz.txt")
])
def test_escape_reserved(href_text, encoded_url):
    assert relaxnginline.escape_reserved_characters(href_text) == encoded_url


def test_include_cant_inline_non_grammar_elements():
    """
    Verify that <include>s can't pull in a RNG file that doesn't start with a
    <grammar>.
    """
    illegal_url = construct_py_pkg_data_url(
        TESTPKG, "data/inline-non-grammar-els/illegal.rng")

    with pytest.raises(InvalidGrammarError):
        relaxnginline.inline(url=illegal_url)

    legal_url = construct_py_pkg_data_url(
        TESTPKG, "data/inline-non-grammar-els/legal.rng")
    schema = relaxnginline.inline(url=legal_url)

    assert schema(etree.XML("<foo/>"))


def _testcase_id(tc):
    prefix = "data/testcases/"
    schema, file, should_match = tc

    assert schema.startswith(prefix)
    assert file.startswith(prefix)

    return "{},{},{}".format(schema[len(prefix):], file[len(prefix):],
                             should_match)


test_testcases_testcases = _load_testcases()
@pytest.mark.parametrize(
    "schema_file,test_file,should_match", test_testcases_testcases,
    ids=map(_testcase_id, test_testcases_testcases))
def test_testcases(schema_file, test_file, should_match):
    schema = relaxnginline.inline(
        construct_py_pkg_data_url(TESTPKG, schema_file))

    xml = etree.parse(pr.resource_stream(TESTPKG, test_file))

    if should_match:
        try:
            # Should match
            schema.assertValid(xml)
        except etree.DocumentInvalid as e:
            pytest.fail("{} should match {} but didn't: {}"
                        .format(test_file, schema_file, schema.error_log))
    else:
        with pytest.raises(etree.DocumentInvalid):
            # Shouldn't match
            schema.assertValid(xml)
            pytest.fail("{} shouldn't match {} but did"
                        .format(test_file, schema_file))


def test_lxml_doesnt_honor_namespace_prefixes():
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
    assert d.prefix is None


def test_deferred_xml_insertion__replace():
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


@pytest.mark.parametrize("xml,index,expected", [
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
    ("""<a xmlns="foo" xmlns:f1="foo"><b/><b/><b/></a>""", 5, 3)
])
def test_deferred_xml_insertion__insert(xml, index, expected):
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
    new_d = list(new_c)[0]

    assert new_a.prefix is None
    assert new_c.prefix == "f2"
    assert new_d.prefix == "f3"

    assert new_a.index(new_c) == expected
