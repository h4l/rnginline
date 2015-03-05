rnginline API
=============

This is the Python API reference for rnginline.

``rnginline``
-------------

.. automodule:: rnginline

    .. autofunction:: inline(source-arg, [optional-kwargs])

    .. autoclass:: rnginline.Inliner(handlers=None, postprocessors=None, default_base_uri=None)

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
    >>> from rnginline import urlhandlers
    >>> urlhandlers.file.can_handle(u"file:/tmp/foo.txt")
    True
    >>> urlhandlers.pydata.can_handle(u"pydata://mypackage/path/a.txt")
    True
