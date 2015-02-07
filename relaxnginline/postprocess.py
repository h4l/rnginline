from relaxnginline.constants import NSMAP, RNG_DATA_TAG, RNG_VALUE_TAG


__all__ = ["datatypelibrary"]


class PropagateDatatypeLibraryPostProcess(object):
    """
    Implements the propagation part of simplification 4.3: datatypeLibrary
    attributes are resolved and explicitly set on each data and value element,
    then removed from all other elements.

    This can be used to work around libxml2 not resolving datatypeLibrary
    attributes from div elements:
        https://bugzilla.gnome.org/show_bug.cgi?id=744146
    """

    def lookup_datatypelibrary(self, element):
        while element is not None:
            if "datatypeLibrary" in element.attrib:
                return element.attrib["datatypeLibrary"]
            element = element.getparent()
        return ""

    def resolve_datatypelibrary(self, element):
        lib = self.lookup_datatypelibrary(element)
        element.attrib["datatypeLibrary"] = lib

    def postprocess(self, grammar):
        # Resolve the datatypeLibrary of all data and value elements
        for element in grammar.xpath("//rng:data|//rng:value", namespaces=NSMAP):
            self.resolve_datatypelibrary(element)

        # Strip datatypeLibrary from all other elements
        for element in grammar.iter():
            if (element.tag not in [RNG_DATA_TAG, RNG_VALUE_TAG]
                    and "datatypeLibrary" in element.attrib):
                del element.attrib["datatypeLibrary"]

        return grammar

    def __call__(self, grammar):
        return self.postprocess(grammar)


datatypelibrary = PropagateDatatypeLibraryPostProcess()
