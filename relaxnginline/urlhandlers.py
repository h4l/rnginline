from __future__ import unicode_literals

import os.path
import pkgutil
import re

import six
from six.moves.urllib import parse
from six.moves.urllib.request import pathname2url, url2pathname

from relaxnginline.exceptions import DereferenceError


# Python package pattern
PACKAGE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]+(\.[a-zA-Z_][a-zA-Z0-9_]+)*$")


# Python 3 uses text consistently, but 2 returns bytes from quote/unquote and
# friends.
def ensure_text(text_or_bytes, encoding):
    if isinstance(text_or_bytes, six.text_type):
        return text_or_bytes
    return text_or_bytes.decode(encoding)


def xlink_url_decode(part):
    # XLink 1.0 permits non-ascii chars in the URL. They are represented as
    # UTF-8, with non-ascii bytes percent encoded.
    return ensure_text(parse.unquote(part), "utf-8")


def file_url(file_path):
    """
    Create a file:// URL pointing to file_path.

    file_path must be an absolute path.
    """
    if not os.path.isabs(file_path):
        raise ValueError("file_path is not absolute: {}".format(file_path))

    path = ensure_text(pathname2url(file_path.encode("utf-8")), "ascii")
    return parse.urljoin("file://", path)


def python_package_data_url(package, resource_path):
    """
    Create a URL referencing data under a Python package.

    The made up scheme pypkgdata:// is used.

    The arguments are the same as would be passed to pkgutil.get_data() in
    order to fetch the data from the package.

    The URL can be handled by PackageDataUrlHandler, using pkgutil.get_data().
    """
    if not PACKAGE.match(package):
        raise ValueError("package is not a valid Python package name: {}"
                         .format(package))

    if resource_path.startswith("/"):
        raise ValueError("resource_path must not start with a slash: {}"
                         .format(resource_path))

    path = ensure_text(parse.quote(resource_path.encode("utf-8")), "ascii")

    return parse.urlunparse(("pypkgdata", package, path,
                             None, None, None))


class FilesystemUrlHandler(object):
    make_url = staticmethod(file_url)

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
        path = ensure_text(url2pathname(url.path), "utf-8")

        try:
            with open(path, "rb") as f:
                return f.read()
        except IOError as cause:
            err = DereferenceError(
                "Unable to dereference file url: {} : {}"
                .format(url.geturl(), cause))
            six.raise_from(err, cause)


class PackageDataUrlHandler(object):
    make_url = staticmethod(python_package_data_url)

    def can_handle(self, url):
        return url.scheme == "pypkgdata"

    def dereference(self, url):
        assert self.can_handle(url)

        package = xlink_url_decode(url.netloc)
        path = xlink_url_decode(url.path)
        assert path.startswith("/")
        pkg_path = path[1:]

        data = pkgutil.get_data(package, pkg_path)

        if data is None:
            raise DereferenceError("Unable to dereference url: {}".format(url))

        return data


def get_default_handlers():
    return [FilesystemUrlHandler(), PackageDataUrlHandler()]

