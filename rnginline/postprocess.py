from typing import Sequence

from lxml import etree
from typing_extensions import Final, Protocol

from rnginline.constants import NSMAP, RNG_DATA_TAG, RNG_VALUE_TAG

__all__ = ["datatypelibrary"]

_lookup_datatype_library: Final = etree.XPath(
    "string(ancestor-or-self::*[@datatypeLibrary][position()=1]" "/@datatypeLibrary)"
)
_data_value_els: Final = etree.XPath("//rng:data|//rng:value", namespaces=NSMAP)


class PostProcessor(Protocol):
    def postprocess(self, grammar: etree._Element) -> etree._Element:
        ...


class PropagateDatatypeLibraryPostProcess(PostProcessor):
    """
    Implements the propagation part of simplification 4.3: datatypeLibrary
    attributes are resolved and explicitly set on each data and value element,
    then removed from all other elements.

    This can be used to work around `libxml2 not resolving datatypeLibrary
    attributes from div elements <libxml2 bug>`_.

    .. _libxml2 bug: https://bugzilla.gnome.org/show_bug.cgi?id=744146
    """

    def lookup_datatypelibrary(self, element: etree._Element) -> str:
        lib = _lookup_datatype_library(element)
        assert isinstance(lib, str)
        return lib

    def resolve_datatypelibrary(self, element: etree._Element) -> None:
        lib = self.lookup_datatypelibrary(element)
        element.attrib["datatypeLibrary"] = lib

    def postprocess(self, grammar: etree._Element) -> etree._Element:
        # Resolve the datatypeLibrary of all data and value elements
        for element in _data_value_els(grammar):
            self.resolve_datatypelibrary(element)

        # Strip datatypeLibrary from all other elements
        for element in grammar.iter():
            if (
                element.tag not in [RNG_DATA_TAG, RNG_VALUE_TAG]
                and "datatypeLibrary" in element.attrib
            ):
                del element.attrib["datatypeLibrary"]

        return grammar

    def __call__(self, grammar: etree._Element) -> etree._Element:
        return self.postprocess(grammar)


datatypelibrary: Final = PropagateDatatypeLibraryPostProcess()
"""
The default instance of :py:class:`PropagateDatatypeLibraryPostProcess`
"""


def get_default_postprocessors() -> Sequence[PostProcessor]:
    """
    Get a list containing the default postprocessor objects.

    Currently contains just :py:data:`datatypelibrary`.
    """
    # For compatibility with libxml2
    return [datatypelibrary]
