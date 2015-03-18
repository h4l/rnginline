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

    Default URL Handler instances
    *****************************

    The following URL Handler objects are provided, ready to use:

    .. autodata:: file
        :annotation:
    .. autodata:: pydata
         :annotation:

    They're also available via:

    .. autofunction:: get_default_handlers

    URL Handler Classes
    *******************

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

``rnginline.postprocess``
-------------------------

.. automodule:: rnginline.postprocess

    .. autodata:: datatypelibrary

    .. autofunction:: get_default_postprocessors

    .. autoclass:: PropagateDatatypeLibraryPostProcess
