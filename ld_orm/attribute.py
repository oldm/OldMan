from collections import namedtuple
from weakref import WeakKeyDictionary
from .exceptions import LDAttributeTypeCheckError, RequiredPropertyError
from ld_orm.parsing.value import AttributeValueExtractorFromGraph


LDAttributeMetadata = namedtuple("DataAttributeMetadata", ["name", "property", "language", "jsonld_type",
                                                           "container", "reversed"])


class LDAttribute(object):
    """
        A LD attribute is a key-value pair.

        The key is the name of the attribute. Technically, the key is a JSON-LD term,
        namely "a short-hand string that expands to an IRI or a blank node identifier"
        ( http://www.w3.org/TR/json-ld/#dfn-term ) which corresponds here to a RDF property
        (see SupportedProperty).

        This value may be :
          - None
          - A Python equivalent for a RDF literal (double, string, date, etc.)
          - An URI
          - A collection (set, list and dict) of these types.

        TODO: explain further details.
    """

    CONTAINER_REQUIREMENTS = {'@set': set,
                              '@list': list,
                              #'@language': dict,
                              # '@index': dict,
                              None: object}

    def __init__(self, metadata, value_type=object):
        self._metadata = metadata
        self._value_type = value_type
        self._data = WeakKeyDictionary()
        # Non-saved former values
        self._former_values = WeakKeyDictionary()

        self._value_extractor = AttributeValueExtractorFromGraph(self)

        # TODO: support "@language" and "@index"
        if not self.container in [None, "@set", "@list"]:
            raise NotImplementedError("Container %s is not yet supported" % self.container)

        #TODO: support
        if self.reversed:
            raise NotImplementedError("Reversed properties (like %s) are not yet supported" % self.name)

    @property
    def is_required(self):
        return self._metadata.property.is_required

    @property
    def ld_property(self):
        return self._metadata.property

    @property
    def name(self):
        return self._metadata.name

    @property
    def language(self):
        return self._metadata.language

    @property
    def jsonld_type(self):
        return self._metadata.jsonld_type

    @property
    def reversed(self):
        return self._metadata.reversed

    @property
    def other_attributes(self):
        """
            Attributes of the same property
        """
        return self.ld_property.attributes.difference([self])

    def is_valid(self, instance):
        try:
            self.check_validity(instance)
            return True
        except RequiredPropertyError:
            return False

    @property
    def container(self):
        return self._metadata.container

    def check_validity(self, instance):
        if self.is_locally_satisfied(instance):
            return

        for other in self.other_attributes:
            if other.is_locally_satisfied(instance):
                return
        raise RequiredPropertyError(self.name)

    def is_locally_satisfied(self, instance):
        if not self.is_required:
            return True
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

    def pop_former_value_and_serialize_line(self, instance):
        """
            SPARQL-compatible version
            of pop_former_value()
        """
        values = self.pop_former_value(instance)
        return self.serialize_values_into_lines(values)

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
        if not values:
            return ""

        vs = values if isinstance(values, (list, set)) else [values]
        converted_values = [self._convert_serialized_value(v) for v in vs]

        property_uri = self.ld_property.uri
        lines = ""

        if self.container == "@list":
            list_value = "( " + " ".join(converted_values) + " )"
            serialized_values = [list_value]
        else:
            serialized_values = converted_values

        if self.reversed:
            assert(v.startswith("<") and v.endswith(">"))
            for v in serialized_values:
                lines += '  %s <%s> %s .\n' % (v, property_uri, "{0}")
        else:
            for v in serialized_values:
                lines += '  %s <%s> %s .\n' % ("{0}", property_uri, v)

        return lines

    def update_from_graph(self, instance, sub_graph, storage_graph):
        values = self._value_extractor.extract_values(instance, sub_graph, storage_graph)

        if values:
            setattr(instance, self.name, values)
            # Clears "None" former value
            self.pop_former_value(instance)

    def _convert_serialized_value(self, value):
        """
            SPARQL encoding
        """
        jsonld_type = self.jsonld_type
        language = self.language
        if jsonld_type == "@id":
            return "<%s>" % value
        elif language:
            return '"%s"@%s' % (value, language)
        elif jsonld_type:
            return '"%s"^^<%s>' % (value, jsonld_type)
        # Should we really define unknown types as string?
        else:
            raise NotImplementedError("Untyped JSON-LD value are not (yet?) supported")
            #return '"%s"' % value

    def __get__(self, instance, owner):
        value = self._data.get(instance, None)
        return value

    def __set__(self, instance, value):
        # None value are always allowed
        # (at assignment time)
        if not value is None:
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
        required_container_type = LDAttribute.CONTAINER_REQUIREMENTS[self.container]
        if not isinstance(value, required_container_type):
            raise LDAttributeTypeCheckError("A container (%s) was expected instead of %s"
                                            % (required_container_type, type(value)))
        if isinstance(value, (list, set, dict)):
            self._check_container(value)
        else:
            self._check_value(value)

    def _check_value(self, v):
        if v and not isinstance(v,  self._value_type):
            raise LDAttributeTypeCheckError("{0} is not a {1}".format(v, self._value_type))

    def _check_container(self, value):
        if not self.container:
            #TODO: replaces by a log alert
            print "Warning: no container declared for %s" % self.name

            # List declaration is required (default: set)
            # TODO: what about dict?
            if isinstance(value, list):
                raise LDAttributeTypeCheckError("Undeclared list %s assigned to %s ."
                                                "For using a list, '@container': '@list' must be declared"
                                                "in the JSON-LD context." % (value, self.name))

        vs = value.values() if isinstance(value, dict) else value
        for v in vs:
            self._check_value(v)


class ObjectLDAttribute(LDAttribute):
    """
        TODO: validate that the value is an URI
    """
    def __init__(self, metadata):
        LDAttribute.__init__(self, metadata, (str, unicode))

    def __get__(self, instance, owner):
        uris = LDAttribute.__get__(self, instance, None)
        if isinstance(uris, (list, set)):
            # Returns a generator
            return (type(instance).objects.get_any(uri)
                    for uri in uris)
        elif isinstance(uris, dict):
            raise NotImplementedError("Should we implement it?")
        elif uris:
            return type(instance).objects.get_any(uris)
        else:
            return None

    def __set__(self, instance, value):
        from .model import Model
        f = lambda x: x.id if isinstance(x, Model) else x

        if isinstance(value, set):
            values = {f(v) for v in value}
        elif isinstance(value, list):
            values = [f(v) for v in value]
        elif isinstance(value, dict):
            raise NotImplementedError("Dict are not yet supported")
        else:
            values = value
        LDAttribute.__set__(self, instance, values)


class StringLDAttribute(LDAttribute):
    def __init__(self, metadata):
        LDAttribute.__init__(self, metadata, (str, unicode))


class IntegerLDAttribute(LDAttribute):
    def __init__(self, metadata):
        LDAttribute.__init__(metadata, int)


class EmailLDAttribute(StringLDAttribute):
    """ TODO: implement it """
    def __init__(self, metadata):
        super(self).__init__(metadata, str)

    def check_value(self, value):
        raise NotImplementedError("TODO: implement it")
