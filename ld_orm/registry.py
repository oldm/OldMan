from rdflib.plugins.sparql import prepareQuery
from rdflib import RDF, URIRef


class ModelRegistry(object):
    """
        All model classes are registered here
    """

    def __init__(self, default_graph):
        self._model_classes = {}
        self._default_graph = default_graph

    def register(self, model_class):
        self._model_classes[model_class.class_uri] = model_class

    def unregister(self, model_class):
        self._model_classes.pop(model_class.class_uri)

    def get_model_class(self, class_uri):
        return self._model_classes.get(class_uri)

    def find_class_manager(self, object_uri):
        types = self._default_graph.objects(URIRef(object_uri), RDF["type"])
        for t in types:
            class_uri = str(t)
            if class_uri in self._model_classes:
                return self.get_model_class(class_uri).objects

        #Untyped one
        untyped_model = self._model_classes.get(None)
        if untyped_model:
            return untyped_model.objects

        raise Exception("No model found, no untyped model registered")

