from exceptions import Exception
from collections import namedtuple
from weakref import WeakKeyDictionary


class AttributeTypeError(Exception):
    pass


class RequiredAttributeError(Exception):
    pass


AttributeMetadata = namedtuple("AttributeMetadata", ["name", "property", "language"])


class Attribute(object):

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
        except RequiredAttributeError:
            return False

    def check_validity(self, instance):
        if self.is_locally_satisfied(instance):
            return

        for other in self.other_attributes:
            if other.is_locally_satisfied(instance):
                return
        raise RequiredAttributeError(self.name)

    def is_locally_satisfied(self, instance):
        if not self.is_required:
            return True
        return instance in self.data

    def __get__(self, instance, owner):
        value = self.data.get(instance, None)
        # TODO: keep it? Should have been detected earlier
        if self.is_required and value is None:
            self.check_validity(instance)
        return value

    def __set__(self, instance, value):
        if self.is_required and value is None:
            self.check_validity(instance)
        self._check_type(value)
        self.data[instance] = value

    def _check_type(self, value):
        if not isinstance(value,  self.value_type):
            raise AttributeTypeError("{0} is not a {1}".format(value, self.value_type))


class StringAttribute(Attribute):
    def __init__(self, metadata):
        Attribute.__init__(self, metadata, str)


class IntegerAttribute(Attribute):
    def __init__(self, metadata):
        Attribute.__init__(metadata, int)


class EmailAttribute(Attribute):
    """ TODO: implement it """
    def __init__(self, metadata):
        super(self).__init__(metadata, str)

    def _check_type(self, value):
        raise NotImplementedError("TODO: implement it")
