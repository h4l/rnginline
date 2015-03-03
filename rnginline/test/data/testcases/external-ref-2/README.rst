This testcase verifies simple inclusion of an external grammar with an
``<externalRef>`` element.

- ``this.rng`` contains just an ``<element>`` element, and specifies the RELAX NG namespace with the rng prefix, instead of as the default namespace.
- ``that.rng`` contains a full ``<grammar>`` element.
