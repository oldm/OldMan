from ld_orm.parsing.schema.property import HydraPropertyExtractor
from ld_orm.parsing.schema.context import JsonLdContextAttributeMdExtractor
from ld_orm.value_format import StringValueFormat, AnyValueFormat, URIValueFormat, BooleanValueFormat
from ld_orm.property import PropertyType


class LDAttributeExtractor(object):
    """ Extracts LDAttribute objects for a given class.

        Extensible in two ways:
            1. Property extractors (new RDF vocabularies)
            2. Attribute md extractors (e.g. JSON-LD context)
            3. New Attribute classes for (through its attribute_class_selector):
              * Some specific properties (eg. foaf:mbox and EmailAttribute)
              * Some types, as defined in the JSON-LD context or the domain or range (eg. xsd:string)
    """

    def __init__(self, property_extractors=[], attr_md_extractors=[], use_hydra=True,
                 use_jsonld_context=True):
        self._class_selector = ValueFormatSelector()
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
        for prop in properties.values():
            prop.generate_attributes(self._class_selector)
            attrs += prop.attributes

        # TODO: detects if attribute names are not unique
        return {a.name: a for a in attrs}


class ValueFormatSelector(object):

    def __init__(self, special_properties={}, include_default_datatypes=True):
        """
            TODO: enrich default datatypes
        """
        self._special_properties = special_properties
        self._datatypes = {}
        if include_default_datatypes:
            #TODO: enrich it
            xsd = "http://www.w3.org/2001/XMLSchema#"
            self._datatypes.update({xsd + "string": StringValueFormat(),
                                    xsd + "boolean": BooleanValueFormat(),
                                   })
            self._uri_format = URIValueFormat()
            self._any_format = AnyValueFormat()

    def add_special_property(self, property_uri, value_format):
        self._special_properties[property_uri] = value_format

    def add_datatype(self, type_uri, value_format):
        self._datatypes[type_uri] = value_format

    def find_value_format(self, attr_md):
        prop = attr_md.property

        value_format = self._special_properties.get(prop.uri, None)
        if value_format:
            return value_format

        # If not a special property but an ObjectProperty
        if prop.type == PropertyType.ObjectProperty:
            return self._uri_format

        # If a DatatypeProperty
        return self._datatypes.get(attr_md.jsonld_type, self._any_format)

