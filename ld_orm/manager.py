from weakref import WeakValueDictionary
from rdflib import URIRef, Graph


class InstanceManager(object):
    def __init__(self, cls, storage_graph, default_graph, schema_graph, registry):
        self._cls = cls
        self._storage_graph = storage_graph
        self._default_graph = default_graph
        self._schema_graph = schema_graph
        self._cache = WeakValueDictionary()
        self._registry = registry

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

        lines = ""
        # Access to a protected attribute: design choice
        # (We do not want a regular user to access to model.attributes)
        for name, attr in self._cls._attributes.iteritems():
            if not name in kwargs:
                continue
            value = kwargs[name]
            if value:
                lines += attr.serialize_values_into_lines(value)

        query = build_query_part("SELECT ?s WHERE", "?s", lines)
        #print query
        results = self._storage_graph.query(query)

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
        instance_graph += self._storage_graph.triples((URIRef(id), None, None))
        return self._new_instance(id, instance_graph)

    def get_any(self, id):
        """ Any class """
        other_class_manager = self.registry.find_class_manager(id)
        obj = other_class_manager.get(id=id)
        return obj

    def _new_instance(self, id, instance_graph):
        #print "Instance graph: %s" % instance_graph.serialize(format="turtle")
        if len(instance_graph) == 0:
            instance = self._cls(id=id)
        else:
            instance = self._cls.from_graph(id, instance_graph)
        self._cache[id] = instance
        return instance

    def __get__(self, instance, type=None):
        """
            Not accessible via model instances (like in Django)
        """
        if instance is not None:
            raise AttributeError("Manager isn't accessible via %s instances" % type.__name__)
        return self


def build_query_part(verb_and_vars, subject_term, lines):
    if len(lines) == 0:
        return ""
    query_part = '%s { \n%s } \n' % (verb_and_vars, lines)
    #{0} -> subject_term
    # format() does not work because other special symbols
    return query_part.replace("{0}", subject_term)


def build_update_query_part(verb, subject, lines):
    return build_query_part(verb, "<%s>" % subject, lines)