"""

"""
from functools import partial
from urlparse import urlparse
import logging
import json
from types import GeneratorType
from rdflib import URIRef, Graph, RDF
from rdflib.plugins.sparql.parser import ParseException
from .property import PropertyType
from .exception import OMSPARQLParseError, OMUnauthorizedTypeChangeError, OMInternalError
from .exception import OMAttributeAccessError, OMUniquenessError, OMWrongResourceError, OMEditError
from oldman.utils.sparql import build_update_query_part


class Resource(object):

    _existence_query = u"ASK {?id ?p ?o .}"
    _special_attribute_names = ["_models", "_id", "_types", "_is_blank_node", "_manager",
                                "_former_types", "_logger"]
    _pickle_attribute_names = ["_id", '_types']

    def __init__(self, manager, id=None, types=None, base_iri=None, is_new=True, **kwargs):
        """
            Does not save (like Django)
        """
        self._models, self._types = manager.find_models_and_types(types)
        self._former_types = set(self._types) if not is_new else set()
        main_model = self._models[0]
        self._manager = manager

        if id is not None:
            # Anticipated because used in __hash__
            self._id = id
            if is_new:
                exist = bool(self._manager.union_graph.query(self._existence_query,
                                                             initBindings={'id': URIRef(self._id)}))
                if exist:
                    raise OMUniquenessError("Object %s already exist" % self._id)
        else:
            self._id = main_model.generate_iri(base_iri=base_iri)
        self._init_non_persistent_attributes(self._id)

        for k, v in kwargs.iteritems():
            setattr(self, k, v)

    def _init_non_persistent_attributes(self, id):
        self._logger = logging.getLogger(__name__)
        self._is_blank_node = is_blank_node(id)

    @classmethod
    def load_from_graph(cls, manager, id, subgraph, is_new=True):
        """
            Loads a new Resource object from a subgraph
        """
        types = list({unicode(t) for t in subgraph.objects(URIRef(id), RDF.type)})
        instance = cls(manager, id=id, types=types, is_new=is_new)
        instance.full_update_from_graph(subgraph, is_end_user=True, save=False, initial=True)
        return instance

    def __getattr__(self, name):
        for model in self._models:
            if name in model.om_attributes:
                return model.access_attribute(name).get(self)
            method = model.methods.get(name)
            if method is not None:
                # Make this function be a method (taking self as first parameter)
                return partial(method, self)
        raise AttributeError("%s has not attribute %s" % (self, name))

    def __setattr__(self, name, value):
        if name in self._special_attribute_names:
            self.__dict__[name] = value
            return

        found = False
        for model in self._models:
            if name in model.om_attributes:
                model.access_attribute(name).set(self, value)
                found = True
        if not found:
            raise AttributeError("%s has not attribute %s" % (self, name))

    def __getstate__(self):
        """ Pickling"""
        state = {name: getattr(self, name) for name in self._pickle_attribute_names}
        state["manager_name"] = self._manager.name

        # Reversed order so that important models can
        # overwrite values
        reversed_models = self._models
        reversed_models.reverse()
        for model in reversed_models:
            for name, attr in model.om_attributes.iteritems():
                value = attr.get(self)
                if isinstance(value, GeneratorType):
                    if attr.container == "@list":
                        value = list(value)
                    else:
                        value = set(value)
                if value is not None:
                    state[name] = value
        return state

    def __setstate__(self, state):
        """Unpickling"""
        required_fields = self._pickle_attribute_names + ["manager_name"]
        for name in required_fields:
            if name not in state:
                #TODO: find a better exception (due to the cache)
                raise OMInternalError("Required field %s is missing in the cached state" % name)

        self._id = state["_id"]
        self._init_non_persistent_attributes(self._id)

        # Manager
        from oldman import ResourceManager
        self._manager = ResourceManager.get_manager(state["manager_name"])

        # Models and types
        self._models, self._types = self._manager.find_models_and_types(state["_types"])
        self._former_types = set(self._types)

        # Attributes (Python attributes or OMAttributes)
        for name, value in state.iteritems():
            if name in ["manager_name", "_id", "_types"]:
                continue
            elif name in self._special_attribute_names:
                setattr(self, name, value)
            # OMAttributes
            else:
                attribute = self._get_om_attribute(name)
                attribute.set(self, value)
                # Clears former values (allows modification)
                attribute.pop_former_value(self)

    @property
    def types(self):
        return list(self._types)

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

    def is_instance_of(self, model):
        return model.class_iri in self._types

    def save(self, is_end_user=True):
        # Checks
        attributes = self._extract_attribute_list()
        for attr in attributes:
            attr.check_validity(self, is_end_user)
        self._save(attributes)

        # Cache
        self._manager.resource_cache.set_resource(self)

        return self

    def _save(self, attributes):
        """
        """
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
                former_objects = [self._manager.get(id=v) for v in former_values if v is not None]
                objects_to_delete += [v for v in former_objects if should_delete_object(v)]

        if self._former_types is not None:
            types = set(self._types)
            # New type
            for t in types.difference(self._former_types):
                type_line = u"<%s> a <%s> .\n" % (self._id, t)
                new_lines += type_line
            # Removed type
            for t in self._former_types.difference(types):
                type_line = u"<%s> a <%s> .\n" % (self._id, t)
                former_lines += type_line

        query = build_update_query_part(u"DELETE DATA", self._id, former_lines)
        if len(query) > 0:
            query += u" ;"
        query += build_update_query_part(u"INSERT DATA", self._id, new_lines)
        if len(query) > 0:
            self._logger.debug("Query: %s" % query)
            try:
                self._manager.data_graph.update(query)
            except ParseException as e:
                raise OMSPARQLParseError(u"%s\n %s" % (query, e))

        self._former_types = None
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
        if self._types and len(self._types) > 0:
            dct["types"] = list(self._types)
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
        attributes = self._extract_attribute_list()
        for attr in attributes:
            # Delete blank nodes recursively
            if attr.om_property.type == PropertyType.ObjectProperty:
                objs = getattr(self, attr.name)
                if objs is not None:
                    if isinstance(objs, (list, set, GeneratorType)):
                        for obj in objs:
                            if should_delete_object(obj):
                                self._logger.debug(u"%s deleted with %s" % (obj.id, self._id))
                                obj.delete()
                            else:
                                self._logger.debug(u"%s not deleted with %s" % (obj.id, self._id))
                    elif should_delete_object(objs):
                        objs.delete()

            setattr(self, attr.name, None)

        #Types
        self._change_types(set())
        self._save(attributes)
        self._manager.resource_cache.remove_resource(self)

    def full_update(self, full_dict, is_end_user=True, allow_new_type=False, allow_type_removal=False,
                    save=True):
        """
            JSON-LD containers are supported.
            Flat rather than deep: no nested object structure (only their IRI).

            If some attributes are not found in the dict,
             their values will be set to None.
        """
        #if not self.is_blank_node() and "id" not in full_dict:
        if "id" not in full_dict:
            raise OMWrongResourceError("Cannot update an object without IRI")
        elif full_dict["id"] != self._id:
            raise OMWrongResourceError("Wrong IRI %s (%s was expected)" % (full_dict["id"], self._id))

        attributes = self._extract_attribute_list()
        attr_names = [a.name for a in attributes]
        for key in full_dict:
            if key not in attr_names and key not in ["@context", "id", "types"]:
                raise OMAttributeAccessError("%s is not an attribute of %s" % (key, self._id))

        # Type change management
        if "types" in full_dict:
            try:
                new_types = set(full_dict["types"])
            except TypeError:
                raise OMEditError("'types' attribute is not a list, a set or a string but is %s " % new_types)
            self._check_and_update_types(new_types, allow_new_type, allow_type_removal)

        for attr in attributes:
            value = full_dict.get(attr.name)
            # set is not a JSON structure (but a JSON-LD one)
            if value is not None and attr.container == "@set":
                value = set(value)
            attr.set(self, value)

        if save:
            self.save(is_end_user)

    def full_update_from_graph(self, subgraph, is_end_user=True, save=True, initial=False,
                               allow_new_type=False, allow_type_removal=False):
        for attr in self._extract_attribute_list():
            attr.update_from_graph(self, subgraph, self._manager.data_graph, initial=initial)
        #Types
        if not initial:
            new_types = {unicode(t) for t in subgraph.objects(URIRef(self._id), RDF.type)}
            self._check_and_update_types(new_types, allow_new_type, allow_type_removal)

        if save:
            self.save(is_end_user)

    def _check_and_update_types(self, new_types, allow_new_type, allow_type_removal):
        current_types = set(self._types)
        if new_types == current_types:
            return
        change = False

        # Appending new types
        additional_types = new_types.difference(current_types)
        if len(additional_types) > 0:
            if not allow_new_type:
                raise OMUnauthorizedTypeChangeError("Adding %s to %s has not been allowed"
                                                    % (additional_types, self._id))
            change = True

        # Removal
        missing_types = current_types.difference(new_types)
        if len(missing_types) > 0:
            implicit_types = {t for m in self._models for t in m.ancestry_iris}.difference(
                {m.class_iri for m in self._models})
            removed_types = missing_types.difference(implicit_types)
            if len(removed_types) > 0:
                if not allow_type_removal:
                    raise OMUnauthorizedTypeChangeError("Removing %s to %s has not been allowed"
                                                        % (removed_types, self._id))
                change = True
        if change:
            self._models, types = self._manager.find_models_and_types(new_types)
            self._change_types(types)

    def _change_types(self, new_types):
        if self._former_types is None:
            self._former_types = set(self._types)
        self._types = new_types

    def _get_om_attribute(self, name):
        for model in self._models:
            if name in model.om_attributes:
                return model.access_attribute(name)
        self._logger.debug(u"Models: %s, types: %s" % ([m.name for m in self._models], self._types))
        #self._logger.debug(u"%s" % self._manager._registry.model_names)
        raise AttributeError(u"%s has not attribute %s" % (self, name))


def is_blank_node(iri):
    # External skolemized blank nodes are not considered as blank nodes
    id_result = urlparse(iri)
    return (u"/.well-known/genid/" in id_result.path) and (id_result.hostname == u"localhost")


def should_delete_object(obj):
    """
    TODO: make sure these blank nodes are not referenced somewhere else
    """
    return obj is not None and obj.is_blank_node()
