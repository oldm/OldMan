from rdflib import RDF, URIRef
from .exceptions import SchemaError, LDInternalError


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

    def find_instance_manager(self, object_uri):
        types = {t.toPython() for t in self._default_graph.objects(URIRef(object_uri), RDF.type)}

        models = set()
        for t in types:
            model = self._model_classes.get(t)
            if model is not None:
                models.add(model)

        if len(models) == 1:
            return list(models)[0].objects
        elif len(models) > 1:
            remaining_models = list(models)
            for model in models:
                for remaining in remaining_models:
                    if (model != remaining) and issubclass(remaining, model):
                        remaining_models.remove(model)
                        break
            if len(remaining_models) == 1:
                return remaining_models[0].objects
            if len(remaining_models) > 1:
                raise SchemaError("Cannot make a choice between classes %s for object %s"
                                  % (remaining_models, object_uri))
            raise LDInternalError("No remaining model class from %s" % models)

        else:
            #Untyped one
            untyped_model = self._model_classes.get(None)
            if untyped_model:
                return untyped_model.objects

        raise LDInternalError("No model found, no untyped model registered")