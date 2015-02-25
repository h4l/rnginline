# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import tempfile

import pytest
import six
from six.moves.urllib import parse

from relaxnginline.exceptions import DereferenceError
from relaxnginline.urlhandlers import (
    FilesystemUrlHandler, PackageDataUrlHandler,
    construct_file_url, deconstruct_file_url,
    construct_py_pkg_data_url, deconstruct_py_pkg_data_url)


def test_fs_handler_handles_file_uris():
    fshandler = FilesystemUrlHandler()
    assert fshandler.can_handle(parse.urlsplit("file:some/file"))


def test_fs_handler_doesnt_handle_raw_paths():
    fshandler = FilesystemUrlHandler()
    assert not fshandler.can_handle(parse.urlsplit("some/file"))


def test_file_url_creates_file_urls():
    file_url = construct_file_url("some/file/∑´^¨∂ƒ")
    assert type(file_url) == six.text_type
    assert file_url == "file:some/file/%E2%88%91%C2%B4%5E%C2%A8%E2%88%82%C6%92"
    assert deconstruct_file_url(file_url) == "some/file/∑´^¨∂ƒ"


def test_fs_handler_raises_dereference_error_on_missing_files():
    handle, path = tempfile.mkstemp(suffix="∆˚¬ß∂ƒ")
    os.close(handle)
    os.unlink(path)

    url = construct_file_url(path)
    with pytest.raises(DereferenceError) as e:
        FilesystemUrlHandler().dereference(parse.urlsplit(url))
    assert url in six.text_type(e.value)


def test_fs_handler_reads_file_at_url():
    handle, path = tempfile.mkstemp(suffix="∆˚¬ß∂ƒ")

    contents = "This is some text\nblah blah\n´∑®ƒ∂ß˚\n".encode("utf-8")

    with os.fdopen(handle, "wb") as f:
        f.write(contents)

    url = construct_file_url(path)
    result = FilesystemUrlHandler().dereference(parse.urlsplit(url))
    assert result == contents


data_data_data_uri = ("pypkgdata://relaxnginline.test/data/"
                      "data-%C9%90%CA%87%C9%90p-data.txt")


data_data_data = """\
This file contains some data which will be loaded by the test_urlhandlers.py
file to test the PackageDataUrlHandler.

It's got some non-ascii characters in the filename and also here:
                                                     ʇxǝʇ ᴉᴉɔsɐ-uou uʍop ǝpᴉsdn
BTW, this file is encoded in UTF-8.
"""


def test_pypkgdata_uri_creation():
    assert type(data_data_data_uri) == six.text_type
    package, path = "relaxnginline.test", "data/data-ɐʇɐp-data.txt"
    created_url = construct_py_pkg_data_url(package, path)

    assert type(created_url) == six.text_type
    assert data_data_data_uri == created_url
    assert deconstruct_py_pkg_data_url(created_url) == (package, path)


@pytest.mark.skipif(six.PY3, reason="Python 2 specific behaviour")
def test_pypkgdata_uri_creation_allows_package_as_bytes():
    # On py2 __name__ is a byte string, so it makes sense to accept bytes for
    # the package
    construct_py_pkg_data_url("foo".encode("ascii"), "bar.txt")


def test_pypkgdata_handler_handles_pypkgdata_uris():
    handler = PackageDataUrlHandler()
    assert handler.can_handle(parse.urlsplit(data_data_data_uri))


def test_pypkgdata_handler_dereferences_to_correct_data():
    assert type(data_data_data) == six.text_type

    data = PackageDataUrlHandler().dereference(
        parse.urlsplit(data_data_data_uri))

    assert data.decode("utf-8") == data_data_data
