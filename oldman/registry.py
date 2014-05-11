from rdflib import RDF, URIRef
from rdflib.plugins.sparql import prepareQuery
from .exception import OMSchemaError, OMInternalError, OMObjectNotFoundError, OMHashIriError


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

    def get_object(self, object_uri):
        cls = self.find_model_class(object_uri)
        return cls.objects.get(id=object_uri)

    def find_object_iris(self, base_uri):
        if "#" in base_uri:
            raise OMHashIriError("%s is not a base IRI" % base_uri)
        #TODO: use initBindings instead (need a bugfix of rdflib)
        query = self.base_uri_raw_query.replace("?base", '"%s"' % base_uri)
        return {unicode(u) for u, in self._default_graph.query(query)}

    def find_model_class(self, object_uri):
        types = extract_types(object_uri, self._default_graph)
        return self.select_model_class(types)

    def find_object_from_base_uri(self, base_uri):
        obj_uris = self.find_object_iris(base_uri)
        if len(obj_uris) == 0:
            raise OMObjectNotFoundError("No object with base uri %s" % base_uri)
        elif len(obj_uris) > 1:
            if base_uri in obj_uris:
                return base_uri
            # Warning
            import sys
            sys.stderr.write("Multiple objects have the same base_uri: %s\n. "
                             "The first one is selected." % obj_uris)
            # TODO: avoid such arbitrary selection
        return list(obj_uris)[0]

    def select_model_class(self, types):
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
                raise OMSchemaError("Cannot make a choice between classes %s" % remaining_models)
            raise OMInternalError("No remaining model class from %s" % models)

        else:
            #Untyped one
            untyped_model = self._model_classes.get(None)
            if untyped_model:
                return untyped_model

        raise OMInternalError("No model found, no untyped model registered")


def extract_types(object_uri, graph):
    return {t.toPython() for t in graph.objects(URIRef(object_uri), RDF.type)}


ANCESTRY_REQUEST = prepareQuery("""
                                SELECT ?class ?parent WHERE {
                                    ?child_class rdfs:subClassOf* ?class.
                                    ?class rdfs:subClassOf ?parent.
                                    FILTER NOT EXISTS { ?class rdfs:subClassOf ?other .
                                                        ?other rdfs:subClassOf+ ?parent . }
                                }""")


def extract_ancestry(class_uri, schema_graph):
    """
        Useful because class_uri is often a local specialization
        of a well-known class
    """
    ancestry = {}
    results = schema_graph.query(ANCESTRY_REQUEST, initBindings={'child_class': URIRef(class_uri)})
    for c, parent in results:
        cls_uri = unicode(c)
        parent_uri = unicode(parent)
        if cls_uri in ancestry:
            ancestry[cls_uri].add(parent_uri)
        else:
            ancestry[cls_uri] = {parent_uri}
    return ancestry


def extract_types_from_bottom(child_class_uri, ancestry_dict):
    anti_chrono = [child_class_uri]
    for class_uri in anti_chrono:
        parents = ancestry_dict.get(class_uri, [])
        anti_chrono += [p for p in parents if p not in anti_chrono]
    return anti_chrono


class ClassAncestry(object):
    def __init__(self, child_class_uri, schema_graph):
        self._child_class_uri = child_class_uri
        if child_class_uri is None:
            self._ancestry_dict = {}
            self._bottom_up_list = []
        else:
            self._ancestry_dict = extract_ancestry(child_class_uri, schema_graph)
            self._bottom_up_list = extract_types_from_bottom(child_class_uri, self._ancestry_dict)

    @property
    def child(self):
        return self._child_class_uri

    @property
    def bottom_up(self):
        """
            Starting from the child
        """
        return self._bottom_up_list

    @property
    def top_down(self):
        chrono = list(self._bottom_up_list)
        chrono.reverse()
        return chrono

    def parents(self, class_uri):
        return self._ancestry.get(class_uri)