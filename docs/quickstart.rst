Quickstart
==========

Install with pip:

.. code-block:: console

    $ pip install rnginline

You can use it from Python like this:

.. code-block:: python

    >>> import rnginline
    >>> rnginline.inline('my-nested-schema-root.rng')
    <lxml.etree.RelaxNG object at ...>

You can load a multi-file schema from a Python package's data like this:

.. doctest::

    >>> import rnginline
    >>> from rnginline.urlhandlers import pydata
    >>> url = pydata.makeurl('rnginline.test',
    ...                      'data/testcases/external-ref-1/schema.rng')
    >>> url
    'pydata://rnginline.test/data/testcases/external-ref-1/schema.rng'
    >>> rnginline.inline(url)
    <lxml.etree.RelaxNG object at ...>

You can use it from the command line like this:

.. code-block:: console

    $ rnginline my-nested-schema-root.rng flattened-output.rng

See :doc:`from-cmdline` or :doc:`from-python` for more details.
