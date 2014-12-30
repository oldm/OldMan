import json
import logging
from urlparse import urlparse

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


class ModelManager(object):
    """
    TODO: update this documentation

    The `model_manager` creates and registers :class:`~oldman.model.Model` objects.

    Internally, it owns a :class:`~oldman.resource.registry.ModelRegistry` object.

    :param schema_graph: :class:`rdflib.Graph` object containing all the schema triples.
    :param data_store: :class:`~oldman.store.datastore.DataStore` object.
    :param attr_extractor: :class:`~oldman.parsing.attribute.OMAttributeExtractor` object that
                            will extract :class:`~oldman.attribute.OMAttribute` for generating
                            new :class:`~oldman.model.Model` objects.
                            Defaults to a new instance of :class:`~oldman.parsing.attribute.OMAttributeExtractor`.
    :param oper_extractor: TODO: describe.
    :param declare_default_operation_functions: TODO: describe.
    """

    def __init__(self, schema_graph=None, attr_extractor=None, oper_extractor=None,
                 declare_default_operation_functions=True):
        self._attr_extractor = attr_extractor if attr_extractor is not None else OMAttributeExtractor()
        self._operation_extractor = oper_extractor if oper_extractor is not None else HydraOperationExtractor()
        self._schema_graph = schema_graph
        self._operation_functions = {}
        self._registry = ModelRegistry()
        self._logger = logging.getLogger(__name__)

        self._include_reversed_attributes = False

        # TODO: examine their relevance
        if declare_default_operation_functions:
            self.declare_operation_function(append_to_hydra_collection, HYDRA_COLLECTION_IRI, HTTP_POST)
            self.declare_operation_function(append_to_hydra_paged_collection, HYDRA_PAGED_COLLECTION_IRI, HTTP_POST)

        # Create "anonymous" models
        if schema_graph is not None:
            self._create_anonymous_models()

    @property
    def include_reversed_attributes(self):
        """Is `True` if at least one of its models use some reversed attributes."""
        return self._include_reversed_attributes

    @property
    def models(self):
        """TODO: describe."""
        return self._registry.models

    @property
    def non_default_models(self):
        """TODO: describe."""
        return self._registry.non_default_models

    def has_default_model(self):
        return self._registry.default_model is not None

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

    def find_descendant_models(self, top_ancestor_name_or_iri):
        """TODO: explain. Includes the top ancestor. """
        return self._registry.find_descendant_models(top_ancestor_name_or_iri)

    def create_model(self, class_name_or_iri, context_iri_or_payload, data_store, iri_prefix=None, iri_fragment=None,
                     iri_generator=None, untyped=False, incremental_iri=False, is_default=False,
                     context_file_path=None):
        """Creates a :class:`~oldman.model.Model` object.

        TODO: remove data_store from the constructor!

        To create it, they are three elements to consider:

          1. Its class IRI which can be retrieved from `class_name_or_iri`;
          2. Its JSON-LD context for mapping :class:`~oldman.attribute.OMAttribute` values to RDF triples;
          3. The :class:`~oldman.iri.IriGenerator` object that generates IRIs from new
             :class:`~oldman.resource.Resource` objects.

        The :class:`~oldman.iri.IriGenerator` object is either:

          * directly given: `iri_generator`;
          * created from the parameters `iri_prefix`, `iri_fragment` and `incremental_iri`.

        :param class_name_or_iri: IRI or JSON-LD term of a RDFS class.
        :param context_iri_or_payload: `dict`, `list` or `IRI` that represents the JSON-LD context .
        :param iri_generator: :class:`~oldman.iri.IriGenerator` object. If given, other `iri_*` parameters are
               ignored.
        :param iri_prefix: Prefix of generated IRIs. Defaults to `None`.
               If is `None` and no `iri_generator` is given, a :class:`~oldman.iri.BlankNodeIriGenerator` is created.
        :param iri_fragment: IRI fragment that is added at the end of generated IRIs. For instance, `"me"`
               adds `"#me"` at the end of the new IRI. Defaults to `None`. Has no effect if `iri_prefix` is not given.
        :param incremental_iri: If `True` an :class:`~oldman.iri.IncrementalIriGenerator` is created instead of a
               :class:`~oldman.iri.RandomPrefixedIriGenerator`. Defaults to `False`.
               Has no effect if `iri_prefix` is not given.
        :param context_file_path: TODO: describe.
        """

        # Only for the DefaultModel
        if untyped:
            class_iri = None
            ancestry = ClassAncestry(class_iri, self._schema_graph)
            om_attributes = {}
        else:
            context_file_path_or_payload = context_file_path if context_file_path is not None \
                else context_iri_or_payload
            class_iri = _extract_class_iri(class_name_or_iri, context_file_path_or_payload)
            ancestry = ClassAncestry(class_iri, self._schema_graph)
            om_attributes = self._attr_extractor.extract(class_iri, ancestry.bottom_up, context_file_path_or_payload,
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

        operations = self._operation_extractor.extract(ancestry, self._schema_graph,
                                                       self._operation_functions)

        model = Model(class_name_or_iri, class_iri, ancestry.bottom_up, context_iri_or_payload, om_attributes,
                      id_generator, operations=operations, local_context=context_file_path)
        self._add_model(model, is_default=is_default)

        # Reversed attributes awareness
        if not self._include_reversed_attributes:
            self._include_reversed_attributes = model.has_reversed_attributes

        return model

    def get_model(self, class_name_or_iri):
        return self._registry.get_model(class_name_or_iri)

    def _add_model(self, model, is_default=False):
        self._registry.register(model, is_default=is_default)

    def _create_anonymous_models(self):
        """ These classes are typically derived from hydra:Link.
            Their role is just to support some operations.
         """
        req = """SELECT ?c WHERE {
            ?c a <http://www.w3.org/ns/hydra/core#Class> .
            FILTER (CONTAINS(STR(?c), "localhost/.well-known/genid") )
        }
        """
        classes = [unicode(r) for r, in self._schema_graph.query(req)]
        # The data store can be ignored here
        data_store = None

        for cls_iri in classes:
            self.create_model(cls_iri, {"@context": {}}, data_store)


class ClientModelManager(ModelManager):
    """Client ModelManager.

    Has access to the `resource_manager`.
    In charge of the conversion between and store and client models.
    """

    def __init__(self, resource_manager, **kwargs):
        ModelManager.__init__(self, **kwargs)
        self._resource_manager = resource_manager
        self._conversion_manager = ModelConversionManager()

    @property
    def resource_manager(self):
        return self._resource_manager

    def import_model(self, store_model, data_store, is_default=False):
        """ Imports a store model. Creates the corresponding client model. """
        if is_default:
            # Default model
            client_model = self.get_model(None)
        else:
            client_model = ClientModel.copy_store_model(self._resource_manager, store_model)
            # Hierarchy registration
            self._registry.register(client_model, is_default=False)
        # Converter
        converter = EquivalentModelConverter(client_model, store_model)
        self._conversion_manager.register_model_converter(client_model, store_model, data_store, converter)

    def convert_store_resources(self, store_resources):
        """Returns converted client resources. """
        return self._conversion_manager.convert_store_to_client_resources(store_resources, self._resource_manager)

    def convert_client_resource(self, client_resource):
        """Returns converted store resources. """
        return self._conversion_manager.convert_client_to_store_resource(client_resource)


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
