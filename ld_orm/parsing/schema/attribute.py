from datetime import date, datetime, time
from decimal import Decimal
from ld_orm.parsing.schema.property import HydraPropertyExtractor
from ld_orm.parsing.schema.context import JsonLdContextAttributeMdExtractor
from ld_orm.value_format import AnyValueFormat, IRIValueFormat, TypedValueFormat, EmailValueFormat
from ld_orm.value_format import PositiveTypedValueFormat, NegativeTypedValueFormat
from ld_orm.value_format import NonPositiveTypedValueFormat, NonNegativeTypedValueFormat
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

    def __init__(self, property_extractors=None, attr_md_extractors=None, use_hydra=True,
                 use_jsonld_context=True):
        self._class_selector = ValueFormatSelector()
        self._property_extractors = list(property_extractors) if property_extractors else []
        self._attr_md_extractors = list(attr_md_extractors) if attr_md_extractors else []
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

    def extract(self, class_uri, type_uris, context_js, graph):
        # Supported properties
        properties = {}

        # Extracts and updates properties
        for property_extractor in self._property_extractors:
            properties = property_extractor.update(properties, class_uri, type_uris, graph)

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

    def __init__(self, special_properties=None, include_default_datatypes=True,
                 include_well_known_properties=True):
        """
            TODO: enrich default datatypes
        """
        self._special_properties = dict(special_properties) if special_properties else {}
        self._datatypes = {}
        if include_default_datatypes:
            #TODO: token, duration, gYearMonth, gYear, gMonthDay, gDay, gMonth (wait for rdflib support)
            #TODO: XMLLiteral and HTMLLiteral validation
            #TODO: hexBinary
            xsd = u"http://www.w3.org/2001/XMLSchema#"
            self._datatypes.update({xsd + u"string": TypedValueFormat((str, unicode)),
                                    xsd + u"boolean": TypedValueFormat(bool),
                                    xsd + u"date": TypedValueFormat(date),
                                    xsd + u"dateTime": TypedValueFormat(datetime),
                                    xsd + u"time": TypedValueFormat(time),
                                    #TODO: improve validation
                                    xsd + u'normalizedString': TypedValueFormat((str, unicode)),
                                    #TODO: improve language validation
                                    xsd + u'language': TypedValueFormat((str, unicode)),
                                    xsd + u'decimal': TypedValueFormat((Decimal, int, long, float)),
                                    xsd + u'integer': TypedValueFormat((int, long)),
                                    xsd + u'nonPositiveInteger': NonPositiveTypedValueFormat(int),
                                    xsd + u'long': TypedValueFormat((int, long)),
                                    xsd + u'nonNegativeInteger': NonNegativeTypedValueFormat(int),
                                    xsd + u'negativeInteger': NegativeTypedValueFormat(int),
                                    xsd + u'int': TypedValueFormat((long, int)),
                                    xsd + u'unsignedLong': NonNegativeTypedValueFormat((long, int)),
                                    xsd + u'positiveInteger': PositiveTypedValueFormat(int),
                                    xsd + u'short': TypedValueFormat(int),
                                    xsd + u'unsignedInt': NonNegativeTypedValueFormat((int, long)),
                                    xsd + u'byte': TypedValueFormat(int),
                                    xsd + u'unsignedShort': NonNegativeTypedValueFormat(int),
                                    xsd + u'unsignedByte': NonNegativeTypedValueFormat(int),
                                    xsd + u'float': TypedValueFormat((float, int, long, Decimal)),
                                    xsd + u'double': TypedValueFormat((float, int, long, Decimal))})
            self._uri_format = IRIValueFormat()
            self._any_format = AnyValueFormat()
        if include_well_known_properties:
            email_value_format = EmailValueFormat()
            self.add_special_property(u"http://xmlns.com/foaf/0.1/mbox", email_value_format)
            self.add_special_property(u"http://schema.org/email", email_value_format)

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