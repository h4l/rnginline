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

        testcases.append((schema, positive_cases, negative_cases))

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
    assert escape_reserved_characters(href_text) == encoded_url


@pytest.mark.parametrize(
    "schema_file,matching_files,unmatching_files", _load_testcases())
def test_testcases(schema_file, matching_files, unmatching_files):

    schema = relaxnginline.inline(
        construct_py_pkg_data_url(TESTPKG, schema_file))

    for file in matching_files:
        good_xml = etree.parse(pr.resource_stream(TESTPKG, file))
        try:
            # Should match
            schema.assertValid(good_xml)
        except etree.DocumentInvalid as e:
            pytest.fail("{} should match {} but didn't: {}"
                        .format(file, schema_file, schema.error_log))

    for file in unmatching_files:
        bad_xml = etree.parse(pr.resource_stream(TESTPKG, file))
        with pytest.raises(etree.DocumentInvalid):
            # Shouldn't match
            schema.assertValid(bad_xml)
            pytest.fail("{} shouldn't match {} but did"
                        .format(file, schema_file))
