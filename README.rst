rnginline: Flatten multi-file RELAX NG schemas
==============================================

rnginline is a Python library and command-line tool for loading multi-file
RELAX NG schemas from arbitary URLs, and flattening them into a single RELAX NG
schema.


Features
--------

* Convert multi-file RNG schemas into one file **without breaking or restructuring the schemas**
    * Great care is taken to maintain the semantics of the separate schema files in the single output
    * The input documents are changed as little as possible, so the output is as readable as the input
* Load schemas from:
    * The filesystem
    * From a Python package's data (without unpacking it to the filesystem)
* command-line interface as well as a Python API
* Test suite covering lots of edge cases, e.g. namespace handling
    * 100% line & branch code coverage


Quickstart
----------

Install with pip:

.. code-block:: console

    $ pip install rnginline

You can use it from Python like this:

.. code-block:: python

    >>> import rnginline
    >>> rnginline.inline('my-nested-schema-root.rng')
    <lxml.etree.RelaxNG object at ...>

You can load a multi-file schema from a Python package's data like this:

.. code-block:: python

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


Documentation
-------------

Documentation is available at TODO: put online.


Motivation
----------

``lxml`` has good support for using RELAX NG schemas, but lacks support for
loading multi-file schemas from anywhere other than the filesystem. This is a
problem if you wish to bundle a multi-file schema with your Python
package/module. You'd have to depend on setuptools being available to use its
`resource extraction`_, or use one of the existing RELAX NG merging tools to
convert your schema into a single file.

.. _resource extraction: https://pythonhosted.org/setuptools/pkg_resources.html#resource-extraction


Existing RELAX NG flattening tools
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following projects didn't quite fit my needs, leading me to write rnginline.
They may work for you though.

* `rng2srng <http://kohsuke.org/relaxng/rng2srng/>`_ - Implements full
    simplification, so the structure of the input schema will be lost
* `rng-incelim <http://ftp.davidashen.net/incelim/>`_ - A similar project to
    this, implemented in XSLT. Unfortunately
    doesn't handle namespace declarations on ``<include>`` elements correctly.
    XSLT 1.0 doesn't support creating namespace nodes, so to fix this
    rng-incelim would have to resolve all QNames in the schema to NCNames with
    ns attributes, which would be undesirable for me.
