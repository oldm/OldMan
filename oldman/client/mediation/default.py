from logging import getLogger

from oldman.client.mediation.broker import Model2ModelBroker
from oldman.client.model.manager import ClientModelManager
from oldman.storage.model.conversion.converter import EquivalentModelConverter
from oldman.storage.model.conversion.manager import ModelConversionManager
from oldman.client.mediation.store_selector import StoreSelector
from oldman.client.mediation.mediator import Mediator
from oldman.client.session import DefaultClientSession

DEFAULT_MODEL_NAME = "Default_Client"


class DefaultMediator(Mediator):

    def __init__(self, oper_extractor, schema_graph=None, attr_extractor=None):
        self._logger = getLogger(__name__)
        self._store_selector = StoreSelector()

        self._model_manager = ClientModelManager(oper_extractor, attr_extractor=attr_extractor)

        # Default model
        self._model_manager.create_model(DEFAULT_MODEL_NAME, {u"@context": {}}, untyped=True, is_default=True,
                                         accept_new_blank_nodes=True)

        self._conversion_manager = ModelConversionManager()
        self._broker = Model2ModelBroker(self._store_selector, self._conversion_manager)

    def declare_method(self, method, name, class_iri):
        """
        TODO: point this comment to the definition.
        """

        models = self._model_manager.find_descendant_models(class_iri)
        for model in models:
            if model.class_iri is None:
                continue
            model.declare_method(method, name, class_iri)

    # def import_store_model(self, class_iri, data_store=None):
    #     raise NotImplementedError("TODO: implement me here")
    #
    # def import_store_models(self, store=None):
    #     """TODO: check possible conflicts with local models."""
    #     stores = [store] if store is not None else self._store_selector.stores
    #
    #     for store in stores:
    #         for store_model in store.model_manager.models:
    #             is_default = (store_model.class_iri is None)
    #             client_model = self._model_manager.import_model(store_model, is_default=is_default,
    #                                                             store_schema_graph=store.model_manager.schema_graph)
    #             # Converter
    #             converter = EquivalentModelConverter(client_model, store_model)
    #             self._conversion_manager.register_model_converter(client_model, store_model, store, converter)

    def create_model(self, class_name_or_iri, context_iri_or_payload, schema_graph, context_file_path=None):
        client_model = self._model_manager.create_model(class_name_or_iri, context_iri_or_payload, schema_graph,
                                                        context_file_path=context_file_path)
        return client_model

    def get_client_model(self, class_name_or_iri):
        return self._model_manager.get_model(class_name_or_iri)

    def bind_store(self, store_proxy, client_model):
        self._store_selector.bind_store(store_proxy, client_model)

        # Temporary code (for transition)
        # TODO: remove
        self._bind_to_store_model(store_proxy, client_model)

    def create_session(self):
        """TODO: explain it """
        return DefaultClientSession(self._model_manager, self._broker)

    def _bind_to_store_model(self, store_proxy, client_model):
        """
        Transition code.
        TODO: remove """
        for store_model in store_proxy.model_manager.models:
            if client_model.class_iri == store_model.class_iri:
                # Converter
                converter = EquivalentModelConverter(client_model, store_model)
                self._conversion_manager.register_model_converter(client_model, store_model, store_proxy, converter)
                return

        raise Exception("No store model found (temporary solution) for %s" % client_model.class_iri)
