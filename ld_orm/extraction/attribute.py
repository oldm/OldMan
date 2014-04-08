from .property import HydraPropertyExtractor
from .context import JsonLdContextAttributeMdExtractor
from ..attribute import StringAttribute, DataAttribute

class DataAttributeExtractor(object):
    """ Extracts Attribute objects for a given class.

        Extensible in two ways:
            1. Property extractors (new RDF vocabularies)
            2. Attribute md extractors (e.g. JSON-LD context)
            3. New Attribute classes for (through its attribute_class_selector):
              * Some specific properties (eg. foaf:mbox and EmailAttribute)
              * Some types, as defined in the JSON-LD context or the domain or range (eg. xsd:string)
    """

    def __init__(self, property_extractors=[], attr_md_extractors=[], use_hydra=True,
                 use_jsonld_context=True):
        self._class_selector = DataAttributeClassSelector()
        self._property_extractors = property_extractors
        self._attr_md_extractors = attr_md_extractors
        if use_hydra:
            self.add_property_extractor(HydraPropertyExtractor())
        if use_jsonld_context:
             self.add_attribute_md_extractor(JsonLdContextAttributeMdExtractor())

    @property
    def attribute_class_selector(self):
        return self._class_selector

    def add_attribute_md_extractor(self, attr_md_extractor):
        if attr_md_extractor not in self._attr_md_extractors:
            self._attr_md_extractors.append(attr_md_extractor)

    def add_property_extractor(self, property_extractor):
        if property_extractor not in self._property_extractors:
            self._property_extractors.append(property_extractor)

    def extract(self, class_uri, context_js, graph):
        # Supported properties
        properties = {}

        # Extracts and updates properties
        for property_extractor in self._property_extractors:
            properties = property_extractor.update(properties, class_uri, graph)

        # Updates properties with attribute metadata
        for md_extractor in self._attr_md_extractors:
            md_extractor.update(properties, context_js, graph)

        # Generates attributes
        attrs = []
        for property in properties.values():
            property.generate_attributes(self._class_selector)
            attrs += property.attributes

        # TODO: detects if attribute names are not unique
        return {a.name: a for a in attrs}


class DataAttributeClassSelector(object):

    def __init__(self, special_properties={}, include_default_basic_types=True):
        """
            TODO: enrich default basic types
        """
        self._special_properties = special_properties
        self._basic_types = {}
        if include_default_basic_types:
            #TODO: enrich it
            self._basic_types.update({"http://www.w3.org/2001/XMLSchema#string": StringAttribute})

    def add_special_property(self, property_uri, attr_class):
        self._special_properties[property_uri] = attr_class

    def add_basic_type(self, type_uri, attr_class):
        self._basic_types[type_uri] = attr_class

    def find_attribute_class(self, property):
        cls = self._special_properties.get(property.property_uri, None)
        # If not a special property
        if cls is None:
            cls = self._basic_types.get(property.basic_type_uri, DataAttribute)
        return cls

