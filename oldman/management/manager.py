import json
from urlparse import urlparse
from rdflib import Graph
from oldman.model import Model
from oldman.resource import Resource
from oldman.exception import OMUndeclaredClassNameError
from oldman.iri import RandomPrefixedIriGenerator, IncrementalIriGenerator, BlankNodeIriGenerator
from oldman.parsing.schema.attribute import OMAttributeExtractor
from .registry import ModelRegistry
from .ancestry import ClassAncestry
from .finder import Finder


DEFAULT_MODEL_NAME = "Thing"


def create_resource_manager(schema_graph, data_graph, union_graph=None):
    """
        By default, union_graph = data_graph
    """
    attr_extractor = OMAttributeExtractor()
    return ResourceManager(attr_extractor, schema_graph, data_graph, union_graph)


class ResourceManager(object):

    def __init__(self, attr_extractor, schema_graph, data_graph, union_graph=None):
        """
            By default, union_graph = data_graph
        """
        self._attr_extractor = attr_extractor
        self._schema_graph = schema_graph
        self._union_graph = union_graph if union_graph is not None else data_graph
        self._data_graph = data_graph
        self._methods = {}
        self._registry = ModelRegistry(self, DEFAULT_MODEL_NAME)
        self._finder = Finder(self)
        # Registered with the "None" key
        self._create_model(DEFAULT_MODEL_NAME, {u"@context": {}}, untyped=True,
                           iri_prefix=u"http://localhost/.well-known/genid/default/")

    @property
    def model_registry(self):
        return self._registry

    @property
    def data_graph(self):
        """  Graph where resource data is added (by default) """
        return self._data_graph

    @property
    def union_graph(self):
        """ Union of all the data graphs (one or more) """
        return self._union_graph

    def add_method(self, method, name, class_iri):
        """
            TODO: Warns when a method is overwritten
        """
        if class_iri in self._methods:
            self._methods[class_iri][name] = method
        else:
            self._methods[class_iri] = {name: method}

    def create_model(self, class_name, context, iri_prefix=None,
                     iri_fragment=None, iri_generator=None, incremental_iri=False):
        """
            Generates a model class
        """
        return self._create_model(class_name, context, iri_prefix=iri_prefix, iri_fragment=iri_fragment,
                                  iri_generator=iri_generator, incremental_uri=incremental_iri)

    def _create_model(self, class_name, context, iri_prefix=None, iri_fragment=None,
                      iri_generator=None, untyped=False, incremental_uri=False):

        # Only for the DefaultModel
        if untyped:
            class_iri = None
            ancestry = ClassAncestry(class_iri, self._schema_graph)
            om_attributes = {}
        else:
            class_iri = extract_class_iri(class_name, context)
            ancestry = ClassAncestry(class_iri, self._schema_graph)
            om_attributes = self._attr_extractor.extract(class_iri, ancestry.bottom_up, context,
                                                         self._schema_graph)
        if iri_generator is not None:
            id_generator = iri_generator
        elif iri_prefix is not None:
            if incremental_uri:
                id_generator = IncrementalIriGenerator(iri_prefix, self._data_graph,
                                                       class_iri, fragment=iri_fragment)
            else:
                id_generator = RandomPrefixedIriGenerator(iri_prefix, fragment=iri_fragment)
        else:
            id_generator = BlankNodeIriGenerator()

        methods = {}
        for m_dict in [self._methods.get(t, {}) for t in ancestry.top_down]:
            methods.update(m_dict)
        model = Model(class_name, class_iri, om_attributes, context,
                      id_generator, ancestry.bottom_up, self, methods=methods)

        return model

    def new(self, **kwargs):
        """
            New resource
        """
        return Resource(self, **kwargs)

    def create(self, **kwargs):
        """
            Creates a new resource and saves it
        """
        return self.new(**kwargs).save()

    def get(self, id=None, **kwargs):
        """Get a resource """
        return self._finder.get(id=id, **kwargs)

    def filter(self, **kwargs):
        return self._finder.filter(**kwargs)

    def clear_resource_cache(self):
        self._finder.clear_cache()


def extract_class_iri(class_name, context):
    """
        Extracts the class URI as the type of a blank node
    """
    g = Graph().parse(data=json.dumps({u"@type": class_name}),
                      context=context, format="json-ld")
    class_iri = unicode(g.objects().next())

    # Check the URI
    result = urlparse(class_iri)
    if result.scheme == u"file":
        raise OMUndeclaredClassNameError(u"Deduced URI %s is not a valid HTTP URL" % class_iri)
    return class_iri
