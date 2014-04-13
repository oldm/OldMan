from exceptions import Exception
from enum import Enum
from .attribute import LDAttributeMetadata


class AlreadyDeclaredDatatypeError(Exception):
    pass


class AlreadyDeclaredPropertyTypeError(Exception):
    pass


class AlreadyGeneratedAttributeError(Exception):
    """
        Attribute generation occurs only once per SupportedProperty.
        You should not try to add metadata or regenerate after that.
    """
    pass


class PropertyType(Enum):
     UnknownPropertyType = 1
     DatatypeProperty = 2
     ObjectProperty = 3


class LDProperty(object):
    """
        RDF property declared "supported by a RDF class"
    """
    def __init__(self, property_uri, supporter_class_uri, is_required=False, cardinality=None,
                 property_type=PropertyType.UnknownPropertyType, domains=set([]), ranges=set([])):
        self._uri = property_uri
        self._supporter_class_uri = supporter_class_uri
        self._is_required = is_required
        # 1, 42, "*", "+"
        self._cardinality = cardinality
        self._type = property_type
        self._ranges = ranges
        self._domains = domains

        # Temporary list, before creating attributes
        self._tmp_attr_mds = []
        self._attributes = None

    @property
    def uri(self):
        """ Read-only """
        return self._uri

    @property
    def type(self):
        """
            Read-only
            Returns a PropertyType
        """
        return self._type

    @type.setter
    def type(self, property_type):
        if self._type != PropertyType.UnknownPropertyType:
            if self._type != property_type:
                raise AlreadyDeclaredPropertyTypeError("Already declared as %s so cannot also be a %s "
                                                        %(self._type,  property_type))
            return
        self._type = property_type

    @property
    def supporter_class_uri(self):
        """ Read-only """
        return self._supporter_class_uri

    @property
    def is_required(self):
        return self._is_required

    def declare_is_required(self):
        """
            is_required is set to True
        """
        self._is_required = True

    @property
    def ranges(self):
        return self._ranges

    def add_range(self, p_range):
        # Detects XSD
        if p_range.startswith("http://www.w3.org/2001/XMLSchema#"):
            self.type = PropertyType.DatatypeProperty

        if self.type == PropertyType.DatatypeProperty and (not p_range in self._ranges) \
                and len(self._ranges) >=1:
            raise AlreadyDeclaredDatatypeError("Property datatype can only be specified once")

        self._ranges.add(p_range)

    @property
    def domains(self):
        return self._domains

    def add_domain(self, domain):
        # Detects XSD
        if range.startswith("http://www.w3.org/2001/XMLSchema#"):
            #TODO: find a better error type
            raise Exception("Domain cannot have a litteral datatype")
        self._domains.add(domain)

    @property
    def default_datatype(self):
        """
            May return None (if ObjectProperty or if not defined)
        """
        if self._type == PropertyType.DatatypeProperty and len(self._ranges) >= 1:
            # Should be one
            return list(self._ranges)[0]
        return None

    @property
    def attributes(self):
        if self._attributes is None:
            raise NotGeneratedAttributeError("Please generate them before accessing this attribute")
        return self._attributes

    def add_attribute_metadata(self, name, jsonld_type=None, language=None, container=None,
                               reverse=None):
        """
            TODO: support:
                - the container variable
                - reverse property
        """
        if self._attributes:
           raise AlreadyGeneratedAttributeError("It is too late to add attribute metadata")
        if jsonld_type:
            if jsonld_type == "@id":
                self.type = PropertyType.ObjectProperty
            else:
                self.type = PropertyType.DatatypeProperty
                if (not jsonld_type in self._ranges) and len(self._ranges) >=1:
                    raise AlreadyDeclaredDatatypeError("Attribute %s cannot have a different datatype"
                                                       "(%s) than the property's one (%s)" % (name, jsonld_type,
                                                        list(self._ranges)[0]))
        # If no datatype defined, use the property one
        else:
            #TODO: warns because this is a bad practice
            #(harder to parse for a JSON-LD client)
            if self.type == PropertyType.ObjectProperty:
                jsonld_type = "@id"
            elif self.type == PropertyType.DatatypeProperty:
                jsonld_type = self.default_datatype
            else:
                #TODO: find a better Exception type
                raise NotImplementedError("Untyped JSON-LD value are not (yet?) supported")

        #TODO: throw an error instead?
        assert(len([md for md in self._tmp_attr_mds
                    if md.name == name]) == 0)
        self._tmp_attr_mds.append(LDAttributeMetadata(name, self, language, jsonld_type, container,
                                                      reverse == True))

    def generate_attributes(self, attr_class_selector):
        """
            Can be called only once
        """
        if self._attributes:
            raise AlreadyGeneratedAttributeError()

        self._attributes = set()
        for md in self._tmp_attr_mds:
            attr_cls = attr_class_selector.find_attribute_class(md)
            self._attributes.add(attr_cls(md))

        # Clears mds
        self._tmp_attr_mds = []