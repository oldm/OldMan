import logging
from rdflib import URIRef, Graph, RDF
from rdflib.plugins.sparql.parser import ParseException
from oldman.resource import Resource
from oldman.utils.sparql import build_query_part
from oldman.exception import OMSPARQLParseError, OMAttributeAccessError, OMClassInstanceError, OMSPARQLError
from oldman.exception import OMHashIriError, OMObjectNotFoundError


class ResourceFinder(object):
    """A :class:`~oldman.management.finder.ResourceFinder` object retrieves
    :class:`~oldman.resource.Resource` objects.

    :param manager: The :class:`~oldman.management.manager.ResourceManager` object.
                    It gives access to RDF graphs.
    """

    def __init__(self, manager):
        self._manager = manager
        self._logger = logging.getLogger(__name__)

    def filter(self, types=None, base_iri=None, limit=None, eager=False, eager_properties=None, **kwargs):
        """Finds the :class:`~oldman.resource.Resource` objects matching the given criteria.

        The `kwargs` dict can contains:

           1. regular attribute key-values ;
           2. the special attribute `id`. If given, :func:`~oldman.management.finder.Finder.get` is called.

        :param types: IRIs of the RDFS classes filtered resources must be instance of. Defaults to `None`.
        :param base_iri: base IRI of filtered resources. Defaults to `None`.
        :param limit: Upper bound on the number of solutions returned (SPARQL LIMIT). Positive integer.
                      Defaults to `None`.
        :param eager: If `True` loads all the Resource objects within one single SPARQL query.
                      Defaults to `False` (lazy).
        :param eager_properties: List of RDF properties to follow eagerly.
                      Defaults to `[]`. If given, `eager` must be `True`. Not yet supported.
        :return: A generator (if lazy) or a list (if eager) of :class:`~oldman.resource.Resource` objects.
        """
        if not eager and eager_properties is not None:
            raise AttributeError(u"Eager properties are incompatible with lazyness. Please set eager to True.")

        id = kwargs.pop("id") if "id" in kwargs else None
        type_iris = types if types is not None else []
        if id is not None:
            return self.get(id=id, types=types, base_iri=base_iri, **kwargs)

        if len(type_iris) == 0 and len(kwargs) > 0:
            raise OMAttributeAccessError(u"No type given in filter() so attributes %s are ambiguous."
                                         % kwargs.keys())
        elif len(type_iris) == 0 and len(kwargs) == 0:
            if base_iri is None:
                self._logger.warn(u"filter() called without parameter. Returns every resource in the union graph.")
            lines = u"?s ?p ?o . \n"
        else:
            type_set = set(types) if types is not None else set()
            models, _ = self._manager.find_models_and_types(type_set)

            lines = u""
            for type_iri in type_iris:
                lines += u"?s a <%s> .\n" % type_iri

            for name, value in kwargs.iteritems():
                # May raise a OMAttributeAccessError
                attr = _find_attribute(models, name)
                value = kwargs[name]
                if value:
                    lines += attr.serialize_value_into_lines(value)

        if base_iri is not None:
            if "#" in base_iri:
                raise OMHashIriError(u"%s is not a base IRI" % base_iri)
            lines += u"""FILTER (REGEX(STR(?s), CONCAT(?base, "#")) || (STR(?s) = ?base) )""".replace(
                u"?base", u'"%s"' % base_iri)

        query = build_query_part(u"SELECT DISTINCT ?s WHERE", u"?s", lines)
        if limit is not None:
            query += u"LIMIT %d" % limit

        if eager:
            return self._filter_eagerly(query, limit, eager_properties)
        # Lazy (by default)
        return self._filter_lazily(query, limit)


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
                raise OMClassInstanceError(u"%s found, but is not instance of %s" % (id, missing_types))
            if len(kwargs) > 0:
                self._logger.warn(u"get(): id given so attributes %s are just ignored" % kwargs.keys())
            return resource

        elif base_iri is None and len(kwargs) == 0:
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

        if base_iri is not None:
            resources = self.filter(types=types, base_iri=base_iri, **kwargs)
            return self._select_resource_from_base_iri(base_iri, list(resources))

        # First found
        resources = self.filter(types=types, base_iri=base_iri, limit=1, **kwargs)
        for resource in resources:
            return resource

        return None

    def _get_by_id(self, id):
        resource = self._manager.resource_cache.get_resource(id)
        if resource:
            return resource
        resource_graph = Graph()
        iri = URIRef(id)
        resource_graph += self._manager.union_graph.triples((iri, None, None))
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
        results = list(self._manager.union_graph.query(list_items_request))
        for subList, value, previous in results:
            if previous is not None:
                resource_graph.add((previous, RDF.rest, subList))
            resource_graph.add((subList, RDF.first, value))

        return self._new_resource_object(id, resource_graph)

    def _new_resource_object(self, id, resource_graph):
        resource = Resource.load_from_graph(self._manager, id, resource_graph, is_new=(len(resource_graph) == 0))
        self._manager.resource_cache.set_resource(resource)
        return resource

    def _select_resource_from_base_iri(self, base_iri, resources):
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

    def _filter_lazily(self, query, limit):
        """ Lazy filtering """
        self._logger.debug(u"Filter query: %s" % query)
        try:
            results = self._manager.union_graph.query(query)
        except ParseException as e:
            raise OMSPARQLParseError(u"%s\n %s" % (query, e))

        # Generator expression
        return (self.get(id=unicode(r[0])) for r in results)

    def _filter_eagerly(self, sub_query, limit, eager_properties, erase_cache=False):
        """ Eager: requests all the properties of all returned resource
        within one single SPARQL query.

        One big query instead of a lot of small ones sent sequently.
        """
        if eager_properties is not None:
            properties = [u"<%s>" % p for p in eager_properties]
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
            results = self._manager.union_graph.query(query)
        except ParseException as e:
            raise OMSPARQLParseError(u"%s\n %s" % (query, e))


        main_resource_iris = set()
        resource_iris = set()
        graph = Graph()

        if eager_properties is not None:
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
                resource = self._manager.resource_cache.get_resource(iri)
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

def _find_attribute(models, name):
    for m in models:
        if name in m.om_attributes:
            return m.access_attribute(name)
    raise OMAttributeAccessError(u"%s not found in models %s " % (name, [m.name for m in models]))