rnginline
=========

.. testsetup::

    import sys
    if sys.version_info.major == 2:
        raise AssertionError(
            "Doctests are written for Python 3 and won't pass on Python 2. "
            "(This is because doctest doesn't abstract output differences "
            "between Py 2 and 3, so it's not practical to support both at "
            "once.)")

rnginline is a Python library and command line tool for flattening multi-file
`RELAX NG`_ schemas into a single file, taking care not to change the semantics
of the schema.

.. _RELAX NG: http://en.wikipedia.org/wiki/RELAX_NG

It works by implementing just enough of the RELAX NG simplification rules to
replace ``<include href="…">`` / ``<externalRef href="…">`` elements with
the content of the external files they reference.

It can be used:

* As part of a build workflow to merge RELAX NG schemas ahead of time
* At runtime as a Python library to load multi-file schemas stored as data files
  in Python packages (`lxml`_ doesn't support loading multi-file schemas from
  anything other than the filesystem.)

.. _lxml: http://lxml.de/validation.html#relaxng

Contents
========

.. toctree::
    :maxdepth: 2

    quickstart
    installing
    From the Command Line <from-cmdline>
    From Python <from-python>
    uri-resolution
    API Documentation <api>
