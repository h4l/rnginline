# -*- coding: utf-8 -*-
"""
This module contains the built-in URL Handlers provided by ``rnginline``.

URL Handler objects are responsible for:

* Saying if they can handle a URL — ``can_handle(url)``
* Fetching the data referenced by a URL — ``dereference(url)``
"""

from __future__ import unicode_literals

import pkgutil
import re

import six
from six.moves.urllib import parse
from six.moves.urllib.request import pathname2url, url2pathname

from rnginline.exceptions import DereferenceError
from rnginline import uri


__all__ = ["file", "pydata"]

# Python package pattern
PACKAGE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]+(\.[a-zA-Z_][a-zA-Z0-9_]+)*$")


def reject_bytes(**kwargs):
    """
    Raise a ValueError if any of the kwarg values are six.binary_type.
    """
    for name, value in kwargs.items():
        if isinstance(value, six.binary_type):
            raise ValueError(
                "Use {0} for {1}, not {2}. got: {3!r}"
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


def _validate_py_pkg_name(package):
    if not PACKAGE.match(package):
        raise ValueError("package is not a valid Python package name: {0}"
                         .format(package))


class FilesystemUrlHandler(object):
    """
    A ``UrlHandler`` for ``file:`` URLs. This handler can resolve references to
    files on the local filesystem.
    """

    def can_handle(self, url):
        """
        Check if this handler supports ``url``.

        This handler supports URLs with the ``file:`` scheme.

        Args:
            url: A URL as a string.

        Returns:
            bool: True if ``url`` is supported by this handler, False otherwise
        """
        return ensure_parsed(url).scheme == "file"

    def dereference(self, url):
        """
        Read the contents of the file identified by ``url``.

        Args:
            url: A ``file:`` URL

        Returns:
            The content of the file as a byte string

        Raises:
            DereferenceError: if an ``IOError`` prevents the file being read
        """
        url = ensure_parsed(url)
        assert self.can_handle(url)

        # Paths will always be absolute due to relative paths being resolved
        # against absolute paths.
        assert url.path.startswith("/"), url

        # The path is URL-encoded, so it needs decoding before we hit the
        # filesystem. In addition, it's a UTF-8 byte string rather than
        # characters, so needs decoding as UTF-8
        path = self.breakurl(url)

        try:
            with open(path, "rb") as f:
                return f.read()
        except IOError as cause:
            err = DereferenceError(
                "Unable to dereference file url: {0} : {1}"
                .format(uri.recombine(url), cause))
            six.raise_from(err, cause)

    @staticmethod
    def makeurl(file_path, abs=False):
        """
        Create relative or absolute URL pointing to the filesystem path
        ``file_path``.

        (Absolute refers to whether or not the URL has a scheme, not whether
        the path is absolute.)

        Args:
            file_path: The path on the filesystem to point to
            abs: Whether the returned URL should be absolute (with a ``file``
                scheme) or a relative URL (URI-reference) without the scheme
        Returns:
            A ``file`` URL pointing to ``file_path``

        Note:
            The current directory of the program has no effect on this function
        Examples:
            >>> from rnginline.urlhandlers import file
            >>> file.makeurl('/tmp/foo')
            '/tmp/foo'
            >>> file.makeurl('/tmp/foo', abs=True)
            'file:/tmp/foo'
            >>> file.makeurl('file.txt')
            'file.txt'
            >>> file.makeurl('file.txt', abs=True)
            'file:file.txt'
        """
        reject_bytes(file_path=file_path)

        path = quote(file_path, quoting_func=pathname2url)
        if abs is True:
            return uri.resolve("file:", path)
        return path

    @staticmethod
    def breakurl(file_url):
        """
        Decode a ``file:`` URL into a filesystem path.

        Args:
            file_url: The URL to decode. Can be an absolute URL with a
                ``file:`` scheme, or a relative URL without a scheme.
        Returns:
            The filesystem path implied by the URL

        Examples:
            >>> from rnginline.urlhandlers import file
            >>> file.breakurl('file:/tmp/some%20file.txt')
            '/tmp/some file.txt'
            >>> file.breakurl('some/path/file%20name.dat')
            'some/path/file name.dat'
        """
        url = ensure_parsed(file_url)
        scheme, _, path, _, _ = url

        if scheme not in ("file", ""):
            raise ValueError("Expected a file: or scheme-less (relative) URL, "
                             "got: {0}".format(uri.recombine(url)))

        return unquote(ensure_parsed(file_url).path,
                       unquoting_func=url2pathname)


class PackageDataUrlHandler(object):
    """
    A URL Handler which allows data files in Python packages to be referenced.

    The URLs handled by instances of this class are layed out as follows::

        pydata://<package-path>/<path-under-package>

    For example ``pydata://rnginline.test/data/loops/start.rng``.
    """

    scheme = "pydata"

    def can_handle(self, url):
        """
        Check if this handler supports ``url``.

        This handler supports URLs with the ``pydata:`` scheme.

        Args:
            url: A URL as a string.

        Returns:
            bool: True if ``url`` is supported by this handler, False otherwise
        """
        return ensure_parsed(url).scheme == self.scheme

    def dereference(self, url):
        """
        Get the contents of the data file identified by ``url``

        ``pkgutil.get_data()`` is used to fetch the data.

        Args:
            url: A ``pydata:`` URL pointing at a file under a Python package
        Returns:
             A byte string
        Raises:
            DereferenceError: If the data identified by the URL does not exist
                or cannot be read
        """
        assert self.can_handle(url)

        package, pkg_path = self.breakurl(url)

        data = pkgutil.get_data(package, pkg_path)

        if data is None:
            raise DereferenceError("Unable to dereference url: {0}"
                                   .format(url))

        return data

    @classmethod
    def makeurl(cls, package, resource_path):
        """
        Create a URL referencing data under a Python package.

        Args:
            package: A dotted path you'd use to import the package in question
            resource_path: The path under the package to a data file
        Returns:
            ...: A URL of the form ``pydata://<package>/<resource_path>``

        Example:
            >>> from rnginline.urlhandlers import pydata
            >>> pydata.makeurl('mypkg.subpkg', 'some/file.txt')
            'pydata://mypkg.subpkg/some/file.txt'
        """
        # Python 2 uses bytes for __name__, so no point in rejecting non-text
        reject_bytes(resource_path=resource_path)
        _validate_py_pkg_name(package)

        if resource_path.startswith("/"):
            raise ValueError("resource_path must not start with a slash: {0}"
                             .format(resource_path))

        path = quote("/" + resource_path)

        return uri.recombine((cls.scheme, package, path, None, None))

    @classmethod
    def breakurl(cls, url):
        """
        Deconstruct a ``pydata:`` URL into constituent parts.

        Args:
            url: A ``pydata:`` URL
        Returns:
            A 2-tuple of the package and path contained in the URL

        Example:
            >>> from rnginline.urlhandlers import pydata
            >>> pydata.breakurl('pydata://mypkg.subpkg/some/file.txt')
            ('mypkg.subpkg', 'some/file.txt')
        """
        url = ensure_parsed(url)
        scheme, package, path, _, _ = url

        if scheme != cls.scheme:
            raise ValueError("Not a pydata: URL: {0}".format(url.geturl()))

        package = unquote(package)
        path = unquote(path)

        _validate_py_pkg_name(package)

        return package, path[1:] if path else path


file = FilesystemUrlHandler()
"""
The default instance of :class:`FilesystemUrlHandler`
"""

pydata = PackageDataUrlHandler()
"""
The default instance of :class:`PackageDataUrlHandler`
"""


def get_default_handlers():
    """
    Get a list of the default URL Handler objects.
    """
    return [file, pydata]
