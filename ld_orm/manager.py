from weakref import WeakValueDictionary
from rdflib import URIRef, Graph
import json

class InstanceManager(object):
    def __init__(self, cls, storage_graph):
        self.cls = cls
        self._graph = storage_graph
        self._cache = WeakValueDictionary()

    @property
    def graph(self):
        return self._graph

    def create(self, **kwargs):
        """
            Creates a new instance and saves it
        """
        instance = self.cls(**kwargs)
        instance.save()
        return instance

    def clear_cache(self):
        """Clears its cache """
        self._cache.clear()


    def filter(self, **kwargs):
        if "id" in kwargs:
            return self.get(**kwargs)

        values = {}
        for name, attr in self.cls._attributes.iteritems():
            if not name in kwargs:
                continue
            value = kwargs[name]
            if value:
                property_uri = attr.supported_property.property_uri
                values[property_uri] = attr.serialize_values(value)

        query = build_query_part("SELECT ?s WHERE", "?s", values)
        print query
        results = self._graph.query(query)

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
        # Str is not weak referenceable
        # TODO: resolve this pb
        instance = self._cache.get(id)
        if instance:
            print "%s found in the cache" % instance
            return instance
        instance_graph = Graph()
        instance_graph += self._graph.triples((URIRef(id), None, None))
        return self._new_instance(id, instance_graph)


    def _new_instance(self, id, instance_graph):
        if len(instance_graph) == 0:
            return None

        instance = self.cls.from_graph(id, instance_graph)
        self._cache[id] = instance
        return instance


    def __get__(self, instance, type=None):
        """
            Not accessible via model instances (like in Django)
        """
        if instance is not None:
            raise AttributeError("Manager isn't accessible via %s instances" % type.__name__)
        return self


def build_query_part(verb_and_vars, subject_term, prop_objects):
    if len(prop_objects) == 0:
        return ""
    query_part = "%s { " % verb_and_vars
    for p, objects in prop_objects.iteritems():
        if isinstance(objects, (list,set)):
            for o in objects:
                query_part += "  %s <%s> %s .\n" %(subject_term, p, o)
        else:
            o = objects
            query_part += "    %s <%s> %s .\n" %(subject_term, p, o)
    query_part += "} \n"
    return query_part


def build_update_query_part(verb, subject, prop_objects):
    return build_query_part(verb, "<%s>" % subject, prop_objects)