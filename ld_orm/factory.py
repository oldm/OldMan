import json
from urlparse import urlparse
from rdflib import Graph
from .model import Model
from .registry import ModelRegistry
from .exceptions import UndeclaredClassNameError, ReservedAttributeNameError
from .uri import RandomPrefixedUriGenerator


def default_model_factory(schema_graph, default_graph):
    from ld_orm.extraction.attribute import LDAttributeExtractor
    attr_extractor = LDAttributeExtractor()
    return ModelFactory(attr_extractor, schema_graph, default_graph)


class ModelFactory(object):

    def __init__(self, attr_manager, schema_graph, default_graph):
        self._attr_manager = attr_manager
        self._registry = ModelRegistry(default_graph)
        self._schema_graph = schema_graph
        self._default_graph = default_graph

        # Registered with the "None" key
        self._generate("DefaultModel", {"@context": {}}, default_graph, untyped=True,
                       uri_prefix="http://localhost/.well-known/genid/default/")

    @property
    def registry(self):
        return self._registry

    def generate(self, class_name, context, storage_graph, uri_prefix=None,
                 uri_generator=None):
        """
            Generates a model class
        """
        return self._generate(class_name, context, storage_graph, uri_prefix, uri_generator)

    def _generate(self, class_name, context, storage_graph, uri_prefix=None,
                  uri_generator=None, untyped=False):

        # Only for the DefaultModel
        if untyped:
            class_uri = None
            types = set()
            attributes = {}
        else:
            class_uri = extract_class_uri(class_name, context)
            types = extract_types(class_uri, self._schema_graph)
            attributes = self._attr_manager.extract(class_uri, context,
                                                    self._schema_graph)
        if uri_generator:
            id_generator = uri_generator
        elif uri_prefix:
            id_generator = RandomPrefixedUriGenerator(prefix=uri_prefix)
        else:
            raise TypeError("Please specify uri_prefix or uri_generator")

        special_attributes = {"class_uri": class_uri,
                              "types": types,
                              "_context_dict": context,
                              "_id_generator": id_generator,
                              "_storage_graph": storage_graph,
                              # Non-attributes (will be popped)
                              "registry": self.registry}

        # First reserved attribute check
        for name in special_attributes:
            if name in attributes:
                raise ReservedAttributeNameError("%s is reserved" % name)
        attributes.update(special_attributes)

        return type(class_name, (Model,), attributes)


def extract_class_uri(class_name, context):
    """
        Extracts the class URI as the type of a blank node
    """
    g = Graph().parse(data=json.dumps({"@type": class_name}),
                      context=context, format="json-ld")
    class_uri = str(g.objects().next())

    # Check the URI
    result = urlparse(class_uri)
    if result.scheme == "file":
        raise UndeclaredClassNameError("Deduced URI %s is not a valid HTTP URL" % class_uri)
    return class_uri


def extract_types(class_uri, schema_graph):
    """
        Useful because class_uri is often a local specialization
        of a well-known class
    """
    types = {class_uri}
    results = schema_graph.query("SELECT ?c WHERE { <%s> rdfs:subClassOf+ ?c }" % class_uri)
    types.update([str(r) for r, in results])
    return types