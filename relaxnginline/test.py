# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import pytest

from relaxnginline import escape_reserved_characters


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
