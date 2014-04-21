from copy import deepcopy
from types import GeneratorType
from six import add_metaclass
from urlparse import urlparse
import json
from rdflib import URIRef
from rdflib.plugins.sparql.parser import ParseException
from .attribute import LDAttribute
from .manager import InstanceManager, build_update_query_part
from .exceptions import MissingClassAttributeError, ReservedAttributeNameError, SPARQLParseError


class ModelBase(type):
    """
        Metaclass for all models
    """
    def __new__(mcs, name, bases, attributes):
        if name != "Model":
            required_fields = ["class_uri", "_storage_graph", "_context_dict", "_id_generator",
                               "types", "registry"]
            for field in required_fields:
                if field not in attributes:
                    raise MissingClassAttributeError("%s is required for class %s" % (field, name))
            attributes["_context_dict"] = mcs.clean_context(attributes["_context_dict"])

            # Removes some "attributes"
            # only used by the manager
            registry = attributes.pop("registry")

            # Should type be reserved?
            # TODO: merge it with class_uri ?
            reserved_attributes = ["id", "_attributes", "objects"]
            for field in reserved_attributes:
                if field in attributes:
                    raise ReservedAttributeNameError("%s is reserved" % field)

        # Descriptors
        attributes["_attributes"] = {k: v for k, v in attributes.iteritems()
                                     if isinstance(v, LDAttribute)}

        cls = type.__new__(mcs, name, bases, attributes)

        if name != "Model":
            #A la Django
            cls.objects = InstanceManager(cls, attributes["_storage_graph"], registry)
            registry.register(cls)

        return cls

    @classmethod
    def clean_context(mcs, context):
        """
            TODO: - make sure context is structured like this:
                {"@context": ...}
                 - make sure "id": "@id" and "type": "@type" are in
        """
        return context


@add_metaclass(ModelBase)
class Model(object):
    """
        TODO: support ids
    """

    def __init__(self, **kwargs):
        """
            Does not save (like Django)
        """

        if "id" in kwargs:
            # Anticipated because used in __hash__
            self._id = kwargs.pop("id")
        else:
            self._id = self._id_generator.generate()

        for k,v in kwargs.iteritems():
            setattr(self, k, v)

        # External skolemized blank nodes are not considered as blank nodes
        id_result = urlparse(self._id)
        self._is_blank_node = (u"/.well-known/genid/" in id_result.path) \
            and (id_result.hostname == u"localhost")

    @property
    def id(self):
        return self._id

    @classmethod
    def from_graph(cls, id, subgraph):
        """
            Loads a new instance from a subgraph
        """
        instance = cls(id=id)
        uri = URIRef(id)
        for attr in instance._attributes.values():
            attr.update_from_graph(instance, subgraph, cls._storage_graph)
        return instance

    def is_valid(self):
        for attr in self._attributes.values():
            if not attr.is_valid(self):
                return False
        return True

    def is_blank_node(self):
        return self._is_blank_node

    def save(self):
        """
            TODO:
                - Warns if there is some non-descriptor ("Attribute") attributes (will not be saved)
                - Saves descriptor attributes
        """
        # Checks
        for attr in self._attributes.values():
            # May raise an RequiredAttributeError
            attr.check_validity(self)

        #TODO: Warns

        former_lines = u""
        new_lines = u""
        for attr in self._attributes.values():
            if not attr.has_new_value(self):
                continue
            # Beware: has a side effect!
            former_lines += attr.pop_former_value_and_serialize_line(self)
            new_lines += attr.serialize_current_value_into_line(self)

        #TODO: only execute once (first save())
        types = self.types
        if former_lines == u"" and len(types) > 0:
            type_line = u"<%s> a" % self._id
            for t in types:
                type_line += u" <%s>," % t
            new_lines = type_line[:-1] + " . \n" + new_lines

        query = build_update_query_part(u"DELETE", self._id, former_lines)
        query += build_update_query_part(u"INSERT", self._id, new_lines)
        query += u"WHERE {}"
        #print query
        try:
            self._storage_graph.update(query)
        except ParseException as e:
            raise SPARQLParseError(u"%s\n %s" % (query, e))

    def to_dict(self, remove_none_values=True):
        dct = {name: self._convert_value(getattr(self, name))
               for name in self._attributes}
        # filter None values
        if remove_none_values:
            dct = {k: v for k,v in dct.iteritems() if v}

        if not self.is_blank_node():
            dct["id"] = self._id
        if self.types and len(self.types) > 0:
            dct["types"] = list(self.types)
        return dct

    def to_json(self, remove_none_values=True):
        """
            Pure JSON (not JSON-LD)
        """
        return json.dumps(self.to_dict(remove_none_values), sort_keys=True, indent=2)

    def to_jsonld(self, remove_none_values=True):
        dct = deepcopy(self._context_dict)
        dct.update(self.to_dict(remove_none_values))
        return json.dumps(dct, sort_keys=True, indent=2)

    # def __hash__(self):
    #     return hash(self.__repr__())
    #
    # def __eq__(self, other):
    #     return self._id == other._id

    def __str__(self):
        return self._id

    def __repr__(self):
        return u"%s(<%s>)" % (self.__class__.__name__, self._id)

    def _convert_value(self, value):
        """
            TODO: improve it
        """
        if isinstance(value, (list, set, GeneratorType)):
            return [self._convert_value(v) for v in value]
        if isinstance(value, Model):
            if value.is_blank_node():
                #TODO: what about its own context? Make sure contexts are
                # not incompatible
                return value.to_dict()
            # TODO: compare its URI if non-blank (if same document that self)
            else:
                # URI
                return value.id
        return value