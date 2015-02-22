This testcase verifies that XML namespaces are handled correctly when inlining
an ``<externalRef>`` element. There are several things to verify, as there are
several ways of specifying namespaces in RELAX NG.

- That the default xmlns of a file has no effect on unprefixed names
- Namespaces in ns attributes are honored
- ns attribute on the ``<externalRef>`` element is transferred to the root el
    of the inlined XML if the root el doesn't already have a ns attribute.
- Prefixed (QName) namespaces are honored
    - That having the same prefix bound to a different namespace value in
        including and includee files does not clobber one or the other's
        namespace.
