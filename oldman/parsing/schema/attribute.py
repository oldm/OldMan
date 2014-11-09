from datetime import date, datetime, time
from decimal import Decimal

from oldman.parsing.schema.property import HydraPropertyExtractor
from oldman.parsing.schema.context import JsonLdContextAttributeMdExtractor
from oldman.validation.value_format import AnyValueFormat, IRIValueFormat, TypedValueFormat, EmailValueFormat
from oldman.validation.value_format import PositiveTypedValueFormat, NegativeTypedValueFormat
from oldman.validation.value_format import NonPositiveTypedValueFormat, NonNegativeTypedValueFormat
from oldman.validation.value_format import HexBinaryFormat
from oldman.common import OBJECT_PROPERTY


class OMAttributeExtractor(object):
    """Extracts :class:`~oldman.attribute.OMAttribute` objects from the schema and the JSON-LD context.

    Extensible in two ways:

        1. New :class:`~oldman.parsing.schema.property.OMPropertyExtractor` objects (new RDF vocabularies);
        2. New :class:`~oldman.parsing.schema.context.OMAttributeMdExtractor` objects (e.g. JSON-LD context);
        3. New :class:`~oldman.validation.value_format.ValueFormat` objects.
           See its :attr:`~oldman.parsing.schema.attribute.OMAttributeExtractor.value_format_registry` attribute.

    :param property_extractors: Defaults to `[]`.
    :param attr_md_extractors: Defaults to `[]`.
    :param use_hydra: Defaults to `True`.
    :param use_jsonld_context: Defaults to `True`.
    """

    def __init__(self, property_extractors=None, attr_md_extractors=None, use_hydra=True,
                 use_jsonld_context=True):
        self._value_format_registry = ValueFormatRegistry()
        self._property_extractors = list(property_extractors) if property_extractors else []
        self._attr_md_extractors = list(attr_md_extractors) if attr_md_extractors else []
        if use_hydra:
            self.add_property_extractor(HydraPropertyExtractor())
        if use_jsonld_context:
            self.add_attribute_md_extractor(JsonLdContextAttributeMdExtractor())

    @property
    def value_format_registry(self):
        """:class:`~oldman.parsing.schema.attribute.ValueFormatRegistry` object."""
        return self._value_format_registry

    def add_attribute_md_extractor(self, attr_md_extractor):
        """Adds a new :class:`~oldman.parsing.schema.context.OMAttributeMdExtractor` object."""
        if attr_md_extractor not in self._attr_md_extractors:
            self._attr_md_extractors.append(attr_md_extractor)

    def add_property_extractor(self, property_extractor):
        """Adds a new :class:`~oldman.parsing.schema.property.OMPropertyExtractor` object."""
        if property_extractor not in self._property_extractors:
            self._property_extractors.append(property_extractor)

    def extract(self, class_iri, type_iris, context_js, schema_graph, manager):
        """Extracts metadata and generates :class:`~oldman.property.OMProperty` and
        :class:`~oldman.attribute.OMAttribute` objects.

        :param class_iri: IRI of RDFS class of the future :class:`~oldman.model.Model` object.
        :param type_iris: Ancestry of the RDFS class.
        :param context_js: the JSON-LD context.
        :param schema_graph: :class:`rdflib.graph.Graph` object.
        :param manager: :class:`~oldman.resource.manager.ResourceManager` object.
        :return: `dict` of :class:`~oldman.attribute.OMAttribute` objects.
        """
        # Supported om_properties
        om_properties = {}

        # Extracts and updates om_properties
        for property_extractor in self._property_extractors:
            om_properties = property_extractor.update(om_properties, class_iri, type_iris, schema_graph, manager)

        # Updates om_properties with attribute metadata
        for md_extractor in self._attr_md_extractors:
            md_extractor.update(om_properties, context_js, schema_graph)

        # Generates attributes
        om_attrs = []
        for prop in om_properties.values():
            prop.generate_attributes(self._value_format_registry)
            om_attrs += prop.om_attributes

        # TODO: detects if attribute names are not unique
        return {a.name: a for a in om_attrs}


class ValueFormatRegistry(object):
    """Finds the :class:`~oldman.validation.value_format.ValueFormat` object that corresponds
    to a :class:`~oldman.attribute.OMAttributeMetadata` object.

    New :class:`~oldman.validation.value_format.ValueFormat` objects can be added, for supporting:

        1. Specific properties (eg. foaf:mbox and :class:`~oldman.validation.value_format.EmailValueFormat`);
        2. Other datatypes, as defined in the JSON-LD context or the RDFS domain or range (eg. xsd:string).

    :param special_properties: Defaults to `{}`.
    :param include_default_datatypes: Defaults to `True`.
    :param include_well_known_properties: Defaults to `True`.
    """

    def __init__(self, special_properties=None, include_default_datatypes=True,
                 include_well_known_properties=True):
        # TODO: enrich default datatypes
        self._special_properties = dict(special_properties) if special_properties else {}
        self._datatypes = {}
        if include_default_datatypes:
            #TODO: token, duration, gYearMonth, gYear, gMonthDay, gDay, gMonth (wait for rdflib support)
            #TODO: XMLLiteral and HTMLLiteral validation
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
                                    xsd + u'double': TypedValueFormat((float, int, long, Decimal)),
                                    xsd + u'hexBinary': HexBinaryFormat()})
            self._uri_format = IRIValueFormat()
            self._any_format = AnyValueFormat()
        if include_well_known_properties:
            email_value_format = EmailValueFormat()
            self.add_special_property(u"http://xmlns.com/foaf/0.1/mbox", email_value_format)
            self.add_special_property(u"http://schema.org/email", email_value_format)

    def add_special_property(self, property_iri, value_format):
        """Registers a :class:`~oldman.validation.value_format.ValueFormat` object for
        a given RDF property.

        :param property_iri: IRI of the RDF property.
        :param value_format: :class:`~oldman.validation.value_format.ValueFormat` object.
        """
        self._special_properties[property_iri] = value_format

    def add_datatype(self, datatype_iri, value_format):
        """Registers a :class:`~oldman.validation.value_format.ValueFormat` object for
        a given datatype.

        :param datatype_iri: IRI of the datatype.
        :param value_format: :class:`~oldman.validation.value_format.ValueFormat` object.
        """
        self._datatypes[datatype_iri] = value_format

    def find_value_format(self, attr_md):
        """Finds the :class:`~oldman.validation.value_format.ValueFormat` object that corresponds
        to a :class:`~oldman.attribute.OMAttributeMetadata` object.

        :param attr_md: :class:`~oldman.attribute.OMAttributeMetadata` object.
        :return: :class:`~oldman.validation.value_format.ValueFormat` object.
        """
        prop = attr_md.property

        value_format = self._special_properties.get(prop.iri, None)
        if value_format:
            return value_format

        # If not a special property but an ObjectProperty
        if prop.type == OBJECT_PROPERTY:
            return self._uri_format

        # If a DatatypeProperty
        return self._datatypes.get(attr_md.jsonld_type, self._any_format)