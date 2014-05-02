from copy import deepcopy
from types import GeneratorType
from six import add_metaclass
from urlparse import urlparse
import json
from rdflib import URIRef, Graph
from rdflib.plugins.sparql.parser import ParseException
from rdflib.plugins.sparql import prepareQuery
from .attribute import LDAttribute
from .manager import InstanceManager, build_update_query_part
from .exceptions import MissingClassAttributeError, ReservedAttributeNameError, SPARQLParseError
from .exceptions import LDAttributeAccessError, LDUniquenessError


class ModelBase(type):
    """
        Metaclass for all models
    """
    def __new__(mcs, name, bases, attributes):
        if name != "Model":
            required_fields = ["class_uri", "_storage_graph", "_context_dict", "_id_generator",
                               "_ancestry", "types", "registry"]
            for field in required_fields:
                if field not in attributes:
                    raise MissingClassAttributeError("%s is required for class %s" % (field, name))
            attributes["_context_dict"] = mcs.clean_context(attributes["_context_dict"])

            # Removes some "attributes"
            # only used by the manager
            registry = attributes.pop("registry")

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

    def __instancecheck__(cls, instance):
        return issubclass(type(instance), cls)

    def __subclasscheck__(cls, subclass):
        if cls == subclass:
            return True
        if not hasattr(subclass, "class_uri"):
            return False
        if cls.__name__ == "Model":
            return True
        return cls.class_uri in subclass.types

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

    existence_query = prepareQuery(u"ASK {?id ?p ?o .}")

    def __init__(self, create=True, **kwargs):
        """
            Does not save (like Django)
        """

        if "id" in kwargs:
            # Anticipated because used in __hash__
            self._id = kwargs.pop("id")
            if create:
                exist = bool(self._storage_graph.query(self.existence_query,
                                                       initBindings={'id': URIRef(self._id)}))
                if exist:
                    raise LDUniquenessError("Object %s already exist" % self._id)

        else:
            self._id = self._id_generator.generate()

        for k, v in kwargs.iteritems():
            setattr(self, k, v)

        # External skolemized blank nodes are not considered as blank nodes
        id_result = urlparse(self._id)
        self._is_blank_node = (u"/.well-known/genid/" in id_result.path) \
            and (id_result.hostname == u"localhost")

    @property
    def id(self):
        return self._id

    @classmethod
    def load_from_graph(cls, id, subgraph, create=True):
        """
            Loads a new instance from a subgraph
        """
        instance = cls(id=id, create=create)
        for attr in instance._attributes.values():
            attr.update_from_graph(instance, subgraph, cls._storage_graph)
        return instance

    @classmethod
    def get_attribute(cls, name):
        try:
            return cls._attributes[name]
        except KeyError:
            raise LDAttributeAccessError("%s has no supported attribute %s" % (cls, name))

    @classmethod
    def reset_counter(cls):
        """
            To be called after clearing the storage graph.
            For unittest purposes.
        """
        if hasattr(cls._id_generator, "reset_counter"):
            cls._id_generator.reset_counter()

    def is_valid(self):
        for attr in self._attributes.values():
            if not attr.is_valid(self):
                return False
        return True

    def is_blank_node(self):
        return self._is_blank_node

    def save(self, is_end_user=True):
        """
            TODO:
                - Warns if there is some non-descriptor ("Attribute") attributes (will not be saved)
                - Saves descriptor attributes
        """
        # Checks
        for attr in self._attributes.values():
            # May raise an RequiredAttributeError
            attr.check_validity(self, is_end_user)

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

    def to_dict(self, remove_none_values=True, include_different_contexts=False,
                ignored_iris=None):
        if ignored_iris is None:
            ignored_iris = set()
        ignored_iris.add(self._id)

        dct = {name: self._convert_value(getattr(self, name), ignored_iris, remove_none_values,
                                         include_different_contexts)
               for name, attr in self._attributes.iteritems()
               if not attr.is_write_only
              }
        # filter None values
        if remove_none_values:
            dct = {k: v for k, v in dct.iteritems() if v is not None}

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

    def to_rdf(self, rdf_format="turtle"):
        g = Graph()
        g.parse(data=self.to_jsonld(), format="json-ld")
        return g.serialize(format=rdf_format)

    def __str__(self):
        return self._id

    def __repr__(self):
        return u"%s(<%s>)" % (self.__class__.__name__, self._id)

    def _convert_value(self, value, ignored_iris, remove_none_values, include_different_contexts=False):
        # Containers
        if isinstance(value, (list, set, GeneratorType)):
            return [self._convert_value(v, ignored_iris, remove_none_values, include_different_contexts)
                    for v in value]
        # Object
        if isinstance(value, Model):
            # If non-blank or in the same document
            if value.id not in ignored_iris and \
                    (value.is_blank_node() or self.in_same_document(value)):
                value_dict = dict(value.to_dict(remove_none_values, include_different_contexts, ignored_iris))
                # TODO: should we improve this test?
                if include_different_contexts and value._context_dict != self._context_dict:
                    value_dict.update(value._context_dict)
                return value_dict
            else:
                # URI
                return value.id
        # Literal
        return value

    def in_same_document(self, other_obj):
        return self._id.split("#")[0] == other_obj.id.split("#")[0]