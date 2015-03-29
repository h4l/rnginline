# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import tempfile

import pytest
import six
from six.moves.urllib import parse

from rnginline.exceptions import DereferenceError
from rnginline.urlhandlers import (reject_bytes, ensure_parsed, quote,
                                   unquote, file, pydata)


def test_reject_bytes():
    reject_bytes(foo="bar", bar="baz", baz="boz")

    with pytest.raises(ValueError) as excinfo:
        reject_bytes(foo="bar", bar=b"baz", baz="boz")

    assert "bar" in six.text_type(excinfo.value)


def test_ensure_parsed():
    assert isinstance(ensure_parsed("x:/foo"), parse.SplitResult)
    assert isinstance(ensure_parsed(parse.urlsplit("x:/foo")),
                      parse.SplitResult)


@pytest.mark.parametrize("text", [
    "foo",
    "ƒß∂åƒ∂ß",
    "abc\U00010300\U00010410def"
])
def test_quoting_roundtrip(text):
    quoted = quote(text)
    unquoted = unquote(quoted)

    # Always working with text, not bytes
    assert isinstance(text, six.text_type)
    assert isinstance(quoted, six.text_type)
    assert isinstance(unquoted, six.text_type)

    # The quoted result should have no non-ascii chars
    assert quoted.encode("ascii").decode("ascii") == quoted

    # End result should match the input
    assert unquoted == text


@pytest.mark.parametrize("path,abs,expected_url,expected_path", [
    ("foo", True, "file:foo", "foo"),
    ("foo", False, "foo", "foo"),
    ("foo", None, "foo", "foo"),
    ("/some/dir/foo", True, "file:/some/dir/foo", "/some/dir/foo"),
    ("/some/dir/foo", False, "/some/dir/foo", "/some/dir/foo"),
    ("/some/dir/foo", None, "/some/dir/foo", "/some/dir/foo"),

    ("some dir/foo bar", True,
     "file:some%20dir/foo%20bar", "some dir/foo bar"),
    ("some dir/foo bar", False,
     "some%20dir/foo%20bar", "some dir/foo bar"),
    ("some dir/foo bar", None,
     "some%20dir/foo%20bar", "some dir/foo bar")
])
def test_file_url_roundtrip(path, abs, expected_url, expected_path):
    kwargs = {"abs": abs} if abs is not None else {}
    result_url = file.makeurl(path, **kwargs)

    assert isinstance(result_url, six.text_type)
    assert result_url == expected_url

    result_path = None
    try:
        result_path = file.breakurl(result_url)
        assert result_path is not None
    except ValueError as e:
        if expected_path is not None:
            raise e

    assert isinstance(result_url, (six.text_type, type(None)))
    assert result_path == expected_path


def test_file_breakurl_permits_relative_urls():
    assert file.breakurl("foo/bar%20baz.txt") == "foo/bar baz.txt"


def test_file_breakurl_rejects_abs_urls_of_wrong_scheme():
    with pytest.raises(ValueError):
        file.breakurl("notfile:foo/bar%20baz.txt")


def test_fs_handler_handles_file_uris():
    assert file.can_handle(parse.urlsplit("file:some/file"))


def test_fs_handler_doesnt_handle_raw_paths():
    assert not file.can_handle(parse.urlsplit("some/file"))


def test_file_url_creates_file_urls():
    file_url = file.makeurl("some/file/∑´^¨∂ƒ", abs=True)
    assert type(file_url) == six.text_type
    assert file_url == "file:some/file/%E2%88%91%C2%B4%5E%C2%A8%E2%88%82%C6%92"
    assert file.breakurl(file_url) == "some/file/∑´^¨∂ƒ"


def test_fs_handler_raises_dereference_error_on_missing_files():
    handle, path = tempfile.mkstemp(suffix="∆˚¬ß∂ƒ")
    os.close(handle)
    os.unlink(path)

    url = file.makeurl(path, abs=True)
    with pytest.raises(DereferenceError) as e:
        file.dereference(parse.urlsplit(url))
    assert url in six.text_type(e.value)


def test_fs_handler_reads_file_at_url():
    handle, path = tempfile.mkstemp(suffix="∆˚¬ß∂ƒ")

    contents = "This is some text\nblah blah\n´∑®ƒ∂ß˚\n".encode("utf-8")

    with os.fdopen(handle, "wb") as f:
        f.write(contents)

    url = file.makeurl(path, abs=True)
    result = file.dereference(parse.urlsplit(url))
    assert result == contents
    os.unlink(path)


data_data_data_uri = ("pydata://rnginline.test/data/"
                      "data-%C9%90%CA%87%C9%90p-data.txt")


def test_pydata_uri_creation():
    assert type(data_data_data_uri) == six.text_type
    package, path = "rnginline.test", "data/data-ɐʇɐp-data.txt"
    created_url = pydata.makeurl(package, path)

    assert type(created_url) == six.text_type
    assert data_data_data_uri == created_url
    assert pydata.breakurl(created_url) == (package, path)


def test_pydata_path_must_be_relative():
    with pytest.raises(ValueError):
        pydata.makeurl("foo", "/abs/path")


def test_pydata_package_name_must_be_python_name():
    with pytest.raises(ValueError):
        pydata.makeurl("ƒancy-name", "foo/bar")


@pytest.mark.skipif(six.PY3, reason="Python 2 specific behaviour")
def test_pydata_uri_creation_allows_package_as_bytes():
    # On py2 __name__ is a byte string, so it makes sense to accept bytes for
    # the package
    pydata.makeurl("foo".encode("ascii"), "bar.txt")


def test_pydata_url_deconstruct_requries_pydata_scheme():
    with pytest.raises(ValueError):
        pydata.breakurl("foo://bar/baz")


def test_pydata_handler_handles_pydata_uris():
    assert pydata.can_handle(parse.urlsplit(data_data_data_uri))


@pytest.mark.parametrize("url", [
    pydata.makeurl("rnginline.tset", "data"),  # dir, not file
    pydata.makeurl("rnginline.tset", "data/jfklsjflsdf.txt")
])
def test_pydata_handler_raises_dereference_error_on_missing_file(url):
    with pytest.raises(DereferenceError):
        pydata.dereference(url)
