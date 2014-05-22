import json
import logging
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


class ResourceManager(object):
    """The `resource_manager` is the central object of this OLDM.

    It gives access to the graphs, creates :class:`~oldman.model.Model` objects
    and retrieves :class:`~oldman.resource.Resource` objects.
    It also manages the resource cache.

    :param schema_graph: :class:`rdflib.Graph` object containing all the schema triples. May be independent of
                         `union_graph`.
    :param data_graph: :class:`rdflib.Graph` object where all the non-schema resources are stored by default.
    :param union_graph: Union of all the named graphs of a :class:`rdflib.ConjunctiveGraph` or a
                        :class:`rdflib.Dataset`.
                        Super-set of `data_graph` and may also include `schema_graph`.
                        Defaults to `data_graph`.
                        Read-only.
    :param attr_extractor: :class:`~oldman.parsing.attribute.OMAttributeExtractor` object that
                            will extract :class:`~oldman.attribute.OMAttribute` for generating
                            new :class:`~oldman.model.Model` objects.
                            Defaults to a new instance of :class:`~oldman.parsing.attribute.OMAttributeExtractor`.
    """

    def __init__(self, schema_graph, data_graph, union_graph=None, attr_extractor=None):
        self._attr_extractor = attr_extractor if attr_extractor is not None else OMAttributeExtractor()
        self._schema_graph = schema_graph
        self._union_graph = union_graph if union_graph is not None else data_graph
        self._data_graph = data_graph
        self._methods = {}
        self._registry = ModelRegistry(self, DEFAULT_MODEL_NAME)
        self._finder = Finder(self)
        self._logger = logging.getLogger(__name__)

        # Registered with the "None" key
        self._create_model(DEFAULT_MODEL_NAME, {u"@context": {}}, untyped=True,
                           iri_prefix=u"http://localhost/.well-known/genid/default/")

    @property
    def data_graph(self):
        """ :class:`rdflib.Graph` attribute where all the non-schema resources are stored by default."""
        return self._data_graph

    @property
    def union_graph(self):
        """Union of all the named graphs of a :class:`rdflib.ConjunctiveGraph` or a :class:`rdflib.Dataset`.
        Super-set of `data_graph` and may also include `schema_graph`.
        Read-only attribute.
        """
        return self._union_graph

    def declare_method(self, method, name, class_iri):
        """Attach a method to the :class:`~oldman.resource.Resource` that are instances of a given RDFS class.

        Like in Object-Oriented Programming, this method can be overwritten by attaching a homonymous
        method to a class that has an higher inheritance priority (such as a sub-class).

        To benefit from this method (or an overwritten one), :class:`~oldman.resource.Resource` objects
        must be associated to a :class:`~oldman.model.Model` that corresponds to the RDFS class or to one of its
        subclasses.

        :param method: Python function that takes as first argument a :class:`~oldman.resource.Resource` object.
        :param name: Name assigned to this method.
        :param class_iri: Targetted RDFS class. If not overwritten, all the instances
                          (:class:`~oldman.resource.Resource` objects) should inherit this method.
        """
        if class_iri in self._methods:
            if name in self._methods[class_iri]:
                self._logger.warn("Method %s of %s is overloaded." % (name, class_iri))
            self._methods[class_iri][name] = method
        else:
            self._methods[class_iri] = {name: method}

    def create_model(self, class_name, context, iri_generator=None, iri_prefix=None,
                     iri_fragment=None, incremental_iri=False):
        """Create a :class:`~oldman.model.Model` object.

        To create it, they are three elements to consider:
          1. Its class IRI which can be retrieved from `class_name`;
          2. Its JSON-LD context for mapping :class:`~oldman.attribute.OMAttribute` values to RDF triples;
          3. The :class:`~oldman.iri.IriGenerator` object that generates IRIs from new
             :class:`~oldman.resource.Resource` objects.

        The :class:`~oldman.iri.IriGenerator` object is either:
          * directly given: `iri_generator`;
          * created from the parameters `iri_prefix`, `iri_fragment` and `incremental_iri`.

        :param class_name: Name of the class IRI as declared in the JSON-LD context.
        :param context: `dict`, `list` or `IRI` that represents the JSON-LD context .
        :param iri_generator: :class:`~oldman.iri.IriGenerator` object. If given, other `iri_*` parameters are
               ignored.
        :param iri_prefix: Prefix of generated IRIs. Defaults to `None`.
               If is `None` and no `iri_generator` is given, a :class:`~oldman.iri.BlankNodeIriGenerator` is created.
        :param iri_fragment: IRI fragment that is added at the end of generated IRIs. For instance, `"me"`
               adds `"#me"` at the end of the new IRI. Defaults to `None`. Has no effect if `iri_prefix` is not given.
        :param incremental_iri: If `True` an :class:`~oldman.iri.IncrementalIriGenerator` is created instead of a
               :class:`~oldman.iri.RandomPrefixedIriGenerator`. Defaults to `False`.
               Has no effect if `iri_prefix` is not given.
        """
        return self._create_model(class_name, context, iri_generator=iri_generator, iri_prefix=iri_prefix,
                                  iri_fragment=iri_fragment, incremental_uri=incremental_iri)

    def _create_model(self, class_name, context, iri_prefix=None, iri_fragment=None,
                      iri_generator=None, untyped=False, incremental_uri=False):

        # Only for the DefaultModel
        if untyped:
            class_iri = None
            ancestry = ClassAncestry(class_iri, self._schema_graph)
            om_attributes = {}
        else:
            class_iri = _extract_class_iri(class_name, context)
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
        self._registry.register(model, class_name)
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

    def get(self, id=None, base_iri=None, **kwargs):
        """Get a resource """
        return self._finder.get(id=id, base_iri=base_iri, **kwargs)

    def filter(self, base_iri=None, **kwargs):
        return self._finder.filter(base_iri=base_iri, **kwargs)

    def sparql_filter(self, query):
        return self._finder.sparql_filter(query)

    def clear_resource_cache(self):
        self._finder.clear_cache()

    def find_models_and_types(self, type_set):
        return self._registry.find_models_and_types(type_set)


def _extract_class_iri(class_name, context):
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
