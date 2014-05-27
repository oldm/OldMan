import logging
from collections import namedtuple
from weakref import WeakKeyDictionary
from rdflib import Literal
from .exception import OMAttributeTypeCheckError, OMRequiredPropertyError, OMReadOnlyAttributeError, OMEditError
from oldman.parsing.value import AttributeValueExtractorFromGraph
from oldman.validation.value_format import ValueFormatError
from oldman.iri import skolemize


OMAttributeMetadata = namedtuple("OMAttributeMetadata", ["name", "property", "language", "jsonld_type",
                                                           "container", "reversed"])


class OMAttribute(object):
    """
    An :class:`~oldman.attribute.OMAttribute` object corresponds
    to a JSON-LD term that refers to a RDF property.

    Technically, the name of the :class:`~oldman.attribute.OMAttribute` object is a JSON-LD term,
    namely *"a short-hand string that expands to an IRI or a blank node identifier"*
    (cf. `the JSON-LD standard <http://www.w3.org/TR/json-ld/#dfn-term>`_) which corresponds here to a RDF property
    (see :class:`~oldman.property.OMProperty`).

    In JSON-LD, the same RDF property may correspond to multiple JSON-LD terms that have different metadata.
    For instance, a foaf:Person resource may have two attributes for its bio in English and in French.
    Look at the quickstart example for seeing it in practise.

    An :class:`~oldman.attribute.OMAttribute` object manages the values of every
    :class:`~oldman.resource.Resource` object that depends on a given :class:`~oldman.model.Model` object.

    Each value may be :

      - `None`;
      - The Python equivalent for a RDF literal (double, string, date, etc.);
      - An IRI ;
      - A collection (set, list and dict) of these types.

    :param manager: :class:`~oldman.management.manager.ResourceManager` object.
    :param metadata: :class:`~oldman.attribute.OMAttributeMetadata` object.
    :param value_format: :class:`~oldman.validation.value_format.ValueFormat` object
                         that validates the format of values and converts RDF values
                         into regular Python objects.
    """

    _CONTAINER_REQUIREMENTS = {'@set': set,
                               '@list': list,
                               '@language': dict,
                               #'@index': dict,
                               None: object}

    def __init__(self, manager, metadata, value_format):
        self._manager = manager
        self._metadata = metadata
        self._value_format = value_format
        self._data = WeakKeyDictionary()
        # Non-saved former values
        self._former_values = WeakKeyDictionary()

        self._value_extractor = AttributeValueExtractorFromGraph(self)

        # TODO: support "@index"
        if not self.container in [None, "@set", "@list", "@language"]:
            raise NotImplementedError(u"Container %s is not yet supported" % self.container)

        #TODO: support
        if self.reversed:
            raise NotImplementedError(u"Reversed properties (like %s) are not yet supported" % self.name)

    @property
    def is_required(self):
        """`True` if its property is required."""
        return self._metadata.property.is_required

    @property
    def is_read_only(self):
        """`True` if the property cannot be modified by regular end-users."""
        return self._metadata.property.is_read_only

    @property
    def is_write_only(self):
        """`True` if the property cannot be accessed by regular end-users."""
        return self._metadata.property.is_write_only

    @property
    def om_property(self):
        """:class:`~oldman.property.OMProperty` to which it belongs."""
        return self._metadata.property

    @property
    def name(self):
        """Its name as an attribute."""
        return self._metadata.name

    @property
    def language(self):
        """Its language if localized."""
        return self._metadata.language

    @property
    def manager(self):
        """Its :class:`~oldman.management.manager.ResourceManager` object."""
        return self._manager

    @property
    def jsonld_type(self):
        """JSON-LD type (datatype IRI or JSON-LD keyword). May be `None`."""
        return self._metadata.jsonld_type

    @property
    def reversed(self):
        """`True` if the object and subject in RDF triples should be reversed."""
        return self._metadata.reversed

    @property
    def other_attributes(self):
        """ Other :class:`~oldman.attribute.OMAttribute` objects of the same property.
        """
        return self.om_property.om_attributes.difference([self])

    @property
    def container(self):
        """JSON-LD container (`"@set"`, `"@list"`, `"@language"` or `"@index"`).
        May be `None`.
        """
        return self._metadata.container

    @property
    def value_format(self):
        """:class:`~oldman.validation.value_format.ValueFormat` object that validates
        the format of values and converts RDF values into regular Python objects.
        """
        return self._value_format

    def is_valid(self, instance, is_end_user=True):
        """Tests if the attribute value assigned to a resource is valid.

        See :func:`~oldman.attribute.OMAttribute.check_validity` for further details.

        :return: `False` if the value assigned to the resource is invalid and `True` otherwise.
        """
        try:
            self.check_validity(instance, is_end_user)
            return True
        except OMEditError:
            return False

    def check_validity(self, instance, is_end_user=True):
        """Raises an :class:`~oldman.exception.OMEditError` exception if
        the attribute value assigned to a resource is invalid.

        :param instance: :class:`~oldman.resource.Resource` object.
        :param is_end_user: `False` when an authorized user (not a regular end-user)
                             wants to force some rights. Defaults to `True`.
        """
        self._check_local_constraints(instance, is_end_user)
        self._check_requirement(instance)

    def _check_local_constraints(self, instance, is_end_user):
        #Read-only constraint
        if is_end_user and self.is_read_only and self.has_new_value(instance):
            raise OMReadOnlyAttributeError("Attribute %s is not editable by end users" % self.name)

    def _check_requirement(self, instance):
        if (not self.om_property.is_required) or self.has_value(instance):
            return
        for other in self.other_attributes:
            if other.has_value(instance):
                return
        raise OMRequiredPropertyError(self.name)

    def has_value(self, instance):
        return self._data.get(instance) is not None

    def has_new_value(self, instance):
        return instance in self._former_values

    def pop_former_value(self, instance):
        """
            To be called before saving the instance.
            Pops out the former value that has been saved
        """
        if instance in self._former_values:
            return self._former_values.pop(instance)
        return None

    def serialize_current_value_into_line(self, instance):
        """
            Serialized in a SPARQL-compatible way
        """
        values = self._data.get(instance, None)
        return self.serialize_values_into_lines(values)

    def serialize_values_into_lines(self, values):
        """
            Each value is returned as a SPARQL encoded string
        """
        if values is None:
            return ""

        vs = values if isinstance(values, (list, set, dict)) else [values]
        if isinstance(vs, dict):
            converted_values = [self._encode_value(v, language) for language, v in vs.iteritems()]
        else:
            converted_values = [self._encode_value(v) for v in vs]

        property_uri = self.om_property.iri
        lines = ""

        if self.container == "@list":
            #list_value = u"( " + u" ".join(converted_values) + u" )"
            # List with skolemized nodes
            first_node = "<%s>" % skolemize()
            node = first_node
            for v in converted_values:
                lines += u'  %s rdf:first %s .\n' % (node, v)
                previous_node = node
                node = "<%s>" % skolemize()
                lines += u'  %s rdf:rest %s .\n' % (previous_node, node)
            lines += u'  %s rdf:rest rdf:nil .\n' % node
            serialized_values = [first_node]
        else:
            serialized_values = converted_values

        if self.reversed:
            assert(v.startswith(u"<") and v.endswith(u">"))
            for v in serialized_values:
                lines += u'  %s <%s> %s .\n' % (v, property_uri, u"{0}")
        else:
            for v in serialized_values:
                lines += u'  %s <%s> %s .\n' % (u"{0}", property_uri, v)

        return lines

    def update_from_graph(self, instance, sub_graph, storage_graph, initial=False):
        values = self._value_extractor.extract_values(instance, sub_graph, storage_graph)

        setattr(instance, self.name, values)
        if initial:
            # Clears "None" former value
            self.pop_former_value(instance)

    def _encode_value(self, value, language=None):
        """
            SPARQL encoding
        """
        jsonld_type = self.jsonld_type
        if language is None:
            language = self.language
        if jsonld_type == "@id":
            return u"<%s>" % value
        elif language:
            return u'"%s"@%s' % (Literal(value), language)
        elif jsonld_type:
            return u'"%s"^^<%s>' % (Literal(value), jsonld_type)
        # Should we really define unknown types as string?
        else:
            raise NotImplementedError(u"Untyped JSON-LD value are not (yet?) supported")

    def get(self, instance):
        value = self._data.get(instance, None)
        return value

    def set(self, instance, value):
        # Even if None
        self.check_value(value)

        # Empty container -> None
        if isinstance(value, (list, set, dict)) and len(value) == 0:
            value = None

        # Former value (if not already in cache)
        # (robust to multiple changes before saving)
        if not instance in self._former_values:
            # May be None (trick!)
            former_value = self._data.get(instance)
            if former_value != value:
                self._former_values[instance] = former_value

        self._data[instance] = value

    def check_value(self, value):
        # None value are always allowed
        # (at assignment time)
        if value is None:
            return

        required_container_type = OMAttribute._CONTAINER_REQUIREMENTS[self.container]
        if not isinstance(value, required_container_type):
            raise OMAttributeTypeCheckError(u"A container (%s) was expected instead of %s"
                                            % (required_container_type, type(value)))
        try:
            if isinstance(value, (list, set, dict)):
                self._check_container(value)
            else:
                self._value_format.check_value(value)
        except ValueFormatError as e:
            raise OMAttributeTypeCheckError(unicode(e))

    def _check_container(self, value):
        if not self.container:
            logger = logging.getLogger(__name__)
            logger.warn("No container declared for %s" % self.name)

            # List declaration is required (default: set)
            # TODO: what about dict?
            if isinstance(value, list):
                raise OMAttributeTypeCheckError(u"Undeclared list %s assigned to %s ."
                                                u"For using a list, '@container': '@list' must be declared"
                                                u"in the JSON-LD context." % (value, self.name))

        vs = value.values() if isinstance(value, dict) else value
        for v in vs:
            self._value_format.check_value(v)


class ObjectOMAttribute(OMAttribute):

    def __init__(self, manager, metadata, value_format):
        OMAttribute.__init__(self, manager, metadata, value_format)

    def get(self, instance):
        iris = OMAttribute.get(self, instance)
        if isinstance(iris, (list, set)):
            # Returns a generator
            return (self.manager.get(id=iri) for iri in iris)
        elif isinstance(iris, dict):
            raise NotImplementedError(u"Should we implement it?")
        elif iris is not None:
            return self.manager.get(id=iris)
        else:
            return None

    def set(self, instance, value):
        from .resource import Resource
        f = lambda x: x.id if isinstance(x, Resource) else x

        if isinstance(value, set):
            values = {f(v) for v in value}
        elif isinstance(value, list):
            values = [f(v) for v in value]
        elif isinstance(value, dict):
            if self.container == "@index":
                raise NotImplementedError(u"Index maps are not yet supported")
            else:
                raise OMAttributeTypeCheckError(u"Index maps must be declared. Other dict structures "
                                                u"are not supported for objects.")
        else:
            values = f(value)
        OMAttribute.set(self, instance, values)