import json
import logging
from urlparse import urlparse

from rdflib import Graph

from oldman.core.exception import OMUndeclaredClassNameError, OMExpiredMethodDeclarationTimeSlotError
from oldman.core.parsing.schema.attribute import OMAttributeExtractor
from oldman.core.model.registry import ModelRegistry
from oldman.core.model.ancestry import ClassAncestry


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
    """

    def __init__(self, attr_extractor=None):
        self._attr_extractor = attr_extractor if attr_extractor is not None else OMAttributeExtractor()
        self._operation_functions = {}
        self._registry = ModelRegistry()
        self._logger = logging.getLogger(__name__)

        self._include_reversed_attributes = False

        # # Create "anonymous" models
        # if schema_graph is not None:
        #     self._create_anonymous_models()

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
        """See :func:`oldman.model.registry.ModelRegistry.find_models_and_types`."""
        return self._registry.find_models_and_types(type_set)

    def find_main_model(self, type_set):
        """See :func:`oldman.model.registry.ModelRegistry.find_main_model`."""
        return self._registry.find_main_model(type_set)

    def find_descendant_models(self, top_ancestor_name_or_iri):
        """TODO: explain. Includes the top ancestor. """
        return self._registry.find_descendant_models(top_ancestor_name_or_iri)

    def _create_model(self, class_name_or_iri, context_iri_or_payload,
                      schema_graph, untyped=False, is_default=False, context_file_path=None, **kwargs):

        # Only for the DefaultModel
        if untyped:
            class_iri = None
            ancestry = ClassAncestry(class_iri, schema_graph)
            om_attributes = {}

        # Regular models
        else:
            context_file_path_or_payload = context_file_path if context_file_path is not None \
                else context_iri_or_payload
            class_iri = _extract_class_iri(class_name_or_iri, context_file_path_or_payload)
            ancestry = ClassAncestry(class_iri, schema_graph)
            om_attributes = self._attr_extractor.extract(class_iri, ancestry.bottom_up,
                                                         context_file_path_or_payload,
                                                         schema_graph)

        model = self._instantiate_model(class_name_or_iri, class_iri, schema_graph, ancestry, context_iri_or_payload,
                                        om_attributes, context_file_path, **kwargs)

        self._add_model(model, is_default=is_default)

        # Reversed attributes awareness
        if not self._include_reversed_attributes:
            self._include_reversed_attributes = model.has_reversed_attributes

        # Anonymous classes derived from hydra:Link properties
        # self._create_anonymous_models(model, context_file_path, data_store)

        return model

    def _instantiate_model(self, class_name_or_iri, class_iri, schema_graph, ancestry, context_iri_or_payload,
                           om_attributes, local_context, **kwargs):
        raise NotImplementedError("To be implemented in sub-classes")

    def get_model(self, class_name_or_iri):
        return self._registry.get_model(class_name_or_iri)

    def _add_model(self, model, is_default=False):
        self._registry.register(model, is_default=is_default)

    # def _create_anonymous_models(self, model, context_iri_or_payload, data_store):
    #     """ These classes are typically derived from hydra:Link.
    #         Their role is just to support some operations.
    #      """
    #     classes = {attr.om_property.link_class_iri for attr in model.om_attributes.values()}.difference({None})
    #
    #     for cls_iri in classes:
    #         if self._registry.get_model(cls_iri) is None:
    #             self.create_model(cls_iri, context_iri_or_payload, data_store)


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