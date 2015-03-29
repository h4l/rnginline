Using rnginline From Python
===========================

Firstly, ensure you've :doc:`installed rnginline <installing>`.

.. testsetup::

    from __future__ import unicode_literals
    import tempfile, os
    tempdir = tempfile.mkdtemp()
    start_dir = os.getcwd()
    os.chdir(tempdir)
    schema = '''\
    <grammar xmlns="http://relaxng.org/ns/structure/1.0">
      <include href="external.rng">
        <!-- Override foo -->
        <define name="foo">
          <element name="foo">
            <value>abc</value>
          </element>
        </define>
      </include>
      <start>
        <element name="root">
          <ref name="foo"/>
          <ref name="bar"/>
        </element>
      </start>
    </grammar>
    '''

    with open('schema.rng', 'w') as f:
       f.write(schema)

    external = '''\
    <rng:grammar xmlns:xyz="x:/my/ns" xmlns:rng="http://relaxng.org/ns/structure/1.0">
      <rng:define name="foo">
        <rng:element name="foo">
          <rng:notAllowed/> <!-- No foo for you! -->
        </rng:element>
      </rng:define>
      <rng:define name="bar">
        <rng:element name="xyz:bar">
          <rng:text/>
        </rng:element>
      </rng:define>
    </rng:grammar>
    '''
    with open('external.rng', 'w') as f:
       f.write(external)

.. testcleanup::

    from os.path import realpath
    assert realpath(os.getcwd()) == realpath(tempdir)
    from os import path
    os.unlink(path.join(tempdir, "schema.rng"))
    os.unlink(path.join(tempdir, "external.rng"))
    os.rmdir(tempdir)
    os.chdir(start_dir)

Basic Usage
-----------

The example files used here are shown at the :ref:`bottom of this section <example-files>`.

RELAX NG files on the filesystem can be referenced by path:

.. doctest::

    >>> import rnginline, os
    >>> sorted(os.listdir('.'))
    ['external.rng', 'schema.rng']
    >>> rnginline.inline('schema.rng')
    <lxml.etree.RelaxNG object at ...>

But ``lxml`` can already do that; the real utility is in loading multi-part
schemas from locations other than the filesystem, which ``lxml`` can't do.

We can load multi-part schemas stored in Python packages (which may be stored
in zip files on disk). Here's how to load one of the schemas from rnginline's
test suite:

.. doctest:: python

    >>> import rnginline
    >>> from rnginline.urlhandlers import pydata
    >>> url = pydata.makeurl('rnginline.test',
    ...                      'data/testcases/external-ref-1/schema.rng')
    >>> url
    'pydata://rnginline.test/data/testcases/external-ref-1/schema.rng'
    >>> rnginline.inline(url)
    <lxml.etree.RelaxNG object at ...>

Data Sources
------------

The first argument to ``inline()`` defines the location to load the top-level
schema from. It can be a filesystem path, a URL, a file-like object or an
``lxml.etree`` element.

If you don't want ``inline`` to guess which input you're providing, you can pass
the input as a specific type using one of the ``url``, ``path``,
``file`` or ``etree`` keyword args instead.

URLs
****

When you use a URL as the input, it's retrieved using the same machinery that
fetches external schemas during the inlining process. By default two types of
URLs are supported.
``file:`` URLs referencing the local filesystem, and ``pydata:`` URLs
referencing data in a Python package. Note that the ``pydata:`` scheme is a
proprietary/unregistered scheme created for use in rnginline.

.. note::
    You can add support for URLs other than these, see
    :ref:`the URL Handlers section<url-handlers>` for details.

.. doctest::

    >>> rnginline.inline('pydata://rnginline.test/data/testcases/include-1/schema.rng')
    <lxml.etree.RelaxNG object at ...>
    >>> from rnginline import urlhandlers
    >>> url = urlhandlers.pydata.makeurl('rnginline.test', 'data/testcases/include-1/schema.rng')
    >>> url
    'pydata://rnginline.test/data/testcases/include-1/schema.rng'
    >>> rnginline.inline(url)
    <lxml.etree.RelaxNG object at ...>

Filesystem Paths
****************

When you pass a filesystem path, it's converted into a scheme-less URL path
which is resolved against the *default base URL*, which by default is the
current working directory.

.. doctest::

    >>> os.link('schema.rng', 'Not valid URL path.rng')
    >>> rnginline.inline('Not valid URL path.rng')
    <lxml.etree.RelaxNG object at ...>
    >>> url = urlhandlers.file.makeurl('Not valid URL path.rng')
    >>> url
    'Not%20valid%20URL%20path.rng'
    >>> rnginline.inline(url)
    <lxml.etree.RelaxNG object at ...>
    >>> os.unlink('Not valid URL path.rng')

File-like Objects
*****************

You may pass a file-like object as the input source. URLs inside the input's
schema document will be relative to the *default base URI* (current directory)
unless you use the ``base_uri`` keyword arg to ``inline()`` to specify a the
base URI of the file object.

.. doctest::

    >>> os.mkdir('foo')
    >>> os.chdir('foo')
    >>> with open('../schema.rng') as f:
    ...     # schema.rng references external.rng, which would fail to
    ...     # resolve unless we provide a base URI
    ...     rnginline.inline(f, base_uri='../schema.rng')
    <lxml.etree.RelaxNG object at ...>
    >>> os.chdir('..')
    >>> os.rmdir('foo')

``lxml.etree`` Element
**********************

You can pass pre-parsed XML as an ``lxml.etree`` element. The base URI of the
elements in the document is respected, and you should most likely ensure it's
defined to be something sensible to allow references to external files to be
resolved correctly.

The base URI of an element is by default the URL of the location the parser read
the document from. It can be overridden from within the XML document using
the ``xml:base`` attribute as well.

.. doctest::

    >>> os.mkdir('foo')
    >>> os.chdir('foo')

    >>> from lxml import etree
    >>> doc = etree.parse('../schema.rng')
    >>> doc.docinfo.URL
    '../schema.rng'
    >>> rnginline.inline(doc)
    <lxml.etree.RelaxNG object at ...>

    >>> with open('../schema.rng') as f:
    ...     schema_content = f.read()
    >>> elem = etree.fromstring(schema_content)
    >>> elem.getroottree().docinfo.URL is None
    True
    >>> rnginline.inline(elem, base_uri='../schema.rng')
    <lxml.etree.RelaxNG object at ...>

    >>> elem = etree.fromstring(schema_content, base_url='../schema.rng')
    >>> rnginline.inline(elem)
    <lxml.etree.RelaxNG object at ...>

    >>> os.chdir('..')
    >>> os.rmdir('foo')

.. note::
    If you use ``etree.XML()``/``etree.fromstring()``, the XML won't have
    a base URI set unless you use the ``base_url`` keyword arg.



.. _url-handlers:

URL Handlers
------------

URLs encountered in ``<include href="…">`` / ``<externalRef href="…">`` elements
are fetched using the URL Handlers registered with the Inliner whose
``inline()`` method has been called. As mentioned above, handlers for ``file:``
and ``pydata:`` URLs are provided and activated by default.

Handlers for other URL schemes can be created and used quite easily. Say you
wanted to inline a schema referencing sub parts via HTTP. You could do it like
this:

.. doctest::

    >>> from rnginline.urlhandlers import ensure_parsed
    >>> import requests  # http://python-requests.org
    >>> class HTTPUrlHandler(object):
    ...     def can_handle(self, url):
    ...         print('Calling can_handle() w/ {}'.format(url))
    ...         return ensure_parsed(url).scheme == 'http'
    ...
    ...     def dereference(self, url):
    ...         print('Calling dereference() w/ {}'.format(url))
    ...         return requests.get(url).content

    >>> from http.server import HTTPServer, SimpleHTTPRequestHandler
    >>> import threading
    >>> # Start an HTTP server serving the schemas in our cwd
    >>> httpd = HTTPServer(('localhost', 8000), SimpleHTTPRequestHandler)
    >>> threading.Thread(target=httpd.serve_forever).start()

    >>> rnginline.inline('http://localhost:8000/schema.rng',
    ...                  handlers=[HTTPUrlHandler()])
    Calling can_handle() w/ http://localhost:8000/schema.rng
    Calling dereference() w/ http://localhost:8000/schema.rng
    Calling can_handle() w/ http://localhost:8000/external.rng
    Calling dereference() w/ http://localhost:8000/external.rng
    <lxml.etree.RelaxNG object at ...>

    >>> httpd.shutdown()

.. _example-files:

Example Files
-------------

The preceding examples in this section assume the following files exist in the
directory the examples are run from.

.. literalinclude:: schema.rng
    :language: xml
    :caption:

.. literalinclude:: external.rng
    :language: xml
    :caption:
