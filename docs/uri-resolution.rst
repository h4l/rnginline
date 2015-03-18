URI Resolution
==============

``rnginline`` uses URI Resolution to map relative paths like
``common/name.rng`` to absolute URIs, such as
``file:/a/b/proj/common/name.rng`` which can be handled by a URL Handler.

Resolution 101
~~~~~~~~~~~~~~

A quick crash course in URI resolution. Check out
`RFC 3986 <https://tools.ietf.org/html/rfc3986>`_ if you want all the details.

URI Types
---------

There are two types of URIs we need to know about. Absolute URIs and relative
URIs. In simple terms, Absolute URIs have a *scheme*, which is the part of a URI
before the first colon, e.g. in ``http://example.org`` ``http`` is the scheme.
Relative URIs don't have a scheme. e.g. ``file.txt``, ``//example.org/foo`` and
``/tmp/file.txt`` are all relative URIs.

Resolving
---------

URI Resolution is the process of merging two URIs. A *base* URI which is always
absolute, and a *reference* URI which can be absolute or relative.

There are two aspects of URI resolution we need to know about. Resolving schemes
and resolving paths.

Schemes
*******

If we resolve a relative reference URI against an absolute base URI, the
resulting URI has the scheme of the base URI, with other parts overridden
by the reference URI:

.. doctest::

    >>> from rnginline import uri
    >>> uri.resolve('file:', 'somefile.txt')
    'file:somefile.txt'

Resolving an absolute reference URI results in the base being replaced by the
reference:

.. doctest::

    >>> uri.resolve('file:somefile.txt', 'other:blah')
    'other:blah'

Paths
*****

The path component of a relative reference URI is resolved against the path
component of the base URI:

.. doctest::

    >>> uri.resolve('file:/some/dir/', 'other/dir/file.txt')
    'file:/some/dir/other/dir/file.txt'

If the reference URI's *path* is absolute (starts with a ``/``) then it replaces
the base URIs path:

.. doctest::

    >>> uri.resolve('file:/some/dir/', '/tmp/foo.txt')
    'file:/tmp/foo.txt'

If the reference URI is absolute, its path replaces the base URIs path,
regardless of whether or not the reference URIs *path* is absolute or not:

.. doctest::

    >>> uri.resolve('file:/some/dir/', 'file:file.txt')
    'file:file.txt'

Also, note that trailing slashes are significant for path resolution. Without
a trailing slash, the base's final path segment is replaced when resolving
paths:

.. doctest::

    >>> uri.resolve('file:/some/dir', 'other/dir/file.txt')
    'file:/some/other/dir/file.txt'


URI Resolution in rnginline
~~~~~~~~~~~~~~~~~~~~~~~~~~~

When the Inliner sees a URI like ``common/name.rng``, it needs to resolve it to
to absolute URIL, such as ``file:/a/b/proj/common/name.rng`` in order to
determine the location it points to, and which URL Handler can fetch the URL.

To do this, ``rnginline`` uses a heirachy of URIs:

1. The *default base URI* — The catch-all, top-most URI. This has to be
    absolute. By default it's ``file:<current-dir>`` but can be set to anything.
2. The current document's base URI — The location the current document was
    loaded from.
3. Any ``xml:base`` attributes on, or on ancestors of the an
    ``<inline>``/``<externalRef>`` XML element.
4. The URI value of the ``href`` attribute of the ``<inline>``/``<externalRef>``
    element.

The absolute URI of an ``href`` attribute is resolved by resolving 2 against 1,
then 3 against the result of that, then 4 against the result of that.

Because the default base URI is ``file:<current-dir>``, relative paths/URIs
passed to ``inline()`` get resolved to ``file:`` URLs, which are handled by
the filesystem handler without having to specify the ``file:`` scheme on the
input to ``inline()``.

Similarly, following what we've learnt above, if an input's base URI is
``pydata://my.pkg/some/dir/a.rng`` and an ``href`` attribute in ``a.rng``
contains the value ``b.rng``, it will be resolved to the absolute URL
``pydata://my.pkg/some/dir/b.rng``, and therefore handled by the pydata handler,
not the filesystem handler.
