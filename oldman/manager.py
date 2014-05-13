from weakref import WeakValueDictionary
from rdflib import URIRef, Graph
from rdflib.plugins.sparql import prepareQuery
from rdflib.plugins.sparql.parser import ParseException
from .exception import OMClassInstanceError, OMSPARQLParseError
from .resource import Resource
from oldman.utils.sparql import build_query_part


class InstanceManager(object):
    def __init__(self, model, domain):
        self._model = model
        self._cache = WeakValueDictionary()
        self._domain = domain
        class_iri = model.class_iri
        if class_iri:
            self._check_type_request = prepareQuery(u"ASK {?s a <%s> }" % class_iri)
        else:
            self._check_type_request = None

    def create(self, **kwargs):
        """
            Creates a new instance and saves it
        """
        #TODO: improve it
        instance = Resource(self._domain, types=self._model.class_types, **kwargs)
        #instance = self._model(**kwargs)
        instance.save()
        return instance

    def clear_cache(self):
        """ Clears its cache """
        self._cache.clear()

    def filter(self, **kwargs):
        if "id" in kwargs:
            return self.get(**kwargs)

        lines = u""
        for name, value in kwargs.iteritems():
            # May raise a LDAttributeAccessError
            attr = self._model.access_attribute(name)
            value = kwargs[name]
            if value:
                lines += attr.serialize_values_into_lines(value)

        query = build_query_part(u"SELECT ?s WHERE", u"?s", lines)
        #print query
        try:
            results = self._domain.default_graph.query(query)
        except ParseException as e:
            raise OMSPARQLParseError(u"%s\n %s" % (query, e))

        # Generator expression
        return (self.get(id=str(r)) for r, in results)

    def get(self, id=None, **kwargs):
        if id:
            return self._get_by_id(id)

        # First found
        for instance in self.filter(**kwargs):
            return instance

        return None

    def _get_by_id(self, id):
        instance = self._cache.get(id)
        if instance:
            #print "%s found in the cache" % instance
            return instance
        instance_graph = Graph()
        iri = URIRef(id)
        instance_graph += self._domain.default_graph.triples((iri, None, None))
        if self._check_type_request and not self._domain.default_graph.query(self._check_type_request,
                                                                      initBindings={'s': iri}):
            raise OMClassInstanceError(u"%s is not an instance of %s" % (id, self._model.class_iri))
        return self._new_instance(id, instance_graph)

    def get_any(self, id):
        """ Finds a object from any model class """
        return self._domain.get(id=id)

    def _new_instance(self, id, instance_graph):
        #print "Instance graph: %s" % instance_graph.serialize(format="turtle")
        if len(instance_graph) == 0:
            instance = self._model.new(id=id)
        else:
            instance = Resource.load_from_graph(self._domain, id, instance_graph, is_new=False)
        self._cache[id] = instance
        return instance