from oldman.model.conversion.entry import ClientToStoreEntryCloner, StoreToClientEntryCloner


class ModelConverter(object):
    """TODO: find a better name and explain """

    def from_client_to_store(self, client_resource, store_resource, conversion_manager):
        raise NotImplementedError("Should be implemented by a sub-class")

    def from_store_to_client(self, store_resource, client_resource, conversion_manager):
        raise NotImplementedError("Should be implemented by a sub-class")


class DirectMappingModelConverter(ModelConverter):

    def __init__(self, client_to_store_mappings):
        """

        :param client_to_store_mappings: Attribute mapping
        :return:
        """
        self._client_to_store_mappings = client_to_store_mappings
        self._store_to_client_mappings = {v: k for k, v in client_to_store_mappings.items()}

    def from_client_to_store(self, client_resource, store_resource, conversion_manager):
        entry_cloner = ClientToStoreEntryCloner(conversion_manager, store_resource.store)
        self._transfer_values(client_resource, store_resource, self._client_to_store_mappings,
                              entry_cloner)

    def from_store_to_client(self, store_resource, client_resource, conversion_manager):
        entry_cloner = StoreToClientEntryCloner(conversion_manager, store_resource.store)
        self._transfer_values(store_resource, client_resource, self._store_to_client_mappings,
                              entry_cloner)

    @staticmethod
    def _transfer_values(source_resource, target_resource, mappings, entry_cloner):
        for source_attr_name, target_attr_name in mappings.items():
            # Attributes
            source_attr = source_resource.get_attribute(source_attr_name)
            target_attr = target_resource.get_attribute(target_attr_name)

            # Transfers a clone of the source entry
            source_entry = source_attr.get_entry(source_resource)
            if source_entry is not None:
                target_attr.set_entry(target_resource, entry_cloner.clone(source_attr, source_entry))


class EquivalentModelConverter(DirectMappingModelConverter):
    """TODO: describe """

    def __init__(self, client_model, store_model):
        mappings = {attr_name: attr_name for attr_name in client_model.om_attributes}
        DirectMappingModelConverter.__init__(self, mappings)
        #TODO: check that the models are equivalent
