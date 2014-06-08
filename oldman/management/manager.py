import json
import logging
from urlparse import urlparse
from rdflib import Graph
from oldman.model import Model
from oldman.resource import Resource
from oldman.exception import OMUndeclaredClassNameError, OMExpiredMethodDeclarationTimeSlotError, OMError
from oldman.iri import PrefixedUUIDIriGenerator, IncrementalIriGenerator, BlankNodeIriGenerator
from oldman.parsing.schema.attribute import OMAttributeExtractor
from .registry import ModelRegistry
from .ancestry import ClassAncestry
from .cache import ResourceCache
from .finder import ResourceFinder


DEFAULT_MODEL_NAME = "Thing"


class ResourceManager(object):
    """The `resource_manager` is the central object of this OLDM.

    It gives access to the graphs and creates :class:`~oldman.model.Model` objects.
    It also creates, retrieves and caches :class:`~oldman.resource.Resource` objects.

    Internally, it owns three objects a :class:`~oldman.management.finder.ResourceFinder`,
    a :class:`~oldman.management.registry.ModelRegistry` and a :class:`~oldman.management.cache.ResourceCache`.

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
    :param cache_region: :class:`dogpile.cache.region.CacheRegion` object.
                         This object must already be configured.
                         Defaults to None (no cache).
                         See :class:`~oldman.management.cache.ResourceCache` for further details.
    :param manager_name: Name of this manager. Defaults to `"default"`. This name must be unique.
    """
    _managers = {}

    def __init__(self, schema_graph, data_graph, union_graph=None, attr_extractor=None,
                 cache_region=None, manager_name="default"):
        self._attr_extractor = attr_extractor if attr_extractor is not None else OMAttributeExtractor()
        self._schema_graph = schema_graph
        self._union_graph = union_graph if union_graph is not None else data_graph
        self._data_graph = data_graph
        self._methods = {}
        self._registry = ModelRegistry()
        self._finder = ResourceFinder(self)
        self._resource_cache = ResourceCache(cache_region)
        self._logger = logging.getLogger(__name__)
        self._name = manager_name
        if manager_name in self._managers:
            raise OMError(u"Manager name %s is already allocated" % manager_name)
        self._managers[manager_name] = self

        # Registered with the "None" key
        self._create_model(DEFAULT_MODEL_NAME, {u"@context": {}}, untyped=True,
                           iri_prefix=u"http://localhost/.well-known/genid/default/", is_default=True)

    @property
    def data_graph(self):
        """:class:`rdflib.Graph` attribute where all the non-schema resources are stored by default."""
        return self._data_graph

    @property
    def union_graph(self):
        """Union of all the named graphs of a :class:`rdflib.ConjunctiveGraph` or a :class:`rdflib.Dataset`.
        Super-set of `data_graph` and may also include `schema_graph`.
        Read-only attribute.
        """
        return self._union_graph

    @property
    def name(self):
        """Name of this manager.
        The manager can be retrieved from its name by calling the
        class method :func:`~oldman.management.manager.ResourceManager.get_manager`.
        """
        return self._name

    @property
    def resource_cache(self):
        """:class:`~oldman.management.cache.ResourceCache` object."""
        return self._resource_cache

    @classmethod
    def get_manager(cls, name):
        """Gets a :class:`~oldman.management.manager.ResourceManager` object by its name.

        :param name: manager name.
        :return: A :class:`~oldman.management.manager.ResourceManager` object.
        """
        return cls._managers.get(name)

    def declare_method(self, method, name, class_iri):
        """Attaches a method to the :class:`~oldman.resource.Resource` objects that are instances of a given RDFS class.

        Like in Object-Oriented Programming, this method can be overwritten by attaching a homonymous
        method to a class that has a higher inheritance priority (such as a sub-class).

        To benefit from this method (or an overwritten one), :class:`~oldman.resource.Resource` objects
        must be associated to a :class:`~oldman.model.Model` that corresponds to the RDFS class or to one of its
        subclasses.

        This method can only be used before the creation of any model (except the default one).

        :param method: Python function that takes as first argument a :class:`~oldman.resource.Resource` object.
        :param name: Name assigned to this method.
        :param class_iri: Targetted RDFS class. If not overwritten, all the instances
                          (:class:`~oldman.resource.Resource` objects) should inherit this method.
        """
        if self._registry.has_specific_models():
            raise OMExpiredMethodDeclarationTimeSlotError(u"Method declaration cannot occur after model creation.")

        if class_iri in self._methods:
            if name in self._methods[class_iri]:
                self._logger.warn(u"Method %s of %s is overloaded." % (name, class_iri))
            self._methods[class_iri][name] = method
        else:
            self._methods[class_iri] = {name: method}

    def create_model(self, class_name_or_iri, context, iri_generator=None, iri_prefix=None,
                     iri_fragment=None, incremental_iri=False):
        """Creates a :class:`~oldman.model.Model` object.

        To create it, they are three elements to consider:

          1. Its class IRI which can be retrieved from `class_name_or_iri`;
          2. Its JSON-LD context for mapping :class:`~oldman.attribute.OMAttribute` values to RDF triples;
          3. The :class:`~oldman.iri.IriGenerator` object that generates IRIs from new
             :class:`~oldman.resource.Resource` objects.

        The :class:`~oldman.iri.IriGenerator` object is either:

          * directly given: `iri_generator`;
          * created from the parameters `iri_prefix`, `iri_fragment` and `incremental_iri`.

        :param class_name_or_iri: IRI or JSON-LD term of a RDFS class.
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
        :return: A new :class:`~oldman.model.Model` object.
        """
        return self._create_model(class_name_or_iri, context, iri_generator=iri_generator, iri_prefix=iri_prefix,
                                  iri_fragment=iri_fragment, incremental_uri=incremental_iri)

    def _create_model(self, class_name_or_iri, context, iri_prefix=None, iri_fragment=None,
                      iri_generator=None, untyped=False, incremental_uri=False, is_default=False):

        # Only for the DefaultModel
        if untyped:
            class_iri = None
            ancestry = ClassAncestry(class_iri, self._schema_graph)
            om_attributes = {}
        else:
            class_iri = _extract_class_iri(class_name_or_iri, context)
            ancestry = ClassAncestry(class_iri, self._schema_graph)
            om_attributes = self._attr_extractor.extract(class_iri, ancestry.bottom_up, context,
                                                         self._schema_graph, self)
        if iri_generator is not None:
            id_generator = iri_generator
        elif iri_prefix is not None:
            if incremental_uri:
                id_generator = IncrementalIriGenerator(iri_prefix, self._data_graph,
                                                       class_iri, fragment=iri_fragment)
            else:
                id_generator = PrefixedUUIDIriGenerator(iri_prefix, fragment=iri_fragment)
        else:
            id_generator = BlankNodeIriGenerator()

        methods = {}
        for m_dict in [self._methods.get(t, {}) for t in ancestry.top_down]:
            methods.update(m_dict)
        model = Model(self, class_name_or_iri, class_iri, ancestry.bottom_up, context, om_attributes,
                      id_generator, methods=methods)
        self._registry.register(model, is_default=is_default)
        return model

    def new(self, id=None, types=None, base_iri=None, **kwargs):
        """Creates a new :class:`~oldman.resource.Resource` object **without saving it** in the `data_graph`.

        The `kwargs` dict can contains regular attribute key-values that will be assigned to
        :class:`~oldman.attribute.OMAttribute` objects.

        :param id: IRI of the new resource. Defaults to `None`.
                   If not given, the IRI is generated by the IRI generator of the main model.
        :param types: IRIs of RDFS classes the resource is instance of. Defaults to `None`.
                      Note that these IRIs are used to find the models of the resource
                      (see :func:`~oldman.management.manager.ResourceManager.find_models_and_types` for more details).
        :param base_iri: base IRI that MAY be considered when generating an IRI for the new resource.
                         Defaults to `None`. Ignored if `id` is given.
        :return: A new :class:`~oldman.resource.Resource` object.
        """
        if (types is None or len(types) == 0) and len(kwargs) == 0:
            name = id if id is not None else ""
            self._logger.info(u"""New resource %s has no type nor attribute.
            As such, nothing is stored in the data graph.""" % name)
        return Resource(self, id=id, types=types, base_iri=base_iri, **kwargs)

    def create(self, id=None, types=None, base_iri=None, **kwargs):
        """Creates a new resource and save it in the `data_graph`.

        See :func:`~oldman.management.manager.ResourceManager.new` for more details.
        """
        return self.new(id=id, types=types, base_iri=base_iri, **kwargs).save()

    def get(self, id=None, types=None, base_iri=None, **kwargs):
        """See :func:`oldman.management.finder.ResourceFinder.get`."""
        return self._finder.get(id=id, types=types, base_iri=base_iri, **kwargs)

    def filter(self, types=None, base_iri=None, limit=None, eager=False, pre_cache_properties=None, **kwargs):
        """See :func:`oldman.management.finder.ResourceFinder.filter`."""
        return self._finder.filter(types=types, base_iri=base_iri, limit=limit, eager=eager,
                                   pre_cache_properties=pre_cache_properties, **kwargs)

    def sparql_filter(self, query):
        """See :func:`oldman.management.finder.ResourceFinder.sparql_filter`."""
        return self._finder.sparql_filter(query)

    def find_models_and_types(self, type_set):
        """See :func:`oldman.management.registry.ModelRegistry.find_models_and_types`."""
        return self._registry.find_models_and_types(type_set)


def _extract_class_iri(class_name, context):
    """Extracts the class IRI as the type of a blank node."""
    g = Graph().parse(data=json.dumps({u"@type": class_name}),
                      context=context, format="json-ld")
    class_iri = unicode(g.objects().next())

    # Check the URI
    result = urlparse(class_iri)
    if result.scheme == u"file":
        raise OMUndeclaredClassNameError(u"Deduced URI %s is not a valid HTTP URL" % class_iri)
    return class_iri