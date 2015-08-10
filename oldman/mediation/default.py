from logging import getLogger

from oldman.model.conversion.converter import EquivalentModelConverter
from oldman.model.conversion.manager import ModelConversionManager
from oldman.mediation.store_selector import StoreSelector
from oldman.model.manager.client import ClientModelManager
from oldman.mediation.mediator import UserMediator
from oldman.session.default import DefaultSession

DEFAULT_MODEL_NAME = "Default_Client"


class DefaultCoreMediator(UserMediator):

    def __init__(self, data_stores, schema_graph=None, attr_extractor=None, oper_extractor=None,
                 declare_default_operation_functions=True):
        self._logger = getLogger(__name__)
        self._store_selector = StoreSelector(data_stores)

        self._model_manager = ClientModelManager(schema_graph=schema_graph, attr_extractor=attr_extractor,
                                                 oper_extractor=oper_extractor,
                                                 declare_default_operation_functions=declare_default_operation_functions)

        # Default model
        self._model_manager.create_model(DEFAULT_MODEL_NAME, {u"@context": {}}, untyped=True,is_default=True,
                                         accept_new_blank_nodes=True)

        self._conversion_manager = ModelConversionManager()

    def declare_method(self, method, name, class_iri):
        """
        TODO: point this comment to the definition.
        """

        models = self._model_manager.find_descendant_models(class_iri)
        for model in models:
            if model.class_iri is None:
                continue
            model.declare_method(method, name, class_iri)

    def import_store_model(self, class_iri, data_store=None):
        raise NotImplementedError("TODO: implement me here")

    def import_store_models(self):
        """TODO: check possible conflicts with local models."""
        for store in self._store_selector.stores:
            for store_model in store.model_manager.models:
                is_default = (store_model.class_iri is None)
                client_model = self._model_manager.import_model(store_model, is_default=is_default)
                # Converter
                converter = EquivalentModelConverter(client_model, store_model)
                self._conversion_manager.register_model_converter(client_model, store_model, store, converter)

    def get_client_model(self, class_name_or_iri):
        return self._model_manager.get_model(class_name_or_iri)

    def create_session(self):
        """TODO: explain it """
        return DefaultSession(self._model_manager, self._store_selector, self._conversion_manager)
