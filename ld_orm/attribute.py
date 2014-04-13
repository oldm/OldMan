from exceptions import Exception
from collections import namedtuple
from weakref import WeakKeyDictionary
from ld_orm.property import PropertyType


class LDAttributeTypeError(Exception):
    pass


class RequiredLDAttributeError(Exception):
    pass


LDAttributeMetadata = namedtuple("DataAttributeMetadata", ["name", "property", "language", "jsonld_type"])


class LDAttribute(object):

    def __init__(self, metadata, value_type=object):
        self._metadata = metadata
        self._value_type = value_type
        self._data = WeakKeyDictionary()
        # Non-saved former values
        self._former_values = WeakKeyDictionary()

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
    def other_attributes(self):
        """
            Attributes of the same property
        """
        return self.ld_property.attributes.difference([self])

    def is_valid(self, instance):
        try:
            self.check_validity(instance)
            return True
        except RequiredLDAttributeError:
            return False

    def check_validity(self, instance):
        if self.is_locally_satisfied(instance):
            return

        for other in self.other_attributes:
            if other.is_locally_satisfied(instance):
                return
        raise RequiredLDAttributeError(self.name)

    def is_locally_satisfied(self, instance):
        if not self.is_required:
            return True
        return instance in self._data

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

    def pop_serialized_former_value(self, instance):
        """
            SPARQL-compatible version
            of pop_former_value()
        """
        values = self.pop_former_value(instance)
        return self.serialize_values(values)


    def get_serialized_value(self, instance):
        """
            Serialized in a SPARQL-compatible way
        """
        values = self._data.get(instance, None)
        return self.serialize_values(values)

    def serialize_values(self, values):
        """
            Each value is returned as a SPARQL encoded string
        """
        if not values:
            return None

        #TODO: manage container
        if isinstance(values, (list, set)):
            return [self._convert_serialized_value(v)
                    for v in values]
        else:
            return self._convert_serialized_value(values)

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
        self._check_type(value)

        # Former value (if not already in cache)
        # (robust to multiple changes before saving
        if not instance in self._former_values:
            # May be None (trick!)
            former_value = self._data.get(instance)
            self._former_values[instance] = former_value

        self._data[instance] = value

    def _check_type(self, value):
        if isinstance(value, (list, set)):
            for v in value:
                self._check_type(v)
            return

        if not isinstance(value,  self._value_type):
            raise LDAttributeTypeError("{0} is not a {1}".format(value, self._value_type))


class ObjectLDAttribute(LDAttribute):
    """
        TODO: validate that the value is an URI
    """
    def __init__(self, metadata):
        LDAttribute.__init__(self, metadata, (str, unicode))


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

    def _check_type(self, value):
        raise NotImplementedError("TODO: implement it")
