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
        self.data = WeakKeyDictionary()

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
        return instance in self.data

    def __get__(self, instance, owner):
        value = self.data.get(instance, None)
        return value

    def __set__(self, instance, value):
        if self.is_required and value is None:
            self.check_validity(instance)
        self._check_type(value)
        self.data[instance] = value

    def _check_type(self, value):
        if isinstance(value, (list, set)):
            for v in value:
                self._check_type(v)
            return

        if not isinstance(value,  self.value_type):
            raise DataAttributeTypeError("{0} is not a {1}".format(value, self.value_type))


class StringAttribute(DataAttribute):
    def __init__(self, metadata):
        DataAttribute.__init__(self, metadata, str)


class IntegerAttribute(DataAttribute):
    def __init__(self, metadata):
        DataAttribute.__init__(metadata, int)


class EmailAttribute(DataAttribute):
    """ TODO: implement it """
    def __init__(self, metadata):
        super(self).__init__(metadata, str)

    def _check_type(self, value):
        raise NotImplementedError("TODO: implement it")
