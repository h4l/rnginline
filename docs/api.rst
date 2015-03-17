rnginline API
=============

This is the Python API reference for rnginline.

.. testsetup::

    from __future__ import unicode_literals

``rnginline``
-------------

.. automodule:: rnginline

    .. autofunction:: inline(source-arg, [optional-kwargs])

    .. autoclass:: rnginline.Inliner

        .. automethod:: __init__

        .. automethod:: inline([src], **kwargs)


``rnginline.urlhandlers``
-------------------------

.. automodule:: rnginline.urlhandlers

    .. autoclass:: FilesystemUrlHandler

        .. automethod:: can_handle

        .. automethod:: dereference

        .. automethod:: makeurl

        .. automethod:: breakurl

    .. autoclass:: PackageDataUrlHandler

        .. automethod:: can_handle

        .. automethod:: dereference

        .. automethod:: makeurl

        .. automethod:: breakurl

    .. autodata:: file
        :annotation:
    .. autodata:: pydata
         :annotation:

Usage:
.. doctest::

    >>> from rnginline import urlhandlers
    >>> urlhandlers.file.can_handle(u"file:/tmp/foo.txt")
    True
    >>> urlhandlers.pydata.can_handle(u"pydata://mypackage/path/a.txt")
    True
