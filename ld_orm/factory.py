import json
from urlparse import urlparse
from rdflib import Graph
from .model import Model
from .registry import ModelRegistry
from .exceptions import UndeclaredClassNameError, ReservedAttributeNameError
from .iri import RandomPrefixedIriGenerator, IncrementalIriGenerator, BlankNodeIriGenerator
from .ancestry import Ancestry
from ld_orm.parsing.schema.attribute import LDAttributeExtractor


def default_model_factory(schema_graph, default_graph):
    attr_extractor = LDAttributeExtractor()
    return ModelFactory(attr_extractor, schema_graph, default_graph)


class ModelFactory(object):

    def __init__(self, attr_manager, schema_graph, default_graph):
        self._attr_manager = attr_manager
        self._registry = ModelRegistry(default_graph)
        self._schema_graph = schema_graph
        self._default_graph = default_graph
        self._methods = {}
        # Registered with the "None" key
        self._generate("DefaultModel", {u"@context": {}}, default_graph, untyped=True,
                       uri_prefix=u"http://localhost/.well-known/genid/default/")

    @property
    def registry(self):
        return self._registry

    def add_method(self, method, name, class_uri):
        if class_uri in self._methods:
            self._methods[class_uri].append((method, name))
        else:
            self._methods[class_uri] = [(method, name)]

    def generate(self, class_name, context, storage_graph, uri_prefix=None,
                 uri_fragment=None, uri_generator=None, incremental_uri=False):
        """
            Generates a model class
        """
        return self._generate(class_name, context, storage_graph, uri_prefix=uri_prefix, uri_fragment=uri_fragment,
                              uri_generator=uri_generator, incremental_uri=incremental_uri)

    def _generate(self, class_name, context, storage_graph, uri_prefix=None, uri_fragment=None,
                  uri_generator=None, untyped=False, incremental_uri=False):

        # Only for the DefaultModel
        if untyped:
            class_uri = None
            ancestry = Ancestry(class_uri, self._schema_graph)
            attributes = {}
        else:
            class_uri = extract_class_uri(class_name, context)
            ancestry = Ancestry(class_uri, self._schema_graph)
            attributes = self._attr_manager.extract(class_uri, ancestry.bottom_up, context,
                                                    self._schema_graph)
        if uri_generator is not None:
            id_generator = uri_generator
        elif uri_prefix is not None:
            if incremental_uri:
                id_generator = IncrementalIriGenerator(uri_prefix,
                                                       storage_graph,
                                                       class_uri,
                                                       fragment=uri_fragment)
            else:
                id_generator = RandomPrefixedIriGenerator(uri_prefix,
                                                          fragment=uri_fragment)
        else:
            id_generator = BlankNodeIriGenerator()

        special_attributes = {"class_uri": class_uri,
                              "_ancestry": ancestry,
                              "types": ancestry.bottom_up,
                              "_context_dict": context,
                              "_id_generator": id_generator,
                              "_storage_graph": storage_graph,
                              # Non-attributes (will be popped)
                              "registry": self.registry}

        # First reserved attribute check
        for name in special_attributes:
            if name in attributes:
                raise ReservedAttributeNameError(u"%s is reserved" % name)
        attributes.update(special_attributes)

        model_cls = type(class_name, (Model,), attributes)
        for type_uri in ancestry.top_down:
            methods = self._methods.get(type_uri)
            if methods is not None:
                for method, name in methods:
                    setattr(model_cls, name, method)
        return model_cls


def extract_class_uri(class_name, context):
    """
        Extracts the class URI as the type of a blank node
    """
    g = Graph().parse(data=json.dumps({u"@type": class_name}),
                      context=context, format="json-ld")
    class_uri = unicode(g.objects().next())

    # Check the URI
    result = urlparse(class_uri)
    if result.scheme == u"file":
        raise UndeclaredClassNameError(u"Deduced URI %s is not a valid HTTP URL" % class_uri)
    return class_uri
