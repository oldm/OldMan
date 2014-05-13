from rdflib import RDF, URIRef
from rdflib.plugins.sparql import prepareQuery
from .exception import OMSchemaError, OMInternalError, OMObjectNotFoundError, OMHashIriError
from .exception import AlreadyAllocatedModelError


#TODO: replace it with a dereferenceable URL
"""
    ?cls <urn:oldman:test:model:ordering:hasPriority> [
        <urn:oldman:test:model:ordering:class> ?parent1 ;
        <urn:oldman:test:model:ordering:priority> 2
    ],
    [
     etc.
    ].
"""
MODEL_HAS_PRIORITY_IRI = "urn:oldman:test:model:ordering:hasPriority"
MODEL_PRIORITY_CLASS_IRI = "urn:oldman:test:model:ordering:class"
MODEL_PRIORITY_IRI = "urn:oldman:test:model:ordering:priority"


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
        self._model_names = {}
        self._default_graph = default_graph

    @property
    def default_graph(self):
        return self._default_graph

    def register(self, model_class, short_name):
        class_iri = model_class.class_iri
        if class_iri in self._model_classes:
            raise AlreadyAllocatedModelError("%s is already allocated to %s" %
                                             (class_iri, self._model_classes[class_iri]))
        if short_name in self._model_names:
            raise AlreadyAllocatedModelError("%s is already allocated to %s" %
                                             (short_name, self._model_names[short_name].class_iri))
        self._model_classes[class_iri] = model_class
        self._model_names[short_name] = model_class

    def unregister(self, model_class):
        self._model_classes.pop(model_class.class_uri)
        self._model_classes.pop(model_class.name)

    def get_model(self, class_iri):
        return self._model_classes.get(class_iri)

    def get_models(self, types):
        if types is None or len(types) == 0:
            # Default model
            return [self._model_names["Thing"]]
        models = set()
        for t in types:
            model = self._model_classes.get(t)
            if model is not None:
                models.add(model)
        return models

    def get_object(self, object_iri):
        model = self.find_model(object_iri)
        return model.objects.get(id=object_iri)

    def find_object_iris(self, base_iri):
        if "#" in base_iri:
            raise OMHashIriError("%s is not a base IRI" % base_iri)
        #TODO: use initBindings instead (need a bugfix of rdflib)
        query = self.base_uri_raw_query.replace("?base", '"%s"' % base_iri)
        return {unicode(u) for u, in self._default_graph.query(query)}

    def find_model(self, object_iri):
        types = extract_types(object_iri, self._default_graph)
        return self.select_model(self.get_models(types))

    def find_object_from_base_uri(self, base_iri):
        obj_uris = self.find_object_iris(base_iri)
        if len(obj_uris) == 0:
            raise OMObjectNotFoundError("No object with base uri %s" % base_iri)
        elif len(obj_uris) > 1:
            if base_iri in obj_uris:
                return base_iri
            # Warning
            import sys
            sys.stderr.write("Multiple objects have the same base_uri: %s\n. "
                             "The first one is selected." % obj_uris)
            # TODO: avoid such arbitrary selection
        return list(obj_uris)[0]

    def select_model(self, models):
        """
            TODO: refactor it according to class ancestry
        """
        if len(models) == 1:
            return list(models)[0]
        elif len(models) > 1:
            remaining_models = list(models)
            for model in models:
                for remaining in remaining_models:
                    if (model != remaining) and remaining.is_subclass_of(model):
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


def extract_types(object_iri, graph):
    return {t.toPython() for t in graph.objects(URIRef(object_iri), RDF.type)}


ANCESTRY_REQUEST = prepareQuery("""
                                SELECT ?class ?parent ?priority WHERE {
                                    ?child_class rdfs:subClassOf* ?class.
                                    ?class rdfs:subClassOf ?parent.
                                    OPTIONAL {
                                        ?class <urn:oldman:test:model:ordering:hasPriority> ?p .
                                        ?p <urn:oldman:test:model:ordering:class> ?parent ;
                                           <urn:oldman:test:model:ordering:priority> ?priority .
                                    }.
                                    FILTER NOT EXISTS { ?class rdfs:subClassOf ?other .
                                                        ?other rdfs:subClassOf+ ?parent . }
                                } ORDER BY DESC(?priority)
                                """)


def _extract_ancestry(class_iri, schema_graph):
    """
        Useful because class_iri is often a local specialization
        of a well-known class
    """
    ancestry_dict = {}
    results = schema_graph.query(ANCESTRY_REQUEST, initBindings={'child_class': URIRef(class_iri)})
    for c, parent, pr in results:
        priority = pr.toPython() if pr is not None else None
        cls_iri = unicode(c)
        parent_iri = unicode(parent)
        if cls_iri in ancestry_dict:
            ancestry_dict[cls_iri].append((parent_iri, priority))
        else:
            ancestry_dict[cls_iri] = [(parent_iri, priority)]
    return ancestry_dict


def _extract_types_from_bottom(child_class_iri, ancestry_dict, ignored_types=None):
    """
        ignored_types is only for recursive call.
    """
    ignored_types = list(ignored_types) if ignored_types else []
    if child_class_iri in ignored_types:
        raise OMInternalError("%s should not be in %s" %(child_class_iri, ignored_types))

    anti_chrono = [child_class_iri]
    for class_iri in anti_chrono:
        prioritized_parents = ancestry_dict.get(class_iri, [])

        # Prioritizes if there are different priorities
        prioritize = (len({priority for _, priority in prioritized_parents}) > 1)
        if prioritize:
            for parent, _ in prioritized_parents:
                if (parent not in ignored_types) and (parent not in anti_chrono):
                    # Hybrid recursive style
                    anti_chrono += _extract_types_from_bottom(parent, ancestry_dict, anti_chrono)
        else:
            anti_chrono += [parent for parent, _ in prioritized_parents if parent not in ignored_types
                            and parent not in anti_chrono]
    return anti_chrono


class ClassAncestry(object):
    def __init__(self, child_class_iri, schema_graph):
        self._child_class_iri = child_class_iri
        if child_class_iri is None:
            self._ancestry_dict = {}
            self._bottom_up_list = []
        else:
            self._ancestry_dict = _extract_ancestry(child_class_iri, schema_graph)
            self._bottom_up_list = _extract_types_from_bottom(child_class_iri, self._ancestry_dict)

    @property
    def child(self):
        return self._child_class_iri

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

    def parents(self, class_iri):
        return [parent for parent, _ in self._ancestry_dict.get(class_iri, [])]