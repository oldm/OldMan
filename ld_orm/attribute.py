from exceptions import Exception
from collections import namedtuple
from weakref import WeakKeyDictionary


class DataAttributeTypeError(Exception):
    pass


class RequiredDataAttributeError(Exception):
    pass


DataAttributeMetadata = namedtuple("DataAttributeMetadata", ["name", "property", "language"])


class DataAttribute(object):

    def __init__(self, metadata, value_type=object):
        self.metadata = metadata
        self.value_type = value_type
        self._data = WeakKeyDictionary()
        # Non-saved former values
        self._former_values = WeakKeyDictionary()

    @property
    def is_required(self):
        return self.metadata.property.is_required

    @property
    def supported_property(self):
        return self.metadata.property

    @property
    def name(self):
        return self.metadata.name

    @property
    def other_attributes(self):
        """
            Attributes of the same property
        """
        return self.supported_property.attributes.difference([self])

    def is_valid(self, instance):
        try:
            self.check_validity(instance)
            return True
        except RequiredDataAttributeError:
            return False

    def check_validity(self, instance):
        if self.is_locally_satisfied(instance):
            return

        for other in self.other_attributes:
            if other.is_locally_satisfied(instance):
                return
        raise RequiredDataAttributeError(self.name)

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
        if not values:
            return None
        type_uri = self.supported_property.basic_type_uri
        language = self.metadata.language

        if isinstance(values, (list, set)):
            return [self._convert_serialized_value(v, type_uri, language)
                    for v in values]
        else:
            v = values
            return self._convert_serialized_value(v, type_uri, language)

    def _convert_serialized_value(self, value, type_uri, language):
        """ SPARQL encoding """
        if type_uri == "@id":
            return "<%s>" % value
        elif language:
            return '"%s"@%s' % (value, language)
        elif type_uri:
            return '"%s"^^<%s>' % (value, type_uri)
        else:
            return '"%s"' % value

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

        if not isinstance(value,  self.value_type):
            raise DataAttributeTypeError("{0} is not a {1}".format(value, self.value_type))


class StringAttribute(DataAttribute):
    def __init__(self, metadata):
        DataAttribute.__init__(self, metadata, (str, unicode))


class IntegerAttribute(DataAttribute):
    def __init__(self, metadata):
        DataAttribute.__init__(metadata, int)


class EmailAttribute(DataAttribute):
    """ TODO: implement it """
    def __init__(self, metadata):
        super(self).__init__(metadata, str)

    def _check_type(self, value):
        raise NotImplementedError("TODO: implement it")
