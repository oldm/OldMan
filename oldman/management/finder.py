from weakref import WeakValueDictionary
import logging
from rdflib import URIRef, Graph
from rdflib.plugins.sparql.parser import ParseException
from oldman.resource import Resource
from oldman.utils.sparql import build_query_part
from oldman.exception import OMSPARQLParseError, OMAttributeAccessError, OMClassInstanceError, OMSPARQLError
from oldman.exception import OMHashIriError, OMObjectNotFoundError


class Finder(object):
    """A :class:`~oldman.management.finder.Finder` object retrieves and  caches
       :class:`~oldman.resource.Resource` objects.

       :param manager: The :class:`~oldman.management.manager.ResourceManager` object.
                       It gives access to RDF graphs.
    """

    _base_uri_raw_query = u"""
        SELECT DISTINCT ?uri
        WHERE {
            ?uri ?p ?o .
            FILTER (REGEX(STR(?uri), CONCAT(?base, "#")) || (STR(?uri) = ?base) )
         } """

    def __init__(self, manager):
        self._manager = manager
        self._cache = WeakValueDictionary()
        # if class_iri:
        #     self._check_type_request = u"ASK {?s a <%s> }" % class_iri
        self._logger = logging.getLogger(__name__)

    def clear_cache(self):
        """Clears the cache of :class:`~oldman.resource.Resource` objects."""
        self._cache.clear()

    def filter(self, types=None, base_iri=None, **kwargs):
        """Finds the :class:`~oldman.resource.Resource` objects matching the given criteria.

        The `kwargs` dict can contains:

           1. regular attribute key-values ;
           2. the special attribute `id`. If given, :func:`~oldman.management.finder.Finder.get` is called.

        :param types: IRIs of the RDFS classes filtered resources must be instance of. Defaults to `None`.
        :param base_iri: base IRI of filtered resources. Defaults to `None`.
        :return: A generator of :class:`~oldman.resource.Resource` objects.
        """
        if kwargs.get("id") is not None:
            return self.get(**kwargs)

        elif base_iri is not None:
            return self._filter_base_iri(base_iri)

        elif len(kwargs) == 0:
            self._logger.warn(u"filter() called without parameter. Returns every resource of the union graph.")
            query = u"SELECT DISTINCT ?s WHERE { ?s ?p ?o }"
        else:
            type_set = set(types) if types is not None else set()
            models, _ = self._manager.find_models_and_types(type_set)

            lines = u""
            for type_iri in types:
                lines += u"?s a <%s> ." % type_iri

            for name, value in kwargs.iteritems():
                if name == "id":
                    continue
                # May raise a OMAttributeAccessError
                attr = _find_attribute(models, name)
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
        """Finds the :class:`~oldman.resource.Resource` objects matching a given query.

        :param query: SPARQL SELECT query where the first variable assigned
                      corresponds to the IRIs of the resources that will be returned.
        :return: A generator of :class:`~oldman.resource.Resource` objects.
        """
        if "SELECT" not in query:
            raise OMSPARQLError(u"Not a SELECT query. Query: %s" % query)
        try:
            results = self._manager.union_graph.query(query)
        except ParseException as e:
            raise OMSPARQLError(u"%s\n %s" % (query, e))
        return (self.get(id=unicode(r[0])) for r in results)

    def get(self, id=None, types=None, base_iri=None, **kwargs):
        """Gets the first :class:`~oldman.resource.Resource` object matching the given criteria.

        The `kwargs` dict can contains regular attribute key-values.

        When `id` is given, types are then checked.
        An :exc:`~oldman.exception.OMClassInstanceError` is raised if the resource
        is not instance of these classes.
        **Other criteria are not checked**.

        :param id: IRI of the resource. Defaults to `None`.
        :param types: IRIs of the RDFS classes filtered resources must be instance of. Defaults to `None`.
        :param base_iri: base IRI of filtered resources. Defaults to `None`.
        :return: A :class:`~oldman.resource.Resource` object or `None` if no resource has been found.
        """
        types = set(types) if types is not None else set()

        if id is not None:
            resource = self._get_by_id(id)
            if not types.issubset(resource.types):
                missing_types = types.difference(resource.types)
                raise OMClassInstanceError("%s found, but is not instance of %s" % (id, missing_types))
            #TODO: warn that attributes should not be given with the id
            return resource

        elif base_iri is not None:
            #TODO: fix it!!! Should also consider types.
            return self._get_from_base_iri(base_iri)

        elif len(kwargs) == 0:
            self._logger.warn(u"get() called without parameter. Returns the first resource found in the union graph.")
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
        for resource in self.filter(types=types, base_iri=base_iri, **kwargs):
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

    def _filter_base_iri(self, base_iri):
        if "#" in base_iri:
            raise OMHashIriError(u"%s is not a base IRI" % base_iri)
        query = self._base_uri_raw_query.replace(u"?base", u'"%s"' % base_iri)
        # Generator
        return (self.get(id=unicode(result[0])) for result in self._manager.union_graph.query(query))

    def _get_from_base_iri(self, base_iri):
        resources = list(self._filter_base_iri(base_iri))
        if len(resources) == 0:
            raise OMObjectNotFoundError(u"No resource with base iri %s" % base_iri)
        elif len(resources) > 1:
            for r in resources:
                if r.id == base_iri:
                    return r
            # TODO: avoid such arbitrary selection
            self._logger.warn(u"Multiple resources have the same base_uri: %s\n. "
                              u"The first one is selected." % resources)
        return resources[0]


def _find_attribute(models, name):
    for m in models:
        if name in m.om_attributes:
            return m.access_attribute(name)
    raise OMAttributeAccessError(u"%s not found in models %s " % (name, [m.name for m in models]))