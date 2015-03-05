#!/usr/bin/env bash
set -e
set -o verbose

TEMPDIR="$(mktemp -d)"

pushd "$TEMPDIR"

cat > schema.rng <<'EOF'
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

cat > external.rng <<'EOF'
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

rnginline schema.rng | xmllint --format - | tee out.rng

xmllint --relaxng out.rng - <<'EOF'
<root>
    <foo>abc</foo>
    <bar xmlns="x:/my/ns">123</bar>
</root>
EOF

rm schema.rng external.rng out.rng
popd
rmdir "$TEMPDIR"
