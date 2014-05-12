"""

"""
from urlparse import urlparse
import json
from types import GeneratorType
from rdflib import URIRef, Graph, RDF
from rdflib.plugins.sparql.parser import ParseException
from rdflib.plugins.sparql import prepareQuery
from .property import PropertyType
from .exception import OMSPARQLParseError
from .exception import OMAttributeAccessError, OMUniquenessError, OMWrongObjectError, OMEditError
from oldman.utils.sparql import build_update_query_part


class Resource(object):

    existence_query = prepareQuery(u"ASK {?id ?p ?o .}")

    def __init__(self, domain, create=True, base_iri=None, types=None, **kwargs):
        """
            Does not save (like Django)
            TODO: rename create into is_new
        """
        models = domain.registry.get_models(types)
        main_model = domain.registry.select_model(models)
        self._models = models
        self._domain = domain

        if "id" in kwargs:
            # Anticipated because used in __hash__
            self._id = kwargs.pop("id")
            if create:
                #TODO: test the default graph
                exist = bool(self._domain.default_graph.query(self.existence_query,
                                                              initBindings={'id': URIRef(self._id)}))
                if exist:
                    raise OMUniquenessError("Object %s already exist" % self._id)
        else:
            self._id = main_model.generate_iri(base_iri=base_iri)

        self._types = types
        #TODO: improve the order
        for model in models:
            self._types += [t for t in model.class_types if t not in self._types]

        for k, v in kwargs.iteritems():
            setattr(self, k, v)
        self._is_blank_node = is_blank_node(self._id)

    @classmethod
    def load_from_graph(cls, domain, id, subgraph, is_new=True):
        """
            Loads a new Resource object from a subgraph
        """
        types = list({unicode(t) for t in subgraph.objects(URIRef(id), RDF.type)})
        instance = cls(domain, id=id, types=types, create=is_new)
        instance.full_update_from_graph(subgraph, is_end_user=True, save=False, initial=True)
        return instance

    def __getattr__(self, name):
        for model in self._models:
            if name in model.om_attributes:
                return model.access_attribute(name).get(self, self._domain)
        raise AttributeError("%s has not attribute %s" % (self, name))

    def __setattr__(self, name, value):
        if name in ["_models", "_id", "_types", "_is_blank_node", "_domain"]:
            self.__dict__[name] = value
            return

        found = False
        for model in self._models:
            if name in model.om_attributes:
                model.access_attribute(name).set(self, value)
                found = True
        if not found:
            raise AttributeError("%s has not attribute %s" % (self, name))

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
        if len(self._models) > 1:
            raise NotImplementedError("TODO: merge contexts when a Resource has multiple models")
        return list(self._models)[0].context

    def add_type(self, additional_type):
        if additional_type not in self._types:
            self._types.append(additional_type)

    def is_valid(self):
        for model in self._models:
            for attr in model.om_attributes.values():
                if not attr.is_valid(self):
                    return False
        return True

    def check_validity(self):
        """
            May raise a LDEditError
        """
        for model in self._models:
            for attr in model.om_attributes.values():
                attr.check_validity(self)

    def is_blank_node(self):
        return self._is_blank_node

    def save(self, is_end_user=True):
        # Checks
        attributes = self._extract_attribute_list()
        for attr in attributes:
            attr.check_validity(self, is_end_user)
        self._save(attributes)

    def _save(self, attributes):
        """
            TODO:
                - Warns if there is some non-descriptor ("Attribute") attributes (will not be saved)
                - Saves descriptor attributes
        """

        #TODO: Warns
        objects_to_delete = []
        former_lines = u""
        new_lines = u""
        for attr in attributes:
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
                self._domain.default_graph.update(query)
            except ParseException as e:
                raise OMSPARQLParseError(u"%s\n %s" % (query, e))

        for obj in objects_to_delete:
            obj.delete()

    def _extract_attribute_list(self):
        attributes = []
        for model in self._models:
            attributes += model.om_attributes.values()
        return attributes

    def to_dict(self, remove_none_values=True, include_different_contexts=False,
                ignored_iris=None):
        if ignored_iris is None:
            ignored_iris = set()
        ignored_iris.add(self._id)

        dct = {attr.name: self._convert_value(getattr(self, attr.name), ignored_iris, remove_none_values,
                                         include_different_contexts)
               for attr in self._extract_attribute_list()
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
        dct['@context'] = self.context
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
        if isinstance(value, Resource):
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

        attributes = self._extract_attribute_list()
        attr_names = [a.name for a in attributes]
        for key in full_dict:
            if key not in attr_names and key not in ["@context", "id", "types"]:
                raise OMAttributeAccessError("%s is not an attribute of %s" % (key, self._id))

        for attr in attributes:
            value = full_dict.get(attr.name)
            # set is not a JSON structure (but a JSON-LD one)
            if value is not None and attr.container == "@set":
                value = set(value)
            attr.set(self, value)

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

    def full_update_from_graph(self, subgraph, is_end_user=True, save=True, initial=False):
        for attr in self._extract_attribute_list():
            attr.update_from_graph(self, subgraph, self._domain.default_graph, initial=initial)
        #Types
        if not initial:
            new_types = {unicode(t) for t in subgraph.objects(URIRef(self._id), RDF.type)}
            self._types += [t for t in new_types if t not in self._types]

        if save:
            self.save(is_end_user)


def is_blank_node(iri):
    # External skolemized blank nodes are not considered as blank nodes
    id_result = urlparse(iri)
    return (u"/.well-known/genid/" in id_result.path) and (id_result.hostname == u"localhost")


def should_delete_object(obj):
    """
        TODO: make sure these blank nodes are not referenced somewhere else
    """
    return obj.is_blank_node()
