from rdflib import RDF, URIRef, Literal
from rdflib.plugins.sparql import prepareQuery
from .exceptions import SchemaError, LDInternalError, ObjectNotFoundError


class ModelRegistry(object):
    """
        All model classes are registered here
    """

    #TODO: replace by a prepareQuery

    base_uri_raw_query = """
        SELECT DISTINCT ?uri
        WHERE {
            ?uri ?p ?o .
            FILTER (REGEX(STR(?uri), CONCAT(?base, "#")) || (STR(?uri) = ?base) )
         } """

    def __init__(self, default_graph):
        self._model_classes = {}
        self._default_graph = default_graph

    def register(self, model_class):
        self._model_classes[model_class.class_uri] = model_class

    def unregister(self, model_class):
        self._model_classes.pop(model_class.class_uri)

    def get_model_class(self, class_uri):
        return self._model_classes.get(class_uri)

    def find_object(self, object_uri):
        cls = self.find_model_class(object_uri)
        return cls.objects.get(id=object_uri)

    def find_model_class(self, object_uri):
        types = {t.toPython() for t in self._default_graph.objects(URIRef(object_uri), RDF.type)}
        return self._select_model_class(types)

    def find_object_from_base_uri(self, base_uri):
        #TODO: use initBindings instead (need a bugfix)
        #obj_uris = [u for u, in self._default_graph.query(self.base_uri_raw_query,
        #                                                  initBindings={'base': Literal(base_uri)})]
        query = self.base_uri_raw_query.replace("?base", '"%s"' % base_uri)
        obj_uris = [u for u, in self._default_graph.query(query)]


        if len(obj_uris) == 0:
            raise ObjectNotFoundError("No object with base uri %s" % base_uri)
        elif len(obj_uris) > 1:
            # Warning
            import sys
            sys.stderr.write("Multiple objects have the same base_uri: %s\n. "
                             "The first one is selected." % obj_uris)
            # TODO: avoid such arbitrary selection
        return obj_uris[0]

    def _select_model_class(self, types):
        models = set()
        for t in types:
            model = self._model_classes.get(t)
            if model is not None:
                models.add(model)

        if len(models) == 1:
            return list(models)[0]
        elif len(models) > 1:
            remaining_models = list(models)
            for model in models:
                for remaining in remaining_models:
                    if (model != remaining) and issubclass(remaining, model):
                        remaining_models.remove(model)
                        break
            if len(remaining_models) == 1:
                return remaining_models[0]
            if len(remaining_models) > 1:
                raise SchemaError("Cannot make a choice between classes %s" % remaining_models)
            raise LDInternalError("No remaining model class from %s" % models)

        else:
            #Untyped one
            untyped_model = self._model_classes.get(None)
            if untyped_model:
                return untyped_model

        raise LDInternalError("No model found, no untyped model registered")