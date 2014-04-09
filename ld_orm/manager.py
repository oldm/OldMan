#from weakref import WeakKeyDictionary
from rdflib import URIRef, Graph
import json

class InstanceManager(object):
    def __init__(self, cls, storage_graph):
        self.cls = cls
        self._graph = storage_graph
        # TODO: find a way to use a WeakKeyDictionary
        #self._cache = WeakKeyDictionary()
        self._cache = {}

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

    def clear(self):
        """Clears its cache """
        self._cache.clear()

    def get(self, id=None, **kwargs):
        if id:
            # Str is not weak referenceable
            instance = self._cache.get(id)
            if instance:
                print "%s found in the cache" % instance
                return instance
            instance_graph = Graph()
            instance_graph += self._graph.triples((URIRef(id), None, None))
            return self._new_instance(id, instance_graph)

        else:
            # TODO: continue
            raise NotImplementedError()

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

