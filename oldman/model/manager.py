import json
import logging
from urlparse import urlparse
from uuid import uuid4

from rdflib import Graph
from oldman.model.converter import ModelConversionManager, EquivalentModelConverter

from oldman.model.model import Model, ClientModel
from oldman.exception import OMUndeclaredClassNameError, OMExpiredMethodDeclarationTimeSlotError
from oldman.iri import PrefixedUUIDIriGenerator, IncrementalIriGenerator, BlankNodeIriGenerator
from oldman.parsing.schema.attribute import OMAttributeExtractor
from oldman.parsing.operation import HydraOperationExtractor
from oldman.vocabulary import HYDRA_COLLECTION_IRI, HYDRA_PAGED_COLLECTION_IRI, HTTP_POST
from oldman.model.operation import append_to_hydra_collection, append_to_hydra_paged_collection
from oldman.model.registry import ModelRegistry
from oldman.model.ancestry import ClassAncestry


DEFAULT_MODEL_NAME = "Thing"


class ModelManager(object):
    """
    TODO: update this documentation

    The `model_manager` is the central object of this OLDM.

    It gives access to the :class:`~oldman.store.datastore.DataStore` object
    and creates :class:`~oldman.model.Model` objects.
    It also creates, retrieves and caches :class:`~oldman.resource.Resource` objects.

    Internally, it owns a :class:`~oldman.resource.registry.ModelRegistry` object.

    TODO: UPDATE DESCRIPTION

    :param schema_graph: :class:`rdflib.Graph` object containing all the schema triples.
    :param data_store: :class:`~oldman.store.datastore.DataStore` object. Supports CRUD operations on
                       :class:`~oldman.resource.Resource` objects.
    :param attr_extractor: :class:`~oldman.parsing.attribute.OMAttributeExtractor` object that
                            will extract :class:`~oldman.attribute.OMAttribute` for generating
                            new :class:`~oldman.model.Model` objects.
                            Defaults to a new instance of :class:`~oldman.parsing.attribute.OMAttributeExtractor`.
    :param oper_extractor: TODO: describe.
    :param declare_default_operation_functions: TODO: describe.
    """
    _managers = {}

    def __init__(self, schema_graph=None, attr_extractor=None, oper_extractor=None,
                 declare_default_operation_functions=True):
        self._attr_extractor = attr_extractor if attr_extractor is not None else OMAttributeExtractor()
        self._operation_extractor = oper_extractor if oper_extractor is not None else HydraOperationExtractor()
        self._schema_graph = schema_graph
        self._methods = {}
        self._operation_functions = {}
        self._registry = ModelRegistry()
        self._logger = logging.getLogger(__name__)
        self._name = uuid4()
        self._managers[self._name] = self

        self._include_reversed_attributes = False

        # Registered with the "None" key
        #TODO: in which store??
        #self.create_model(DEFAULT_MODEL_NAME, {u"@context": {}}, untyped=True,
        #                  iri_prefix=u"http://localhost/.well-known/genid/default/", is_default=True)

        #TODO: examine their relevance
        if declare_default_operation_functions:
            self.declare_operation_function(append_to_hydra_collection, HYDRA_COLLECTION_IRI, HTTP_POST)
            self.declare_operation_function(append_to_hydra_paged_collection, HYDRA_PAGED_COLLECTION_IRI, HTTP_POST)

    @property
    def name(self):
        """Name of this manager.
        The manager can be retrieved from its name by calling the
        class method :func:`~oldman.resource.manager.ModelManager.get_manager`.
        """
        return self._name

    @property
    def include_reversed_attributes(self):
        """Is `True` if at least one of its models use some reversed attributes."""
        return self._include_reversed_attributes

    @property
    def non_default_models(self):
        """TODO: describe."""
        return self._registry.non_default_models

    @classmethod
    def get_manager(cls, name):
        """Gets a :class:`~oldman.resource.manager.ModelManager` object by its name.

        :param name: manager name.
        :return: A :class:`~oldman.resource.manager.ModelManager` object.
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
        :param class_iri: Targeted RDFS class. If not overwritten, all the instances
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

    def declare_operation_function(self, func, class_iri, http_method):
        """
        TODO: comment
        """
        if self._registry.has_specific_models():
            raise OMExpiredMethodDeclarationTimeSlotError(u"Operation declaration cannot occur after model creation.")

        http_method = http_method.upper()
        if class_iri in self._operation_functions:
            if http_method in self._methods[class_iri]:
                self._logger.warn(u"Operation %s of %s is overloaded." % (http_method, class_iri))
            self._operation_functions[class_iri][http_method] = func
        else:
            self._operation_functions[class_iri] = {http_method: func}

    def find_models_and_types(self, type_set):
        """See :func:`oldman.resource.registry.ModelRegistry.find_models_and_types`."""
        return self._registry.find_models_and_types(type_set)

    def create_model(self, class_name_or_iri, context, data_store, iri_prefix=None, iri_fragment=None,
                     iri_generator=None, untyped=False, incremental_iri=False, is_default=False):
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
        """

        # Only for the DefaultModel
        if untyped:
            class_iri = None
            ancestry = ClassAncestry(class_iri, self._schema_graph)
            om_attributes = {}
        else:
            class_iri = _extract_class_iri(class_name_or_iri, context)
            ancestry = ClassAncestry(class_iri, self._schema_graph)
            om_attributes = self._attr_extractor.extract(class_iri, ancestry.bottom_up, context,
                                                         self._schema_graph)
        if iri_generator is not None:
            id_generator = iri_generator
        elif iri_prefix is not None:
            if incremental_iri:
                id_generator = IncrementalIriGenerator(iri_prefix, data_store,
                                                       class_iri, fragment=iri_fragment)
            else:
                id_generator = PrefixedUUIDIriGenerator(iri_prefix, fragment=iri_fragment)
        else:
            id_generator = BlankNodeIriGenerator()

        methods = {}
        for m_dict in [self._methods.get(t, {}) for t in ancestry.top_down]:
            methods.update(m_dict)

        operations = self._operation_extractor.extract(ancestry, self._schema_graph,
                                                       self._operation_functions)

        model = Model(class_name_or_iri, class_iri, ancestry.bottom_up, context, om_attributes,
                      id_generator, methods=methods, operations=operations)
        self._add_model(model, is_default=is_default)

        # Reversed attributes awareness
        if not self._include_reversed_attributes:
            self._include_reversed_attributes = model.has_reversed_attributes

        return model

    def get_model(self, class_name_or_iri):
        return self._registry.get_model(class_name_or_iri)

    def _add_model(self, model, is_default=False):
        self._registry.register(model, is_default=is_default)


class ClientModelManager(ModelManager):
    """TODO: complete """

    def __init__(self, resource_manager, **kwargs):
        ModelManager.__init__(self, **kwargs)
        self._resource_manager = resource_manager
        self._conversion_manager = ModelConversionManager()

    # @property
    # def resource_manager(self):
    #     return self._resource_manager

    def import_model(self, store_model, data_store, is_default=False):
        """TODO: describe """
        client_model = ClientModel.copy_store_model(self._resource_manager, store_model)
        # Hierarchy registration
        self._registry.register(client_model, is_default=is_default)
        # Converter
        converter = EquivalentModelConverter(client_model, store_model)
        self._conversion_manager.register_model_converter(client_model, store_model, data_store,
                                                          converter)

    def convert_store_resources(self, store_resources):
        """TODO: describe """
        return self._conversion_manager.convert_store_to_client_resources(store_resources, self._resource_manager)


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
