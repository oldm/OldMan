import json
from urlparse import urlparse
from exceptions import Exception
from uuid import uuid1
from rdflib import Graph
#from rdflib.plugins.sparql import prepareQuery
from .model import Model
from .registry import ModelRegistry


def default_model_generator(schema_graph, default_graph):
    from ld_orm.extraction.attribute import LDAttributeExtractor
    attr_extractor = LDAttributeExtractor()
    return ModelManager(attr_extractor, schema_graph, default_graph)


class UnknownClassNameError(Exception):
    """ When a local (file://) URL has been deduced from the class name.
        This happens when the class name is not defined in the context
    """
    pass


class ModelManager(object):

    def __init__(self, attr_manager, schema_graph, default_graph):
        self._attr_manager = attr_manager
        self._registry = ModelRegistry(default_graph)
        self._schema_graph = schema_graph
        self._default_graph = default_graph

        # Registered with the "None" key
        UntypedModel = self.generate("UntypedModel", {"@context": {}}, default_graph,
                                     uri_prefix="http://localhost/.well-known/genid/untyped/",
                                     untyped=True)

    @property
    def registry(self):
        return self._registry

    def generate(self, class_name, context, storage_graph, uri_prefix=None,
                 uri_generator=None, untyped=False):
        """
            Generates a model class
        """

        # Only for UntypedModel
        if untyped:
            class_uri = None
            types = set()
            attributes = {}
        else:
            class_uri = self._extract_class_uri(class_name, context)
            types = self._extract_types(class_uri, self._schema_graph)
            attributes = self._attr_manager.extract(class_uri, context,
                                                    self._schema_graph)

        if uri_generator:
            id_generator = uri_generator
        elif uri_prefix:
            id_generator = RandomPrefixedUriGenerator(prefix=uri_prefix)
        else:
            raise Exception("Please specify uri_prefix or uri_generator")

        registry = self.registry

        attributes.update({"class_uri": class_uri,
                           "types": types,
                           "_context_dict": context,
                           "_id_generator": id_generator,
                           "_storage_graph": storage_graph,
                           # Non-attributes (will be popped)
                           "registry": self.registry,
                           "default_graph": self._default_graph,
                           "schema_graph": self._schema_graph})
        return type(class_name, (Model,), attributes)

    def _extract_class_uri(self, class_name, context):
        """
            Extracts the class URI as the type of a blank node
        """
        g = Graph().parse(data=json.dumps({"@type": class_name}),
                            context=context, format="json-ld")
        class_uri = str(g.objects().next())

        # Check the URI
        result = urlparse(class_uri)
        if result.scheme == "file":
            raise UnknownClassNameError("Deduced URI %s is not a valid HTTP URL" % class_uri)
        return class_uri

    def _extract_types(self, class_uri, schema_graph):
        """
            Useful because class_uri is often a local specialization
            of a well-known class
        """
        types = set([class_uri])
        results = schema_graph.query("SELECT ?c WHERE { <%s> rdfs:subClassOf+ ?c }" % class_uri)
        types.update([str(r) for r, in results])
        return types


class UriGenerator(object):

    def __init__(self, **kwargs):
        pass

    def generate(self):
        raise NotImplementedError()


class RandomPrefixedUriGenerator(UriGenerator):

    def __init__(self, **kwargs):
        self.prefix = kwargs["prefix"]

    def generate(self):
        return "%s%s"%(self.prefix, uuid1().hex)

class RandomUriGenerator(RandomPrefixedUriGenerator):

    def __init__(self, **kwargs):
        hostname = kwargs.get("hostname", "localhost")
        prefix = "http://%s/.well-known/genid/"
        RandomPrefixedUriGenerator.__init__(self, prefix=prefix)