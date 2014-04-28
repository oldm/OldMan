from weakref import WeakValueDictionary
from rdflib import URIRef, Graph
from rdflib.plugins.sparql import prepareQuery
from rdflib.plugins.sparql.parser import ParseException
from .exceptions import ClassInstanceError, SPARQLParseError


class InstanceManager(object):
    def __init__(self, cls, storage_graph, registry):
        self._cls = cls
        self._storage_graph = storage_graph
        self._cache = WeakValueDictionary()
        self._registry = registry
        class_uri = cls.class_uri
        if class_uri:
            self._check_type_request = prepareQuery(u"ASK {?s a <%s> }" % class_uri)
        else:
            self._check_type_request = None

    @property
    def storage_graph(self):
        return self._storage_graph

    @property
    def registry(self):
        return self._registry

    def create(self, **kwargs):
        """
            Creates a new instance and saves it
        """
        instance = self._cls(**kwargs)
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
            attr = self._cls.get_attribute(name)
            value = kwargs[name]
            if value:
                lines += attr.serialize_values_into_lines(value)

        query = build_query_part(u"SELECT ?s WHERE", u"?s", lines)
        #print query
        try:
            results = self._storage_graph.query(query)
        except ParseException as e:
            raise SPARQLParseError(u"%s\n %s" % (query, e))

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
        uri = URIRef(id)
        instance_graph += self._storage_graph.triples((uri, None, None))
        if self._check_type_request and not self._storage_graph.query(self._check_type_request,
                                                                      initBindings={'s': uri}):
            raise ClassInstanceError(u"%s is not an instance of %s" % (id, self._cls.__name__))
        return self._new_instance(id, instance_graph)

    def get_any(self, id):
        """ Any class """
        other_class_manager = self.registry.find_instance_manager(id)
        obj = other_class_manager.get(id=id)
        return obj

    def _new_instance(self, id, instance_graph):
        #print "Instance graph: %s" % instance_graph.serialize(format="turtle")
        if len(instance_graph) == 0:
            instance = self._cls(id=id)
        else:
            instance = self._cls.load_from_graph(id, instance_graph, create=False)
        self._cache[id] = instance
        return instance

    def __get__(self, instance, type=None):
        """
            Not accessible via model instances (like in Django)
        """
        if instance is not None:
            raise AttributeError(u"Manager isn't accessible via %s instances" % type.__name__)
        return self


def build_query_part(verb_and_vars, subject_term, lines):
    if len(lines) == 0:
        return ""
    query_part = u'%s { \n%s } \n' % (verb_and_vars, lines)
    #{0} -> subject_term
    # format() does not work because other special symbols
    return query_part.replace(u"{0}", subject_term)


def build_update_query_part(verb, subject, lines):
    return build_query_part(verb, u"<%s>" % subject, lines)