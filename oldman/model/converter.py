import types
from oldman.resource.resource import ClientResource, StoreResource


class ModelConversionManager(object):
    """TODO: describe and find a better name."""

    def __init__(self):
        # { (client_model, data_store): store_model }
        self._client_to_store_models = {}
        # { store_model: client_model
        self._store_to_client_models = {}
        # { (client_model, store_model): converter}
        self._converters = {}

    def register_model_converter(self, client_model, store_model, data_store, model_converter):
        self._client_to_store_models[(client_model, data_store)] = store_model
        self._store_to_client_models[store_model] = client_model
        self._converters[(client_model, store_model)] = model_converter

    def convert_store_to_client_resources(self, store_resources, client_resource_manager):
        """TODO: describe """
        if isinstance(store_resources, types.GeneratorType):
            return (self.convert_store_to_client_resource(r)
                    for r in store_resources)
        # Otherwise, returns a list
        return [self.convert_store_to_client_resource(r, client_resource_manager)
                for r in store_resources]

    def convert_store_to_client_resource(self, store_resource, client_resource_manager):
        client_types = self._extract_types_from_store_resource(store_resource)

        client_model_manager = client_resource_manager.model_manager

        # Mutable
        client_resource = ClientResource(client_resource_manager, client_model_manager, store_resource.store,
                                         id=store_resource.id, types=client_types, is_new=False)
        store = store_resource.store

        # Client models from the most general to the more specific
        client_models = list(client_resource.models)
        client_models.reverse()
        for client_model in client_models:
            # Corresponding store model
            store_model = self._client_to_store_models.get((client_model, store))
            if store_model is None:
                #TODO: find a better exception
                raise Exception("No store model associate to %s" % client_model.name)

            converter = self._converters[(client_model, store_model)]

            # Update the client resource according to the model properties
            converter.from_store_to_client(store_resource, client_resource)

        return client_resource

    def convert_client_to_store_resource(self, client_resource):
        # Same store between the client_resource and the store_resource
        store = client_resource.store
        store_types = self._extract_types_from_store_resource(client_resource)

        #TODO: should we consider late IRI attributions?
        store_resource = StoreResource(store.model_manager, store, id=client_resource.id,
                                       types=store_types, is_new=False)

        # From the most general to the more specific
        store_models = list(store_resource.models)
        store_models.reverse()

        for store_model in store_models:
            client_model = self._store_to_client_models.get(store_model)
            if client_model is None:
                #TODO: find a better exception
                raise Exception("No client model associate to %s" % store_model.name)

            converter = self._converters[(client_model, store_model)]

            # Update the client resource according to the model properties
            converter.from_client_to_store(client_resource, store_resource)

        return store_resource

    def _extract_types_from_store_resource(self, store_resource):
        client_models = [self._store_to_client_models.get(store_model)
                         for store_model in store_resource.models]
        if None in client_models:
            #TODO: See if relevant and find a better name
            raise Exception("No client model corresponding to %s" % store_model.name)

        return {m.class_iri for m in client_models}.union(store_resource.types)

    def _extract_types_from_client_resource(self, client_resource):
        store = client_resource.store
        store_models = [self._client_to_store_models.get((client_model, store))
                        for client_model in client_resource.models]
        if None in store_models:
            #TODO: See if relevant and find a better name
            raise Exception("No store model corresponding to %s" % client_model.name)

        return {m.class_iri for m in store_models}.union(client_resource.types)


class ModelConverter(object):
    """TODO: find a better name and explain """

    def from_client_to_store(self, client_resource, store_resource):
        raise NotImplementedError("Should be implemented by a sub-class")

    def from_store_to_client(self, store_resource, client_resource):
        raise NotImplementedError("Should be implemented by a sub-class")


class DirectMappingModelConverter(ModelConverter):

    def __init__(self, client_to_store_mappings):
        """

        :param client_to_store_mappings: Attribute mapping
        :return:
        """
        self._client_to_store_mappings = client_to_store_mappings
        self._store_to_client_mappings = {v: k for k, v in client_to_store_mappings.items()}

    def from_client_to_store(self, client_resource, store_resource):
        self._transfer_values(client_resource, store_resource, self._client_to_store_mappings)

    def from_store_to_client(self, store_resource, client_resource):
        self._transfer_values(store_resource, client_resource, self._store_to_client_mappings)

    @staticmethod
    def _transfer_values(source_resource, target_resource, mappings):
        for source_attr_name, target_attr_name in mappings.items():
            value = source_resource.get_lightly(source_attr_name)
            setattr(target_resource, target_attr_name, value)


class EquivalentModelConverter(DirectMappingModelConverter):
    """TODO: describe """

    def __init__(self, client_model, store_model):
        mappings = {attr_name: attr_name for attr_name in client_model.om_attributes}
        DirectMappingModelConverter.__init__(self, mappings)
        #TODO: check that the models are equivalent


