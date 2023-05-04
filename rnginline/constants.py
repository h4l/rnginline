from __future__ import annotations

from lxml import etree
from typing_extensions import Final

RNG_NS: Final = "http://relaxng.org/ns/structure/1.0"
NSMAP: Final = {"rng": RNG_NS}
RNG_GRAMMAR_TAG: Final = str(etree.QName(RNG_NS, "grammar"))
RNG_DEFINE_TAG: Final = str(etree.QName(RNG_NS, "define"))
RNG_START_TAG: Final = str(etree.QName(RNG_NS, "start"))
RNG_DIV_TAG: Final = str(etree.QName(RNG_NS, "div"))
RNG_INCLUDE_TAG: Final = str(etree.QName(RNG_NS, "include"))
RNG_DATA_TAG: Final = str(etree.QName(RNG_NS, "data"))
RNG_VALUE_TAG: Final = str(etree.QName(RNG_NS, "value"))
