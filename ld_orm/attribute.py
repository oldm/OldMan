from collections import namedtuple
from weakref import WeakKeyDictionary
from .exceptions import LDAttributeTypeCheckError, RequiredPropertyError


LDAttributeMetadata = namedtuple("DataAttributeMetadata", ["name", "property", "language", "jsonld_type",
                                                           "container", "reversed"])


class LDAttribute(object):

    CONTAINER_REQUIREMENTS = {'@set': set,
                              '@list': list,
                            # '@language': dict,
                            # '@index': dict,
                              None: object,
                             }

    def __init__(self, metadata, value_type=object):
        self._metadata = metadata
        self._value_type = value_type
        self._data = WeakKeyDictionary()
        # Non-saved former values
        self._former_values = WeakKeyDictionary()

        # TODO: support "@list", "@language" and "@index"
        if not self.container in [None, "@set"]:
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
        return self._data.get(instance) != None

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
        serialized_values = [self._convert_serialized_value(v)
                             for v in vs]

        property_uri = self.ld_property.uri
        lines = ""

        if self.reversed:
            assert(v.startswith("<") and v.endswith(">"))
            for v in serialized_values:
                lines += '  %s <%s> %s .\n' %(v, property_uri, "{0}")
        else:
            for v in serialized_values:
                lines += '  %s <%s> %s .\n' %("{0}", property_uri, v)

        return lines



    def _convert_serialized_value(self, value):
        """
            SPARQL encoding

             TODO: replace with line encoding
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
        if self.is_required and value is None:
            self.check_validity(instance)
        self.check_value(value)

        # Former value (if not already in cache)
        # (robust to multiple changes before saving)
        if not instance in self._former_values:
            # May be None (trick!)
            former_value = self._data.get(instance)
            self._former_values[instance] = former_value

        self._data[instance] = value

    def check_value(self, value):
        required_container_type = LDAttribute.CONTAINER_REQUIREMENTS[self.container]
        if not isinstance(value, required_container_type):
            raise LDAttributeTypeCheckError("A container (%s) was expected instead of %s"
                                       % (required_container_type, type(value)))

        if isinstance(value, (list, set, dict)):
            if not self.container:
                #TODO: replaces by a log alert
                print "Warning: no container declared for %s" % self.name

            vs = value.values() if isinstance(value, dict) else value
            for v in vs:
                self._check_value(v)
            return
        self._check_value(value)

    def _check_value(self, v):
        if v and not isinstance(v,  self._value_type):
            raise LDAttributeTypeCheckError("{0} is not a {1}".format(v, self._value_type))


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
        f = lambda v: v._id if isinstance(v, Model) else v

        if isinstance(value, set):
            values = set([f(v) for v in value])
        elif isinstance(value, list):
            values = set([f(v) for v in value])
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
