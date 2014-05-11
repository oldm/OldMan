from enum import Enum
from .attribute import OMAttributeMetadata, OMAttribute, ObjectOMAttribute
from .exception import OMAlreadyDeclaredDatatypeError, OMPropertyDefTypeError
from .exception import OMAlreadyGeneratedAttributeError, OMInternalError, OMPropertyDefError


class PropertyType(Enum):
    UnknownPropertyType = 1
    DatatypeProperty = 2
    ObjectProperty = 3


class OMProperty(object):
    """
        RDF property declared "supported by a RDF class"
    """
    def __init__(self, property_uri, supporter_class_uri, is_required=False, read_only=False,
                 write_only=False, cardinality=None, property_type=PropertyType.UnknownPropertyType,
                 domains=None, ranges=None):
        self._uri = property_uri
        self._supporter_class_uri = supporter_class_uri
        self._is_required = is_required
        if cardinality:
            raise NotImplementedError("Property cardinality is not yet supported")
        # 1, 42, "*", "+"
        self._cardinality = cardinality
        self._type = property_type
        self._ranges = ranges if ranges is not None else set()
        self._domains = domains if domains is not None else set()

        if read_only and write_only:
            raise OMPropertyDefError("Property %s cannot be read-only and write-only" % property_uri)
        self._read_only = read_only
        self._write_only = write_only

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
                raise OMPropertyDefTypeError("Already declared as %s so cannot also be a %s "
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

    @property
    def is_read_only(self):
        return self._read_only

    @property
    def is_write_only(self):
        return self._write_only

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
        if p_range.startswith(u"http://www.w3.org/2001/XMLSchema#"):
            self.type = PropertyType.DatatypeProperty

        if self.type == PropertyType.DatatypeProperty and (not p_range in self._ranges) \
                and len(self._ranges) >=1:
            raise OMAlreadyDeclaredDatatypeError("Property datatype can only be specified once")

        self._ranges.add(p_range)

    @property
    def domains(self):
        return self._domains

    def add_domain(self, domain):
        # Detects XSD
        if range.startswith(u"http://www.w3.org/2001/XMLSchema#"):
            #TODO: find a better error type
            raise Exception("Domain cannot have a literal datatype")
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
            raise OMInternalError("Please generate them before accessing this attribute")
        return self._attributes

    def add_attribute_metadata(self, name, jsonld_type=None, language=None, container=None,
                               reverse=None):
        """
            TODO: support:
                - the container variable
                - reverse property
        """
        if self._attributes:
            raise OMAlreadyGeneratedAttributeError("It is too late to add attribute metadata")
        if jsonld_type:
            if jsonld_type == "@id":
                self.type = PropertyType.ObjectProperty
            else:
                self.type = PropertyType.DatatypeProperty
                if (not jsonld_type in self._ranges) and len(self._ranges) >=1:
                    raise OMAlreadyDeclaredDatatypeError("Attribute %s cannot have a different datatype"
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
            elif language is None:
                #TODO: find a better Exception type
                raise NotImplementedError("Untyped JSON-LD value (with no language) are not (yet?) supported")

        if len([md for md in self._tmp_attr_mds
                    if md.name == name]) > 0:
            raise OMInternalError("Multiple attribute named %s" % name)

        self._tmp_attr_mds.append(OMAttributeMetadata(name, self, language, jsonld_type, container,
                                                      bool(reverse)))

    def generate_attributes(self, attr_format_selector):
        """
            Can be called only once
        """
        if self._attributes:
            raise OMAlreadyGeneratedAttributeError()

        self._attributes = set()
        for md in self._tmp_attr_mds:
            value_format = attr_format_selector.find_value_format(md)
            attr_cls = ObjectOMAttribute if self._type == PropertyType.ObjectProperty else OMAttribute
            self._attributes.add(attr_cls(md, value_format))

        # Clears mds
        self._tmp_attr_mds = []