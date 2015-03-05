Using rnginline From the Command Line
=====================================

Firstly, ensure you've :doc:`installed rnginline <installing>`.

Basic Usage
-----------

Basic usage is:

.. code-block:: console

    $ rnginline my-nested-schema-root.rng flattened-output.rng

If the second argument is not given, output goes to stdout, so you can pipe it
through ``xmllint --format`` or similar:

.. code-block:: console

    $ rnginline schema.rng | xmllint --format -
    <grammar xmlns="http://...

``rnginline -h`` gives help output as you'd expect, listing all available
options:

.. code-block:: console

    $ rnginline -h
    Flatten a hierachy of RELAX NG schemas into a single schema by recursively
    inlining <include>/<externalRef> elements.

    usage: rnginline [options] <rng-src> [<rng-output>]
           rnginline [options] --stdin [<rng-output>]

    [...]


Full Example
------------

In this example we create ``schema.rng``, which references ``external.rng`` and
inline them into one file, tidying the output with ``xmllint``:

.. code-block:: console

    $ cat > schema.rng <<'EOF'
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
    EOF

    $ cat > external.rng <<'EOF'
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
    EOF

Flatten ``schema.rng`` and everything it includes into a single XML document,
re-indent it with ``xmllint`` and save the output in ``out.rng``:

.. code-block:: console

    $ rnginline schema.rng | xmllint --format - > out.rng

    $ cat out.rng
    <?xml version="1.0"?>
    <grammar xmlns="http://relaxng.org/ns/structure/1.0">
      <div>
        <rng:div xmlns:xyz="x:/my/ns" xmlns:rng="http://relaxng.org/ns/structure/1.0">
          <rng:define name="bar">
            <rng:element name="xyz:bar">
              <rng:text/>
            </rng:element>
          </rng:define>
        </rng:div>
        <!-- Override foo -->
        <define name="foo">
          <element name="foo">
            <value datatypeLibrary="">abc</value>
          </element>
        </define>
      </div>
      <start>
        <element name="root">
          <ref name="foo"/>
          <ref name="bar"/>
        </element>
      </start>
    </grammar>

The resulting schema acts as expected — the ``foo`` definition from
``external.rng`` has been overridden:

.. code-block:: console

    $ xmllint --relaxng out.rng - <<'EOF'
    <root>
        <foo>abc</foo>
        <bar xmlns="x:/my/ns">123</bar>
    </root>
    EOF
    <?xml version="1.0"?>
    <root>
        <foo>abc</foo>
        <bar xmlns="x:/my/ns">123</bar>
    </root>
    - validates


Advanced Usage
--------------

This section describes some less common use cases.

Passing the input on stdin
^^^^^^^^^^^^^^^^^^^^^^^^^^

You can send the root schema on stdin, but doing so means rnginline won't know
the location of the file, which means it can't resolve relative references in
the input without extra information. To prevent casual use of stdin without
realising the issues, the ``--stdin`` option must be passed in place of the
input file.

To tell rnginline where the schema on stdin is from, use the ``--base-uri``
option. If you don't specify a base, the paths of included files will be
relative to the current directory.

Here's a (contrived) example of pre-processing the input before passing it on
stdin:

.. code-block:: console

    $ xmllint --format - < /tmp/schema.rnc | rnginline --base-uri /tmp/schema.rnc --stdin
    <grammar xmlns="http://...
