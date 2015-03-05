Quickstart
==========

Once you've :doc:`installed rnginline <installing>` you can use it from Python
like this:

.. code-block:: python

    >>> import rnginline
    >>> rnginline.inline("my-nested-schema-root.rng")
    <lxml.etree.RelaxNG at 0x10db63098>

You can load a multi-file schema from a Python package's data like this:

.. code-block:: python

    >>> import rnginline
    >>> from rnginline.urlhandlers import pydata
    >>> url = pydata.makeurl(u"rnginline.test",
    ...                      u"data/testcases/external-ref-1/schema.rng")
    >>> url
    u'pydata://rnginline.test/data/testcases/external-ref-1/schema.rng'
    >>> rnginline.inline(url)
    <lxml.etree.RelaxNG at 0x10daddc68>

You can use it from the command line like this:

.. code-block:: console

    $ rnginline my-nested-schema-root.rng flattened-output.rng

See :doc:`from-cmdline` or :doc:`from-python` for more details.
