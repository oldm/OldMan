from exceptions import Exception
from copy import deepcopy
from six import add_metaclass
from .attribute import LDAttribute
from .manager import InstanceManager, build_update_query_part
from rdflib import URIRef, Literal, Graph
import json


class MissingClassAttributeError(Exception):
    """
        Attributes "storage_graph", "class_uri" and "context" are compulsory.
    """
    pass


class ReservedAttributeError(Exception):
    pass


class ModelBase(type):
    """
        Metaclass for all models
    """
    def __new__(mcs, name, bases, attributes):
        if name != "Model":
            required_fields = ["class_uri", "_storage_graph", "_context_dict", "_id_generator",
                               "types", "registry", "default_graph", "schema_graph"]
            for field in required_fields:
                if field not in attributes:
                    raise MissingClassAttributeError("%s is required for class %s" % (field, name))
            attributes["_context_dict"] = mcs.clean_context(attributes["_context_dict"])

            # Removes some "attributes"
            # only used by the manager
            registry = attributes.pop("registry")
            # Default graph should be managed as read-only
            default_graph = attributes.pop("default_graph")
            # Read-only too
            schema_graph = attributes.pop("schema_graph")

            # Should type be reserved?
            # TODO: merge it with class_uri ?
            reserved_attributes = ["id", "_attributes"]
            for field in reserved_attributes:
                if field in attributes:
                    raise ReservedAttributeError("%s is reserved" % field)

        # Descriptors
        attributes["_attributes"] = {k: v for k, v in attributes.iteritems()
                                     if isinstance(v, LDAttribute)}

        cls = type.__new__(mcs, name, bases, attributes)

        if name != "Model":
            #TODO: log a message if "objects" was already allocated (data attribute)
            #A la Django
            cls.objects = InstanceManager(cls, attributes["_storage_graph"], default_graph,
                                          schema_graph, registry)
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
        for attr_name, attr in instance._attributes.iteritems():
            property_uri = URIRef(attr.ld_property.uri)
            language = attr.language

            results = subgraph.objects(uri, property_uri)

            # Filter if language is specified
            if language:
                results = [r for r in results if isinstance(r, Literal)
                           and r._language == language]

            f = lambda x: unicode(x) if isinstance(x, Literal) else str(x)
            values = [f(r) for r in results]
            #print "Results for %s: %s" %(attr_name, values)

            if len(values) == 0:
                continue
            elif not attr.container and len(values) == 1:
                values = values[0]
            elif attr.container == "@set":
                values = set(values)
            setattr(instance, attr_name, values)
            # Clears "None" former value
            attr.pop_former_value(instance)
        return instance

    def is_valid(self):
        for attr in self._attributes.values():
            if not attr.is_valid(self):
                return False
        return True

    def is_blank_node(self):
        """
            TODO: implement it
        """
        return True

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

        former_lines = ""
        new_lines = ""
        for attr in self._attributes.values():
            if not attr.has_new_value(self):
                continue
            property_uri = attr.ld_property.uri
            # Beware: has a side effect!
            former_lines += attr.pop_former_value_and_serialize_line(self)
            new_lines += attr.serialize_current_value_into_line(self)

        #TODO: only execute once (first save())
        types = self.types
        if former_lines == "" and len(types) > 0:
            type_line = "<%s> a" % self._id
            for t in types:
                type_line += " <%s>," % t
            new_lines = type_line[:-1] + " . \n" + new_lines

        query = build_update_query_part("DELETE", self._id, former_lines)
        query += build_update_query_part("INSERT", self._id, new_lines)
        query += "WHERE {}"
        #print query
        self._storage_graph.update(query)

    def to_dict(self):
        dct = { name: self._convert_value(getattr(self, name))
                 for name in self._attributes}
        dct["id"] = self._id
        dct["types"] = self.types
        return dct

    def to_json(self):
        """
            Pure JSON (not JSON-LD)
        """
        return json.dumps(self.to_dict())

    def to_jsonld(self):
        dct = deepcopy(self._context_dict)
        dct.update(self.to_dict())
        return json.dumps(dct)

    # def __hash__(self):
    #     return hash(self.__repr__())
    #
    # def __eq__(self, other):
    #     return self._id == other._id

    def __str__(self):
        return self._id

    def __repr__(self):
        return "%s(<%s>)" % (self.__class__.__name__, self._id)


    def _convert_value(self, value):
        """
            TODO: improve it
        """
        if isinstance(value, (list, set)):
            return [self._convert_value(v) for v in value]
        if isinstance(value, Model):
            if value.is_blank_node():
                #TODO: what about its own context? Make sure contexts are
                # not incompatible
                return value.to_dict()
            # TODO: compare its URI if non-blank (if same document that self)
            else:
                # URI
                return value._id
        return value