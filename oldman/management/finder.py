from weakref import WeakValueDictionary
import logging
from rdflib import URIRef, Graph
from rdflib.plugins.sparql.parser import ParseException
from oldman.resource import Resource
from oldman.utils.sparql import build_query_part
from oldman.exception import OMSPARQLParseError, OMAttributeAccessError, OMClassInstanceError


class Finder(object):
    def __init__(self, manager):
        self._manager = manager
        self._cache = WeakValueDictionary()
        # if class_iri:
        #     self._check_type_request = u"ASK {?s a <%s> }" % class_iri
        self._logger = logging.getLogger(__name__)

    def clear_cache(self):
        """ Clears its cache """
        self._cache.clear()

    def filter(self, **kwargs):
        if "id" in kwargs:
            return self.get(**kwargs)

        if len(kwargs) == 0:
            self._logger.warn(u"filter() called without parameter. Returns every resource of the union graph.")
            query = u"SELECT DISTINCT ?s WHERE { ?s ?p ?o }"
        else:
            type_set = set(kwargs.get("types", []))
            models, _ = self._manager.model_registry.find_models_and_types(type_set)

            lines = u""
            for name, value in kwargs.iteritems():
                if name == "types":
                    if not isinstance(value, (set, list)):
                        value = [value]
                    for type_iri in value:
                        lines += u"?s a <%s> ." % type_iri
                    continue
                # May raise a OMAttributeAccessError
                attr = find_attribute(models, name)
                value = kwargs[name]
                if value:
                    lines += attr.serialize_values_into_lines(value)

            query = build_query_part(u"SELECT ?s WHERE", u"?s", lines)
        try:
            results = self._manager.union_graph.query(query)
        except ParseException as e:
            raise OMSPARQLParseError(u"%s\n %s" % (query, e))

        # Generator expression
        return (self.get(id=unicode(r[0])) for r in results)

    def sparql_filter(self, query):
        try:
            results = self._manager.union_graph.query(query)
        except ParseException as e:
            raise OMSPARQLParseError(u"%s\n %s" % (query, e))
        return (self.get(id=unicode(r[0])) for r in results)

    def get(self, id=None, **kwargs):
        """
            When an id (IRI) is given, a Resource object is always returned.
            None is returned when no id has been given and no resource has been found.
        """
        if id:
            resource = self._get_by_id(id)
            types = set(kwargs.get("types", []))
            if not types.issubset(resource.types):
                missing_types = types.difference(resource.types)
                raise OMClassInstanceError("%s found, but is not instance of %s" % (id, missing_types))
            #TODO: warn that attributes should not be given with the id
            return resource
        elif len(kwargs) == 0:
            self._logger.warn(u"get() called without parameter. Returns the first resounce found in the union graph.")
            query = u"SELECT ?s WHERE { ?s ?p ?o } LIMIT 1"
            try:
                results = self._manager.union_graph.query(query)
            except ParseException as e:
                raise OMSPARQLParseError(u"%s\n %s" % (query, e))
            for r, in results:
                return self._get_by_id(unicode(r))
            # If no resource in the union graph
            return None

        # First found
        for resource in self.filter(**kwargs):
            return resource

        return None

    def _get_by_id(self, id):
        resource = self._cache.get(id)
        if resource:
            self._logger.debug("%s found in the cache" % resource)
            return resource
        resource_graph = Graph()
        iri = URIRef(id)
        resource_graph += self._manager.union_graph.triples((iri, None, None))
        return self._new_resource_object(id, resource_graph)

    def _new_resource_object(self, id, resource_graph):
        resource = Resource.load_from_graph(self._manager, id, resource_graph, is_new=(len(resource_graph) == 0))
        self._cache[id] = resource
        return resource


def find_attribute(models, name):
    for m in models:
        if name in m.om_attributes:
            return m.access_attribute(name)
    raise OMAttributeAccessError(u"%s not found in models %s " % (name, [m.name for m in models]))