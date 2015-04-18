from logging import getLogger
from oldman.model.converter import EquivalentModelConverter, ModelConversionManager
from oldman.resource.client import ClientResource
from oldman.mediation.store_selector import StoreSelector
from oldman.model.manager.client import ClientModelManager
from oldman.mediation.mediator import UserMediator, ResourceMediator


DEFAULT_MODEL_NAME = "Default_Client"


class DefaultCoreMediator(UserMediator, ResourceMediator):

    def __init__(self, data_stores, schema_graph=None, attr_extractor=None, oper_extractor=None,
                 declare_default_operation_functions=True):
        self._logger = getLogger(__name__)
        self._store_selector = StoreSelector(data_stores)

        self._model_manager = ClientModelManager(self, schema_graph=schema_graph, attr_extractor=attr_extractor,
                                                 oper_extractor=oper_extractor,
                                                 declare_default_operation_functions=declare_default_operation_functions)

        # Default model
        self._model_manager.create_model(DEFAULT_MODEL_NAME, {u"@context": {}}, untyped=True,is_default=True,
                                         accept_new_blank_nodes=True)

        self._conversion_manager = ModelConversionManager()
        #TODO: consider using an external cache, like for store resources.
        self._updated_iris = {}

    @property
    def model_manager(self):
        return self._model_manager

    def declare_method(self, method, name, class_iri):
        """
        TODO: point this comment to the definition.
        """

        models = self._model_manager.find_descendant_models(class_iri)
        for model in models:
            if model.class_iri is None:
                continue
            model.declare_method(method, name, class_iri)

    def new(self, iri=None, types=None, hashless_iri=None, collection_iri=None, **kwargs):
        """
            TODO: point this comment to the definition.
        """
        if (types is None or len(types) == 0) and len(kwargs) == 0:
            name = iri if iri is not None else ""
            self._logger.info(u"""New resource %s has no type nor attribute.
            As such, nothing is stored in the data graph.""" % name)

        return ClientResource(self, iri=iri, types=types, hashless_iri=hashless_iri,
                              collection_iri=collection_iri, **kwargs)

    def create(self, iri=None, types=None, hashless_iri=None, collection_iri=None, **kwargs):
        """TODO: point this comment to the definition.
        """
        return self.new(iri=iri, types=types, hashless_iri=hashless_iri,
                        collection_iri=collection_iri, **kwargs).save()

    def get(self, iri=None, types=None, hashless_iri=None, eager_with_reversed_attributes=True, **kwargs):
        """See :func:`oldman.store.datastore.DataStore.get`."""
        #TODO: consider parallelism
        store_resources = [store.get(iri=iri, types=types, hashless_iri=hashless_iri,
                                     eager_with_reversed_attributes=eager_with_reversed_attributes, **kwargs)
                           for store in self._store_selector.select_stores(iri=iri, types=types,
                                                                           hashless_iri=hashless_iri, **kwargs)]
        returned_store_resources = filter(lambda x: x, store_resources)
        resources = self._conversion_manager.convert_store_to_client_resources(returned_store_resources, self)
        resource_count = len(resources)
        if resource_count == 1:
            return resources[0]
        elif resource_count == 0:
            return None
        #TODO: find a better exception and explain better
        #TODO: see if relevant
        raise Exception("Non unique object")

    def filter(self, types=None, hashless_iri=None, limit=None, eager=False, pre_cache_properties=None, **kwargs):
        """See :func:`oldman.store.datastore.DataStore.filter`."""
        #TODO: support again generator. Find a way to aggregate them.
        store_resources = [r for store in self._store_selector.select_stores(types=types, hashless_iri=hashless_iri,
                                                                             pre_cache_properties=pre_cache_properties,
                                                                             **kwargs)
                           for r in store.filter(types=types, hashless_iri=hashless_iri, limit=limit, eager=eager,
                                                 pre_cache_properties=pre_cache_properties, **kwargs)]
        return self._conversion_manager.convert_store_to_client_resources(store_resources, self)

    def sparql_filter(self, query):
        """See :func:`oldman.store.datastore.DataStore.sparql_filter`."""
        #TODO: support again generator. Find a way to aggregate them.
        store_resources = [r for store in self._store_selector.select_sparql_stores(query)
                           for r in store.sparql_filter(query)]
        return self._conversion_manager.convert_store_to_client_resources(store_resources, self)

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

    def save_resource(self, client_resource, is_end_user):
        store = self._store_selector.select_store(id=client_resource, types=client_resource.types)
        store_resource = self._conversion_manager.convert_client_to_store_resource(client_resource, store)
        store_resource.save(is_end_user)
        previous_id = client_resource.id
        new_id = store_resource.id

        # Keeps track of the temporary IRI replacement
        if previous_id != new_id:
            self._updated_iris[previous_id] = new_id
        return new_id

    def delete_resource(self, client_resource):
        store = self._store_selector.select_store(id=client_resource, types=client_resource.types)
        store_resource = self._conversion_manager.convert_client_to_store_resource(client_resource, store)
        store_resource.delete()

    def get_updated_iri(self, tmp_iri):
        return self._updated_iris.get(tmp_iri, tmp_iri)
