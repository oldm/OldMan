import logging
from threading import Lock
from rdflib import URIRef, Graph, RDF
from rdflib.plugins.sparql.parser import ParseException
from oldman.utils.sparql import build_query_part, build_update_query_part
from oldman.resource import Resource
from oldman.exception import OMSPARQLParseError, OMAttributeAccessError, OMClassInstanceError, OMSPARQLError
from oldman.exception import OMHashIriError, OMObjectNotFoundError
from oldman.exception import OMDataStoreError
from .datastore import DataStore


class SPARQLDataStore(DataStore):
    """A :class:`~oldman.management.finder.ResourceFinder` object retrieves
    :class:`~oldman.resource.Resource` objects.

    :param manager: The :class:`~oldman.management.manager.ResourceManager` object.
                    It gives access to RDF graphs.
    """
    _iri_mutex = Lock()
    _counter_query_req = u"""
            PREFIX oldman: <urn:oldman:>
            SELECT ?number
            WHERE {
                ?class_iri oldman:nextNumber ?number .
            }"""
    _counter_update_req = u"""
            PREFIX oldman: <urn:oldman:>
            DELETE {
                ?class_iri oldman:nextNumber ?current .
            }
            INSERT {
                ?class_iri oldman:nextNumber ?next .
            }
            WHERE {
                ?class_iri oldman:nextNumber ?current .
                BIND (?current+1 AS ?next)
            }"""

    def __init__(self, data_graph, union_graph=None, cache_region=None):
        DataStore.__init__(self, cache_region)
        self._logger = logging.getLogger(__name__)
        self._data_graph = data_graph
        self._union_graph = union_graph if union_graph is not None else data_graph

    def filter(self, types=None, hashless_iri=None, limit=None, eager=False, pre_cache_properties=None, **kwargs):
        """Finds the :class:`~oldman.resource.Resource` objects matching the given criteria.

        The `kwargs` dict can contains:

           1. regular attribute key-values ;
           2. the special attribute `id`. If given, :func:`~oldman.management.finder.Finder.get` is called.

        :param types: IRIs of the RDFS classes filtered resources must be instance of. Defaults to `None`.
        :param hashless_iri: Hash-less IRI of filtered resources. Defaults to `None`.
        :param limit: Upper bound on the number of solutions returned (SPARQL LIMIT). Positive integer.
                      Defaults to `None`.
        :param eager: If `True` loads all the Resource objects within one single SPARQL query.
                      Defaults to `False` (lazy).
        :param pre_cache_properties: List of RDF ObjectProperties to pre-cache eagerly.
                      Their values (:class:`~oldman.resource.Resource` objects) are loaded and
                      added to the cache. Defaults to `[]`. If given, `eager` must be `True`.
                      Disabled if there is no cache.
        :return: A generator (if lazy) or a list (if eager) of :class:`~oldman.resource.Resource` objects.

        TODO: refactor
        """
        if not eager and pre_cache_properties is not None:
            raise AttributeError(u"Eager properties are incompatible with lazyness. Please set eager to True.")

        id = kwargs.pop("id") if "id" in kwargs else None
        type_iris = types if types is not None else []
        if id is not None:
            return self.get(id=id, types=types, hashless_iri=hashless_iri, **kwargs)

        if len(type_iris) == 0 and len(kwargs) > 0:
            raise OMAttributeAccessError(u"No type given in filter() so attributes %s are ambiguous."
                                         % kwargs.keys())

        return self._filter(type_iris, hashless_iri, limit, eager, pre_cache_properties, **kwargs)

    def _filter(self, type_iris, hashless_iri, limit, eager, pre_cache_properties, **kwargs):
        if len(type_iris) == 0 and len(kwargs) == 0:
            if hashless_iri is None:
                self._logger.warn(u"filter() called without parameter. Returns every resource in the union graph.")
            lines = u"?s ?p ?o . \n"
        else:
            type_set = set(type_iris)
            models, _ = self.manager.find_models_and_types(type_set)

            lines = u""
            for type_iri in type_iris:
                lines += u"?s a <%s> .\n" % type_iri

            for name, value in kwargs.iteritems():
                # May raise a OMAttributeAccessError
                attr = _find_attribute(models, name)
                value = kwargs[name]
                if value:
                    lines += attr.serialize_value_into_lines(value)

        if hashless_iri is not None:
            if "#" in hashless_iri:
                raise OMHashIriError(u"%s is not a hash-less IRI" % hashless_iri)
            lines += u"""FILTER (REGEX(STR(?s), CONCAT(?base, "#")) || (STR(?s) = ?base) )""".replace(
                u"?base", u'"%s"' % hashless_iri)

        query = build_query_part(u"SELECT DISTINCT ?s WHERE", u"?s", lines)
        if limit is not None:
            query += u"LIMIT %d" % limit

        if eager:
            return self._filter_eagerly(query, pre_cache_properties)
        # Lazy (by default)
        return self._filter_lazily(query)

    def sparql_filter(self, query):
        """Finds the :class:`~oldman.resource.Resource` objects matching a given query.

        :param query: SPARQL SELECT query where the first variable assigned
                      corresponds to the IRIs of the resources that will be returned.
        :return: A generator of :class:`~oldman.resource.Resource` objects.
        """
        if "SELECT" not in query:
            raise OMSPARQLError(u"Not a SELECT query. Query: %s" % query)
        try:
            results = self._union_graph.query(query)
        except ParseException as e:
            raise OMSPARQLError(u"%s\n %s" % (query, e))
        return (self.get(id=unicode(r[0])) for r in results)

    def get(self, id=None, types=None, hashless_iri=None, **kwargs):
        """Gets the first :class:`~oldman.resource.Resource` object matching the given criteria.

        The `kwargs` dict can contains regular attribute key-values.

        When `id` is given, types are then checked.
        An :exc:`~oldman.exception.OMClassInstanceError` is raised if the resource
        is not instance of these classes.
        **Other criteria are not checked**.

        :param id: IRI of the resource. Defaults to `None`.
        :param types: IRIs of the RDFS classes filtered resources must be instance of. Defaults to `None`.
        :param hashless_iri: Hash-less IRI of filtered resources. Defaults to `None`.
        :return: A :class:`~oldman.resource.Resource` object or `None` if no resource has been found.
        """
        types = set(types) if types is not None else set()

        if id is not None:
            resource = self._get_by_id(id)
            if not types.issubset(resource.types):
                missing_types = types.difference(resource.types)
                raise OMClassInstanceError(u"%s found, but is not instance of %s" % (id, missing_types))
            if len(kwargs) > 0:
                self._logger.warn(u"get(): id given so attributes %s are just ignored" % kwargs.keys())
            return resource

        elif hashless_iri is None and len(kwargs) == 0:
            self._logger.warn(u"get() called without parameter. Returns the first resource found in the union graph.")
            query = u"SELECT ?s WHERE { ?s ?p ?o } LIMIT 1"
            try:
                results = self._union_graph.query(query)
            except ParseException as e:
                raise OMSPARQLParseError(u"%s\n %s" % (query, e))
            for r, in results:
                return self._get_by_id(unicode(r))
            # If no resource in the union graph
            return None

        if hashless_iri is not None:
            resources = self.filter(types=types, hashless_iri=hashless_iri, **kwargs)
            return self._select_resource_from_hashless_iri(hashless_iri, list(resources))

        # First found
        resources = self.filter(types=types, hashless_iri=hashless_iri, limit=1, **kwargs)
        for resource in resources:
            return resource

        return None

    def _get_by_id(self, id):
        resource = self.resource_cache.get_resource(id)
        if resource:
            return resource
        resource_graph = Graph()
        iri = URIRef(id)
        resource_graph += self._union_graph.triples((iri, None, None))
        self._logger.debug(u"All triples with subject %s loaded from the union_graph" % iri)
        # Extracts lists
        list_items_request = u"""
        SELECT ?subList ?value ?previous
        WHERE {
          <%s> ?p ?l .
          ?l rdf:rest* ?subList .
          ?subList rdf:first ?value .
          OPTIONAL { ?previous rdf:rest ?subList }
        }""" % id
        results = list(self._union_graph.query(list_items_request))
        for subList, value, previous in results:
            if previous is not None:
                resource_graph.add((previous, RDF.rest, subList))
            resource_graph.add((subList, RDF.first, value))

        return self._new_resource_object(id, resource_graph)

    def _new_resource_object(self, id, resource_graph):
        resource = Resource.load_from_graph(self._manager, id, resource_graph, is_new=(len(resource_graph) == 0))
        self.resource_cache.set_resource(resource)
        return resource

    def _select_resource_from_hashless_iri(self, hashless_iri, resources):
        if len(resources) == 0:
            raise OMObjectNotFoundError(u"No resource with hash-less iri %s" % hashless_iri)
        elif len(resources) > 1:
            for r in resources:
                if r.id == hashless_iri:
                    return r
            # TODO: avoid such arbitrary selection
            self._logger.warn(u"Multiple resources have the same base_uri: %s\n. "
                              u"The first one is selected." % resources)
        return resources[0]

    def _filter_lazily(self, query):
        """ Lazy filtering """
        self._logger.debug(u"Filter query: %s" % query)
        try:
            results = self._union_graph.query(query)
        except ParseException as e:
            raise OMSPARQLParseError(u"%s\n %s" % (query, e))

        # Generator expression
        return (self.get(id=unicode(r[0])) for r in results)

    def _filter_eagerly(self, sub_query, pre_cache_properties, erase_cache=False):
        """ Eager: requests all the properties of all returned resource
        within one single SPARQL query.

        One big query instead of a long sequence of small ones.
        """
        if pre_cache_properties is not None:
            properties = [u"<%s>" % p for p in pre_cache_properties]
            query = u"""SELECT DISTINCT ?s ?s2 ?p2 ?o2
            WHERE
            {
                 {
                  %s
                 }
                 {
                   ?s2 ?p2 ?o2 .
                   FILTER (?s = ?s2)
                 }
                 UNION
                 {
                   ?s ?sp ?s2 .
                   ?s2 ?p2 ?o2 .
                   VALUES ?sp { %s }
                 }
                FILTER (isIRI(?s2)) .
            }""" % (sub_query, " ".join(properties))
        else:
            query = u"""SELECT DISTINCT ?s ?p ?o
            WHERE
            {
              ?s ?p ?o .
                 {
                  %s
                 }
            }""" % sub_query

        self._logger.debug(u"Filter query: %s" % query)
        try:
            results = self._union_graph.query(query)
        except ParseException as e:
            raise OMSPARQLParseError(u"%s\n %s" % (query, e))

        main_resource_iris = set()
        resource_iris = set()
        graph = Graph()

        if pre_cache_properties is not None:
            for s, s2, p2, o2 in results:
                main_resource_iris.add(s)
                resource_iris.add(s2)
                graph.add((s2, p2, o2))
        else:
            # Same set
            resource_iris = main_resource_iris
            for s, p, o in results:
                # Also add it implicitly in main_resource_iris
                resource_iris.add(s)
                graph.add((s, p, o))

        main_resources = []
        if erase_cache:
            new_resource_iris = resource_iris
        else:
            new_resource_iris = []
            # Resource from cache
            for iri in resource_iris:
                resource = self.resource_cache.get_resource(iri)
                if resource is None:
                    new_resource_iris.append(iri)
                elif iri in main_resource_iris:
                    main_resources.append(resource)

        #TODO: retrieve list values on new resource iris

        for iri in new_resource_iris:
            # Resource created and set in the cache
            resource = self._new_resource_object(iri, graph)
            if iri in main_resource_iris:
                main_resources.append(resource)

        return main_resources

    def _save_resource_attributes(self, resource, attributes, former_types):
        id = resource.id

        former_lines = u""
        new_lines = u""
        for attr in attributes:
            if not attr.has_new_value(resource):
                continue

            former_value = attr.get_former_value(resource)
            former_lines += attr.serialize_value_into_lines(former_value)
            new_lines += attr.serialize_current_value_into_line(resource)

        if former_types is not None:
            types = set(resource.types)
            # New type
            for t in types.difference(former_types):
                type_line = u"<%s> a <%s> .\n" % (id, t)
                new_lines += type_line
            # Removed type
            for t in former_types.difference(types):
                type_line = u"<%s> a <%s> .\n" % (id, t)
                former_lines += type_line

        query = build_update_query_part(u"DELETE DATA", id, former_lines)
        if len(query) > 0:
            query += u" ;"
        query += build_update_query_part(u"INSERT DATA", id, new_lines)
        if len(query) > 0:
            self._logger.debug("Query: %s" % query)
            try:
                self._data_graph.update(query)
            except ParseException as e:
                raise OMSPARQLParseError(u"%s\n %s" % (query, e))

    def exists(self, id):
        return bool(self._union_graph.query(u"ASK {?id ?p ?o .}", initBindings={'id': URIRef(id)}))

    def generate_instance_number(self, class_iri):
        """ Needed for generating incremental IRIs
        """
        counter_query_req = unicode(self._counter_query_req).replace("?class_iri", u"<%s>" % class_iri)
        counter_update_req = unicode(self._counter_update_req).replace("?class_iri", u"<%s>" % class_iri)

        # Critical section
        self._iri_mutex.acquire()
        try:
            self._data_graph.update(counter_update_req)
            numbers = [int(r) for r, in self._data_graph.query(counter_query_req)]
        finally:
            self._iri_mutex.release()

        if len(numbers) == 0:
            raise OMDataStoreError(u"No counter for class %s (has disappeared)" % class_iri)
        elif len(numbers) > 1:
            raise OMDataStoreError(u"Multiple counter for class %s" % class_iri)

        return numbers[0]

    def check_counter(self, class_iri):
        """ Inits if needed.
        """
        counter_query_req = unicode(self._counter_query_req).replace("?class_iri", u"<%s>" % class_iri)
        numbers = list(self._data_graph.query(counter_query_req))
        # Inits if no counter
        if len(numbers) == 0:
            self.reset_instance_counter(class_iri)
        elif len(numbers) > 1:
            raise OMDataStoreError(u"Multiple counter for class %s" % class_iri)

    def reset_instance_counter(self, class_iri):
        """Resets the counter.

        For test purposes **only**.
        """
        delete_req = u"""
            PREFIX oldman: <urn:oldman:>
            DELETE {
                ?class_iri oldman:nextNumber ?number .
            }
            WHERE {
                ?class_iri oldman:nextNumber ?number .
            }""".replace("?class_iri", "<%s>" % class_iri)
        self._data_graph.update(delete_req)

        insert_req = u"""
            PREFIX oldman: <urn:oldman:>
            INSERT DATA {
                <%s> oldman:nextNumber 0 .
                }""" % class_iri
        self._data_graph.update(insert_req)


def _find_attribute(models, name):
    for m in models:
        if name in m.om_attributes:
            return m.access_attribute(name)
    raise OMAttributeAccessError(u"%s not found in models %s " % (name, [m.name for m in models]))