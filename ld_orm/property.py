from exceptions import Exception
from .attribute import AttributeMetadata

class AlreadyDeclaredBasicTypeError(Exception):
    pass

class AlreadyGeneratedAttributeError(Exception):
    """
        Attribute generation occurs only once per SupportedProperty.
        You should not try to add metadata or regenerate after that.
    """
    pass


class SupportedProperty(object):
    """
        RDF property declared "supported by a RDF class"
    """
    def __init__(self, property_uri, supporter_class_uri, is_required=False, cardinality=None,
                 basic_type_uri=None):
        self._property_uri = property_uri
        self._supporter_class_uri = supporter_class_uri
        self._is_required = is_required
        # 1, 42, "*", "+"
        self._cardinality = cardinality
        self._basic_type_uri = basic_type_uri

        # Temporary list, before creating attributes
        self._tmp_attr_mds = []
        self._attributes = None

    @property
    def property_uri(self):
        """ Read-only """
        return self._property_uri

    @property
    def supporter_class_uri(self):
        """ Read-only """
        return self._supporter_class_uri

    @property
    def is_required(self):
        return self._is_required

    def declare_is_required(self):
        self._is_required = True

    @property
    def basic_type_uri(self):
        return self._basic_type_uri

    @basic_type_uri.setter
    def basic_type_uri(self, type_uri):
        if self._basic_type_uri and self._basic_type_uri != type_uri:
            raise AlreadyDeclaredBasicTypeError("New basic type %s for property %s (%s already defined)"
                                                %(basic_type,self._property_uri, self._basic_type_uri))
        self._basic_type_uri = ype_uri

    @property
    def attributes(self):
        if self._attributes is None:
            raise NotGeneratedAttributeError("Please generate them before accessing this attribute")
        return self._attributes

    def add_attribute_metadata(self, name, basic_type_uri=None, language=None, container=None,
                               reverse=None):
        """
            TODO: support:
                - the container variable
                - reverse property
        """
        if self._attributes:
           raise AlreadyGeneratedAttributeError("It is too late to add attribute metadata")

        if container:
            raise NotImplementedError("Not yet")

        if basic_type_uri:
            self._basic_type_uri = basic_type_uri

        if reverse:
            raise NotImplementedError("Reverse properties are not yet supported")

        #TODO: throw an error instead?
        assert(len([md for md in self._tmp_attr_mds
                    if md.name == name]) == 0)
        self._tmp_attr_mds.append(AttributeMetadata(name, self, language))

    def generate_attributes(self, attr_class_selector):
        """
            Can be called only once
        """
        if self._attributes:
            raise AlreadyGeneratedAttributeError()

        attr_cls = attr_class_selector.find_attribute_class(self)
        self._attributes = set([attr_cls(md) for md in self._tmp_attr_mds])
        self._tmp_attr_mds = []