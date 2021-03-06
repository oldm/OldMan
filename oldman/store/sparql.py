import logging
from threading import Lock

from rdflib import URIRef, Graph, RDF
from rdflib.plugins.sparql.parser import ParseException

from oldman.utils.sparql import build_query_part, build_update_query_part
from oldman.model.manager import ModelManager
from oldman.exception import OMSPARQLParseError, OMAttributeAccessError, OMSPARQLError
from oldman.exception import OMHashIriError
from oldman.exception import OMDataStoreError
from .datastore import DataStore


class SPARQLDataStore(DataStore):
    """A :class:`~oldman.store.sparql.SPARQLDataStore` is a :class:`~oldman.store.datastore.DataStore` object
    relying on a SPARQL 1.1 endpoint (Query and Update).

    :param data_graph: :class:`rdflib.graph.Graph` object where all the non-schema resources are stored by default.
    :param union_graph: Union of all the named graphs of a :class:`rdflib.ConjunctiveGraph` or a
                        :class:`rdflib.Dataset`.
                        Super-set of `data_graph` and may also include `schema_graph`.
                        Defaults to `data_graph`.
                        Read-only.
    :param cache_region: :class:`dogpile.cache.region.CacheRegion` object.
                         This object must already be configured.
                         Defaults to None (no cache).
                         See :class:`~oldman.store.cache.ResourceCache` for further details.

    TODO: explain the choice between schema_graph and resource_manager
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

    def __init__(self, data_graph, schema_graph=None, model_manager=None, union_graph=None, cache_region=None):
        manager = model_manager if model_manager is not None else ModelManager(schema_graph)
        DataStore.__init__(self, manager, cache_region, support_sparql=True)
        self._logger = logging.getLogger(__name__)
        self._data_graph = data_graph
        self._union_graph = union_graph if union_graph is not None else data_graph

    def extract_prefixes(self, other_graph):
        """Adds the RDF prefix (namespace) information from an other graph
        to the namespace of the `data_graph`.
        :param other_graph: `rdflib.graph.Graph` that some prefix information.
        """
        for prefix, namespace in other_graph.namespace_manager.namespaces():
            self._data_graph.bind(prefix, namespace)

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

    def exists(self, id):
        return bool(self._union_graph.query(u"ASK {?id ?p ?o .}", initBindings={'id': URIRef(id)}))

    def generate_instance_number(self, class_iri):
        """ Needed for generating incremental IRIs. """
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

    def check_and_repair_counter(self, class_iri):
        """ Checks the counter of a given RDFS class and repairs (inits) it if needed.

        :param class_iri: RDFS class IRI.
        """
        counter_query_req = unicode(self._counter_query_req).replace("?class_iri", u"<%s>" % class_iri)
        numbers = list(self._data_graph.query(counter_query_req))
        # Inits if no counter
        if len(numbers) == 0:
            self.reset_instance_counter(class_iri)
        elif len(numbers) > 1:
            raise OMDataStoreError(u"Multiple counter for class %s" % class_iri)

    def reset_instance_counter(self, class_iri):
        """ Reset the counter related to a given RDFS class.

        For test purposes **only**.

        :param class_iri: RDFS class IRI.
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

    def _get_first_resource_found(self):
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

    def _get_by_id(self, id, eager_with_reversed_attributes=True):
        resource = self.resource_cache.get_resource(id)
        if resource:
            return resource
        resource_graph = Graph()
        iri = URIRef(id)

        eager = eager_with_reversed_attributes and self.model_manager.include_reversed_attributes
        if eager:
            #TODO: look at specific properties and see if it improves the performance
            triple_query = u"""SELECT ?s ?p ?o
            WHERE {
               {
                  ?s ?p ?o .
                  VALUES ?s { ?subject }
               }
               UNION
               {
                 ?s ?p ?o .
                 VALUES ?o { ?subject }
               }
            }""".replace("?subject", "<%s>" % iri)
            for s, p, o in self._union_graph.query(triple_query):
                resource_graph.add((s, p, o))
        #Lazy
        else:
            resource_graph += self._union_graph.triples((iri, None, None))

            if self.model_manager.include_reversed_attributes:
                #Extracts the types
                types = {unicode(o) for o in resource_graph.objects(iri, RDF.type)}
                models, _ = self.model_manager.find_models_and_types(types)

                #TODO: improve by looking at specific properties
                if True in [m.include_reversed_attributes for m in models]:
                    resource_graph += self._union_graph.triples((None, None, iri))

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

    def _filter(self, type_iris, hashless_iri, limit, eager, pre_cache_properties, **kwargs):
        if len(type_iris) == 0 and len(kwargs) == 0:
            if hashless_iri is None:
                self._logger.warn(u"filter() called without parameter. Returns every resource in the union graph.")
            lines = u"?s ?p ?o . \n"
        else:
            type_set = set(type_iris)
            models, _ = self.model_manager.find_models_and_types(type_set)

            lines = u""
            for type_iri in type_iris:
                lines += u"?s a <%s> .\n" % type_iri

            for name, value in kwargs.iteritems():
                # May raise a OMAttributeAccessError
                attr = _find_attribute(models, name)
                value = kwargs[name]
                if value:
                    lines += attr.value_to_nt(value)

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
        """Eager: requests all the properties of all returned resource
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
        """Makes a SPARQL DELETE-INSERT request to save the changes into the `data_graph`."""
        id = resource.id

        former_lines = u""
        new_lines = u""
        for attr in attributes:
            if not attr.has_changed(resource):
                continue

            former_value, _ = attr.diff(resource)
            former_lines += attr.value_to_nt(former_value)
            new_lines += attr.to_nt(resource)

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

        # Same IRI (no change)
        return id


def _find_attribute(models, name):
    for m in models:
        if name in m.om_attributes:
            return m.access_attribute(name)
    raise OMAttributeAccessError(u"%s not found in models %s " % (name, [m.name for m in models]))