# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import tempfile

import pytest
import six
from six.moves.urllib import parse

from relaxnginline.exceptions import DereferenceError
from relaxnginline.urlhandlers import FilesystemUrlHandler, file_url


def test_fs_handler_handles_file_uris():
    fshandler = FilesystemUrlHandler()
    assert fshandler.can_handle(parse.urlsplit("file:some/file"))


def test_fs_handler_doesnt_handle_raw_paths():
    fshandler = FilesystemUrlHandler()
    assert not fshandler.can_handle(parse.urlsplit("some/file"))


def test_file_url_creates_file_uris():
    file_uri = file_url("some/file")
    assert file_uri == "file:some/file"


def test_fs_handler_raises_dereference_error_on_missing_files():
    handle, path = tempfile.mkstemp()
    os.close(handle)
    os.unlink(path)

    url = file_url(path)
    with pytest.raises(DereferenceError) as e:
        FilesystemUrlHandler().dereference(parse.urlsplit(url))
    assert url in six.text_type(e.value)


def test_fs_handler_reads_file_at_url():
    handle, path = tempfile.mkstemp()

    contents = "This is some text\nblah blah\n".encode("ascii")

    with os.fdopen(handle, "wb") as f:
        f.write(contents)

    result = FilesystemUrlHandler().dereference(parse.urlsplit(file_url(path)))
    assert result == contents
