# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

from lxml import etree
import pytest
import pkg_resources as pr  # setuptools, but only used in tests

from relaxnginline import escape_reserved_characters, uri
import relaxnginline
from relaxnginline.urlhandlers import construct_py_pkg_data_url


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
