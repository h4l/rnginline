from __future__ import annotations

import copy

import pytest
from lxml import etree

from rnginline import urlhandlers
from rnginline.constants import NSMAP
from rnginline.postprocess import datatypelibrary


@pytest.mark.parametrize(
    "xml,expected",
    [
        ('<a datatypeLibrary="a"><b><c id="start"/></b></a>', "a"),
        ('<a datatypeLibrary="a"><b><c datatypeLibrary="c" id="start"/></b></a>', "c"),
        ('<a datatypeLibrary="a"><b datatypeLibrary="b"><c id="start"/></b></a>', "b"),
        ('<a datatypeLibrary="a"><b><c datatypeLibrary="c" id="start"/></b></a>', "c"),
        ('<a datatypeLibrary="a"><b><c datatypeLibrary="" id="start"/></b></a>', ""),
        ('<a><b><c id="start"/></b></a>', ""),
    ],
)
def test_lookup_datatypelibrary(xml: str, expected: str) -> None:
    root = etree.XML(xml)
    (start,) = root.xpath("//*[@id='start']")

    assert datatypelibrary.lookup_datatypelibrary(start) == expected


@pytest.mark.parametrize(
    "path",
    [
        "data/datatype-library-propagation/a.rng",
        "data/datatype-library-propagation/b.rng",
    ],
)
def test_propagate_datatype_library(path: str) -> None:
    url = urlhandlers.pydata.makeurl("rnginline.test", path)
    el = etree.XML(urlhandlers.pydata.dereference(url))

    propagated = datatypelibrary(copy.deepcopy(el))

    # Ensure we've not lost any elements
    assert len(list(el.iter())) == len(list(propagated.iter()))

    # Only data/value els have datatype library attrs
    assert propagated.xpath(
        "//rng:data|//rng:value", namespaces=NSMAP
    ) == propagated.xpath("//*[@datatypeLibrary]")

    # Ensure the resolved values match those we expect
    for el in propagated.xpath("//rng:data|//rng:value", namespaces=NSMAP):
        assert el.attrib["datatypeLibrary"] == el.attrib["{expected}expected"]
