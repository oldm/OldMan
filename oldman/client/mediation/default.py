from logging import getLogger

from oldman.client.mediation.exchange.model2model import Model2ModelBroker
from oldman.client.model.manager import ClientModelManager
from oldman.storage.model.conversion.converter import EquivalentModelConverter
from oldman.storage.model.conversion.manager import ModelConversionManager
from oldman.client.mediation.store_selector import StoreSelector
from oldman.client.mediation.mediator import Mediator
from oldman.client.session import DefaultClientSession


class DefaultMediator(Mediator):

    def __init__(self, schema_graph, contexts, oper_extractor, attr_extractor=None):
        self._logger = getLogger(__name__)
        self._store_selector = StoreSelector()
        self._schema_graph = schema_graph
        self._contexts = contexts

        # TODO: create all the models!

        self._model_manager = ClientModelManager(schema_graph, contexts, oper_extractor, attr_extractor=attr_extractor)

        # TODO: remove (Model2Model approach)
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

    # def create_model(self, class_name_or_iri, context_iri_or_payload, schema_graph, context_file_path=None):
    #     client_model = self._model_manager.create_model(class_name_or_iri, context_iri_or_payload, schema_graph,
    #                                                     context_file_path=context_file_path)
    #     return client_model

    def get_model(self, class_name_or_iri):
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
