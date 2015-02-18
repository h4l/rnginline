from __future__ import unicode_literals

import pkgutil
import re

import six
from six.moves.urllib import parse
from six.moves.urllib.request import pathname2url, url2pathname

from relaxnginline.exceptions import DereferenceError
from relaxnginline import uri


# Python package pattern
PACKAGE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]+(\.[a-zA-Z_][a-zA-Z0-9_]+)*$")


def reject_bytes(**kwargs):
    """
    Raise a ValueError if any of the kwarg values are six.binary_type.
    """
    for name, value in kwargs.items():
        if isinstance(value, six.binary_type):
            raise ValueError(
                "Use {} for {}, not {}. got: {!r}"
                .format(six.text_type.__name__, name, six.binary_type.__name__,
                        value))


def ensure_parsed(uri):
    reject_bytes(uri=uri)
    if isinstance(uri, six.text_type):
        return parse.urlsplit(uri)
    assert len(uri) == 5
    return uri


def quote(text, quoting_func=parse.quote):
    """
    Pass a text string through quoting_func, following the conventions of the
    Python version.

    Args:
        text: A text (not byte) string to be encoded by quoting_func.
        quoting_func: The function to perform the URI-encoding. On PY2 this
            func will receive and produce bytes, on PY3 it will receive and
            produce text.
    Returns: A text (not byte) string, encoded by quoting_func.
    """
    reject_bytes(text=text)

    if six.PY3:
        return quoting_func(text)

    # Handle Python 2 weirdness
    return quoting_func(text.encode("utf-8")).decode("ascii")


def unquote(uri_encoded_text, unquoting_func=parse.unquote):
    """
    Pass a percent-encoded string through unquoting_func, following the
    conventions of the Python version.

    Args:
        uri_encoded_text: A text (not byte) string, possibly containing
            percent-encoded escapes.
        unquoting_func: The function to escape the percent encoded escapes. On
            PY2 this func will receive and produce bytes. On PY3 it will
            receive and produce text.
    Returns:
        A text (not byte) string decoded by unquoting_func.
    """
    reject_bytes(uri_encoded_text=uri_encoded_text)

    if six.PY3:
        return unquoting_func(uri_encoded_text)

    return unquoting_func(uri_encoded_text.encode("ascii")).decode("utf-8")


def construct_file_url(file_path, base="file:"):
    """
    Create a file:// URL pointing to the filesystem path file_path.
    """
    reject_bytes(file_path=file_path)

    path = quote(file_path, quoting_func=pathname2url)
    return uri.resolve(base, path)


def deconstruct_file_url(file_url):
    url = ensure_parsed(file_url)
    scheme, _, path, _, _ = url

    if scheme != "file":
        raise ValueError("Expected a file: URL, got: {}"
                         .format(uri.recombine(url)))

    return unquote(ensure_parsed(file_url).path, unquoting_func=url2pathname)


def _validate_py_pkg_name(package):
    if not PACKAGE.match(package):
        raise ValueError("package is not a valid Python package name: {}"
                         .format(package))


def construct_py_pkg_data_url(package, resource_path):
    """
    Create a URL referencing data under a Python package.

    The made up scheme pypkgdata:// is used.

    The arguments are the same as would be passed to pkgutil.get_data() in
    order to fetch the data from the package.

    The URL can be handled by PackageDataUrlHandler, using pkgutil.get_data().
    """
    reject_bytes(package=package, resource_path=resource_path)
    _validate_py_pkg_name(package)

    if resource_path.startswith("/"):
        raise ValueError("resource_path must not start with a slash: {}"
                         .format(resource_path))

    path = quote("/" + resource_path)

    return uri.recombine(("pypkgdata", package, path, None, None))


def deconstruct_py_pkg_data_url(url):
    url = ensure_parsed(url)
    scheme, package, path, _, _ = url

    if scheme != "pypkgdata":
        raise ValueError("Not a pypkgdata: URL: {}".format(url.geturl()))

    package = unquote(package)
    path = unquote(path)

    _validate_py_pkg_name(package)

    return package, path[1:] if path else path


class FilesystemUrlHandler(object):

    def can_handle(self, url):
        return url.scheme == "file"

    def dereference(self, url):
        assert self.can_handle(url)

        # Paths will always be absolute due to relative paths being resolved
        # against absolute paths.
        assert url.path.startswith("/")

        # The path is URL-encoded, so it needs decoding before we hit the
        # filesystem. In addition, it's a UTF-8 byte string rather than
        # characters, so needs decoding as UTF-8
        path = deconstruct_file_url(url)

        try:
            with open(path, "rb") as f:
                return f.read()
        except IOError as cause:
            err = DereferenceError(
                "Unable to dereference file url: {} : {}"
                .format(uri.recombine(url), cause))
            six.raise_from(err, cause)


class PackageDataUrlHandler(object):

    def can_handle(self, url):
        return url.scheme == "pypkgdata"

    def dereference(self, url):
        assert self.can_handle(url)

        package, pkg_path = deconstruct_py_pkg_data_url(url)

        data = pkgutil.get_data(package, pkg_path)

        if data is None:
            raise DereferenceError("Unable to dereference url: {}"
                                   .format(uri.recombine(url)))

        return data


def get_default_handlers():
    return [FilesystemUrlHandler(), PackageDataUrlHandler()]

