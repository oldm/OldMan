from copy import deepcopy
from six import add_metaclass
from urlparse import urlparse
import json
from types import GeneratorType
from rdflib import URIRef, Graph, RDF
from rdflib.plugins.sparql.parser import ParseException
from rdflib.plugins.sparql import prepareQuery
from .attribute import OMAttribute
from .property import PropertyType
from .manager import InstanceManager, build_update_query_part
from .exception import OMMissingClassAttributeError, OMReservedAttributeNameError, OMSPARQLParseError
from .exception import OMAttributeAccessError, OMUniquenessError, OMWrongObjectError, OMEditError


class ModelBase(type):
    """
        Metaclass for all models
    """
    def __new__(mcs, name, bases, attributes):
        if name != "Model":
            required_fields = ["class_uri", "_storage_graph", "_context", "_id_generator",
                               "_ancestry", "class_types", "registry"]
            for field in required_fields:
                if field not in attributes:
                    raise OMMissingClassAttributeError("%s is required for class %s" % (field, name))
            attributes["_context"] = mcs.clean_context(attributes["_context"])

            # Removes some "attributes"
            # only used by the manager
            registry = attributes.pop("registry")

            reserved_names = ["id", "_attributes", "objects", "base_iri", "_types",
                              "types"]
            for field in reserved_names:
                if field in attributes:
                    raise OMReservedAttributeNameError("%s is reserved" % field)

        # Descriptors
        attributes["_attributes"] = {k: v for k, v in attributes.iteritems()
                                     if isinstance(v, OMAttribute)}

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
        return cls.class_uri in subclass.class_types

    @classmethod
    def clean_context(mcs, context):
        """
            Context can be an IRI, a list or a dict
            TODO: - make sure "id": "@id" and "type": "@type" are in
        """
        if isinstance(context, dict) and "@context" in context.keys():
            context = context["@context"]
        return context


@add_metaclass(ModelBase)
class Model(object):

    existence_query = prepareQuery(u"ASK {?id ?p ?o .}")

    def __init__(self, create=True, base_iri=None, **kwargs):
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
                    raise OMUniquenessError("Object %s already exist" % self._id)
        else:
            self._id = self._id_generator.generate(base_iri=base_iri)

        self._types = list(self.class_types)
        if "types" in kwargs:
            new_types = kwargs.pop("types")
            if isinstance(new_types, str):
                new_types = [new_types]
            self._types += [t for t in new_types if t not in self._types]

        for k, v in kwargs.iteritems():
            setattr(self, k, v)
        self._is_blank_node = is_blank_node(self._id)

    @property
    def types(self):
        return self._types

    @property
    def id(self):
        return self._id

    @property
    def base_iri(self):
        return self._id.split('#')[0]

    @property
    def context(self):
        return self._context

    def add_type(self, additional_type):
        if additional_type not in self._types:
            self._types.append(additional_type)

    @classmethod
    def load_from_graph(cls, id, subgraph, create=True):
        """
            Loads a new instance from a subgraph
        """
        instance = cls(id=id, create=create)
        for attr in cls._attributes.values():
            attr.update_from_graph(instance, subgraph, cls._storage_graph, initial=True)
        return instance

    @classmethod
    def get_attribute(cls, name):
        try:
            return cls._attributes[name]
        except KeyError:
            raise OMAttributeAccessError("%s has no supported attribute %s" % (cls, name))

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

    def check_validity(self):
        """
            May raise a LDEditError
        """
        for attr in self._attributes.values():
            attr.check_validity(self)

    def is_blank_node(self):
        return self._is_blank_node

    def save(self, is_end_user=True):
        # Checks
        for attr in self._attributes.values():
            attr.check_validity(self, is_end_user)
        self._save(is_end_user)

    def _save(self, is_end_user=True):
        """
            TODO:
                - Warns if there is some non-descriptor ("Attribute") attributes (will not be saved)
                - Saves descriptor attributes
        """

        #TODO: Warns
        objects_to_delete = []
        former_lines = u""
        new_lines = u""
        for attr in self._attributes.values():
            if not attr.has_new_value(self):
                continue
            # Beware: has a side effect!
            former_values = attr.pop_former_value(self)
            former_lines += attr.serialize_values_into_lines(former_values)
            new_lines += attr.serialize_current_value_into_line(self)

            # Some former objects may be deleted
            if attr.om_property.type == PropertyType.ObjectProperty:
                if isinstance(former_values, dict):
                    raise NotImplementedError("Object dicts are not yet supported.")
                former_values = former_values if isinstance(former_values, (set, list)) else [former_values]
                former_objects = [self.__class__.objects.get_any(id=v) for v in former_values if v is not None]
                objects_to_delete += [v for v in former_objects if should_delete_object(v)]

        #TODO: only execute once (first save())
        types = self.types
        if former_lines == u"" and len(types) > 0:
            type_line = u"<%s> a" % self._id
            for t in types:
                type_line += u" <%s>," % t
            new_lines = type_line[:-1] + " . \n" + new_lines

        query = build_update_query_part(u"DELETE", self._id, former_lines)
        query += build_update_query_part(u"INSERT", self._id, new_lines)
        if len(query) > 0:
            query += u"WHERE {}"
            #print query
            try:
                self._storage_graph.update(query)
            except ParseException as e:
                raise OMSPARQLParseError(u"%s\n %s" % (query, e))

        for obj in objects_to_delete:
            obj.delete()

    def to_dict(self, remove_none_values=True, include_different_contexts=False,
                ignored_iris=None):
        if ignored_iris is None:
            ignored_iris = set()
        ignored_iris.add(self._id)

        dct = {name: self._convert_value(getattr(self, name), ignored_iris, remove_none_values,
                                         include_different_contexts)
               for name, attr in self._attributes.iteritems()
               if not attr.is_write_only}
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
        dct = self.to_dict(remove_none_values)
        dct['@context'] = self._context
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
                if include_different_contexts and value._context != self._context:
                    value_dict["@context"] = value._context
                return value_dict
            else:
                # URI
                return value.id
        # Literal
        return value

    def in_same_document(self, other_obj):
        return self._id.split("#")[0] == other_obj.id.split("#")[0]

    def delete(self):
        for attr_name, attr in self._attributes.iteritems():
            # Delete blank nodes recursively
            if attr.om_property.type == PropertyType.ObjectProperty:
                objs = getattr(self, attr_name)
                if objs is not None:
                    if isinstance(objs, (list, set, GeneratorType)):
                        for obj in objs:
                            if should_delete_object(obj):
                                obj.delete()
                    elif should_delete_object(objs):
                        objs.delete()

            setattr(self, attr_name, None)
        self._save()

    def full_update(self, full_dict, is_end_user=True):
        """
            JSON-LD containers are supported.
            Flat rather than deep: no nested object structure (only their IRI).

            If some attributes are not found in the dict,
             their values will be set to None.
        """
        #if not self.is_blank_node() and "id" not in full_dict:
        if "id" not in full_dict:
            raise OMWrongObjectError("Cannot update an object without IRI")
        elif full_dict["id"] != self._id:
            raise OMWrongObjectError("Wrong IRI %s (%s was expected)" % (full_dict["id"], self._id))

        for key in full_dict:
            if key not in self._attributes and key not in ["@context", "id", "types"]:
                raise OMAttributeAccessError("%s is not an attribute of %s" % (key, self.__class__.__name__))

        for attr_name, attr in self._attributes.iteritems():
            value = full_dict.get(attr_name)
            # set is not a JSON structure (but a JSON-LD one)
            if value is not None and attr.container == "@set":
                value = set(value)
            setattr(self, attr_name, value)

        if "types" in full_dict:
            new_types = full_dict["types"]
            if isinstance(new_types, (list, str)):
                self._types += [t for t in new_types if t not in self._types]
            elif isinstance(new_types, str):
                new_type = new_types
                if not new_type in self._types:
                    self._types.append(new_type)
            else:
                raise OMEditError("'types' attribute is not a list, a set or a string but is %s " % new_types)

        self.save(is_end_user)

    def full_update_from_graph(self, subgraph, is_end_user=True, save=True):
        for attr in self._attributes.values():
            attr.update_from_graph(self, subgraph, self._storage_graph)
        #Types
        new_types = {unicode(t) for t in subgraph.objects(URIRef(self._id), RDF.type)}
        self._types += [t for t in new_types if t not in self._types]

        if save:
            self.save(is_end_user)


def is_blank_node(uri):
    # External skolemized blank nodes are not considered as blank nodes
    id_result = urlparse(uri)
    return (u"/.well-known/genid/" in id_result.path) and (id_result.hostname == u"localhost")


def should_delete_object(obj):
    """
        TODO: make sure these blank nodes are not referenced somewhere else
    """
    return obj.is_blank_node()