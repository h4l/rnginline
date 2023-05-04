from __future__ import annotations

import os
import tempfile
from urllib import parse

import pytest

from rnginline.exceptions import DereferenceError
from rnginline.urlhandlers import ensure_parsed, file, pydata


def test_ensure_parsed() -> None:
    assert isinstance(ensure_parsed("x:/foo"), parse.SplitResult)
    assert isinstance(ensure_parsed(parse.urlsplit("x:/foo")), parse.SplitResult)


@pytest.mark.parametrize(
    "path,abs,expected_url,expected_path",
    [
        ("foo", True, "file:foo", "foo"),
        ("foo", False, "foo", "foo"),
        ("foo", None, "foo", "foo"),
        ("/some/dir/foo", True, "file:/some/dir/foo", "/some/dir/foo"),
        ("/some/dir/foo", False, "/some/dir/foo", "/some/dir/foo"),
        ("/some/dir/foo", None, "/some/dir/foo", "/some/dir/foo"),
        ("some dir/foo bar", True, "file:some%20dir/foo%20bar", "some dir/foo bar"),
        ("some dir/foo bar", False, "some%20dir/foo%20bar", "some dir/foo bar"),
        ("some dir/foo bar", None, "some%20dir/foo%20bar", "some dir/foo bar"),
    ],
)
def test_file_url_roundtrip(
    path: str, abs: bool | None, expected_url: str, expected_path: str
) -> None:
    kwargs = {"abs": abs} if abs is not None else {}
    result_url = file.makeurl(path, **kwargs)

    assert isinstance(result_url, str)
    assert result_url == expected_url

    result_path = None
    try:
        result_path = file.breakurl(result_url)
        assert result_path is not None
    except ValueError as e:
        if expected_path is not None:
            raise e

    assert isinstance(result_url, (str, type(None)))
    assert result_path == expected_path


def test_file_breakurl_permits_relative_urls() -> None:
    assert file.breakurl("foo/bar%20baz.txt") == "foo/bar baz.txt"


def test_file_breakurl_rejects_abs_urls_of_wrong_scheme() -> None:
    with pytest.raises(ValueError):
        file.breakurl("notfile:foo/bar%20baz.txt")


def test_fs_handler_handles_file_uris() -> None:
    assert file.can_handle(parse.urlsplit("file:some/file"))


def test_fs_handler_doesnt_handle_raw_paths() -> None:
    assert not file.can_handle(parse.urlsplit("some/file"))


def test_file_url_creates_file_urls() -> None:
    file_url = file.makeurl("some/file/∑´^¨∂ƒ", abs=True)
    assert type(file_url) == str
    assert file_url == "file:some/file/%E2%88%91%C2%B4%5E%C2%A8%E2%88%82%C6%92"
    assert file.breakurl(file_url) == "some/file/∑´^¨∂ƒ"


def test_fs_handler_raises_dereference_error_on_missing_files() -> None:
    handle, path = tempfile.mkstemp(suffix="∆˚¬ß∂ƒ")
    os.close(handle)
    os.unlink(path)

    url = file.makeurl(path, abs=True)
    with pytest.raises(DereferenceError) as e:
        file.dereference(parse.urlsplit(url))
    assert url in str(e.value)


def test_fs_handler_reads_file_at_url() -> None:
    handle, path = tempfile.mkstemp(suffix="∆˚¬ß∂ƒ")

    contents = "This is some text\nblah blah\n´∑®ƒ∂ß˚\n".encode("utf-8")

    with os.fdopen(handle, "wb") as f:
        f.write(contents)

    url = file.makeurl(path, abs=True)
    result = file.dereference(parse.urlsplit(url))
    assert result == contents
    os.unlink(path)


data_data_data_uri = "pydata://rnginline.test/data/" "data-%C9%90%CA%87%C9%90p-data.txt"


def test_pydata_uri_creation() -> None:
    assert type(data_data_data_uri) == str
    package, path = "rnginline.test", "data/data-ɐʇɐp-data.txt"
    created_url = pydata.makeurl(package, path)

    assert type(created_url) == str
    assert data_data_data_uri == created_url
    assert pydata.breakurl(created_url) == (package, path)


def test_pydata_path_must_be_relative() -> None:
    with pytest.raises(ValueError):
        pydata.makeurl("foo", "/abs/path")


def test_pydata_package_name_must_be_python_name() -> None:
    with pytest.raises(ValueError):
        pydata.makeurl("ƒancy-name", "foo/bar")


def test_pydata_url_deconstruct_requries_pydata_scheme() -> None:
    with pytest.raises(ValueError):
        pydata.breakurl("foo://bar/baz")


def test_pydata_handler_handles_pydata_uris() -> None:
    assert pydata.can_handle(parse.urlsplit(data_data_data_uri))


@pytest.mark.parametrize(
    "url",
    [
        pydata.makeurl("rnginline.tset", "data"),  # dir, not file
        pydata.makeurl("rnginline.tset", "data/jfklsjflsdf.txt"),
    ],
)
def test_pydata_handler_raises_dereference_error_on_missing_file(url: str) -> None:
    with pytest.raises(DereferenceError):
        pydata.dereference(url)
