from __future__ import unicode_literals

from lxml import etree


RNG_NS = "http://relaxng.org/ns/structure/1.0"
NSMAP = {"rng": RNG_NS}
RNG_GRAMMAR_TAG = etree.QName(RNG_NS, "grammar")
RNG_DEFINE_TAG = etree.QName(RNG_NS, "define")
RNG_START_TAG = etree.QName(RNG_NS, "start")
RNG_DIV_TAG = etree.QName(RNG_NS, "div")
RNG_INCLUDE_TAG = etree.QName(RNG_NS, "include")
RNG_DATA_TAG = etree.QName(RNG_NS, "data")
RNG_VALUE_TAG = etree.QName(RNG_NS, "value")
