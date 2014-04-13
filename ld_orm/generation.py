import json
from urlparse import urlparse
from exceptions import Exception
from uuid import uuid1
from rdflib import Graph
#from rdflib.plugins.sparql import prepareQuery
from .model import Model
from .registry import ModelRegistry


def default_model_generator():
    from ld_orm.extraction.attribute import LDAttributeExtractor
    attr_extractor = LDAttributeExtractor()
    return ModelManager(attr_extractor)


class UnknownClassNameError(Exception):
    """ When a local (file://) URL has been deduced from the class name.
        This happens when the class name is not defined in the context
    """
    pass


class ModelManager(object):

    def __init__(self, attr_manager):
        self._attr_manager = attr_manager
        self._registry = ModelRegistry()

    @property
    def registry(self):
        return self._registry

    def generate(self, class_name, context, schema_graph, storage_graph, uri_prefix=None, uri_generator=None):
        """
            Generates a model class
        """
        class_uri = self._extract_class_uri(class_name, context)
        types = self._extract_types(class_uri, schema_graph)
        #print "Types: %s" % types
        attributes = self._attr_manager.extract(class_uri, context, schema_graph)

        if uri_generator:
            id_generator = uri_generator
        elif uri_prefix:
            id_generator = RandomPrefixedUriGenerator(prefix=uri_prefix)
        else:
            raise Exception("Please specify uri_prefix or uri_generator")

        registry = self.registry

        attributes.update({"class_uri": class_uri,
                           "types": types,
                           "registry": self.registry,
                           "_context_dict": context,
                           "_id_generator": id_generator,
                           "_storage_graph": storage_graph})
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
        types = [class_uri]
        results = schema_graph.query("SELECT ?c WHERE { <%s> rdfs:subClassOf+ ?c }" % class_uri)
        types += [str(r) for r, in results]
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